import copy
import json
import os
from pathlib import Path

import pytest

from app import storyboard_brief as brief, storyboard_runtime as runtime, video_storyboard as legacy
from app.knowledge_store import canonical, digest
from knowledge_fixtures import accepted
from test_c3_authority import doc_and_decision
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_video_storyboard import CASES, start, work

pool = registry_pool
TRAY = next(c for c in CASES if c["id"] == "index-tray")
TAG = TRAY | dict(id="swatch-tag", company="Xưởng Nhãn Thử", brand="Mép Giấy", product="Thẻ so màu Mép Giấy", sku="MG-4",
                 audience="Người phụ trách nhà in", wording="Thẻ có ô ghi mã màu", qualifier="Áp dụng cho bản giấy mẫu.",
                 hypotheses=["Cần phỏng vấn để biết người phụ trách đối chiếu mã màu ở bước nào."], exclusions=["bền màu tuyệt đối"])
REF = {"id": "synthetic-unit-test", "digest": "a" * 64}


@PG
def test_corrupt_handoff_stops_after_one_verified_attempt(pool, monkeypatch):
    from app import workforce_worker
    from app.pool_worker import report, run_job
    from test_diamond import take_node

    case, intent = case_input(TRAY)
    base, owner, _, _, _, queued = start(pool, case, release=runtime.RELEASE, intent_overrides=intent)
    rid = queued["id"]
    work(pool, rid, "director", [])
    work(pool, rid, "content", [])
    # Simulate an integration regression while constructing the *next* envelope.
    # The already persisted Content checkpoint remains available for diagnosis.
    original = workforce_worker.node_request

    def with_incorrect_handoff(*args, **kwargs):
        return original(*args, **kwargs) | {"content_digest": "0" * 64}

    monkeypatch.setattr(workforce_worker, "node_request", with_incorrect_handoff)
    worker, job = take_node(pool)
    assert job["run"] == rid and job["body"]["stage"] == "storyboard"
    reply = run_job(pool.config, job["body"])
    assert reply == ({"blocked": "storyboard_invalid_checkpoint"}, 0, 0)
    assert report(worker.conn, job, list(reply)) and pool.consume()
    result = accepted(pool.api.get(base + "/workforce/runs/" + rid, headers=owner["headers"]))
    failure = result["journal"][-1]
    assert result["state"] == "failed" and result["deliverable_id"] is None
    assert failure["outcome"] == "storyboard_invalid_checkpoint" and failure["attempt"] == 1
    assert failure["recovery"] == "inspect_checkpoint_integrity_before_new_run"
    assert [c["skill"] for c in result["checkpoints"]] == ["director", "content"]


def case_input(case, prepare=False):
    objective = brief.PURPOSES["rfq"][int(prepare)] + " " + case["product"]
    return case | {"objective": objective}, {
        "editorial_style": "formal" if prepare else "plain",
        "requirements": [brief.ILLUSTRATE, brief.TERMS if prepare else brief.PROOF],
        "acceptance_criteria": [brief.CAPTIONS, brief.COMMERCIAL],
    }


def test_same_rfq_different_brief_and_tampered_predecessor():
    p = dict(product=TAG["product"], audience=TAG["audience"], brand=TAG["brand"], channel="vertical-social", locale="vi-VN",
             brand_guidelines={"digest": "c" * 64, "guidance": "Câu ngắn."},
             facts=[{"id":"F1", "category":"description", "wording":TAG["wording"], "qualifiers":[TAG["qualifier"]]}])
    original, inputs = case_input(TAG)
    p["objective"] = original["objective"]
    p["task_intent"] = inputs | dict(purpose=p["objective"], buyer_action="rfq", rights=legacy.RIGHTS, exclusions=[], duration_seconds=32)
    first = runtime.compose(p, REF, release=runtime.RELEASE)
    runtime.require_fulfillment(first, p)
    second = copy.deepcopy(p)
    changed, other = case_input(TAG, prepare=True)
    second["objective"] = changed["objective"]
    second["task_intent"].update(**other, purpose=second["objective"])
    alternate = runtime.compose(second, REF, release=runtime.RELEASE)
    assert first["hook"] != alternate["hook"] and first["shots"][0]["visual"] != alternate["shots"][0]["visual"]
    assert first["cta"] == alternate["cta"] and first["source_refs"] == alternate["source_refs"]
    assert not alternate["brief_fulfillment"]["ready_for_qa"]  # missing commercial authority
    with pytest.raises(ValueError):
        runtime.require_fulfillment(alternate, second)
    with pytest.raises(legacy.GatewayError, match="storyboard_invalid_checkpoint"):
        runtime.execute(dict(local_adapter=runtime.ADAPTER, stage="storyboard", context=second, manifest=REF,
                             content_digest=first["content_handoff_digest"]))
    second["task_intent"].update(purpose="Tăng doanh thu gấp đôi", requirements=[brief.ILLUSTRATE + " Bao gồm âm thanh.", "Thu âm lời thoại."])
    blocked = runtime.compose(second, REF, release=runtime.RELEASE)
    statuses = {r["field"]: r["status"] for r in blocked["brief_fulfillment"]["rows"]}
    assert statuses["purpose"] == statuses["requirements[0]"] == "clarify" and statuses["requirements[1]"] == "unsupported"
    assert all("doanh thu" not in s["voice"] for s in blocked["shots"])


@PG
@pytest.mark.parametrize("case,prepare,blocked", [(TRAY, False, False), (TAG, True, False), (TAG, False, True)],
                         ids=["product-proof", "new-print-quote", "clarify-and-unsupported"])
def test_content_checkpoint_handoff_and_current_qa(pool, case, prepare, blocked):
    case, intent = case_input(case, prepare)
    if blocked:
        intent.update(requirements=[brief.ILLUSTRATE, "Thu âm lời thoại."], acceptance_criteria=["Người xem sẽ nhớ thương hiệu."])
    base, owner, _, _, snap, queued = start(pool, case, release=runtime.RELEASE, intent_overrides=intent)
    rid = queued["id"]
    states = []
    for stage in ("director", "content", "storyboard"):
        work(pool, rid, stage, states)
    trace = accepted(pool.api.get(base + "/workforce/runs/" + rid, headers=owner["headers"]))
    assert trace["plan"] == ["director", "content", "storyboard"] and trace["state"] == "awaiting_qa"
    assert all(row["provider"] == "deterministic" and row["model"] == runtime.ADAPTER and row["input_tokens"] == row["output_tokens"] == 0
               for row in trace["journal"])
    content = trace["checkpoints"][1]["output"]
    plan = json.loads(content["sections"]["content_handoff"])
    board = json.loads(trace["checkpoints"][2]["output"]["text"])
    assert plan["role"] == "ai-copywriter-content-strategist" and plan["audience"] == case["audience"]
    assert content["text"] == board["content_handoff_digest"] == digest(canonical(plan))
    assert plan["channel_copy"]["opening"] == board["hook"] and plan["channel_copy"]["action"] == board["cta"]
    assert plan["channel_copy"]["declarations"][0]["lines"][0] == case["wording"]
    assert plan["angle"] == ("quote_conditions" if prepare else "show_evidence")
    assert board["brief_fulfillment"]["ready_for_qa"] is not blocked
    qa = reader(pool.api, owner, "admin")
    doc, terms = doc_and_decision(pool, base, owner, rid)
    decision = pool.api.post(doc + "/review", headers=qa["headers"], json=terms)
    assert decision.status_code == (409 if blocked else 200), decision.text
    if folder := os.getenv("AMC_BRIEF_EVIDENCE"):
        destination = Path(folder) / (case["id"] + ("-needs-clarification" if blocked else ""))
        destination.mkdir(parents=True, exist_ok=False)
        rows = dict(brief=snap["projection"]["task_intent"], content=plan, raw=board,
                    receipt=dict(run_id=rid, workflow=runtime.RELEASE, manifest=plan["manifest"], handoff_digest=content["text"],
                                 journal=trace["journal"], document_id=trace["deliverable_id"], revision=terms["expected_qa_revision"],
                                 digest=terms["expected_content_digest"], qa_status=decision.status_code,
                                 reviewer_id=qa["id"], review_decision="approved" if not blocked else "blocked",
                                 reviewed_body=decision.json().get("content", {}).get("client_preview") if not blocked else None))
        for name, value in rows.items():
            (destination / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")
