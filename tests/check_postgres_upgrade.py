"""Exercise upgrading a populated starter. Requires an empty local amc_test* database."""
import os
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine, text

from app.database import prepare_database
from migrations.apply import migrate

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def verify():
    dsn = os.environ["AMC_MIGRATION_DSN"]
    runtime = create_engine(os.environ["DATABASE_URL"])
    with psycopg.connect(dsn) as conn:
        assert conn.info.host in ("127.0.0.1", "localhost", "::1")
        assert conn.info.dbname.startswith("amc_test")
        assert runtime.url.database == conn.info.dbname
        assert not conn.execute("SELECT 1 FROM pg_tables WHERE schemaname='public'").fetchone()
        conn.execute((MIGRATIONS / "000_starter_schema.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO tenants VALUES ('agency','Existing agency','agency',now())")
        conn.execute("INSERT INTO users VALUES ('alice','synthetic@example.com','unused',now())")
        conn.execute("INSERT INTO memberships VALUES ('agency','alice','viewer')")
        conn.execute("INSERT INTO clients VALUES ('a','agency','Client A','Retail'), ('b','agency','Client B','Retail')")
    migrate(dsn, os.environ.get("AMC_RUNTIME_PASSWORD"))
    migrate(dsn)
    prepare_database(runtime)
    privileged = create_engine("postgresql+psycopg://", creator=lambda: psycopg.connect(dsn))
    with pytest.raises(RuntimeError, match="unprivileged"):
        prepare_database(privileged)
    privileged.dispose()
    with runtime.connect() as c:
        def identify():
            c.execute(text("SELECT set_config('amc.user_id','alice',true),set_config('amc.tenant_id','agency',true)"))
        identify()
        assert set(c.scalars(text("SELECT id FROM clients"))) == {"a", "b"}
        c.rollback()
        with psycopg.connect(dsn) as owner:
            owner.execute("UPDATE memberships SET role='client_viewer',client_id='a' WHERE user_id='alice'")
        identify()
        assert set(c.scalars(text("SELECT id FROM clients"))) == {"a"}
        assert set(c.scalars(text("SELECT version FROM amc_schema_versions"))) == {2}
    runtime.dispose()
    print("PASS: populated v1 database, repeated migration, privileged API login refused, internal grant retained, mapped client isolated")


if __name__ == "__main__":
    verify()
