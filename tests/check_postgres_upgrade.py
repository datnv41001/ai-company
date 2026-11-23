"""Exercise upgrading a populated starter. Requires an empty local amc_test* database."""
import os
import sys
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
        if "--from-v2" in sys.argv or "--from-v3" in sys.argv:
            conn.execute((MIGRATIONS / "002_client_isolation.sql").read_text(encoding="utf-8"))
            conn.execute("CREATE TABLE amc_schema_versions(version int PRIMARY KEY)")
            conn.execute("INSERT INTO amc_schema_versions VALUES (2)")
            conn.execute("GRANT SELECT ON amc_schema_versions TO amc_runtime")
            conn.execute("INSERT INTO users VALUES ('external','external@example.com','unused',now())")
            conn.execute("INSERT INTO memberships(tenant_id,user_id,role,client_id) VALUES ('agency','external','client_viewer','a')")
            conn.execute("INSERT INTO brands(id,tenant_id,client_id,name,brand_guidelines,product_truth) VALUES('br','agency','a','Brand','','')")
            conn.execute("INSERT INTO campaigns(id,tenant_id,brand_id,name,brief,objective,status) VALUES('ca','agency','br','Name','Brief','Goal','draft')")
            conn.execute("""INSERT INTO deliverables(id,tenant_id,campaign_id,title,content,status,created_by)
                         VALUES('doc','agency','ca','Internal','{}','draft','alice')""")
        if "--from-v3" in sys.argv:
            for file in ("003_delivery_tables.sql", "003_delivery_policies.sql"):
                conn.execute((MIGRATIONS / file).read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(3)")
            # V3 permitted rejection without a reason. Preserve the archived evidence verbatim.
            conn.execute("""INSERT INTO client_reviews(id,tenant_id,client_id,brand_id,campaign_id,deliverable_id,version,title,
                         preview,digest,requested_by,qa_by,created_at,expires_at) VALUES('rv','agency','a','br','ca','doc',1,
                         'Title','Preview',encode(sha256(convert_to('{"preview":"Preview","title":"Title"}','UTF8')),'hex'),
                         'alice','alice',now(),now()+interval '1 day')""")
            conn.execute("""INSERT INTO review_entries(id,tenant_id,review_id,digest,actor_id,kind,note,request_key,created_at)
                         SELECT 'entry','agency','rv',digest,'external','rejected','','legacy-key',now() FROM client_reviews WHERE id='rv'""")
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
        assert set(c.scalars(text("SELECT version FROM amc_schema_versions"))) == {2,3,4}
        if "--from-v2" in sys.argv or "--from-v3" in sys.argv:
            c.rollback()
            c.execute(text("SELECT set_config('amc.user_id','external',true),set_config('amc.tenant_id','agency',true)"))
            assert c.execute(text("SELECT client_id,can_comment,can_decide FROM portal_grants")).one() == ("a",False,False)
            for table in ("client_reviews","review_entries","deliverables"):
                expected = int("--from-v3" in sys.argv and table in ("client_reviews", "review_entries"))
                assert c.scalar(text(f"SELECT count(*) FROM {table}")) == expected
            if "--from-v3" in sys.argv:
                assert c.execute(text("SELECT kind,note FROM review_entries")).one() == ("rejected", "")
            with psycopg.connect(dsn) as owner:
                assert owner.execute("SELECT title FROM deliverables WHERE id='doc'").fetchone() == ("Internal",)
    runtime.dispose()
    baseline = "v3" if "--from-v3" in sys.argv else "v2" if "--from-v2" in sys.argv else "v1"
    print(f"PASS: populated {baseline} to v4, repeated migration, privileged API login refused, client isolated")


if __name__ == "__main__":
    verify()
