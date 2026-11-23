-- Runtime grants stay unchanged. Trigger functions operate only on the addressed recipient's runs.
CREATE POLICY authority_owner_briefs ON workforce_briefs FOR SELECT TO CURRENT_USER USING (true);
CREATE POLICY authority_owner_runs ON workforce_runs FOR ALL TO CURRENT_USER USING (true) WITH CHECK (true);
CREATE POLICY authority_owner_grants_read ON portal_grants FOR SELECT TO CURRENT_USER USING (true);
CREATE POLICY authority_owner_grants_lock ON portal_grants FOR UPDATE TO CURRENT_USER USING (true) WITH CHECK (true);
CREATE POLICY authority_owner_audit ON audit_events FOR INSERT TO CURRENT_USER
    WITH CHECK (event='workforce.recipient_revoked');

CREATE FUNCTION amc_acl.guard_workforce_enqueue() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
    -- Revocation and enqueue take conflicting locks on the same grant. A transaction
    -- that waited for a grant change rechecks the current row under READ COMMITTED.
    PERFORM g.user_id FROM public.portal_grants g JOIN public.workforce_briefs b
      ON b.tenant_id=g.tenant_id AND b.recipient_id=g.user_id AND b.client_id=g.client_id
      WHERE b.id=NEW.brief_id AND b.tenant_id=NEW.tenant_id
      AND (g.brand_id IS NULL OR g.brand_id=b.brand_id)
      AND (g.campaign_id IS NULL OR g.campaign_id=b.campaign_id) FOR SHARE OF g;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Brief recipient unavailable' USING ERRCODE='23514',CONSTRAINT='workforce_recipient_required';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION amc_acl.cancel_withdrawn_workforce() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
    UPDATE public.workforce_runs r SET state='failed',last_error='recipient_revoked',lease=NULL,
      journal=CASE WHEN r.state='running' THEN jsonb_set(r.journal::jsonb,'{-1}',
         (r.journal::jsonb -> -1) || jsonb_build_object('outcome','recipient_revoked','finished_at',clock_timestamp(),
         'usage_unconfirmed',true))::json ELSE r.journal END
      WHERE r.state IN ('queued','running') AND r.tenant_id=OLD.tenant_id
      AND EXISTS (SELECT FROM public.workforce_briefs b WHERE b.id=r.brief_id AND b.recipient_id=OLD.user_id)
      AND NOT EXISTS (SELECT FROM public.portal_grants g WHERE g.tenant_id=r.tenant_id AND g.user_id=OLD.user_id
        AND g.client_id=r.client_id AND (g.brand_id IS NULL OR g.brand_id=r.brand_id)
        AND (g.campaign_id IS NULL OR g.campaign_id=r.campaign_id));
    RETURN NULL;
END $$;

CREATE FUNCTION amc_acl.audit_withdrawn_workforce() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
    INSERT INTO public.audit_events(id,tenant_id,user_id,event,subject_id,details,occurred_at)
    VALUES (gen_random_uuid()::text,NEW.tenant_id,coalesce(nullif(current_setting('amc.user_id',true),''),'workforce-policy'),
        'workforce.recipient_revoked',NEW.id,json_build_object('previous_state',OLD.state,'reserved_microusd',NEW.reserved_microusd),clock_timestamp());
    RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.guard_workforce_enqueue(),amc_acl.cancel_withdrawn_workforce(),amc_acl.audit_withdrawn_workforce() FROM PUBLIC;
CREATE TRIGGER workforce_check_intake BEFORE INSERT ON workforce_runs FOR EACH ROW EXECUTE FUNCTION amc_acl.guard_workforce_enqueue();
CREATE TRIGGER workforce_grant_withdrawn AFTER DELETE OR UPDATE OF brand_id,campaign_id ON portal_grants
    FOR EACH ROW EXECUTE FUNCTION amc_acl.cancel_withdrawn_workforce();
CREATE TRIGGER workforce_audit_withdrawal AFTER UPDATE OF last_error ON workforce_runs FOR EACH ROW
    WHEN (NEW.last_error='recipient_revoked' AND OLD.last_error IS DISTINCT FROM NEW.last_error)
    EXECUTE FUNCTION amc_acl.audit_withdrawn_workforce();

-- A v5 database can already contain orphaned active work. Preserve completed snapshots and prior reservations.
UPDATE workforce_runs r SET state='failed',lease=NULL,last_error='recipient_revoked',
    journal=CASE WHEN r.state='running' THEN jsonb_set(r.journal::jsonb,'{-1}',(r.journal::jsonb -> -1) ||
       jsonb_build_object('outcome','recipient_revoked','usage_unconfirmed',true,'finished_at',clock_timestamp()))::json ELSE r.journal END
    WHERE r.state IN ('queued','running') AND NOT EXISTS
    (SELECT FROM workforce_briefs b JOIN portal_grants g ON g.tenant_id=b.tenant_id AND g.user_id=b.recipient_id
     AND g.client_id=b.client_id WHERE b.id=r.brief_id AND (g.brand_id IS NULL OR g.brand_id=b.brand_id)
     AND (g.campaign_id IS NULL OR g.campaign_id=b.campaign_id));
