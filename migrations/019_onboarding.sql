-- Preserve v18 inbox offers. New offers can be addressed before there is a user.
ALTER TABLE public.portal_invitations ALTER COLUMN user_id DROP NOT NULL, ADD COLUMN link_digest varchar(64);
CREATE UNIQUE INDEX uq_invitation_link ON public.portal_invitations(link_digest);
CREATE UNIQUE INDEX uq_pending_invite_email ON public.portal_invitations(tenant_id,lower(email)) WHERE state='pending';

CREATE FUNCTION amc_acl.addressed_recipient(target text, address text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT amc_acl.authenticated_actor() AND EXISTS (
 SELECT FROM public.users WHERE id=current_setting('amc.user_id',true) AND verified_at IS NOT NULL
 AND email=address AND (target IS NULL OR id=target))
$$;
REVOKE ALL ON FUNCTION amc_acl.addressed_recipient(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.addressed_recipient(text,text) TO amc_runtime;
CREATE POLICY addressed_inbox ON public.portal_invitations FOR SELECT TO amc_runtime
 USING(amc_acl.addressed_recipient(user_id,email));
ALTER POLICY owner_invite_read ON public.portal_invitations USING(amc_acl.addressed_recipient(user_id,email));
ALTER POLICY owner_invite_accept ON public.portal_invitations
 USING(state='pending' AND amc_acl.addressed_recipient(user_id,email))
 WITH CHECK(state='accepted' AND user_id=current_setting('amc.user_id',true));
ALTER POLICY signed_invite ON public.portal_invitations WITH CHECK(
 amc_acl.authenticated_actor() AND EXISTS(SELECT FROM public.users WHERE id=invited_by AND verified_at IS NOT NULL)
 AND (role<>'admin' OR amc_acl.member_role(tenant_id)='owner')
 AND user_id IS NULL AND email=lower(email) AND length(link_digest)=64 AND link_digest IS NOT NULL);

-- Restrict workspace creation to a verified actor. The underlying insert atomically
-- creates the tenant and owner and refuses an existing ID.
CREATE FUNCTION amc_acl.create_verified_workspace(t text, org text, org_mode text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF amc_acl.authenticated_actor() IS NOT TRUE OR NOT EXISTS
   (SELECT FROM public.users WHERE id=current_setting('amc.user_id',true) AND verified_at IS NOT NULL) THEN
   RAISE EXCEPTION 'Verified actor required' USING ERRCODE='42501';
 END IF;
 PERFORM amc_acl.create_workspace(t,org,org_mode);
END $$;
REVOKE ALL ON FUNCTION amc_acl.create_verified_workspace(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.create_verified_workspace(text,text,text) TO amc_runtime;

-- A generic signed runtime transaction cannot set a chosen verification digest
-- or present the digest it can read as evidence of having received the code.
DO $install$
DECLARE crypto_schema name;
BEGIN
 SELECT n.nspname INTO STRICT crypto_schema FROM pg_catalog.pg_extension e
 JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace
 JOIN pg_catalog.pg_depend d ON d.refclassid='pg_catalog.pg_extension'::regclass
 AND d.refobjid=e.oid AND d.deptype='e' AND d.classid='pg_catalog.pg_proc'::regclass
 WHERE e.extname='pgcrypto' AND d.objid=pg_catalog.to_regprocedure(
 pg_catalog.format('%I.hmac(pg_catalog.bytea,pg_catalog.bytea,pg_catalog.text)',n.nspname));
 EXECUTE pg_catalog.format($def$
 CREATE FUNCTION amc_acl.challenge_authorized(purpose text, digest text) RETURNS boolean
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog
 BEGIN ATOMIC
 SELECT amc_acl.authenticated_actor() AND coalesce(current_setting('amc.challenge_proof',true)=encode(
 %I.hmac(convert_to('challenge:'||purpose||':'||current_setting('amc.user_id',true)||':'||txid_current()::text||':'||digest,'UTF8'),secret,'sha256'::text),'hex'),false)
 FROM amc_acl.identity_key WHERE singleton;
 END $def$,crypto_schema);
END $install$;
REVOKE ALL ON FUNCTION amc_acl.challenge_authorized(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.challenge_authorized(text,text) TO amc_runtime;
CREATE POLICY signed_challenge_issue ON public.identity_challenges AS RESTRICTIVE FOR INSERT TO amc_runtime
 WITH CHECK(amc_acl.challenge_authorized('issue',digest));
CREATE POLICY signed_challenge_replace ON public.identity_challenges AS RESTRICTIVE FOR UPDATE TO amc_runtime
 USING(true) WITH CHECK(amc_acl.challenge_authorized('issue',digest));
ALTER FUNCTION amc_acl.verify_email(text) RENAME TO complete_verified_email;
REVOKE ALL ON FUNCTION amc_acl.complete_verified_email(text) FROM amc_runtime;
CREATE FUNCTION amc_acl.verify_email(candidate text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF amc_acl.challenge_authorized('redeem',candidate) IS NOT TRUE THEN RETURN false; END IF;
 RETURN amc_acl.complete_verified_email(candidate);
END $$;
REVOKE ALL ON FUNCTION amc_acl.verify_email(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.verify_email(text) TO amc_runtime;

CREATE OR REPLACE FUNCTION amc_acl.accept_portal_invitation(invite text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE i public.portal_invitations%ROWTYPE; issuer_role text; actor text:=current_setting('amc.user_id',true);
BEGIN
 IF amc_acl.authenticated_actor() IS NOT TRUE THEN RETURN false; END IF;
 SELECT * INTO i FROM public.portal_invitations WHERE id=invite
 AND amc_acl.addressed_recipient(user_id,email) FOR UPDATE;
 IF NOT FOUND OR i.state<>'pending' OR i.expires_at<=clock_timestamp() THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT FROM public.users WHERE id=actor AND email=i.email AND verified_at IS NOT NULL)
 OR NOT EXISTS(SELECT FROM public.users WHERE id=i.invited_by AND verified_at IS NOT NULL) THEN RETURN false; END IF;
 SELECT role INTO issuer_role FROM public.memberships WHERE tenant_id=i.tenant_id AND user_id=i.invited_by FOR SHARE;
 IF NOT FOUND OR issuer_role NOT IN ('owner','admin') OR (i.role='admin' AND issuer_role<>'owner') THEN RETURN false; END IF;
 -- The composite client/brand/campaign FKs and invited_scope are enforced for the
 -- frozen row and again on the grant. No scope or role comes from the recipient.
 INSERT INTO public.memberships(tenant_id,user_id,role,client_id) VALUES(i.tenant_id,actor,i.role,i.client_id)
 ON CONFLICT(tenant_id,user_id) DO NOTHING;
 IF NOT FOUND THEN RETURN false; END IF;
 IF i.role='client_viewer' THEN
   INSERT INTO public.portal_grants(tenant_id,user_id,client_id,brand_id,campaign_id,can_comment,can_decide)
   VALUES(i.tenant_id,actor,i.client_id,i.brand_id,i.campaign_id,i.can_comment,i.can_decide);
 END IF;
 UPDATE public.portal_invitations SET state='accepted',user_id=actor WHERE id=i.id;
 INSERT INTO public.audit_events(id,tenant_id,user_id,event,subject_id,details,occurred_at)
 VALUES(gen_random_uuid()::text,i.tenant_id,actor,'portal.invitation_accepted',i.id,json_build_object('role',i.role),clock_timestamp());
 RETURN true;
END $$;
