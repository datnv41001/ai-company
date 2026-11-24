"""Separate PostgreSQL LOGINs race one frozen run using a deterministic provider."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.pool_worker import report
from pool_lab import Lab
from test_diamond import take_node
from test_dynamic_plan import node
from test_workforce import call_model

pytestmark = pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires PostgreSQL")


@pytest.fixture
def parallel():
    with TestClient(app) as api:
        pool = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow="dynamic-v1", parallelism=2)
        try:
            pool.configure(pool.y, 10000, False)
            pool.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=%s", (pool.runs[1],))
            worker, job = take_node(pool)
            assert report(worker.conn, job, [{"nodes": [node("email", "content"), node("page", "content")]}, 125, 32])
            assert pool.consume()
            yield pool
        finally:
            pool.close()


def offer_pair(lab, hold=0):
    for worker in lab.workers:
        assert worker.take() is None
    gate = Barrier(2)

    def dispatch(_):
        gate.wait(10)
        return lab.dispatch(reserve=hold)

    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(dispatch, range(2)))


@pytest.mark.parametrize("cap", ["run", "agency"])
def test_final_budget_slot(parallel, cap):
    lab = parallel
    if cap == "run":
        lab.owner.execute("update workforce_runs set budget_microusd=1000 where id=%s", (lab.runs[0],))
    else:
        # Leave one ready specialist in each of two runs belonging to the same agency.
        lab.owner.execute("update amc_ops.dag_nodes set ready_at=now()+interval '1 day' where run=%s and slot>0", (lab.runs[0],))
        lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (lab.runs[1],))
        w, j = take_node(lab)
        assert j["run"] == lab.runs[1]
        assert report(w.conn, j, [{"nodes": [node("email", "content")]}, 100, 20]) and lab.consume()
        lab.owner.execute("update amc_ops.dag_nodes set ready_at=now() where run=%s and slot=1", (lab.runs[0],))
        lab.configure(lab.x, 1000)
    assert sorted(offer_pair(lab, 700)) == [False, True]
    assert lab.balance_x() == (700, 0)


def test_overlapping_calls_and_atomic_join(parallel):
    lab = parallel
    assert offer_pair(lab) == [True, True]
    jobs = [w.take() for w in lab.workers]
    assert not lab.workers[0].complete(jobs[1]) and not lab.workers[1].complete(jobs[0])
    base, _, _, *_ = lab.cases[0]
    status = lab.api.get(base + "/workforce/runs/" + lab.runs[0], headers=lab.x["headers"]).json()
    assert status["state"] == "running" and sum(n["status"] == "running" for n in status["graph"]["nodes"]) == 2
    for actor in (lab.cases[1][2], lab.y):
        assert lab.api.get(base + "/workforce/runs/" + lab.runs[0], headers=actor["headers"]).status_code == 404
    gate = Barrier(2)

    def infer(pair):
        w, j = pair
        start = time.perf_counter_ns()
        gate.wait(10)
        time.sleep(0.03)  # Deterministic provider holds both calls open across the barrier.
        output = call_model(None, j["body"])
        gate.wait(10)
        stop = time.perf_counter_ns()
        assert report(w.conn, j, output)
        gate.wait(10)
        assert lab.consume()
        return start, stop

    with ThreadPoolExecutor(max_workers=2) as executor:
        spans = list(executor.map(infer, zip(lab.workers, jobs, strict=True)))
    overlap = min(s[1] for s in spans) - max(s[0] for s in spans)
    assert overlap > 0
    rid = lab.runs[0]
    assert lab.states()[0] == "awaiting_qa"
    assert lab.owner.execute("select count(*) from deliverables where campaign_id=%s", (lab.cases[0][-1],)).fetchone() == (1,)
    assert lab.owner.execute("select count(distinct node_id) from amc_ops.attempts where run=%s and step>0 and outcome='ok'", (rid,)).fetchone() == (2,)
    assert all(not w.complete(j) for w, j in zip(lab.workers, jobs, strict=True))


@pytest.mark.parametrize("reason", ["revoke", "exhaust", "timeout"])
def test_fence_and_sibling_lifecycle(parallel, reason):
    lab = parallel
    assert offer_pair(lab, 700) == [True, True]
    w1, w2 = lab.workers
    a, b = w1.take(), w2.take()
    if reason == "revoke":
        lab.revoke_and_restore_a()
        assert not w1.complete(a) and not w2.complete(b)
        assert lab.consume() and lab.consume()
        assert lab.balance_x() == (1400, 0)
        lab.bill(b, 350, "late")
        lab.bill(b, 350, "late")
        lab.bill(b, 0, "refund")
        assert lab.balance_x() == (700, 0)
    elif reason == "timeout":
        assert w1.error(a, "timeout") and lab.consume()
        assert w2.complete(b) and lab.consume()
        assert not w1.complete(a)
        assert not lab.dispatch()
        assert lab.states()[0] == "queued"
    else:
        for attempt in range(3):
            assert w1.error(a, "timeout") and lab.consume()
            if attempt < 2:
                lab.owner.execute("update amc_ops.dag_nodes set ready_at=now() where run=%s", (lab.runs[0],))
                w1.take()
                assert lab.dispatch()
                a = w1.take()
        assert not w2.complete(b)
        assert lab.consume() and lab.states()[0] == "failed"
    assert lab.owner.execute("select deliverable_id from workforce_runs where id=%s", (lab.runs[0],)).fetchone() == (None,)


def test_expired_worker_and_unsent_sibling(parallel):
    lab = parallel
    assert offer_pair(lab, 700) == [True, True]
    w1, w2 = lab.workers
    stale = w1.take()
    lab.owner.execute("update amc_ops.attempts set deadline=now()-interval '1 second' where run=%s and parallel", (lab.runs[0],))
    assert w2.take() is None and not w1.complete(stale)
    assert lab.consume() and lab.consume()
    assert lab.balance_x() == (700, 0)
    unsent = lab.owner.execute("select id from amc_ops.ledger where event='unsent' and tenant=%s", (lab.x["tenant"],)).fetchone()[0]
    assert lab.receipt({"id": str(unsent)}, 0, "never-sent").status_code == 409
    lab.bill(stale, 350, "confirmed")
    lab.owner.execute("update amc_ops.dag_nodes set ready_at=now() where run=%s", (lab.runs[0],))
    assert offer_pair(lab) == [True, True]
    jobs = [w.take() for w in lab.workers]
    assert not w1.complete(stale)
    for w, j in zip(lab.workers, jobs, strict=True):
        assert w.complete(j) and lab.consume()
    assert lab.states()[0] == "awaiting_qa" and lab.balance_x() == (0, 350)


def test_prior_month_hold_counts_toward_run_cap(parallel):
    from uuid import uuid4

    lab = parallel
    rid, tenant = lab.runs[0], lab.x["tenant"]
    old_id = uuid4()
    month = lab.owner.execute("select (date_trunc('month',now() at time zone 'UTC')-interval '1 month')::date").fetchone()[0]
    # Restore a synthetic unresolved sent call from the prior billing period.
    lab.owner.execute("insert into amc_ops.periods values (%s,%s,1000)", (tenant, month))
    lab.owner.execute(
        """insert into amc_ops.attempts(id,run,step,worker,operator,tenant,month,deadline,body,status,reserved,ordinal,
        input_rate,output_rate,node_id,plan_revision,outcome)
        select %s,a.run,1,a.worker,a.operator,a.tenant,%s,now()-interval '1 day','{}','closed',700,1,0,0,n.node_id,n.revision,'timeout'
        from amc_ops.attempts a join amc_ops.dag_nodes n on n.run=a.run and n.slot=1 where a.run=%s and a.step=0""",
        (old_id, month, rid),
    )
    lab.owner.execute("insert into amc_ops.ledger(id,tenant,month,event,actor,held,spent) values(%s,%s,%s,'hold','fixture',700,0)", (old_id, tenant, month))
    lab.owner.execute("update workforce_runs set budget_microusd=1000,reserved_microusd=700 where id=%s", (rid,))
    assert offer_pair(lab, 700) == [False, False]
    lab.bill({"id": str(old_id)}, 250, "prior-invoice")
    assert lab.owner.execute("select distinct month from amc_ops.ledger where id=%s", (old_id,)).fetchall() == [(month,)]
    assert sorted(offer_pair(lab, 700)) == [False, True]
    assert lab.balance_x() == (700, 250)


def test_join_failure_rolls_back_only_last_checkpoint(parallel, monkeypatch):
    from app import workforce_worker

    lab = parallel
    assert offer_pair(lab) == [True, True]
    for w in lab.workers:
        assert w.complete(w.take())
    assert lab.consume()

    def interrupt(*_):
        raise RuntimeError("stop before commit")

    with monkeypatch.context() as patch:
        patch.setattr(workforce_worker, "evaluate", interrupt)
        with pytest.raises(RuntimeError, match="stop before commit"):
            lab.consume()
    assert lab.owner.execute("select count(*) from deliverables where campaign_id=%s", (lab.cases[0][-1],)).fetchone() == (0,)
    assert lab.consume() and not lab.consume()
    assert lab.states()[0] == "awaiting_qa"
    assert lab.owner.execute("select count(*) from deliverables where campaign_id=%s", (lab.cases[0][-1],)).fetchone() == (1,)
