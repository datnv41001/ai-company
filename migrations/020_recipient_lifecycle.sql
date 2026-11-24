-- Address is the stable serialization key even before a user account exists.
CREATE FUNCTION amc_acl.lock_recipient(t text, address text) RETURNS void
LANGUAGE plpgsql VOLATILE STRICT SET search_path=pg_catalog AS $$
BEGIN
 -- Each query following acquisition must see the last holder's commit.
 IF current_setting('transaction_isolation') <> 'read committed' THEN
   RAISE EXCEPTION 'Recipient changes require READ COMMITTED' USING ERRCODE='25000';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(length(t)::text || ':' || t || lower(btrim(address)),20));
END $$;
REVOKE ALL ON FUNCTION amc_acl.lock_recipient(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.lock_recipient(text,text) TO amc_runtime;

CREATE FUNCTION amc_acl.guard_offer_insert() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF amc_acl.authenticated_actor() IS NOT TRUE OR coalesce(amc_acl.member_role(NEW.tenant_id),'') NOT IN ('admin','owner') THEN
   RAISE insufficient_privilege;
 END IF;
 PERFORM amc_acl.lock_recipient(NEW.tenant_id,NEW.email);
 IF EXISTS (SELECT FROM public.memberships m JOIN public.users u ON m.user_id=u.id
            WHERE m.tenant_id=NEW.tenant_id AND lower(u.email)=lower(btrim(NEW.email))) THEN
   RAISE EXCEPTION 'Recipient already belongs to workspace' USING ERRCODE='23505';
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_acl.guard_offer_insert() FROM PUBLIC;
CREATE TRIGGER recipient_guard BEFORE INSERT ON public.portal_invitations
 FOR EACH ROW WHEN (NEW.state='pending') EXECUTE FUNCTION amc_acl.guard_offer_insert();

-- Preserve the v19 consent implementation behind a fenced entry point.
ALTER FUNCTION amc_acl.accept_portal_invitation(text) RENAME TO consume_locked_invitation;
REVOKE ALL ON FUNCTION amc_acl.consume_locked_invitation(text) FROM PUBLIC,amc_runtime;
CREATE FUNCTION amc_acl.accept_portal_invitation(invite text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE recipient public.portal_invitations%ROWTYPE;
BEGIN
 IF amc_acl.authenticated_actor() IS NOT TRUE THEN RETURN false; END IF;
 SELECT * INTO recipient FROM public.portal_invitations WHERE id=invite
 AND amc_acl.addressed_recipient(user_id,email) AND state='pending';
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM amc_acl.lock_recipient(recipient.tenant_id,recipient.email);
 IF EXISTS(SELECT FROM public.memberships WHERE tenant_id=recipient.tenant_id
           AND user_id=current_setting('amc.user_id',true)) THEN RETURN false; END IF;
 RETURN amc_acl.consume_locked_invitation(invite);
END $$;
REVOKE ALL ON FUNCTION amc_acl.accept_portal_invitation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.accept_portal_invitation(text) TO amc_runtime;

-- Direct DELETE would take a membership row lock before reaching a row trigger.
-- Expose one ordered command, including cleanup and audit, to every runtime writer.
REVOKE DELETE ON public.memberships FROM amc_runtime;
CREATE POLICY owner_close_offer_read ON public.portal_invitations FOR SELECT TO CURRENT_USER
 USING (amc_acl.authenticated_actor() AND amc_acl.member_role(tenant_id) IN ('admin','owner'));
CREATE POLICY owner_close_offer_update ON public.portal_invitations FOR UPDATE TO CURRENT_USER
 USING (state='pending' AND amc_acl.authenticated_actor() AND amc_acl.member_role(tenant_id) IN ('admin','owner'))
 WITH CHECK (state='revoked' AND amc_acl.authenticated_actor() AND amc_acl.member_role(tenant_id) IN ('admin','owner'));
CREATE POLICY owner_scope_revoke_audit ON public.audit_events FOR INSERT TO CURRENT_USER
 WITH CHECK (event='member.client_scope_revoked' AND user_id=current_setting('amc.user_id',true)
 AND amc_acl.authenticated_actor() AND amc_acl.member_role(tenant_id) IN ('admin','owner'));

CREATE FUNCTION amc_acl.revoke_client_member(t text, uid text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE address text; client text; actor text:=current_setting('amc.user_id',true);
BEGIN
 IF amc_acl.authenticated_actor() IS NOT TRUE OR coalesce(amc_acl.member_role(t),'') NOT IN ('admin','owner')
 THEN RETURN false; END IF;
 SELECT u.email INTO address FROM public.users u JOIN public.memberships m ON m.user_id=u.id
 WHERE m.tenant_id=t AND m.user_id=uid AND m.role='client_viewer';
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM amc_acl.lock_recipient(t,address);
 PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=actor AND role IN ('admin','owner') FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 DELETE FROM public.memberships WHERE tenant_id=t AND user_id=uid AND role='client_viewer' RETURNING client_id INTO client;
 IF NOT FOUND THEN RETURN false; END IF;
 UPDATE public.portal_invitations SET state='revoked' WHERE tenant_id=t AND state='pending'
 AND (user_id=uid OR lower(btrim(email))=lower(btrim(address)));
 INSERT INTO public.audit_events(id,tenant_id,user_id,event,subject_id,details,occurred_at)
 VALUES(gen_random_uuid()::text,t,actor,'member.client_scope_revoked',uid,json_build_object('client_id',client),clock_timestamp());
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION amc_acl.revoke_client_member(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.revoke_client_member(text,text) TO amc_runtime;
