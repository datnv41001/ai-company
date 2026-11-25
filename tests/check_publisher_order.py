"""Characterize two pinned AMC development publishers on disposable loopback PostgreSQL databases."""
import argparse
from contextlib import contextmanager
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tarfile
import tempfile

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.types.json import Jsonb

RULE = "amc_acl.knowledge_commercial_conflict(text,text,text,text,text,timestamptz)"
DESK = "amc_business.claim_display_current(text,text,text,text,text)"
CATALOG = "amc_business.catalog_conflict(text,text,text,text,text,text,text,boolean)"
SCHEMAS = ["public", "amc_acl", "amc_ops", "amc_business"]
LOCAL = {"127.0.0.1", "::1", "localhost"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def maintenance():
    cfg = conninfo_to_dict(os.environ.get("AMC_ORDER_ADMIN_DSN", ""))
    require(not (cfg.keys() - {"host", "hostaddr", "port", "user", "dbname", "password", "sslmode",
                               "connect_timeout"}), "Pass explicit direct loopback connection parameters")
    require(cfg.get("host") in LOCAL and cfg.get("dbname") == "postgres",
            "Provide a loopback maintenance DSN for the synthetic postgres database")
    addr = cfg.get("hostaddr", "::1" if cfg["host"] == "::1" else "127.0.0.1")
    require(addr in {"127.0.0.1", "::1"}, "Loopback hostaddr required")
    require(not any(k.startswith("PG") and k != "PGPASSWORD" for k in os.environ),
            "Run with explicit connection parameters and no inherited libpq configuration")
    return make_conninfo(**(cfg | {"hostaddr": addr, "connect_timeout": 5}))


def command(argv, project, env):
    return subprocess.run(argv, cwd=project, env=env, capture_output=True, timeout=120)


def archive(checkout, sha, target, env):
    require(re.fullmatch("[0-9a-f]{40}", sha), "Expected full lowercase Git commit pin")
    head = command(["git", "rev-parse", "HEAD"], checkout, env)
    require(head.returncode == 0 and head.stdout.decode().strip() == sha, "Checkout HEAD differs from pin")
    packed = command(["git", "archive", "--format=tar", sha, "migrations", "catalog", "app",
                      "requirements.txt", "requirements-registry.txt"], checkout, env)
    require(packed.returncode == 0, "Cannot archive pinned migration inputs")
    target.mkdir()
    with tarfile.open(fileobj=io.BytesIO(packed.stdout)) as bundle:
        bundle.extractall(target, filter="data")
    rule = command([sys.executable, "-c", "from migrations.knowledge_commerce import RULE_DIGEST; print(RULE_DIGEST)"],
                   target, env)
    pin = rule.stdout.decode().strip()
    require(rule.returncode == 0 and re.fullmatch("[0-9a-f]{64}", pin), "Cannot determine pinned rule digest")
    return pin


@contextmanager
def disposable(ctrl, admin):
    name = "amc_test_order_" + secrets.token_hex(12)
    ident = sql.Identifier(name)
    ctrl.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(ident))
    def owner():
        return ctrl.execute("SELECT oid, datdba FROM pg_database WHERE datname=%s", (name,)).fetchone()
    created = owner()
    try:
        yield make_conninfo(admin, dbname=name)
    finally:
        require(created is not None and owner() == created, "Disposable database identity changed")
        ctrl.execute(sql.SQL("DROP DATABASE {}").format(ident))


def apply(project, env, *, refuse=False):
    result = command([sys.executable, "-m", "migrations.apply"], project, env)
    if refuse:
        require(result.returncode and b"Unknown schema version" in result.stderr, "Expected explicit schema refusal")
    else:
        require(result.returncode == 0, "Reviewed migration publisher failed in " + project.name)


def seed(db):
    db.execute("INSERT INTO tenants(id,name,mode,created_at) VALUES('t','Synthetic','agency',now())")
    db.execute("INSERT INTO clients(id,tenant_id,name,sector) VALUES('c','t','Synthetic','Ceramics')")
    payload = {"name": {"value": "Synthetic studio", "revision": 1}}
    request_digest = digest(json.dumps(payload, sort_keys=True).encode())
    db.execute("""INSERT INTO business_workspace_records
        (id,tenant_id,client_id,scope,kind,revision,actor,command_key,request_digest,payload,created_at)
        VALUES('r','t','c','company','company',1,'synthetic','one',%s,%s,now())""", (request_digest, Jsonb(payload)))


def fixture(db):
    rows = db.execute("SELECT to_jsonb(r)::text FROM business_workspace_records r ORDER BY id").fetchall()
    require(len(rows) == 1, "Expected one synthetic workspace record")
    return rows


def state(db, env, core, modules, rule):
    versions = [v for v, in db.execute("SELECT version FROM amc_schema_versions ORDER BY version")]
    require(versions == list(range(2, core + 1)), "Unexpected core migration ledger")
    exists = db.execute("SELECT to_regclass('amc_business.versions') IS NOT NULL").fetchone()[0]
    actual = [v for v, in db.execute("SELECT version FROM amc_business.versions ORDER BY version")] if exists else []
    require(actual == modules, "Unexpected business module ledger")
    installed, body = db.execute("""SELECT obj_description(to_regprocedure(%s),'pg_proc'),
        pg_get_functiondef(to_regprocedure(%s))""", (RULE, RULE)).fetchone()
    require(installed == rule, "Installed commercial rule differs from pinned publisher")
    proof = db.execute("SELECT secret FROM amc_acl.identity_key WHERE singleton").fetchone()[0]
    expected = hmac.digest(env["JWT_SECRET"].encode(), b"amc-identity-v17", "sha256")
    if core == 23:
        expected = bytes.fromhex(env["AMC_DB_PROOF_KEY"])
        markers = db.execute("SELECT quota_fingerprint,restore_generation FROM amc_acl.session_keys WHERE singleton").fetchone()
        require(markers == tuple(digest(bytes.fromhex(env[k])) for k in ("AMC_QUOTA_KEY", "AMC_SESSION_GENERATION")),
                "Quota or restore identity marker mismatched")
    require(hmac.compare_digest(bytes(proof), expected), "Unexpected signing key domain")
    return {"core": core, "amc_business": modules, "commercial_rule": installed, "commercial_sql": digest(body.encode())}


def capabilities(db):
    return [db.execute("""SELECT pg_get_functiondef(to_regprocedure(%s)),
        has_function_privilege('amc_runtime',to_regprocedure(%s),'execute')""", (sig, sig)).fetchone()
            for sig in (DESK, CATALOG)]


def fingerprint(db):
    """Fingerprint synthetic rows, relation grants/RLS, policies and routine bodies/ACLs."""
    acc = hashlib.sha256()
    def add(rows):
        for r in rows:
            acc.update(json.dumps(r, ensure_ascii=True, separators=(",", ":"), default=str).encode() + b"\n")
    relations = db.execute("""SELECT n.nspname,c.relname,c.relrowsecurity,c.relforcerowsecurity,c.relacl::text
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=ANY(%s) AND c.relkind='r' ORDER BY 1,2""", (SCHEMAS,)).fetchall()
    for schema, table, *attributes in relations:
        add([(schema, table, *attributes)])
        add(db.execute(sql.SQL("SELECT to_jsonb(r)::text FROM {} r ORDER BY 1").format(sql.Identifier(schema, table))))
    add(db.execute("""SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies
        WHERE schemaname=ANY(%s) ORDER BY 1,2,3""", (SCHEMAS,)))
    add(db.execute("""SELECT n.nspname,p.oid::regprocedure::text,pg_get_functiondef(p.oid),p.proacl::text,
        obj_description(p.oid,'pg_proc') FROM pg_proc p JOIN pg_namespace n ON p.pronamespace=n.oid
        WHERE n.nspname=ANY(%s) AND p.prokind IN ('f','p') ORDER BY 1,2""", (SCHEMAS,)))
    return acc.digest()


def rehearse(ctrl, admin, base_env, c2, a1, c2_pin, a1_pin, c2_first):
    with disposable(ctrl, admin) as dsn:
        jwt = secrets.token_hex(48)
        env = base_env | {"AMC_MIGRATION_DSN": dsn, "JWT_SECRET": jwt, "AMC_DB_PROOF_KEY": secrets.token_hex(32),
                          "AMC_QUOTA_KEY": hmac.digest(jwt.encode(), b"amc/identity-quota/v1", "sha256").hex(),
                          "AMC_SESSION_GENERATION": secrets.token_hex(32)}
        report = {"order": "C2 then A1" if c2_first else "A1 then C2"}
        if c2_first:
            apply(c2, env)
            with psycopg.connect(dsn) as db:
                seed(db)
                report["before"] = state(db, env, 22, [1, 2], c2_pin)
                old_fixture, old_caps = fixture(db), capabilities(db)
                require(all(body for body, grant in old_caps), "Missing protected C2 capability")
        apply(a1, env)
        with psycopg.connect(dsn) as db:
            report["after_a1"] = state(db, env, 23, [1, 2] if c2_first else [], a1_pin)
            if c2_first:
                require(fixture(db) == old_fixture and capabilities(db) == old_caps, "C2 row or desk/catalog predicate changed")
                require(report["before"]["commercial_sql"] != report["after_a1"]["commercial_sql"],
                        "Pinned publishers no longer replace distinct commercial rules; reassess integration gate")
                report["workspace_row_and_desk_catalog_definitions_grants_preserved"] = True
            before_retry = fingerprint(db)
        apply(a1, env)
        with psycopg.connect(dsn) as db:
            require(fingerprint(db) == before_retry, "Repeated A1 changed observed database state")
        apply(c2, env, refuse=True)
        with psycopg.connect(dsn) as db:
            require(fingerprint(db) == before_retry, "C2 refusal changed observed database state")
        return report | {"v23_identity_domains_checked": True, "a1_replay_unchanged": True,
                         "c2_refused_core23_observed_state_unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("c2", "identity"):
        parser.add_argument("--" + name + "-checkout", type=Path, required=True)
        parser.add_argument("--" + name + "-sha", required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    require(args.c2_checkout.resolve() != args.identity_checkout.resolve(), "Supply separate publisher checkouts")
    admin = maintenance()
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"}}
    env.update(APP_ENV="test", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    with tempfile.TemporaryDirectory(prefix="amc-order-") as tmp, psycopg.connect(admin, autocommit=True) as ctrl:
        login = ctrl.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='amc_runtime'").fetchone()
        require(login and login[0], "Start a loopback synthetic cluster with the standard unprivileged amc_runtime login")
        c2, a1 = Path(tmp) / "c2", Path(tmp) / "a1"
        c2_pin = archive(args.c2_checkout, args.c2_sha, c2, env)
        a1_pin = archive(args.identity_checkout, args.identity_sha, a1, env)
        require(c2_pin != a1_pin, "Publisher rule pins now coincide; update the characterization")
        cases = [rehearse(ctrl, admin, env, c2, a1, c2_pin, a1_pin, first) for first in (True, False)]
        result = {"c2_sha": args.c2_sha, "identity_sha": args.identity_sha, "postgres": ctrl.info.server_version,
                  "disposable_databases_removed": 2, "cases": cases}
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
