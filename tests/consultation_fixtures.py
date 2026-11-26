"""A signed three-box inquiry against MOQ five, through both campaign and organization APIs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from intake_previous_api import previous_api
from knowledge_fixtures import accepted
from test_claim_desk import reader


def settle_inquiry(api, owner, buyer, other, operator, desk, sandbox, original, additional_inquiry, *, pg):
    sales = reader(api, owner, "viewer")
    alternate = reader(api, owner, "viewer")
    value = original["value"]
    plan, ident = original["plan_id"], original["entity_id"]
    assert value["missing"] == ["commercial_moq"] and value["quantity"] == "3"
    assert value["state"] == "received" and value["contact_purpose"] == "quote_request"
    def grant(actor, enabled=True, revision=0):
        return accepted(api.post(desk+"/grants", headers=owner["headers"], json={"key":uuid4().hex,
            "subject":actor["id"], "role":"sales_recipient", "enabled":enabled,"expected_revision":revision}))
    def payload(step, rev, **extra):
        common = {"request_id":uuid4().hex,"plan_id":plan,"rfq_id":ident,"expected_revision":rev,
                  "occurred_at":datetime.now(timezone.utc).isoformat(),**extra}
        if step=="consultation":
            return common | {"kind":step}
        return common | {"kind":"sales","step":step}
    def decision(actor, role, cmd):
        return api.post(desk+"/"+role+"/decisions", headers=actor["headers"], json=cmd)
    def inbox(actor):
        return api.get(desk+"/sales_recipient/inbox",headers=actor["headers"])
    def measure():
        return accepted(api.get(sandbox,headers=owner["headers"]))["intake_measurement"]
    records=[]
    def record(actor, role, cmd):
        result=accepted(decision(actor,role,cmd))
        records.append({"receipt":result["id"],"step":result["step"],"actor":actor["id"],
                        "revision":result["value"]["revision"],"state":result["value"]["state"]})
        return result
    routing="marketing_operator"
    role="sales_recipient"
    grant(sales)
    grant(alternate)
    assert accepted(inbox(sales))["items"]==[]
    assert inbox(buyer).status_code==404 and inbox(other).status_code in (403,404)
    referral=payload("refer",1,assignee_id=sales["id"])
    assert decision(sales,role,referral).status_code==404
    if pg:
        with previous_api("c5c6329599a66fd2dc6011428e7ab8eed9208df4") as old:
            assert old("POST",desk+"/"+routing+"/decisions",operator,referral | {"step":"assign"})["status"]==409
            assert old("POST",desk+"/"+routing+"/decisions",operator,referral)["status"]==422
            old_metrics=old("GET",sandbox,owner)["body"]["intake_measurement"]
            assert old_metrics["qualified_quotes"]==0 and "quotes_issued" not in old_metrics
    first=record(operator,routing,referral)
    assert first["value"]["state"]=="consulting" and not first["value"]["sales_accepted"]
    assert accepted(decision(operator,routing,referral))==first
    assert [x["value"]["id"] for x in accepted(inbox(sales))["items"]]==[ident]
    assert accepted(inbox(alternate))["items"]==[]
    note=payload("consultation",2,note="Buyer requests advice on three boxes; approved MOQ is five.")
    assert decision(alternate,role,note).status_code==404
    assert decision(operator,routing,note).status_code==404
    for step in ("accept","quote","order"):
        assert decision(sales,role,payload(step,2)).status_code==409
    if pg:
        with previous_api("c5c6329599a66fd2dc6011428e7ab8eed9208df4") as old:
            for step in ("quote","order"):
                assert old("POST",desk+"/"+role+"/decisions",sales,payload(step,2))["status"]==409
            assert old("POST",desk+"/"+role+"/decisions",sales,note)["status"]==422
            assert old("GET",desk+"/"+role+"/inbox",sales)["body"]["items"][0]["value"]["revision"]==2
        barrier=Barrier(2)
        def worker(cmd):
            barrier.wait(timeout=10)
            return decision(sales,role,cmd)
        other_note=note | {"request_id":uuid4().hex,"note":"Alternative wording from a second open tab."}
        with ThreadPoolExecutor(max_workers=2) as workers:
            attempts=list(workers.map(worker,[note,other_note]))
        assert sorted(response.status_code for response in attempts)==[200,409]
        if attempts[0].status_code!=200:
            note=other_note
    written=record(sales,role,note)
    assert accepted(decision(sales,role,note))==written
    assert written["value"]["feedback"][-1]["text"]==note["note"]
    assert decision(sales,role,note | {"request_id":uuid4().hex}).status_code==409
    assert decision(sales,role,note | {"note":"different"}).status_code==409
    grant(sales,False,1)
    assert inbox(sales).status_code==404 and decision(sales,role,note).status_code==404
    new_owner=record(operator,routing,payload("reassign",3,assignee_id=alternate["id"],reason="Shift handoff."))
    assert new_owner["value"]["state"]=="consulting"
    grant(sales,True,2)
    assert accepted(inbox(sales))["items"]==[] and decision(sales,role,note).status_code==404
    insufficient=record(alternate,role,payload("consultation",4,quantity="4",note="Buyer now needs four boxes."))
    assert insufficient["value"]["state"]=="consulting" and measure()["qualified_rfqs"]==0
    assert decision(alternate,role,payload("consultation",5,quantity="4.5",note="Invalid fractional box.")).status_code==409
    enough=payload("consultation",5,quantity="5",note="Buyer confirms five boxes for the original site and date.")
    ready=record(alternate,role,enough)
    assert ready["value"]["state"]=="awaiting_assignment" and ready["value"]["intake"]==value["intake"]
    assert accepted(decision(alternate,role,enough))==ready
    for step in ("accept","reject","quote","order"):
        assert decision(alternate,role,payload(step,6,reason="Testing commercial authority.")).status_code==409
    if pg:
        with previous_api("c5c6329599a66fd2dc6011428e7ab8eed9208df4") as old:
            for step in ("accept","reject","quote","order"):
                assert old("POST",desk+"/"+role+"/decisions",alternate,payload(step,6,reason="Read-only handback."))["status"]==409
    metrics=measure()
    assert metrics["qualified_rfqs"]==metrics["qualified_quotes"]==metrics["inquiries"]==1
    assert metrics["quotes_issued"]==metrics["orders"]==metrics["sales_accepted"]==0
    record(operator,routing,payload("assign",6,assignee_id=sales["id"]))
    assert accepted(inbox(alternate))["items"]==[] and decision(alternate,role,enough).status_code==404
    record(sales,role,payload("accept",7,reason="Verified updated quantity and approval."))
    assert measure()["sales_accepted"]==1 and measure()["quotes_issued"]==0
    record(sales,role,payload("quote",8))
    assert measure()["quotes_issued"]==1 and measure()["orders"]==0
    record(sales,role,payload("order",9))
    confirmed=payload("confirm",10,amount_vnd=5000)
    if pg:
        with previous_api("c5c6329599a66fd2dc6011428e7ab8eed9208df4") as old:
            assert old("POST",sandbox+"/commands",owner,confirmed)["body"]["value"]["state"]=="confirmed"
    else:
        accepted(api.post(sandbox+"/commands",headers=owner["headers"],json=confirmed))
    settled=measure()
    assert settled["current_states"]=={"confirmed":1}
    assert settled["valid_submissions"]==settled["orders"]==1 and settled["confirmed_revenue_vnd"]==5000
    accepted(api.post(sandbox+"/commands",headers=owner["headers"],json=payload("refund",11,amount_vnd=1000,reason="Partial refund.")))
    assert measure()["confirmed_revenue_vnd"]==4000
    record(operator,routing,payload("cancel",12,reason="Synthetic cancellation."))
    final=measure()
    assert final["current_states"]=={"cancelled":1} and final["confirmed_revenue_vnd"]==0
    assert final["orders"]==final["quotes_issued"]==final["sales_accepted"]==final["qualified_rfqs"]==1
    second=additional_inquiry()["entity_id"]
    record(operator,routing,payload("refer",1,assignee_id=sales["id"]) | {"rfq_id":second})
    record(sales,role,payload("reject",2,reason="Buyer declined to increase the quantity.") | {"rfq_id":second})
    after_rejection=measure()
    assert after_rejection["inquiries"]==after_rejection["valid_submissions"]==2
    assert after_rejection["current_states"]=={"cancelled":1,"rejected":1}
    assert after_rejection["qualified_rfqs"]==after_rejection["quotes_issued"]==after_rejection["orders"]==1
    third=additional_inquiry()
    third_id=third["entity_id"]
    def third_action(step, revision, **fields):
        return payload(step,revision,rfq_id=third_id,**fields)
    record(operator,routing,third_action("refer",1,assignee_id=sales["id"]))
    qualified=record(sales,role,third_action("consultation",2,quantity="5",note="Buyer confirmed MOQ."))
    assert qualified["value"]["state"]=="awaiting_assignment"
    request=third_action("cancel",3,reason="Buyer changed the requirement and withdrew this request.")
    assert api.post(sandbox+"/commands",headers=owner["headers"],json=request).status_code==409
    for actor, profile in ((sales,role),(buyer,routing),(other,routing)):
        assert decision(actor,profile,request).status_code in (403,404)
    assert decision(operator,routing,request | {"reason":None}).status_code==409
    withdrawn=record(operator,routing,request)
    assert accepted(decision(operator,routing,request))==withdrawn
    assert decision(operator,routing,request | {"reason":"Changed testimony."}).status_code==409
    assert withdrawn["value"]["feedback"][-1]=={"step":"cancel","actor":operator["id"],"text":request["reason"]}
    assert withdrawn["value"]["state"]=="cancelled" and withdrawn["value"]["revision"]==4
    assert withdrawn["value"]["intake"]==third["value"]["intake"]
    for rev in (3,4):
        assert decision(operator,routing,third_action("assign",rev,assignee_id=sales["id"])).status_code==409
    after_withdrawal=measure()
    assert after_withdrawal["current_states"]=={"cancelled":2,"rejected":1}
    assert after_withdrawal["qualified_rfqs"]==2 and after_withdrawal["inquiries"]==3
    for metric in ("quotes_issued","sales_accepted","orders","confirmed_revenue_vnd"):
        assert after_withdrawal[metric]==after_rejection[metric]
    journal=accepted(api.get(sandbox,headers=owner["headers"]))["receipts"]
    assert {r["receipt"] for r in records} <= {r["id"] for r in journal}
    if out:=os.getenv("AMC_CONSULTATION_EVIDENCE"):
        directory=Path(out)
        directory.mkdir(parents=True,exist_ok=True)
        result={"synthetic":True,"plan_id":plan,"case_id":ident,"form_receipt":original["id"],"events":records,
                "qualified":metrics,"after_confirmation":settled,"after_cancellation":final,"after_rejection":after_rejection,"after_withdrawal":after_withdrawal,"withdrawal_receipt":withdrawn["id"]}
        (directory/("postgres.json" if pg else "sqlite.json")).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
