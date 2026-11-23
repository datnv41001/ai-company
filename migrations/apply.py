"""Apply reviewed SQL atomically on a dedicated AMC PostgreSQL database."""
import os
from pathlib import Path

import psycopg
from psycopg import sql

HERE = Path(__file__).resolve().parent
BASE = {"tenants", "users", "memberships", "clients", "brands", "campaigns",
        "work_tasks", "deliverables", "action_requests", "audit_events"}


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
        if conn.execute("SELECT 1 FROM amc_schema_versions WHERE version=2").fetchone():
            return
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


if __name__ == "__main__":
    migrate(os.environ["AMC_MIGRATION_DSN"], os.getenv("AMC_RUNTIME_PASSWORD"))
    print("AMC schema version 2 ready")
