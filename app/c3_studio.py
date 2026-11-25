"""Compose staff assets from frozen source facts. Model text is a suggestion until each asset passes QA."""

import re

from . import c3_assets, c3_order_units
from .c3_actions import ACTIONS, BUYER_INPUTS

VERSION = "amc.marketing-studio/1"
FIELDS = {
    c3_assets.RESEARCH: {
        "research": ("buyer_problem", "research_question", "evidence", "hypothesis"),
        "strategy": ("positioning", "channel_choice", "rationale", "execution"),
        "measurement": ("test_hypothesis", "measurable_action", "measurement_method"),
    },
    c3_assets.LANDING: {
        "copy": ("headline", "value_proposition", "benefit", "commercial_terms", "call_to_action"),
        "seo": ("page_title", "meta_description", "search_intent"),
    },
}


def buyer_action(projection):
    intent = projection.get("task_intent", {})
    chosen = ACTIONS.get(intent.get("buyer_action"))
    if not chosen:
        return ""
    lang = "vi" if projection["locale"] == "vi-VN" else "en"
    label = chosen[lang]
    material = BUYER_INPUTS.get(intent.get("buyer_input"))
    if material and material[lang].casefold() not in label.casefold():
        instruction = "Gửi kèm " if lang == "vi" else "Include "
        label = f"{label}. {instruction}{material[lang].lower()}."
    return label


def compose(workflow, projection, checkpoints=None):
    """Without checkpoints, return the deterministic comparison arm using the same approved inputs."""
    sections = c3_order_units.artifacts(workflow, projection, checkpoints or {})
    vi = projection["locale"] == "vi-VN"

    def language(local, english):
        return local if vi else english

    product = projection["product"]
    audience = projection.get("audience") or ""
    channel = projection.get("channel") or ""
    facts = sections["evidence_report"]["facts"]
    commercial = "\n".join(f["text"] for f in facts)
    action = buyer_action(projection)
    intent = projection.get("task_intent", {})
    method = language(
        "So sánh tỷ lệ hành động hoàn tất trên lượt xem đủ điều kiện. Ghi nhận mỗi yêu cầu đúng một lần theo mã.",
        "Compare completed actions per eligible view. Deduplicate requests by event identifier.",
    )
    choice = intent.get("buyer_action")
    if choice in ("rfq", "request_assessment", "appointment", "choose_session"):
        method = language(
            "Theo dõi số yêu cầu hoàn tất trên lượt vào trang. Đối chiếu mã yêu cầu khi bộ phận phụ trách tiếp nhận.",
            "Track completed requests per page visit. Reconcile the request identifier when the responsible team receives it.",
        )
    elif choice in ("sample_request", "colour_card_request", "select_sample", "submit_reference"):
        method = language(
            "So sánh tỷ lệ gửi lựa chọn mẫu. Đối chiếu từng lựa chọn với yêu cầu gốc trước khi tổng hợp.",
            "Compare sample selection completion rates. Match each selection to its original request before aggregating.",
        )
    elif choice == "purchase":
        method = language(
            "Đối chiếu đơn đã xác nhận theo mã đơn và phiên đủ điều kiện. Ghi nhận riêng đơn bị hủy.",
            "Match confirmed order identifiers to eligible sessions and record cancellations separately.",
        )
    elif choice in ("registration", "catalogue_download"):
        method = language(
            "Đo lượt hoàn tất sau khi gửi biểu mẫu hoặc tải tài liệu, loại sự kiện trùng theo mã.",
            "Track completion after form submission or document download. Deduplicate by event identifier.",
        )
    nonprice = [f for f in projection["facts"] if not f.get("price")]
    benefit = " ".join(c3_order_units.fact_lines(nonprice[0], projection)) if nonprice else ""
    if workflow == c3_assets.LANDING:
        copy, seo = sections["buyer_copy"], sections["seo_fields"]
        lead = language(
            f"Đối chiếu quy cách và điều kiện áp dụng của {product} trước khi lựa chọn.",
            f"Review the specifications and applicable terms for {product} before choosing.",
        )
        if intent.get("editorial_style") == "concise":
            lead = language(f"{product}: xem quy cách và điều kiện áp dụng.", f"{product}: review specifications and terms.")
        elif intent.get("editorial_style") == "formal":
            lead = language(f"Vui lòng đối chiếu quy cách và điều kiện áp dụng của {product}.", f"Please review the specifications and terms for {product}.")
        elif intent.get("editorial_style") == "friendly":
            lead = language(f"Bạn đang cân nhắc {product}? Hãy xem các điều kiện áp dụng.", f"Considering {product}? Explore the applicable terms.")
        return {
            "copy": {
                "headline": copy.get("headline") or product,
                "value_proposition": copy.get("value_proposition") or lead,
                "benefit": copy.get("benefit") or benefit,
                "commercial_terms": commercial,
                # A role reply cannot replace the task author's chosen conversion action.
                "call_to_action": action,
            },
            "seo": {
                "page_title": seo.get("page_title") or f"{product} | {projection['region']}",
                "meta_description": seo.get("meta_description")
                or language(
                    f"Xem thông tin về {product} tại {projection['region']}. {action}".strip(), f"Explore {product} in {projection['region']}. {action}".strip()
                ),
                "search_intent": seo.get("search_intent")
                or language(
                    f"Tìm hiểu điều kiện lựa chọn {product} tại {projection['region']}.", f"Find conditions for choosing {product} in {projection['region']}."
                ),
            },
        }
    research = sections["research_notes"]["fields"]
    strategy = sections["strategy_decisions"]
    measurement = sections["measurement_plan"]
    return {
        "research": {
            "buyer_problem": research.get("buyer_problem")
            or language(f"Cần tìm hiểu điều gì khiến {audience} còn do dự khi chọn {product}?", f"What prevents {audience} from choosing {product}?"),
            "research_question": research.get("research_question")
            or language(
                f"Trong lần mua gần nhất, {audience} đã so sánh {product} với phương án nào?",
                f"Which alternatives did {audience} compare with {product} during their latest purchase?",
            ),
            "evidence": commercial,
            "hypothesis": language(
                f"Giả thuyết cần thử: làm rõ điều kiện của {product} giúp {audience} chọn bước tiếp theo.",
                f"Hypothesis to test: clearer terms for {product} help {audience} select a next step.",
            ),
        },
        "strategy": {
            "positioning": strategy.get("positioning")
            or language(f"Đề xuất định vị {product} qua quy cách có thể đối chiếu.", f"Position {product} around verifiable specifications."),
            "channel_choice": strategy.get("channel_choice") or channel,
            "rationale": strategy.get("rationale")
            or language(f"Thử trên {channel} vì đây là kênh nằm trong phạm vi được duyệt.", f"Test on {channel}, the channel within the approved market."),
            "execution": language(
                f"Soạn hai phiên bản giới thiệu {product} trên {channel}, giữ nguyên điều kiện và đo cùng một hành động.",
                f"Prepare two presentations of {product} on {channel}, keep terms fixed and measure the same action.",
            ),
        },
        "measurement": {
            "test_hypothesis": strategy.get("test_hypothesis")
            or language(
                "So sánh bản trình bày dữ kiện trước và sau lời mời hành động trên cùng nhóm khách.",
                "Compare placing facts before versus after the call to action in the same audience.",
            ),
            "measurable_action": action or measurement.get("measurable_action", ""),
            "measurement_method": measurement.get("measurement_method") or method,
        },
    }


def quality_issues(workflow, groups, projection):
    """Conservative structural signals; professional relevance still requires an independent review."""
    result, seen = [], {}
    norm = c3_assets.normalized
    product_terms = set(re.findall(r"[^\W_]{3,}", norm(projection["product"] + " " + (projection.get("sku") or ""))))
    product_terms -= {"the", "for", "and", "sản", "phẩm", "của", "cho", "với"}
    for group, fields in FIELDS[workflow].items():
        for field in fields:
            text = norm(groups[group][field])
            reason = ""
            if not text:
                reason = "missing"
            elif field not in ("evidence", "commercial_terms") and text in seen and not ({field, seen[text]} <= {"headline", "page_title"}):
                reason = "repetition"
            elif re.search(r"\b(lorem ipsum|as an ai|tôi là một ai|điền vào đây|insert text here)\b", text):
                reason = "placeholder"
            elif field in ("headline", "page_title", "search_intent") and product_terms and product_terms.isdisjoint(re.findall(r"[^\W_]+", text)):
                reason = "relevance"
            elif field == "call_to_action":
                expected = buyer_action(projection)
                if not expected or text != norm(expected):
                    reason = "buyer_action"
            if field in ("commercial_terms", "evidence"):
                declarations = [" ".join(c3_order_units.fact_lines(f, projection)) for f in projection["facts"]]
                if not declarations or any(line not in groups[group][field].splitlines() for line in declarations):
                    reason = "missing_declaration"
            if reason:
                result.append({"group": group, "field": field, "reason": reason})
            seen[text] = field
    return result


def preview(workflow, groups, initial):
    """Portal snapshots contain only buyer copy. Staff-only research/strategy never enter a public preview."""
    if workflow == c3_assets.RESEARCH:
        return initial
    copy = groups["copy"]
    return {"title": copy["headline"], "body": "\n\n".join(copy[k] for k in FIELDS[workflow]["copy"] if k != "headline" and copy[k])}
