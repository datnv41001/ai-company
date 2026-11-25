"""Prepare the 20 historical unit-recovery cases through the public local API before queuing inference."""

from copy import deepcopy
from time import monotonic
from uuid import uuid4

from c3_fixtures import prepared
from knowledge_fixtures import accepted, revision

# A synthetic brief author supplies these selections explicitly. Each key is paired
# with the exact historical instruction so changes in the corpus require re-review.
TASK_ACTIONS = {
    "service-01": ("đặt ca kiểm tra quạt", "appointment", None),
    "service-02": ("gửi ảnh rèm để khảo sát", "request_assessment", "photo"),
    "service-03": ("đặt lịch khảo sát đàn", "appointment", None),
    "service-04": ("xác nhận ca vệ sinh bếp", "appointment", None),
    "service-05": ("gửi ảnh bản lề hỏng", "request_assessment", "photo"),
    "service-06": ("chọn buổi xem cây", "choose_session", "session_choice"),
    "service-07": ("gửi ảnh tường để thẩm định", "request_assessment", "photo"),
    "service-08": ("đặt khung giờ kiểm tra phanh", "appointment", None),
    "service-09": ("gửi ảnh đầu kéo để báo phí", "rfq", "photo"),
    "service-10": ("đặt buổi đo tại nhà", "appointment", None),
    "inhouse-01": ("đăng ký buổi khâu gáy", "registration", None),
    "inhouse-02": ("chọn buổi vẽ ngoài trời", "choose_session", "session_choice"),
    "inhouse-03": ("giữ chỗ buổi làm bình hoa", "registration", None),
    "inhouse-04": ("xác nhận chỗ thực hành ánh sáng", "registration", None),
    "inhouse-05": ("gửi lựa chọn mẫu thêu", "select_sample", "sample_choice"),
    "inhouse-06": ("chọn buổi thực hành nhào bột", "choose_session", "session_choice"),
    "inhouse-07": ("ghi danh buổi thu giọng nói", "registration", None),
    "inhouse-08": ("đăng ký đọc thử kịch bản", "registration", None),
    "inhouse-09": ("gửi mẫu cho buổi thử in", "submit_reference", "sample"),
    "inhouse-10": ("ghi danh buổi chọn mùi", "registration", None),
}


def start_recovery(api, case, owner, base, client, brand, campaign, *, project=None):
    strategy = case["workflow"] == "WF-03"
    prompt, action, buyer_input = TASK_ACTIONS[case["id"]]
    assert prompt == case["cta"]
    # The operator selects a high-level action for the fixture while retaining the exact
    # original request as a staff requirement. In live use the task author makes this choice.
    intent = {
        **{k: case[k] for k in ("product", "audience", "locale", "channel", "region")},
        "purpose": case["objective"],
        "deliverable_type": "marketing_strategy" if strategy else "landing_page",
        "requirements": [case["cta"]],
        "exclusions": [case["unsupported_example"]],
        "acceptance_criteria": ["Chỉ sử dụng căn cứ đã duyệt."],
        "buyer_action": action,
        "editorial_style": "plain",
    }
    if buyer_input:
        intent["buyer_input"] = buyer_input
    task = accepted(
        api.post(base + "/workforce/internal-tasks", headers=owner["headers"], json={"campaign_id": campaign, "key": str(uuid4()), "intent": intent})
    )
    inputs = deepcopy(case)
    for fact in inputs["facts"]:
        fact["qualifiers"] = [fact["qualifiers"]]
    workflow = "WF-03/research-strategy-draft@3" if strategy else "WF-13/landing-seo-draft@6"
    s = prepared(api, owner, base, client, brand, campaign, task["id"], workflow, case=inputs, project=project)
    guide = revision(api, owner, s["path"], "recovery-guide", "guidelines", {"guidance": "Câu ngắn."})
    s["params"]["guidelines"] = guide["id"]
    return s, intent


def attestation(case, issue):
    fact = next(f for f in case["facts"] if f.get("category") == "price")
    labels = {"/lượt.": "visit", "/người.": "participant"}
    (unit,) = [code for suffix, code in labels.items() if fact["wording"].endswith(suffix)]
    return {
        "key": str(uuid4()),
        "unit": unit,
        "document": "Bảng giá tổng hợp " + case["id"],
        "locator": fact["id"],
        "excerpt": fact["wording"],
        "confirm_same_terms": True,
        **{k: issue[k] for k in ("claim", "claim_digest", "offer_digest")},
    }


def prepare_recovered(api, case, owner, base, client, brand, campaign, *, project=None):
    """Use an already-routed internal scope and return a real manifest; this helper never calls a model."""
    started = monotonic()
    s, intent = start_recovery(api, case, owner, base, client, brand, campaign, project=project)
    path = s["marketing"]
    selected = s["params"]
    reviewer = s["commercial_reviewer"]

    def send(endpoint, body, actor=owner):
        return accepted(api.post(path + "/" + endpoint, headers=actor["headers"], json=body))

    blocked = monotonic()
    check = send("readiness", selected)
    assert check["status"] == "needs_input"
    (issue,) = check["clarifications"]
    correction = attestation(case, issue)
    proposed = send("clarifications/propose", {"selection": selected, "correction": correction})
    submitted = monotonic()

    def prior_revision(rid):
        return accepted(api.get(s["path"] + "/revisions/" + rid, headers=owner["headers"]))

    original_binding = prior_revision(proposed["original_claim"])["data"]["binding"]
    original_source = prior_revision(original_binding)["data"]["source"]
    (issue,) = accepted(api.get(path + "/clarifications", headers=reviewer["headers"]))["items"]
    pending = issue["proposal"]
    assert pending["id"] and pending["claim"] == proposed["claim"] and not pending["own"]
    approved = send(
        "clarifications/approve",
        {
            "key": str(uuid4()),
            "proposal": pending["id"],
            "qualification_revision": pending["qualifications"][0],
            "reason": "Kiểm tra đơn vị ghi trên bảng giá tổng hợp.",
        },
        reviewer,
    )
    approved_at = monotonic()
    resume = {**selected, "key": str(uuid4()), "claims": [approved["claim"] if rid == approved["original_claim"] else rid for rid in selected["claims"]]}
    assert send("readiness", resume)["status"] == "ready"
    snap = send("manifests", resume)
    finished = monotonic()
    return {
        "task_id": selected["target"]["brief_id"],
        "workflow": selected["workflow"],
        "manifest": snap,
        "selection": resume,
        "correction": {
            "initial_status": "needs_input",
            "unit_before": "service",
            "unit_confirmed": correction["unit"],
            "original_claim": issue["claim"],
            "original_offer": proposed["original_offer"],
            "original_offer_digest": issue["offer_digest"],
            "original_source": original_source,
            "original_binding": original_binding,
            "proposal_receipt": pending["id"],
            "offer": proposed["offer"],
            "source": proposed["source"],
            "binding": proposed["binding"],
            "claim": approved["claim"],
            "source_excerpt": correction["excerpt"],
            "guidelines": resume["guidelines"],
            "buyer_action": intent["buyer_action"],
            "buyer_input": intent.get("buyer_input"),
            "requested_cta": case["cta"],
            "timing_seconds": {
                "seed_and_task": round(blocked - started, 4),
                "clarify_and_propose": round(submitted - blocked, 4),
                "approve": round(approved_at - submitted, 4),
                "resume": round(finished - approved_at, 4),
            },
            "practitioner_minutes": None,
        },
    }
