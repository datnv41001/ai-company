"""Compatibility checks for the joined C2 business module and A1 device issuer."""
import hashlib
import hmac
import os

from . import claim_display, knowledge_commerce

# Prior configuration from the reviewed standalone A1 v23 publisher.
A1_COMMERCIAL = "b76ebcda230c5ca15fe26fb3199fb25111b1fe5acd0b3274cffa80d223545418"


def material_from_environment():
    names = ("AMC_QUOTA_KEY", "AMC_DB_PROOF_KEY", "AMC_SESSION_GENERATION")
    try:
        keys = tuple(bytes.fromhex(os.environ[name]) for name in names)
    except (KeyError, ValueError):
        raise ValueError("Provide the three authoritative 32-byte identity keys") from None
    if any(len(k) != 32 for k in keys) or len(set(keys)) != 3 or any(k.hex() == os.getenv("JWT_SECRET", "").lower() for k in keys):
        raise ValueError("Provide independent quota, database proof and restore keys")
    return keys


def verify_stored_keys(conn, material):
    quota, proof, generation = material
    row = conn.execute("""SELECT k.secret,s.quota_fingerprint,s.restore_generation
        FROM amc_acl.identity_key k JOIN amc_acl.session_keys s USING(singleton) WHERE k.singleton""").fetchone()
    if (not row or not hmac.compare_digest(bytes(row[0]), proof)
            or row[1:] != (hashlib.sha256(quota).hexdigest(), hashlib.sha256(generation).hexdigest())):
        raise ValueError("Authoritative identity keys differ from the publisher configuration")


def check_commercial_input(conn):
    row = conn.execute("SELECT prosrc FROM pg_proc WHERE oid=to_regprocedure(%s)", (knowledge_commerce.SIGNATURE,)).fetchone()
    if row:
        # Both reviewed installers wrap the SQL with one literal space on either side.
        body = row[0]
        actual = hashlib.sha256(body[1:-1].encode()).hexdigest()
        if not (body.startswith(" ") and body.endswith(" ") and actual in {knowledge_commerce.RULE_DIGEST, A1_COMMERCIAL}):
            raise ValueError("Unrecognized commercial decision body; restore the matching publisher")


def predicate_current(signature, digest):
    # Verify the actual pg_proc definition, effective ACL and safe resolution path.
    return f"""SELECT EXISTS(SELECT FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang
        WHERE p.oid=to_regprocedure('{signature}') AND p.prosecdef AND p.provolatile='s' AND l.lanname='sql'
        AND p.proconfig=ARRAY['search_path=pg_catalog'] AND left(p.prosrc,1)=' ' AND right(p.prosrc,1)=' '
        AND encode(sha256(convert_to(substring(p.prosrc FROM 2 FOR length(p.prosrc)-2),'UTF8')),'hex')='{digest}'
        AND obj_description(p.oid,'pg_proc')='{digest}' AND has_function_privilege('amc_runtime',p.oid,'EXECUTE')
        AND NOT EXISTS(SELECT FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
                       WHERE a.grantee=0 AND a.privilege_type='EXECUTE'))"""


COMMERCIAL_CURRENT = predicate_current(knowledge_commerce.SIGNATURE, knowledge_commerce.RULE_DIGEST)
DESK_CURRENT = predicate_current(claim_display.SIGNATURE, claim_display.DIGEST)


def check_capabilities(conn):
    if not conn.execute(COMMERCIAL_CURRENT).fetchone()[0] or not conn.execute(DESK_CURRENT).fetchone()[0]:
        raise ValueError("Combined commercial or claim-display capability differs from its reviewed definition")
