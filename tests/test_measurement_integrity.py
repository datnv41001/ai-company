"""Frozen Luồng Rõ RED and a distinct completed-service cohort on authorized synthetic records."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app import c3_assets, c3_customer_assets, c3_releases, c3_studio, campaign_channels, measurement_integrity as metrics
from app.knowledge_contracts import KPI
from app.knowledge_store import parse_time
from campaign_planner_fixtures import prepare_inputs
from knowledge_fixtures import accepted, revision
from test_claim_desk import reader


DATA = Path(__file__).parent / "evaluation/kpi_integrity"
HISTORICAL = json.loads((DATA / "luong-ro.json").read_text(encoding="utf-8"))
HOLDOUT = json.loads((DATA / "holdout.json").read_text(encoding="utf-8"))


def definition(outcome, days):
    return {"version": "appointment-measurement/1", "business_outcome": outcome, "window_days": days, "owner_role": "service_operations"}


def test_optimization_source_revisions_matter_even_with_identical_totals():
    from app.campaign_operations import measurement_inputs_digest
    from app.campaign_operations_crm import reconcile

    state = {"appointments": {}, "actions": {}, "leads": {}, "sessions": {"s": {"visitor": "visitor-a"}}}
    corrected = {**state, "sessions": {"s": {"visitor": "visitor-b"}}}
    assert reconcile(state) == reconcile(corrected)
    assert measurement_inputs_digest(state, {"digest": "plan-1"}) != measurement_inputs_digest(corrected, {"digest": "plan-1"})
    assert measurement_inputs_digest(state, {"digest": "plan-1"}) != measurement_inputs_digest(state, {"digest": "plan-2"})


def test_approved_definition_cannot_disagree_with_free_text():
    payload = {"measurement": definition("appointment.confirmed_per_requested", 21), "name": "Confirmation rate", "objective": "a" * 36}
    model = KPI.model_validate(payload)
    assert model.unit == "ratio" and model.window == "21 days"
    for change in ({"method": "per visit"}, {"unit": "page_views"}, {"window": "3 days"}, {"owner": "unapproved operator"}):
        with pytest.raises(ValidationError):
            KPI.model_validate(payload | change)
    with pytest.raises(ValidationError):
        KPI.model_validate(payload | {"measurement": payload["measurement"] | {"numerator": "page.view"}})


def test_archived_approved_source_and_signed_edition_disagree_before_fix():
    projection = HISTORICAL["projection"]
    bad = HISTORICAL["published_groups"]
    assert "số đề nghị khảo sát" in projection["kpi"]
    assert "trên lượt vào" in bad["measurement"]["measurement_method"] and "trên lượt vào" in bad["client_measurement"]["method"]
    # Old snapshots have no typed KPI. New editions must disclose that measurement is unqualified.
    expected = metrics.legacy_statement("vi-VN")
    assert c3_studio.compose(c3_assets.RESEARCH, projection)["measurement"]["measurement_method"] == expected
    assert c3_customer_assets.strategy(projection)["client_measurement"]["method"] == expected
    assert {i["group"] for i in metrics.quality_issues(bad, projection)} == {"measurement", "client_measurement"}


def holdout_state():
    cutoff = parse_time(HOLDOUT["observed_at"])
    state = {"appointments": {}, "sessions": {}}

    def row(key, events, *, same_plan=True, attributed=False):
        history = [{"event": event, "at": (cutoff + timedelta(days=delta)).isoformat()} for event, delta in events]
        state["appointments"][key] = {"id": key, "plan_id": "holdout" if same_plan else "other", "history": history, "session_id": key if attributed else None}
        if attributed:
            state["sessions"][key] = {"id": key, "plan_id": "holdout", "action_id": "authorized-test-action", "occurred_at": history[0]["at"]}

    row("A", [("requested", -13), ("confirmed", -12), ("assigned", -11), ("completed", -10)], attributed=True)
    row("B", [("requested", -4), ("confirmed", -3), ("cancelled", -2)])
    row("C", [("requested", -1), ("confirmed", 0), ("completed", 1)])
    row("too-early", [("requested", -15), ("confirmed", -14), ("completed", -13)])
    row("request-only", [("requested", -1)])
    row("foreign", [("requested", -1), ("confirmed", 0)], same_plan=False)
    return cutoff, state


def test_frozen_holdout_rejects_denominator_window_attribution_and_duplicates():
    cutoff, state = holdout_state()
    contract = metrics.terms(definition(HOLDOUT["primary"], HOLDOUT["days"]))
    report = metrics.evaluate(contract, "holdout", state, cutoff)
    assert {k: report[k] for k in ("numerator", "denominator", "unattributed", "cancelled")} == {
        k: HOLDOUT["expected"][k] for k in ("numerator", "denominator", "unattributed", "cancelled")
    }
    assert report["ratio"] == HOLDOUT["expected"]["rate"]
    assert metrics.evaluate(contract, "empty", state, cutoff)["ratio"] is None
    state["appointments"]["A"]["history"].append(dict(state["appointments"]["A"]["history"][1]))
    assert metrics.evaluate(contract, "holdout", state, cutoff) == report


def test_rescheduling_cannot_reenter_a_prior_confirmation_cohort():
    cutoff,state=holdout_state()
    contract=metrics.terms(definition("appointment.completed_per_confirmed",14))
    report=metrics.evaluate(contract,"holdout",state,cutoff)
    # This confirmation is exactly on the open lower bound. The service is still pending
    # when Marketing reschedules inside the reporting period, then finishes it normally.
    row=state["appointments"]["too-early"]
    row["history"]=[*row["history"][:2],
        {"event":"confirmed","step":"reschedule","at":(cutoff-timedelta(days=10)).isoformat()},
        {"event":"assigned","step":"assign","at":(cutoff-timedelta(days=9)).isoformat()},
        {"event":"completed","at":(cutoff-timedelta(days=8)).isoformat()}]
    assert metrics.evaluate(contract,"holdout",state,cutoff)==report


def test_secondary_quotes_count_only_the_explicit_plan_and_settlements():
    from app import campaign_operations_crm as crm
    lead={"confirmed":True,"state":"confirmed","session_id":None,"gross_vnd":90,"refunded_vnd":10,"missing":[],
          "sales_accepted":True,"quoted":True,"ordered":True}
    state={"sessions":{},"actions":{},"leads":{"scoped":dict(lead,plan_id="v2"),"previous":dict(lead,plan_id="v1")}}
    plan={"id":"v2","buyer_action":"appointment"}
    assert crm.secondary_rfq_funnel(plan,state) is None
    secondary=crm.secondary_rfq_funnel(dict(plan,secondary_conversions=["rfq"]),state)
    assert (secondary["plan_id"],secondary["window"],secondary["rfqs"],secondary["confirmed_orders"])==("v2","plan_lifetime",1,1)
    assert (secondary["confirmed_revenue_vnd"],secondary["refunds_vnd"])==(80,10)


@pytest.mark.parametrize("case_name", ["luong-ro", "holdout"])
def test_scoped_campaign_through_final_edition_and_crm(api, agency, case_name):
    owner, base, ((customer, scope), (other, other_scope)) = agency
    cid = next(iter(scope["campaigns"]))
    brand = next(c["brand_id"] for c in accepted(api.get(base + "/campaigns", headers=owner["headers"])) if c["id"] == cid)
    case = dict(HISTORICAL["case"])
    outcome, days = "appointment.confirmed_per_requested", 21
    if case_name == "holdout":
        case.update(
            company="Dịch vụ thiết bị Mực Chuẩn",
            brand="Mực Chuẩn",
            product=HOLDOUT["product"],
            audience=HOLDOUT["buyer"],
            sku="MC-KT",
            objective=HOLDOUT["purpose"],
            kpi="Tỷ lệ hoàn tất buổi kiểm tra",
            kpi_method=HOLDOUT["cohort"],
            wording="Bàn giao biên bản kiểm tra điểm cân",
            qualifier="Trong phạm vi một buổi kiểm tra.",
            amount=510000,
            hypotheses=["Ca vận hành có thể ảnh hưởng thời điểm đặt lịch; cần phỏng vấn trước khi kết luận."],
            cta="Đặt lịch kiểm tra, nêu địa điểm và thời gian bàn giao.",
        )
        outcome, days = HOLDOUT["primary"], HOLDOUT["days"]
    case["measurement"] = definition(outcome, days)
    manifests, setup = prepare_inputs(api, owner, customer, next(iter(scope["clients"])), brand, cid, case)
    assert len(manifests) == 2
    contract = manifests[0]["projection"]["measurement_contract"]
    assert contract == manifests[1]["projection"]["measurement_contract"]
    assert contract["id"] == setup["selections"]["kpi"] and contract["revision"] == 1 and len(contract["digest"]) == 64
    assert contract["business_outcome"] == outcome
    if case_name == "luong-ro":
        catalog_path = setup["ui"].rsplit("/business-workspace", 1)[0] + "/catalog/items/"
        data = accepted(api.get(catalog_path + contract["id"], headers=owner["headers"]))["data"]
        alternative = revision(
            api,
            owner,
            setup["path"],
            "service-completion",
            "kpi",
            {
                "name": "Buổi hoàn tất",
                "objective": setup["selections"]["objective"],
                "source": data["source"],
                "measurement": definition("appointment.completed_per_confirmed", 14),
            },
        )
        alternate = api.post(
            setup["marketing"] + "/manifests", headers=owner["headers"], json={**setup["params"], "key": uuid4().hex, "kpi": alternative["id"]}
        )
        assert alternate.status_code == 409 and "KPI" in alternate.text
        unpinned = accepted(
            api.post(
                setup["ui"] + "/briefs",
                headers=owner["headers"],
                json={
                    "key": uuid4().hex,
                    "title": "Luồng Rõ · chỉ ghim mục tiêu",
                    "expected_revision": 1,
                    "expected_company_revision": 1,
                    "selections": {k: v for k, v in setup["selections"].items() if k != "kpi"},
                },
            )
        )
        absent = api.post(
            setup["marketing"] + "/manifests", headers=owner["headers"], json={**setup["params"], "key": uuid4().hex, "workspace_brief_id": unpinned["id"]}
        )
        assert absent.status_code == 409 and "KPI" in absent.text
    root = base + "/campaigns/" + cid
    body = {"key": uuid4().hex, "expected_revision": 0, "manifest_ids": [s["id"] for s in manifests], "duration_days": days, "budget_vnd": 0}
    other_route = base + "/campaigns/" + next(iter(other_scope["campaigns"]))
    assert api.post(other_route + "/engine/plans", headers=owner["headers"], json=body).status_code == 404
    plan = accepted(api.post(root + "/engine/plans", headers=owner["headers"], json=body))
    approved = accepted(
        api.post(root + "/engine/plans/" + plan["id"] + "/approve", headers=owner["headers"], json={"key": uuid4().hex, "expected_digest": plan["digest"]})
    )
    assert plan["measurement_contract"] == plan["measurement_plan"]["primary"] == contract
    production = accepted(api.get(root + "/engine/plans/" + plan["id"] + "/production", headers=owner["headers"]))
    assert len(production["assets"]) == 4 and all(a["measurement_contract"] == contract for a in production["assets"])
    for item in manifests:
        projection = item["projection"]
        for role in ("director", *c3_assets.ROLES[item["workflow"]]):
            context = c3_releases.role_view(item["workflow"], role, projection)
            assert ("primary_measurement" in context) == (role in ("director", "research", "strategy"))
            if "primary_measurement" in context:
                assert "id" not in context["primary_measurement"] and "digest" not in context["primary_measurement"]
    projection = manifests[0]["projection"]
    groups = c3_studio.compose(c3_assets.RESEARCH, projection) | c3_customer_assets.strategy(projection)
    ctx = {"due_days": {p["id"]: p["due_day"] for p in plan["work_packages"]}, "channel_plan": ["web"]}
    groups.update(campaign_channels.compose(projection, ctx))
    expected = metrics.statement(contract, "vi-VN")
    assert groups["measurement"]["measurement_method"] == groups["client_measurement"]["method"] == groups["ad"]["measurement"] == expected
    assert not metrics.quality_issues(groups, projection)
    secondary = metrics.secondary_statement("vi-VN")
    separated = metrics.editorial_method(projection, "KPI chính là lượt xem.\n" + secondary)
    assert separated == expected + "\n" + secondary
    assert metrics.quality_issues({"measurement": {"measurement_method": separated}}, projection) == []
    for group, field in (("measurement", "measurement_method"), ("client_measurement", "method"), ("ad", "measurement")):
        damaged = deepcopy(groups)
        damaged[group][field] = expected + " KPI chính được tính trên số lượt vào trang."
        assert metrics.quality_issues(damaged, projection) == [{"group": group, "field": field, "reason": "primary_measurement_mismatch"}]
    for group, field in (("client_strategy", "decision"), ("ad", "description"), ("social", "opening")):
        changed = deepcopy(groups)
        changed[group][field] += " KPI chính là lượt xem trang."
        assert metrics.quality_issues(changed, projection) == [{"group": group, "field": field, "reason": "unbound_measurement_definition"}]

    def get_report():
        return accepted(api.get(root + "/sandbox", headers=owner["headers"]))["report"]["primary_measurement"]

    assert api.get(root + "/sandbox", headers=other["headers"]).status_code in (403, 404)
    assert get_report()["ratio"] is None
    assert api.get(root + "/sandbox", params={"measurement_plan_id": str(uuid4())}, headers=owner["headers"]).status_code == 404
    scoped_report = accepted(api.get(root + "/sandbox", params={"measurement_plan_id": plan["id"]}, headers=owner["headers"]))
    assert scoped_report["report"]["primary_measurement"]["contract"] == contract
    now = datetime.now(timezone.utc) - timedelta(days=2)

    def at(hours):
        return (now + timedelta(hours=hours)).isoformat()

    def send(kind, actor=owner, **fields):
        return accepted(
            api.post(root + "/sandbox/commands", headers=actor["headers"], json={"request_id": uuid4().hex, "plan_id": plan["id"], "kind": kind, **fields})
        )

    waiting_id = uuid4().hex
    send("propose_optimization", proposal_id=waiting_id)
    receipt_ids = []
    for ident in ("first", "second", "third"):
        req = send(
            "appointment",
            appointment_id=ident,
            product_id=plan["product_id"],
            unit="visit",
            quantity="1",
            contract="service-appointment/1",
            location="Cơ sở tổng hợp",
            service_scope="Một ca khảo sát trong sandbox",
            requested_for=at(3),
            contact_purpose="appointment_request",
            occurred_at=at(0),
        )
        receipt_ids.append(req["id"])
        if case_name == "holdout" or ident != "third":
            receipt_ids.append(
                send("appointment_decision", appointment_id=ident, step="confirm", expected_revision=1, occurred_at=at(1), confirmed_for=at(3))["id"]
            )
        if ident == "first":
            staff = reader(api, owner, "admin")
            receipt_ids.append(
                send("appointment_decision", appointment_id=ident, step="assign", expected_revision=2, occurred_at=at(2), assignee_id=staff["id"])["id"]
            )
            receipt_ids.append(
                send(
                    "appointment_decision",
                    staff,
                    appointment_id=ident,
                    step="complete",
                    expected_revision=3,
                    occurred_at=at(4),
                    feedback="Đã giao biên bản thử.",
                )["id"]
            )
        if ident == "second":
            receipt_ids.append(
                send("appointment_decision", appointment_id=ident, step="cancel", expected_revision=2, occurred_at=at(2), feedback="Khách đổi kế hoạch.")["id"]
            )
    report = get_report()
    assert report["numerator"] == (2 if case_name == "luong-ro" else 1) and report["denominator"] == report["unattributed"] == 3
    assert report["secondary_metrics"] == [{"metric_id": "web.sessions", "unit": "session_count", "value": 0}]
    assert report["cancelled"] == 1 and report["ratio"] == report["numerator"] / 3 and report["contract"] == contract
    # The other approver sees the original measurement cutoff. An intervening CRM
    # change invalidates a proposal; an unchanged source still approves after time advances.
    stale = api.post(root + "/sandbox/commands", headers=staff["headers"],
                     json={"request_id": uuid4().hex, "plan_id": plan["id"], "kind": "approve_optimization", "proposal_id": waiting_id})
    assert stale.status_code == 409
    fresh_id = uuid4().hex
    send("propose_optimization", proposal_id=fresh_id)
    send("approve_optimization", staff, proposal_id=fresh_id)
    resolved = accepted(api.get(root + "/sandbox", headers=owner["headers"]))
    decision = next(p for p in resolved["proposals"] if p["id"] == fresh_id)
    assert decision["status"] == "approved" and decision["evidence"]["primary_measurement"]["contract"] == contract
    if output := os.getenv("AMC_KPI_EVIDENCE"):
        destination = Path(output)
        destination.mkdir(parents=True, exist_ok=True)
        result = {
            "fixture": case_name,
            "source": "synthetic authenticated campaign API; deterministic editions, no model inference",
            "knowledge_revision": contract,
            "brief_pins": setup["selections"],
            "manifests": [{k: s[k] for k in ("id", "digest", "workflow")} for s in manifests],
            "plan": {"id": plan["id"], "digest": plan["digest"], "revision": plan["revision"]},
            "approval": approved["status"],
            "strategy_method": groups["measurement"]["measurement_method"],
            "customer_method": groups["client_measurement"]["method"],
            "ad_method": groups["ad"]["measurement"],
            "crm_receipts": receipt_ids,
            "actual_analytics": report,
        }
        (destination / f"{case_name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if case_name == "luong-ro" and str(api.base_url).startswith("http://127.0.0.1:") and (browser_output := os.getenv("AMC_KPI_BROWSER")):
        from kpi_integrity_browser import capture

        capture(str(api.base_url).rstrip("/"), owner, owner["tenant"], next(iter(scope["clients"])), brand, cid, setup, contract, browser_output)
