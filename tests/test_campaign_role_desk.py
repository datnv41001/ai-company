"""Signed, campaign-specific handoffs on SQLite and restricted PostgreSQL, using independently invited viewers."""
from datetime import datetime,timedelta,timezone
import os
from uuid import uuid4

from knowledge_fixtures import accepted
from test_campaign_appointments import service_campaign
from test_claim_desk import reader
from campaign_capability_fixtures import write_evidence


def change_fixture_membership(api,tenant,user,role):
    """The test membership owner changes synthetic staff authority in a separate transaction."""
    if hasattr(api,"app"):
        from sqlalchemy import text
        from app.database import get_db
        session=api.app.dependency_overrides[get_db]()
        try:
            db=next(session)
            db.execute(text("UPDATE memberships SET role=:role WHERE tenant_id=:tid AND user_id=:uid"),
                       {"role":role,"tid":tenant,"uid":user})
            db.commit()
        finally:
            session.close()
    else:
        import psycopg
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
            assert db.info.host in {"localhost","127.0.0.1","::1"} and db.info.dbname.startswith("amc_test")
            db.execute("UPDATE memberships SET role=%s WHERE tenant_id=%s AND user_id=%s",(role,tenant,user))


def test_scoped_role_cannot_read_another_customers_business_case(api,agency):
    owner,root,plan,other,other_root=service_campaign(api,agency,secondary=True)
    desk=root+"/business-desk"
    operator,service,replacement,sales,reviewer,business=[reader(api,owner,"viewer") for _ in range(6)]
    def get(role,actor,base=desk):
        return api.get(base+"/"+role+"/inbox",headers=actor["headers"])
    def grant(actor,role,enabled=True,rev=0,by=owner):
        return api.post(desk+"/grants",headers=by["headers"],json={"key":uuid4().hex,"subject":actor["id"],"role":role,
                                                                "enabled":enabled,"expected_revision":rev})
    def act(actor,role,kind,**fields):
        key=fields.pop("key",uuid4().hex)
        return api.post(desk+"/"+role+"/decisions",headers=actor["headers"],json={"kind":kind,"request_id":key,"plan_id":plan["id"],**fields})
    for actor,role in [(operator,"marketing_operator"),(service,"service_assignee"),(replacement,"service_assignee"),
                       (sales,"sales_recipient"),(reviewer,"reviewer"),(business,"business_owner")]:
        assert get(role,actor).status_code==404
        accepted(grant(actor,role))
        assert accepted(get(role,actor))["items"]==[]
        assert get(role,actor,other_root+"/business-desk").status_code==404
        assert api.get(root+"/sandbox",headers=actor["headers"]).status_code==404
    assert grant(other,"marketing_operator").status_code==404
    assert grant(reviewer,"business_owner",by=business).status_code==404
    assert get("business_owner",other).status_code==404
    assert get("marketing_operator",operator,desk.replace(owner["tenant"],operator["tenant"])).status_code==404
    then=datetime.now(timezone.utc)-timedelta(days=1)
    def when(hour):
        return (then+timedelta(hours=hour)).isoformat()
    def admin(kind,**payload):
        return api.post(root+"/sandbox/commands",headers=owner["headers"],
            json={"kind":kind,"request_id":uuid4().hex,"plan_id":plan["id"],**payload})
    apt={"contract":"service-appointment/1","appointment_id":"service-01","product_id":plan["product_id"],"unit":"machine",
         "quantity":"1","service_scope":"Inspect a synthetic pump","location":"Synthetic only","requested_for":when(3),
         "contact_purpose":"appointment_request","occurred_at":when(0)}
    accepted(admin("appointment",**apt))
    accepted(admin("rfq",rfq_id="sales-01",product_id=plan["product_id"],unit="machine",quantity="2",location="Synthetic sales site",
                   required_date=then.date().isoformat(),contact_purpose="quote_request",occurred_at=when(0)))
    def apt_command(actor,role,step,rev,t,**values):
        return act(actor,role,"appointment_decision",appointment_id="service-01",step=step,expected_revision=rev,occurred_at=when(t),**values)
    def deal(actor,role,step,rev,**values):
        return act(actor,role,"sales",rfq_id="sales-01",step=step,expected_revision=rev,occurred_at=when(rev),**values)
    assert len(accepted(get("business_owner",business))["items"])==2
    assert set(accepted(get("reviewer",reviewer))["items"][0]["value"])=={"id","plan_id","revision","state"}
    assert accepted(get("sales_recipient",sales))["items"]==[]
    assert apt_command(reviewer,"reviewer","confirm",1,1,confirmed_for=when(3)).status_code==404
    accepted(apt_command(operator,"marketing_operator","confirm",1,1,confirmed_for=when(3)))
    assert apt_command(operator,"marketing_operator","assign",2,2,assignee_id=other["id"]).status_code==409
    accepted(apt_command(operator,"marketing_operator","assign",2,2,assignee_id=service["id"]))
    assert len(accepted(get("service_assignee",service))["items"])==1
    assert apt_command(replacement,"service_assignee","complete",3,4,feedback="wrong person").status_code==404
    accepted(apt_command(business,"business_owner","reschedule",3,2,confirmed_for=when(4),feedback="Customer requested another slot"))
    accepted(apt_command(operator,"marketing_operator","reassign",4,3,assignee_id=replacement["id"],feedback="Shift handover"))
    assert accepted(get("service_assignee",service))["items"]==[]
    assert apt_command(service,"service_assignee","complete",5,5,feedback="No longer assigned").status_code==404
    assert apt_command(replacement,"service_assignee","complete",4,5,feedback="From a stale inbox").status_code==409
    done=accepted(apt_command(replacement,"service_assignee","complete",5,5,feedback="Inspection performed",key="lost-ack"))
    assert done==accepted(apt_command(replacement,"service_assignee","complete",5,5,feedback="Inspection performed",key="lost-ack"))
    assert done["actor"]==replacement["id"] and done["value"]["state"]=="completed"
    accepted(deal(operator,"marketing_operator","assign",1,assignee_id=sales["id"]))
    assert len(accepted(get("sales_recipient",sales))["items"])==1
    assert deal(operator,"marketing_operator","accept",2,reason="Not a Sales recipient").status_code==404
    accepted(deal(sales,"sales_recipient","accept",2,reason="Quantity and buyer response permission are usable"))
    note=accepted(act(reviewer,"reviewer","review_feedback",entity="leads",entity_id="sales-01",expected_revision=3,note="Sales received usable quantities"))
    assert note["reviewed_revision"]==3 and note["actor"]==reviewer["id"]
    assert note in accepted(get("business_owner",business))["feedback"]
    assert note not in accepted(get("service_assignee",replacement))["feedback"]
    accepted(grant(replacement,"service_assignee",False,1))
    assert get("service_assignee",replacement).status_code==404
    assert apt_command(replacement,"service_assignee","complete",5,5,feedback="Inspection performed",key="lost-ack").status_code==404
    report=accepted(api.get(root+"/sandbox",headers=owner["headers"]))["report"]
    assert report["appointments"]["completed"]==1 and report["sales_accepted"]==1 and report["confirmed_revenue_vnd"]==0
    assert report["secondary_rfq_funnel"]["plan_id"]==plan["id"]
    assert report["secondary_rfq_funnel"]["sales_accepted"]==1
    change_fixture_membership(api,owner["tenant"],sales["id"],"editor")
    change_fixture_membership(api,owner["tenant"],sales["id"],"viewer")
    assert get("sales_recipient",sales).status_code==404
    expired=next(g for g in accepted(api.get(desk+"/grants",headers=owner["headers"])) if g["subject"]==sales["id"])
    assert expired["enabled"] is True and expired["effective"] is False
    accepted(grant(sales,"sales_recipient",True,1))
    assert len(accepted(get("sales_recipient",sales))["items"])==1
    if not hasattr(api,"app"):
        write_evidence("business-role-decisions.json",{"synthetic":True,"plan":plan["digest"],"service_receipt":done["id"],
            "service_revision":done["value"]["revision"],"service_role":done["desk_role"],"review_receipt":note["id"],
            "reviewed_lead_revision":note["reviewed_revision"],"distinct_assignee":done["actor"]!=owner["id"],
            "confirmed_revenue_vnd":report["confirmed_revenue_vnd"],"business_acceptance":"unmeasured"})
