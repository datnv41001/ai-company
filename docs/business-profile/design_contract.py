"""Executable examples for the C0 design, independent of AMC runtime and databases."""
import hashlib
import json
from datetime import datetime, timezone


def digest(value):
    # The fixture's v2 wire values contain JSON integers/strings/null, never floats.
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def instant(value):
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None:
        raise ValueError("A timezone is required")
    return stamp.astimezone(timezone.utc)


def in_window(row, now):
    return instant(row["valid_from"]) <= now < instant(row["valid_until"])


def preview(snapshot, created_at):
    if instant(created_at) < instant(snapshot["snapshot_as_of"]):
        raise ValueError("Preview precedes materialization")
    return {"snapshot_as_of": snapshot["snapshot_as_of"], "snapshot_digest": digest(snapshot),
            "preview_created_at": created_at}


def gate(snapshot, ticket, claim_id, effective_at, scope, use, qualifiers, states, *, authorized=True):
    """Reference outcome for one required claim. states is the current trusted authority view."""
    if not authorized or snapshot["scope"] != scope:
        return "unavailable"
    if ticket["snapshot_digest"] != digest(snapshot) or ticket["snapshot_as_of"] != snapshot["snapshot_as_of"]:
        return "stale_preview"
    now = instant(effective_at)
    if now < instant(ticket["preview_created_at"]):
        return "invalid_clock"
    claims = [c for c in snapshot["claims"] if c["id"] == claim_id and c["use"] == use]
    if len(claims) != 1:
        return "wrong_subject_or_use"
    claim = claims[0]
    if claim["state"] != "approved" or not in_window(claim, now):
        return "claim_ineligible"
    claim_state = states.get(("claim", claim["id"], claim["revision"]))
    if claim_state != "approved":
        return claim_state or "missing_authority"
    if not set(claim["qualifiers"]) <= set(qualifiers) or not claim["sources"]:
        return "claim_ineligible"
    for link in claim["sources"]:
        rows = [s for s in snapshot["sources"]
                if (s["id"], s["revision"], s["locator"]) == (link["id"], link["revision"], link["locator"])]
        if len(rows) != 1 or rows[0]["use"] != use:
            return "wrong_subject_or_use"
        src = rows[0]
        if src["content_digest"] != hashlib.sha256(src["excerpt"].encode("utf-8")).hexdigest():
            return "invalid_evidence"
        if not set(src["qualifiers"]) <= set(qualifiers):
            return "claim_ineligible"
        state = states.get(("source", src["id"], src["revision"]))
        if state != "approved":
            return state or "missing_authority"
        if not in_window(src, now):
            return "expired"
    return "eligible"


def next_setup_step(fields, task, approval):
    required = ("company", "product_or_service", "intended_audience", "goal")
    if any(not fields.get(key, "").strip() for key in required):
        return "complete_quick_setup"
    if task == "research_brief":
        return "draft_with_gaps"
    if task == "commercial_copy":
        # Approval and source eligibility are checked again by gate at actual use.
        return "check_current_authority" if approval == "human_approved" else "request_claim_review"
    raise ValueError("Unknown task")


def commercial_case(case, change):
    """Evaluate structured commercial terms from synthetic, pre-approved records."""
    request = {**case["requested"], **change}
    if any(request[k] != v for k, v in case["scope"].items()):
        return "wrong_scope"
    source = case["source"]
    if (request["source_revision"] != source["revision"] or request["source_id"] != source["id"]
            or request["locator"] != source["locator"] or request["offer"] != source["offer"] or
            any(request[k] != source[k] for k in ("product", "variant", "market", "locale", "channel"))):
        return "wrong_subject_or_use"
    offer, availability = case["offer"], case["availability"]
    if request["offer"] != offer["ref"] or any(request[k] != offer[k] for k in ("product", "variant", "market", "channel", "locale")):
        return "wrong_subject_or_use"
    now = instant(request["at"])
    if (not in_window(offer, now) or availability["market"] != request["market"]
            or availability["status"] != "available" or request["location"] != availability["location"]
            or not instant(availability["observed_at"]) <= now < instant(availability["valid_until"])):
        return "offer_or_availability_ineligible"
    if request["currency"] != offer["currency"] or request["price_minor"] != offer["price_minor"]:
        return "incorrect_price"
    if request["quantity"] < offer["quantity_min"]:
        return "quantity_below_minimum"
    if any(request[k] != case["policy"][k] for k in ("warranty", "delivery")):
        return "incorrect_policy"
    if request["qualifiers"] != case["policy"]["qualifiers"]:
        return "qualifier_missing"
    return "eligible"
