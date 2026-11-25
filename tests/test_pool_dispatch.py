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


def test_partial_setup_releases_only_its_own_logins(monkeypatch):
    import psycopg
    from pool_lab import Lab

    names = []
    original = Lab.login

    def fail_after_provision(lab, group):
        name, dsn = original(lab, group)
        names.append(name)
        if len(names) == 2:
            raise RuntimeError("synthetic failure during setup")
        return name, dsn

    monkeypatch.setattr(Lab, "login", fail_after_provision)
    dsn = os.environ["AMC_MIGRATION_DSN"]
    with pytest.raises(RuntimeError, match="synthetic failure during setup"):
        Lab(None, dsn)
    with psycopg.connect(dsn) as conn:
        assert len(names) == 2
        assert not conn.execute("select rolname from pg_roles where rolname=any(%s)", (names,)).fetchall()
        assert not conn.execute("select worker from amc_ops.routes where worker=any(%s)", (names,)).fetchall()


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
    from app.main import app
    from pool_lab import Lab, lab_client

    with lab_client(app) as api:
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


@pytest.fixture()
def one_run(pool_lab):
    lab = pool_lab
    lab.limit_x(10000)  # Keep the agency cap separate from the run's 1,000.
    lab.owner.execute("update workforce_runs set budget_microusd=1000 where id=%s", (lab.runs[0],))
    lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=%s", (lab.runs[1],))
    assert lab.dispatch(reserve=700)
    return lab


def exposure(lab):
    return lab.owner.execute(
        """
        select r.reserved_microusd, (select sum(l.held+l.spent) from amc_ops.attempts a
        join amc_ops.ledger l using(id) where a.run=r.id)
        from workforce_runs r where r.id=%s""",
        (lab.runs[0],),
    ).fetchone()


def sent_timeout(lab):
    worker, job = next((w, j) for w in lab.workers if (j := w.take()))
    assert worker.error(job, "timeout")
    assert lab.consume()
    lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (job["run"],))
    return job


def test_late_receipt_releases_run_budget_for_next_400(one_run):
    lab = one_run
    job = sent_timeout(lab)
    lab.bill(job, 350, "invoice")
    assert lab.dispatch(reserve=400)
    assert exposure(lab) == (750, 750)
    assert lab.balance_x() == (400, 350)


def test_unsent_rejects_receipts_without_financial_effect(one_run):
    lab = one_run
    rid = lab.runs[0]
    job = {"id": str(lab.owner.execute("select id from amc_ops.attempts where run=%s", (rid,)).fetchone()[0])}
    lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (rid,))
    assert lab.consume()
    for amount in (350, 0):
        assert lab.receipt(job, amount, "unsent").status_code == 409
    assert exposure(lab) == (0, 0)
    assert lab.owner.execute("select event from amc_ops.ledger where id=%s order by seq", (job["id"],)).fetchall() == [("hold",), ("unsent",)]


def test_overage_duplicate_and_refund_keep_run_retryable(one_run):
    lab = one_run
    job = sent_timeout(lab)
    lab.bill(job, 3_000_000_000, "overage")
    assert exposure(lab) == (3_000_000_000, 3_000_000_000)
    assert not lab.dispatch(reserve=400)
    assert lab.states()[0] == "queued"
    lab.bill(job, 0, "refund")
    lab.bill(job, 3_000_000_000, "overage")  # Replay after refund must not restore old spend.
    assert exposure(lab) == (0, 0)
    assert lab.dispatch(reserve=400)
    assert exposure(lab) == (400, 400)


def test_concurrent_receipts_and_dispatch_share_one_balance(one_run):
    from threading import Barrier

    lab = one_run
    job = sent_timeout(lab)
    barrier = Barrier(3)

    def bill():
        barrier.wait(timeout=10)
        return lab.receipt(job, 350, "same-receipt").status_code

    def dispatch():
        barrier.wait(timeout=10)
        return lab.dispatch(reserve=400)

    with ThreadPoolExecutor(max_workers=3) as executor:
        left, right, claim = executor.submit(bill), executor.submit(bill), executor.submit(dispatch)
        assert left.result() == right.result() == 200
        if not claim.result():
            assert lab.dispatch(reserve=400)
    assert exposure(lab) == (750, 750)
    assert lab.owner.execute("select count(*) from amc_ops.ledger where id=%s and event='receipt'", (job["id"],)).fetchone() == (1,)


def test_receipt_after_revocation_only_changes_finances(one_run):
    lab = one_run
    _, job = next((w, j) for w in lab.workers if (j := w.take()))
    lab.revoke_and_restore_a()
    assert lab.consume()
    assert exposure(lab) == (700, 700)
    lab.bill(job, 220, "withdrawn-invoice")
    assert exposure(lab) == (220, 220)
    assert lab.owner.execute(
        "select state,last_error,deliverable_id,json_array_length(checkpoints) from workforce_runs where id=%s", (job["run"],)
    ).fetchone() == ("failed", "recipient_revoked", None, 0)


def test_two_late_invoices_for_one_run_commit_independent_deltas(one_run):
    from threading import Barrier

    lab = one_run
    first = sent_timeout(lab)
    assert lab.dispatch(reserve=200)
    second = sent_timeout(lab)
    assert exposure(lab) == (900, 900)
    barrier = Barrier(2)

    def settle(job, amount, ref):
        barrier.wait(timeout=10)
        lab.bill(job, amount, ref)

    with ThreadPoolExecutor(max_workers=2) as executor:
        left = executor.submit(settle, first, 250, "first-invoice")
        right = executor.submit(settle, second, 150, "second-invoice")
        left.result()
        right.result()
    assert exposure(lab) == (400, 400)
    assert lab.balance_x() == (0, 400)
