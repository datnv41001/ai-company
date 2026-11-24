-- The runtime LOGIN cannot sign an authenticated request. Bind its identity proof
-- to the current database transaction so another connection cannot reuse it.
CREATE SCHEMA amc_crypto;
CREATE EXTENSION pgcrypto WITH SCHEMA amc_crypto;
CREATE TABLE amc_acl.identity_key (singleton boolean PRIMARY KEY CHECK(singleton), secret bytea NOT NULL);
CREATE FUNCTION amc_acl.authenticated_actor() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT coalesce(current_setting('amc.identity_proof',true)=encode(amc_crypto.hmac(
    convert_to(current_setting('amc.user_id',true)||':'||txid_current()::text,'UTF8'), secret, 'sha256'),'hex'),false)
 FROM amc_acl.identity_key WHERE singleton
$$;
REVOKE ALL ON FUNCTION amc_acl.authenticated_actor() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.authenticated_actor() TO amc_runtime;

ALTER TABLE users ADD COLUMN verified_at timestamptz;
REVOKE INSERT ON users FROM amc_runtime;
GRANT INSERT(id,email,password_hash,created_at) ON users TO amc_runtime;
CREATE POLICY signed_registration ON users AS RESTRICTIVE FOR INSERT TO amc_runtime
 WITH CHECK (amc_acl.authenticated_actor());

CREATE TABLE identity_challenges (
 user_id varchar(36) PRIMARY KEY REFERENCES users(id),
 digest varchar(64) NOT NULL CHECK(length(digest)=64),
 expires_at timestamptz NOT NULL,
 workspace_id varchar(36) UNIQUE, organization_name varchar(150), mode varchar(12),
 CHECK ((workspace_id IS NULL AND organization_name IS NULL AND mode IS NULL)
     OR (workspace_id IS NOT NULL AND organization_name IS NOT NULL AND mode IS NOT NULL AND mode IN ('agency','inhouse')))
);
ALTER TABLE identity_challenges ENABLE ROW LEVEL SECURITY;
GRANT SELECT,INSERT,UPDATE(digest,expires_at) ON identity_challenges TO amc_runtime;
CREATE POLICY own_challenge ON identity_challenges TO amc_runtime
 USING(user_id=current_setting('amc.user_id',true) AND amc_acl.authenticated_actor())
 WITH CHECK(user_id=current_setting('amc.user_id',true) AND amc_acl.authenticated_actor());

REVOKE EXECUTE ON FUNCTION amc_acl.create_workspace(text,text,text) FROM amc_runtime;
CREATE FUNCTION amc_acl.verify_email(candidate text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor text:=current_setting('amc.user_id',true); challenge public.identity_challenges%ROWTYPE;
BEGIN
 IF amc_acl.authenticated_actor() IS NOT TRUE THEN RETURN false; END IF;
 DELETE FROM public.identity_challenges WHERE user_id=actor AND digest=candidate AND expires_at>clock_timestamp()
 RETURNING * INTO challenge;
 IF NOT FOUND THEN RETURN false; END IF;
 UPDATE public.users SET verified_at=clock_timestamp() WHERE id=actor AND verified_at IS NULL;
 IF NOT FOUND THEN RETURN false; END IF;
 IF challenge.workspace_id IS NOT NULL THEN
    PERFORM set_config('amc.tenant_id',challenge.workspace_id,true);
    PERFORM amc_acl.create_workspace(challenge.workspace_id,challenge.organization_name,challenge.mode);
 END IF;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION amc_acl.verify_email(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.verify_email(text) TO amc_runtime;

ALTER TABLE portal_invitations ALTER COLUMN client_id DROP NOT NULL, ALTER COLUMN client_name DROP NOT NULL,
 ADD COLUMN role varchar(16) NOT NULL DEFAULT 'client_viewer',
 ADD CONSTRAINT invited_scope CHECK(
 (role='client_viewer' AND client_id IS NOT NULL AND client_name IS NOT NULL)
 OR (role IN ('viewer','editor','admin') AND client_id IS NULL AND client_name IS NULL AND brand_id IS NULL
 AND campaign_id IS NULL AND NOT can_decide AND NOT can_comment)),
 ADD FOREIGN KEY (tenant_id) REFERENCES tenants(id);
REVOKE INSERT ON memberships,portal_grants FROM amc_runtime;
DROP POLICY membership_grant ON memberships;
-- Scope transitions operate only on an existing membership. Create its replacement
-- portal grant from the row AFTER the admin's authorized update has succeeded.
CREATE FUNCTION amc_acl.replace_scoped_grant() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 INSERT INTO public.portal_grants(tenant_id,user_id,client_id,can_comment,can_decide)
 VALUES(NEW.tenant_id,NEW.user_id,NEW.client_id,false,false);
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_acl.replace_scoped_grant() FROM PUBLIC;
CREATE POLICY owner_rescope_grant ON portal_grants FOR INSERT TO CURRENT_USER
 WITH CHECK(amc_acl.member_role(tenant_id) IN ('owner','admin') AND amc_acl.authenticated_actor());
CREATE TRIGGER replacement_portal_grant AFTER UPDATE OF role,client_id ON memberships
 FOR EACH ROW WHEN (NEW.role='client_viewer' AND (OLD.client_id IS DISTINCT FROM NEW.client_id OR OLD.role<>NEW.role))
 EXECUTE FUNCTION amc_acl.replace_scoped_grant();
CREATE POLICY signed_rescope ON memberships AS RESTRICTIVE FOR UPDATE TO amc_runtime
 USING(amc_acl.authenticated_actor()) WITH CHECK(amc_acl.authenticated_actor());
CREATE POLICY signed_revoke ON memberships AS RESTRICTIVE FOR DELETE TO amc_runtime USING(amc_acl.authenticated_actor());
CREATE POLICY signed_rights ON portal_grants AS RESTRICTIVE FOR UPDATE TO amc_runtime
 USING(amc_acl.authenticated_actor()) WITH CHECK(amc_acl.authenticated_actor());
CREATE POLICY signed_remove ON portal_grants AS RESTRICTIVE FOR DELETE TO amc_runtime USING(amc_acl.authenticated_actor());
CREATE POLICY signed_invitation_read ON portal_invitations AS RESTRICTIVE FOR SELECT TO amc_runtime
 USING(amc_acl.authenticated_actor() AND (amc_acl.member_role(tenant_id) IN ('owner','admin')
 OR EXISTS(SELECT FROM users u WHERE u.id=current_setting('amc.user_id',true) AND u.verified_at IS NOT NULL)));
CREATE POLICY signed_invite ON portal_invitations AS RESTRICTIVE FOR INSERT TO amc_runtime WITH CHECK(
 amc_acl.authenticated_actor() AND EXISTS(SELECT FROM users WHERE id=invited_by AND verified_at IS NOT NULL)
 AND (role<>'admin' OR amc_acl.member_role(tenant_id)='owner')
 AND EXISTS(SELECT FROM users u WHERE u.id=user_id AND u.email=portal_invitations.email));
CREATE POLICY signed_withdraw ON portal_invitations AS RESTRICTIVE FOR UPDATE TO amc_runtime
 USING(amc_acl.authenticated_actor()) WITH CHECK(amc_acl.authenticated_actor());

CREATE OR REPLACE FUNCTION amc_acl.accept_portal_invitation(invite text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE i public.portal_invitations%ROWTYPE; issuer_role text;
BEGIN
 IF amc_acl.authenticated_actor() IS NOT TRUE THEN RETURN false; END IF;
 SELECT * INTO i FROM public.portal_invitations WHERE id=invite
 AND user_id=current_setting('amc.user_id',true) FOR UPDATE;
 IF NOT FOUND OR i.state<>'pending' OR i.expires_at<=clock_timestamp() THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT FROM public.users WHERE id=i.user_id AND email=i.email AND verified_at IS NOT NULL)
 OR NOT EXISTS(SELECT FROM public.users WHERE id=i.invited_by AND verified_at IS NOT NULL) THEN RETURN false; END IF;
 SELECT role INTO issuer_role FROM public.memberships WHERE tenant_id=i.tenant_id AND user_id=i.invited_by FOR SHARE;
 IF NOT FOUND OR issuer_role NOT IN ('owner','admin') OR (i.role='admin' AND issuer_role<>'owner') THEN RETURN false; END IF;
 -- The composite client/brand/campaign FKs and invited_scope are enforced for the
 -- frozen row and again on the grant. No scope or role comes from the recipient.
 INSERT INTO public.memberships(tenant_id,user_id,role,client_id) VALUES(i.tenant_id,i.user_id,i.role,i.client_id)
 ON CONFLICT(tenant_id,user_id) DO NOTHING;
 IF NOT FOUND THEN RETURN false; END IF;
 IF i.role='client_viewer' THEN
   INSERT INTO public.portal_grants(tenant_id,user_id,client_id,brand_id,campaign_id,can_comment,can_decide)
   VALUES(i.tenant_id,i.user_id,i.client_id,i.brand_id,i.campaign_id,i.can_comment,i.can_decide);
 END IF;
 UPDATE public.portal_invitations SET state='accepted' WHERE id=i.id;
 INSERT INTO public.audit_events(id,tenant_id,user_id,event,subject_id,details,occurred_at)
 VALUES(gen_random_uuid()::text,i.tenant_id,i.user_id,'portal.invitation_accepted',i.id,json_build_object('role',i.role),clock_timestamp());
 RETURN true;
END $$;
