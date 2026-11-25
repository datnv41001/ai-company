"""AMC bootstrap API: real persistence + tenant authorization, NOT production GA."""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from .identity_quota import admit
from .business_knowledge import router as knowledge_router
from .claim_desk import router as claim_desk_router
from .business_workspace import router as workspace_router
from .marketing_catalog import router as catalog_router
from .company_objectives import router as objective_router
from .identity import MailboxConfigurationError, issue, router as identity_router, verify_email
from .revision_qa import content_digest, evaluate
from .workforce_evidence import RULESET
from .delivery import router as delivery_router, working_copy
from .operations import router as operations_router
from .registry import router as registry_router
from .workforce import router as workforce_router
from .recipients import router as recipients_router, lock_recipient, revoke_pending, preview_link, accept_link
from .delivery_models import PortalGrant
from .access import set_context, visible
from .database import APP_ENV, engine, get_db, prepare_database
from .models import IdentityChallenge, User, Tenant, Membership, Client, Brand, Campaign, WorkTask, Deliverable, ActionRequest, AuditEvent, new_id
from .schemas import RegisterIn, LoginIn, ClientIn, BrandIn, CampaignIn, AddMemberIn, DeliverableIn, DeliverableReviewIn, ReviewIn, ActionIn, ClientScopeIn
from .security import DUMMY_HASH, sign_actor, hash_password, check_password, make_token, current_user, require_tenant
from .device_api import login_cookies, reauthenticate, router as devices_router
from .session_state import issue as issue_device
from .services.marketing import WORKFLOW_STEPS

ROOT = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if APP_ENV == "production":
        # Migration tool and security audit are required before enabling production.
        raise RuntimeError("Production bootstrap disabled: run migrations, RLS audits and deployment hardening first.")
    prepare_database(engine)
    yield


app = FastAPI(title="AI Marketing Company - Engineering Bootstrap", version="0.1.0", lifespan=lifespan)
app.include_router(identity_router)
app.include_router(devices_router)
app.include_router(delivery_router)
app.include_router(recipients_router)
app.include_router(workforce_router)
app.include_router(registry_router)
app.include_router(operations_router)
app.include_router(knowledge_router)
app.include_router(claim_desk_router)
app.include_router(workspace_router)
app.include_router(catalog_router)
app.include_router(objective_router)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


def data(record: Any) -> dict:
    return {p.key: getattr(record, p.key) for p in inspect(record).mapper.column_attrs}


def audit(db: Session, tenant_id: str, user_id: str, event: str, subject_id: str, details: dict | None = None) -> None:
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user_id, event=event, subject_id=subject_id, details=details or {}))


def member(db: Session, user: User, tenant_id: str, role: str = "viewer") -> Membership:
    return require_tenant(db, user, tenant_id, role)


def target(db: Session, typ: type, tenant_id: str, object_id: str):
    item = db.get(typ, object_id)
    if item is None or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


def campaign_of(db: Session, tenant_id: str, campaign_id: str) -> Campaign:
    return target(db, Campaign, tenant_id, campaign_id)


def visible_campaign(db: Session, membership: Membership, campaign_id: str):
    record = db.scalar(visible(Campaign, membership).where(Campaign.id == campaign_id))
    if record is None:
        raise HTTPException(404, "Resource not found")
    return record


def done(db: Session, item):
    db.commit()
    db.refresh(item)
    return data(item)


def workspaces(db: Session, user: User):
    rows = db.execute(select(Membership, Tenant.name, Tenant.mode)
                      .join(Tenant, Tenant.id == Membership.tenant_id)
                      .where(Membership.user_id == user.id)
                      .order_by(Tenant.name, Tenant.id))
    return [{**data(m), "organization_name": name, "mode": mode} for m, name, mode in rows]


@app.get("/")
def homepage():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "stage": "engineering_bootstrap", "environment": APP_ENV, "production_ready": False}


@app.post("/api/auth/register", status_code=202)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    admit(db, request, "register", address=email)
    password_hash = hash_password(payload.password)
    acknowledgement = {"status": "accepted"}
    set_context(db, email=email)
    if db.scalar(select(User).where(User.email == email)):
        return acknowledgement
    user = User(id=new_id(), email=email, password_hash=password_hash)
    tenant_id = new_id() if payload.organization_name else None
    set_context(db, actor=user.id, tenant=tenant_id or "")
    sign_actor(db, user.id)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        set_context(db, email=email)
        if db.scalar(select(User.id).where(User.email == email)):
            return acknowledgement
        raise
    reservation = {"workspace_id": tenant_id, "organization_name": payload.organization_name, "mode": payload.mode} if tenant_id else {}
    try:
        issue(db, user, **reservation)
    except (OSError, MailboxConfigurationError):
        db.rollback()
        logging.getLogger("amc.identity_limits").error("identity_delivery_unavailable action=register")
        return acknowledgement
    db.commit()
    return acknowledgement


@app.post("/api/auth/login")
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = str(payload.email).lower().strip()
    admit(db, request, "login", address=email)
    set_context(db, email=email)
    user = db.scalar(select(User).where(User.email == email))
    password_ok = check_password(payload.password, user.password_hash if user else DUMMY_HASH)
    if not password_ok or user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    set_context(db, actor=user.id)
    sign_actor(db, user.id)
    device, secret, csrf = issue_device(db,user,user.password_hash,request.headers.get("user-agent",""))
    pending = db.get(IdentityChallenge, user.id) if user.verified_at is None else None
    result = {
        "access_token": make_token(device),
        "token_type": "bearer",
        "user_id": user.id,
        "pending_workspace_id": pending.workspace_id if pending else None,
        "email_verified": user.verified_at is not None,
        "tenants": workspaces(db, user),
    }
    result["browser_context"] = login_cookies(request,response,device,secret,csrf)
    db.commit()
    return result


@app.get("/api/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"id": user.id, "email": user.email, "email_verified": user.verified_at is not None, "tenants": workspaces(db, user)}


@app.post("/api/tenants/{tenant_id}/members", status_code=201)
def add_member(tenant_id: str, body: AddMemberIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "admin")
    raise HTTPException(410, "Create a workspace invitation and have the recipient accept it")


@app.put("/api/tenants/{tenant_id}/members/{member_id}/client-scope")
def change_client_scope(tenant_id: str, member_id: str, body: ClientScopeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "admin")
    target(db, Client, tenant_id, body.client_id)
    record = db.get(Membership, (tenant_id, member_id), with_for_update=True)
    if record is None or record.role not in ("viewer", "client_viewer"):
        raise HTTPException(404, "Eligible membership not found")
    old_scope = record.client_id
    if record.role == "client_viewer" and old_scope == body.client_id:
        return data(record)
    grant = db.get(PortalGrant, (tenant_id, member_id))
    if grant:
        db.delete(grant)
        db.flush()
    record.role, record.client_id = "client_viewer", body.client_id
    db.flush()
    if db.get_bind().dialect.name != "postgresql":
        db.add(PortalGrant(tenant_id=tenant_id,user_id=member_id,client_id=body.client_id))
    audit(db, tenant_id, user.id, "member.client_scope_changed", member_id,
          {"previous_client_id": old_scope, "client_id": body.client_id})
    return done(db, record)


@app.delete("/api/tenants/{tenant_id}/members/{member_id}/client-scope", status_code=204)
def revoke_client_scope(tenant_id: str, member_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "admin")
    if db.get_bind().dialect.name == "postgresql":
        removed = db.scalar(text("SELECT amc_acl.revoke_client_member(:t,:u)"), {"t":tenant_id,"u":member_id})
        if not removed:
            raise HTTPException(404, "Client membership not found")
    else:
        lock_recipient(db, tenant_id, member_id)
        record = db.get(Membership, (tenant_id, member_id), populate_existing=True)
        if record is None or record.role != "client_viewer":
            raise HTTPException(404, "Client membership not found")
        audit(db, tenant_id, user.id, "member.client_scope_revoked", member_id, {"client_id": record.client_id})
        revoke_pending(db, tenant_id, member_id, db.get(User, member_id).email)
        db.delete(record)
    db.commit()


@app.get("/api/tenants/{tenant_id}/clients")
def list_clients(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    return [data(i) for i in db.scalars(visible(Client, membership))]


@app.post("/api/tenants/{tenant_id}/clients", status_code=201)
def create_client(tenant_id: str, body: ClientIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    item = Client(tenant_id=tenant_id, **body.model_dump())
    db.add(item)
    db.flush()
    audit(db, tenant_id, user.id, "client.created", item.id)
    return done(db, item)


@app.get("/api/tenants/{tenant_id}/brands")
def list_brands(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    return [data(i) for i in db.scalars(visible(Brand, membership))]


@app.post("/api/tenants/{tenant_id}/brands", status_code=201)
def create_brand(tenant_id: str, body: BrandIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    target(db, Client, tenant_id, body.client_id)
    item = Brand(tenant_id=tenant_id, **body.model_dump())
    db.add(item)
    db.flush()
    audit(db, tenant_id, user.id, "brand.created", item.id)
    return done(db, item)


@app.get("/api/tenants/{tenant_id}/campaigns")
def list_campaigns(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    return [data(i) for i in db.scalars(visible(Campaign, membership))]


@app.post("/api/tenants/{tenant_id}/campaigns", status_code=201)
def create_campaign(tenant_id: str, body: CampaignIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    target(db, Brand, tenant_id, body.brand_id)
    item = Campaign(tenant_id=tenant_id, **body.model_dump())
    db.add(item)
    db.flush()
    audit(db, tenant_id, user.id, "campaign.created", item.id)
    return done(db, item)


@app.get("/api/tenants/{tenant_id}/campaigns/{campaign_id}")
def get_campaign(tenant_id: str, campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    return data(visible_campaign(db, membership, campaign_id))


@app.post("/api/tenants/{tenant_id}/campaigns/{campaign_id}/plan")
def build_campaign_plan(tenant_id: str, campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    campaign = campaign_of(db, tenant_id, campaign_id)
    existing = {i.workflow_key: i for i in db.scalars(select(WorkTask).where(WorkTask.tenant_id == tenant_id, WorkTask.campaign_id == campaign_id)).all()}
    created = []
    for key, title, role, output in WORKFLOW_STEPS:
        if key not in existing:
            item = WorkTask(tenant_id=tenant_id, campaign_id=campaign_id, workflow_key=key, title=title, role_slug=role, expected_output=output)
            db.add(item)
            created.append(item)
    campaign.status = "planned"
    db.flush()
    audit(db, tenant_id, user.id, "campaign.plan_scaffolded", campaign_id, {"new_tasks": len(created), "llm_called": False})
    db.commit()
    tasks = db.scalars(select(WorkTask).where(WorkTask.tenant_id == tenant_id, WorkTask.campaign_id == campaign_id)).all()
    return {"campaign_id": campaign_id, "llm_called": False, "created_count": len(created), "tasks": [data(i) for i in tasks]}


@app.get("/api/tenants/{tenant_id}/campaigns/{campaign_id}/tasks")
def list_tasks(tenant_id: str, campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    visible_campaign(db, membership, campaign_id)
    return [data(i) for i in db.scalars(select(WorkTask).where(WorkTask.tenant_id == tenant_id, WorkTask.campaign_id == campaign_id)).all()]


@app.get("/api/tenants/{tenant_id}/deliverables")
def list_deliverables(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    return [data(i) for i in db.scalars(visible(Deliverable, membership))]


@app.get("/api/tenants/{tenant_id}/deliverables/{deliverable_id}")
def get_working_deliverable(tenant_id: str, deliverable_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    item = db.scalar(visible(Deliverable, membership).where(Deliverable.id == deliverable_id))
    if item is None:
        raise HTTPException(404, "Resource not found")
    return data(item)


@app.post("/api/tenants/{tenant_id}/deliverables", status_code=201)
def create_deliverable(tenant_id: str, body: DeliverableIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    campaign_of(db, tenant_id, body.campaign_id)
    reserved = {'qa_claims', 'qa_evidence', 'workforce_run_id', 'source_ids', 'qa_approved_digest', 'qa_revision', 'qa_approved_revision'}
    content = {key: value for key, value in body.content.items() if key not in reserved}
    item = Deliverable(tenant_id=tenant_id, campaign_id=body.campaign_id, title=body.title, content=content, created_by=user.id)
    db.add(item)
    db.flush()
    evaluate(db, item, user.id)
    audit(db, tenant_id, user.id, "deliverable.created", item.id)
    return done(db, item)


@app.post("/api/tenants/{tenant_id}/deliverables/{deliverable_id}/submit")
def submit_deliverable(tenant_id: str, deliverable_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    item = working_copy(db, tenant_id, deliverable_id)
    if item.status != "draft":
        raise HTTPException(409, "Only draft deliverables may be submitted")
    if (item.qa_evidence or {}).get("qa_revision") != item.qa_revision:
        evaluate(db, item, user.id)
    item.status = "submitted"
    audit(db, tenant_id, user.id, "deliverable.submitted", item.id)
    return done(db, item)


@app.post("/api/tenants/{tenant_id}/deliverables/{deliverable_id}/assessment")
def assess_working_copy(tenant_id: str, deliverable_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    item = working_copy(db, tenant_id, deliverable_id)
    previous = item.qa_evidence or {}
    report = evaluate(db, item, user.id)
    if any(previous.get(k) != report[k] for k in ("qa_revision", "content_digest", "ruleset_version", "state", "findings")):
        item.qa_approved_revision = None
        item.qa_approved_digest = None
    return done(db, item)


@app.post("/api/tenants/{tenant_id}/deliverables/{deliverable_id}/review")
def review_deliverable(tenant_id: str, deliverable_id: str, body: DeliverableReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "admin")
    item = working_copy(db, tenant_id, deliverable_id)
    report = item.qa_evidence or {}
    digest = content_digest(item.title, item.content.get("client_preview", ""))
    if (
        body.expected_qa_revision != item.qa_revision
        or report.get("qa_revision") != item.qa_revision
        or digest != body.expected_content_digest
        or report.get("content_digest") != digest
        or report.get("ruleset_version") != RULESET
        or report.get("state") not in {"current", "source_unavailable"}
    ):
        raise HTTPException(412, "Content changed or assessment is stale. Reload and reassess before deciding.")
    legacy_approval = item.status == "approved" and item.qa_approved_revision is None
    if item.status != "submitted" and not legacy_approval:
        raise HTTPException(409, "Deliverable is not awaiting review")
    if user.id in (item.created_by, item.last_editor_id):
        raise HTTPException(403, "Self-approval is forbidden")
    item.status, item.reviewed_by, item.review_note = body.decision, user.id, body.note
    item.qa_approved_revision = item.qa_revision if body.decision == "approved" else None
    item.qa_approved_digest = digest if body.decision == "approved" else None
    audit(
        db,
        tenant_id,
        user.id,
        "deliverable.reviewed",
        item.id,
        {"decision": body.decision, "qa_revision": item.qa_revision, "content_digest": digest, "ruleset_version": report["ruleset_version"]},
    )
    return done(db, item)


@app.post("/api/tenants/{tenant_id}/campaigns/{campaign_id}/strategy", deprecated=True)
def ai_strategy(tenant_id: str, campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    campaign_of(db, tenant_id, campaign_id)
    raise HTTPException(410, "Use the budgeted Workforce brief and run workflow.")



@app.get("/api/tenants/{tenant_id}/actions")
def list_actions(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    membership = member(db, user, tenant_id)
    return [data(i) for i in db.scalars(visible(ActionRequest, membership))]


@app.post("/api/tenants/{tenant_id}/actions", status_code=201)
def propose_action(tenant_id: str, body: ActionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "editor")
    campaign_of(db, tenant_id, body.campaign_id)
    item = ActionRequest(tenant_id=tenant_id, campaign_id=body.campaign_id, action_kind=body.action_kind, payload=body.payload, proposed_by=user.id)
    db.add(item)
    db.flush()
    audit(db, tenant_id, user.id, "external_action.proposed", item.id, {"kind": body.action_kind})
    return done(db, item)


@app.post("/api/tenants/{tenant_id}/actions/{action_id}/review")
def review_action(tenant_id: str, action_id: str, body: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "admin")
    item = target(db, ActionRequest, tenant_id, action_id)
    if item.state != "proposed":
        raise HTTPException(409, "Action request already resolved")
    if item.proposed_by == user.id:
        raise HTTPException(403, "Self-approval is forbidden")
    item.state, item.reviewed_by, item.review_note = body.decision, user.id, body.note
    audit(db, tenant_id, user.id, "external_action.reviewed", item.id, {"decision": body.decision})
    return done(db, item)


@app.post("/api/tenants/{tenant_id}/actions/{action_id}/execute", status_code=501)
def execute_action_disabled(tenant_id: str, action_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "admin")
    target(db, ActionRequest, tenant_id, action_id)
    raise HTTPException(501, "External side effects are disabled until official connectors, policy engine, idempotency and receipt checks pass")


@app.get("/api/tenants/{tenant_id}/audit")
def audit_events(tenant_id: str, subject_id: str | None = None, offset: int = Query(0, ge=0),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    member(db, user, tenant_id, "admin")
    query = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if subject_id:
        query = query.where(AuditEvent.subject_id == subject_id)
    return [data(i) for i in db.scalars(query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc()).offset(offset).limit(100))]


@app.get("/api/catalog/roles")
def role_catalog(user: User = Depends(current_user)):
    _ = user
    return json.loads((ROOT.parent / "catalog" / "agent_roles.json").read_text(encoding="utf-8"))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.scope.get("endpoint") not in (register, login, verify_email, preview_link, accept_link, reauthenticate):
        return await request_validation_exception_handler(request, exc)
    # Validation inputs can contain a password or the entire submitted body.
    errors = [
        {"loc": ["body"], "type": error["type"], "msg": "Invalid authentication input"}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})
