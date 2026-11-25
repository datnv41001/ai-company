CREATE SCHEMA amc_c3;
REVOKE ALL ON SCHEMA amc_c3 FROM PUBLIC, amc_runtime;
CREATE TABLE amc_c3.versions(version integer PRIMARY KEY);
INSERT INTO amc_c3.versions VALUES(1);
ALTER TABLE public.workforce_briefs ADD COLUMN origin varchar(12) NOT NULL DEFAULT 'agency';
ALTER TABLE public.workforce_briefs ADD CONSTRAINT c3_brief_origin CHECK (
 (origin='agency' AND NOT(coalesce(payload::jsonb,'{}') ? 'internal_task')) OR
 (origin='internal' AND payload IS NOT NULL AND payload::jsonb @> '{"internal_task":true}'
  AND jsonb_typeof(payload::jsonb->'task_intent')='object' AND payload::jsonb ? 'task_intent'));

CREATE POLICY c3_internal_brief_open ON public.workforce_briefs FOR INSERT TO amc_runtime WITH CHECK (
 origin='internal' AND recipient_id=current_setting('amc.user_id',true) AND tenant_id=current_setting('amc.tenant_id',true)
 AND amc_acl.authenticated_actor() AND amc_acl.member_role(tenant_id) IN ('owner','admin','editor')
 AND EXISTS(SELECT FROM public.tenants t WHERE t.id=tenant_id AND t.mode='inhouse'));
CREATE POLICY c3_internal_brief_private ON public.workforce_briefs AS RESTRICTIVE FOR SELECT TO amc_runtime USING (
 origin='agency' OR (amc_acl.authenticated_actor() AND amc_acl.member_role(tenant_id) IN ('owner','admin','editor','viewer')));

CREATE FUNCTION amc_acl.lock_c3_internal_target(t text,c text,b text,k text,i text) RETURNS boolean
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE author_id text;
BEGIN
 PERFORM amc_acl.lock_knowledge(t,c,b);
 SELECT wb.recipient_id INTO author_id FROM public.workforce_briefs wb
 JOIN public.tenants org ON org.id=wb.tenant_id AND org.mode='inhouse'
 WHERE (wb.tenant_id,wb.client_id,wb.brand_id,wb.campaign_id,wb.id,wb.origin)=(t,c,b,k,i,'internal');
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=author_id AND role IN ('owner','admin','editor') FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM 1 FROM public.campaigns WHERE (tenant_id,brand_id,id)=(t,b,k) FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM 1 FROM public.workforce_briefs WHERE (tenant_id,client_id,brand_id,campaign_id,id,recipient_id,origin)=(t,c,b,k,i,author_id,'internal') FOR SHARE;
 RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION amc_acl.lock_c3_internal_target(text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.lock_c3_internal_target(text,text,text,text,text) TO amc_runtime;

CREATE FUNCTION amc_acl.guard_c3_task_origin() RETURNS trigger
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE task_origin text;
BEGIN
 SELECT b.origin INTO task_origin FROM public.workforce_briefs b WHERE
  (b.id,b.tenant_id,b.client_id,b.brand_id,b.campaign_id)=(NEW.brief_id,NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id);
 IF (task_origin='internal') IS DISTINCT FROM (NEW.knowledge::jsonb @> '{"internal_task":true}') THEN
   RAISE EXCEPTION 'Task origin differs' USING ERRCODE='23514',CONSTRAINT='workforce_recipient_required';
 END IF;
 IF task_origin='internal' AND (
   coalesce(NEW.knowledge::jsonb #>> '{registry,workflow}','') NOT IN ('WF-03/research-strategy-draft@3','WF-13/landing-seo-draft@6')
   OR NOT (NEW.knowledge::jsonb ? 'c3_manifest') OR
   NOT amc_acl.lock_c3_internal_target(NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.brief_id)
 ) THEN RAISE EXCEPTION 'Internal task unavailable' USING ERRCODE='23514',CONSTRAINT='workforce_recipient_required';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_acl.guard_c3_task_origin() FROM PUBLIC;
CREATE TRIGGER c3_verify_task_origin BEFORE INSERT ON public.workforce_runs FOR EACH ROW EXECUTE FUNCTION amc_acl.guard_c3_task_origin();
DROP TRIGGER workforce_check_intake ON public.workforce_runs;
CREATE TRIGGER workforce_check_intake BEFORE INSERT ON public.workforce_runs FOR EACH ROW
 WHEN (NOT (NEW.knowledge::jsonb @> '{"internal_task":true}')) EXECUTE FUNCTION amc_acl.guard_workforce_enqueue();

CREATE FUNCTION amc_acl.cancel_internal_task_author() RETURNS trigger
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.role NOT IN ('owner','admin','editor') OR
    (TG_OP='UPDATE' AND NEW.role IN ('owner','admin','editor')) THEN RETURN NULL; END IF;
 UPDATE public.workforce_runs r SET state='failed',last_error='recipient_revoked',lease=NULL,
  journal=CASE WHEN state='running' THEN jsonb_set(r.journal::jsonb,'{-1}',(r.journal::jsonb -> -1)
    || jsonb_build_object('outcome','recipient_revoked','finished_at',clock_timestamp(),'usage_unconfirmed',true))::json
    ELSE r.journal END
  WHERE r.tenant_id=OLD.tenant_id AND state IN ('queued','running') AND EXISTS (
    SELECT FROM public.workforce_briefs b WHERE b.id=r.brief_id AND b.origin='internal' AND b.recipient_id=OLD.user_id);
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.cancel_internal_task_author() FROM PUBLIC;
CREATE TRIGGER workforce_internal_author_revoked AFTER DELETE OR UPDATE OF role ON public.memberships
 FOR EACH ROW EXECUTE FUNCTION amc_acl.cancel_internal_task_author();

-- Operations owns these non-interactive identities. The web runtime has no enrollment or lookup privileges.
CREATE TABLE amc_c3.worker_operators (
 tenant_id text PRIMARY KEY REFERENCES public.tenants(id), user_id text NOT NULL UNIQUE REFERENCES public.users(id)
);
