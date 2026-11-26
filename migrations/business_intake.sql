-- Scoped append compatibility for mixed core-v26 workers. No historical rows are rewritten.
LOCK TABLE public.knowledge_commands IN SHARE ROW EXCLUSIVE MODE;
CREATE FUNCTION amc_acl.check_business_intake() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE contract jsonb;
BEGIN
 SELECT p.result::jsonb->'intake_contract' INTO contract FROM public.knowledge_commands p
 WHERE p.operation='campaign_plan' AND (p.tenant_id,p.client_id,p.brand_id,p.result->>'id') =
       (NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.result->>'plan_id');
 IF NEW.operation IN ('studio_production','studio_landing_v2') THEN
   IF NOT FOUND OR (NEW.result::jsonb #> '{master,intake_contract}') IS DISTINCT FROM contract
      OR ((NEW.operation='studio_landing_v2') IS DISTINCT FROM (contract IS NOT NULL)) THEN
     RAISE EXCEPTION 'Reload the approved business intake with a compatible landing writer' USING ERRCODE='55000';
   END IF;
 ELSIF contract IS NOT NULL AND (NEW.result->>'intake_writer') IS DISTINCT FROM 'business-intake/1' THEN
   RAISE EXCEPTION 'Use a compatible writer for the approved business intake' USING ERRCODE='55000';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_acl.check_business_intake() FROM PUBLIC;
CREATE TRIGGER business_intake_writer BEFORE INSERT ON public.knowledge_commands FOR EACH ROW
 WHEN ((NEW.operation IN ('studio_production','studio_landing_v2') AND NEW.result->>'kind'='landing')
   OR (NEW.operation='campaign_sandbox_v2' AND NEW.result->>'entity' IN ('sessions','appointments','leads')))
 EXECUTE FUNCTION amc_acl.check_business_intake();
