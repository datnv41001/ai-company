"""Apply reviewed SQL atomically on a dedicated AMC PostgreSQL database."""
import hashlib
import hmac
import json
import os
import sys

from psycopg.types.json import Jsonb
from pathlib import Path

import psycopg
from psycopg import sql

# Also support the Docker entry point: python migrations/apply.py.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.registry_compatibility import validate_manifest  # noqa: E402
from migrations.knowledge_commerce import RULE_IS_CURRENT, install as install_knowledge_commerce  # noqa: E402

HERE = Path(__file__).resolve().parent
BASE = {"tenants", "users", "memberships", "clients", "brands", "campaigns",
        "work_tasks", "deliverables", "action_requests", "audit_events"}


def publish_registry(conn, manifest):
    """The migration publisher owns definitions. Identical imports may be replayed."""
    with conn.transaction():
        _publish_registry(conn, manifest)


def _publish_registry(conn, manifest):
    validate_manifest(manifest)
    for contract in manifest["contracts"].values():
        for kind, key, version in (("role", "role_id", "contract_version"), ("skill", "skill_id", "skill_version")):
            identity = (kind, contract[key], contract[version])
            definition = contract if kind == "skill" else {k:v for k,v in contract.items() if k not in ("adapter","skill_id","skill_version","adapter_digest")}
            conn.execute("INSERT INTO amc_ops.registry_versions VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING", (*identity, Jsonb(definition)))
            existing = conn.execute("SELECT definition FROM amc_ops.registry_versions WHERE (kind,id,version)=(%s,%s,%s)", identity).fetchone()[0]
            if existing != definition:
                raise ValueError(f"Immutable {kind} version changed")
    key = f"{manifest['workflow_id']}@{manifest['workflow_version']}"
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    conn.execute("INSERT INTO amc_ops.registry_releases(workflow,digest,manifest) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                 (key,digest,Jsonb(manifest)))
    if conn.execute("SELECT digest FROM amc_ops.registry_releases WHERE workflow=%s",(key,)).fetchone() != (digest,):
        raise ValueError("Immutable workflow version changed")


def migrate(dsn: str, runtime_password: str | None = None):
    with psycopg.connect(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(4197832741)")
        conn.execute("SET LOCAL search_path = public, pg_catalog")
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname='amc_runtime'").fetchone()
        if not exists:
            if not runtime_password:
                raise ValueError("Set AMC_RUNTIME_PASSWORD for the initial application login")
            conn.execute(sql.SQL("CREATE ROLE amc_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD {}")
                         .format(sql.Literal(runtime_password)))
        unsafe = conn.execute("""SELECT rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb
            OR rolreplication OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member=r.oid)
            FROM pg_roles r WHERE rolname='amc_runtime'""").fetchone()[0]
        if unsafe:
            raise ValueError("amc_runtime must be an unprivileged role without inherited roles")
        conn.execute("CREATE TABLE IF NOT EXISTS amc_schema_versions (version int PRIMARY KEY)")
        versions = {row[0] for row in conn.execute("SELECT version FROM amc_schema_versions")}
        if versions - set(range(2, 23)):
            raise ValueError("Unknown schema version; use its matching application revision")
        if 16 in versions and 15 not in versions:
            raise ValueError("Isolated schema v16 is missing migration 015; restore a pre-016 backup before upgrading")
        if versions and versions != set(range(2, max(versions) + 1)):
            raise ValueError("Incomplete migration history; restore a consistent backup before upgrading")
        if 22 in versions:
            if not conn.execute(RULE_IS_CURRENT).fetchone()[0]:
                install_knowledge_commerce(conn)
            return
        if 2 not in versions:
            tables = {row[0] for row in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'amc_schema_versions'")}
            if not tables:
                conn.execute((HERE / "000_starter_schema.sql").read_text(encoding="utf-8"))
            elif tables != BASE:
                raise ValueError("Expected an empty database or the ten tables of the reviewed starter")
            conn.execute((HERE / "001_correct_content_role.sql").read_text(encoding="utf-8"))
            conn.execute((HERE / "002_client_isolation.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (2)")
            conn.execute("GRANT SELECT ON amc_schema_versions TO amc_runtime")
        if 3 not in versions:
            for migration in ("003_delivery_tables.sql", "003_delivery_policies.sql"):
                conn.execute((HERE / migration).read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (3)")
        if 4 not in versions:
            conn.execute((HERE / "004_review_operations.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (4)")
        if 5 not in versions:
            conn.execute((HERE / "005_workforce.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (5)")
        if 6 not in versions:
            conn.execute((HERE / "006_workforce_authority.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (6)")
        if 7 not in versions:
            conn.execute((HERE / "007_revision_qa.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (7)")
        if 8 not in versions:
            conn.execute((HERE / "008_qa_revision.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (8)")
        if 9 not in versions:
            conn.execute((HERE / "009_company_operations.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (9)")
        if 10 not in versions:
            conn.execute((HERE / "010_run_reconciliation.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (10)")
        if 11 not in versions:
            conn.execute((HERE / "011_workflow_dag.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (11)")
        if 12 not in versions:
            conn.execute((HERE / "012_dynamic_plan.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (12)")
        if 13 not in versions:
            conn.execute((HERE / "013_node_leases.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (13)")
        if 14 not in versions:
            conn.execute((HERE / "014_workflow_registry.sql").read_text(encoding="utf-8"))
            publish_registry(conn, json.loads((HERE.parent / "catalog/landing-seo-v1.json").read_text(encoding="utf-8")))
            conn.execute("INSERT INTO amc_schema_versions VALUES (14)")
        if 15 not in versions:
            conn.execute((HERE / "015_registry_outputs.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (15)")
        if 16 not in versions:
            conn.execute((HERE / "016_scheduler_diagnostics.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (16)")
        if 17 not in versions:
            secret = os.environ.get("JWT_SECRET", "")
            if len(secret) < 32 or secret.startswith(("REPLACE-", "LOCAL_ONLY")):
                raise ValueError("Set the same strong JWT_SECRET on the migration publisher and API")
            conn.execute((HERE / "017_verified_identity.sql").read_text(encoding="utf-8"))
            key = hmac.digest(secret.encode(), b"amc-identity-v17", "sha256")
            conn.execute("INSERT INTO amc_acl.identity_key VALUES(true,%s)", (key,))
            conn.execute("INSERT INTO amc_schema_versions VALUES (17)")
        if 18 not in versions:
            conn.execute((HERE / "018_invitation_scope_names.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (18)")
        if 19 not in versions:
            conn.execute((HERE / "019_onboarding.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (19)")
        if 20 not in versions:
            conn.execute((HERE / "020_recipient_lifecycle.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (20)")
        if 21 not in versions:
            conn.execute((HERE / "021_identity_quotas.sql").read_text(encoding="utf-8"))
            rules = json.loads((HERE / "021_quota_policy.json").read_text(encoding="utf-8"))
            for action, dimensions in rules.items():
                for dimension, (capacity, seconds) in dimensions.items():
                    conn.execute("INSERT INTO amc_acl.quota_policy VALUES(%s,%s,%s,%s)",(action,dimension,capacity,seconds))
            conn.execute("INSERT INTO amc_schema_versions VALUES (21)")
        conn.execute((HERE / "022_business_knowledge.sql").read_text(encoding="utf-8"))
        install_knowledge_commerce(conn)
        conn.execute("INSERT INTO amc_schema_versions VALUES (22)")



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish-registry", type=Path, help="Import a reviewed release using the migration identity")
    args = parser.parse_args()
    if args.publish_registry:
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as conn:
            publish_registry(conn, json.loads(args.publish_registry.read_text(encoding="utf-8")))
    else:
        migrate(os.environ["AMC_MIGRATION_DSN"], os.getenv("AMC_RUNTIME_PASSWORD"))
    print("AMC schema version 22 ready")
