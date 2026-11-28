"""Roll back the reader edition without converting the guide or reopening historical access."""

import os

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from agency_fixtures import postgres_api
from app.database import engine
from app.security import current_user, require_tenant
from knowledge_fixtures import accepted
from migrations.product_guide_contract import GUIDE_FENCE
from product_guide_fixtures import activate_guide, advance_guide, guide_case

pytestmark = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Real reader edition and row policies required")

VISIBLE = text("""
    SELECT (SELECT count(*) FROM workforce_briefs WHERE id=:brief),
           (SELECT count(*) FROM knowledge_snapshots WHERE id=:manifest),
           (SELECT count(*) FROM workforce_runs WHERE id=:run),
           (SELECT count(*) FROM deliverables WHERE id=:doc)
""")


def test_previous_reader_sees_strategy_but_cannot_load_guide():
    with postgres_api() as api, guide_case(api) as ctx:
        activate_guide(api, ctx)
        started = accepted(api.post(ctx["start_guide"], headers=ctx["recipient"]["headers"], json=ctx["guide_request"]))
        attempts = advance_guide(ctx)
        assert [r["stage"] for r in attempts] == ["director", "content"]
        db_admin = ctx["lab"].owner
        doc = db_admin.execute("SELECT deliverable_id FROM workforce_runs WHERE id=%s", (started["run_id"],)).fetchone()[0]
        child = dict(brief=started["task_id"], manifest=started["manifest_id"], run=started["run_id"], doc=doc)
        parent = dict(brief=ctx["task"]["id"], manifest=ctx["snap"]["id"], run=ctx["run"]["id"], doc=ctx["doc"].rsplit("/", 1)[-1])
        token = ctx["recipient"]["headers"]["Authorization"].split()[1]
        with Session(engine) as session, session.begin():
            user = current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), session)
            require_tenant(session, user, ctx["scope"]["tenant_id"], "admin")
            assert session.execute(VISIBLE, child).one() == (1, 1, 1, 1)
            audit = text("SELECT event,details FROM audit_events WHERE subject_id IN (:doc,:brief,:run) ORDER BY id")
            child_audit = session.execute(audit, child).all()
            parent_audit = session.execute(audit, parent).all()
            assert any(e == "deliverable.qa_evaluated" for e, _ in child_audit)
            assert parent_audit and all(v.get("product_guide_edition") == "guide/1" for _, v in child_audit)
            # Older API code supplies no product_guide_protocol. Use the same authenticated subject in the same transaction.
            session.execute(text("SELECT set_config('amc.product_guide_protocol','',true)"))
            assert session.execute(VISIBLE, parent).one() == (1, 1, 1, 1)
            assert session.execute(VISIBLE, child).one() == (0, 0, 0, 0)
            assert not session.execute(audit, child).all()
            assert session.execute(audit, parent).all() == parent_audit
            session.execute(text("SELECT set_config('amc.product_guide_protocol','guide/1',true)"))
            assert session.execute(VISIBLE, child).one() == (1, 1, 1, 1)
        # Startup and publisher must both refuse partial installation of the feature.
        with db_admin.transaction(force_rollback=True):
            db_admin.execute("DROP POLICY guide_reader_edition ON deliverables")
            assert db_admin.execute(GUIDE_FENCE).fetchone() == (False,)
        assert db_admin.execute(GUIDE_FENCE).fetchone() == (True,)
        assert db_admin.execute("SELECT state,deliverable_id FROM workforce_runs WHERE id=%s", (started["run_id"],)).fetchone() == ("awaiting_qa", doc)
        ledger_before = db_admin.execute("SELECT count(*) FROM amc_ops.ledger WHERE tenant=%s", (ctx["scope"]["tenant_id"],)).fetchone()
        revoked = accepted(
            api.put(
                ctx["base"] + "/workforce/registry/" + ctx["scope"]["campaign_id"],
                headers=ctx["owner"]["headers"],
                json={"workflow": "WF-06/product-use-guide@1", "skills": ["director", "content"], "action": "revoke"},
            )
        )
        assert revoked["action"] == "revoke"
        hidden = api.get(ctx["base"] + "/deliverables/" + doc + "/studio/product-guide", headers=ctx["recipient"]["headers"])
        assert hidden.status_code == 409
        assert accepted(api.get(ctx["studio"] + "/content-handoff", headers=ctx["recipient"]["headers"]))["work_order"]["asset_type"] == "web_use_guide"
        assert db_admin.execute("SELECT count(*) FROM amc_ops.ledger WHERE tenant=%s", (ctx["scope"]["tenant_id"],)).fetchone() == ledger_before
        assert db_admin.execute("SELECT id FROM deliverables WHERE id=%s", (doc,)).fetchone() == (doc,)
        assert db_admin.execute("SELECT count(*) FROM amc_ops.attempts WHERE run=%s AND status='closed'", (started["run_id"],)).fetchone() == (2,)


def test_report_waits_for_human_transaction_then_keeps_zero_metering():
    from app.pool_worker import report, run_job
    from c3_fixtures import withdraw

    with postgres_api() as api, guide_case(api) as ctx:
        activate_guide(api, ctx)
        started = accepted(api.post(ctx["start_guide"], headers=ctx["recipient"]["headers"], json=ctx["guide_request"]))
        lab = ctx["lab"]
        worker = lab.workers[0]
        worker.take()
        assert lab.dispatch()
        job = worker.take()
        assert job["run"] == started["run_id"]
        assert report(worker.conn, job, run_job(lab.config, job["body"]))
        scope = ctx["scope"]
        key = "k22:" + scope["tenant_id"] + ":" + scope["client_id"] + ":" + scope["brand_id"]
        with lab.owner.transaction():
            lab.owner.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,22))", (key,))
            assert not lab.consume()
            assert lab.owner.execute("SELECT status FROM amc_ops.attempts WHERE id=%s", (job["id"],)).fetchone() == ("reported",)
        accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
        assert lab.consume()
        assert lab.owner.execute("SELECT outcome,input_tokens,output_tokens FROM amc_ops.attempts WHERE id=%s", (job["id"],)).fetchone() == (
            "guide_authority_changed",
            0,
            0,
        )
        assert lab.owner.execute("SELECT sum(held),sum(spent) FROM amc_ops.ledger WHERE id=%s", (job["id"],)).fetchone() == (0, 0)
