"""Compose bounded, internal campaign materials from the same verified C3 task and evidence."""

from . import c3_assets, c3_skill_library
from . import business_intake
from .c3_actions import ACTIONS
from .knowledge_store import canonical, conflict, digest
from .revision_qa import content_digest

KINDS = {c3_assets.RESEARCH: "strategy", c3_assets.LANDING: "landing"}
PACKAGES = {
    "strategy": ("Strategy", "multi_section", "Quyết định phân khúc, kênh và bước xử lý tiếp theo", 1),
    "measurement": ("Analytics", "multi_section", "KPI, mẫu số và phương pháp đối soát Sales", 1),
    "landing": ("Content", "multi_section", "Nội dung trang có CTA và điều kiện theo manifest", 2),
    "seo": ("SEO", "single_asset", "Tiêu đề SEO và mô tả khớp trang", 2),
    "social": ("Social", "single_asset", "Bài xã hội có hành động nhất quán với brief", 2),
    "ad": ("Media", "single_asset", "Mẫu quảng cáo nháp cho người mua đã chọn", 2),
    "creative_brief": ("Design", "single_asset", "Brief nêu sản phẩm, người xem và tiêu chí hình ảnh", 2),
    "calendar": ("Campaign Manager", "multi_channel", "Lịch dự kiến có người nhận, mốc QA và kênh", 3),
}


def compose_plan(store, campaign_id, selections, body, plan_id):
    snap, envelope, source = selections[0]
    intent = source["task_intent"]
    action = intent["buyer_action"]
    options = envelope["options"]
    selected = envelope["brief_pins"]["selections"]
    # WF-03 and WF-13 have distinct task IDs. Their approved commercial, market,
    # guideline and objective references must still describe the same commission.
    for _, other, projection in selections[1:]:
        if (
            other["brief_pins"]["selections"] != selected
            or any(other["options"].get(k) != options.get(k) for k in ("market", "kpi", "claims", "guidelines", "currency", "quantity"))
            or projection["task_intent"]["buyer_action"] != action
            or any(projection[k] != source[k] for k in ("audience", "product", "channel", "region", "locale", "facts", "brand_guidelines"))
        ):
            conflict("Select compatible manifests for the same objective, product, audience, buyer action and claims")
    refs = {
        KINDS[b["options"]["workflow"]]: {"id": s.id, "digest": s.digest, "brief_id": s.brief_id, "workflow": b["options"]["workflow"]}
        for s, b, _ in selections
    }
    commercial_units = {p["unit"] for f in source["facts"] for p in (f.get("price") or {}, f.get("applicability") or {}) if p.get("unit")}
    if len(commercial_units) > 1:
        conflict("Clarify which approved selling unit applies to this campaign")
    channels = list(dict.fromkeys(body.channels or [source["channel"]]))
    kinds = [
        k for k in PACKAGES if k not in ("strategy", "measurement", "landing", "seo") or ("strategy" if k in ("strategy", "measurement") else "landing") in refs
    ]
    packages = [
        {
            "id": k,
            "kind": k,
            "role": PACKAGES[k][0],
            "complexity": PACKAGES[k][1],
            "criteria": PACKAGES[k][2],
            "due_day": max(1, (body.duration_days * PACKAGES[k][3] + 2) // 3),
        }
        for k in kinds
    ]
    plan = {
        "id": plan_id,
        "scope": dict(store.scope, campaign_id=campaign_id),
        "campaign_id": campaign_id,
        "revision": body.expected_revision + 1,
        "status": "proposed",
        "objective": source["objective"],
        "objective_revision": selected["objective"],
        "audience_revision": selected["audience"],
        "product_id": selected["product"]["id"],
        "product": source["product"],
        "audience": source["audience"],
        "buyer_action": action,
        "locale": source["locale"],
        "selling_unit": next(iter(commercial_units), None),
        "target_outcome": body.target_outcome or source["objective"],
        "research_gaps": source["gaps"],
        "channels": channels,
        "budget_vnd": body.budget_vnd,
        "ai_budget_microusd_per_run": body.ai_budget_microusd_per_run,
        "duration_days": body.duration_days,
        "budget_scope": "simulated_media_only",
        "work_packages": packages,
        "brand_guidelines": source["brand_guidelines"],
        "commercial_facts": source["facts"],
        "sku": source.get("sku"),
        **({"measurement_contract": source["measurement_contract"]} if source.get("measurement_contract") else {}),
        "measurement_plan": {
            "kpi": source["kpi"],
            **({"primary": source["measurement_contract"]} if source.get("measurement_contract") else {}),
            "buyer_action": action,
            "hypothesis": f"Thử một CTA cho {source['audience']} rồi đối soát với kết quả Sales.",
            "attribution": "Theo mã yêu cầu và biên nhận, ghi riêng kết quả thiếu nguồn.",
        },
        "manifests": refs,
        "method": "deterministic-campaign-planner/1",
        "optimization_basis": body.optimization_basis,
    }
    if body.secondary_rfq:
        if action != "appointment":
            conflict("Optional quote intake is available only alongside a service appointment")
        plan["secondary_conversions"] = ["rfq"]
    if action in {"appointment", "rfq"} and plan["selling_unit"]:
        landing = next((p for _, b, p in selections if KINDS[b["options"]["workflow"]] == "landing"), source)
        lists = {tuple(business_intake.submitted_fields(p["task_intent"], strict=True)) for _, _, p in selections}
        lists.discard(())
        if len(lists) > 1:
            conflict("Reconcile the required buyer fields across the approved briefs")
        intake_source = landing if business_intake.submitted_fields(landing["task_intent"]) else next(
            (p for _, _, p in selections if business_intake.submitted_fields(p["task_intent"])), landing)
        source_kind = next(KINDS[b["options"]["workflow"]] for _, b, p in selections if p is intake_source)
        plan["intake_contract"] = business_intake.issue(plan, intake_source, body.intake_fields, plan["manifests"][source_kind])
    elif body.intake_fields:
        conflict("Select a transactional journey with an approved selling unit")
    plan["digest"] = digest(canonical(plan))
    return plan


def compose_assets(plan):
    """Called only after each commissioned package receives its durable request."""
    action = plan["buyer_action"]
    refs, packages, channels = plan["manifests"], plan["work_packages"], plan["channels"]
    offer, buyer = plan["product"], plan["audience"]
    vi = plan["locale"].lower().startswith("vi")
    cta = ACTIONS[action]["vi" if vi else "en"]
    channels_text = ", ".join(channels)
    copy = {
        "social": ("Nội dung mạng xã hội", f"{buyer} đang cân nhắc {offer}? {cta} để trao đổi nhu cầu về sản phẩm và điều kiện áp dụng."),
        "ad": ("Nội dung quảng cáo", f"{offer} dành cho {buyer}. {cta}."),
        "creative_brief": (
            "Brief sản xuất hình ảnh",
            f"Thiết kế cho {buyer} trên {channels_text}. Đặt {offer} ở vị trí chính và dùng CTA “{cta}”. "
            f"Giọng điệu: {plan['brand_guidelines']['guidance']} Kiểm tra quyền sử dụng hình ảnh trước bàn giao.",
        ),
        "calendar": (
            "Lịch nội dung dự kiến",
            "\n".join(f"Ngày {p['due_day']} · {p['role']} · {p['criteria']}" for p in packages)
            + f"\nKênh đề xuất: {channels_text}. Điểm duyệt: kiểm tra chứng cứ và phê duyệt từng tài sản trước thực thi.",
        ),
    }
    if not vi:
        copy = {
            "social": ("Social post", f"Is {offer} on your shortlist? {cta} to discuss the requirements and terms for {buyer}."),
            "ad": ("Ad copy", f"{offer} for {buyer}. {cta}."),
            "creative_brief": (
                "Creative brief",
                f"Show {offer} for {buyer} on {channels_text}. CTA: {cta}. "
                f"Use the approved brand guidance: {plan['brand_guidelines']['guidance']} Check image rights before handoff.",
            ),
            "calendar": (
                "Proposed content calendar",
                "\n".join(f"Day {p['due_day']} · {p['role']} · {p['kind']}" for p in packages)
                + f"\nChannels: {channels_text}. Verify evidence and approve assets before execution.",
            ),
        }
    primary = refs.get("landing", refs.get("strategy"))
    method_versions = {stage: c3_skill_library.skill_pins(stage) for stage in c3_assets.ROLES[primary["workflow"]]}
    return [
        {
            "id": kind,
            "kind": kind,
            "title": title,
            "body": text,
            "revision": 1,
            "digest": content_digest(title, text),
            "status": "draft",
            "provenance": "deterministic-composition/1",
            "plan_id": plan["id"],
            "plan_revision": plan["revision"],
            "manifest": primary,
            "buyer_action": action,
            "product_id": plan["product_id"],
            "guideline_digest": plan["brand_guidelines"]["digest"],
            "referenced_workflow_skills": method_versions,
            **({"measurement_contract": plan["measurement_contract"]} if plan.get("measurement_contract") else {}),
            "requires_channel_evidence": True,
        }
        for kind, (title, text) in copy.items()
    ]
