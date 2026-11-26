"""Reconcile archived synthetic Studio intake with the production funnel, without external I/O."""
import argparse
import json
from pathlib import Path
from app.business_intake import funnel
from app.knowledge_store import canonical, digest, parse_time
from app.measurement_integrity import evaluate, matched_landing


def readback(packet):
    intake, landing = packet["intake"], packet["landing"]
    contract = intake["contract"]
    plan = {"id": intake["plan_id"], "digest": intake["plan_digest"], "intake_contract": contract}
    events = {event["id"]: event for event in packet["events"]}
    visit, submission = (events[intake[key]] for key in ("visit_id", "submitted_id"))
    session, request = visit["value"], submission["value"]
    if (intake["synthetic"] is not True or contract["digest"] != digest(canonical(
        {key: value for key, value in contract.items() if key != "digest"}
    )) or contract != landing["master"]["intake_contract"] or contract["plan_id"] != plan["id"]):
        raise ValueError("Intake definition does not match the approved landing")
    action = contract["action"]
    bucket = {"rfq": "leads", "appointment": "appointments"}[action]
    source = session["landing_source"]
    expected = {"campaign_id": visit["campaign_id"], "plan_id": plan["id"], "plan_digest": plan["digest"],
                "package_id": landing["id"], "package_version": landing["version"], "package_digest": landing["digest"],
                "studio_revision": landing["studio_revision"], "document_id": landing["did"],
                "file_digest": landing["files"]["landing.html"]["sha256"], "intake_contract_digest": contract["digest"]}
    if (len(events) != len(packet["events"]) or visit["entity"] != "sessions" or submission["entity"] != bucket
            or request["id"] != submission["entity_id"] or session["id"] != visit["entity_id"]
            or submission["campaign_id"] != visit["campaign_id"] or visit["sequence"] >= submission["sequence"]
            or any(row["plan_id"] != plan["id"] for row in (visit, submission, session, request, landing))
            or request["session_id"] != session["id"] or parse_time(session["occurred_at"]) > parse_time(request["occurred_at"])
            or not matched_landing(session, request, expected) or intake["package_id"] != landing["id"]
            or intake["package_digest"] != landing["digest"] or intake["file"] != landing["files"]["landing.html"]
            or request["intake"]["consent"].get("granted") is not True):
        raise ValueError("Visit, submission or approved edition mismatch")
    state = {"sessions": {session["id"]: session}, bucket: {request["id"]: request}}
    observed = funnel(plan, state)
    if observed != intake["landing_funnel"]:
        raise ValueError("Single-journey replay disagrees with the archived intake report")
    primary = intake["primary_measurement"]
    if contract["measurement_digest"]:
        if not primary or primary["contract"]["digest"] != contract["measurement_digest"]:
            raise ValueError("Expected the approved KPI definition")
        replay = evaluate(primary["contract"], plan["id"], state, parse_time(primary["as_of_inclusive"]),
                          contract["locale"], landing_scope=expected)
        if replay != primary:
            raise ValueError("Windowed service KPI disagrees with source events")
    elif primary is not None:
        raise ValueError("No approved primary KPI for this journey")
    return {"case": intake["case"], "plan_digest": plan["digest"], "contract_digest": contract["digest"],
            "landing_sha256": source["file_digest"], "journal_receipts": [visit["id"], submission["id"]],
            "window": observed["window"], "visit": observed["landing_visits"],
            "inquiry": observed.get("inquiries"), "qualified_rfq": observed.get("qualified_rfqs"),
            "sales_acceptance": observed.get("sales_accepted"), "quote": observed.get("quotes_issued"),
            "order": observed.get("orders"), "confirmed_revenue_vnd": observed.get("confirmed_revenue_vnd"),
            "appointment_request": observed["valid_submissions"] if action == "appointment" else None,
            "confirmed_appointment": observed.get("confirmed"), "assignee_at_submission": request["assignee_id"],
            "primary_measurement": primary, "creative_effect_estimate": None,
            "missing_for_effect": ["randomized_assignment_receipts", "variant_exposure", "complete_followup"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packets", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps([readback(json.loads(path.read_text(encoding="utf-8"))) for path in args.packets],
                     indent=2, ensure_ascii=False))
