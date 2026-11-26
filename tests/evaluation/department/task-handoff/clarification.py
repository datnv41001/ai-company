"""Offline single-field Sales/Service handoff trace. All references and inputs are synthetic."""
from datetime import date
import re


# Deliberately narrow coverage: an entire message must match a commissioned statement.
# An unseen phrase needs review even if CRM already has a value.
STATEMENTS = {
    "en": (
        ("set", r"Change the FIELD to (?P<value>[A-Z]{2}-[0-9]{2})[.!]?"),
        ("withdraw", r"The FIELD is no longer valid[.!]?"),
        ("confirm", r"The FIELD in the file is correct[.!]?"),
    ),
    "vi": (
        ("set", r"Đổi FIELD sang (?P<value>[A-Z]{2}-[0-9]{2})[.!]?"),
        ("withdraw", r"FIELD cũ đã hết hiệu lực[.!]?"),
        ("confirm", r"FIELD trong hồ sơ vẫn đúng[.!]?"),
    ),
}


FIELD_LABELS = {"site": {"en": "site", "vi": "địa điểm"}, "dock": {"en": "dock", "vi": "điểm giao"}}


def parse_statement(message, locale, field):
    for action, pattern in STATEMENTS[locale]:
        match = re.fullmatch(pattern.replace("FIELD", FIELD_LABELS[field][locale]), message.strip(), flags=re.IGNORECASE)
        if match:
            value = match.groupdict().get("value")
            return {"action": action, "value": value.upper() if value else None, "quote": match.group()}
    return {"action": "unresolved", "value": None, "quote": message}


def project(case):
    """Separate buyer evidence from scoped CRM and the server-selected policy revision."""
    policy = case["policy"]
    crm = case["crm"]
    buyer = case["buyer"]
    if any(record["scope"] != case["scope"] for record in (crm, policy, buyer)):
        raise ValueError("Scope mismatch")
    if not all(record["ref"] for record in (crm, policy, buyer)):
        raise ValueError("Source reference required")
    if policy["revision"] != case["current_policy_revision"] or not policy["approved"]:
        raise ValueError("Require the current approved fixture policy")
    as_of = date.fromisoformat(case["as_of"])
    if not date.fromisoformat(policy["since"]) <= as_of <= date.fromisoformat(policy["until"]):
        raise ValueError("Policy out of date")
    statement = parse_statement(buyer["text"], case["locale"], policy["field"])
    return {
        "statement": statement,
        "sources": {"crm": crm["ref"], "buyer": buyer["ref"], "policy": policy["ref"], "policy_revision": policy["revision"]},
        "crm_valid": crm["value"] is not None and as_of <= date.fromisoformat(crm["valid_until"]),
        "buyer_current": date.fromisoformat(crm["recorded_at"]) <= date.fromisoformat(buyer["recorded_at"]) <= as_of,
    }


def resolve(case, projection):
    evidence = projection["statement"]
    old = case["crm"]["value"]
    action = evidence["action"]
    if not projection["buyer_current"] or action == "unresolved":
        return {"status": "unresolved_message", "current": None, "old": old, "source": case["buyer"]["ref"]}
    if action == "set":
        return {"status": "corrected" if evidence["value"] != old else "confirmed", "current": evidence["value"],
                "old": old, "source": case["buyer"]["ref"]}
    if action == "withdraw" or not projection["crm_valid"]:
        return {"status": "withdrawn" if action == "withdraw" else "absent_or_expired",
                "current": None, "old": old, "source": case["buyer"]["ref"] if action == "withdraw" else case["crm"]["ref"]}
    return {"status": "confirmed", "current": old, "old": old, "source": case["crm"]["ref"]}


def route(policy, fact):
    if fact["status"] == "unresolved_message":
        return "clarify_policy", policy["authority"], "unresolved_evidence"
    if fact["current"] is None:
        return "ask", "buyer", "missing_current_value"
    if fact["current"] not in policy["allowed"]:
        return "clarify_policy", policy["authority"], "outside_approved_scope"
    return "ready", "coordinator", "supported_within_policy"


def draft(case, decision):
    field, question = "", ""
    if decision == "ask":
        field = case["policy"]["field"]
        question = case["policy"]["questions"][case["locale"]]
    return {"id": case["id"], "decision": decision, "field": field, "question": question}


def verify(case, proposal):
    """Re-read the supplied sources here, as a reviewer would. Return an unsigned advisory proposal only."""
    projection = project(case)
    fact = resolve(case, projection)
    decision, recipient, reason = route(case["policy"], fact)
    if proposal != draft(case, decision):
        raise ValueError("Proposal differs from the grounded decision or approved question")
    return {"sources": projection["sources"], "buyer_statement": projection["statement"], "fact": fact,
            "recipient": recipient, "reason": reason, "proposal": proposal, "confirmation": "human_review_required"}
