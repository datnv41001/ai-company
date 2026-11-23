-- LOGINs are provisioned separately, with one password per process.
DO $$
BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='amc_pool_worker') THEN CREATE ROLE amc_pool_worker NOLOGIN; END IF;
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='amc_dispatch') THEN CREATE ROLE amc_dispatch NOLOGIN; END IF;
END $$;
DO $$
BEGIN
 IF EXISTS(SELECT FROM pg_roles r WHERE r.rolname IN ('amc_dispatch','amc_pool_worker') AND
   (r.rolcanlogin OR r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication
    OR EXISTS(SELECT FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid WHERE m.member=r.oid
      AND (r.rolname='amc_pool_worker' OR g.rolname<>'amc_runtime')))) THEN
   RAISE EXCEPTION 'Unexpected privileges on pool group';
 END IF;
END $$;
GRANT amc_runtime TO amc_dispatch;
CREATE SCHEMA amc_ops;
REVOKE ALL ON SCHEMA amc_ops FROM PUBLIC;
GRANT USAGE ON SCHEMA amc_ops TO amc_dispatch,amc_pool_worker,amc_runtime;
CREATE TABLE amc_ops.agencies(
 tenant text PRIMARY KEY REFERENCES public.tenants(id), enabled boolean NOT NULL DEFAULT true,
 capacity int NOT NULL CHECK(capacity BETWEEN 1 AND 64), served bigint NOT NULL DEFAULT 0);
CREATE SEQUENCE amc_ops.turn;
CREATE TABLE amc_ops.periods(
 tenant text REFERENCES amc_ops.agencies, month date NOT NULL, ceiling bigint NOT NULL CHECK(ceiling>=0),
 PRIMARY KEY(tenant,month));
CREATE TABLE amc_ops.routes(
 worker name NOT NULL, tenant text NOT NULL REFERENCES amc_ops.agencies, client text NOT NULL, brand text NOT NULL,
 campaign text NOT NULL, operator text NOT NULL,
 FOREIGN KEY(tenant,client,brand) REFERENCES public.brands(tenant_id,client_id,id),
 FOREIGN KEY(tenant,brand,campaign) REFERENCES public.campaigns(tenant_id,brand_id,id),
 FOREIGN KEY(tenant,operator) REFERENCES public.memberships(tenant_id,user_id),
 PRIMARY KEY(worker,tenant,client,brand,campaign));
ALTER TABLE public.workforce_runs ADD COLUMN execution_mode text NOT NULL DEFAULT 'legacy' CHECK(execution_mode IN ('legacy','pool')),
 ADD UNIQUE(tenant_id,client_id,brand_id,campaign_id,id);
CREATE TABLE amc_ops.tasks(
 tenant text NOT NULL, client text NOT NULL, brand text NOT NULL, campaign text NOT NULL, run text NOT NULL,
 step int NOT NULL CHECK(step>=0), predecessor int GENERATED ALWAYS AS (nullif(step,0)-1) STORED, skill text NOT NULL,
 done boolean NOT NULL DEFAULT false, PRIMARY KEY(run,step), UNIQUE(run,step,tenant),
 FOREIGN KEY(tenant,client,brand,campaign,run) REFERENCES public.workforce_runs(tenant_id,client_id,brand_id,campaign_id,id),
 FOREIGN KEY(run,predecessor) REFERENCES amc_ops.tasks(run,step));
CREATE TABLE amc_ops.attempts(
 id uuid PRIMARY KEY, run text NOT NULL, step int NOT NULL, worker name NOT NULL, operator text NOT NULL,
 tenant text NOT NULL, month date NOT NULL, deadline timestamptz NOT NULL,
 body jsonb NOT NULL, result jsonb, error text, status text NOT NULL DEFAULT 'offered'
 CHECK(status IN ('offered','sent','reported','closed')), reserved bigint NOT NULL CHECK(reserved>=0),
 input_rate bigint NOT NULL, output_rate bigint NOT NULL, outcome text, started timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(run,step,tenant) REFERENCES amc_ops.tasks(run,step,tenant), FOREIGN KEY(tenant,month) REFERENCES amc_ops.periods,
 UNIQUE(id,tenant,month));
CREATE UNIQUE INDEX one_worker_slot ON amc_ops.attempts(worker) WHERE status<>'closed';
CREATE UNIQUE INDEX one_run_slot ON amc_ops.attempts(run) WHERE status<>'closed';
CREATE TABLE amc_ops.ledger(
 seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, id uuid NOT NULL, tenant text NOT NULL, month date NOT NULL,
 event text NOT NULL CHECK(event IN ('hold','usage','receipt','unsent')), receipt text, actor text NOT NULL, booked timestamptz NOT NULL DEFAULT now(),
 held bigint NOT NULL, spent bigint NOT NULL, absolute_cost bigint,
 FOREIGN KEY(id,tenant,month) REFERENCES amc_ops.attempts(id,tenant,month), UNIQUE(tenant,receipt));
CREATE UNIQUE INDEX one_auto_entry ON amc_ops.ledger(id,event) WHERE receipt IS NULL;
CREATE FUNCTION amc_ops.immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'append-only ledger'; END $$;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON amc_ops.ledger
 FOR EACH STATEMENT EXECUTE FUNCTION amc_ops.immutable();

CREATE FUNCTION amc_ops.route_new() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(4197832742);
 NEW.execution_mode:=CASE WHEN EXISTS (SELECT FROM amc_ops.agencies WHERE tenant=NEW.tenant_id AND enabled) THEN 'pool' ELSE 'legacy' END;
 RETURN NEW;
END $$;
CREATE TRIGGER route_new BEFORE INSERT ON public.workforce_runs FOR EACH ROW EXECUTE FUNCTION amc_ops.route_new();
CREATE FUNCTION amc_ops.build_tasks() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 INSERT INTO amc_ops.tasks(tenant,client,brand,campaign,run,step,skill)
 SELECT NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.id,idx-1,skill
 FROM json_array_elements_text(NEW.plan) WITH ORDINALITY AS p(skill,idx);
 RETURN NULL;
END $$;
CREATE TRIGGER build_tasks AFTER INSERT ON public.workforce_runs FOR EACH ROW WHEN(NEW.execution_mode='pool') EXECUTE FUNCTION amc_ops.build_tasks();
CREATE POLICY pool_cutover ON public.workforce_runs AS RESTRICTIVE FOR SELECT TO amc_runtime USING
 (execution_mode='legacy' OR nullif(current_setting('amc.worker_campaign',true),'') IS NULL OR pg_has_role(session_user,'amc_dispatch','member'));
CREATE POLICY pool_write ON public.workforce_runs AS RESTRICTIVE FOR UPDATE TO amc_runtime USING
 (execution_mode='legacy' OR pg_has_role(session_user,'amc_dispatch','member'));

-- Only the scheduler may enumerate candidates. The worker receives its single assigned envelope.
CREATE FUNCTION amc_ops.candidates() RETURNS TABLE(worker name,tenant text,client text,brand text,campaign text,operator text,run text,step int)
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT d.worker,d.tenant,d.client,d.brand,d.campaign,d.operator,t.run,t.step
 FROM amc_ops.tasks t JOIN amc_ops.routes d USING(tenant,client,brand,campaign)
 JOIN amc_ops.agencies a USING(tenant) JOIN public.workforce_runs r ON r.id=t.run
 WHERE EXISTS (SELECT FROM public.memberships m WHERE (m.tenant_id,m.user_id)=(d.tenant,d.operator) AND m.role='editor')
 AND a.enabled AND r.state='queued' AND r.ready_at<=clock_timestamp() AND NOT t.done
 AND (t.step=0 OR EXISTS(SELECT FROM amc_ops.tasks p WHERE p.run=t.run AND p.step=t.step-1 AND p.done))
 AND NOT EXISTS(SELECT FROM amc_ops.attempts x WHERE x.status<>'closed' AND (x.run=t.run OR x.worker=d.worker))
 AND a.capacity>(SELECT count(*) FROM amc_ops.attempts x WHERE x.tenant=a.tenant AND x.status<>'closed')
 ORDER BY a.served,r.ready_at,t.run,d.worker
$$;
CREATE FUNCTION amc_ops.live(i uuid) RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM amc_ops.attempts x JOIN public.workforce_runs r ON x.run=r.id
 JOIN amc_ops.routes d ON (d.worker,d.tenant,d.client,d.brand,d.campaign,d.operator)=
 (x.worker,r.tenant_id,r.client_id,r.brand_id,r.campaign_id,x.operator)
 JOIN public.memberships m ON (m.tenant_id,m.user_id)=(x.tenant,x.operator) AND m.role='editor'
 WHERE x.id=i AND r.state='running' AND r.lease=x.id::text AND r.ready_at>clock_timestamp())
$$;
CREATE POLICY pool_owner_members ON public.memberships FOR SELECT TO CURRENT_USER USING(true);
CREATE FUNCTION amc_ops.take() RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE j jsonb;
BEGIN
 UPDATE amc_ops.attempts x SET status='sent' WHERE x.worker=session_user AND x.status='offered' AND amc_ops.live(x.id)
 RETURNING jsonb_build_object('id',x.id,'run',x.run,'body',x.body) INTO j;
 RETURN j;
END $$;
CREATE FUNCTION amc_ops.report(i uuid,p jsonb,e text) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF (p IS NULL AND e IS NULL) OR length(p::text)>65536 OR (e IS NOT NULL AND e NOT IN
 ('timeout','incomplete_output','provider_or_format','provider_process','invalid_usage','worker_key_unavailable')) THEN RETURN false; END IF;
 UPDATE amc_ops.attempts SET result=p,error=e,status='reported'
 WHERE id=i AND worker=session_user AND status='sent' AND amc_ops.live(id);
 RETURN FOUND;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA amc_ops FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.take(),amc_ops.report(uuid,jsonb,text) TO amc_pool_worker;
GRANT EXECUTE ON FUNCTION amc_ops.candidates(),amc_ops.live(uuid) TO amc_dispatch;
GRANT SELECT ON ALL TABLES IN SCHEMA amc_ops TO amc_dispatch;
GRANT UPDATE(served) ON amc_ops.agencies TO amc_dispatch;
GRANT UPDATE(ceiling) ON amc_ops.periods TO amc_dispatch;
GRANT UPDATE(done) ON amc_ops.tasks TO amc_dispatch;
GRANT INSERT,UPDATE(status,outcome,result,body) ON amc_ops.attempts TO amc_dispatch;
GRANT INSERT ON amc_ops.ledger TO amc_dispatch;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA amc_ops TO amc_dispatch;

CREATE FUNCTION amc_ops.retire(i uuid) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 UPDATE public.workforce_runs r SET state=CASE WHEN r.attempts>=3 THEN 'failed' ELSE 'queued' END,
 last_error='lease_expired',lease=NULL,ready_at=clock_timestamp(),
 journal=jsonb_set(r.journal::jsonb,'{-1}',(r.journal::jsonb->-1)||jsonb_build_object('outcome','lease_expired','finished_at',clock_timestamp()))::json
 FROM amc_ops.attempts a WHERE a.id=i AND r.id=a.run AND r.lease=i::text AND NOT amc_ops.live(i);
 RETURN (SELECT coalesce(r.last_error,'lease_expired') FROM public.workforce_runs r JOIN amc_ops.attempts a ON a.run=r.id WHERE a.id=i);
END $$;
CREATE TABLE amc_ops.policy_history(
 tenant text NOT NULL REFERENCES amc_ops.agencies, month date NOT NULL, actor text NOT NULL, ceiling bigint NOT NULL,
 capacity int NOT NULL, enabled boolean NOT NULL, recorded timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON amc_ops.policy_history FOR EACH STATEMENT EXECUTE FUNCTION amc_ops.immutable();
CREATE FUNCTION amc_ops.authorize(t text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF coalesce(amc_acl.member_role(t),'') NOT IN ('owner','admin') THEN RAISE insufficient_privilege; END IF;
END $$;
CREATE FUNCTION amc_ops.configure(t text, lim bigint, cap int, en boolean) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE m date:=date_trunc('month',now() AT TIME ZONE 'UTC')::date;
BEGIN
 PERFORM amc_ops.authorize(t);
 PERFORM pg_advisory_xact_lock(4197832742);
 IF en AND EXISTS(SELECT FROM public.workforce_runs WHERE tenant_id=t AND execution_mode='legacy' AND state IN ('queued','running')) THEN
  RAISE EXCEPTION 'Drain active legacy runs first' USING ERRCODE='23514',CONSTRAINT='pool_cutover_pending';
 END IF;
 INSERT INTO amc_ops.agencies VALUES(t,en,cap,0) ON CONFLICT(tenant) DO UPDATE SET capacity=cap,enabled=en;
 INSERT INTO amc_ops.periods VALUES(t,m,lim) ON CONFLICT(tenant,month) DO UPDATE SET ceiling=lim;
 INSERT INTO amc_ops.policy_history VALUES(t,m,current_setting('amc.user_id'),lim,cap,en,clock_timestamp());
END $$;
CREATE FUNCTION amc_ops.bill(t text,i uuid,amount bigint,ref text) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a amc_ops.attempts; prior amc_ops.ledger; h bigint; s bigint;
BEGIN
 PERFORM amc_ops.authorize(t);
 IF amount<0 OR length(trim(ref)) NOT BETWEEN 1 AND 160 THEN RAISE check_violation; END IF;
 PERFORM pg_advisory_xact_lock(4197832742);
 SELECT * INTO a FROM amc_ops.attempts WHERE id=i AND tenant=t AND status='closed';
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT * INTO prior FROM amc_ops.ledger WHERE tenant=t AND receipt=ref;
 IF FOUND THEN RETURN prior.id=i AND prior.absolute_cost=amount; END IF;
 SELECT sum(held),sum(spent) INTO h,s FROM amc_ops.ledger WHERE id=i;
 INSERT INTO amc_ops.ledger(id,tenant,month,event,receipt,actor,held,spent,absolute_cost)
 VALUES(i,t,a.month,'receipt',ref,current_setting('amc.user_id'),-h,amount-s,amount);
 RETURN true;
END $$;
CREATE FUNCTION amc_ops.summary(t text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE m date:=date_trunc('month',now() AT TIME ZONE 'UTC')::date; result jsonb;
BEGIN
 PERFORM amc_ops.authorize(t);
 SELECT jsonb_build_object('month',m,'enabled',a.enabled,'capacity',a.capacity,'ceiling',p.ceiling,
 'held',coalesce((SELECT sum(held) FROM amc_ops.ledger WHERE tenant=t AND month=m),0),
 'spent',coalesce((SELECT sum(spent) FROM amc_ops.ledger WHERE tenant=t AND month=m),0),
 'attempts',(SELECT count(*) FROM amc_ops.attempts WHERE tenant=t AND month=m),
 'active',(SELECT count(*) FROM amc_ops.attempts WHERE tenant=t AND status<>'closed'),
 'outcomes',coalesce((SELECT jsonb_object_agg(k,n) FROM (SELECT coalesce(outcome,status) k,count(*) n
 FROM amc_ops.attempts WHERE tenant=t AND month=m GROUP BY 1) q),'{}'::jsonb)) INTO result
 FROM amc_ops.agencies a LEFT JOIN amc_ops.periods p ON p.tenant=t AND p.month=m WHERE a.tenant=t;
 RETURN coalesce(result,jsonb_build_object('enabled',false,'month',m,'attempts',0,'active',0,'held',0,'spent',0));
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA amc_ops FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.retire(uuid) TO amc_dispatch;
GRANT EXECUTE ON FUNCTION amc_ops.configure(text,bigint,int,boolean),amc_ops.bill(text,uuid,bigint,text),amc_ops.summary(text) TO amc_runtime;

-- Serialise completion with changes to the assigned route and editor membership.
CREATE FUNCTION amc_ops.fence(i uuid) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM m.user_id FROM amc_ops.attempts a JOIN public.memberships m ON (m.tenant_id,m.user_id)=(a.tenant,a.operator)
 WHERE a.id=i AND m.role='editor' FOR SHARE OF m;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM d.worker FROM amc_ops.routes d JOIN amc_ops.tasks t USING(tenant,client,brand,campaign)
 JOIN amc_ops.attempts a ON (a.run,a.step,a.worker,a.operator)=(t.run,t.step,d.worker,d.operator)
 WHERE a.id=i FOR SHARE OF d;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM r.id FROM public.workforce_runs r JOIN amc_ops.attempts a ON r.id=a.run WHERE a.id=i FOR UPDATE OF r;
 RETURN amc_ops.live(i);
END $$;
REVOKE ALL ON FUNCTION amc_ops.fence(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.fence(uuid) TO amc_dispatch;
