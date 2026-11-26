"""Bounded contradictions in edited copy relative to a pinned commercial assertion."""
from decimal import Decimal
import re


MONEY = re.compile(r"(?<![\w.,])(\d+(?:[., ]\d{3})*)\s*(vnd|₫|jpy)(?!\w)", re.I)
BUYER_RECEIVES = re.compile(
    r"(?:^|[.;,!]\s*(?:(?:và|and)\s+)?|\b(?:bạn|anh chị|quý khách|khách hàng|you|buyers?|customers?)\s+)"
    r"(?:sẽ\s+|được\s+|will\s+)?(?:nhận(?: ngay| lại)?|receive|get paid)\s*$", re.I
)
REBATE = re.compile(r"\b(?:khoản hoàn tiền|hoàn lại|tiền thưởng|chiết khấu|cashback|refund|rebate|incentive)\s*(?:of\s+)?$", re.I)
DIVIDER = re.compile(r"vách ngăn.*?tháo rời|removable divider|divider.*?remov", re.I)
TRAY = re.compile(r"(?:cả |toàn bộ )?khay(?: cũng)?(?: có thể| được)? tháo rời|tháo rời (?:cả|toàn bộ) khay|removable (?:entire |whole )?tray|(?:whole |entire )?tray (?:is removable|can be removed)", re.I)
OBSERVED = re.compile(r"\b(?:đã (?:khảo sát|phỏng vấn|quan sát) (?:khách hàng|người mua)|(?:we|our team) (?:surveyed|interviewed) (?:customers|buyers)|(?:survey|interview) (?:shows|confirmed))\b", re.I)


def assertion(fact, projection):
    """Carry the exact source record, including variant, currency and all release conditions."""
    price = fact.get("price")
    return {
        "schema": "commercial-assertion/1", "handle": fact["id"], "status": "approved_fact",
        "kind": "selling_price" if price else fact["category"], "wording": fact["wording"],
        "payer": "buyer" if price else None, "payee": "seller" if price else None,
        "price": dict(price) if price else None, "applicability": fact.get("applicability") or {},
        "qualifiers": list(fact.get("qualifiers", [])),
        "scope": {k: projection.get(k) for k in ("product", "sku", "region", "channel", "market")},
    }


def contradiction(text, facts, projection):
    """Only flag a price interpretation when one matching selling-price source exists."""
    for match in MONEY.finditer(text):
        amount = Decimal(re.sub(r"[., ]", "", match[1]))
        currency = "VND" if match[2] == "₫" else match[2].upper()
        prices = [assertion(f, projection) for f in facts if f.get("price") and f["price"]["currency"] == currency
                  and Decimal(str(f["price"]["amount_minor"])) == amount]
        if len(prices) != 1:
            continue
        prefix = text[:match.start()]
        reason = "payment_kind" if REBATE.search(prefix) else "payment_direction" if BUYER_RECEIVES.search(prefix) else None
        if reason:
            return prices[0]["kind"], "contradiction", reason, [prices[0]["handle"]]
    tray_matches = list(TRAY.finditer(text))
    if tray_matches:
        features = [f for f in facts if DIVIDER.search(f["wording"])]
        if len(features) == 1 and not any(TRAY.search(f["wording"]) for f in facts):
            if all(re.search(r"(?:không(?: phải)?|not(?: an?)?|never)\s*$", text[:m.start()]) for m in tray_matches):
                return "feature", "unresolved", "scope_paraphrase", [features[0]["id"]]
            return "feature", "contradiction", "component_scope", [features[0]["id"]]
    if projection.get("hypotheses") and OBSERVED.search(text):
        if not any(OBSERVED.search(f["wording"]) for f in facts):
            return "research", "contradiction", "observation_status", []
    return None


def suggestions(findings, projection, references):
    """Anchor suggestions to the assessed sentence. Never infer a replacement source."""
    by_handle = {row["handle"]: row["text"] for row in references}
    result = []
    for row in findings:
        if not row["field"].startswith("studio.") or row["outcome"] in ("verified", "reviewed", "editorial"):
            continue
        handles = row["handles"]
        proposed = by_handle.get(handles[0]) if len(handles) == 1 else None
        if row["reason"] == "observation_status" and len(projection.get("hypotheses", [])) == 1:
            proposed = projection["hypotheses"][0]
        if proposed and proposed != row["text"]:
            original, start = row["text"], row["start"]
            for boundary in re.finditer(r",\s*(?:và|and|nhưng|but)\s+|;\s+", original, re.I):
                tail = original[boundary.end():]
                found = contradiction(tail, projection.get("facts", []), projection)
                if found and found[2:] == (row["reason"], handles):
                    start += boundary.end()
                    original = tail
                    break
            result.append({"finding": row["id"], "field": row["field"], "start": start, "end": row["end"],
                           "original": original, "proposed": proposed, "reason": row["reason"],
                           "handles": handles, "evidence": proposed})
    return result
