"""A signed agency brief reaches a real PostgreSQL dispatcher, worker, document and independent QA."""

from datetime import timedelta
import json
import os
from pathlib import Path
from time import perf_counter

import pytest
from app import video_storyboard as video
from app.models import utcnow
from app.pool_worker import run_job, report
from app.storyboard_contract import release_manifest
from c3_fixtures import capture, prepared, withdraw
from c3_task_fixtures import INTENT
from campaign_planner_fixtures import facts
from knowledge_fixtures import accepted, revision
from migrations.apply import publish_registry
from test_c3_authority import doc_and_decision
from test_claim_desk import reader
from test_diamond import take_node
from test_registry import PG, policy, pool as registry_pool
from test_workforce import DATA

pool = registry_pool
ROOT = Path(__file__).resolve().parents[1]
BRIEFS = json.loads((ROOT / "tests/evaluation/department/briefs-v1.json").read_text(encoding="utf8"))
CASES = [c for group in BRIEFS.values() if isinstance(group, list) for c in group if isinstance(c, dict) and c.get("id") in ("index-tray", "receipt-map")]
THIRD = dict(
    id="rhythm-class",
    company="Lớp Nhạc Chậm",
    brand="Phách Mở",
    product="Buổi đọc nhịp Phách Mở",
    sku="PM-N",
    audience="Người lớn quay lại học nhạc",
    objective="Thu nhận lựa chọn buổi luyện đọc nhịp",
    kpi="Số lựa chọn được tiếp nhận",
    buyer_action="choose_session",
    wording="Bảng nhịp có ký hiệu phách mạnh và phách nhẹ.",
    qualifier="Áp dụng cho phần luyện đọc.",
)
CASES = [*CASES, THIRD]
assert len(CASES) == 3


def start(lab, case, *, conflicting=False):
    api = lab.api
    base, owner, buyer, client, campaign = lab.cases[0]
    lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=any(%s)", (lab.runs,))
    disk = json.loads((ROOT / "catalog/video-storyboard-v1.json").read_text(encoding="utf8"))
    assert disk == release_manifest()
    publish_registry(lab.owner, disk)
    publish_registry(lab.owner, disk)
    accepted(policy(lab, "activate", skills=["director", "storyboard"], workflow=video.RELEASE))
    root = base + "/workforce/briefs"
    payload = dict(campaign_id=campaign, recipient_id=buyer["id"], title=case["objective"])
    bid = accepted(api.post(root, headers=owner["headers"], json=payload))["id"]
    path = root + "/" + bid
    intent = (
        INTENT
        | {k: case[k] for k in ("product", "audience", "buyer_action")}
        | dict(
            purpose=case["objective"],
            channel="vertical-social",
            deliverable_type="video_storyboard",
            duration_seconds=18 if case["id"] == "rhythm-class" else 32,
            rights=video.RIGHTS,
            aspect_ratio="9:16",
            editorial_style="plain",
            requirements=["Soạn storyboard có hình minh họa."],
            exclusions=case.get("exclusions", []),
            acceptance_criteria=["Đối chiếu điều kiện thương mại theo đúng nguồn."],
        )
    )
    accepted(api.put(path + "/submission", headers=buyer["headers"], json=DATA | {"task_intent": intent}))
    brand = lab.owner.execute("select brand_id from campaigns where id=%s", (campaign,)).fetchone()[0]
    evidence = (
        facts(case | {"moq": "5" if case["id"] == "index-tray" else "1"})
        if "amount" in case
        else [{"wording": case["wording"], "qualifiers": [case["qualifier"]]}]
    )
    if case["id"] == "receipt-map":
        # This new synthetic price approval carries the service-specific condition.
        # The signed #58 control remains immutable.
        condition = "Người phụ trách xác nhận lịch sau khi nhận đề nghị."
        evidence[1]["price"]["conditions"] = [condition]
        evidence[1]["qualifiers"] = [condition]
    prep = prepared(api, owner, base, client, brand, campaign, bid, video.RELEASE, case=case | dict(channel=intent["channel"], facts=evidence))
    policy_text = dict(guidance="Liên kết mỗi cảnh với dữ kiện đã duyệt; dùng câu ngắn.")
    if conflicting:
        policy_text["prohibited_claims"] = [case["wording"]]
    guide = revision(api, owner, prep["path"], "video-brand-voice", "guidelines", policy_text)
    prep["params"]["guidelines"] = guide["id"]
    snap = capture(api, owner, prep)
    terms = dict(workflow="dynamic-v1", registry_workflow=video.RELEASE, budget_microusd=0, knowledge_manifest={"id": snap["id"], "digest": snap["digest"]})

    def queue(actor, body):
        return api.post(path + "/run", headers=actor["headers"], json=body)

    assert queue(lab.cases[1][2], terms).status_code in (403, 404)
    assert queue(owner, terms | {"knowledge_manifest": {"id": snap["id"], "digest": "0" * 64}}).status_code == 409
    if case["id"] == "rhythm-class" and not conflicting:
        # Same agency admin can see both campaigns, but a manifest captured for
        # another client/brand must never authorize this second brief.
        _, _, other_buyer, _, other_campaign = lab.cases[1]
        foreign = accepted(api.post(root, headers=owner["headers"], json=payload | {"campaign_id": other_campaign, "recipient_id": other_buyer["id"]}))
        other_path = root + "/" + foreign["id"]
        accepted(api.put(other_path + "/submission", headers=other_buyer["headers"], json=DATA | {"task_intent": intent}))
        assert api.post(other_path + "/run", headers=owner["headers"], json=terms).status_code == 404
    queued = accepted(queue(owner, terms))
    assert queued["state"] == "queued" and accepted(queue(owner, terms)) == queued
    return base, owner, buyer, prep, snap, queued


def work(lab, rid, stage, states, *, expect_error=False):
    w, job = take_node(lab)
    assert job["run"] == rid and job["body"]["stage"] == stage
    states.append({"stage": stage, "attempt": job["id"], "state": "running"})
    reply = run_job(lab.config, job["body"])
    assert reply[1:] == (0, 0)
    if expect_error:
        assert reply[0] == {"blocked": "storyboard_needs_revision"}
    else:
        assert "blocked" not in reply[0]
    assert report(w.conn, job, list(reply))
    assert lab.consume()


@PG
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_queued_storyboard_and_revised_qa(pool, case):
    lab, api = pool, pool.api
    base, owner, buyer, prep, snap, queued = start(lab, case)
    rid = queued["id"]
    staff = reader(api, owner, "editor")
    qa = reader(api, owner, "admin")
    states = [queued]
    t = perf_counter()
    work(lab, rid, "director", states)
    work(lab, rid, "storyboard", states)
    runtime_ms = round((perf_counter() - t) * 1000, 2)
    url = base + "/workforce/runs/" + rid
    trace = accepted(api.get(url, headers=owner["headers"]))
    assert trace["state"] == "awaiting_qa" and trace["plan"] == ["director", "storyboard"]
    states.append({"state": trace["state"], "document": trace["deliverable_id"]})
    for actor in (buyer, lab.cases[1][2], lab.y):
        assert api.get(url, headers=actor["headers"]).status_code == 404
    raw = json.loads(trace["checkpoints"][-1]["output"]["text"])
    assert (
        raw["brand"] == case["brand"]
        and raw["product"] == case["product"]
        and raw["shots"][-1]["end_s"] == snap["projection"]["task_intent"]["duration_seconds"]
    )
    assert raw["buyer_action"] == snap["projection"]["task_intent"]["buyer_action"]
    assert all(raw["source_refs"]["declarations"][f["id"]]["wording"] == f["wording"] for f in snap["projection"]["facts"])
    assert raw["rights"] == video.RIGHTS and all(j["model"] == video.ADAPTER and j["provider"] == "deterministic" for j in trace["journal"])
    assert trace["reserved_microusd"] == 0 and all(j["input_tokens"] == j["output_tokens"] == 0 for j in trace["journal"])
    assert raw["vtt"] == video.captions(raw["shots"])
    copy = " ".join(s["voice"] for s in raw["shots"])
    assert case["wording"].rstrip(".") in copy
    if "amount" in case:
        assert "Giá tham khảo" in copy and str(case["amount"])[:3] in copy and "thuế" in copy and "tối thiểu" in copy
    else:
        assert raw["editorial"]["price_status"] == "unavailable" and raw["editorial"]["price_source_ids"] == []
        assert "Chưa có giá được duyệt." in raw["editorial"]["note"]
        assert "giá" not in copy.casefold() and "giá" not in raw["vtt"].casefold() and "VND" not in copy
        assert not any(s["purpose"] in ("scope", "terms") for s in raw["shots"])
    doc, old = doc_and_decision(lab, base, owner, rid)
    inputs = {k: v for k, v in old.items() if k.startswith("expected_")}
    assert api.post(url + "/storyboard-edition", headers=staff["headers"], json=inputs | {"hook_variant": "audience"}).status_code == 404
    edited = accepted(api.post(url + "/storyboard-edition", headers=owner["headers"], json=inputs | {"hook_variant": "audience"}))
    assert edited["storyboard"]["hook"] != raw["hook"]
    assert api.post(url + "/storyboard-edition", headers=owner["headers"], json=inputs | {"hook_variant": "direct"}).status_code == 412
    accepted(api.post(doc + "/submit", headers=staff["headers"]))
    assert api.post(doc + "/review", headers=qa["headers"], json=old).status_code == 412
    terms = old | dict(expected_qa_revision=edited["revision"], expected_content_digest=edited["content_digest"])
    reviewed = accepted(api.post(doc + "/review", headers=qa["headers"], json=terms))
    assert reviewed["status"] == "approved" and reviewed["reviewed_by"] == qa["id"]
    assert (
        api.post(
            doc + "/share",
            headers=owner["headers"],
            json={
                "expires_at": (utcnow() + timedelta(days=1)).isoformat(),
                "expected_qa_revision": edited["revision"],
                "expected_content_digest": edited["content_digest"],
            },
        ).status_code
        == 409
    )
    provenance = accepted(api.get(trace["marketing_provenance"], headers=owner["headers"]))
    receipt = dict(
        case=case["id"],
        scope=dict(
            tenant=owner["tenant"],
            campaign_objective=snap["projection"]["task_intent"]["purpose"],
            campaign_id=prep["params"]["target"]["campaign_id"],
            brief_id=prep["params"]["target"]["brief_id"],
        ),
        run_id=rid,
        states=states,
        registry=trace["registry"],
        original_revision=old["expected_qa_revision"],
        raw_revision_digest=old["expected_content_digest"],
        reviewed_revision=edited["revision"],
        reviewed_digest=edited["content_digest"],
        reviewed_by=qa["id"],
        reviewed_state=reviewed["status"],
        editorial_change="Approved audience hook variation; claims and commercial fields rebuilt from pinned authority.",
        manifest=raw["source_refs"]["manifest"],
        source_chain=provenance,
        worker_journal=trace["journal"],
        execution_ms=runtime_ms,
        commercial_acceptance=None,
        external_calls=0,
        input_tokens=0,
        output_tokens=0,
        provider_fee_microusd=0,
        editing_labor_minutes=None,
    )
    if folder := os.environ.get("AMC_STORYBOARD_EVIDENCE"):
        dest = Path(folder) / case["id"]
        dest.mkdir(parents=True, exist_ok=False)
        for name, value in (("raw", raw), ("reviewed", edited["storyboard"]), ("receipt", receipt)):
            (dest / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")
    withdraw(api, owner, prep)
    assert api.post(doc + "/review", headers=qa["headers"], json=terms).status_code == 409


def test_showroom_session_does_not_imply_a_lesson():
    projection = {
        "task_intent": {"buyer_action": "choose_session", "duration_seconds": 25, "rights": video.RIGHTS, "exclusions": []},
        "brand": "Cánh Men",
        "product": "Buổi xem men gốm",
        "audience": "Chủ cửa hàng nội thất",
        "locale": "vi-VN",
        "channel": "vertical-social",
        "brand_guidelines": {"digest": "a" * 64, "guidance": "Câu ngắn, chỉ dẫn rõ."},
        "facts": [{"id": "F1", "category": "description", "wording": "Mẫu có thẻ mã men", "qualifiers": ["Dùng tại phòng trưng bày."]}],
    }
    result = video.compose(projection, {"id": "pinned", "digest": "b" * 64})
    assert result["hook"] == "Bạn muốn chọn buổi nào?"
    assert "Mẫu có thẻ mã men. Dùng tại" in " ".join(s["voice"] for s in result["shots"])
    assert all(x not in video.json_text(result) for x in ("buổi học", "phách", "âm nhạc"))
    forged = {"board_json": video.json_text(result | {"cta": "Đã xác nhận lịch"})}
    with pytest.raises(video.GatewayError, match="invalid_storyboard_reply"):
        video.validated(
            forged, {"local_adapter": video.ADAPTER, "stage": "storyboard", "context": projection, "manifest": {"id": "pinned", "digest": "b" * 64}}
        )


@PG
def test_conflicting_brand_policy_fails_with_receipt(pool):
    conf = THIRD
    base, owner, _, _, _, queued = start(pool, conf, conflicting=True)
    states = []
    work(pool, queued["id"], "director", states)
    for _ in range(3):
        pool.owner.execute("update workforce_runs set ready_at=now() where id=%s", (queued["id"],))
        work(pool, queued["id"], "storyboard", states, expect_error=True)
    result = accepted(pool.api.get(base + "/workforce/runs/" + queued["id"], headers=owner["headers"]))
    assert result["state"] == "failed" and result["last_error"] == "storyboard_needs_revision" and result["deliverable_id"] is None
    assert result["journal"][-1]["outcome"] == "storyboard_needs_revision"
    if folder := os.environ.get("AMC_STORYBOARD_EVIDENCE"):
        Path(folder).mkdir(exist_ok=True, parents=True)
        document = {
            "run_id": queued["id"],
            "state": result["state"],
            "last_error": result["last_error"],
            "deliverable_id": result["deliverable_id"],
            "journal": result["journal"],
        }
        (Path(folder) / "failed-policy-conflict.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")
