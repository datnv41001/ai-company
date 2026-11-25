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
    migrate_historical_fixture("923a89050325ff05a6980f1ebeb392da367bb140")
    with psycopg.connect(dsn) as db:
        assert db.execute("SELECT version FROM amc_business.versions ORDER BY version").fetchall() == [(1,)]
        payload = {"name": {"value": "Synthetic company", "revision": 1}}
        db.execute(
            """INSERT INTO public.business_workspace_records
            (id,tenant_id,client_id,scope,kind,revision,actor,command_key,request_digest,payload,created_at)
            VALUES('w1','t','c','company','company',1,'fixture-author','one',%s,%s,now())""",
            (digest(canonical(payload)), Jsonb(payload)),
        )
        workspace_before = db.execute("SELECT to_jsonb(w) FROM business_workspace_records w").fetchall()
    with pytest.raises(RuntimeError):
        prepare_database(engine)
    migrate_historical_fixture("727a344be4c387a612a74c69fafdac8b966f1fa2")
    with psycopg.connect(dsn) as db:
        assert db.execute("SELECT version FROM amc_business.versions ORDER BY version").fetchall() == [(1,), (2,)]
        old_objective = {"name":"Local company target","owner":"Brand lead","level":"company","parent":None,"campaign_id":None}
        db.execute(
            """INSERT INTO knowledge_revisions(subject,kind,revision,data,digest,author,created_at,id,tenant_id,client_id,brand_id,visibility)
            VALUES('local-goal','objective',1,%s,%s,'fixture-author',now(),'legacy-goal','t','c','b','internal')""",
            (Jsonb(old_objective), digest(canonical(old_objective))),
        )
        before = db.execute("SELECT to_jsonb(k) FROM knowledge_revisions k ORDER BY id").fetchall()
    with pytest.raises(RuntimeError):
        prepare_database(engine)
    migrate(dsn)
    migrate(dsn)
    prepare_database(engine)
    with psycopg.connect(dsn) as db:
        assert db.execute("SELECT version FROM amc_business.versions ORDER BY version").fetchall() == [(1,), (2,), (3,)]
        assert db.execute("SELECT version FROM amc_schema_versions ORDER BY version").fetchall() == core
        assert db.execute("SELECT to_jsonb(k) FROM knowledge_revisions k ORDER BY id").fetchall() == before
        assert db.execute("SELECT count(*) FROM business_company_objectives").fetchone()==(0,)
        assert db.execute("SELECT to_jsonb(w) FROM business_workspace_records w").fetchall() == workspace_before
        db.execute("INSERT INTO amc_business.versions VALUES(99)")
    with pytest.raises(ValueError, match="Unsupported business workspace"):
        migrate(dsn)
    with pytest.raises(RuntimeError, match="compatible business workspace"):
        prepare_database(engine)
    engine.dispose()
    print("PASS core v22, workspace v1 and catalog v2 to workspace v3. Repeated publication preserved legacy objectives, company profile and core markers.")


if __name__ == "__main__":
    verify()
