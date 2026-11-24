"""Exercise upgrading a populated starter. Requires an empty local amc_test* database."""
import hashlib
import io
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.conninfo import make_conninfo
import pytest
from sqlalchemy import create_engine, text

from app.database import prepare_database
from migrations.apply import migrate

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
V16_BASE = "d81df0bee0d381007acfd0cf0b786a7f56e38719"
V17_REVIEWED = "df48ef265f14cdc049dec8125c271c8390416c4a"


def migrate_historical_fixture(revision):
    # Each historical binary writes its own genuine markers and schema.
    archive = subprocess.check_output(["git","archive",revision,"app","migrations","catalog","requirements.txt","requirements-registry.txt"],
                                      cwd=MIGRATIONS.parent)
    with tempfile.TemporaryDirectory() as checkout, tarfile.open(fileobj=io.BytesIO(archive)) as sources:
        sources.extractall(checkout, filter="data")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run([sys.executable, "migrations/apply.py"], cwd=checkout, env=env, check=True)


def rehearse_archive(dsn, container, version=16):
    """Round-trip the populated v16 fixture through matching PostgreSQL client tools."""
    tables = ("amc_schema_versions", "users", "memberships", "portal_grants", "portal_invitations",
              "client_reviews", "review_entries", "workforce_runs", "amc_ops.attempts", "amc_ops.ledger",
              "amc_ops.registry_releases", "amc_ops.registry_versions", "amc_ops.dag_nodes")

    if version == 18:
        tables += ("identity_challenges", "amc_acl.identity_key")

    def snapshot(conn):
        return [conn.execute(f"SELECT to_jsonb(t) FROM {table} t ORDER BY to_jsonb(t)").fetchall()
                for table in tables]

    with psycopg.connect(dsn) as source:
        assert source.info.host in ("localhost", "127.0.0.1", "::1") and source.info.dbname.startswith("amc_test")
        assert source.execute("SELECT max(version) FROM amc_schema_versions").fetchone() == (version,)
        db, owner = source.info.dbname, source.info.user
        before = snapshot(source)
    assert all(before)
    # Both the archive and restore are inside this disposable CI container.
    target = "amc_test_restore_" + uuid4().hex
    archive = "/tmp/" + target + ".dump"
    command = ["docker", "exec", container]
    subprocess.run([*command, "pg_dump", "-U", owner, "-Fc", "-f", archive, db], check=True)
    subprocess.run([*command, "createdb", "-U", owner, target], check=True)
    subprocess.run([*command, "pg_restore", "-U", owner, "--single-transaction", "--exit-on-error", "-d", target, archive], check=True)
    with psycopg.connect(make_conninfo(dsn, dbname=target)) as restored:
        assert snapshot(restored) == before
    print(f"PASS: pg_dump/pg_restore v{version} into a separate database; identical rows in {len(tables)} tables")


def verify():
    from_v18 = "--from-v18" in sys.argv
    from_v17 = '--from-v17' in sys.argv or from_v18
    from_v16 = '--from-v16' in sys.argv or from_v17
    from_v15 = '--from-v15' in sys.argv or from_v16
    orphan_v16 = '--from-isolated-v16' in sys.argv
    from_v14 = '--from-v14' in sys.argv or from_v15 or orphan_v16
    from_v13 = '--from-v13' in sys.argv or from_v14
    from_v12 = '--from-v12' in sys.argv or from_v13
    from_v11 = '--from-v11' in sys.argv or from_v12
    from_v10 = "--from-v10" in sys.argv or from_v11
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
        if from_v11:
            conn.execute((MIGRATIONS/"011_workflow_dag.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(11)")
            conn.execute("update amc_ops.agencies set enabled=true where tenant='agency'")
            conn.execute("""insert into workforce_briefs(id,tenant_id,client_id,brand_id,campaign_id,recipient_id,title,created_at)
                values('diamond-brief','agency','a','br','ca','current','Existing diamond',now())""")
            conn.execute("""insert into workforce_runs(id,tenant_id,client_id,brand_id,campaign_id,brief_id,knowledge,plan,
                checkpoints,journal,state,ready_at,attempts,budget_microusd,reserved_microusd,created_at)
                values('diamond-run','agency','a','br','ca','diamond-brief','{"workflow":"diamond-v1","workflow_revision":1}',
                '["director","research","strategy","content","seo"]','[]','[]','queued',now(),0,1000,0,now())""")
            frozen=conn.execute("select id,checkpoints::text,journal::text,ready_at from workforce_runs order by id").fetchall()
        if from_v12:
            conn.execute((MIGRATIONS/"012_dynamic_plan.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(12)")
            conn.execute("""insert into workforce_briefs(id,tenant_id,client_id,brand_id,campaign_id,recipient_id,title,created_at)
                values('dynamic-brief','agency','a','br','ca','current','Existing planner',now())""")
            conn.execute("""insert into workforce_runs(id,tenant_id,client_id,brand_id,campaign_id,brief_id,knowledge,plan,
                checkpoints,journal,state,ready_at,attempts,budget_microusd,reserved_microusd,created_at)
                values('dynamic-run','agency','a','br','ca','dynamic-brief','{"workflow":"dynamic-v1","required_outputs":["content"]}',
                '["director"]','[]','[]','queued',now(),0,1000,0,now())""")
            frozen=conn.execute("select id,checkpoints::text,journal::text,ready_at from workforce_runs order by id").fetchall()
        if from_v13:
            conn.execute((MIGRATIONS/"013_node_leases.sql").read_text(encoding="utf-8"))
            conn.execute("INSERT INTO amc_schema_versions VALUES(13)")
            import registry_upgrade_fixture
            registry_upgrade_fixture.seed(conn)
            v13_snapshot = registry_upgrade_fixture.snapshot(conn)
            original = original[0], conn.execute("select * from amc_ops.ledger order by seq").fetchall()
        if from_v14:
            from migrations.apply import publish_registry
            import json
            conn.execute((MIGRATIONS/"014_workflow_registry.sql").read_text(encoding="utf-8"))
            publish_registry(conn,json.loads((MIGRATIONS.parent/"catalog/landing-seo-v1.json").read_text(encoding="utf-8")))
            conn.execute("insert into amc_schema_versions values (14)")
            if from_v15:
                conn.execute((MIGRATIONS/"015_registry_outputs.sql").read_text(encoding="utf-8"))
                conn.execute("INSERT INTO amc_schema_versions VALUES (15)")
                publish_registry(conn,json.loads((MIGRATIONS.parent/"catalog/research-strategy-v1.json").read_text(encoding="utf-8")))
                conn.execute("insert into users values ('v15-owner','owner15@example.test','unused',now())")
                conn.execute("insert into memberships(tenant_id,user_id,role) values ('agency','v15-owner','owner')")
                conn.execute("select set_config('amc.user_id','v15-owner',true),set_config('amc.tenant_id','agency',true)")
                workflow = "WF-03/research-strategy-draft@1"
                assert conn.execute("select amc_ops.change_registry('agency','ca',%s,'activate',ARRAY['director','research','strategy'])",(workflow,)).fetchone() == (True,)
                conn.execute("""insert into workforce_briefs(id,tenant_id,client_id,brand_id,campaign_id,recipient_id,title,created_at)
                    values('v15-brief','agency','a','br','ca','current','Existing strategy proposal',now())""")
                conn.execute("""insert into workforce_runs(id,tenant_id,client_id,brand_id,campaign_id,brief_id,knowledge,plan,
                    checkpoints,journal,state,ready_at,attempts,budget_microusd,reserved_microusd,created_at)
                    values('v15-run','agency','a','br','ca','v15-brief',jsonb_build_object('workflow','dynamic-v1',
                    'required_outputs',jsonb_build_array('strategy'),'registry',amc_ops.registry_pin('agency','ca',%s)),
                    '["director"]','[]','[]','queued',now(),0,1000,0,now())""",(workflow,))
                frozen = conn.execute("select id,checkpoints::text,journal::text,ready_at from workforce_runs order by id").fetchall()
                v13_snapshot = registry_upgrade_fixture.snapshot(conn)
            if orphan_v16:
                # Reproduce the real independent branch schema (DDL and marker), before 015 ever ran.
                conn.execute((MIGRATIONS/"016_scheduler_diagnostics.sql").read_text(encoding="utf-8"))
                conn.execute("INSERT INTO amc_schema_versions VALUES (16)")
            if from_v16:
                conn.execute("""insert into portal_invitations(id,tenant_id,client_id,user_id,invited_by,email,workspace_name,client_name,
                    brand_id,campaign_id,can_comment,can_decide,expires_at,state) select 'legacy-invite','agency','a',id,'v15-owner',email,
                    'Existing agency','Client A','br','ca',true,false,now()+interval '1 day','pending' from users where id='external'""")
            # Record the actual marker insert order, including the second migration invocation.
            conn.execute("create table upgrade_marker_probe(seq bigint generated always as identity primary key,version int)")
            conn.execute("""create function observe_upgrade_marker() returns trigger language plpgsql as $$
                begin insert into upgrade_marker_probe(version) values(new.version); return new; end $$""")
            conn.execute("create trigger observe_marker after insert on amc_schema_versions for each row execute function observe_upgrade_marker()")
            before_release = conn.execute("select workflow,digest,manifest from amc_ops.registry_releases order by workflow").fetchall()
    if orphan_v16:
        with pytest.raises(ValueError, match="missing migration 015"):
            migrate(dsn)
        with pytest.raises(RuntimeError, match="missing migration 015"):
            prepare_database(runtime)
        with psycopg.connect(dsn) as owner:
            assert registry_upgrade_fixture.snapshot(owner) == v13_snapshot
            assert owner.execute("select version from upgrade_marker_probe").fetchall() == []
            assert owner.execute("select version from amc_schema_versions order by version").fetchall() == [(v,) for v in (*range(2,15),16)]
            assert owner.execute("select preview from client_reviews where id='rv'").fetchone() == ("Preview",)
        runtime.dispose()
        print("PASS: isolated v16 without 015 refused by migrator and API; ledger, leases and approved snapshot preserved")
        return
    ext_before = None
    extension = "select oid,extnamespace::regnamespace::text,extversion from pg_extension where extname='pgcrypto'"
    if from_v15 and not from_v17:
        with psycopg.connect(dsn) as owner:
            if from_v16:
                owner.execute('CREATE SCHEMA "Existing Crypto"')
                owner.execute('CREATE EXTENSION pgcrypto WITH SCHEMA "Existing Crypto"')
            else:
                owner.execute("CREATE EXTENSION pgcrypto WITH SCHEMA public")
            ext_before = owner.execute(extension).fetchone()
    if from_v16:
        migrate_historical_fixture(V16_BASE)
        if not from_v18 and os.getenv("AMC_UPGRADE_BACKUP_CONTAINER"):
            rehearse_archive(dsn, os.environ["AMC_UPGRADE_BACKUP_CONTAINER"])
        if from_v17:
            migrate_historical_fixture(V17_REVIEWED)
        if from_v18:
            migrate_historical_fixture("ece8ecc84b4938900821ff85403bb5b8243534c6")
            with psycopg.connect(dsn) as owner:
                owner.execute("UPDATE users SET verified_at=now() WHERE id='v15-owner'")
                owner.execute("INSERT INTO identity_challenges(user_id,digest,expires_at) VALUES ('external',repeat('a',64),now()+interval '10 minutes')")
                v18_challenges = owner.execute("select * from identity_challenges order by user_id").fetchall()
                v18_verified = owner.execute("select id,verified_at from users order by id").fetchall()
            if os.getenv("AMC_UPGRADE_BACKUP_CONTAINER"):
                rehearse_archive(dsn, os.environ["AMC_UPGRADE_BACKUP_CONTAINER"], 18)
        prior_version = 18 if from_v18 else 17 if from_v17 else 16
        # Fail at the next genuine marker and verify atomic rollback.
        with psycopg.connect(dsn) as owner:
            owner.execute(f"alter table upgrade_marker_probe add constraint synthetic_failure check (version <= {prior_version})")
        with pytest.raises(psycopg.errors.CheckViolation):
            migrate(dsn)
        with psycopg.connect(dsn) as owner:
            owner.execute("alter table upgrade_marker_probe drop constraint synthetic_failure")
            assert owner.execute("select max(version) from amc_schema_versions").fetchone() == (prior_version,)
            assert owner.execute("select count(*) from information_schema.columns where table_schema='public' and table_name='portal_invitations' and column_name='brand_name'").fetchone() == (int(from_v18),)
            assert owner.execute("select count(*) from information_schema.columns where table_schema='public' and table_name='portal_invitations' and column_name='link_digest'").fetchone() == (0,)
            if not from_v17:
                assert owner.execute("select to_regclass('identity_challenges')").fetchone() == (None,)
            assert registry_upgrade_fixture.snapshot(owner) == v13_snapshot
            legacy = owner.execute("select id,email,password_hash,created_at from users order by id").fetchall()
            memberships = owner.execute("select * from memberships order by tenant_id,user_id").fetchall()
            grants = owner.execute("select * from portal_grants order by tenant_id,user_id").fetchall()
    migrate(dsn, os.environ.get("AMC_RUNTIME_PASSWORD"))
    migrate(dsn)
    prepare_database(runtime)
    if ext_before:
        with psycopg.connect(dsn) as owner:
            assert owner.execute(extension).fetchone() == ext_before
        print(f"PASS: preinstalled pgcrypto in {ext_before[1]} retained its OID, namespace and version; runtime signer verified")
    privileged = create_engine("postgresql+psycopg://", creator=lambda: psycopg.connect(dsn))
    with pytest.raises(RuntimeError, match="unprivileged"):
        prepare_database(privileged)
    privileged.dispose()
    with runtime.connect() as c:
        if from_v14:
            with psycopg.connect(dsn) as owner:
                assert owner.execute("select version from upgrade_marker_probe order by seq").fetchall() == [(v,) for v in range(16 if from_v15 else 15, 20)]
                if from_v16:
                    assert owner.execute("select state,role,client_id,can_comment,can_decide from portal_invitations where id='legacy-invite'").fetchone() == ("pending","client_viewer","a",True,False)
                    assert owner.execute("select brand_name,campaign_name from portal_invitations where id='legacy-invite'").fetchone() == ("Brand","Name")
                    assert owner.execute("select id,email,password_hash,created_at from users order by id").fetchall() == legacy
                    if from_v18:
                        assert owner.execute("select id,verified_at from users order by id").fetchall() == v18_verified
                        assert owner.execute("select * from identity_challenges order by user_id").fetchall() == v18_challenges
                        assert owner.execute("select user_id,link_digest from portal_invitations where id='legacy-invite'").fetchone() == ("external",None)
                    else:
                        assert owner.execute("select count(*) from users where verified_at is not null").fetchone() == (0,)
                    assert owner.execute("select * from memberships order by tenant_id,user_id").fetchall() == memberships
                    assert owner.execute("select * from portal_grants order by tenant_id,user_id").fetchall() == grants
            assert c.execute(text("select workflow,digest,manifest from amc_ops.registry_releases order by workflow")).fetchall() == before_release
        def identify():
            c.execute(text("SELECT set_config('amc.user_id','alice',true),set_config('amc.tenant_id','agency',true)"))
        identify()
        assert set(c.scalars(text("SELECT id FROM clients"))) == {"a", "b"}
        c.rollback()
        with psycopg.connect(dsn) as owner:
            owner.execute("UPDATE memberships SET role='client_viewer',client_id='a' WHERE user_id='alice'")
        identify()
        assert set(c.scalars(text("SELECT id FROM clients"))) == {"a"}
        assert set(c.scalars(text("SELECT version FROM amc_schema_versions"))) == set(range(2,20))
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
                    assert owner.execute("select count(*) from amc_ops.dag_plans").fetchone()==(int(from_v11)+int(from_v12)+int(from_v15),)
                    if from_v13:
                        assert registry_upgrade_fixture.snapshot(owner) == v13_snapshot
                    elif from_v12:
                        assert owner.execute("select amc_ops.parallel_node('dynamic-run',0),contract from amc_ops.dag_plans where run='dynamic-run'").fetchone()==(False,None)
                    if from_v11:
                        assert owner.execute("select amc_ops.valid_diamond('diamond-run')").fetchone()==(True,)
                    assert owner.execute("select id,checkpoints::text,journal::text,ready_at from workforce_runs order by id").fetchall()==frozen
                    assert owner.execute("select count(*) from amc_ops.attempts where node_id is not null").fetchone()==(2 if from_v13 else 0,)
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
    baseline = "v13" if from_v13 else "v12" if from_v12 else "v11" if from_v11 else "v10" if from_v10 else "v9" if from_v9 else "v8" if from_v8 else "v7" if from_v7 else "v6" if from_v6 else "v5" if from_v5 else "v4" if from_v4 else "v3" if from_v3 else "v2" if "--from-v2" in sys.argv else "v1"
    print(f"PASS: populated {'v18' if from_v18 else 'v17' if from_v17 else 'v16' if from_v16 else 'v15' if from_v15 else 'v14' if from_v14 else baseline} to v19, repeated migration, privileged API login refused, client isolated")


if __name__ == "__main__":
    verify()
