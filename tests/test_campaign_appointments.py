"""Two independent agency customers exercise a real service appointment and bounded cost reporting."""
from datetime import datetime,timedelta,timezone
import hashlib
import hmac
from uuid import uuid4

from app import c3_assets
from app.knowledge_store import canonical
from campaign_capability_fixtures import write_evidence
from campaign_planner_fixtures import CASES,prepare_inputs
from knowledge_fixtures import accepted
from test_claim_desk import reader


def service_campaign(api,agency):
    owner,base,((customer,scope),(other,other_scope))=agency
    cid=next(iter(scope["campaigns"]))
    brand=next(c["brand_id"] for c in accepted(api.get(base+"/campaigns",headers=owner["headers"])) if c["id"]==cid)
    [snap],_=prepare_inputs(api,owner,customer,next(iter(scope["clients"])),brand,cid,CASES[1],workflows=(c3_assets.LANDING,))
    root=base+"/campaigns/"+cid
    plan=accepted(api.post(root+"/engine/plans",headers=owner["headers"],json={"key":uuid4().hex,"expected_revision":0,
        "manifest_ids":[snap["id"]],"duration_days":14,"budget_vnd":50000}))
    accepted(api.post(root+"/engine/plans/"+plan["id"]+"/approve",headers=owner["headers"],json={"key":uuid4().hex,"expected_digest":plan["digest"]}))
    return owner,root,plan,other,base+"/campaigns/"+next(iter(other_scope["campaigns"]))


def test_service_results_do_not_count_as_quotes_or_revenue(api,agency,monkeypatch):
    owner,root,plan,other,other_root=service_campaign(api,agency)
    staff=reader(api,owner,"admin")
    def send(kind,*,status=200,key=None,actor=owner,route=root,**values):
        res=api.post(route+"/sandbox/commands",headers=actor["headers"],json={"plan_id":plan["id"],"request_id":key or uuid4().hex,"kind":kind,**values})
        assert res.status_code==status,(kind,res.text[:600])
        return res.json()
    def state():
        return accepted(api.get(root+"/sandbox",headers=owner["headers"]))
    then=datetime.now(timezone.utc)-timedelta(days=1)
    def t(hour):
        return (then+timedelta(hours=hour)).isoformat()
    req={"contract":"service-appointment/1","appointment_id":"pump-001","product_id":plan["product_id"],"unit":"machine",
         "quantity":"2","location":"Synthetic inspection site","service_scope":"Kiểm tra tiếng ồn của hai máy bơm",
         "requested_for":t(3),"contact_purpose":"appointment_request","occurred_at":t(0)}
    send("appointment",actor=other,status=404,**req)
    send("appointment",route=other_root,status=409,**req)
    send("appointment",status=409,**(req|{"unit":"piece"}))
    send("appointment",status=422,**(req|{"contact_purpose":"quote_request"}))
    first=send("appointment",key="appointment-ack",**req)
    assert send("appointment",key="appointment-ack",**req)==first
    def decide(ident,step,rev,hour,**values):
        return send("appointment_decision",appointment_id=ident,step=step,expected_revision=rev,occurred_at=t(hour),**values)
    decide("pump-001","complete",1,1,feedback="Premature",status=409)
    decide("pump-001","confirm",1,1,confirmed_for=t(3))
    decide("pump-001","assign",2,2,assignee_id=other["id"],status=409)
    decide("pump-001","assign",2,2,assignee_id=staff["id"])
    decide("pump-001","no_show",3,2,feedback="Premature",status=409)
    decide("pump-001","complete",3,4,actor=staff,feedback="Đã kiểm tra hai máy và bàn giao phiếu kiểm tra.")
    send("appointment",**(req|{"appointment_id":"pump-002"}))
    decide("pump-002","cancel",1,1,feedback="Người yêu cầu muốn dời lịch.")
    send("appointment",**(req|{"appointment_id":"pump-003"}))
    decide("pump-003","confirm",1,1,confirmed_for=t(3))
    decide("pump-003","no_show",2,4,feedback="Không có người nhận máy tại lịch hẹn.")
    view=state()
    assert view["report"]["rfqs"]==view["report"]["confirmed_revenue_vnd"]==0
    assert view["appointment_summary"]=={"requests":3,"confirmed":2,"assigned":0,"completed":1,"cancelled":1,"no_show":1,"attributed":0,"unattributed":3}
    assert view["optimization"]["basis"]=="appointment_exceptions"
    unit=next(u for u in view["work_units"] if u["package_id"]=="calendar")
    send("labor",package_id=unit["id"],seconds=45,phase="qa",allocated_cost_vnd=20,observation="Synthetic time study")
    send("close_unit_cost",package_id=unit["id"],nonlabor_vnd=30,manual_baseline_seconds=60,basis="Operator estimate")
    def current():
        return next(u for u in state()["work_units"] if u["id"]==unit["id"])
    coverage=current()["cost_coverage"]
    assert coverage["verified_vnd"] is None and coverage["manual_baseline_seconds"]==60
    lines=[{"category":c,"allocation_id":"synthetic-"+c,"amount_vnd":i} for i,c in enumerate(("model","compute","tools","human"))]
    params={"package_id":unit["id"],"inventory_digest":coverage["digest"],"lines":lines}
    send("verify_unit_cost",status=409,signature="0"*64,**params)
    key=uuid4().hex+uuid4().hex
    monkeypatch.setenv("AMC_SANDBOX_COST_METER_KEY",key)
    def sign(u,slices):
        payload={"contract":"campaign-cost-meter/1","scope":u["scope"],"plan_id":plan["id"],"unit_id":u["id"],
                 "inventory_digest":u["cost_coverage"]["digest"],"lines":slices}
        return hmac.new(key.encode(),canonical(payload).encode(),hashlib.sha256).hexdigest()
    send("verify_unit_cost",signature=sign(current(),lines),**params)
    assert current()["cost_coverage"]["verified_vnd"]==6
    different=next(u for u in state()["work_units"] if u["package_id"]=="social")
    send("verify_unit_cost",status=409,package_id=different["id"],inventory_digest=different["cost_coverage"]["digest"],
         signature=sign(different,lines),lines=lines)
    send("labor",package_id=unit["id"],seconds=2,phase="editing",observation="Later correction")
    assert current()["cost_coverage"]["verified_vnd"] is None and state()["cost_per_business_accepted_vnd"] is None
    # Both parametrized databases run the flow. Record the PostgreSQL proof from the restricted HTTP fixture.
    if str(api.base_url).startswith("http://127.0.0.1:"):
        write_evidence("appointments.json",{"conditions":"Synthetic pump service, authenticated agency operator and assigned colleague on PostgreSQL.",
            "plan":plan["id"],"state":view["appointments"],"summary":view["appointment_summary"],"rfqs":view["report"]["rfqs"],
            "revenue_vnd":view["report"]["confirmed_revenue_vnd"],"receipt_ids":[r["id"] for r in view["receipts"] if r["kind"].startswith("appointment")],
            "cost_measurement":{"observed_baseline_seconds":60,"synthetic_signed_allocation_vnd":6,"subsequent_cost_state":"Missing fresh evidence",
                                "business_accepted_units":0,"cost_per_business_accepted_vnd":None}})
