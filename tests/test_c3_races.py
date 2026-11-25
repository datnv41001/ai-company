"""Observe PostgreSQL blocking before committing the actual Marketing side effects."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from queue import Queue
from threading import Event

import psycopg
import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app import c3_marketing
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from test_c3_authority import doc_and_decision, run_workers, setup_pool
from test_registry import PG, pool as registry_pool
from test_verified_identity import wait_for_lock

pool = registry_pool


@PG
@pytest.mark.parametrize("stage", ["queue","qa","share"])
@pytest.mark.parametrize("first", ["decision","withdrawal"])
def test_serial_authority_on_side_effect(pool, stage, first):
    lab=pool
    api=lab.api
    base,owner,*_=lab.cases[0]
    path,terms,data,snap=setup_pool(lab)
    def enqueue():
        return api.post(path,headers=owner["headers"],json=terms)
    decide=enqueue
    if stage!="queue":
        rid=accepted(enqueue())["id"]
        run_workers(lab,rid,c3_marketing.LANDING)
        doc,qa=doc_and_decision(lab,base,owner,rid)
        def approval():
            return api.post(doc+"/review",headers=owner["headers"],json=qa)
        decide=approval
        if stage=="share":
            accepted(approval())
            deadline=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
            def share():
                return api.post(doc+"/share",headers=owner["headers"],json={"expires_at":deadline,
                                "expected_qa_revision":qa["expected_qa_revision"],"expected_content_digest":qa["expected_content_digest"]})
            decide=share
    blocked,release=Queue(),Event()
    def gate(session):
        if release.is_set():
            return
        session.flush()
        blocked.put(session.connection().scalar(text("select pg_backend_pid()")))
        assert release.wait(35)
    def retire():
        return withdraw(api,owner,data)
    winner,loser=(decide,retire) if first=="decision" else (retire,decide)
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"],autocommit=True) as observer,ThreadPoolExecutor(2) as executor:
        event.listen(Session,"before_commit",gate)
        try:
            ahead=executor.submit(winner)
            try:
                lock=blocked.get(timeout=25)
                later=executor.submit(loser)
                wait_for_lock(observer,lock)
            finally:
                release.set()
            assert ahead.result(timeout=30).is_success
            result=later.result(timeout=30)
        finally:
            event.remove(Session,"before_commit",gate)
    expected_count=int(first=="decision")
    assert result.is_success if expected_count else result.status_code==409
    count=lab.owner.execute("select count(*) from knowledge_commands where snapshot_id=%s and operation=%s",(snap["id"],"c3_"+stage)).fetchone()[0]
    assert count==expected_count
    if stage=="queue":
        assert lab.owner.execute("select count(*) from workforce_runs where brief_id=%s",(data["params"]["target"]["brief_id"],)).fetchone()[0]==expected_count
