-- A process advertises only its own login/backend. Database time is authoritative.
CREATE TABLE amc_ops.dispatcher_inventory (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), expected name[] NOT NULL CHECK(cardinality(expected)>0),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE amc_ops.pool_heartbeats (
 login name NOT NULL, pid integer NOT NULL, kind text NOT NULL, observed_at timestamptz NOT NULL,
 capabilities jsonb NOT NULL, PRIMARY KEY(login,pid)
);
CREATE FUNCTION amc_ops.heartbeat(kind text, caps jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT ((kind='dispatcher' AND pg_has_role(session_user,'amc_dispatch','member'))
      OR (kind='worker' AND pg_has_role(session_user,'amc_pool_worker','member')))
 OR jsonb_typeof(caps) IS DISTINCT FROM 'object' OR octet_length(caps::text)>10000
 THEN RAISE insufficient_privilege; END IF;
 DELETE FROM amc_ops.pool_heartbeats h WHERE h.login=session_user AND h.observed_at < now()-interval '1 hour';
 INSERT INTO amc_ops.pool_heartbeats VALUES(session_user,pg_backend_pid(),kind,clock_timestamp(),caps)
 ON CONFLICT(login,pid) DO UPDATE SET observed_at=excluded.observed_at,kind=excluded.kind,capabilities=excluded.capabilities;
END $$;
REVOKE ALL ON FUNCTION amc_ops.heartbeat(text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.heartbeat(text,jsonb) TO amc_dispatch,amc_pool_worker;
GRANT SELECT ON amc_ops.pool_heartbeats TO amc_dispatch;

-- One set of admission predicates feeds both the offer query and the scoped explanation.
CREATE FUNCTION amc_ops.route_state(only_run text) RETURNS TABLE (
 worker name,tenant text,client text,brand text,campaign text,operator text,run text,step int,
 operator_ok boolean, enabled boolean, queued boolean, due boolean, dependencies_ok boolean,
 polling boolean, worker_free boolean, run_free boolean, capacity_free boolean,
 served bigint, ready_at timestamptz, tries bigint
) LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT d.worker,t.tenant,t.client,t.brand,t.campaign,d.operator,t.run,t.step,
 EXISTS(SELECT FROM public.memberships m WHERE (m.tenant_id,m.user_id)=(d.tenant,d.operator) AND m.role='editor'),
 a.enabled,r.state='queued' AND NOT t.done,
 CASE WHEN mode.multi THEN n.ready_at ELSE r.ready_at END <= statement_timestamp(),
 CASE WHEN n.node_id IS NOT NULL THEN n.checkpoint IS NULL AND amc_ops.dag_ready(n.run,n.node_id)
      ELSE t.step=0 OR EXISTS(SELECT FROM amc_ops.tasks p WHERE p.run=t.run AND p.step=t.step-1 AND p.done) END,
 coalesce(w.polled>statement_timestamp()-interval '10 seconds',false),
 NOT EXISTS(SELECT FROM amc_ops.attempts x WHERE x.status<>'closed' AND x.worker=d.worker),
 NOT EXISTS(SELECT FROM amc_ops.attempts x WHERE x.status<>'closed' AND x.run=t.run AND (NOT mode.multi OR x.step=t.step OR NOT x.parallel))
 AND (NOT mode.multi OR 2>(SELECT count(*) FROM amc_ops.attempts x WHERE x.run=t.run AND x.status<>'closed')),
 a.capacity>(SELECT count(*) FROM amc_ops.attempts x WHERE x.tenant=t.tenant AND x.status<>'closed'),
 a.served,r.ready_at,(SELECT count(*) FROM amc_ops.attempts x WHERE x.run=n.run AND x.node_id=n.node_id)
 FROM amc_ops.tasks t JOIN public.workforce_runs r ON r.id=t.run JOIN amc_ops.agencies a USING(tenant)
 LEFT JOIN amc_ops.routes d USING(tenant,client,brand,campaign)
 LEFT JOIN amc_ops.readiness w ON w.worker=d.worker
 LEFT JOIN amc_ops.dag_nodes n ON (n.run,n.slot)=(t.run,t.step)
 CROSS JOIN LATERAL (SELECT amc_ops.parallel_node(t.run,t.step) multi) mode
 WHERE only_run IS NULL OR t.run=only_run
$$;
REVOKE ALL ON FUNCTION amc_ops.route_state(text) FROM PUBLIC;

CREATE FUNCTION amc_ops.eligible_routes(only_run text) RETURNS TABLE(worker name,tenant text,client text,brand text,campaign text,operator text,run text,step int)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT worker,tenant,client,brand,campaign,operator,run,step FROM amc_ops.route_state(only_run)
 WHERE operator_ok AND enabled AND queued AND due AND dependencies_ok AND polling AND worker_free AND run_free AND capacity_free
 ORDER BY served,ready_at,run,tries,step,worker
$$;

REVOKE ALL ON FUNCTION amc_ops.eligible_routes(text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION amc_ops.candidates() RETURNS TABLE(worker name,tenant text,client text,brand text,campaign text,operator text,run text,step int)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT * FROM amc_ops.eligible_routes(NULL)
$$;

-- Shared with the dispatcher's final reservation check under the scheduler lock.
CREATE FUNCTION amc_ops.available_budget(t text) RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT p.ceiling-coalesce((SELECT sum(l.held+l.spent) FROM amc_ops.ledger l WHERE (l.tenant,l.month)=(p.tenant,p.month)),0)
 FROM amc_ops.periods p WHERE p.tenant=t AND p.month=date_trunc('month',now() AT TIME ZONE 'UTC')::date
$$;
REVOKE ALL ON FUNCTION amc_ops.available_budget(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.available_budget(text) TO amc_dispatch;

-- All evidence comes from one statement snapshot. No scheduler lock, lease, receipt or retry update.
CREATE FUNCTION amc_ops.wait_snapshot(t text,rid text) RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 IF coalesce(amc_acl.member_role(t),'') NOT IN ('owner','admin') THEN RETURN NULL; END IF;
 WITH run AS (SELECT * FROM public.workforce_runs WHERE id=rid AND tenant_id=t AND execution_mode='pool'),
 routes AS MATERIALIZED (SELECT a.* FROM run CROSS JOIN LATERAL amc_ops.route_state(run.id) a),
 eligible AS MATERIALIZED (SELECT c.step FROM run CROSS JOIN LATERAL amc_ops.eligible_routes(run.id) c),
 roster AS (SELECT unnest(expected) AS login FROM amc_ops.dispatcher_inventory),
 sessions AS (
    SELECT a.usename,a.pid FROM pg_stat_activity a WHERE a.datname=current_database()
      AND EXISTS(SELECT FROM pg_auth_members m WHERE m.member=a.usesysid AND m.roleid='amc_dispatch'::regrole)
 ), replicas AS (
    SELECT CASE WHEN r.login IS NOT NULL THEN h.capabilities END AS capabilities
    FROM roster r FULL JOIN sessions s ON s.usename=r.login
    LEFT JOIN amc_ops.pool_heartbeats h ON h.login=s.usename AND h.pid=s.pid AND h.kind='dispatcher'
        AND h.observed_at>statement_timestamp()-interval '15 seconds'
 ), facts AS (
 SELECT n.*, p.template, EXISTS (SELECT FROM eligible WHERE eligible.step=n.slot) candidate, amc_ops.parallel_node(n.run,n.slot) multi,
 (SELECT jsonb_agg(to_jsonb(s)-ARRAY['tenant','client','brand','campaign','operator','worker','ready_at','served','tries'] ||
    jsonb_build_object('worker_known',EXISTS(SELECT FROM amc_ops.pool_heartbeats h JOIN pg_stat_activity a ON a.pid=h.pid AND a.usename=h.login
           WHERE h.login=s.worker AND h.kind='worker' AND h.observed_at>statement_timestamp()-interval '15 seconds')))
  FROM routes s WHERE s.step=n.slot) routes,
 (SELECT jsonb_agg(jsonb_build_object('skill',parent.skill_type,'id',parent.node_id,'checkpoint',parent.checkpoint) ORDER BY parent.position)
    FROM amc_ops.dag_edges e JOIN amc_ops.dag_nodes parent ON (parent.run,parent.revision,parent.node_id)=(e.run,e.revision,e.parent)
    WHERE (e.run,e.revision,e.child)=(n.run,n.revision,n.node_id)) parents,
 (SELECT jsonb_agg(jsonb_build_object('status',a.status,'live',amc_ops.live(a.id))) FROM amc_ops.attempts a
    WHERE (a.run,a.plan_revision,a.node_id)=(n.run,n.revision,n.node_id) AND a.status<>'closed') active,
 (SELECT count(*) FROM amc_ops.attempts a WHERE a.run=n.run AND a.node_id=n.node_id AND a.status='closed'
   AND NOT EXISTS (SELECT FROM amc_ops.ledger l WHERE l.id=a.id AND l.event='unsent')) attempts,
 (SELECT a.outcome FROM amc_ops.attempts a WHERE a.run=n.run AND a.node_id=n.node_id AND a.status='closed'
   AND NOT EXISTS (SELECT FROM amc_ops.ledger l WHERE l.id=a.id AND l.event='unsent') ORDER BY a.started DESC LIMIT 1) last_error,
 (SELECT coalesce(sum(l.held+l.spent),0) FROM amc_ops.attempts a JOIN amc_ops.ledger l USING(id)
    WHERE a.run=n.run AND a.node_id=n.node_id) exposure
 FROM run JOIN amc_ops.dag_plans p ON p.run=run.id
 JOIN amc_ops.dag_nodes n ON (n.run,n.revision)=(p.run,p.revision)
 )
 SELECT jsonb_build_object('observed_at',statement_timestamp(),'state',run.state,'knowledge',run.knowledge,'plan',run.plan,
  'checkpoints',run.checkpoints,'journal',run.journal,'run_ready_at',run.ready_at,'run_budget',run.budget_microusd-run.reserved_microusd,
  'agency_budget',amc_ops.available_budget(t),'dispatchers',(SELECT jsonb_agg(capabilities) FROM replicas),
  'nodes',(SELECT jsonb_agg(to_jsonb(f) ORDER BY position) FROM facts f))
 INTO result FROM run WHERE EXISTS(SELECT FROM facts);
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION amc_ops.wait_snapshot(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.wait_snapshot(text,text) TO amc_runtime;
