ALTER TABLE public.users ADD COLUMN credential_epoch integer NOT NULL DEFAULT 1;
CREATE FUNCTION amc_acl.bump_credential_epoch() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NEW.password_hash IS DISTINCT FROM OLD.password_hash THEN
   PERFORM pg_advisory_xact_lock(hashtextextended(OLD.id,23001));
   NEW.credential_epoch := OLD.credential_epoch+1;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER account_password_epoch BEFORE UPDATE OF password_hash ON public.users
 FOR EACH ROW EXECUTE FUNCTION amc_acl.bump_credential_epoch();

CREATE TABLE public.device_sessions (
 id varchar(36) PRIMARY KEY, user_id varchar(36) NOT NULL REFERENCES public.users(id),
 epoch integer NOT NULL CHECK(epoch>0), credential_epoch integer NOT NULL CHECK(credential_epoch>0),
 generation varchar(64) NOT NULL, current_digest varchar(64) NOT NULL, csrf_digest varchar(64) NOT NULL,
 device varchar(40) NOT NULL, created bigint NOT NULL, seen bigint NOT NULL, reauthed bigint NOT NULL,
 revoked boolean NOT NULL DEFAULT false
);
CREATE INDEX ix_device_sessions_user_id ON public.device_sessions(user_id);
CREATE TABLE public.used_refresh_grants (
 session_id varchar(36) NOT NULL REFERENCES public.device_sessions(id) ON DELETE CASCADE,
 digest varchar(64) NOT NULL, PRIMARY KEY(session_id,digest)
);
ALTER TABLE public.device_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.used_refresh_grants ENABLE ROW LEVEL SECURITY;
CREATE POLICY device_actor ON public.device_sessions TO amc_runtime USING (
 amc_acl.authenticated_actor() AND user_id=current_setting('amc.user_id',true));
CREATE POLICY grant_actor ON public.used_refresh_grants TO amc_runtime USING (
 EXISTS (SELECT FROM public.device_sessions s WHERE s.id=session_id));
REVOKE ALL ON public.device_sessions,public.used_refresh_grants FROM PUBLIC,amc_runtime;
GRANT SELECT,INSERT ON public.device_sessions,public.used_refresh_grants TO amc_runtime;
GRANT UPDATE (epoch,current_digest,seen,reauthed,revoked) ON public.device_sessions TO amc_runtime;
CREATE TABLE amc_acl.session_keys (
 singleton boolean PRIMARY KEY CHECK(singleton), quota_fingerprint text NOT NULL, restore_generation text NOT NULL
);
CREATE FUNCTION amc_acl.session_config() RETURNS TABLE(quota_fingerprint text,restore_generation text)
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT quota_fingerprint,restore_generation FROM amc_acl.session_keys WHERE singleton $$;
REVOKE ALL ON FUNCTION amc_acl.session_config() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.session_config() TO amc_runtime;
