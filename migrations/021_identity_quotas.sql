-- Only the migration owner can read identifiers and counters. API workers can
-- consume a slot, but cannot reset an active window or choose a larger limit.
CREATE TABLE amc_acl.quota_policy (
    action text NOT NULL, dimension text NOT NULL,
    capacity integer NOT NULL CHECK(capacity>0), seconds integer NOT NULL CHECK(seconds>0),
    PRIMARY KEY(action,dimension)
);
CREATE TABLE amc_acl.identity_windows (
    digest text PRIMARY KEY, action text NOT NULL, dimension text NOT NULL,
    until_epoch bigint NOT NULL, used integer NOT NULL, denied bigint NOT NULL DEFAULT 0
);
CREATE INDEX identity_windows_expiry ON amc_acl.identity_windows(until_epoch);

CREATE FUNCTION amc_acl.consume_identity_quota(operation text, subjects jsonb) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE spec record; stamp bigint; cooldown integer := 0; cap_count integer; submitted integer;
BEGIN
 IF current_setting('transaction_isolation') <> 'read committed' THEN
   RAISE EXCEPTION 'Identity admission requires READ COMMITTED';
 END IF;
 IF jsonb_typeof(subjects) IS DISTINCT FROM 'object' THEN RAISE invalid_parameter_value; END IF;
 SELECT count(*) INTO cap_count FROM amc_acl.quota_policy WHERE action=operation;
 SELECT count(*) INTO submitted FROM jsonb_object_keys(subjects);
 IF cap_count=0 OR submitted<>cap_count OR EXISTS (
     SELECT FROM amc_acl.quota_policy WHERE action=operation AND
     (NOT subjects ? dimension OR coalesce(subjects->>dimension,'') !~ '^[0-9a-f]{64}$')
 ) THEN RAISE invalid_parameter_value; END IF;
 -- All dimensions are checked before admission. Denied traffic never pushes
 -- the deadline back and cannot create a new address row for a saturated origin.
 FOR spec IN SELECT value FROM jsonb_each_text(subjects) ORDER BY value LOOP
   PERFORM pg_advisory_xact_lock(hashtextextended(spec.value,21));
 END LOOP;
 stamp := floor(extract(epoch FROM clock_timestamp()))::bigint;
 SELECT coalesce(max(w.until_epoch-stamp),0) INTO cooldown
 FROM amc_acl.quota_policy p JOIN amc_acl.identity_windows w ON w.digest=subjects->>p.dimension
 WHERE p.action=operation AND w.until_epoch>stamp AND w.used>=p.capacity;
 IF cooldown>0 THEN
   UPDATE amc_acl.identity_windows w SET denied=w.denied+1 FROM amc_acl.quota_policy p
   WHERE p.action=operation AND w.digest=subjects->>p.dimension AND w.until_epoch>stamp AND w.used>=p.capacity;
 ELSE
   INSERT INTO amc_acl.identity_windows AS w(digest,action,dimension,until_epoch,used,denied)
   SELECT subjects->>dimension,action,dimension,stamp+seconds,1,0 FROM amc_acl.quota_policy WHERE action=operation
   ON CONFLICT(digest) DO UPDATE SET
     used=CASE WHEN w.until_epoch<=stamp THEN 1 ELSE w.used+1 END,
     until_epoch=CASE WHEN w.until_epoch<=stamp THEN excluded.until_epoch ELSE w.until_epoch END,
     denied=CASE WHEN w.until_epoch<=stamp THEN 0 ELSE w.denied END;
 END IF;
 DELETE FROM amc_acl.identity_windows WHERE digest IN (
   SELECT digest FROM amc_acl.identity_windows WHERE until_epoch<stamp-86400
   ORDER BY until_epoch LIMIT 64 FOR UPDATE SKIP LOCKED);
 RETURN cooldown;
END $$;
REVOKE ALL ON FUNCTION amc_acl.consume_identity_quota(text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.consume_identity_quota(text,jsonb) TO amc_runtime;
