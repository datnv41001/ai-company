"""Commercial units and audience-specific outputs for the new pinned C3 releases."""

from decimal import Decimal
import re

RESEARCH = "WF-03/research-strategy-draft@3"
LANDING = "WF-13/landing-seo-draft@6"
ROLES = {RESEARCH: ("research", "strategy"), LANDING: ("content", "seo")}
COPY = ("headline", "value_proposition", "benefit", "call_to_action")
SEO = ("page_title", "meta_description", "search_intent")
MEASUREMENT = ("measurable_action", "measurement_method")

LEXICONS = {
    "vi-VN": {
        "units": {"machine": "máy", "participant": "người", "piece": "chiếc", "m²": "m²", "box": "hộp",
                  "kg": "kg", "tonne": "tấn", "subscription_month": "tháng thuê bao", "subscription_year": "năm thuê bao"},
        "tax": {"included": "đã gồm thuế", "excluded": "chưa gồm thuế", "unknown": "chưa xác định thuế"},
        "price": "Giá tham khảo", "minimum": "Đơn tối thiểu", "from": "Áp dụng từ", "to": "đến",
        "quantity": "Số lượng đối chiếu", "option": "Phương án", "buyer": "Nhóm mua", "payment_type": "Thanh toán",
        "service_level": "Mức dịch vụ", "unit": "Đơn vị", "maximum": "Tối đa", "scope": "Phạm vi",
        "retail": "bán lẻ", "wholesale": "bán sỉ", "prepaid": "trả trước", "credit": "trả sau",
        "standard": "tiêu chuẩn", "extended": "mở rộng",
    },
    "en-US": {
        "units": {"machine": "machine", "participant": "person", "piece": "piece", "m²": "m²", "box": "box",
                  "kg": "kg", "tonne": "tonne", "subscription_month": "subscription month", "subscription_year": "subscription year"},
        "tax": {"included": "tax included", "excluded": "tax excluded", "unknown": "tax treatment unconfirmed"},
        "price": "Indicative price", "minimum": "Minimum order", "from": "Applies from", "to": "to",
        "quantity": "Quoted quantity", "option": "Option", "buyer": "Buyer", "payment_type": "Payment",
        "service_level": "Service level", "unit": "Unit", "maximum": "Maximum", "scope": "Area",
        "retail": "retail", "wholesale": "wholesale", "prepaid": "prepaid", "credit": "credit",
        "standard": "standard", "extended": "extended",
    },
}


def lexicon(locale):
    if locale not in LEXICONS:
        raise ValueError("Choose a supported asset locale (vi-VN or en-US) and matching approved evidence")
    return LEXICONS[locale]


def number(value, locale, digits=None):
    amount = Decimal(str(value))
    places = max(0, -amount.normalize().as_tuple().exponent) if digits is None else digits
    result = f"{amount:,.{places}f}"
    return result.translate(str.maketrans(",.", ".,")) if locale == "vi-VN" else result


def unit_text(code, labels):
    if code not in labels["units"]:
        raise ValueError("Approve a price or applicability revision with an exact selling unit, such as machine or participant")
    return labels["units"][code]


def measure(quantity, code, locale, labels):
    unit = unit_text(code, labels)
    if locale == "en-US" and Decimal(str(quantity)) != 1:
        unit = {"box":"boxes", "machine":"machines", "piece":"pieces", "person":"people",
                "tonne":"tonnes", "subscription month":"subscription months", "subscription year":"subscription years"}.get(unit, unit)
    return f"{number(quantity, locale)} {unit}"


def fact_lines(fact, projection):
    locale = projection["locale"]
    labels = lexicon(locale)
    price = fact.get("price")
    lines = []
    if price:
        digits = 0 if price["currency"] in ("VND", "JPY") else 2
        money = number(Decimal(price["amount_minor"]).scaleb(-digits), locale, digits)
        code = price["unit"]
        denominator = measure(price["basis_quantity"], code, locale, labels)
        lines.append(f"{labels['price']}: {money} {price['currency']} / {denominator}, {labels['tax'][price['tax']]}.")
        lines.append(f"{labels['minimum']}: {measure(price['moq'], code, locale, labels)}.")
        interval = f"{labels['from']} {measure(price['tier_min'], code, locale, labels)}"
        if price.get("tier_max"):
            interval += f" {labels['to']} {measure(price['tier_max'], code, locale, labels)}"
        lines.append(interval + ".")
        if fact.get("quantity"):
            lines.append(f"{labels['quantity']}: {measure(fact['quantity'], code, locale, labels)}.")
        lines.extend(price["conditions"])
    else:
        lines.append(fact["wording"])
        if fact.get("quantity"):
            lines.append(f"{labels['quantity']}: {number(fact['quantity'], locale)}.")
    lines.extend(fact.get("qualifiers", []))
    for key, value in (fact.get("applicability") or {}).items():
        if value is not None:
            localized = unit_text(value, labels) if key == "unit" else (
                number(value, locale) if key in ("minimum", "maximum") else labels[str(value)]
            )
            lines.append(f"{labels[key]}: {localized}.")
    return list(dict.fromkeys(lines))


def _flatten(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _flatten(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten(item)
    elif isinstance(value, str):
        yield value


def normalized(text):
    return " ".join(text.casefold().split())


def prohibitions(projection):
    intent = projection.get("task_intent", {})
    guidelines = projection.get("brand_guidelines", {})
    return {normalized(v) for v in [*intent.get("exclusions", []), *guidelines.get("prohibited_claims", [])] if v.strip()}


def _public_fields(checkpoint, fields, projection):
    # The public adapter cannot see private planner prose. Also withhold echoed private
    # fields from historical/imported checkpoints when preparing the editable preview.
    intent = projection.get("task_intent", {})
    sensitive = [projection.get(k) for k in ("objective", "kpi", "gaps", "hypotheses", "brand_guidelines")]
    sensitive += [intent.get(k) for k in ("purpose", "requirements", "exclusions", "acceptance_criteria")]
    excluded = prohibitions(projection) | {normalized(v) for v in _flatten(sensitive) if len(v.strip()) >= 5}
    reserved = re.compile(r"(?:WF-\d+/|\bKPI\b|mục tiêu chiến dịch|campaign objective|internal instruction|dữ liệu cần bổ sung)", re.I)
    result = {}
    for key in fields:
        text = checkpoint.get("sections", {}).get(key, "")
        if key == "headline" and len(text) > 160:
            continue
        if text and not reserved.search(text) and not any(secret in normalized(text) for secret in excluded):
            result[key] = text
    return result


def artifacts(workflow, projection, checkpoints):
    """Internal staff projection. Only customer_preview can become an external snapshot."""
    if workflow not in ROLES:
        raise ValueError("Unknown separated-asset release")
    labels = lexicon(projection["locale"])
    facts = [{"handle": f["id"], "text": " ".join(fact_lines(f, projection))} for f in projection["facts"]]
    copy = _public_fields(checkpoints.get("content", {}), COPY, projection) if workflow == LANDING else {}
    seo = _public_fields(checkpoints.get("seo", {}), SEO, projection) if workflow == LANDING else {}
    research = checkpoints.get("research", {}).get("sections", {})
    decisions = checkpoints.get("strategy", {}).get("sections", {})
    measure = {k: decisions[k] for k in MEASUREMENT if k in decisions}
    title = copy.get("headline") or projection["product"]
    # Keep every material condition with the corresponding approved fact. Suggested
    # copy does not override or suppress currency, tiers, unit, tax or geography.
    paragraphs = [projection["product"], f"{labels['scope']}: {projection['region']}", copy.get("value_proposition"),
                  copy.get("benefit"), *(fact["text"] for fact in facts), copy.get("call_to_action")]
    preview = {"title": title, "body": "\n\n".join(dict.fromkeys(p for p in paragraphs if p))}
    return {
        "research_notes": {"fields": research, "hypotheses": projection.get("hypotheses", []), "gaps": projection.get("gaps", [])},
        "strategy_decisions": {k: v for k, v in decisions.items() if k not in MEASUREMENT},
        "buyer_copy": copy, "seo_fields": seo,
        "evidence_report": {"status": "source_handles_only", "facts": facts,
                            "suggested_handles": {role: checkpoints.get(role, {}).get("source_ids", []) for role in ROLES[workflow]}},
        "measurement_plan": {"selected_kpi": projection["kpi"], **measure} if workflow == RESEARCH else {},
        "customer_preview": preview,
    }


def render(workflow, projection, checkpoints):
    return artifacts(workflow, projection, checkpoints)["customer_preview"]
