"""Read-only departmental drafts pinned to one active plan and its approved facts."""
from datetime import datetime, timedelta, timezone
import re
import unicodedata

from . import c3_order_units, c3_studio


ADS_SOURCE = "https://support.google.com/google-ads/answer/7684791"
SEARCH_SOURCE = "https://developers.google.com/search/docs/fundamentals/creating-helpful-content"
HANDOFF_SOURCE = "https://www.wecommit.com.vn/bai-viet/tam-ban-do-tong-the-cho-doi-ai-agent"

BUYER_FIELDS = {
    "box_count": ("số hộp", "number of boxes"), "quantity": ("số lượng", "quantity"),
    "destination": ("địa bàn", "delivery area"), "need_date": ("thời điểm cần hàng", "required delivery date"),
    "site": ("địa điểm", "location"), "receiving_shift": ("ca nhận hàng cần quan sát", "receiving shift to observe"),
    "preferred_time": ("khung giờ mong muốn", "preferred time"),
}


def submitted_fields(intent):
    """Read complete field lists in the pinned brief. Never copy free-form staff instructions into public copy."""
    lookup = {label: key for key, names in BUYER_FIELDS.items() for label in names}
    result = []
    for item in intent.get("requirements", []):
        words = unicodedata.normalize("NFC", item).casefold().strip().rstrip(".")
        match = re.search(r"(?:^|, | và | and )(?:ghi|cung cấp|gửi kèm|include|provide) (.+)$", words)
        if not match:
            continue
        values = re.split(r",\s*| và | and ", match[1])
        if all(value in lookup for value in values):
            result += [lookup[value] for value in values]
    return list(dict.fromkeys(result))


def search_ad_checks(headlines, descriptions):
    def length(s):
        return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
                   for c in unicodedata.normalize("NFC", s))

    problems = []
    for items, name, minimum, maximum, limit in (
        (headlines, "headline", 3, 15, 30), (descriptions, "description", 2, 4, 90)
    ):
        if len(set(items)) != len(items) or not minimum <= len(items) <= maximum:
            problems.append({"field": name, "reason": "count_or_duplicates"})
        problems.extend({"field": name, "variant": i + 1, "reason": "length", "length": length(value), "limit": limit}
                        for i, value in enumerate(items) if not value.strip() or length(value) > limit)
    return problems


def compose(plan, projection):
    vi = projection["locale"] == "vi-VN"
    def tr(vietnamese, english):
        return vietnamese if vi else english

    product, buyer = projection["product"], projection["audience"]
    cta = c3_studio.buyer_action(projection)
    terms = "\n".join(" ".join(c3_order_units.fact_lines(f, projection)) for f in projection["facts"])
    action = plan["buyer_action"]
    if action == "rfq":
        ask = tr("Cần gì để yêu cầu báo giá?", "What do you need for a quote?")
        quantity = tr("số hộp", "number of boxes") if plan.get("selling_unit") == "box" else tr("số lượng", "quantity")
        lead = tr(f"Ghi {quantity}, địa bàn và thời điểm cần hàng để bên bán chuẩn bị báo giá.",
                  f"Include the {quantity}, destination and required date so Sales can prepare a quote.")
        short = tr("Chuẩn bị yêu cầu báo giá", "Prepare your quote request")
    elif action in ("appointment", "choose_session", "request_assessment"):
        ask = tr("Cần chuẩn bị gì trước khi hẹn?", "What should you prepare before requesting a visit?")
        lead = tr("Ghi địa điểm và thời gian thuận tiện. Nhân sự phụ trách sẽ đối chiếu yêu cầu trước khi xác nhận lịch.",
                  "Include the location and preferred time. Staff review the request before confirming the booking.")
        short = tr("Gửi yêu cầu hẹn", "Request an appointment")
    else:
        ask = tr("Điều kiện nào áp dụng?", "Which terms apply?")
        lead = tr("Xem điều kiện cho lựa chọn của bạn trước khi gửi yêu cầu.", "Check the conditions for your selection before submitting.")
        short = tr("Xem điều kiện", "Check the terms")
    fields = submitted_fields(projection["task_intent"])
    if fields:
        labels = [BUYER_FIELDS[k][0 if vi else 1] for k in fields]
        inputs = (", ".join(labels[:-1]) + tr(" và ", " and ") if len(labels) > 1 else "") + labels[-1]
        lead = tr(f"Gửi kèm {inputs}.", f"Include the {inputs}.")
    title = tr(f"{product} dành cho {buyer}", f"{product} for {buyer}")
    headlines = [product, short, tr("Xem phạm vi áp dụng", "Check applicable terms")]
    descriptions = [lead, cta]
    pillars = [tr("Chuẩn bị nhu cầu", "Prepare your requirements"), tr("Điều kiện áp dụng", "Understand the terms")]
    group_a = plan["budget_vnd"] // 2
    approved_at = datetime.fromisoformat(plan["approval"]["at"])
    approval_date = approved_at.replace(tzinfo=approved_at.tzinfo or timezone.utc).astimezone(timezone.utc).date()
    return {
        "version": "department-content-pack/1", "status": "internal_draft", "plan_digest": plan["digest"],
        "plan_id": plan["id"], "plan_revision": plan["revision"], "manifests": plan["manifests"],
        "objective": plan["objective"], "audience": buyer, "pillars": pillars, "buyer_fields": fields,
        "social": [
            {"platform": "LinkedIn", "stage": "consideration", "pillar": pillars[0],
             "copy": f"{title}\n\n{ask} {lead}\n\n{terms}\n\n{cta}"},
            {"platform": "Facebook", "stage": "decision", "pillar": pillars[1],
             "copy": f"{ask}\n\n{product}\n{terms}\n\n{lead} {cta}"},
        ],
        "website": {"headline": title, "body": lead, "commercial_terms": terms, "cta": cta},
        "organic_search": {"title": product + " · " + short, "question": ask, "answer": lead + "\n" + terms,
                           "next_step": cta, "rubric": SEARCH_SOURCE},
        "calendar_timezone": "UTC",
        "calendar": [{"date": (approval_date + timedelta(days=p["due_day"] - 1)).isoformat(), "owner": p["role"],
                      "kind": p["kind"], "acceptance": p["criteria"]} for p in plan["work_packages"]],
        "creative": {"subject": product, "audience": buyer, "caption": short, "terms": terms,
                     "cta": cta, "rights_gate": "licensed_source_and_independent_revision_approval"},
        "advertising": {
            "format": "google_responsive_search_ad_draft", "source": ADS_SOURCE,
            "headlines": headlines, "descriptions": descriptions, "format_issues": search_ad_checks(headlines, descriptions),
            "ad_groups": [{"hypothesis": product, "intent": "product", "budget_vnd": group_a},
                          {"hypothesis": short, "intent": action, "budget_vnd": plan["budget_vnd"] - group_a}],
            "experiment": tr("So sánh lời nhấn vào nhu cầu với lời nhấn vào điều kiện. Giữ nguyên CTA, trang đích và nhóm người mua.",
                             "Compare needs-led and terms-led copy with the same CTA, audience and landing page."),
            "measurement": projection.get("measurement_contract") or {
                "status": "requires_measurement_contract", "approved_label": projection["kpi"]},
            "destination": {"kind": "sandbox_landing", "manifest": plan["manifests"].get("landing"),
                            "requirement": "select_approved_package_for_current_revision"},
            "external_spend_vnd": 0, "external_spend_scope": "this_offline_draft_only", "publication_receipt": None,
        },
        "research": {"sources": [ADS_SOURCE, SEARCH_SOURCE, HANDOFF_SOURCE], "approved_facts": [f["id"] for f in projection["facts"]],
                     "hypotheses": projection.get("hypotheses", []), "open_questions": projection.get("gaps", []),
                     "workflow_references": ([{"source": "https://calendly.com/scheduling/routing",
                         "scope": "public_vendor_description", "observation": "Form answers can guide appointment routing.",
                         "question": "Who receives this request and what evidence confirms the appointment?"},
                         {"source": "https://www.hubspot.com/products/sales/schedule-meeting",
                          "scope": "public_vendor_description", "observation": "A buyer can use a scheduling page to book a meeting.",
                          "question": "Does this service support self-booking or does staff need to confirm?"}]
                         if action in ("appointment", "choose_session", "request_assessment") else []),
                     "competitor_observations": [], "competitor_status": "awaiting_scoped_public_evidence"},
    }
