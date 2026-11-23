"""Exercise real PostgreSQL logins, concurrent dispatch and immutable per-attempt accounting."""

import os
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires disposable PostgreSQL")


def test_two_workers_three_campaigns(pool_lab):
    lab = pool_lab
    a, b, c = lab.runs
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert all(executor.map(lambda _: lab.dispatch(), range(2)))
    first, second = [w.take() for w in lab.workers]
    assert {first["run"], second["run"]} == {a, c}
    assert all(w.take() is None for w in lab.workers)
    lab.check_isolation(first, second)
    lab.revoke_and_restore_a()
    for worker, job in zip(lab.workers, (first, second), strict=True):
        assert worker.complete(job) == (job["run"] != a)
    lab.drain()
    assert lab.states() == ["failed", "awaiting_qa", "awaiting_qa"]
    lab.verify_assets_and_dependencies(b, c)


def test_last_agency_balance_and_late_duplicate_bill(pool_lab):
    lab = pool_lab
    lab.limit_x(1000)
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: lab.dispatch(reserve=700), range(2)))
    jobs = [(w, w.take()) for w in lab.workers]
    assert sum(j is not None for _, j in jobs) == 1
    worker, job = next((w, j) for w, j in jobs if j and j["run"] == lab.runs[0])
    assert worker.error(job, "timeout")
    lab.consume()
    assert lab.balance_x() == (700, 0)
    lab.dispatch(reserve=700)
    assert lab.balance_x() == (700, 0)
    assert not worker.complete(job)
    lab.bill(job, 350, "receipt-1")
    lab.bill(job, 350, "receipt-1")
    assert lab.balance_x() == (0, 350)
    lab.reject_conflicting_receipt(job)


@pytest.fixture()
def pool_lab():
    from fastapi.testclient import TestClient
    from app.main import app
    from pool_lab import Lab

    with TestClient(app) as api:
        lab = Lab(api, os.environ["AMC_MIGRATION_DSN"])
        try:
            assert all(w.take() is None for w in lab.workers)
            yield lab
        finally:
            lab.close()


def test_pool_expiry_releases_only_undelivered_envelopes(pool_lab):
    lab = pool_lab
    lab.limit_x(1000)
    assert lab.dispatch(reserve=700)
    rid = lab.runs[0]

    def expire():
        lab.owner.execute("update workforce_runs set ready_at=now()-interval '1 second' where id=%s", (rid,))

    expire()
    assert lab.consume()
    assert lab.balance_x() == (0, 0)
    assert all(w.take() is None for w in lab.workers)
    # Keep the second campaign waiting so the next reservation belongs to A again.
    lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 hour' where id=%s", (lab.runs[1],))
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: lab.dispatch(reserve=700), range(2))) == [False, True]
    worker, job = next((w, j) for w in lab.workers if (j := w.take()) is not None)
    assert job["run"] == rid
    expire()
    assert not worker.complete(job)
    assert lab.consume()
    assert lab.balance_x() == (700, 0)
    assert lab.owner.execute("select distinct step from amc_ops.attempts where run=%s", (rid,)).fetchall() == [(0,)]
    lab.bill(job, 1100, "late-overage")
    assert lab.balance_x() == (0, 1100)
    assert not lab.dispatch(reserve=700)


def test_duplicate_completion_and_measured_invalid_plan(pool_lab):
    from app.pool_worker import report

    lab = pool_lab
    assert lab.dispatch()
    worker, job = next((w, j) for w in lab.workers if (j := w.take()) is not None)
    assert report(worker.conn, job, [{"plan": "Write copy", "assignments": {}, "source_ids": ["S1"]}, 50, 16])
    assert not worker.complete(job)
    assert lab.consume()
    assert lab.owner.execute("select outcome from amc_ops.attempts where id=%s", (job["id"],)).fetchone() == ("invalid_plan",)
    assert lab.owner.execute("select count(*) from amc_ops.ledger where id=%s and event='usage'", (job["id"],)).fetchone() == (1,)


def test_offline_worker_and_cutover(pool_lab):
    lab = pool_lab
    offline = lab.workers[0].conn.info.user
    lab.owner.execute("update amc_ops.readiness set polled=now()-interval '1 minute' where worker=%s", (offline,))
    assert lab.dispatch()
    assert lab.workers[0].take() is None
    assert lab.workers[1].take() is not None
    lab.configure(lab.y, 10000, False)
    lab.seed("D", lab.y)
    response = lab.api.put(
        "/api/tenants/" + lab.y["tenant"] + "/operations/budget", headers=lab.y["headers"], json={"enabled": True, "capacity": 2, "ceiling": 1000}
    )
    assert response.status_code == 409
    assert lab.owner.execute("select execution_mode from workforce_runs where id=%s", (lab.runs[-1],)).fetchone() == ("legacy",)
