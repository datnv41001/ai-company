-- Opt-in specialist concurrency only. Planner and all earlier runs keep their run lease.
SELECT pg_advisory_xact_lock(4197832742);
ALTER TABLE amc_ops.dag_nodes ADD COLUMN ready_at timestamptz NOT NULL DEFAULT '-infinity';
ALTER TABLE amc_ops.attempts ADD COLUMN parallel boolean NOT NULL DEFAULT false,
 ADD COLUMN collected timestamptz, ADD COLUMN reported timestamptz;
DROP INDEX amc_ops.one_run_slot;
CREATE UNIQUE INDEX one_run_slot ON amc_ops.attempts(run) WHERE status<>'closed' AND NOT parallel;
CREATE UNIQUE INDEX one_node_lease ON amc_ops.attempts(run,plan_revision,node_id) WHERE status<>'closed' AND parallel;

CREATE FUNCTION amc_ops.parallel_node(r text,s int) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM public.workforce_runs w JOIN amc_ops.dag_plans g ON g.run=w.id
 WHERE w.id=r AND s>0 AND g.template='dynamic-v1' AND g.contract IS NOT NULL AND w.knowledge->>'max_parallel_nodes'='2')
$$;
CREATE FUNCTION amc_ops.guard_node_lease() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='INSERT' THEN
  PERFORM pg_advisory_xact_lock(4197832742);
  NEW.parallel:=amc_ops.parallel_node(NEW.run,NEW.step);
  IF EXISTS(SELECT FROM amc_ops.attempts WHERE run=NEW.run AND status<>'closed' AND parallel<>NEW.parallel)
    OR (NEW.parallel AND (SELECT count(*) FROM amc_ops.attempts WHERE run=NEW.run AND status<>'closed')>=2)
  THEN RAISE EXCEPTION 'Run lease capacity reached' USING ERRCODE='23514'; END IF;
 ELSIF NEW.status='sent' AND OLD.status='offered' THEN NEW.collected:=clock_timestamp();
 ELSIF NEW.status='reported' AND OLD.status='sent' THEN NEW.reported:=clock_timestamp();
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER guard_node_lease BEFORE INSERT OR UPDATE OF status ON amc_ops.attempts FOR EACH ROW EXECUTE FUNCTION amc_ops.guard_node_lease();
REVOKE ALL ON FUNCTION amc_ops.parallel_node(text,int),amc_ops.guard_node_lease() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.parallel_node(text,int) TO amc_dispatch;
GRANT UPDATE(ready_at) ON amc_ops.dag_nodes TO amc_dispatch;

CREATE OR REPLACE FUNCTION amc_ops.live(i uuid) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT FROM amc_ops.attempts x JOIN public.workforce_runs r ON x.run=r.id
 JOIN amc_ops.routes d ON (d.worker,d.tenant,d.client,d.brand,d.campaign,d.operator)=
 (x.worker,r.tenant_id,r.client_id,r.brand_id,r.campaign_id,x.operator)
 JOIN public.memberships m ON (m.tenant_id,m.user_id)=(x.tenant,x.operator) AND m.role='editor'
 WHERE x.id=i AND CASE WHEN x.parallel THEN r.state='queued' AND x.status<>'closed' AND x.deadline>clock_timestamp()
 AND EXISTS(SELECT FROM amc_ops.dag_nodes n WHERE (n.run,n.revision,n.node_id)=(x.run,x.plan_revision,x.node_id) AND n.checkpoint IS NULL)
 ELSE r.state='running' AND r.lease=x.id::text AND r.ready_at>clock_timestamp() END)
$$;
-- A dead lease may have lost its operator grant; retire under the same narrow
-- authority as v9. Sent usage stays held for a receipt in the original period.
ALTER FUNCTION amc_ops.retire(uuid) RENAME TO retire_run_lease;
REVOKE EXECUTE ON FUNCTION amc_ops.retire_run_lease(uuid) FROM amc_dispatch;
CREATE FUNCTION amc_ops.retire(i uuid) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a amc_ops.attempts; r public.workforce_runs; reason text;
BEGIN
 SELECT * INTO STRICT a FROM amc_ops.attempts WHERE id=i FOR UPDATE;
 IF NOT a.parallel THEN RETURN amc_ops.retire_run_lease(i); END IF;
 IF a.status='closed' OR amc_ops.live(i) THEN RAISE check_violation; END IF;
 SELECT * INTO STRICT r FROM public.workforce_runs WHERE id=a.run FOR UPDATE;
 reason:=CASE WHEN r.last_error='recipient_revoked' THEN 'recipient_revoked' WHEN r.state='failed' THEN 'sibling_failed' ELSE 'lease_expired' END;
 UPDATE public.workforce_runs SET reserved_microusd=reserved_microusd-CASE WHEN a.status='offered' THEN a.reserved ELSE 0 END,
  state=CASE WHEN a.ordinal>=3 AND a.status<>'offered' AND state='queued' THEN 'failed' ELSE state END,
  last_error=CASE WHEN a.ordinal>=3 AND a.status<>'offered' AND state='queued' THEN reason ELSE last_error END,
  journal=(SELECT jsonb_agg(CASE WHEN j->>'attempt_id'=i::text THEN j||jsonb_build_object('outcome',reason,'finished_at',clock_timestamp()) ELSE j END ORDER BY idx)
    FROM jsonb_array_elements(r.journal::jsonb) WITH ORDINALITY x(j,idx))::json WHERE id=a.run;
 UPDATE amc_ops.dag_nodes SET ready_at=clock_timestamp() + CASE WHEN a.status='offered' THEN interval '0' ELSE (2^a.ordinal)*interval '1 second' END
 WHERE run=a.run AND revision=a.plan_revision AND node_id=a.node_id;
 RETURN reason;
END $$;
REVOKE ALL ON FUNCTION amc_ops.retire(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.retire(uuid) TO amc_dispatch;

CREATE OR REPLACE FUNCTION amc_ops.candidates() RETURNS TABLE(worker name,tenant text,client text,brand text,campaign text,operator text,run text,step int)
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT d.worker,d.tenant,d.client,d.brand,d.campaign,d.operator,t.run,t.step
 FROM amc_ops.tasks t JOIN amc_ops.routes d USING(tenant,client,brand,campaign)
 JOIN amc_ops.agencies a USING(tenant) JOIN public.workforce_runs r ON r.id=t.run
 JOIN amc_ops.readiness w ON w.worker=d.worker AND w.polled>clock_timestamp()-interval '10 seconds'
 LEFT JOIN amc_ops.dag_nodes n ON (n.run,n.slot)=(t.run,t.step)
 CROSS JOIN LATERAL (SELECT amc_ops.parallel_node(t.run,t.step) multi) mode
 WHERE EXISTS(SELECT FROM public.memberships m WHERE (m.tenant_id,m.user_id)=(d.tenant,d.operator) AND m.role='editor')
 AND a.enabled AND r.state='queued' AND NOT t.done
 AND CASE WHEN mode.multi THEN n.ready_at<=clock_timestamp() ELSE r.ready_at<=clock_timestamp() END
 AND CASE WHEN n.node_id IS NOT NULL THEN n.checkpoint IS NULL AND amc_ops.dag_ready(n.run,n.node_id)
 ELSE t.step=0 OR EXISTS(SELECT FROM amc_ops.tasks p WHERE p.run=t.run AND p.step=t.step-1 AND p.done) END
 AND NOT EXISTS(SELECT FROM amc_ops.attempts x WHERE x.status<>'closed'
 AND (x.worker=d.worker OR (x.run=t.run AND (NOT mode.multi OR x.step=t.step OR NOT x.parallel))))
 AND (NOT mode.multi OR 2>(SELECT count(*) FROM amc_ops.attempts x WHERE x.run=t.run AND x.status<>'closed'))
 AND a.capacity>(SELECT count(*) FROM amc_ops.attempts x WHERE x.tenant=a.tenant AND x.status<>'closed')
 ORDER BY a.served,r.ready_at,t.run,(SELECT count(*) FROM amc_ops.attempts x WHERE x.run=n.run AND x.node_id=n.node_id),t.step,d.worker
$$;

-- Show retry deadlines and active attempts from node state to the same agency readers.
ALTER FUNCTION amc_ops.dag_report(text,text) RENAME TO dag_report_v12;
CREATE FUNCTION amc_ops.dag_report(t text,r text) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE base jsonb; nodes jsonb;
BEGIN
 base:=amc_ops.dag_report_v12(t,r);
 IF base IS NULL OR NOT amc_ops.parallel_node(r,1) THEN RETURN base; END IF;
 SELECT jsonb_agg(j||jsonb_build_object('status',CASE WHEN j->>'status'='ready' AND n.ready_at>clock_timestamp()
 THEN 'retry_wait' ELSE j->>'status' END,'active_ordinal',a.ordinal,'ready_at',nullif(n.ready_at,'-infinity')) ORDER BY n.position) INTO nodes
 FROM jsonb_array_elements(base->'nodes') j JOIN amc_ops.dag_nodes n ON n.run=r AND n.node_id=j->>'node_id'
 LEFT JOIN amc_ops.attempts a ON (a.run,a.node_id)=(n.run,n.node_id) AND a.status<>'closed';
 RETURN base||jsonb_build_object('nodes',nodes,'max_parallel_nodes',2);
END $$;
REVOKE ALL ON FUNCTION amc_ops.dag_report(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.dag_report(text,text) TO amc_runtime;
