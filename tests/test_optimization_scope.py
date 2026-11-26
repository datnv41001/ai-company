"""The same campaign can change journey, KPI and outcome while old plans are settled."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import campaign_operations as ops, measurement_integrity as metrics
from app.knowledge_store import parse_time, stamp


CUTOFF = parse_time("2026-11-21T12:00:00Z")


def plan(pid, journey, *, measured=False):
    p = {"id": pid, "campaign_id": "factory", "digest": pid + "-digest", "buyer_action": journey,
         "locale": "vi-VN", "measurement_plan": {"kpi": "Confirmed visits" if journey == "appointment" else "RFQs qualified"}}
    if measured:
        p["measurement_contract"] = metrics.terms({"version": "appointment-measurement/1",
            "business_outcome": "appointment.completed_per_confirmed", "window_days": 14, "owner_role": "service_operations"}) | {
                "id":"service-outcome", "revision": 2, "digest":"approved-definition"}
        p["secondary_conversions"] = ["rfq"]
    return p


def appointment(pid, hist):
    history = [{"event": event, "step": step, "at": stamp(CUTOFF + timedelta(days=day))} for event, step, day in hist]
    return {"id": "visit", "plan_id": pid, "revision": len(history), "state": history[-1]["event"], "history": history,
            "session_id": None, "occurred_at": history[0]["at"]}


def decide(state, p, *, approve=False, proposal_id="review"):
    store = SimpleNamespace(actor="reviewer" if approve else "operator", scope={"tenant_id": "synthetic"}, now=lambda: CUTOFF)
    command = SimpleNamespace(kind="approve_optimization" if approve else "propose_optimization", proposal_id=proposal_id)
    return ops.optimize_command(command, state, store, p)[2]


def test_previous_plan_exception_cannot_steer_new_rfq_plan_or_invalidate_its_proposal():
    state = {k: {} for k in ops.BUCKETS}
    state["appointments"]["old"] = appointment("visits", [("requested", "request", -2), ("cancelled", "cancel", -1)])
    rfq = plan("quotes", "rfq")
    assert ops.reconcile(state)["appointments"]["cancelled"] == 1
    proposed = decide(state, rfq)
    assert proposed["basis"] == "no_rfqs"
    evidence = proposed["evidence"]
    assert (evidence["period"], evidence["plan_id"], evidence["kpi"]) == ("plan_lifetime", "quotes", "RFQs qualified")
    assert evidence["as_of_inclusive"] == stamp(CUTOFF)
    state["proposals"]["review"] = proposed
    state["appointments"]["old"]["revision"] += 1
    assert decide(state, rfq, approve=True)["status"] == "approved"
    # A pending legacy recommendation cannot issue a package based on the old aggregate.
    state["proposals"]["review"] = proposed | {"evidence": ops.reconcile(state)}
    with pytest.raises(HTTPException) as legacy:
        decide(state, rfq, approve=True)
    assert legacy.value.status_code == 409


def test_new_service_plan_uses_signed_denominator_cohort_even_with_secondary_rfq_or_old_no_show():
    service = plan("service", "appointment", measured=True)
    state = {k: {} for k in ops.BUCKETS}
    # First confirmation is outside the 14-day window. Rescheduling inside does not enter the cohort.
    state["appointments"]["expired"] = appointment("service", [("requested","request",-20),("confirmed","confirm",-16),
        ("confirmed","reschedule",-3),("no_show","no_show",-2)])
    state["leads"]["secondary"] = {"plan_id":"service","confirmed":False,"ordered":False,"quoted":False,
        "sales_accepted":False,"missing":[],"session_id":None,"occurred_at":stamp(CUTOFF),"refunded_vnd":0,"state":"qualified"}
    assert ops.reconcile(state)["rfqs"] == 1
    empty = decide(state, service)
    assert empty["basis"] == "no_eligible_appointments"
    primary = empty["evidence"]["primary_measurement"]
    assert primary["ratio"] is None and primary["denominator"] == primary["no_show"] == 0
    assert primary["contract"] == service["measurement_contract"]
    assert empty["evidence"]["period"] == "measurement_window" and primary["window_start_exclusive"] == stamp(CUTOFF-timedelta(days=14))
    state["proposals"]["review"] = empty
    # A backdated confirmation arriving after proposal creation belongs in the frozen cohort.
    hist = [("requested","request",-5),("confirmed","confirm",-3)]
    state["appointments"]["late"] = appointment("service", hist)
    with pytest.raises(HTTPException) as exc:
        decide(state, service, approve=True)
    assert exc.value.status_code == 409
    assert decide(state, service, proposal_id="updated")["basis"] == "appointment_followup"
    state["appointments"]["late"] = appointment("service", [*hist, ("cancelled","cancel",-1)])
    changed = decide(state, service, proposal_id="after-cancellation")
    assert changed["basis"] == "appointment_exceptions"
    assert changed["evidence"]["primary_measurement"]["cancelled"] == 1


def test_replan_from_service_to_rfq_keeps_distinct_kpis_and_historical_reports(api, agency):
    from uuid import uuid4
    from app import c3_assets
    from agency_fixtures import create
    from c3_fixtures import capture
    from c3_task_fixtures import INTENT
    from campaign_planner_fixtures import CASES, prepare_inputs
    from knowledge_fixtures import accepted, revision
    from test_workforce import DATA

    owner, base, ((customer, scope), _) = agency
    cid = next(iter(scope["campaigns"]))
    brand = next(row["brand_id"] for row in accepted(api.get(base+"/campaigns",headers=owner["headers"])) if row["id"] == cid)
    root = base+"/campaigns/"+cid
    case = CASES[1]
    [first], setup = prepare_inputs(api, owner, customer, next(iter(scope["clients"])), brand, cid, case, workflows=(c3_assets.LANDING,))

    def post(path, **data):
        return accepted(api.post(root+path,headers=owner["headers"],json=data))

    def approve(manifest, previous):
        draft = post("/engine/plans",key=uuid4().hex,expected_revision=previous,manifest_ids=[manifest["id"]],duration_days=14,budget_vnd=50000)
        post("/engine/plans/"+draft["id"]+"/approve",key=uuid4().hex,expected_digest=draft["digest"])
        return draft

    old = approve(first, 0)
    now = datetime.now(timezone.utc)
    post("/sandbox/commands",request_id=uuid4().hex,plan_id=old["id"],kind="appointment",contract="service-appointment/1",
         appointment_id="old-visit", product_id=old["product_id"], unit="machine", quantity="1",
         location="Synthetic site",service_scope="Kiểm tra bơm",requested_for=stamp(now),
         contact_purpose="appointment_request",occurred_at=stamp(now-timedelta(days=2)))
    post("/sandbox/commands",request_id=uuid4().hex,plan_id=old["id"],kind="appointment_decision",
         appointment_id="old-visit",step="cancel",expected_revision=1,occurred_at=stamp(now-timedelta(days=1)),
         feedback="Nhà xưởng đổi kế hoạch.")
    # The new brief and measurement selection change while the approved product/brand stay the same.
    title="Yêu cầu báo giá bảo trì máy"
    bid=create(api,base+"/workforce/briefs",owner,{"campaign_id":cid,"recipient_id":customer["id"],"title":title})["id"]
    intent=INTENT | {"product":case["product"],"audience":case["audience"],"buyer_action":"rfq","purpose":title,
                    "deliverable_type":"landing_page","editorial_style":"plain","requirements":["Gửi yêu cầu báo giá."],
                    "acceptance_criteria":["Chuyển yêu cầu hợp lệ tới Sales."]}
    accepted(api.put(base+"/workforce/briefs/"+bid+"/submission",headers=customer["headers"],json=DATA | {"task_intent":intent}))
    path=setup["ui"].rsplit("/business-workspace",1)[0]+"/catalog/items/"+setup["params"]["kpi"]
    prior=accepted(api.get(path,headers=owner["headers"]))["data"]
    new_kpi=revision(api,owner,setup["path"],"rfq-followup","kpi",prior | {"name":"Yêu cầu báo giá hợp lệ"})
    snap=capture(api,owner,setup | {"params":setup["params"] | {"key":uuid4().hex, "kpi":new_kpi["id"],
                 "target":{"campaign_id":cid,"brief_id":bid}}})
    current=approve(snap,1)
    assert old["buyer_action"]=="appointment" and current["buyer_action"]=="rfq"
    assert old["measurement_plan"]["kpi"] != current["measurement_plan"]["kpi"]
    result=post("/sandbox/commands",request_id=uuid4().hex,plan_id=current["id"],kind="propose_optimization",proposal_id="new-rfq")
    assert result["value"]["basis"] == "no_rfqs"
    for selected,basis in ((old,"appointment_exceptions"),(current,"no_rfqs")):
        view=accepted(api.get(root+"/sandbox",params={"measurement_plan_id":selected["id"]},headers=owner["headers"]))
        assert view["report"]["aggregate_scope"]=="campaign_lifetime" and view["report"]["appointments"]["cancelled"]==1
        assert view["optimization"]["basis"]==basis
        evidence=view["optimization"]["evidence"]
        assert evidence["plan_digest"]==selected["digest"] and evidence["kpi"]==selected["measurement_plan"]["kpi"]
