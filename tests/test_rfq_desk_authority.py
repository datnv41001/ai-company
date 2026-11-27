"""Capture public synthetic inputs from the existing restricted PostgreSQL APIs."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from agency_fixtures import account, create
from app import c3_assets
from app.access import set_context
from app.database import engine
from app.knowledge_store import canonical, digest
from app.security import sign_actor
from campaign_planner_fixtures import CASES, prepare_inputs
from identity_fixtures import invite_member
from knowledge_fixtures import accepted
from scripts.rfq_evidence import build_card
from test_channel_editions import commission
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_storyboard_distribution import run_connected_distribution

pool = registry_pool


def export_fixture(name, value):
    if directory := os.getenv("AMC_RFQ_EVIDENCE"):
        path = Path(directory) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        # A new capture is a distinct experiment with new IDs. Never replace a prior capture.
        with path.open("x", encoding="utf8", newline="\n") as file:
            file.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def count_commands(actor, tenant, cid, *, restricted=False):
    query = "SELECT count(*) FROM knowledge_commands WHERE tenant_id=:tid AND result->>'campaign_id'=:cid"
    if restricted:
        query += " AND visibility='restricted' AND operation='campaign_sandbox_v2'"
    with Session(engine) as db:
        set_context(db, actor=actor["id"], tenant=tenant)
        sign_actor(db, actor["id"])
        return db.scalar(text(query), {"tid": tenant, "cid": cid})


def check_authority(lab, owner, operator, scope, plan, initial, correction):
    api, tid, cid = lab.api, owner["tenant"], scope["campaign_id"]
    base = "/api/tenants/" + tid
    campaign = base + "/campaigns/" + cid
    desk = campaign + "/business-desk"
    customer_a = lab.cases[0][2]
    campaigns = accepted(api.get(base + "/campaigns", headers=owner["headers"]))
    a = next(item for item in campaigns if item["id"] == cid)
    client_b = create(api, base + "/clients", owner, {"name": "RFQ isolation client"})["id"]
    customer_b = account(api, "DeskCustomerB")
    invite_member(api, base, owner["headers"], customer_b["headers"], email=customer_b["email"], role="client_viewer", client_id=client_b)
    b_brand = create(api, base + "/brands", owner, {"name": "RFQ isolation fixture", "client_id": client_b})["id"]
    b = create(api, base + "/campaigns", owner, {"name": a["name"], "brand_id": b_brand,
               "brief": "Synthetic parallel RFQ campaign", "objective": "Verify signed Business Desk scope"})
    assert b["name"] == a["name"] and b["id"] != a["id"] and b_brand != a["brand_id"]
    other_desk = base + "/campaigns/" + b["id"] + "/business-desk"
    [snapshot], _ = prepare_inputs(api, owner, customer_b, client_b, b_brand, b["id"], CASES[0], workflows=(c3_assets.LANDING,))
    other_plan = commission(api, base, owner, b["id"], snapshot)
    other_case = accepted(api.post(base + "/campaigns/" + b["id"] + "/sandbox/commands", headers=owner["headers"], json={
        "kind": "rfq", "request_id": uuid4().hex, "plan_id": other_plan["id"], "rfq_id": "buyer-b-inquiry",
        "product_id": other_plan["product_id"], "unit": "box", "quantity": "2", "location": "Synthetic site B",
        "required_date": datetime.now(timezone.utc).date().isoformat(), "contact_purpose": "quote_request",
        "occurred_at": datetime.now(timezone.utc).isoformat()}))
    old_cut = {"recorded_as_of": initial["recorded_at"]}
    seller, replacement = [reader(api, owner, "viewer") for _ in range(2)]
    reviewer = reader(api, owner, "viewer")
    assertions = []

    def check(label, expected, actual):
        assert expected == actual, (label, expected, actual)
        assertions.append({"case": label, "expected": expected, "actual": actual})

    def grant(actor, role, enabled=True, expected_revision=0, endpoint=desk):
        return accepted(api.post(endpoint + "/grants", headers=owner["headers"], json={
            "key": uuid4().hex, "subject": actor["id"], "role": role,
            "enabled": enabled, "expected_revision": expected_revision}))

    def inbox(actor, role, endpoint=desk):
        return api.get(endpoint + "/" + role + "/inbox", headers=actor["headers"], params=old_cut)

    def ids(actor, role, endpoint=desk):
        return [i["value"]["id"] for i in accepted(inbox(actor, role, endpoint))["items"]]

    for customer, client_id, own, foreign in ((customer_a, scope["client_id"], a, b), (customer_b, client_b, b, a)):
        accounts = accepted(api.get(base + "/clients", headers=customer["headers"]))
        check("customer sees its own client record " + own["id"], [client_id], [item["id"] for item in accounts])
        visible = {item["id"] for item in accepted(api.get(base + "/campaigns", headers=customer["headers"]))}
        check("raw agency campaigns are internal " + own["id"], [False, False], [own["id"] in visible, foreign["id"] in visible])
        for endpoint in (desk, other_desk):
            check("client Desk access " + own["id"] + " " + endpoint.split("/")[-2], 404, inbox(customer, "sales_recipient", endpoint).status_code)
    check("foreign tenant operator", 404, inbox(lab.y, "marketing_operator").status_code)
    check("same agency, same campaign name without role B", 404, inbox(operator, "marketing_operator", other_desk).status_code)
    grant(operator, "marketing_operator", endpoint=other_desk)
    check("same agency, same campaign name with role B", [other_case["entity_id"]], ids(operator, "marketing_operator", other_desk))
    check("same agency role A", [initial["entity_id"]], ids(operator, "marketing_operator"))

    grant(seller, "sales_recipient")
    grant(replacement, "sales_recipient")
    grant(reviewer, "reviewer")
    grant(reviewer, "sales_recipient")
    check("reviewer with both roles keeps reviewer projection", ["id", "plan_id", "revision", "state"],
          sorted(accepted(inbox(reviewer, "reviewer"))["items"][0]["value"]))
    check("second role does not inherit case assignment", [], ids(reviewer, "sales_recipient"))
    check("unassigned Sales", [], ids(seller, "sales_recipient"))
    check("operator direct restricted RFQ journal", 0, count_commands(operator, tid, cid, restricted=True))
    check("reviewer direct restricted RFQ journal", 0, count_commands(reviewer, tid, cid, restricted=True))
    check("existing approver sees synthetic journal", True, count_commands(owner, tid, cid, restricted=True) > 0)
    before = count_commands(owner, tid, cid)
    for _ in range(2):
        latest = accepted(inbox(operator, "marketing_operator"))["items"]
        assert latest == [{"entity": "leads", "value": correction["value"]}]
    check("repeat reads at an old cutoff return the current Desk revision", 2, latest[0]["value"]["revision"])
    check("repeat signed inbox GETs append no command", before, count_commands(owner, tid, cid))
    def route(step, recipient, revision):
        return accepted(api.post(desk + "/marketing_operator/decisions", headers=operator["headers"], json={
            "kind": "sales", "request_id": uuid4().hex, "plan_id": plan["id"], "rfq_id": initial["entity_id"],
            "expected_revision": revision, "step": step, "assignee_id": recipient["id"],
            "occurred_at": datetime.now(timezone.utc).isoformat(), "reason": "Synthetic assignment verification"}))
    route("assign", seller, 2)
    check("assigned Sales", [initial["entity_id"]], ids(seller, "sales_recipient"))
    check("assigned Sales direct restricted RFQ journal", 0, count_commands(seller, tid, cid, restricted=True))
    route("reassign", replacement, 3)
    check("removed assignment with old cutoff", [], ids(seller, "sales_recipient"))
    check("replacement assignee", [initial["entity_id"]], ids(replacement, "sales_recipient"))
    grant(replacement, "sales_recipient", False, 1)
    check("revoked role with old cutoff", 404, inbox(replacement, "sales_recipient").status_code)
    return {"backend": "PostgreSQL", "campaign_a": a["id"], "campaign_b": b["id"], "campaign_name": a["name"],
            "client_a": scope["client_id"], "client_b": client_b, "inquiry_id": initial["entity_id"],
            "cutoff": initial["recorded_at"], "revision_at_cutoff": 1, "checks": assertions}


def capture_two_revisions(lab, owner, operator, proposed_plan, plan, visit, first, metric, contract):
    val, api = first["value"], lab.api
    scope = {key: val["landing_source"][key] for key in ("tenant_id", "client_id", "brand_id", "campaign_id")}
    assert val["revision"] == 1 and val["quantity"] == "1" and val["minimum_order_quantities"] == ["5"]
    assert val["unit"] == "box" and val["missing"] == ["commercial_moq"]
    assert visit["entity_id"] == val["session_id"] and visit["value"]["landing_source"] == val["landing_source"]
    assert plan["product_id"] == val["product_id"] and plan["intake_contract"] == contract
    assert plan["digest"] == val["landing_source"]["plan_digest"]
    plan_snapshot = {key: value for key, value in proposed_plan.items() if key != "digest"}
    assert digest(canonical(plan_snapshot)) == proposed_plan["digest"] == plan["digest"]
    sandbox = "/api/tenants/" + scope["tenant_id"] + "/campaigns/" + scope["campaign_id"] + "/sandbox"
    payload = {"kind": "complete_rfq", "request_id": uuid4().hex, "plan_id": plan["id"],
               "rfq_id": first["entity_id"], "expected_revision": 1, "quantity": "5",
               **{key: val[key] for key in ("location", "required_date", "contact_purpose")}}
    second = accepted(api.post(sandbox + "/commands", headers=owner["headers"], json=payload))
    assert second == accepted(api.post(sandbox + "/commands", headers=owner["headers"], json=payload))
    assert second["entity_id"] == first["entity_id"] and second["value"]["revision"] == 2
    assert second["sequence"] > first["sequence"] > visit["sequence"] and second["recorded_at"] > first["recorded_at"]
    assert second["value"]["missing"] == [] and second["value"]["quantity"] == "5"
    assert second["value"]["last_event_at"] == val["last_event_at"] and "occurred_at" not in payload
    assert not any(second["value"][key] for key in ("sales_accepted", "quoted", "ordered", "confirmed"))
    state = accepted(api.get(sandbox, headers=owner["headers"], params={"measurement_plan_id": plan["id"]}))
    updated = state["intake_measurement"]
    assert metric["version"] == updated["version"] == "intake-funnel/2"
    assert metric["qualified_rfqs"] == 0 and updated["qualified_rfqs"] == 1
    assert metric["sales_accepted"] == updated["sales_accepted"] == metric["quotes_issued"] == updated["quotes_issued"] == 0
    assert metric["orders"] == updated["orders"] == metric["confirmed_revenue_vnd"] == updated["confirmed_revenue_vnd"] == 0
    assert plan["measurement_plan"].get("primary") is None and "primary_measurement" not in state["optimization"]["evidence"]
    # Privileged fixture setup exports only these three authoritative API receipts from one synthetic journey.
    # The application exposes no historical card reader. All authority tests below use actual current role sessions.
    events = [visit, first, second]
    generated = datetime.now(timezone.utc).isoformat()
    pre_read_count = count_commands(owner, scope["tenant_id"], scope["campaign_id"])
    for event, expected_qty, expected_revision in ((first, "1", 1), (second, "5", 2)):
        inputs = dict(scope=scope, inquiry_id=first["entity_id"], events=events, recorded_as_of=event["recorded_at"], generated_at=generated)
        card = build_card(**inputs)
        assert card == build_card(**inputs)
        assert card["request"]["quantity"] == expected_qty and card["revision"] == expected_revision
        assert card["qualification"]["status"] == "no_authorized_receipt"
    assert count_commands(owner, scope["tenant_id"], scope["campaign_id"]) == pre_read_count
    after_read = accepted(api.get(sandbox, headers=owner["headers"], params={"measurement_plan_id": plan["id"]}))
    assert after_read["intake_measurement"] == updated and "primary_measurement" not in after_read["optimization"]["evidence"]
    lineage = {"synthetic": True, "backend": "PostgreSQL", "scope": scope, "inquiry_id": first["entity_id"],
               "events": events, "cutoffs": {"revision_1": first["recorded_at"], "revision_2": second["recorded_at"]},
               "generated_at": generated,
               "provenance": {"plan_id": plan["id"], "revision": plan["revision"], "digest": plan["digest"], "plan_snapshot": plan_snapshot,
                              "approval": plan["approval"], "manifest": plan["manifests"]["landing"],
                              "product_id": plan["product_id"], "product": plan["product"], "sku": plan["sku"],
                              "intake_contract": contract},
               "measurement": {"revision_1": metric, "revision_2": updated, "primary_measurement": None}}
    authority = check_authority(lab, owner, operator, scope, plan, first, second)
    export_fixture("lineage.json", lineage)
    export_fixture("authority.json", authority)


@PG
def test_new_synthetic_rfq_lineage_and_current_desk_authority(pool):
    run_connected_distribution(pool, 2, inspect_intake=capture_two_revisions)
