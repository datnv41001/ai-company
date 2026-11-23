CREATE TABLE portal_invitations (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	invited_by VARCHAR(36) NOT NULL,
	email VARCHAR(320) NOT NULL,
	workspace_name VARCHAR(150) NOT NULL,
	client_name VARCHAR(160) NOT NULL,
	brand_id VARCHAR(36),
	campaign_id VARCHAR(36),
	can_comment BOOLEAN NOT NULL,
	can_decide BOOLEAN NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	state VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, client_id) REFERENCES clients (tenant_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	FOREIGN KEY(tenant_id, brand_id, campaign_id) REFERENCES campaigns (tenant_id, brand_id, id),
	CHECK (campaign_id IS NULL OR brand_id IS NOT NULL),
	CHECK (state IN ('pending','accepted','revoked')),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(invited_by) REFERENCES users (id)
);

CREATE INDEX ix_portal_invitations_tenant_id ON portal_invitations (tenant_id);

CREATE INDEX ix_portal_invitations_user_id ON portal_invitations (user_id);

CREATE UNIQUE INDEX uq_pending_portal_invite ON portal_invitations (tenant_id, user_id) WHERE state='pending';

CREATE INDEX ix_review_page ON client_reviews (tenant_id,created_at,id);
CREATE INDEX ix_client_review_page ON client_reviews (tenant_id,client_id,created_at,id);
-- Historical decisions retain their exact text. Enforce reasons on new entries.
ALTER TABLE review_entries ADD CONSTRAINT require_change_reason
    CHECK (kind NOT IN ('rejected','changes_requested')
        OR length(regexp_replace(note,'^[[:space:]]+|[[:space:]]+$','','g')) >= 5) NOT VALID;
CREATE POLICY editor_cancel ON review_entries FOR INSERT TO amc_runtime WITH CHECK (
    kind='cancelled' AND actor_id=current_setting('amc.user_id',true)
    AND amc_acl.member_role(tenant_id)='editor'
    AND EXISTS (SELECT FROM client_reviews r WHERE r.id=review_id)
);

ALTER TABLE portal_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_invitations FORCE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE(state) ON portal_invitations TO amc_runtime;
CREATE POLICY invitation_read ON portal_invitations FOR SELECT TO amc_runtime USING (
    user_id=current_setting('amc.user_id',true) OR amc_acl.member_role(tenant_id) IN ('owner','admin')
);
CREATE POLICY invitation_create ON portal_invitations FOR INSERT TO amc_runtime WITH CHECK (
    amc_acl.member_role(tenant_id) IN ('owner','admin') AND invited_by=current_setting('amc.user_id',true)
    AND state='pending' AND expires_at>now()
);
CREATE POLICY invitation_revoke ON portal_invitations FOR UPDATE TO amc_runtime
    USING (amc_acl.member_role(tenant_id) IN ('owner','admin') AND state='pending')
    WITH CHECK (amc_acl.member_role(tenant_id) IN ('owner','admin') AND state='revoked');

-- FORCE RLS also applies to a non-BYPASSRLS table owner. These narrowly scoped
-- policies support the two functions below when the migration owner is unprivileged at runtime.
CREATE POLICY owner_invite_read ON portal_invitations FOR SELECT TO CURRENT_USER
    USING (user_id=current_setting('amc.user_id',true));
CREATE POLICY owner_invite_accept ON portal_invitations FOR UPDATE TO CURRENT_USER
    USING (user_id=current_setting('amc.user_id',true) AND state='pending')
    WITH CHECK (user_id=current_setting('amc.user_id',true) AND state='accepted');
CREATE POLICY owner_directory ON portal_grants FOR SELECT TO CURRENT_USER
    USING (amc_acl.member_role(tenant_id) IN ('owner','admin'));
CREATE POLICY owner_accepted_grant ON portal_grants FOR INSERT TO CURRENT_USER
    WITH CHECK (user_id=current_setting('amc.user_id',true));
CREATE POLICY owner_accept_audit ON audit_events FOR INSERT TO CURRENT_USER
    WITH CHECK (event='portal.invitation_accepted' AND user_id=current_setting('amc.user_id',true));

-- Only return addresses for recipients of the selected agency. Do not expand identity-table SELECT.
CREATE FUNCTION amc_acl.recipient_emails(t text) RETURNS TABLE(uid text, email text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
    SELECT u.id::text, u.email::text FROM public.users u JOIN public.portal_grants g ON g.user_id=u.id
    WHERE g.tenant_id=t AND amc_acl.member_role(t) IN ('owner','admin')
$$;

-- A recipient has no tenant role yet. Only this narrow operation can consume their addressed invitation.
-- Scope, rights and identities come from the locked invitation, never from arguments supplied by a client.
CREATE FUNCTION amc_acl.accept_portal_invitation(invite text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE i public.portal_invitations%ROWTYPE;
BEGIN
    SELECT * INTO i FROM public.portal_invitations WHERE id=invite
        AND user_id=current_setting('amc.user_id',true) FOR UPDATE;
    IF NOT FOUND OR i.state<>'pending' OR i.expires_at<=clock_timestamp() THEN RETURN false; END IF;
    INSERT INTO public.memberships (tenant_id,user_id,role,client_id)
        VALUES (i.tenant_id,i.user_id,'client_viewer',i.client_id)
        ON CONFLICT (tenant_id,user_id) DO NOTHING;
    IF NOT FOUND THEN RETURN false; END IF;
    INSERT INTO public.portal_grants (tenant_id,user_id,client_id,brand_id,campaign_id,can_comment,can_decide)
        VALUES (i.tenant_id,i.user_id,i.client_id,i.brand_id,i.campaign_id,i.can_comment,i.can_decide);
    UPDATE public.portal_invitations SET state='accepted' WHERE id=i.id;
    INSERT INTO public.audit_events(id,tenant_id,user_id,event,subject_id,details,occurred_at)
        VALUES(gen_random_uuid()::text,i.tenant_id,i.user_id,'portal.invitation_accepted',i.id,'{}',clock_timestamp());
    RETURN true;
END $$;
REVOKE ALL ON FUNCTION amc_acl.recipient_emails(text), amc_acl.accept_portal_invitation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.recipient_emails(text), amc_acl.accept_portal_invitation(text) TO amc_runtime;
