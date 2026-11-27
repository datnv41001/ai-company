"""Controlled RS-02 research diagnostics. All source records are synthetic."""
import json
import os
from pathlib import Path

import pytest

import campaign_planner_fixtures as planner
from agency_fixtures import postgres_api
from app import c3_assets, c3_order_units, c3_skill_library, c3_studio, measurement_integrity
from app.c3_tasks import ActionIntent
from app.workforce_gateway import GatewayError
from knowledge_fixtures import accepted
from strategy_runtime_fixtures import INTENT, PRODUCT, commission_lab, prepare_review, studio_save
from test_strategy_runtime_handoff import check_content_readback, terms

DATA = Path(__file__).resolve().parents[1] / "docs/evaluation/rs02"
CASES = json.loads((DATA / "controlled-briefs.json").read_bytes())


def inputs(api, agency, case):
    owner, base, ((customer, scope), _) = agency
    campaign = next(iter(scope["campaigns"]))
    brands = accepted(api.get(base + "/campaigns", headers=owner["headers"]))
    brand = next(row["brand_id"] for row in brands if row["id"] == campaign)
    return planner.prepare_inputs(api, owner, customer, next(iter(scope["clients"])), brand, campaign,
                                  case, workflows=(c3_assets.RESEARCH,))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_scoped_measurement_and_editorial_sources(api, agency, case):
    snapshots, setup = inputs(api, agency, case)
    projection = snapshots[0]["projection"]
    action = ActionIntent.model_validate(projection["task_intent"]).buyer_action
    assert action == case["buyer_action"]
    evidence = {f["id"]: f for f in projection["facts"]}
    raw = {"positioning": "Nêu điều kiện trước khi gửi yêu cầu.", "rationale": "Giúp người mua kiểm tra phần còn thiếu.",
           "channel_choice": "web", "test_hypothesis": "Thử trình bày hướng dẫn trước lời mời.",
           "measurable_action": "Một hành động khác do worker đề xuất.", "measurement_method": "Đề xuất đếm biểu mẫu theo phiên.",
           "source_ids": [next(iter(evidence))]}
    with pytest.raises(GatewayError, match="invalid_source"):
        c3_skill_library.validate({**raw, "source_ids": ["ABSENT"]}, "strategy", {}, evidence)
    checkpoints = {"strategy": c3_skill_library.validate(raw, "strategy", {}, evidence)}
    sections = c3_order_units.artifacts(c3_assets.RESEARCH, projection, checkpoints)
    groups = c3_studio.compose(c3_assets.RESEARCH, projection, checkpoints)
    assert groups["research"]["evidence"] == "\n".join(row["text"] for row in sections["evidence_report"]["facts"])
    assert all(s in groups["research"]["evidence"] for s in (case["wording"], case["qualifier"]))
    assert groups["measurement"]["measurable_action"] == c3_studio.buyer_action(projection) != raw["measurable_action"]
    method = groups["measurement"]["measurement_method"]
    assert sections["measurement_plan"]["measurement_method"] == raw["measurement_method"]
    if action == "appointment":
        contract = projection["measurement_contract"]
        assert contract["id"] == setup["selections"]["kpi"] and contract["revision"] == 1 and len(contract["digest"]) == 64
        assert (contract["numerator"]["event"], contract["denominator"]["event"]) == ("confirmed", "requested")
        assert (contract["window_days"], contract["aggregation"]) == (18, "distinct_appointment_id")
        assert method == measurement_integrity.statement(contract, projection["locale"]) != raw["measurement_method"]
        assert not measurement_integrity.quality_issues(groups, projection)
        groups["measurement"]["measurement_method"] = raw["measurement_method"]
        assert measurement_integrity.quality_issues(groups, projection)
    else:
        assert "measurement_contract" not in projection
        assert measurement_integrity.expected_statement(projection) is None
        assert method == raw["measurement_method"]
        assert "qualified" not in method and "execution_authorized" not in sections["measurement_plan"]


def test_rfq_cannot_bind_appointment_definition(api, agency, monkeypatch):
    def capture_rejection(api, author, setup):
        result = api.post(setup["marketing"] + "/manifests", headers=author["headers"], json=setup["params"])
        assert result.status_code == 409 and "requires an approved appointment brief" in result.text
        return result.status_code

    monkeypatch.setattr(planner, "capture", capture_rejection)
    snapshots, _ = inputs(api, agency, {**CASES[1], "measurement": CASES[0]["measurement"]})
    assert snapshots == [409]


@pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Requires disposable PostgreSQL roles")
def test_edited_interview_question_documents_evidence_hold():
    example = json.loads((DATA / "editor-example.json").read_bytes())
    with postgres_api() as api, commission_lab(api) as ctx:
        projection = ctx["snap"]["projection"]
        sources = {f["id"]: f for f in projection["facts"]}
        raw = {**ctx["raw"]["research"], "buyer_problem": example["observation"],
               "research_question": example["question"], "evidence_needed": example["evidence_needed"]}
        research = c3_skill_library.validate(raw, "research", {}, sources)
        sections = c3_order_units.artifacts(c3_assets.RESEARCH, projection, {"research": research})
        assert sections["research_notes"]["fields"]["evidence_needed"] == example["evidence_needed"]
        groups = c3_studio.compose(c3_assets.RESEARCH, projection, {"research": research})
        groups["strategy"].update(positioning=PRODUCT, channel_choice="web")
        saved = studio_save(api, ctx, groups)
        assert saved["groups"]["research"]["research_question"] == example["question"]
        reviewer = ctx["reviewer"]["headers"]
        accepted(api.post(ctx["doc"] + "/submit", headers=ctx["author"]["headers"]))
        evidence = accepted(api.get(ctx["doc"] + "/content-evidence", headers=reviewer))
        flagged = [row["text"] for row in evidence["statements"] if row["field"] == "studio.research.research_question"
                   and row["outcome"] == "unresolved"]
        assert " ".join(flagged) == example["question"]
        denied = api.post(ctx["studio"] + "/approvals", headers=reviewer, json={
            "group": "research", "expected_revision": saved["revision"], "expected_asset_digest": saved["asset_digests"]["research"],
            "note": "Check hold for a newly edited interview prompt."})
        assert denied.status_code == 409
        assert accepted(api.get(ctx["studio"] + "/content-handoff", headers=reviewer))["work_order"] is None


@pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Requires disposable PostgreSQL roles")
def test_decision_example_qualified_internal_handoff():
    example = json.loads((DATA / "editor-example.json").read_bytes())
    with postgres_api() as api, commission_lab(api) as ctx:
        reviewed = prepare_review(api, ctx)
        endpoint = ctx["studio"] + "/content-handoff"
        reviewer = ctx["reviewer"]["headers"]
        ready = accepted(api.get(endpoint, headers=reviewer))
        assert ready["revision"] == reviewed["studio"]["revision"]
        decision = {**terms(ready, ctx), **example["decision_fields"]}
        assert decision["observation_excerpt"] == example["observation"]
        assert api.post(endpoint, headers=ctx["author"]["headers"], json=decision).status_code == 403
        signed = accepted(api.post(endpoint, headers=reviewer, json=decision))
        received = accepted(api.get(endpoint, headers=ctx["recipient"]["headers"]))
        check_content_readback(signed, received, decision, INTENT)
        assert received["work_order"]["measurement"]["execution_authorized"] is False
