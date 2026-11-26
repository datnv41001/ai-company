"""Campaign-scoped business handoffs share the sales and appointment state machines and signed journal."""
from typing import Annotated, Literal, get_args

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from . import campaign_operations_appointments as appointments, campaign_operations_crm as crm
from .campaign_operations import OP
from .campaign_operations_contracts import AppointmentDecision, Command, Consultation, Id, Note, Positive, Sales
from .campaign_planner import campaign_store
from .database import get_db
from .knowledge_contracts import Input
from .knowledge_models import KnowledgeCommand as Record
from .knowledge_store import canonical, conflict, digest, missing, signed_document, stamp
from .models import Membership, User, new_id
from .security import current_user

router = APIRouter(prefix="/api/tenants/{tenant_id}/campaigns/{campaign_id}/business-desk", tags=["Campaign business desk"])
Role = Literal["marketing_operator","sales_recipient","service_assignee","reviewer","business_owner"]
ROUTING = {"marketing_operator","business_owner"}
GRANT = "campaign_role_grant"
FEEDBACK = "campaign_desk_feedback"


class Grant(Input):
    key: Id
    subject: Id
    role: Role
    enabled: bool
    expected_revision: Annotated[int,Field(strict=True,ge=0)]


class Feedback(Command):
    kind: Literal["review_feedback"]
    entity: Literal["leads","appointments"]
    entity_id: Id
    expected_revision: Positive
    note: Note


Decision = Annotated[Sales | Consultation | AppointmentDecision | Feedback,Field(discriminator="kind")]


def sqlite_membership_epochs(connection):
    connection.exec_driver_sql("""CREATE TABLE IF NOT EXISTS campaign_member_epochs
        (tenant_id TEXT NOT NULL,user_id TEXT NOT NULL,epoch INTEGER NOT NULL,PRIMARY KEY(tenant_id,user_id))""")
    for suffix,clause in (("removed","DELETE"),("changed","UPDATE OF role,client_id")):
        condition="WHEN OLD.role IS NOT NEW.role OR OLD.client_id IS NOT NEW.client_id" if suffix=="changed" else ""
        connection.exec_driver_sql(f"""CREATE TRIGGER IF NOT EXISTS campaign_membership_{suffix} AFTER {clause} ON memberships
            FOR EACH ROW {condition} BEGIN INSERT INTO campaign_member_epochs VALUES(OLD.tenant_id,OLD.user_id,1)
            ON CONFLICT(tenant_id,user_id) DO UPDATE SET epoch=epoch+1; END""")


def sqlite_intake_guard(connection):
    connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS campaign_rfq_intake BEFORE INSERT ON knowledge_commands
        FOR EACH ROW WHEN NEW.operation='campaign_sandbox_v2' AND json_extract(NEW.result,'$.kind')='rfq'
        AND NOT EXISTS (SELECT 1 FROM knowledge_commands p JOIN knowledge_commands a ON
          a.tenant_id=p.tenant_id AND a.client_id=p.client_id AND a.brand_id=p.brand_id AND a.operation='campaign_plan_approve'
          AND json_extract(a.result,'$.id')=json_extract(p.result,'$.id') AND json_extract(a.result,'$.digest')=json_extract(p.result,'$.digest')
          WHERE p.operation='campaign_plan' AND p.tenant_id=NEW.tenant_id AND p.client_id=NEW.client_id AND p.brand_id=NEW.brand_id
          AND json_extract(p.result,'$.id')=json_extract(NEW.result,'$.plan_id')
          AND json_extract(p.result,'$.campaign_id')=json_extract(NEW.result,'$.campaign_id')
          AND (json_extract(p.result,'$.buyer_action')='rfq' OR (json_extract(p.result,'$.buyer_action')='appointment'
                AND EXISTS (SELECT 1 FROM json_each(p.result,'$.secondary_conversions') WHERE value='rfq'))))
        BEGIN SELECT RAISE(ABORT,'campaign plan does not authorize quote intake'); END""")


@event.listens_for(Record.__table__,"after_create")
def on_journal_create(_table,connection,**_):
    if connection.dialect.name=="sqlite":
        sqlite_intake_guard(connection)
        from migrations.sandbox_contract import sqlite_business_intake
        sqlite_business_intake(connection)


@event.listens_for(Membership.__table__,"after_create")
def on_membership_create(_table,connection,**_):
    if connection.dialect.name=="sqlite":
        sqlite_membership_epochs(connection)


def member_epoch(store,cid,subject,role):
    if store.postgres:
        envelope={**store.scope,"campaign_id":cid,"role":role,"actor":store.actor,"mode":"grant_epoch","subject":subject}
        return store.db.scalar(text("SELECT amc_acl.campaign_desk(:doc,:proof)"),signed_document(store.db,store.actor,"campaign_role_desk",envelope))
    return store.db.scalar(text("SELECT epoch FROM campaign_member_epochs WHERE tenant_id=:tenant_id AND user_id=:subject"),
                           {"tenant_id":store.scope["tenant_id"],"subject":subject}) or 0


def has_campaign_role(store,cid,role):
    """Check the current actor's scoped authority; callers still enforce their own resource and write contracts."""
    if store.postgres:
        envelope={**store.scope,"campaign_id":cid,"role":role,"actor":store.actor,"mode":"eligible","subject":store.actor}
        signed=signed_document(store.db,store.actor,"campaign_role_desk",envelope)
        return store.db.scalar(text("SELECT amc_acl.campaign_desk(:doc,:proof)"),signed) is True
    current=grant_head(store,cid,store.actor,role)
    return bool(current and current["enabled"] and current["membership_epoch"]==member_epoch(store,cid,store.actor,role))


def scope_rows(store,cid):
    return select(Record).filter_by(**store.scope,visibility="restricted").where(Record.result["campaign_id"].as_string()==cid)


def grant_head(store,cid,subject,role):
    query=scope_rows(store,cid).filter_by(operation=GRANT).where(Record.result["subject"].as_string()==subject,
        Record.result["role"].as_string()==role).order_by(Record.result["revision"].as_integer().desc()).limit(1)
    row=store.db.scalar(query)
    return row.result if row else None


@router.post("/grants")
def set_grant(tenant_id:str,campaign_id:str,body:Grant,user:User=Depends(current_user),db:Session=Depends(get_db)):
    store=campaign_store(db,user,tenant_id,campaign_id,write=True)
    if not store.approver:
        missing()
    def change(at):
        member=db.get(Membership,{"tenant_id":tenant_id,"user_id":body.subject})
        if body.enabled and (not member or member.role not in {"viewer","editor","admin","owner"}):
            missing()
        prior=grant_head(store,campaign_id,body.subject,body.role)
        if body.expected_revision!=(prior["revision"] if prior else 0):
            conflict("Campaign role revision changed")
        epoch=member_epoch(store,campaign_id,body.subject,body.role) if body.enabled else None
        if body.enabled and type(epoch) is not int:
            missing()
        return {"id":new_id(),"campaign_id":campaign_id,"subject":body.subject,"role":body.role,"enabled":body.enabled,"membership_epoch":epoch,
                "revision":body.expected_revision+1,"actor":user.id,"at":stamp(at)},"restricted",None
    return store.command(GRANT,body,change,target=campaign_id)


@router.get("/access")
def access(tenant_id:str,campaign_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    store=campaign_store(db,user,tenant_id,campaign_id,write=False)
    granted=[role for role in get_args(Role) if has_campaign_role(store,campaign_id,role)]
    return {"roles":granted,"may_manage":store.approver}


@router.get("/grants")
def grants(tenant_id:str,campaign_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    store=campaign_store(db,user,tenant_id,campaign_id,write=False)
    if not store.approver:
        missing()
    rows=sorted((r.result for r in db.scalars(scope_rows(store,campaign_id).filter_by(operation=GRANT))),key=lambda v:v["revision"])
    current={(r["subject"],r["role"]):r for r in rows}
    result=[]
    for grant in current.values():
        epoch=member_epoch(store,campaign_id,grant["subject"],grant["role"]) if grant["enabled"] else None
        result.append({**grant,"effective":type(epoch) is int and epoch==grant["membership_epoch"]})
    return result


class Desk:
    def __init__(self,db,user,tid,cid,role,*,write):
        if write and db.get_bind().dialect.name=="sqlite" and not db.connection().connection.driver_connection.in_transaction:
            db.execute(text("BEGIN IMMEDIATE"))
        self.store=campaign_store(db,user,tid,cid,write=False)
        self.db,self.actor,self.cid,self.role=db,user.id,cid,role

    def procedure(self,mode,**params):
        q={**self.store.scope,"campaign_id":self.cid,"role":self.role,"actor":self.actor,"mode":mode,**params}
        signed=signed_document(self.db,self.actor,"campaign_role_desk",q)
        return self.db.scalar(text("SELECT amc_acl.campaign_desk(:doc,:proof)"),signed)

    def eligible(self,subject,role):
        if self.store.postgres:
            return self.procedure("eligible",subject=subject,role=role) is True
        member=self.db.get(Membership,{"tenant_id":self.store.scope["tenant_id"],"user_id":subject})
        entry=grant_head(self.store,self.cid,subject,role)
        return (member and member.role in {"viewer","editor","admin","owner"} and entry and entry["enabled"]
                and entry["membership_epoch"]==member_epoch(self.store,self.cid,subject,role))

    def inspect(self,key=""):
        if self.store.postgres:
            result=self.procedure("inspect",key=key)
            if result is None:
                missing()
            return result
        if not self.eligible(self.actor,self.role):
            missing()
        rows=list(self.db.scalars(scope_rows(self.store,self.cid).where(Record.operation.in_(("campaign_sandbox_v1",OP,FEEDBACK)))))
        journal=sorted((r.result for r in rows if r.operation!=FEEDBACK), key=lambda e:e["sequence"])
        current={(e["entity"],e["entity_id"]):e["value"] for e in journal if e["entity"] in {"appointments","leads"}}
        items=[]
        for (entity,_),value in sorted(current.items()):
            if self.role=="reviewer":
                value={k:value[k] for k in ("id","revision","plan_id","state")}
            elif self.role not in ROUTING and (value.get("assignee_id")!=self.actor or
                    entity!={"sales_recipient":"leads","service_assignee":"appointments"}.get(self.role)):
                continue
            items.append({"entity":entity,"value":value})
        replay=next(({"digest":r.request_digest,"result":r.result} for r in rows if r.actor==self.actor and r.key==key),None)
        allowed={(x["entity"],x["value"]["id"]) for x in items}
        notes=[r.result for r in rows if r.operation==FEEDBACK and (r.result["entity"],r.result["entity_id"]) in allowed]
        return {"items":items,"feedback":sorted(notes,key=lambda r:(r["recorded_at"],r["id"])),"replay":replay,
                "sequence":(journal[-1]["sequence"] if journal else 0)+1}

    def append(self,prior,op,receipt,key,fp):
        now=self.store.now()
        row={**self.store.scope,"id":receipt["id"],"actor":self.actor,"operation":op,"request_digest":fp,"key":key,
             "visibility":"restricted","result":receipt,"snapshot_id":None,"queued_at":None,"effective_at":now}
        if self.store.postgres:
            self.procedure("append",row={**row,"effective_at":stamp(now)},key=key,prior_revision=prior)
        else:
            self.db.execute(Record.__table__.insert().values(**row))


@router.get("/{role}/inbox")
def inbox(tenant_id:str,campaign_id:str,role:Role,user:User=Depends(current_user),db:Session=Depends(get_db)):
    desk=Desk(db,user,tenant_id,campaign_id,role,write=False)
    state=desk.inspect()
    return {"campaign_id":campaign_id,"role":role,"items":state["items"],"feedback":state["feedback"]}


def permitted(role,cmd):
    if isinstance(cmd,Feedback):
        return role in {"reviewer","business_owner"}
    if isinstance(cmd,Consultation):
        return role=="sales_recipient"
    if isinstance(cmd,Sales):
        if role in ROUTING:
            return cmd.step in {"refer","assign","reassign","cancel"}
        return role=="sales_recipient" and cmd.step in {"accept","reject","quote","order"}
    if role in ROUTING:
        return cmd.step in {"assign","confirm","cancel","reschedule","reassign"}
    return role=="service_assignee" and cmd.step in {"complete","no_show","cancel"}


@router.post("/{role}/decisions")
def decide(tenant_id:str,campaign_id:str,role:Role,body:Decision,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if not permitted(role,body):
        missing()
    desk=Desk(db,user,tenant_id,campaign_id,role,write=True)
    key="desk:"+digest(canonical([campaign_id,body.request_id]))
    fingerprint=digest(canonical([role,body.model_dump(mode="json")]))
    state=desk.inspect(key)
    if isinstance(body,Feedback):
        entity,ident=body.entity,body.entity_id
    elif isinstance(body,(Sales,Consultation)):
        entity,ident="leads",body.rfq_id
    else:
        entity,ident="appointments",body.appointment_id
    prior=next((x["value"] for x in state["items"] if x["entity"]==entity and x["value"]["id"]==ident),None)
    if not prior or prior["plan_id"]!=body.plan_id:
        missing()
    if old:=state["replay"]:
        if old["digest"]!=fingerprint:
            conflict("Request already used for another business decision")
        return old["result"]
    if prior["revision"]!=body.expected_revision:
        conflict("The business case revision changed; reload the inbox")
    event={"id":new_id(),"actor":user.id,"campaign_id":campaign_id,"plan_id":body.plan_id,"entity":entity,"entity_id":ident,
           "recorded_at":stamp(desk.store.now()),"kind":body.kind,"desk_role":role}
    if isinstance(body,Feedback):
        op=FEEDBACK
        event.update(reviewed_revision=prior["revision"],note=body.note)
    else:
        op=OP
        state_slice={entity:{ident:prior}}
        plan={"id":body.plan_id}
        if isinstance(body,(Sales,Consultation)):
            _,_,value=crm.observation(body,state_slice,plan,desk.store,recipient=desk.eligible,coordinator=role in ROUTING)
        else:
            _,_,value=appointments.appointment(body,state_slice,plan,desk.store,recipient=desk.eligible)
        event.update(sequence=state["sequence"],step=body.kind if isinstance(body,Consultation) else body.step,
                     value=value, intake_writer="business-intake/1",
                     origin="landing" if value.get("landing_source") else "manual")
    desk.append(prior["revision"],op,event,key,fingerprint)
    db.commit()
    return event
