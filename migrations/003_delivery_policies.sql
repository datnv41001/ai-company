-- Match Python's compact UTF-8 JSON in alphabetical key order.
ALTER TABLE client_reviews ADD CONSTRAINT snapshot_digest_matches CHECK (
    digest=encode(sha256(convert_to('{"preview":'||to_json(preview)::text||',"title":'||to_json(title)::text||'}','UTF8')),'hex')
);
ALTER TABLE deliverables ADD COLUMN last_editor_id varchar(36) REFERENCES users(id);
INSERT INTO portal_grants (tenant_id,user_id,client_id,can_comment,can_decide)
SELECT tenant_id,user_id,client_id,false,false FROM memberships WHERE role='client_viewer';

-- V2 lists were client-scoped, but they contained agency-only drafts and briefs.
DO $$
DECLARE tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['brands','campaigns','work_tasks','deliverables','action_requests'] LOOP
        EXECUTE format('DROP POLICY scoped_read ON %I',tbl);
        EXECUTE format('CREATE POLICY staff_read ON %I FOR SELECT TO amc_runtime USING
            (amc_acl.member_role(tenant_id) IN (''viewer'',''editor'',''admin'',''owner''))',tbl);
    END LOOP;
    FOREACH tbl IN ARRAY ARRAY['portal_grants','client_reviews','review_entries'] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',tbl);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',tbl);
        EXECUTE format('GRANT SELECT, INSERT ON %I TO amc_runtime',tbl);
    END LOOP;
END $$;
GRANT UPDATE(brand_id,campaign_id,can_comment,can_decide), DELETE ON portal_grants TO amc_runtime;
CREATE POLICY grant_admin ON portal_grants FOR ALL TO amc_runtime
USING (amc_acl.member_role(tenant_id) IN ('owner','admin'))
WITH CHECK (amc_acl.member_role(tenant_id) IN ('owner','admin'));
CREATE POLICY grant_read ON portal_grants FOR SELECT TO amc_runtime USING
    (user_id=current_setting('amc.user_id',true) AND client_id=amc_acl.client_scope(tenant_id));

CREATE POLICY review_read ON client_reviews FOR SELECT TO amc_runtime USING (
    amc_acl.member_role(tenant_id) IN ('owner','admin','editor','viewer') OR EXISTS (
        SELECT 1 FROM portal_grants g WHERE g.tenant_id=client_reviews.tenant_id
        AND g.user_id=current_setting('amc.user_id',true) AND g.client_id=client_reviews.client_id
        AND (g.brand_id IS NULL OR g.brand_id=client_reviews.brand_id)
        AND (g.campaign_id IS NULL OR g.campaign_id=client_reviews.campaign_id)
    )
);
CREATE POLICY review_share ON client_reviews FOR INSERT TO amc_runtime WITH CHECK (
    amc_acl.member_role(tenant_id) IN ('owner','admin') AND requested_by=current_setting('amc.user_id',true)
    AND EXISTS (SELECT 1 FROM deliverables d WHERE d.id=deliverable_id AND d.status='approved'
        AND d.reviewed_by=qa_by AND d.title=client_reviews.title AND d.content->>'client_preview'=preview)
);
CREATE POLICY entry_read ON review_entries FOR SELECT TO amc_runtime USING (
    EXISTS (SELECT 1 FROM client_reviews r WHERE r.id=review_id)
);
CREATE POLICY entry_append ON review_entries FOR INSERT TO amc_runtime WITH CHECK (
    actor_id=current_setting('amc.user_id',true) AND EXISTS (SELECT 1 FROM client_reviews r WHERE r.id=review_id)
    AND ((amc_acl.member_role(tenant_id) IN ('admin','owner') AND kind IN ('cancelled','superseded','comment'))
         OR (amc_acl.member_role(tenant_id)='editor' AND kind='comment')
         OR (amc_acl.member_role(tenant_id)='client_viewer' AND EXISTS (
            SELECT 1 FROM portal_grants g WHERE g.tenant_id=review_entries.tenant_id AND g.user_id=actor_id AND
            ((g.can_comment AND kind='comment') OR (g.can_decide AND kind IN ('approved','changes_requested','rejected')))
         )))
);
-- Runtime cannot UPDATE/DELETE snapshots or events. Enforce expiry for SQL writers too.
CREATE FUNCTION amc_acl.check_open_review() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$
DECLARE deadline timestamptz; document_id text;
BEGIN
    SELECT expires_at,deliverable_id INTO deadline,document_id FROM public.client_reviews WHERE id=NEW.review_id;
    IF document_id IS NULL THEN RAISE EXCEPTION 'Review unavailable' USING ERRCODE='42501'; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(document_id,3));
    IF EXISTS (SELECT FROM public.review_entries WHERE review_id=NEW.review_id AND kind <> 'comment')
       OR (deadline<=clock_timestamp() AND NEW.kind NOT IN ('cancelled','superseded')) THEN
        RAISE EXCEPTION 'Review closed' USING ERRCODE='23514';
    END IF;
    NEW.created_at=clock_timestamp();
    RETURN NEW;
END $$;
CREATE TRIGGER review_is_open BEFORE INSERT ON review_entries FOR EACH ROW EXECUTE FUNCTION amc_acl.check_open_review();
