"""Verify the authority available at the human and deferred dispatch boundaries on the same Strategy receipt."""

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from agency_fixtures import postgres_api
from app.workforce_models import WorkforceRun
from app.workforce_worker import Scope, authorized_queue
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from strategy_runtime_fixtures import commission_lab, prepare_review
from test_strategy_runtime_handoff import terms

pytestmark = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Real scoped PostgreSQL dispatcher required")


def dispatcher_view(ctx, receipt):
    lab = ctx["lab"]
    with Session(lab.bind) as db, db.begin():
        route = db.execute(text("SELECT tenant,client,brand,campaign,operator FROM amc_ops.routes WHERE worker=:name"), {"name": lab.worker_name}).one()
        scope = Scope(*route)
        run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == ctx["run"]["id"]))
        assert run is not None and run.tenant_id == ctx["scope"]["tenant_id"]
        # Use the dispatch login and normal operator scope. Only count accessible rows.
        checks = db.execute(
            text("""
            SELECT amc_acl.knowledge_read(:tenant,'public'), amc_acl.knowledge_read(:tenant,'restricted'),
                   (SELECT count(*) FROM knowledge_commands WHERE id=:receipt),
                   (SELECT count(*) FROM knowledge_revisions WHERE id=:mandate)
        """),
            {"tenant": scope.tenant, "receipt": receipt, "mandate": ctx["mandate"]["id"]},
        ).one()
        return {
            "strategy_run": run.id,
            "manifest": run.knowledge["c3_manifest"],
            "knowledge_public": checks[0],
            "knowledge_restricted": checks[1],
            "visible_handoff_receipts": checks[2],
            "visible_mandates": checks[3],
        }


def test_strategy_revocation_and_dispatcher_view():
    with postgres_api() as api, commission_lab(api) as ctx:
        prepare_review(api, ctx)
        url = ctx["studio"] + "/content-handoff"
        reviewer, recipient = (ctx[key]["headers"] for key in ("reviewer", "recipient"))
        ready = accepted(api.get(url, headers=reviewer))
        decision = accepted(api.post(url, headers=reviewer, json=terms(ready, ctx)))
        receipt = decision["decision"]["receipt_id"]
        current = accepted(api.get(url, headers=recipient))
        assert current["work_order"]["asset_type"] == "web_use_guide" and current["decision"]["receipt_id"] == receipt
        before = dispatcher_view(ctx, receipt)
        assert not before["knowledge_public"] and not before["knowledge_restricted"]
        assert before["visible_handoff_receipts"] == before["visible_mandates"] == 0
        accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
        withheld = accepted(api.get(url, headers=recipient))
        assert withheld["work_order"] is None and "qualification_withdrawn" in withheld["reasons"]
        # The same bound run and manifest stay readable for historical accounting.
        after = dispatcher_view(ctx, receipt)
        assert before == after
        if directory := os.environ.get("AMC_PRODUCT_GUIDE_EVIDENCE"):
            path = Path(directory) / "dispatcher-authority.json"
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_text(
                json.dumps(
                    {
                        "strategy_document": ready["provenance"]["document_id"],
                        "qa_revision": ready["revision"],
                        "receipt": receipt,
                        "recipient_before": "web_use_guide",
                        "recipient_after": withheld["reasons"],
                        "dispatcher_before": before,
                        "dispatcher_after": after,
                        "guide_worker_started": False,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
