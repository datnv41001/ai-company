"""Labelled synthetic outputs. Compare exact finding sets, including unexpected warnings."""
from types import SimpleNamespace

import pytest

from app import workflow_dag
from app.registry import release
from app.workforce_gateway import validate_output
from app.workforce_worker import save_checkpoint
from migrations.runtime_bundle import canonical_hash


SOURCES = {"brand": {"excerpt": "A5 notebook for students."}, "S1": {"excerpt": "The notebook has 80 pages."}}
PAGE = {"headline": "Student sketchbook", "body_copy": "Students can sketch in this A5 notebook.", "call_to_action": "Explore the notebook"}
META = {"page_title": "Student sketchbook for class", "meta_description": "Explore a student sketchbook for notes and drawing in class.", "search_intent": "student sketchbook"}
LIMITS = {"page_title": [12, 70], "meta_description": [30, 170]}


def checkpoint(monkeypatch, skill, changes, *, source=None, limits=None):
    binding = release()
    contract = binding["contracts"][skill]
    contract.update(qa_policy=skill + "-qa@2", adapter=skill + ("@2" if skill == "content" else "@3"))
    if skill == "seo":
        contract["qa_limits"] = limits or LIMITS
    sources = {**SOURCES, **({"S1": {"excerpt": source}} if source else {})}
    output = validate_output({**(PAGE if skill == "content" else META), **changes, "source_ids": ["S1"]}, skill, [], sources)
    parent = validate_output({**PAGE, "source_ids": ["brand"]}, "content", [], sources)
    run = SimpleNamespace(id="run-a", knowledge={"registry": {**binding, "manifest_digest": "a"*64}, "sources": sources,
        "objective": "Students sketch during class", "offer": "A5 notebook", "audience": "students",
        "brand_rules": "Avoid: miracle"}, checkpoints=[{"output": {"plan_digest": "b"*64}}])
    node = SimpleNamespace(id="n03", revision=1, skill=skill)
    records = []
    monkeypatch.setattr(workflow_dag, "checkpoint", lambda db, run, node, record: records.append(record))
    db = SimpleNamespace(execute=lambda *args: [("n01", parent)])
    save_checkpoint(db, None, run, skill, output, node)
    return records[0]["quality"]["role_qa"], output


@pytest.mark.parametrize("skill,changes,source,expected", [
    ("content", {}, None, set()),
    ("content", {"call_to_action": "Student sketchbook"}, None, {"cta_action"}),
    ("content", {"body_copy": "Students love this miracle notebook."}, None, {"brand_instruction"}),
    ("content", {"headline": "Ocean cruise", "body_copy": "Ocean cruises depart nightly.", "call_to_action": "Book a cruise"},
     None, {"brief_alignment", "brand_alignment"}),
    ("content", {"body_copy": "The best notebook."}, "Customer feedback did not say it was the best notebook.", {"claim_evidence"}),
    ("content", {"body_copy": "The best notebook."}, "The best notebook. This was one student's opinion.", {"quote_context"}),
    ("content", {"body_copy": "Students save 90% with this notebook."}, None, {"claim_evidence"}),
    ("seo", {}, None, set()),
    ("seo", {"search_intent": "cruise tickets"}, None, {"intent_alignment"}),
    ("seo", {"page_title": "Island cruise deals"}, None, {"page_alignment"}),
    ("seo", {"meta_description": META["page_title"]}, None, {"duplicate_metadata", "metadata_length"}),
    ("seo", {"meta_description": "Student sketchbook search volume is 9000."}, None, {"claim_evidence"}),
])
def test_labelled_role_findings(monkeypatch, skill, changes, source, expected):
    report, output = checkpoint(monkeypatch, skill, changes, source=source)
    assert {f["rule_id"] for f in report["findings"]} == expected
    assert report["scope"] == "node_checkpoint" and report["node_id"] == "n03"
    assert report["output_digest"] == canonical_hash(output)
    assert report["plan_digest"] == "b"*64 and report["manifest_digest"] == "a"*64
    assert report["contract_digest"] and report["role_id"] == release()["contracts"][skill]["role_id"]
    for finding in report["findings"]:
        assert finding["rule_version"] == 2 and finding["node_id"] == "n03"
        assert finding["field"] in output["sections"] and finding["evidence"] and finding["status"] == "needs_review"
        assert finding["severity"] in ("warning", "info") and set(finding["source_ids"]) <= SOURCES.keys()


def test_seo_length_is_pinned_configuration(monkeypatch):
    report, _ = checkpoint(monkeypatch, "seo", {}, limits={**LIMITS, "page_title": [40, 80]})
    assert [(f["rule_id"], f["field"]) for f in report["findings"]] == [("metadata_length", "page_title")]
