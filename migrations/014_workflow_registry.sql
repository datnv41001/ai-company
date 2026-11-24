-- Registry publication uses the migration identity. API and worker logins have no definition writes.
SELECT pg_advisory_xact_lock(4197832742);
CREATE TABLE amc_ops.registry_releases(
 workflow text PRIMARY KEY, digest text NOT NULL UNIQUE CHECK(length(digest)=64), manifest jsonb NOT NULL,
 published_by name NOT NULL DEFAULT session_user, published_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE amc_ops.registry_versions(kind text, id text, version int, definition jsonb NOT NULL, PRIMARY KEY(kind,id,version));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON amc_ops.registry_releases
 FOR EACH STATEMENT EXECUTE FUNCTION amc_ops.immutable();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON amc_ops.registry_versions
 FOR EACH STATEMENT EXECUTE FUNCTION amc_ops.immutable();
GRANT SELECT ON amc_ops.registry_releases TO amc_runtime;
CREATE TABLE amc_ops.registry_grants(
 tenant text NOT NULL, client text NOT NULL, brand text NOT NULL, campaign text NOT NULL, workflow text REFERENCES amc_ops.registry_releases,
 skill text, mode text NOT NULL CHECK(mode IN ('activate','disable','revoke')),
 PRIMARY KEY(tenant,campaign,workflow,skill), FOREIGN KEY(tenant,brand,campaign) REFERENCES public.campaigns(tenant_id,brand_id,id),
 FOREIGN KEY(tenant,client,brand) REFERENCES public.brands(tenant_id,client_id,id));
ALTER TABLE amc_ops.registry_grants ENABLE ROW LEVEL SECURITY;
CREATE POLICY registry_reader ON amc_ops.registry_grants FOR SELECT TO amc_runtime
 USING(amc_acl.member_role(tenant) IN ('owner','admin','editor','viewer') AND EXISTS
 (SELECT FROM public.campaigns c WHERE (c.tenant_id,c.id)=(tenant,campaign)));
GRANT SELECT ON amc_ops.registry_grants TO amc_runtime;
CREATE TABLE amc_ops.registry_history(tenant text, campaign text, workflow text, skills text[], mode text, actor text, recorded_at timestamptz DEFAULT clock_timestamp());
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON amc_ops.registry_history FOR EACH STATEMENT EXECUTE FUNCTION amc_ops.immutable();

CREATE FUNCTION amc_ops.change_registry(t text,c text,w text,m text,s text[]) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE manifest jsonb;
BEGIN
 PERFORM amc_ops.authorize(t);
 PERFORM pg_advisory_xact_lock(4197832742);
 SELECT r.manifest INTO manifest FROM amc_ops.registry_releases r WHERE r.workflow=w;
 IF manifest IS NULL OR m NOT IN ('activate','disable','revoke') OR cardinality(s) NOT BETWEEN 1 AND 5
 OR NOT EXISTS(SELECT FROM public.campaigns WHERE tenant_id=t AND id=c)
 OR EXISTS(SELECT FROM unnest(s) k WHERE k IS NULL OR NOT ((manifest->'contracts') ? k))
 THEN RETURN false; END IF;
 INSERT INTO amc_ops.registry_grants(tenant,client,brand,campaign,workflow,skill,mode)
 SELECT t,b.client_id,b.id,c,w,k,m FROM public.campaigns ca JOIN public.brands b ON (b.tenant_id,b.id)=(ca.tenant_id,ca.brand_id)
 CROSS JOIN (SELECT DISTINCT unnest(s) k) skills WHERE (ca.tenant_id,ca.id)=(t,c) ORDER BY k
 ON CONFLICT(tenant,campaign,workflow,skill) DO UPDATE SET mode=excluded.mode;
 INSERT INTO amc_ops.registry_history(tenant,campaign,workflow,skills,mode,actor) VALUES(t,c,w,s,m,current_setting('amc.user_id'));
 IF m='revoke' THEN
  -- Clearing the run lease fences serial workers. Terminal state fences parallel workers through live().
  UPDATE public.workforce_runs r SET state='failed', last_error='registry_revoked',lease=NULL
  FROM amc_ops.dag_plans p WHERE r.id=p.run AND r.tenant_id=t AND r.campaign_id=c
  AND r.knowledge->'registry'->>'workflow'=w AND r.state IN ('queued','running')
  AND (r.knowledge->'registry'->'skills')::jsonb ?| s
  AND (p.contract IS NULL OR 'director'=ANY(s) OR EXISTS(
      SELECT FROM jsonb_array_elements(p.contract->'nodes') n WHERE n->>'skill_type'=ANY(s)));
 END IF;
 RETURN true;
END $$;

CREATE FUNCTION amc_ops.registry_pin(t text,c text,w text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(4197832742);
 IF coalesce(amc_acl.member_role(t),'') NOT IN ('owner','admin','editor') THEN RETURN NULL; END IF;
 SELECT jsonb_build_object('workflow',w,'workflow_id',r.manifest->'workflow_id','workflow_version',r.manifest->'workflow_version',
   'manifest_digest',r.digest,'skills',jsonb_agg(g.skill ORDER BY g.skill),'contracts',jsonb_object_agg(g.skill,r.manifest->'contracts'->g.skill))
 INTO result FROM amc_ops.registry_releases r JOIN amc_ops.registry_grants g USING(workflow)
 WHERE g.tenant=t AND g.campaign=c AND g.workflow=w AND g.mode='activate' GROUP BY r.workflow
 HAVING jsonb_agg(g.skill) @> (r.manifest->'required');
 RETURN result;
END $$;

CREATE FUNCTION amc_ops.check_registry_binding() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE binding jsonb := (NEW.knowledge->'registry')::jsonb;
BEGIN
 IF binding IS DISTINCT FROM amc_ops.registry_pin(NEW.tenant_id,NEW.campaign_id,binding->>'workflow')
 OR NEW.knowledge->>'workflow' IS DISTINCT FROM 'dynamic-v1'
 OR (NEW.knowledge->'required_outputs')::jsonb IS DISTINCT FROM '["content","seo"]'::jsonb
 THEN RAISE check_violation; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER verify_registry BEFORE INSERT ON public.workforce_runs FOR EACH ROW
 WHEN (NEW.knowledge::jsonb ? 'registry') EXECUTE FUNCTION amc_ops.check_registry_binding();

CREATE FUNCTION amc_ops.registry_nodes(r text) RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT jsonb_agg(jsonb_build_object('node_id',n.node_id,'exposure',tot.held+tot.spent,'held',tot.held,'spent',tot.spent,
 'overage',greatest(0,tot.held+tot.spent-(b.contract->>'node_cap')::bigint),'attempt_ids',ids.attempts,'attempts',ids.trace)
 || b.contract ORDER BY n.position)
 FROM amc_ops.dag_nodes n JOIN public.workforce_runs wr ON wr.id=n.run
 CROSS JOIN LATERAL (SELECT (wr.knowledge->'registry'->'contracts'->n.skill_type)::jsonb contract) b
 CROSS JOIN LATERAL (SELECT coalesce(sum(l.held),0) held,coalesce(sum(l.spent),0) spent FROM amc_ops.attempts a
   JOIN amc_ops.ledger l ON l.id=a.id WHERE (a.run,a.node_id)=(r,n.node_id)) tot
 CROSS JOIN LATERAL (SELECT coalesce(jsonb_agg(a.id ORDER BY a.started),'[]') attempts,
   coalesce(jsonb_agg(jsonb_build_object('id',a.id,'ordinal',a.ordinal,'outcome',a.outcome,'status',a.status,
   'month',a.month,'held',cost.held,'spent',cost.spent) ORDER BY a.started),'[]') trace
   FROM amc_ops.attempts a CROSS JOIN LATERAL (SELECT coalesce(sum(l.held),0) held,coalesce(sum(l.spent),0) spent
      FROM amc_ops.ledger l WHERE l.id=a.id) cost WHERE (a.run,a.node_id)=(r,n.node_id)) ids
 WHERE n.run=r AND b.contract IS NOT NULL
$$;
ALTER FUNCTION amc_ops.dag_report(text,text) RENAME TO dag_report_v13;
CREATE FUNCTION amc_ops.dag_report(t text,r text) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE base jsonb; binding jsonb;
BEGIN
 base:=amc_ops.dag_report_v13(t,r);
 IF base IS NULL THEN RETURN NULL; END IF;
 SELECT (knowledge->'registry')::jsonb INTO binding FROM public.workforce_runs WHERE tenant_id=t AND id=r;
 IF binding IS NULL THEN RETURN base; END IF;
 RETURN base||jsonb_build_object('registry',(binding-'contracts')||jsonb_build_object('status','pinned','plan_digest',base->'digest',
    'nodes',amc_ops.registry_nodes(r)));
END $$;
REVOKE ALL ON FUNCTION amc_ops.registry_pin(text,text,text), amc_ops.change_registry(text,text,text,text,text[]),
 amc_ops.check_registry_binding(),amc_ops.registry_nodes(text),amc_ops.dag_report(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.registry_pin(text,text,text),amc_ops.change_registry(text,text,text,text,text[]),amc_ops.dag_report(text,text) TO amc_runtime;
