"""Registry v14 acceptance on isolated agency/campaign data."""

import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dynamic_plan import compile_plan, InvalidPlan
from pool_lab import Lab
from test_dynamic_plan import node

WORKFLOW = "WF-13/landing-seo-draft@1"
PG = pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="PostgreSQL registry")


def test_registry_compiler_pins_identity_and_limits_skills():
    binding = {"workflow": WORKFLOW, "manifest_digest": "a" * 64, "skills": ["director", "content", "seo"]}
    proposal = {"nodes": [node("copy", "content"), node("meta", "seo", ["copy"])]}
    plan, digest = compile_plan(proposal, ["content", "seo"], binding)
    assert plan["registry"] == binding
    assert compile_plan(proposal, ["content", "seo"], {**binding, "manifest_digest": "b" * 64})[1] != digest
    with pytest.raises(InvalidPlan):
        compile_plan({"nodes": [node("facts", "research"), node("copy", "content", ["facts"]), node("meta", "seo", ["copy"])]}, ["content", "seo"], binding)


@PG
def test_publication_and_version_immutability():
    from migrations.apply import publish_registry
    from copy import deepcopy
    from app.registry import release

    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
        manifest = release()
        publish_registry(db, manifest)
        changed = deepcopy(manifest)
        changed["contracts"]["seo"]["node_cap"] += 1
        with pytest.raises(ValueError):
            publish_registry(db, changed)
    with psycopg.connect(os.environ["DATABASE_URL"].replace("+psycopg", "")) as db:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute("delete from amc_ops.registry_releases")


@pytest.fixture
def pool():
    with TestClient(app) as api:
        lab = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow="dynamic-v1")
        try:
            yield lab
        finally:
            lab.close()


def registry_brief(lab, idx=0, objective="Write notebook landing page copy and matching SEO metadata for students."):
    base, admin, reader, _, campaign = lab.cases[idx]
    api = lab.api
    bid = api.post(
        base + "/workforce/briefs", headers=admin["headers"], json={"title": "Landing page draft", "recipient_id": reader["id"], "campaign_id": campaign}
    ).json()["id"]
    path = base + "/workforce/briefs/" + bid
    from test_workforce import DATA

    api.put(
        path + "/submission", headers=reader["headers"], json={**DATA, "objective": objective}
    ).raise_for_status()
    return path + "/run", {"workflow": "dynamic-v1", "registry_workflow": WORKFLOW, "budget_microusd": 10000, "max_parallel_nodes": 2}


def policy(lab, mode, idx=0, actor=None, skills=("director", "content", "seo"), workflow=WORKFLOW):
    base, admin, _, _, campaign = lab.cases[idx]
    return lab.api.put(
        base + "/workforce/registry/" + campaign, headers=(actor or admin)["headers"], json={"workflow": workflow, "action": mode, "skills": list(skills)}
    )


@PG
def test_activation_scope_disable_revoke_and_legacy_trace(pool):
    lab = pool
    base, admin, reader, *_ = lab.cases[0]

    def start(i):
        path, terms = registry_brief(lab, i)
        return lab.api.post(path, headers=admin["headers"], json=terms)

    assert start(0).status_code == 409
    assert policy(lab, "activate", actor=reader).status_code in (403, 404)
    assert policy(lab, "activate", actor=lab.y).status_code in (403, 404)
    policy(lab, "activate").raise_for_status()
    with psycopg.connect(os.environ["DATABASE_URL"].replace("+psycopg", "")) as conn:
        for actor, tenant, expected in [(reader, admin["tenant"], 0), (lab.y, lab.y["tenant"], 0), (admin, admin["tenant"], 3)]:
            conn.execute("select set_config('amc.user_id',%s,true),set_config('amc.tenant_id',%s,true)", (actor["id"], tenant))
            assert conn.execute("select count(*) from amc_ops.registry_grants where campaign=%s", (lab.cases[0][-1],)).fetchone() == (expected,)
    assert start(1).status_code == 409
    run = start(0).json()["id"]

    def report(rid):
        return lab.api.get(base + "/workforce/runs/" + rid, headers=admin["headers"]).json()

    assert report(lab.runs[0])["registry"]["status"] == "legacy_v13"
    assert report(run)["registry"]["workflow"] == WORKFLOW
    policy(lab, "disable").raise_for_status()
    assert start(0).status_code == 409 and report(run)["state"] == "queued"
    policy(lab, "revoke").raise_for_status()
    policy(lab, "activate").raise_for_status()
    assert report(run)["state"] == "failed"


def frozen_run(lab, workflow=WORKFLOW):
    from app.pool_worker import report
    from test_diamond import take_node

    lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=any(%s)", (lab.runs,))
    policy(lab, "activate").raise_for_status()
    path, terms = registry_brief(lab)
    rid = lab.api.post(path, headers=lab.x["headers"], json={**terms, "registry_workflow": workflow}).json()["id"]
    w, j = take_node(lab)
    assert j["run"] == rid
    assert report(w.conn, j, [{"nodes": [node("copy", "content"), node("meta", "seo", ["copy"])]}, 100, 30]) and lab.consume()
    return rid


@PG
def test_node_budget_receipt_refund_and_trace(pool):
    lab = pool
    rid = frozen_run(lab)
    for w in lab.workers:
        w.take()
    assert lab.dispatch(reserve=700)
    w = next(w for w in lab.workers if (job := w.take()))
    assert w.error(job, "timeout") and lab.consume()
    lab.owner.execute("update amc_ops.dag_nodes set ready_at=now() where run=%s", (rid,))
    for w in lab.workers:
        w.take()
    assert not lab.dispatch(reserve=400)
    lab.bill(job, 1050, "overage")
    assert not lab.dispatch(reserve=1)
    lab.bill(job, 350, "refund")
    lab.bill(job, 350, "refund")
    assert lab.dispatch(reserve=400)
    info = lab.api.get(lab.cases[0][0] + "/workforce/runs/" + rid, headers=lab.x["headers"]).json()
    detail = next(n for n in info["registry"]["nodes"] if n["skill_id"] == "content")
    assert detail["exposure"] == 750 and detail["role_id"] == "ai-copywriter-content-strategist"
    assert str(job["id"]) in detail["attempt_ids"] and info["registry"]["plan_digest"] == info["graph"]["digest"]


@PG
@pytest.mark.parametrize("revoke_first", [True, False])
@pytest.mark.parametrize("qa2", [False, True])
def test_revoke_checkpoint_commit_order(pool, monkeypatch, revoke_first, qa2):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app import pool_dispatch
    from test_diamond import take_node

    lab = pool
    workflow = WORKFLOW
    if qa2:
        from test_role_qa_rollout import WORKFLOW as qa_workflow, activate_qa
        activate_qa(lab)
        workflow = qa_workflow
    rid = frozen_run(lab, workflow)
    w, j = take_node(lab)
    from app.pool_worker import report

    assert report(
        w.conn,
        j,
        [{"headline": "Student notebook", "body_copy": "A notebook for study", "call_to_action": "Read the product card", "source_ids": ["S1"]}, 90, 36],
    )
    entered, release = Event(), Event()
    original = pool_dispatch.lock_scheduler

    def hold(db):
        if revoke_first:
            entered.set()
            assert release.wait(10)
        original(db)
        if not revoke_first:
            entered.set()
            assert release.wait(10)

    if qa2 and not revoke_first:
        from app import landing_qa
        assess_node = landing_qa.evaluate_node

        def pause_after_qa(*args):
            result = assess_node(*args)
            entered.set()
            assert release.wait(10)
            return result

        monkeypatch.setattr(landing_qa, "evaluate_node", pause_after_qa)
    else:
        monkeypatch.setattr(pool_dispatch, "lock_scheduler", hold)
    with ThreadPoolExecutor(max_workers=2) as executor:
        cp = executor.submit(lab.consume)
        assert entered.wait(10)
        rv = executor.submit(policy, lab, "revoke", workflow=workflow)
        if revoke_first:
            rv.result(10).raise_for_status()
        release.set()
        assert cp.result(10)
        rv.result(10).raise_for_status()
    saved = lab.owner.execute("select checkpoint is not null from amc_ops.dag_nodes where run=%s and node_id='n01'", (rid,)).fetchone()[0]
    assert saved == (not revoke_first)
    assert lab.owner.execute("select state,deliverable_id from workforce_runs where id=%s", (rid,)).fetchone() == ("failed", None)


@pytest.mark.parametrize(
    "skill,field,bad,good",
    [
        ("research", "observed_fact", "Outsells every competitor", "A5 notebook"),
        ("strategy", "success_metric", "Excellent performance", "Weekly sign-up count"),
        ("content", "call_to_action", "Student notebook", "Read the product card"),
        ("seo", "meta_description", "Search volume of 9000", "Explore the A5 notebook for students"),
    ],
)
def test_specialist_policy_and_closed_outputs(skill, field, bad, good):
    from app.registry import release
    from app.registry_qa import assess_role
    from app.workforce_gateway import validate_output, GatewayError

    contract = release()["contracts"][skill]
    sources = {"brand": {"excerpt": "A5 notebook"}}
    raw = {k: "Student notebook" for k in contract["outputs"]}
    raw.update(source_ids=["brand"])

    def findings(value):
        raw[field] = value
        output = validate_output(raw, skill, [], sources, {"contracts": {skill: contract}})
        return assess_role(skill, output, sources, contract)["findings"]

    assert findings(bad) and not findings(good)
    with pytest.raises(GatewayError):
        validate_output({**raw, "unexpected": True}, skill, [], sources, {"contracts": {skill: contract}})
    with pytest.raises(GatewayError):
        validate_output({**raw, "source_ids": ["foreign"]}, skill, [], sources, {"contracts": {skill: contract}})


@PG
def test_publishing_second_release_preserves_running_version(pool):
    from migrations.apply import publish_registry
    from app.registry import release

    lab = pool
    rid = frozen_run(lab)
    base, admin, _, _, campaign = lab.cases[0]
    report_path = base + "/workforce/runs/" + rid
    before = lab.api.get(report_path, headers=admin["headers"]).json()["registry"]
    second = release()
    second["workflow_version"] = 2
    with lab.owner.transaction():
        publish_registry(lab.owner, second)
    ref = second["workflow_id"] + "@2"
    lab.api.put(
        base + "/workforce/registry/" + campaign, headers=admin["headers"], json={"workflow": ref, "action": "activate", "skills": second["required"]}
    ).raise_for_status()
    path, terms = registry_brief(lab)
    started = lab.api.post(path, headers=admin["headers"], json={**terms, "registry_workflow": ref})
    started.raise_for_status()
    after = lab.api.get(base + "/workforce/runs/" + started.json()["id"], headers=admin["headers"]).json()["registry"]
    assert before["workflow_version"] == 1 and after["workflow_version"] == 2
    assert before["manifest_digest"] != after["manifest_digest"]
    assert lab.api.get(report_path, headers=admin["headers"]).json()["registry"] == before
