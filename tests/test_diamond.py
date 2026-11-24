"""PostgreSQL acceptance for the opt-in frozen diamond."""

import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.main import app
from app.pool_worker import report
from pool_lab import Lab, lab_client
from test_workforce import call_model

pytestmark = pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires PostgreSQL")


@pytest.fixture
def diamond():
    with lab_client(app) as api:
        lab = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow="diamond-v1")
        try:
            lab.configure(lab.y, 10000, False)
            lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=%s", (lab.runs[1],))
            assert all(w.take() is None for w in lab.workers)
            yield lab
        finally:
            lab.close()


def graph(lab):
    base, admin, *_ = lab.cases[0]
    return lab.api.get(base + "/workforce/runs/" + lab.runs[0], headers=admin["headers"]).json()["graph"]


def take_node(lab):
    for w in lab.workers:
        assert w.take() is None
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(lambda _: lab.dispatch(), range(2))) == [False, True]
    return next((w, j) for w in lab.workers if (j := w.take()))


def complete(lab, expected, invalid=False):
    w, job = take_node(lab)
    body = job["body"]
    assert body["response_format"]["json_schema"]["name"] == expected
    context = json.loads(body["messages"][1]["content"])
    if expected in ("content", "seo"):
        assert list(context["earlier_drafts"]) == ["strategy"]
    sibling = {"content": "seo", "seo": "content"}.get(expected)
    if sibling:
        assert f"checkpoint-{sibling}-only" not in json.dumps(body)
    result = list(call_model(None, body))
    for key in list(result[0]):
        if isinstance(result[0][key], str):
            result[0][key] += f" checkpoint-{expected}-only"
    if invalid:
        result[0]["source_ids"] = ["unknown-source"]
    assert report(w.conn, job, result)
    assert not report(w.conn, job, result)
    assert lab.consume()
    lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (job["run"],))


@pytest.mark.parametrize("seo_first", [False, True])
def test_diamond_join_and_sibling_isolation(diamond, seo_first):
    lab = diamond

    def ready():
        return {n["node_id"] for n in graph(lab)["nodes"] if n["status"] == "ready"}

    assert ready() == {"director"}
    complete(lab, "director")
    assert ready() == {"research"}
    complete(lab, "research")
    assert ready() == {"strategy"}
    complete(lab, "strategy")
    assert ready() == {"content", "seo"}
    complete(lab, "content", invalid=seo_first)
    assert lab.states()[0] == "queued"
    complete(lab, "seo")
    if seo_first:
        assert lab.states()[0] == "queued"
        complete(lab, "content")
    assert lab.states()[0] == "awaiting_qa"
    run = lab.owner.execute("select checkpoints,deliverable_id from workforce_runs where id=%s", (lab.runs[0],)).fetchone()
    assert [p["node_id"] for p in run[0]] == ["director", "research", "strategy", "content", "seo"]
    base, admin, *_ = lab.cases[0]
    draft = lab.api.get(base + "/deliverables/" + run[1], headers=admin["headers"]).json()
    preview = "\n\n".join(p["skill"].upper() + "\n" + p["output"]["text"] for p in run[0] if p["skill"] != "director")
    from app.revision_qa import content_digest

    assert draft["qa_evidence"]["workflow"] == {"template": "diamond-v1", "revision": 1}
    assert draft["content"]["client_preview"] == preview
    assert draft["qa_evidence"]["content_digest"] == content_digest(draft["title"], preview)
    assert all(n["status"] == "succeeded" for n in graph(lab)["nodes"])
    assert lab.owner.execute("select count(*) from deliverables where id=%s", (run[1],)).fetchone() == (1,)


def test_failed_branch_blocks_join_and_preserves_other_checkpoint(diamond):
    lab = diamond
    for skill in ("director", "research", "strategy", "content"):
        complete(lab, skill)
    for _ in range(3):
        complete(lab, "seo", invalid=True)
    nodes = {n["node_id"]: n for n in graph(lab)["nodes"]}
    assert nodes["content"]["attempts"] == 1 and nodes["content"]["status"] == "succeeded"
    assert nodes["seo"]["status"] == "failed" and nodes["seo"]["error"] == "invalid_source"
    assert nodes["join"]["status"] == "blocked" and nodes["join"]["missing"] == ["seo"]
    assert lab.owner.execute("select state,deliverable_id,json_array_length(checkpoints) from workforce_runs where id=%s", (lab.runs[0],)).fetchone() == (
        "failed",
        None,
        4,
    )


def test_crash_during_join_can_replay_only_once(diamond, monkeypatch):
    from app import workforce_worker

    lab = diamond
    for stage in ("director", "research", "strategy", "content"):
        complete(lab, stage)
    w, job = take_node(lab)
    assert w.complete(job)

    def crash(*_):
        raise RuntimeError("simulated loss before commit")

    with monkeypatch.context() as patch:
        patch.setattr(workforce_worker, "evaluate", crash)
        with pytest.raises(RuntimeError, match="before commit"):
            lab.consume()
    assert lab.owner.execute("select count(*) from deliverables where campaign_id=%s", (lab.cases[0][-1],)).fetchone() == (0,)
    assert lab.consume()
    assert not lab.consume() and not w.complete(job)
    assert lab.owner.execute("select count(*) from deliverables where campaign_id=%s", (lab.cases[0][-1],)).fetchone() == (1,)


@pytest.mark.parametrize("withdraw", [True, False])
def test_late_branch_result_never_opens_join(diamond, withdraw):
    lab = diamond
    for stage in ("director", "research", "strategy", "content"):
        complete(lab, stage)
    for worker in lab.workers:
        assert worker.take() is None
    assert lab.dispatch(reserve=700)
    w, job = next((w, j) for w in lab.workers if (j := w.take()))
    if withdraw:
        lab.revoke_and_restore_a()
    else:
        lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (job["run"],))
    assert not w.complete(job)
    assert lab.consume()
    assert lab.balance_x() == (700, 0)
    lab.bill(job, 350, "late-diamond")
    assert lab.balance_x() == (0, 350)
    assert lab.owner.execute(
        "select reserved_microusd,deliverable_id,json_array_length(checkpoints) from workforce_runs where id=%s", (job["run"],)
    ).fetchone() == (350, None, 4)


def test_frozen_topology_and_scope_enforcement(diamond):
    import psycopg

    lab = diamond
    rid = lab.runs[0]
    for case in lab.cases[1:]:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            lab.owner.execute(
                """insert into amc_ops.dag_edges select tenant,client,brand,campaign,%s,revision,'seo','research'
                from amc_ops.dag_plans where campaign=%s""",
                (rid, case[-1]),
            )
    with pytest.raises(psycopg.errors.UniqueViolation):
        lab.owner.execute("insert into amc_ops.dag_nodes select * from amc_ops.dag_nodes where run=%s and node_id='seo'", (rid,))
    for change in (
        "delete from amc_ops.dag_edges where child='join' and run=%s",
        "delete from amc_ops.dag_edges where child='seo' and run=%s",
        """insert into amc_ops.dag_edges select tenant,client,brand,campaign,run,revision,'strategy','seo'
                      from amc_ops.dag_plans where run=%s""",
    ):
        with lab.owner.transaction(force_rollback=True):
            lab.owner.execute(change, (rid,))
            assert not lab.owner.execute("select amc_ops.valid_diamond(%s)", (rid,)).fetchone()[0]
    assert lab.owner.execute("select amc_ops.valid_diamond(%s)", (rid,)).fetchone()[0]
    for w in lab.workers:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            w.conn.execute("select checkpoint from amc_ops.dag_nodes")
    base, admin, reader, *_ = lab.cases[0]
    for actor in (reader, lab.y):
        assert lab.api.get(base + "/workforce/runs/" + rid, headers=actor["headers"]).status_code == 404
    brief = lab.owner.execute("select brief_id from workforce_runs where id=%s", (rid,)).fetchone()[0]
    invalid = lab.api.post(base + "/workforce/briefs/" + brief + "/run", headers=admin["headers"], json={"workflow": "diamond-v1", "edges": []})
    assert invalid.status_code == 422


def test_dag_timeout_retry_and_financial_fencing(diamond):
    lab = diamond
    for w in lab.workers:
        assert w.take() is None
    assert lab.dispatch(reserve=700)
    w, job = next((w, j) for w in lab.workers if (j := w.take()))
    assert w.error(job, "timeout") and lab.consume()
    assert lab.balance_x() == (700, 0)
    lab.bill(job, 350, "director-invoice")
    lab.bill(job, 350, "director-invoice")
    assert lab.balance_x() == (0, 350)
    lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (job["run"],))
    complete(lab, "director")
    director = next(n for n in graph(lab)["nodes"] if n["node_id"] == "director")
    assert (director["attempts"], director["spent"], director["held"]) == (2, 350, 0)


def test_canonical_digest_matches_across_both_completion_orders(diamond):
    lab = diamond

    def finish_copy(seo_first):
        for stage in ("director", "research", "strategy"):
            complete(lab, stage)
        complete(lab, "content", invalid=seo_first)
        complete(lab, "seo")
        if seo_first:
            complete(lab, "content")

    def draft(rid):
        return lab.owner.execute(
            """select d.content->>'client_preview',d.qa_evidence->>'content_digest'
            from workforce_runs r join deliverables d on r.deliverable_id=d.id where r.id=%s""",
            (rid,),
        ).fetchone()

    finish_copy(False)
    first = draft(lab.runs[0])
    # A fresh brief with identical title, facts and deterministic model output.
    lab.seed("A", lab.x)
    finish_copy(True)
    assert first and draft(lab.runs[-1]) == first
