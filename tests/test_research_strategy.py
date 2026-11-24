"""WF-03 acceptance through publisher, pool, human QA and the client portal."""

import json
from pathlib import Path

import pytest

from migrations.apply import publish_registry
from migrations.runtime_bundle import canonical_hash
from pool_model_smoke import receipts
from test_dynamic_plan import node
from test_registry import PG, policy, pool as registry_pool, registry_brief
from test_role_qa_rollout import post_output

pool = registry_pool
MANIFEST = Path(__file__).resolve().parents[1] / "catalog/research-strategy-v1.json"
WORKFLOW = "WF-03/research-strategy-draft@1"


def read_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_witness_and_terminal_contract():
    from app.registry_compatibility import validate_manifest

    manifest = read_manifest()
    validate_manifest(manifest)
    manifest["contracts"]["strategy"]["predecessors"] = []
    with pytest.raises(ValueError):
        validate_manifest(manifest)


def start_research(lab):
    lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=any(%s)", (lab.runs,))
    manifest = read_manifest()
    publish_registry(lab.owner, manifest)
    policy(lab, "activate", skills=manifest["required"], workflow=WORKFLOW).raise_for_status()
    path, terms = registry_brief(lab, objective="Research the supplied notebook evidence and propose a measurable strategy for students.")
    response = lab.api.post(path, headers=lab.x["headers"], json={**terms, "registry_workflow":WORKFLOW})
    response.raise_for_status()
    lab.runs = [response.json()["id"]]
    return lab.runs[0]


@PG
def test_research_scope_provenance_and_strategy_snapshot(pool):
    lab = pool
    rid = start_research(lab)
    base, admin, reader, *_ = lab.cases[0]
    url = base + "/workforce/runs/" + rid
    for actor in (reader, lab.cases[1][2], lab.y):
        assert lab.api.get(url, headers=actor["headers"]).status_code == 404
    post_output(lab, rid, "planner", {"nodes":[node("facts","research"),node("plan","strategy",["facts"])]})
    from app.research_strategy import KPI_FIELDS
    source = lab.api.get(url,headers=admin["headers"]).json()["source_registry"]["brand"]["excerpt"]
    post_output(lab, rid, "research", {"observed_fact":source,"audience_hypothesis":"Internal untested hypothesis","knowledge_gap":"Missing monthly sales","source_ids":["brand"]})
    raw = dict.fromkeys(KPI_FIELDS, "unknown")
    raw.update(positioning="Propose a student pilot", proposed_channel="Campus newsletter", success_metric="Sign-up rate",
               metric_kind="ratio", unit="percent", measurement_window="30 days", measurement_method="Count completed forms",
               proposed_target="Target for discussion", numerator="completed forms", denominator="unknown",
               baseline="unverified historical sales", baseline_source="brand", source_ids=["brand"])
    post_output(lab, rid, "strategy", raw)
    trace = lab.api.get(url,headers=admin["headers"]).json()
    research, strategy = trace["checkpoints"][1:]
    qa = strategy["quality"]["role_qa"]
    assert qa["research_parents"] == {research["node_id"]:canonical_hash(research["output"])}
    assert {f["rule_id"] for f in qa["findings"]} >= {"ratio_denominator","baseline_evidence"}
    assert trace["graph"]["contract"]["required"] == ["strategy"]
    receipts(lab,[(rid,lab.cases[0],"WF-03")])
    snap = lab.api.get(url,headers=admin["headers"]).json()["approved_assets"][0]
    route = base + "/reviews/" + snap["id"]
    snapshot = lab.api.get(route,headers=reader["headers"]).json()
    assert "Propose a student pilot" in snapshot["preview"]
    assert "Internal untested hypothesis" not in snapshot["preview"] and "unverified historical sales" not in snapshot["preview"]
    assert lab.api.get(route,headers=lab.cases[1][2]["headers"]).status_code == 404
