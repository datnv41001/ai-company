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
