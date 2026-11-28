"""Exercise real concurrent Knowledge withdrawal and reporting by the assigned WF-06 worker."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from threading import Event

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from agency_fixtures import postgres_api
from app.database import engine
from app.pool_worker import report
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from product_guide_fixtures import activate_guide, guide_case
from test_product_guide_fence import content_offer

pytestmark = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Requires separate real worker and Knowledge transactions")
CONTROLLED = [{"heading": "product", "layout": "numbered"}, 110, 12]


def transaction_states(observer, report_xid, owner_xid):
    return list(observer.execute("SELECT pg_xact_status(%s::xid8), pg_xact_status(%s::xid8)", (report_xid, owner_xid)).fetchone())


def assert_no_guide(lab, run_id, campaign):
    state, error, lease, output, steps = lab.owner.execute(
        "SELECT state,last_error,lease,deliverable_id,checkpoints FROM workforce_runs WHERE id=%s", (run_id,)
    ).fetchone()
    assert output is None and [step["skill"] for step in steps] == ["director"]
    assert lab.owner.execute("SELECT count(*) FROM deliverables WHERE campaign_id=%s AND content::jsonb ? 'product_guide'", (campaign,)).fetchone() == (0,)
    return state, error, lease


def mailbox(lab, job_id):
    with lab.bind.connect() as dispatcher:
        return dispatcher.execute(text("SELECT status,result FROM amc_ops.attempts WHERE id=:id"), {"id": job_id}).one()


def overlap(api, ctx, job, target, order):
    # The barrier only delays the ordinary signed HTTP command just before commit. The
    # worker remains a separate database LOGIN, calling its production report function.
    ready, release = Queue(), Event()
    lab, worker = ctx["lab"], ctx["lab"].workers[0]

    def pause_owner(session):
        if session.get_bind() is not engine or release.is_set():
            return
        session.flush()
        xid, backend, role = session.execute(text("SELECT pg_current_xact_id()::text, pg_backend_pid(),current_user")).one()
        assert role == "amc_runtime"
        ready.put((xid, backend))
        assert release.wait(timeout=8)

    trace = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        event.listen(Session, "before_commit", pause_owner)
        revoke = pool.submit(withdraw, api, ctx["owner"], ctx["state"], target)
        try:
            owner_xid, owner_pid = ready.get(timeout=8)
            with worker.conn.transaction():
                worker.conn.execute("SET LOCAL statement_timeout='3s'")
                report_xid, worker_pid = worker.conn.execute("SELECT pg_current_xact_id()::text, pg_backend_pid()").fetchone()
                assert worker_pid != owner_pid and owner_xid != report_xid
                assert transaction_states(lab.owner, report_xid, owner_xid) == ["in progress", "in progress"]
                if order == "withdraw_visible_before_report":
                    release.set()
                    accepted(revoke.result(timeout=6))
                assert report(worker.conn, job, CONTROLLED)
                assert mailbox(lab, job["id"]) == ("sent", None)
                if order != "report_commits_first":
                    release.set()
                    accepted(revoke.result(timeout=6))
                    states = transaction_states(lab.owner, report_xid, owner_xid)
                    assert states == ["in progress", "committed"]
                    trace.append({"point": "withdrawal_committed", "report_then_owner_xid_status": states})
            if order == "report_commits_first":
                states = transaction_states(lab.owner, report_xid, owner_xid)
                assert states == ["committed", "in progress"]
                assert mailbox(lab, job["id"]) == ("reported", CONTROLLED)
                # The first consume poll encounters the live Knowledge scope lock.
                assert not lab.consume()
                assert mailbox(lab, job["id"]) == ("reported", CONTROLLED)
                assert_no_guide(lab, job["run"], ctx["scope"]["campaign_id"])
                trace.append({"point": "dispatcher_deferred_on_open_withdrawal", "report_then_owner_xid_status": states})
                release.set()
                accepted(revoke.result(timeout=6))
        finally:
            release.set()
            event.remove(Session, "before_commit", pause_owner)
        states = transaction_states(lab.owner, report_xid, owner_xid)
        assert states == ["committed", "committed"]
        trace.append({"point": "both_committed", "report_then_owner_xid_status": states})
    return {"report_xid": report_xid, "withdraw_xid": owner_xid, "distinct_postgres_backends": worker_pid != owner_pid, "trace": trace}


@pytest.mark.parametrize("change", ["mandate", "source"])
@pytest.mark.parametrize("order", ["report_commits_first", "withdraw_commits_first", "withdraw_visible_before_report"])
def test_content_report_and_withdrawal_overlap(change, order):
    with postgres_api() as api, guide_case(api) as ctx:
        activate_guide(api, ctx)
        started = accepted(api.post(ctx["start_guide"], headers=ctx["recipient"]["headers"], json=ctx["guide_request"]))
        lab, run_id = ctx["lab"], started["run_id"]
        campaign = ctx["scope"]["campaign_id"]
        worker = content_offer(lab, run_id)
        job = worker.take()
        assert job["run"] == run_id
        target = ctx["mandate"] if change == "mandate" else ctx["state"]["sources"][1]
        txn = overlap(api, ctx, job, target, order)
        expected = [None, 110, 12] if order == "withdraw_visible_before_report" else CONTROLLED
        assert mailbox(lab, job["id"]) == ("reported", expected)
        with lab.bind.connect() as dispatcher:
            predicates = dispatcher.execute(text("SELECT amc_ops.live(:id),amc_ops.fence(:id)"), {"id": job["id"]}).one()
            assert predicates == (False, False)
            can_read = dispatcher.scalar(text("SELECT has_column_privilege(current_user,'amc_ops.attempts','result','SELECT')"))
            assert can_read
        # Resolve effective column privileges as catalog metadata even for logins without schema USAGE.
        reader_roles = lab.owner.execute(
            """SELECT has_column_privilege('amc_runtime','amc_ops.attempts','result','SELECT'),
                      has_column_privilege(%s,'amc_ops.attempts','result','SELECT'),
                      has_column_privilege(current_user,'amc_ops.attempts','result','SELECT')""",
            (lab.worker_name,),
        ).fetchone()
        assert reader_roles == (False, False, True)
        assert_no_guide(lab, run_id, campaign)
        assert lab.consume()
        assert mailbox(lab, job["id"]) == ("closed", None)
        assert assert_no_guide(lab, run_id, campaign) == ("failed", "guide_authority_changed", None)
        actual = lab.owner.execute(
            """SELECT outcome,body,input_tokens,output_tokens,input_rate,output_rate
               FROM amc_ops.attempts WHERE id=%s""",
            (job["id"],),
        ).fetchone()
        assert actual == ("guide_authority_changed", {}, 110, 12, 0, 0)
        assert not report(worker.conn, job, CONTROLLED) and not lab.consume() and not lab.dispatch()
        receipt = {"amount": 0, "receipt": "synthetic-closed-" + str(job["id"])}
        path = ctx["base"] + "/operations/attempts/" + str(job["id"]) + "/receipts"
        receipt_codes = []
        for _ in range(2):
            response = api.post(path, headers=ctx["owner"]["headers"], json=receipt)
            assert accepted(response) == {"recorded": True}
            receipt_codes.append(response.status_code)
        conflict = api.post(path, headers=ctx["owner"]["headers"], json=receipt | {"amount": 1})
        receipt_codes.append(conflict.status_code)
        assert receipt_codes == [200, 200, 409]
        journal = lab.owner.execute("SELECT journal::jsonb->-1,reserved_microusd FROM workforce_runs WHERE id=%s", (run_id,)).fetchone()
        assert journal[0]["usage_unconfirmed"] is False and journal[1] == 0
        ledger = lab.owner.execute("SELECT event,held,spent FROM amc_ops.ledger WHERE id=%s ORDER BY event", (job["id"],)).fetchall()
        assert ledger == [("hold", 0, 0), ("receipt", 0, 0), ("usage", 0, 0)]
        assert assert_no_guide(lab, run_id, campaign) == ("failed", "guide_authority_changed", None)
        if folder := os.environ.get("AMC_GUIDE_MAILBOX_EVIDENCE"):
            dest = Path(folder)
            dest.mkdir(parents=True, exist_ok=True)
            record = {
                "case": order,
                "postgres_version_num": lab.owner.info.server_version,
                "withdrawn_kind": change,
                "withdrawn_revision": target["id"],
                "run": run_id,
                "attempt": str(job["id"]),
                "source_handoff": ctx["guide_request"]["receipt_id"],
                "transactions": txn,
                "before_consume": {"status": "reported", "result": expected},
                "after_revocation": {"live": predicates[0], "fence": predicates[1]},
                "effective_readers_tested": {
                    "dispatcher": can_read,
                    "runtime_login": reader_roles[0],
                    "assigned_worker": reader_roles[1],
                    "database_owner": reader_roles[2],
                },
                "after_consume": {
                    "status": "closed",
                    "result": None,
                    "envelope": actual[1],
                    "outcome": actual[0],
                    "lease": None,
                    "checkpoints": ["director"],
                    "guide_documents": 0,
                },
                "metering": {
                    "source": "controlled fixture",
                    "input": actual[2],
                    "output": actual[3],
                    "rate_input": actual[4],
                    "rate_output": actual[5],
                    "usage_unconfirmed": journal[0]["usage_unconfirmed"],
                    "ledger_event_held_spent": ledger,
                    "run_exposure_microusd": journal[1],
                },
                "receipt_replay": receipt_codes,
                "post_close_report_accepted": False,
                "service_inference_calls": 0,
            }
            (dest / f"{order}-{change}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
