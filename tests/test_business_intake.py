"""Plan selection, optional fields and commercial follow-up for the internal intake contract."""
from copy import deepcopy
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import business_intake as intake
from app.campaign_operations_contracts import CompleteRFQ, Sales
from app.campaign_operations_crm import observation


def test_optional_fields_change_the_plan_contract_without_weakening_the_approved_brief():
    source = {"id": "manifest", "digest": "a"*64, "brief_id": "brief", "workflow": "landing"}
    plan = {"id":"plan", "revision": 4, "locale":"vi-VN", "selling_unit":"visit", "buyer_action":"appointment", "product_id":"service"}
    projection = {"task_intent":{"requirements":["Đặt lịch, ghi địa điểm và ca nhận hàng cần quan sát."]}, "facts":[]}
    requested = [intake.IntakeField(id="site"), intake.IntakeField(id="receiving_shift"),
                 intake.IntakeField(id="preferred_time", required=False)]
    schema = intake.issue(plan, projection, requested, source)
    assert schema["revision"] == 4 and schema["source"] == source
    assert schema["digest"] != intake.issue(plan, projection, None, source)["digest"]
    assert schema["digest"] != intake.issue(plan | {"revision":5}, projection, requested, source)["digest"]
    selected = {"site":"north","receiving_shift":"night"}
    assert intake.validate_answers(schema, schema["digest"], selected, True) == {"location":"north","receiving_shift":"night"}
    assert intake.validate_answers(schema, schema["digest"], selected | {"preferred_time":"7"}, True)["requested_for"] == "7"
    with pytest.raises(HTTPException) as bad:
        intake.validate_answers(schema, schema["digest"], selected | {"receiving_shift":"unknown"}, True)
    assert bad.value.status_code == 422
    for fields in [requested[:1], requested + [requested[0]], [requested[0], intake.IntakeField(id="receiving_shift", required=False)]]:
        with pytest.raises(HTTPException) as changed:
            intake.issue(plan, projection, fields, source)
        assert changed.value.status_code == 409


@pytest.mark.parametrize("cta", ["Đặt lịch khảo sát, ghi địa điểm và mã dây chuyền.",
                                 "Request a quote and provide number of boxes and cable ID.",
                                 "Đặt lịch khảo sát, ghi mã dây chuyền."])
def test_explicit_buyer_list_requires_supported_fields(cta):
    intent = {"requirements": [cta]}
    with pytest.raises(HTTPException, match="unsupported intake field") as denied:
        intake.submitted_fields(intent, strict=True)
    assert denied.value.status_code == 409
    assert intake.submitted_fields(intent) == []  # Archived content packs retain their historical read path.
    internal = {"requirements":["Đối chiếu ghi chú của biên tập, ghi địa điểm và người phê duyệt."]}
    assert intake.submitted_fields(internal, strict=True) == []


def test_sales_followup_rechecks_moq_before_transition():
    lead = {"id":"lead", "unit":"box", "plan_id":"plan", "revision":1, "state":"received", "minimum_order_quantities":["5"],
            "quantity":"3","location":"Synthetic A","required_date":"2030-01-01","contact_purpose":"quote_request"}
    command = {"kind":"complete_rfq","rfq_id":"lead","plan_id":"plan","request_id":"receipt","expected_revision":1,
               "location":"Synthetic A","required_date":date(2030,1,1),"contact_purpose":"quote_request"}
    state = {"leads":{"lead":deepcopy(lead)}}
    for quantity, expected in [("4","received"),("5","qualified")]:
        cmd = CompleteRFQ(**command, quantity=quantity)
        _, _, result = observation(cmd,state,{"id":"plan"},None)
        assert result["state"] == expected
    assert state["leads"]["lead"] == lead


def test_consultation_referral_requires_buyer_permission_and_campaign_grant():
    at=datetime.now(timezone.utc)
    lead={"id":"lead","plan_id":"plan","state":"received","revision":1,"contact_purpose":"none",
          "last_event_at":at.isoformat(),"assignee_id":None}
    cmd=Sales(kind="sales",step="refer",rfq_id="lead",expected_revision=1,assignee_id="sales",
              plan_id="plan",request_id="request",occurred_at=at)
    store=SimpleNamespace(actor="operator",approver=True,now=lambda:at)
    def refer(value,recipient):
        return observation(cmd,{"leads":{"lead":value}},{"id":"plan"},store,coordinator=True,recipient=recipient)
    for row, eligible in ((lead,lambda *_: True),(lead|{"contact_purpose":"quote_request"},lambda *_:False),
                          (lead|{"contact_purpose":"quote_request"},None)):
        with pytest.raises(HTTPException) as denied:
            refer(row,eligible)
        assert denied.value.status_code==409
    assert lead["state"]=="received" and lead["revision"]==1
