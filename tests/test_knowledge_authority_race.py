"""Two live signed API transactions contend for the same scoped authority guard."""
from concurrent.futures import ThreadPoolExecutor
import os
from queue import Queue
from threading import Event
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from knowledge_fixtures import bundle, call, accepted
from test_verified_identity import wait_for_lock


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
@pytest.mark.parametrize("operation", ["qa", "share"])
@pytest.mark.parametrize("withdraw_first", [True, False])
def test_withdrawal_and_authorization_have_one_serial_order(api, operation, withdraw_first):
    actor, path, source, _, preview = bundle(api)
    terms = {"snapshot_id": preview["id"], "digest": preview["digest"]}
    parent = accepted(call(api, actor, path, "/authorize", operation="queue", **terms))
    if operation == "share":
        parent = accepted(call(api, actor, path, "/authorize", operation="qa", previous_receipt=parent["id"], **terms))

    def authorize():
        return call(api, actor, path, "/authorize", key=uuid4().hex, operation=operation, previous_receipt=parent["id"], **terms)

    def withdraw():
        return call(api, actor, path, f"/revisions/{source['id']}/events", state="withdrawn",
                    expected_digest=source["digest"], expected_sequence=1, reason="Fixture source withdrawn")

    # Hold the winner immediately before its actual COMMIT, after flushing its
    # normal command. Observe the other connection blocked inside PostgreSQL.
    entered = Queue()
    release = Event()

    def hold_first(session):
        if release.is_set():
            return
        session.flush()
        conn = session.connection()
        assert conn.scalar(text("select current_user")) == "amc_runtime"
        entered.put(conn.scalar(text("select pg_backend_pid()")))
        assert release.wait(timeout=12)

    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as observer, ThreadPoolExecutor(2) as pool:
        event.listen(Session, "before_commit", hold_first)
        try:
            a = pool.submit(withdraw if withdraw_first else authorize)
            try:
                locker = entered.get(timeout=6)
                b = pool.submit(authorize if withdraw_first else withdraw)
                wait_for_lock(observer, locker)
            finally:
                release.set()
                a.result(timeout=10)
            first, second = a.result(), b.result(timeout=10)
        finally:
            event.remove(Session, "before_commit", hold_first)
    assert first.is_success, first.text
    if withdraw_first:
        assert second.status_code == 409, second.text
    else:
        assert second.is_success, second.text
        receipt = first.json()
        historical = api.get(path + "/receipts/" + receipt["id"], headers=actor["headers"])
        assert historical.is_success and historical.json()["digest"] == preview["digest"]
        assert authorize().status_code == 409
