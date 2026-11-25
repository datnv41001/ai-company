"""Project commissioned outputs and locked fixture receipts into a pilot scorecard."""

from .knowledge_store import canonical, digest
from .revision_qa import content_digest


# Commission the denominator before production. A later revision keeps the same slot.
SLOTS = {
    "landing": ("conversion_copy", "multi_section", "Trang tiếp nhận yêu cầu báo giá", "Sales"),
    "social": ("channel_copy", "single_asset", "Bài đăng theo brief người mua", "Social"),
    "ad": ("channel_copy", "single_asset", "Mẫu quảng cáo dẫn tới RFQ", "Media"),
    "seo": ("channel_copy", "single_asset", "Tiêu đề và mô tả tìm kiếm", "SEO"),
    "creative": ("production_plan", "single_asset", "Brief thiết kế có điều kiện sử dụng hình", "Design"),
    "calendar": ("production_plan", "multi_channel", "Lịch nội dung gồm kênh và điểm duyệt", "Campaign Manager"),
}


def measure_lab_units(scenario_id, assets, reviews):
    """Pure current-state projection. Replaying the same request adds no accepted units."""
    artifacts = {}
    for asset in assets:
        key = asset["id"]
        if key not in SLOTS:
            raise ValueError("Asset outside the commissioned RFQ slots")
        if key in artifacts and artifacts[key] != asset:
            raise ValueError("Ambiguous current revision for the same commissioned slot")
        artifacts[key] = asset

    rows = []
    for key, (category, complexity, outcome, receiver) in SLOTS.items():
        asset = artifacts.get(key)
        receipt = reviews.get(key)
        approved = bool(asset and receipt and receipt == {
            "subject": key, "digest": digest(canonical(asset)), "reviewer": "fixture:marketing-qa", "synthetic": True
        } and asset["digest"] == content_digest(asset["title"], asset["body"]))
        rows.append({
            "unit_id": f"{scenario_id}/{key}", "category": category, "complexity": complexity,
            "requested_outcome": outcome, "receiver": receiver, "completion_criteria": "locked-fixture-asset-and-qa/v1",
            "status": "fixture_accepted" if approved else ("awaiting_review" if asset else "missing"),
            "acceptance_actor": receipt["reviewer"] if approved else None,
            "approval_digest": receipt["digest"] if approved else None,
            "accepted_revision": asset["revision"] if approved else None,
            "accepted_content_digest": asset["digest"] if approved else None,
            "manual_baseline_seconds": None, "assisted_elapsed_seconds": None, "clarification_seconds": None,
            "editing_seconds": None, "qa_seconds": None, "allocated_cost_vnd": None,
        })
    return {"contract": "rfq-work-units/v1", "synthetic": True, "rows": rows,
            "requested": len(rows), "fixture_accepted": sum(r["status"] == "fixture_accepted" for r in rows),
            "business_accepted": 0, "cost_per_business_accepted_vnd": None}
