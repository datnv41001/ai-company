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

-- Obtain the address while the membership still exists. This function is also
-- used before taking its row lock, so normal commands always lock address first.
CREATE FUNCTION amc_acl.removal_address(t text, uid text) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT u.email FROM public.users u JOIN public.memberships m ON m.user_id=u.id
 WHERE m.tenant_id=t AND m.user_id=uid AND amc_acl.authenticated_actor()
 AND amc_acl.member_role(t) IN ('admin','owner')
$$;
REVOKE ALL ON FUNCTION amc_acl.removal_address(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.removal_address(text,text) TO amc_runtime;

CREATE FUNCTION amc_acl.close_member_offers() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE address text;
BEGIN
 SELECT amc_acl.removal_address(OLD.tenant_id,OLD.user_id) INTO address;
 IF address IS NULL THEN RAISE insufficient_privilege; END IF;
 PERFORM amc_acl.lock_recipient(OLD.tenant_id,address);
 UPDATE public.portal_invitations SET state='revoked' WHERE tenant_id=OLD.tenant_id
 AND state='pending' AND (user_id=OLD.user_id OR lower(btrim(email))=lower(btrim(address)));
 RETURN OLD;
END $$;
REVOKE ALL ON FUNCTION amc_acl.close_member_offers() FROM PUBLIC;
CREATE TRIGGER close_member_offers BEFORE DELETE ON public.memberships
 FOR EACH ROW WHEN (OLD.role='client_viewer') EXECUTE FUNCTION amc_acl.close_member_offers();
