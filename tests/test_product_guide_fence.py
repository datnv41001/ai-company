"""Guide authority is checked even after admission, including between report and consumption."""

import json
import os
from pathlib import Path

import pytest

from agency_fixtures import postgres_api
from app.pool_worker import report, run_job
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from product_guide_fixtures import activate_guide, guide_case
from strategy_runtime_fixtures import studio_save

pytestmark = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Real pool lease and scope locks required")


def withdraw_authority(api, ctx, change):
    if change == "source":
        return accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["state"]["sources"][1]))
    if change == "mandate":
        return accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
    if change == "revision":
        groups = accepted(api.get(ctx["studio"], headers=ctx["owner"]["headers"]))["groups"]
        return studio_save(api, ctx, groups)
    assert change == "recipient"
    # Preserve operator and ordinary editor membership, but remove restricted commission rights.
    ctx["lab"].owner.execute("UPDATE memberships SET role='editor' WHERE tenant_id=%s AND user_id=%s", (ctx["scope"]["tenant_id"], ctx["recipient"]["id"]))


def content_offer(lab, run_id):
    worker = lab.workers[0]
    worker.take()
    assert lab.dispatch()
    director = worker.take()
    assert director and director["run"] == run_id
    assert report(worker.conn, director, run_job(lab.config, director["body"])) and lab.consume()
    assert lab.dispatch()
    return worker


@pytest.mark.parametrize(
    ("phase", "change"),
    [
        ("queued", "source"),
        ("offered", "recipient"),
        ("sent", "mandate"),
        ("reported", "revision"),
    ],
)
def test_revocation_at_guide_lease_boundaries(phase, change):
    with postgres_api() as api, guide_case(api) as ctx:
        activate_guide(api, ctx)
        start = accepted(api.post(ctx["start_guide"], headers=ctx["recipient"]["headers"], json=ctx["guide_request"]))
        run_id, lab = start["run_id"], ctx["lab"]
        worker = lab.workers[0]
        controlled = [{"heading": "product", "layout": "numbered"}, 110, 12]
        if phase != "queued":
            worker = content_offer(lab, run_id)
        if phase in ("sent", "reported"):
            job = worker.take()
            assert job and job["run"] == run_id
            if phase == "reported":
                assert report(worker.conn, job, controlled)
        withdraw_authority(api, ctx, change)
        if phase == "queued":
            worker.take()
            assert not lab.dispatch()
        else:
            if phase == "offered":
                assert not worker.take()
            if phase == "sent":
                assert report(worker.conn, job, controlled)
                # Only metering survives this late report. The revoked text cannot become content.
                result = lab.owner.execute("SELECT result FROM amc_ops.attempts WHERE id=%s", (job["id"],)).fetchone()[0]
                assert result == [None, 110, 12]
            assert lab.consume()
        state = lab.owner.execute(
            "SELECT state,last_error,lease,deliverable_id,checkpoints,reserved_microusd FROM workforce_runs WHERE id=%s", (run_id,)
        ).fetchone()
        assert state[:4] == ("failed", "guide_authority_changed", None, None)
        assert not any(item["skill"] == "content" for item in state[4])
        attempts = lab.owner.execute(
            """SELECT a.status,a.outcome,a.input_tokens,a.output_tokens,
            (SELECT sum(held) FROM amc_ops.ledger WHERE id=a.id),
            (SELECT sum(spent) FROM amc_ops.ledger WHERE id=a.id)
            FROM amc_ops.attempts a WHERE a.run=%s ORDER BY a.started""",
            (run_id,),
        ).fetchall()
        assert all(a[0] == "closed" and a[4:] == (0, 0) for a in attempts)
        assert len(attempts) == (0 if phase == "queued" else 2)
        if phase in ("sent", "reported"):
            assert attempts[-1][1:4] == ("guide_authority_changed", 110, 12)
        if phase == "offered":
            assert attempts[-1][1:4] == ("guide_authority_changed", None, None)
        assert not lab.consume() and not lab.dispatch()
        if folder := os.environ.get("AMC_PRODUCT_GUIDE_EVIDENCE"):
            path = Path(folder) / ("fence-" + phase + ".json")
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_text(
                json.dumps(
                    {
                        "phase": phase,
                        "change": change,
                        "run": run_id,
                        "task": start["task_id"],
                        "manifest": start["manifest_id"],
                        "handoff_receipt": ctx["guide_request"]["receipt_id"],
                        "outcome": state[1],
                        "guide_document": None,
                        "attempts": [
                            dict(status=s, outcome=o, input_tokens=i, output_tokens=u, net_held=int(h), spent=int(c)) for s, o, i, u, h, c in attempts
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
