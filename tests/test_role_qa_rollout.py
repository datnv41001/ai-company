"""Exercise role QA via real pool mailboxes and the review/portal API on PostgreSQL."""

import json
import os
from pathlib import Path

import psycopg
import pytest

from app.pool_worker import report
from migrations.apply import publish_registry
from migrations.runtime_bundle import canonical_hash
from pool_model_smoke import receipts
from test_adapter_rollout import specialist
from test_diamond import take_node
from test_dynamic_plan import node
from test_registry import frozen_run, pool as registry_pool_fixture, registry_brief
from test_role_qa import PAGE


pool = registry_pool_fixture
pytestmark = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="requires PostgreSQL")
RELEASE = Path(__file__).resolve().parents[1] / "catalog/landing-seo-v4.json"
WORKFLOW = "WF-13/landing-seo-draft@4"


def activate_qa(lab):
    manifest = json.loads(RELEASE.read_text(encoding="utf-8"))
    with lab.owner.transaction():
        publish_registry(lab.owner, manifest)
    base, admin, _, _, campaign = lab.cases[0]
    lab.api.put(
        base + "/workforce/registry/" + campaign, headers=admin["headers"], json={"workflow": WORKFLOW, "skills": manifest["required"], "action": "activate"}
    ).raise_for_status()


def post_output(lab, rid, skill, raw):
    worker, job = take_node(lab)
    assert job["run"] == rid and job["body"]["response_format"]["json_schema"]["name"] == skill
    assert report(worker.conn, job, [raw, 100, 35]) and lab.consume()
    return job["id"]


def test_rollout_parent_binding_fencing_and_review_history(pool):
    lab = pool
    base, admin, reader, _, _ = lab.cases[0]
    headers = admin["headers"]
    old = frozen_run(lab)
    specialist(lab, old, "content")
    activate_qa(lab)
    specialist(lab, old, "seo")

    def trace(rid):
        return lab.api.get(base + "/workforce/runs/" + rid, headers=headers).json()

    assert [s["quality"]["role_qa"]["policy"] for s in trace(old)["checkpoints"]] == ["director@1", "content@1", "seo@1"]
    receipts(lab, [(old, lab.cases[0], "historical")])

    def history():
        return (
            trace(old)["checkpoints"],
            trace(old)["approved_assets"],
            lab.owner.execute("select l.* from amc_ops.ledger l join amc_ops.attempts a using(id) where a.run=%s order by seq", (old,)).fetchall(),
            lab.owner.execute(
                """select e.* from review_entries e join client_reviews r on r.id=e.review_id
                    join workforce_runs w on w.deliverable_id=r.deliverable_id where w.id=%s order by e.id""",
                (old,),
            ).fetchall(),
        )

    baseline = history()
    path, terms = registry_brief(lab)
    rid = lab.api.post(path, headers=headers, json={**terms, "registry_workflow": WORKFLOW, "max_parallel_nodes": 1}).json()["id"]
    proposal = [node("alpha", "content"), node("other", "content"), node("meta", "seo", ["alpha"])]
    post_output(lab, rid, "planner", {"nodes": proposal})
    # One source ID belongs to neither this run nor its immutable source registry.
    bad = post_output(lab, rid, "content", {**PAGE, "source_ids": ["other-campaign"]})
    assert lab.owner.execute("select outcome from amc_ops.attempts where id=%s", (bad,)).fetchone()[0] == "invalid_source"
    assert len(trace(rid)["checkpoints"]) == 1
    lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (rid,))
    # Retrying alpha may let its sibling run first. Identify the work by the
    # actual mailbox assignment, independent of scheduling order.
    for _ in range(3):
        worker, job = take_node(lab)
        assert job["run"] == rid
        if job["body"]["response_format"]["json_schema"]["name"] == "seo":
            raw = {
                "page_title": "Tropical cruises by sea",
                "meta_description": "Explore tropical cruises departing every week.",
                "search_intent": "tropical cruises",
                "source_ids": ["S1"],
            }
        elif json.loads(job["body"]["messages"][1]["content"])["assignment"].endswith("alpha"):
            raw = {**PAGE, "source_ids": ["brand"]}
        else:
            raw = {"headline": "Tropical cruises", "body_copy": "Sail in tropical waters.", "call_to_action": "Tropical cruises", "source_ids": ["S1"]}
        assert report(worker.conn, job, [raw, 100, 35]) and lab.consume()
    result = trace(rid)
    first, sibling, seo = result["checkpoints"][1:]
    a, b, s = [p["quality"]["role_qa"] for p in (first, sibling, seo)]
    assert first["node_id"] == a["node_id"] == "n01" and b["node_id"] == "n02"
    assert a["source_ids"] == ["brand"] and b["source_ids"] == ["S1"]
    assert not any(f["rule_id"] == "cta_action" for f in a["findings"])
    assert any(f["rule_id"] == "cta_action" for f in b["findings"])
    assert s["content_parents"] == {a["node_id"]: canonical_hash(first["output"])}
    assert {f["rule_id"] for f in s["findings"]} >= {"page_alignment", "intent_alignment"}
    for p in (a, b, s):
        assert p["plan_digest"] == result["registry"]["plan_digest"] and p["manifest_digest"] == result["registry"]["manifest_digest"]
        assert p["run_id"] == rid and p["policy"] in ("content-qa@2", "seo-qa@2")
    doc = base + "/deliverables/" + result["deliverable_id"]
    for actor in (reader, lab.cases[1][2], lab.cases[2][2], lab.y):
        assert lab.api.get(base + "/workforce/runs/" + rid, headers=actor["headers"]).status_code == 404
        assert lab.api.get(doc, headers=actor["headers"]).status_code == 404
        with psycopg.connect(os.environ["DATABASE_URL"].replace("+psycopg", "")) as db:
            db.execute("select set_config('amc.user_id',%s,true),set_config('amc.tenant_id',%s,true)", (actor["id"], admin["tenant"]))
            assert db.execute("select checkpoints from workforce_runs where id=%s", (rid,)).fetchone() is None

    original = lab.api.get(doc, headers=headers).json()
    proof = {"expected_content_digest": original["qa_evidence"]["content_digest"], "expected_qa_revision": original["qa_revision"]}
    assert original["status"] == "submitted" and original["qa_evidence"]["scope"] == "delivery_revision"
    for copy in ("The best.", original["content"]["client_preview"]):
        draft = lab.api.patch(doc + "/draft", headers=headers, json={"title": original["title"], "client_preview": copy})
        draft.raise_for_status()
        revision = lab.api.get(doc, headers=headers).json()["qa_evidence"]
        assert revision["scope"] == "delivery_revision" and all("node_id" not in f for f in revision["findings"])
        if copy == "The best.":
            assert any(f["claim"] == copy and f["status"] == "needs_evidence" for f in revision["findings"])
    lab.api.post(doc + "/submit", headers=headers).raise_for_status()
    assert revision["content_digest"] == proof["expected_content_digest"] and revision["qa_revision"] > proof["expected_qa_revision"]
    assert lab.api.post(doc + "/review", headers=headers, json={"decision": "approved", **proof}).status_code == 412
    assert trace(rid)["checkpoints"] == result["checkpoints"] and history() == baseline
    # An authorized reader sees the archived client preview. Other clients cannot
    # fetch it by its known ID, and original checkpoint evidence stays internal.
    snapshot = base + "/reviews/" + baseline[1][0]["id"]
    own = lab.api.get(snapshot, headers=reader["headers"])
    own.raise_for_status()
    assert own.json()["status"] == "approved" and "quality" not in own.json() and "checkpoints" not in own.json()
    for actor in (lab.cases[1][2], lab.cases[2][2], lab.y):
        assert lab.api.get(snapshot, headers=actor["headers"]).status_code == 404


@pytest.mark.parametrize("change", [{"qa_policy": "content-qa@2"}, {"qa_limits": {"page_title": [-1, 70]}}, {"qa_policy": "seo@1"}])
def test_publisher_refuses_mismatched_policy_or_limits(change):
    manifest = json.loads(RELEASE.read_text(encoding="utf-8"))
    manifest["contracts"]["seo"].update(change)
    from app.registry_compatibility import validate_manifest

    with pytest.raises(ValueError):
        validate_manifest(manifest)
