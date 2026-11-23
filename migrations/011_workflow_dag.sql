-- New runs opt in at enqueue. A v10 lease and its journal have no graph identity.
SELECT pg_advisory_xact_lock(4197832742);
CREATE TABLE amc_ops.dag_plans (
 tenant text NOT NULL, client text NOT NULL, brand text NOT NULL, campaign text NOT NULL,
 run text PRIMARY KEY, revision int NOT NULL CHECK(revision=1), template text NOT NULL CHECK(template='diamond-v1'),
 deliverable text UNIQUE,
 UNIQUE(tenant,client,brand,campaign,run,revision),
 FOREIGN KEY(tenant,client,brand,campaign,run) REFERENCES public.workforce_runs(tenant_id,client_id,brand_id,campaign_id,id),
 FOREIGN KEY(tenant,campaign,deliverable) REFERENCES public.deliverables(tenant_id,campaign_id,id)
);
CREATE TABLE amc_ops.dag_nodes (
 tenant text NOT NULL, client text NOT NULL, brand text NOT NULL, campaign text NOT NULL,
 run text NOT NULL, revision int NOT NULL, node_id text NOT NULL, position int NOT NULL, slot int, checkpoint jsonb,
 PRIMARY KEY(tenant,client,brand,campaign,run,revision,node_id), UNIQUE(run,node_id), UNIQUE(run,position),
 UNIQUE(run,slot,revision,node_id),
 FOREIGN KEY(tenant,client,brand,campaign,run,revision) REFERENCES amc_ops.dag_plans(tenant,client,brand,campaign,run,revision),
 FOREIGN KEY(run,slot) REFERENCES amc_ops.tasks(run,step),
 CHECK((node_id='join' AND slot IS NULL) OR (node_id<>'join' AND slot IS NOT NULL AND slot=position))
);
CREATE TABLE amc_ops.dag_edges (
 tenant text NOT NULL, client text NOT NULL, brand text NOT NULL, campaign text NOT NULL,
 run text NOT NULL, revision int NOT NULL, child text NOT NULL, parent text NOT NULL,
 PRIMARY KEY(run,revision,child,parent), CHECK(child<>parent),
 FOREIGN KEY(tenant,client,brand,campaign,run,revision,child) REFERENCES amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id),
 FOREIGN KEY(tenant,client,brand,campaign,run,revision,parent) REFERENCES amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id)
);
ALTER TABLE amc_ops.attempts ADD COLUMN node_id text, ADD COLUMN plan_revision int,
 ADD CHECK ((node_id IS NULL)=(plan_revision IS NULL)),
 ADD FOREIGN KEY(run,step,plan_revision,node_id) REFERENCES amc_ops.dag_nodes(run,slot,revision,node_id);
CREATE INDEX dag_attempt_history ON amc_ops.attempts(run,node_id,started) WHERE node_id IS NOT NULL;
CREATE FUNCTION amc_ops.diamond() RETURNS TABLE(pos int, id text, parents text[])
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 VALUES (0,'director','{}'::text[]),(1,'research',ARRAY['director']),(2,'strategy',ARRAY['research']),
 (3,'content',ARRAY['strategy']),(4,'seo',ARRAY['strategy']),(5,'join',ARRAY['content','seo'])
$$;
-- Compare complete node and edge sets to a trusted acyclic template. This also
-- rejects missing outputs, disconnected nodes, cycles, and sibling input leakage.
CREATE FUNCTION amc_ops.valid_diamond(r text) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 WITH expected AS (SELECT * FROM amc_ops.diamond()),
 actual AS (SELECT position pos,node_id id FROM amc_ops.dag_nodes WHERE run=r),
 edges AS (SELECT child,parent FROM amc_ops.dag_edges WHERE run=r),
 required AS (SELECT id child,unnest(parents) parent FROM expected)
 SELECT NOT EXISTS((SELECT pos,id FROM expected EXCEPT TABLE actual) UNION ALL (TABLE actual EXCEPT SELECT pos,id FROM expected))
 AND NOT EXISTS((TABLE required EXCEPT TABLE edges) UNION ALL (TABLE edges EXCEPT TABLE required))
$$;
CREATE FUNCTION amc_ops.freeze_diamond() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.execution_mode<>'pool' THEN RAISE EXCEPTION 'Enable pool first' USING ERRCODE='23514',CONSTRAINT='dag_requires_pool'; END IF;
 IF NEW.knowledge->>'workflow_revision' IS DISTINCT FROM '1' THEN RAISE check_violation; END IF;
 IF NEW.plan::jsonb<>(SELECT jsonb_agg(id ORDER BY pos) FROM amc_ops.diamond() WHERE id<>'join') THEN RAISE check_violation; END IF;
 INSERT INTO amc_ops.dag_plans(tenant,client,brand,campaign,run,revision,template)
 VALUES(NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.id,1,'diamond-v1');
 INSERT INTO amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id,position,slot)
 SELECT NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.id,1,id,pos,CASE WHEN id<>'join' THEN pos END FROM amc_ops.diamond();
 INSERT INTO amc_ops.dag_edges SELECT NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.id,1,id,unnest(parents)
 FROM amc_ops.diamond();
 IF NOT amc_ops.valid_diamond(NEW.id) THEN RAISE check_violation; END IF;
 RETURN NULL;
END $$;
-- Runs after build_tasks; the original task slots remain accounting compatibility keys.
CREATE TRIGGER freeze_diamond AFTER INSERT ON public.workforce_runs FOR EACH ROW WHEN(NEW.knowledge->>'workflow'='diamond-v1')
 EXECUTE FUNCTION amc_ops.freeze_diamond();

CREATE FUNCTION amc_ops.dag_ready(r text,n text) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT NOT EXISTS (SELECT FROM amc_ops.dag_edges e JOIN amc_ops.dag_nodes p ON (p.run,p.node_id)=(e.run,e.parent)
 WHERE e.run=r AND e.child=n AND p.checkpoint IS NULL)
$$;
CREATE FUNCTION amc_ops.dag_report(t text,r text) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE g amc_ops.dag_plans; result jsonb;
BEGIN
 IF coalesce(amc_acl.member_role(t),'') NOT IN ('owner','admin','editor','viewer') THEN RETURN NULL; END IF;
 SELECT * INTO g FROM amc_ops.dag_plans WHERE tenant=t AND run=r;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT jsonb_build_object('template',g.template,'revision',g.revision,'nodes',jsonb_agg(jsonb_build_object(
 'node_id',n.node_id,'dependencies',deps.all_ids,'missing',deps.missing,'attempts',x.calls,
 'held',cost.held,'spent',cost.spent,'error',x.last_error,
 'status',CASE WHEN n.checkpoint IS NOT NULL THEN 'succeeded' WHEN x.active THEN 'running'
 WHEN w.state='failed' AND x.calls>=3 THEN 'failed' WHEN w.state='failed' THEN 'blocked'
 WHEN jsonb_array_length(deps.missing)>0 THEN 'waiting' WHEN x.calls>0 AND w.ready_at>clock_timestamp() THEN 'retry_wait' ELSE 'ready' END
 ) ORDER BY n.position)) INTO result
 FROM amc_ops.dag_nodes n JOIN public.workforce_runs w ON w.id=n.run
 CROSS JOIN LATERAL (SELECT coalesce(jsonb_agg(e.parent ORDER BY e.parent),'[]') all_ids,
 coalesce(jsonb_agg(e.parent ORDER BY e.parent) FILTER(WHERE p.checkpoint IS NULL),'[]') missing
 FROM amc_ops.dag_edges e JOIN amc_ops.dag_nodes p ON (p.run,p.node_id)=(e.run,e.parent) WHERE e.run=r AND e.child=n.node_id) deps
 CROSS JOIN LATERAL (SELECT count(*) FILTER(WHERE NOT EXISTS(SELECT FROM amc_ops.ledger l WHERE l.id=a.id AND l.event='unsent')) calls,
 bool_or(a.status<>'closed') active,(array_agg(a.outcome ORDER BY a.started DESC) FILTER(WHERE a.status='closed'))[1] last_error
 FROM amc_ops.attempts a WHERE a.run=r AND a.node_id=n.node_id) x
 CROSS JOIN LATERAL (SELECT coalesce(sum(l.held),0) held,coalesce(sum(l.spent),0) spent FROM amc_ops.attempts a
 JOIN amc_ops.ledger l USING(id) WHERE a.run=r AND a.node_id=n.node_id) cost
 WHERE n.run=r;
 RETURN result;
END $$;
GRANT SELECT ON amc_ops.dag_nodes,amc_ops.dag_plans,amc_ops.dag_edges TO amc_dispatch;
GRANT UPDATE(checkpoint) ON amc_ops.dag_nodes TO amc_dispatch;
GRANT UPDATE(deliverable) ON amc_ops.dag_plans TO amc_dispatch;
REVOKE ALL ON FUNCTION amc_ops.diamond(),amc_ops.valid_diamond(text),amc_ops.freeze_diamond(),amc_ops.dag_ready(text,text),amc_ops.dag_report(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.dag_ready(text,text) TO amc_dispatch;
GRANT EXECUTE ON FUNCTION amc_ops.dag_report(text,text) TO amc_runtime;
CREATE OR REPLACE FUNCTION amc_ops.candidates() RETURNS TABLE(worker name,tenant text,client text,brand text,campaign text,operator text,run text,step int)
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT d.worker,d.tenant,d.client,d.brand,d.campaign,d.operator,t.run,t.step
 FROM amc_ops.tasks t JOIN amc_ops.routes d USING(tenant,client,brand,campaign)
 JOIN amc_ops.agencies a USING(tenant) JOIN public.workforce_runs r ON r.id=t.run
 JOIN amc_ops.readiness w ON w.worker=d.worker AND w.polled>clock_timestamp()-interval '10 seconds'
 LEFT JOIN amc_ops.dag_nodes n ON (n.run,n.slot)=(t.run,t.step)
 WHERE EXISTS (SELECT FROM public.memberships m WHERE (m.tenant_id,m.user_id)=(d.tenant,d.operator) AND m.role='editor')
 AND a.enabled AND r.state='queued' AND r.ready_at<=clock_timestamp() AND NOT t.done
 AND CASE WHEN n.node_id IS NOT NULL THEN n.checkpoint IS NULL AND amc_ops.dag_ready(n.run,n.node_id)
 ELSE (t.step=0 OR EXISTS(SELECT FROM amc_ops.tasks p WHERE p.run=t.run AND p.step=t.step-1 AND p.done)) END
 AND NOT EXISTS(SELECT FROM amc_ops.attempts x WHERE x.status<>'closed' AND (x.run=t.run OR x.worker=d.worker))
 AND a.capacity>(SELECT count(*) FROM amc_ops.attempts x WHERE x.tenant=a.tenant AND x.status<>'closed')
 ORDER BY a.served,r.ready_at,t.run, (SELECT count(*) FROM amc_ops.attempts x WHERE x.run=n.run AND x.node_id=n.node_id),t.step,d.worker
$$;

-- Reject missing or substituted graph identities even for an erroneous scheduler insert.
CREATE FUNCTION amc_ops.bind_attempt_node() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE n amc_ops.dag_nodes;
BEGIN
 SELECT * INTO n FROM amc_ops.dag_nodes WHERE run=NEW.run AND slot=NEW.step;
 IF NEW.node_id IS DISTINCT FROM n.node_id OR NEW.plan_revision IS DISTINCT FROM n.revision THEN
  RAISE EXCEPTION 'Attempt must match frozen workflow node' USING ERRCODE='23514', CONSTRAINT='attempt_node_identity';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_ops.bind_attempt_node() FROM PUBLIC;
CREATE TRIGGER bind_attempt_node BEFORE INSERT ON amc_ops.attempts FOR EACH ROW EXECUTE FUNCTION amc_ops.bind_attempt_node();
