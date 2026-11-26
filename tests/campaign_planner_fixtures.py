"""Create two unrelated campaign inputs via ordinary business, evidence and task APIs."""

from copy import deepcopy
from uuid import uuid4

from app import c3_assets
from agency_fixtures import create
from c3_fixtures import capture, prepared
from c3_task_fixtures import INTENT
from knowledge_fixtures import accepted, revision
from test_workforce import DATA

CASES = [
    {
        "id": "acoustic-panel",
        "company": "Vật liệu Hải Đăng",
        "brand": "Gỗ tiêu âm Mộc",
        "product": "Tấm gỗ tiêu âm Mộc",
        "sku": "MOC-12",
        "audience": "Nhà thầu phòng thu",
        "objective": "Tăng yêu cầu báo giá tấm gỗ cho dự án phòng thu",
        "kpi": "Yêu cầu đủ số lượng và địa bàn để báo giá",
        "buyer_action": "rfq",
        "unit": "box",
        "amount": 430000,
        "wording": "Lớp mặt phủ veneer.",
        "qualifier": "Dùng trong nhà.",
        "cta": "Gửi yêu cầu báo giá theo hộp.",
    },
    {
        "id": "pump-service",
        "company": "Kỹ thuật Sông Lam",
        "brand": "Xưởng bơm Lam",
        "product": "Dịch vụ kiểm tra bơm Lam",
        "sku": "BOM-KT",
        "audience": "Quản đốc nhà máy",
        "objective": "Tăng lịch khảo sát bảo trì tại xưởng",
        "kpi": "Lịch khảo sát được xác nhận",
        "buyer_action": "appointment",
        "unit": "machine",
        "amount": 270000,
        "wording": "Phiếu kiểm tra ghi tình trạng máy.",
        "qualifier": "Áp dụng cho máy tại xưởng.",
        "cta": "Đặt lịch khảo sát theo máy.",
    },
]


def facts(case):
    return [
        {"wording": case["wording"], "qualifiers": [case["qualifier"]]},
        {
            "category": "price",
            "wording": "Giá từ bảng đã duyệt",
            "qualifiers": ["Xác nhận số lượng trước khi đặt."],
            "quantity": "1",
            "price": {
                "amount_minor": case["amount"],
                "currency": "VND",
                "unit": case["unit"],
                "basis_quantity": "1",
                "moq": "1",
                "tier_min": "1",
                "tax": "included",
                "conditions": ["Xác nhận số lượng trước khi đặt."],
            },
        },
    ]


def prepare_inputs(api, owner, customer, client, brand, campaign, case, workflows=(c3_assets.RESEARCH, c3_assets.LANDING)):
    base = "/api/tenants/" + owner["tenant"]
    prep, snaps = None, []
    for workflow in workflows:
        label = "marketing_strategy" if workflow == c3_assets.RESEARCH else "landing_page"
        bid = create(api, base + "/workforce/briefs", owner, {"campaign_id": campaign, "recipient_id": customer["id"], "title": case["objective"]})["id"]
        intent = INTENT | {k: case[k] for k in ("product", "audience", "buyer_action")}
        intent.update(
            deliverable_type=label,
            purpose=case["objective"],
            editorial_style="plain",
            requirements=[case["cta"]],
            acceptance_criteria=["Bàn giao thông tin đủ để người nhận thực hiện bước tiếp theo."],
        )
        if "campaign_limits" in case:
            intent["campaign_limits"] = case["campaign_limits"]
        accepted(api.put(base + "/workforce/briefs/" + bid + "/submission", headers=customer["headers"], json=DATA | {"task_intent": intent}))
        if prep is None:
            prep = prepared(api, owner, base, client, brand, campaign, bid, workflow, case=case | {"facts": facts(case)})
            guide = revision(
                api, owner, prep["path"], "campaign-voice", "guidelines", {"guidance": "Dùng câu ngắn và nêu rõ điều kiện áp dụng.", "tone": "Cụ thể"}
            )
            prep["params"]["guidelines"] = guide["id"]
        current = deepcopy(prep)
        current["params"].update(workflow=workflow, target={"campaign_id": campaign, "brief_id": bid}, key=uuid4().hex, ttl_seconds=900)
        snaps.append(capture(api, owner, current))
    return snaps, prep
