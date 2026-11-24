-- Only the bootstrap task exists when a dynamic brief enters the pool.
SELECT pg_advisory_xact_lock(4197832742);
ALTER TABLE amc_ops.dag_plans DROP CONSTRAINT dag_plans_template_check,
 ADD CHECK(template IN ('diamond-v1','dynamic-v1')),
 ADD COLUMN contract jsonb, ADD COLUMN digest text CHECK(length(digest)=64),
 ADD CHECK((contract IS NULL)=(digest IS NULL));
ALTER TABLE amc_ops.dag_nodes ADD COLUMN skill_type text, ADD COLUMN assignment text;

CREATE FUNCTION amc_ops.begin_planning() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.execution_mode<>'pool' THEN RAISE EXCEPTION 'Enable pool first' USING ERRCODE='23514',CONSTRAINT='dag_requires_pool'; END IF;
 IF NEW.plan::jsonb <> '["director"]'::jsonb THEN RAISE check_violation; END IF;
 INSERT INTO amc_ops.dag_plans(tenant,client,brand,campaign,run,revision,template)
 VALUES(NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.id,1,'dynamic-v1');
 INSERT INTO amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id,position,slot,skill_type)
 VALUES(NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.id,1,'director',0,0,'director');
 RETURN NULL;
END $$;
CREATE TRIGGER start_dynamic AFTER INSERT ON public.workforce_runs FOR EACH ROW WHEN(NEW.knowledge->>'workflow'='dynamic-v1')
 EXECUTE FUNCTION amc_ops.begin_planning();

-- Only trusted dispatcher code may submit a compiled contract. The exact live
-- planner attempt fences this write; its report stays replayable on rollback.
CREATE FUNCTION amc_ops.freeze_dynamic(i uuid,c jsonb,d text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE g amc_ops.dag_plans; n jsonb; pos int:=0;
BEGIN
 SELECT p.* INTO STRICT g FROM amc_ops.dag_plans p JOIN amc_ops.attempts a ON a.run=p.run
 WHERE a.id=i AND a.node_id='director' AND a.plan_revision=p.revision AND a.status='reported'
 AND p.template='dynamic-v1' AND amc_ops.fence(i) FOR UPDATE OF p;
 IF g.contract IS NOT NULL THEN
  IF g.contract=c AND g.digest=d THEN RETURN; END IF;
  RAISE check_violation;
 END IF;
 FOR n IN SELECT value FROM jsonb_array_elements(c->'nodes') LOOP
  pos:=pos+1;
  INSERT INTO amc_ops.tasks(tenant,client,brand,campaign,run,step,skill) VALUES(g.tenant,g.client,g.brand,g.campaign,g.run,pos,n->>'skill_type');
  INSERT INTO amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id,position,slot,skill_type,assignment)
  VALUES(g.tenant,g.client,g.brand,g.campaign,g.run,g.revision,n->>'node_id',pos,pos,n->>'skill_type',n->>'assignment');
  INSERT INTO amc_ops.dag_edges SELECT g.tenant,g.client,g.brand,g.campaign,g.run,g.revision,n->>'node_id',value
  FROM jsonb_array_elements_text(CASE WHEN n->'parents'='[]'::jsonb THEN '["director"]'::jsonb ELSE n->'parents' END);
 END LOOP;
 INSERT INTO amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id,position,skill_type)
 VALUES(g.tenant,g.client,g.brand,g.campaign,g.run,g.revision,'join',pos+1,'join');
 INSERT INTO amc_ops.dag_edges SELECT g.tenant,g.client,g.brand,g.campaign,g.run,g.revision,'join',value FROM jsonb_array_elements_text(c->'join');
 UPDATE amc_ops.dag_plans SET contract=c,digest=d WHERE run=g.run;
END $$;
REVOKE ALL ON FUNCTION amc_ops.begin_planning(),amc_ops.freeze_dynamic(uuid,jsonb,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.freeze_dynamic(uuid,jsonb,text) TO amc_dispatch;

ALTER FUNCTION amc_ops.dag_report(text,text) RENAME TO dag_report_v11;
CREATE FUNCTION amc_ops.dag_report(t text,r text) RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE base jsonb; g amc_ops.dag_plans;
BEGIN
 base:=amc_ops.dag_report_v11(t,r);
 IF base IS NULL OR base->>'template'<>'dynamic-v1' THEN RETURN base; END IF;
 SELECT * INTO STRICT g FROM amc_ops.dag_plans WHERE tenant=t AND run=r;
 RETURN base||jsonb_build_object('contract',g.contract,'digest',g.digest,'phase',CASE WHEN g.contract IS NULL AND EXISTS(SELECT FROM amc_ops.attempts WHERE run=r AND step=0 AND status='reported') THEN 'validating'
  WHEN g.contract IS NULL THEN 'planning'
  WHEN EXISTS(SELECT FROM amc_ops.attempts WHERE run=r AND step>0) THEN 'executing' ELSE 'frozen' END);
END $$;
REVOKE ALL ON FUNCTION amc_ops.dag_report(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.dag_report(text,text) TO amc_runtime;
