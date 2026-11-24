import json
import os

from fastapi.testclient import TestClient
import pytest

from app import workflow_dag
from app.main import app
from app.pool_worker import report
from pool_lab import Lab
from test_diamond import take_node
from test_dynamic_plan import node

pytestmark = pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires PostgreSQL")


@pytest.fixture
def lab():
    with TestClient(app) as api:
        pool = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow="dynamic-v1")
        try:
            pool.configure(pool.y, 10000, False)
            pool.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=%s", (pool.runs[1],))
            yield pool
        finally:
            pool.close()


def snapshot(lab):
    rid = lab.runs[0]
    return lab.owner.execute(
        """select digest,(select count(*) from amc_ops.tasks where run=p.run),
        (select count(*) from amc_ops.attempts where run=p.run and step>0)
        from amc_ops.dag_plans p where run=%s""",
        (rid,),
    ).fetchone()


def test_invalid_planner_is_metered_without_specialist_work(lab):
    worker, job = take_node(lab)
    assert report(worker.conn, job, [{"nodes": []}, 120, 30])
    assert lab.consume()
    assert snapshot(lab) == (None, 1, 0)
    assert lab.owner.execute(
        """select outcome,input_tokens,output_tokens,
        (select count(*) from amc_ops.ledger where id=a.id and event='usage')
        from amc_ops.attempts a where run=%s""",
        (job["run"],),
    ).fetchone() == ("invalid_plan", 120, 30, 1)


def test_freeze_crash_replay_and_distinct_copy_tasks(lab, monkeypatch):
    rid = lab.runs[0]
    worker, job = take_node(lab)
    proposal = {"nodes": [node("facts", "research"), node("email", "content"), node("page", "content", ["facts"])]}
    assert report(worker.conn, job, [proposal, 90, 36])
    freeze = workflow_dag.freeze

    def interrupted(*args):
        freeze(*args)
        raise RuntimeError("before freeze commit")

    with monkeypatch.context() as patch:
        patch.setattr(workflow_dag, "freeze", interrupted)
        with pytest.raises(RuntimeError, match="before freeze commit"):
            lab.consume()
    assert snapshot(lab) == (None, 1, 0)
    assert lab.consume() and not lab.consume()
    assert not report(worker.conn, job, [proposal, 90, 36])
    digest, tasks, specialists = snapshot(lab)
    assert len(digest) == 64 and tasks == 4 and specialists == 0
    base, admin, reader, *_ = lab.cases[0]
    path = base + "/workforce/runs/" + rid
    assert lab.api.get(path, headers=reader["headers"]).status_code == 404
    frozen = lab.api.get(path, headers=admin["headers"]).json()["graph"]
    assert frozen["phase"] == "frozen" and frozen["digest"] == digest
    for n in frozen["contract"]["nodes"]:
        w, j = take_node(lab)
        payload = json.loads(j["body"]["messages"][1]["content"])
        assert set(payload["earlier_drafts"]) == set(n["parents"])
        assert payload["assignment"] == n["assignment"]
        assert w.complete(j) and lab.consume()
    data = lab.api.get(path, headers=admin["headers"]).json()
    assert data["state"] == "awaiting_qa"
    copies = [p for p in data["checkpoints"] if p["skill"] == "content"]
    assert len({p["node_id"] for p in copies}) == 2
    assert lab.owner.execute("select count(distinct node_id) from amc_ops.attempts where run=%s and outcome='ok'", (rid,)).fetchone() == (4,)
    assert lab.owner.execute("select count(*) from deliverables where campaign_id=%s", (lab.cases[0][-1],)).fetchone() == (1,)
