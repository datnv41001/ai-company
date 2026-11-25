"""Apply workspace line 1 to the exact reviewed core-v22 publisher on an empty synthetic database."""

import os

import psycopg
from psycopg.types.json import Jsonb
import pytest
from sqlalchemy import create_engine

from app.database import prepare_database
from app.knowledge_store import canonical, digest
from check_postgres_upgrade import migrate_historical_fixture
from migrations.apply import migrate


def verify():
    dsn = os.environ["AMC_MIGRATION_DSN"]
    engine = create_engine(os.environ["DATABASE_URL"])
    with psycopg.connect(dsn) as db:
        assert db.info.host in ("127.0.0.1", "localhost", "::1") and db.info.dbname.startswith("amc_test")
        assert db.execute("SELECT to_regclass('public.amc_schema_versions')").fetchone() == (None,)
    migrate_historical_fixture("c847f910b88c243932f67617c248bd223617b51b")
    with psycopg.connect(dsn) as db:
        assert db.execute("SELECT max(version) FROM amc_schema_versions").fetchone() == (22,)
        assert db.execute("SELECT to_regclass('amc_business.versions')").fetchone() == (None,)
        db.execute("INSERT INTO tenants(id,name,mode,created_at) VALUES('t','Synthetic tenant','agency',now())")
        db.execute("INSERT INTO clients(id,tenant_id,name,sector) VALUES('c','t','Synthetic company','Ceramics')")
        db.execute("INSERT INTO brands(id,tenant_id,client_id,name,brand_guidelines,product_truth) VALUES('b','t','c','Tiles','','')")
        data = {"name": "Pre-existing brand profile", "sells": "Tiles", "audience": "Builders", "goal": "Inquiries"}
        db.execute(
            """INSERT INTO knowledge_revisions(subject,kind,revision,data,digest,author,created_at,id,tenant_id,client_id,brand_id,visibility)
                      VALUES('profile','profile',1,%s,%s,'fixture-author',now(),'legacy-profile','t','c','b','internal')""",
            (Jsonb(data), digest(canonical(data))),
        )
        before = db.execute("SELECT to_jsonb(k) FROM knowledge_revisions k").fetchall()
        core = db.execute("SELECT version FROM amc_schema_versions ORDER BY version").fetchall()
    with pytest.raises(RuntimeError):
        prepare_database(engine)
    migrate(dsn)
    migrate(dsn)
    prepare_database(engine)
    with psycopg.connect(dsn) as db:
        assert db.execute("SELECT version FROM amc_business.versions").fetchall() == [(1,)]
        assert db.execute("SELECT version FROM amc_schema_versions ORDER BY version").fetchall() == core
        assert db.execute("SELECT to_jsonb(k) FROM knowledge_revisions k").fetchall() == before
        assert db.execute("SELECT count(*) FROM business_workspace_records").fetchone() == (0,)
        db.execute("INSERT INTO amc_business.versions VALUES(99)")
    with pytest.raises(ValueError, match="Unsupported business workspace"):
        migrate(dsn)
    with pytest.raises(RuntimeError, match="compatible business workspace"):
        prepare_database(engine)
    engine.dispose()
    print("PASS core v22 at c847f910 to business workspace v1, repeat publication preserved populated C1 history and core markers; unsupported module refused")


if __name__ == "__main__":
    verify()
