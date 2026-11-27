"""Exercise buyer-authorized openings through WF-08/2 workers, scoped editing and independent QA."""

from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from app import storyboard_brief as brief, storyboard_runtime as runtime, video_storyboard as video
from app.knowledge_store import canonical, digest
from knowledge_fixtures import accepted
from test_c3_authority import doc_and_decision
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_storyboard_editions import inputs
from test_video_storyboard import CASES, start, work

pool = registry_pool
CASES_BY_ACTION = {case["buyer_action"]: case for case in CASES}
# Independent Vietnamese buyer vocabulary from the three signed synthetic briefs.
# An approved price in a later card is not another conversion. Apply this oracle only to the hook.
ACTION_WORDS = {
    "rfq": ("báo giá",),
    "appointment": ("hẹn", "đặt lịch", "đề nghị khảo sát"),
    "choose_session": ("buổi", "chọn lớp"),
}
WRONG_CONVERSION = {
    "rfq": ("đặt lịch", "lịch hẹn", "đề nghị khảo sát", "chọn buổi", "buổi học"),
    "appointment": ("báo giá", "chọn buổi", "buổi học", "chọn lớp"),
    "choose_session": ("báo giá", "đặt lịch", "lịch hẹn", "đề nghị khảo sát"),
}
REQUEST = {"rfq": "Nhận yêu cầu báo giá", "appointment": "Nhận đề nghị đặt lịch", "choose_session": "Thu nhận lựa chọn buổi"}
PREPARE = {"appointment": "Giúp người mua chuẩn bị đề nghị đặt lịch", "choose_session": "Giúp người học chọn buổi"}
CTA = {"rfq": "Yêu cầu báo giá", "appointment": "Gửi đề nghị khảo sát", "choose_session": "Chọn buổi"}


def assert_authorized_opening(hook, action):
    words = " ".join(hook.casefold().split())
    assert any(term in words for term in ACTION_WORDS[action]), (action, hook)
    assert not any(term in words for term in WRONG_CONVERSION[action]), (action, hook)


def save_evidence(name, value):
    if folder := os.getenv("AMC_SEMANTIC_EVIDENCE"):
        target = Path(folder)
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


@PG
@pytest.mark.parametrize("action", ["choose_session", "appointment", "rfq"])
@pytest.mark.parametrize("style", ["formal", "concise", "friendly", "plain"])
def test_signed_hook_semantics_through_independent_qa(pool, action, style):
    case = CASES_BY_ACTION[action]
    purpose = f"{REQUEST[action]} {case['product']}"
    intent = dict(editorial_style=style, requirements=[brief.ILLUSTRATE, brief.PROOF],
                  acceptance_criteria=[brief.CAPTIONS, brief.COMMERCIAL])
    base, editor, buyer, _, snapshot, queued = start(
        pool, case | {"objective": purpose}, release=runtime.RELEASE, intent_overrides=intent,
    )
    api, rid = pool.api, queued["id"]
    reviewer = reader(api, editor, "admin")
    assert reviewer["id"] != editor["id"]
    states = []
    for stage in ("director", "content", "storyboard"):
        work(pool, rid, stage, states)
    run_url = base + "/workforce/runs/" + rid
    url = run_url + "/storyboard-edition"
    trace = accepted(api.get(run_url, headers=editor["headers"]))
    content = trace["checkpoints"][1]["output"]
    plan = json.loads(content["sections"]["content_handoff"])
    raw = json.loads(trace["checkpoints"][2]["output"]["text"])
    doc, baseline = doc_and_decision(pool, base, editor, rid)
    assert raw["content_handoff_digest"] == content["text"] == digest(canonical(plan))
    assert raw["hook"] == plan["channel_copy"]["opening"] and raw["cta"] == plan["channel_copy"]["action"]
    assert raw["source_refs"]["manifest"] == plan["manifest"] == {"id": snapshot["id"], "digest": snapshot["digest"]}
    raw_decision = accepted(api.post(doc + "/review", headers=reviewer["headers"], json=baseline))
    edit = dict(expected_qa_revision=baseline["expected_qa_revision"],
                expected_content_digest=baseline["expected_content_digest"], mode="controlled_hook", hook_variant="style_alternate")
    assert api.post(url, headers=buyer["headers"], json=edit).status_code in (403, 404)
    updated = accepted(api.post(url, headers=editor["headers"], json=edit))
    board = updated["storyboard"]
    comparison = updated["receipt"]["comparison"]
    assert comparison["changed_variables"] == ["hook"] and comparison["baseline_holds"] == comparison["candidate_holds"]
    assert board["shots"][1:] == raw["shots"][1:] and board["hook"] != raw["hook"]
    assert all(raw[field] == board[field] for field in ("rights", "cta", "source_refs", "content_handoff_digest"))
    assert board["buyer_action"] == raw["buyer_action"] == action
    assert updated["revision"] == baseline["expected_qa_revision"] + 1
    assert updated["content_digest"] != baseline["expected_content_digest"]
    accepted(api.post(doc + "/submit", headers=editor["headers"]))
    assert api.post(doc + "/review", headers=reviewer["headers"], json=baseline).status_code == 412
    decision = accepted(api.post(doc + "/review", headers=reviewer["headers"], json=baseline | inputs(updated)))
    assert raw_decision["status"] == decision["status"] == "approved"
    assert raw_decision["reviewed_by"] == decision["reviewed_by"] == reviewer["id"]
    qa_rows = pool.owner.execute(
        "select id, actor, result from knowledge_commands where operation='c3_qa' and snapshot_id=%s order by effective_at",
        (snapshot["id"],),
    ).fetchall()
    assert [row[2]["content_digest"] for row in qa_rows] == [baseline["expected_content_digest"], updated["content_digest"]]
    assert all(row[1] == reviewer["id"] for row in qa_rows)
    evidence = dict(action=action, style=style, signed_intent=snapshot["projection"]["task_intent"],
                    source_facts=snapshot["projection"]["facts"], run=rid, manifest=plan["manifest"], content=plan,
                    original=raw, alternate=board, edit_receipt=updated["receipt"], qa=qa_rows,
                    worker_journal=trace["journal"], provenance=accepted(api.get(trace["marketing_provenance"], headers=editor["headers"])))
    save_evidence(f"{action}-{style}", evidence)
    # An approved service price may occur in protected declarations. Check only buyer-facing
    # opening words here: a booking or class selection has no authority to solicit quotations.
    assert raw["cta"] == CTA[action]
    for candidate in (board, raw):
        assert candidate["brief_fulfillment"]["ready_for_qa"]
        assert_authorized_opening(candidate["hook"], action)


@PG
@pytest.mark.parametrize("action,has_terms", [("appointment", True), ("choose_session", False)])
def test_commercial_instruction_cannot_authorize_an_rfq(pool, action, has_terms):
    case = CASES_BY_ACTION[action]
    purpose = f"{PREPARE[action]} {case['product']}"
    intent = dict(editorial_style="formal", requirements=[brief.TERMS], acceptance_criteria=[brief.CAPTIONS, brief.COMMERCIAL])
    base, owner, _, _, snap, queued = start(pool, case | {"objective": purpose}, release=runtime.RELEASE, intent_overrides=intent)
    rid = queued["id"]
    for stage in ("director", "content", "storyboard"):
        work(pool, rid, stage, [])
    trace = accepted(pool.api.get(base + "/workforce/runs/" + rid, headers=owner["headers"]))
    plan = json.loads(trace["checkpoints"][1]["output"]["sections"]["content_handoff"])
    board = json.loads(trace["checkpoints"][2]["output"]["text"])
    reviewer = reader(pool.api, owner, "admin")
    doc, baseline = doc_and_decision(pool, base, owner, rid)
    response = pool.api.post(doc + "/review", headers=reviewer["headers"], json=baseline)
    rows = {row["field"]: row for row in board["brief_fulfillment"]["rows"]}
    source_terms = [f for f in snap["projection"]["facts"] if (f.get("price") or {}).get("conditions")]
    assert bool(source_terms) is has_terms
    save_evidence("terms-" + action, dict(signed=snap["projection"]["task_intent"], content=plan, board=board,
                                          qa_status=response.status_code, qa_revision=baseline,
                                          qa_result=response.json().get("detail", response.json().get("status")),
                                          reviewer=reviewer["id"], manifest=plan["manifest"], run=rid, journal=trace["journal"]))
    assert response.status_code == (200 if has_terms else 409), response.text
    assert rows["requirements[0]"]["status"] == ("met" if has_terms else "clarify")
    assert rows["acceptance_criteria[1]"]["status"] == "met"  # absence of a price is disclosed
    assert board["brief_fulfillment"]["ready_for_qa"] is has_terms
    # Asking for information about quote conditions does not change the target conversion.
    assert "báo giá" not in plan["channel_copy"]["opening"].casefold()
    assert "lời mời báo giá" not in plan["production_direction"].casefold()
    assert board["hook"] == plan["channel_copy"]["opening"] and board["cta"] == plan["channel_copy"]["action"]
    for fact in source_terms:
        before_cta = " ".join(s["voice"] for s in board["shots"] if fact["id"] in s["source_ids"] and
                              s["end_s"] <= board["shots"][-1]["start_s"])
        assert all(condition in before_cta for condition in fact["price"]["conditions"])


@pytest.mark.parametrize("wrong", ["Quý vị cần báo giá?", "Quý vị muốn đặt lịch hẹn?"])
def test_qa_recomputes_purpose_after_a_foreign_conversion_opening(wrong):
    case = CASES_BY_ACTION["choose_session"]
    purpose = f"{REQUEST['choose_session']} {case['product']}"
    projection = dict(product=case["product"], audience=case["audience"], objective=purpose, brand=case["brand"],
                      channel="vertical-social", locale="vi-VN", brand_guidelines={"digest": "c" * 64, "guidance": "Câu ngắn."},
                      facts=[dict(id="F1", category="description", wording=case["wording"], qualifiers=[case["qualifier"]])],
                      task_intent=dict(purpose=purpose, buyer_action="choose_session", rights=video.RIGHTS, exclusions=[],
                                       duration_seconds=18, editorial_style="formal", requirements=[brief.ILLUSTRATE],
                                       acceptance_criteria=[brief.CAPTIONS, brief.COMMERCIAL]))
    original = runtime.compose(projection, {"id": "synthetic-regression", "digest": "a" * 64}, release=runtime.RELEASE)
    runtime.require_fulfillment(original, projection)
    for mismatch in ("hook", "spoken", "caption", "all"):
        current = deepcopy(original)
        if mismatch in ("hook", "all"):
            current["hook"] = wrong
        if mismatch in ("spoken", "all"):
            current["shots"][0]["voice"] = wrong
        if mismatch in ("caption", "all"):
            current["shots"][0]["caption"] = wrong
        current["vtt"] = video.captions(current["shots"])
        # A saved formerly-green assessment cannot authorize a different current opening.
        with pytest.raises(ValueError):
            runtime.require_fulfillment(current, projection)
        current["brief_fulfillment"] = brief.assessment(projection, current)
        assert current["cta"] == "Chọn buổi"
        assert not current["brief_fulfillment"]["ready_for_qa"], mismatch
        with pytest.raises(ValueError):
            runtime.require_fulfillment(current, projection)
