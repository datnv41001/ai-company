"""Exercise upgrading a populated starter. Requires an empty local amc_test* database."""
import hashlib
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
    from_v10 = "--from-v10" in sys.argv
    from_v9 = "--from-v9" in sys.argv or from_v10
    from_v8 = "--from-v8" in sys.argv or from_v9
    from_v7 = "--from-v7" in sys.argv or from_v8
    from_v6 = "--from-v6" in sys.argv or from_v7
    from_v5 = "--from-v5" in sys.argv or from_v6
    from_v4 = "--from-v4" in sys.argv or from_v5
    from_v3 = "--from-v3" in sys.argv or from_v4
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
        if "--from-v2" in sys.argv or from_v3:
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
        if from_v3:
            for file in ("003_delivery_tables.sql", "003_delivery_policies.sql"):
                conn.execute((MIGRATIONS / file).read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(3)")
            # V3 permitted rejection without a reason. Preserve the archived evidence verbatim.
            conn.execute("""INSERT INTO client_reviews(id,tenant_id,client_id,brand_id,campaign_id,deliverable_id,version,title,
                         preview,digest,requested_by,qa_by,created_at,expires_at) VALUES('rv','agency','a','br','ca','doc',1,
                         'Title','Preview',encode(sha256(convert_to('{"preview":"Preview","title":"Title"}','UTF8')),'hex'),
                         'alice','alice',now(),now()+interval '1 day')""")
            conn.execute("""INSERT INTO review_entries(id,tenant_id,review_id,digest,actor_id,kind,note,request_key,created_at)
                         SELECT 'entry','agency','rv',digest,'external',%s,'','legacy-key',now() FROM client_reviews WHERE id='rv'""",
                         ('approved' if from_v7 else 'rejected',))
        if from_v4:
            conn.execute((MIGRATIONS/"004_review_operations.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (4)")
        if from_v5:
            conn.execute((MIGRATIONS/"005_workforce.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (5)")
            conn.execute("""INSERT INTO workforce_briefs(id,tenant_id,client_id,brand_id,campaign_id,recipient_id,title,created_at)
                VALUES('old-brief','agency','a','br','ca','external','Existing brief',now())""")
            conn.execute("""INSERT INTO workforce_runs(id,tenant_id,client_id,brand_id,campaign_id,brief_id,knowledge,plan,
                checkpoints,journal,state,ready_at,attempts,budget_microusd,reserved_microusd,created_at)
                VALUES ('old-run','agency','a','br','ca','old-brief','{}','[]','[]','[{"outcome":"running"}]',
                        'running',now(),1,1000,100,now())""")
            conn.execute("DELETE FROM portal_grants WHERE user_id='external'")
        if from_v6:
            conn.execute((MIGRATIONS/"006_workforce_authority.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (6)")
            conn.execute("""UPDATE deliverables SET status='approved',reviewed_by='alice',
                         content='{"client_preview":"Legacy","qa_evidence":{"state":"current"},"qa_claims":[]}' WHERE id='doc'""")
        if from_v7:
            conn.execute((MIGRATIONS/"007_revision_qa.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES (7)")
            conn.execute("""UPDATE deliverables SET qa_approved_digest=repeat('a',64),
                         qa_evidence='{"ruleset_version":"old"}' WHERE id='doc'""")
        if from_v8:
            conn.execute((MIGRATIONS/"008_qa_revision.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(8)")
            conn.execute("INSERT INTO users VALUES ('current','current@example.com','unused',now())")
            conn.execute("INSERT INTO memberships(tenant_id,user_id,role,client_id) VALUES('agency','current','client_viewer','a')")
            conn.execute("INSERT INTO portal_grants(tenant_id,user_id,client_id,can_comment,can_decide) VALUES('agency','current','a',false,false)")
            conn.execute("""INSERT INTO workforce_briefs(id,tenant_id,client_id,brand_id,campaign_id,recipient_id,title,created_at)
                VALUES('active-brief','agency','a','br','ca','current','Active',now())""")
            conn.execute("""INSERT INTO workforce_runs(id,tenant_id,client_id,brand_id,campaign_id,brief_id,knowledge,plan,
                checkpoints,journal,state,lease,ready_at,attempts,budget_microusd,reserved_microusd,created_at)
                VALUES('active-run','agency','a','br','ca','active-brief','{}','["director"]','[]','[{"outcome":"running"}]',
                    'running','v8-lease',now()+interval '1 hour',1,1000,700,now())""")
        if from_v9:
            import financial_upgrade_fixture
            conn.execute((MIGRATIONS/"009_company_operations.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(9)")
            original = financial_upgrade_fixture.seed(conn)
        if from_v10:
            conn.execute((MIGRATIONS/"010_run_reconciliation.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(10)")
            financial_upgrade_fixture.verify(conn,original)
            # Retain a partially completed linear run as well as the populated v9 pool lease/receipt.
            conn.execute("update amc_ops.agencies set enabled=false where tenant='agency'")
            conn.execute("""insert into workforce_briefs(id,tenant_id,client_id,brand_id,campaign_id,recipient_id,title,created_at)
                values('linear-brief','agency','a','br','ca','current','Existing linear brief',now())""")
            conn.execute("""insert into workforce_runs(id,tenant_id,client_id,brand_id,campaign_id,brief_id,knowledge,plan,
                checkpoints,journal,state,ready_at,attempts,budget_microusd,reserved_microusd,created_at)
                values('linear-run','agency','a','br','ca','linear-brief','{}','["director","research"]',
                '[{"skill":"director","output":{"text":"Retain plan","assignments":{"research":"Verify source"}}}]',
                '[{"skill":"director","outcome":"ok"}]','queued',now(),0,1000,0,now())""")
            frozen=conn.execute("select id,checkpoints::text,journal::text,ready_at from workforce_runs order by id").fetchall()
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
        assert set(c.scalars(text("SELECT version FROM amc_schema_versions"))) == {2,3,4,5,6,7,8,9,10,11}
        if "--from-v2" in sys.argv or from_v3:
            c.rollback()
            c.execute(text("SELECT set_config('amc.user_id','external',true),set_config('amc.tenant_id','agency',true)"))
            assert c.execute(text("SELECT client_id,can_comment,can_decide FROM portal_grants")).one_or_none() == (None if from_v5 else ("a",False,False))
            for table in ("client_reviews","review_entries","deliverables"):
                expected = int(from_v3 and not from_v5 and table in ("client_reviews", "review_entries"))
                assert c.scalar(text(f"SELECT count(*) FROM {table}")) == expected
            if from_v3 and not from_v5:
                assert c.execute(text("SELECT kind,note FROM review_entries")).one() == ("rejected", "")
            with psycopg.connect(dsn) as owner:
                if from_v6:
                    expected_qa = ({"ruleset_version":"old"}, "a"*64) if from_v7 else (None,None)
                    assert owner.execute("SELECT qa_evidence,qa_approved_digest FROM deliverables WHERE id='doc'").fetchone() == expected_qa
                    assert owner.execute("SELECT qa_revision,qa_approved_revision FROM deliverables WHERE id='doc'").fetchone() == (1,None)
                    if from_v7:
                        assert owner.execute("SELECT kind,digest FROM review_entries WHERE id='entry'").fetchone() == (
                            "approved", hashlib.sha256(b'{"preview":"Preview","title":"Title"}').hexdigest())
                    assert owner.execute("SELECT version,title,preview,digest FROM client_reviews WHERE id='rv'").fetchone() == (
                        1, "Title", "Preview", hashlib.sha256(b'{"preview":"Preview","title":"Title"}').hexdigest())
                if from_v10:
                    assert owner.execute("select count(*) from amc_ops.dag_plans").fetchone()==(0,)
                    assert owner.execute("select id,checkpoints::text,journal::text,ready_at from workforce_runs order by id").fetchall()==frozen
                    assert owner.execute("select count(*) from amc_ops.attempts where node_id is not null").fetchone()==(0,)
                if from_v9:
                    financial_upgrade_fixture.verify(owner, original)
                if from_v8:
                    assert owner.execute("SELECT execution_mode,lease,reserved_microusd,state FROM workforce_runs WHERE id='active-run'").fetchone() == (
                        'legacy','v8-lease',700,'running')
                    assert owner.execute("SELECT count(*) FROM amc_ops.tasks WHERE run='active-run'").fetchone() == (0,)
                if from_v5:
                    assert owner.execute("SELECT state,last_error,reserved_microusd FROM workforce_runs WHERE id='old-run'").fetchone() == ("failed","recipient_revoked",100)
                    assert owner.execute("SELECT count(*) FROM audit_events WHERE event='workforce.recipient_revoked'").fetchone() == (1,)
                assert owner.execute("SELECT title FROM deliverables WHERE id='doc'").fetchone() == ("Internal",)
    runtime.dispose()
    baseline = "v10" if from_v10 else "v9" if from_v9 else "v8" if from_v8 else "v7" if from_v7 else "v6" if from_v6 else "v5" if from_v5 else "v4" if from_v4 else "v3" if from_v3 else "v2" if "--from-v2" in sys.argv else "v1"
    print(f"PASS: populated {baseline} to v11, repeated migration, privileged API login refused, client isolated")


if __name__ == "__main__":
    verify()
