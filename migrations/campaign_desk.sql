-- Additive capability on the compatible two-namespace journal. Signed requests bind actor,
-- exact scope, payload and transaction. Only this desk may settle assigned business cases.
CREATE TABLE amc_acl.campaign_member_epochs (tenant_id text NOT NULL,user_id text NOT NULL,epoch bigint NOT NULL,
  PRIMARY KEY(tenant_id,user_id));
REVOKE ALL ON amc_acl.campaign_member_epochs FROM PUBLIC,amc_runtime;
CREATE FUNCTION amc_acl.advance_campaign_membership() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='UPDATE' AND (OLD.role,OLD.client_id) IS NOT DISTINCT FROM (NEW.role,NEW.client_id) THEN RETURN NULL; END IF;
 INSERT INTO amc_acl.campaign_member_epochs VALUES (OLD.tenant_id,OLD.user_id,1)
 ON CONFLICT (tenant_id,user_id) DO UPDATE SET epoch=amc_acl.campaign_member_epochs.epoch+1;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.advance_campaign_membership() FROM PUBLIC;
CREATE TRIGGER campaign_membership_changed AFTER DELETE OR UPDATE OF role,client_id ON public.memberships
 FOR EACH ROW EXECUTE FUNCTION amc_acl.advance_campaign_membership();

-- A compatible predecessor can still boot on core 26. Enforce optional quote intake
-- on append so an older process cannot override the campaign owner's approved journey.
CREATE FUNCTION amc_acl.approved_rfq_intake() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM public.knowledge_commands p JOIN public.knowledge_commands a
      ON (a.tenant_id,a.client_id,a.brand_id,a.result->>'id',a.result->>'digest')=
         (p.tenant_id,p.client_id,p.brand_id,p.result->>'id',p.result->>'digest')
      WHERE p.operation='campaign_plan' AND a.operation='campaign_plan_approve'
      AND (p.tenant_id,p.client_id,p.brand_id,p.result->>'id',p.result->>'campaign_id')=
          (NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.result->>'plan_id',NEW.result->>'campaign_id')
      AND (p.result->>'buyer_action'='rfq' OR p.result->>'buyer_action'='appointment' AND
           coalesce(p.result::jsonb->'secondary_conversions','[]'::jsonb) @> '["rfq"]'::jsonb))
 THEN RAISE EXCEPTION 'Campaign plan does not authorize quote intake' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_acl.approved_rfq_intake() FROM PUBLIC;
CREATE TRIGGER campaign_rfq_intake BEFORE INSERT ON public.knowledge_commands
 FOR EACH ROW WHEN (NEW.operation='campaign_sandbox_v2' AND NEW.result->>'kind'='rfq')
 EXECUTE FUNCTION amc_acl.approved_rfq_intake();
