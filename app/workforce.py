"""Brief intake, operator authorization for spending, and asset provenance."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .delivery import lock_document
from .delivery_models import ClientReview, PortalGrant, ReviewEntry
from .models import AuditEvent, Brand, Campaign, User
from .security import current_user, require_tenant
from .workforce_gateway import CORE, EXTRA, PROMPT_VERSION
from . import workforce_authority  # noqa: F401 - install SQLite triggers on fresh schema
from .workforce_models import WorkforceBrief, WorkforceRun

router = APIRouter(prefix="/api/tenants/{tenant_id}/workforce", tags=["Marketing workforce"])
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]
Paragraph = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1800)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenBrief(Input):
    campaign_id: str
    recipient_id: str
    title: Short


class Source(Input):
    label: Short
    excerpt: Paragraph


class BriefData(Input):
    objective: Paragraph
    audience: Paragraph
    offer: Paragraph
    sources: list[Source] = Field(min_length=1, max_length=4)


class Start(Input):
    workflow: Literal["linear", "diamond-v1"] = "linear"
    extra_skills: list[Literal["seo", "creative", "ads", "analytics"]] = Field(default_factory=list, max_length=4)
    budget_microusd: int = Field(default=0, ge=0, le=1_000_000)


def brief_query(db, member):
    q = select(WorkforceBrief).where(WorkforceBrief.tenant_id == member.tenant_id)
    if member.role == "client_viewer":
        grant = db.get(PortalGrant, (member.tenant_id, member.user_id))
        if not grant or grant.client_id != member.client_id:
            return q.where(False)
        q = q.where(WorkforceBrief.recipient_id == member.user_id, WorkforceBrief.client_id == grant.client_id)
        if grant.brand_id:
            q = q.where(WorkforceBrief.brand_id == grant.brand_id)
        if grant.campaign_id:
            q = q.where(WorkforceBrief.campaign_id == grant.campaign_id)
    return q


def public_brief(b):
    return {"id": b.id, "title": b.title, "submitted": b.payload is not None, "campaign_id": b.campaign_id}


@router.get("/briefs")
def briefs(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member = require_tenant(db, user, tenant_id)
    return [public_brief(b) for b in db.scalars(brief_query(db, member).order_by(WorkforceBrief.created_at.desc()))]


@router.post("/briefs", status_code=201)
def open_brief(tenant_id: str, body: OpenBrief, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    campaign = db.get(Campaign, body.campaign_id)
    grant = db.get(PortalGrant, (tenant_id, body.recipient_id))
    if not campaign or campaign.tenant_id != tenant_id or not grant:
        raise HTTPException(404, "Campaign or recipient unavailable")
    brand = db.get(Brand, campaign.brand_id)
    if grant.client_id != brand.client_id or grant.brand_id not in (None, brand.id) or grant.campaign_id not in (None, campaign.id):
        raise HTTPException(404, "Campaign or recipient unavailable")
    brief = WorkforceBrief(tenant_id=tenant_id, client_id=brand.client_id, brand_id=brand.id, **body.model_dump())
    db.add(brief)
    db.flush()
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, subject_id=brief.id, event="workforce.brief_requested"))
    db.commit()
    return public_brief(brief)


@router.put("/briefs/{bid}/submission")
def submit(tenant_id: str, bid: str, body: BriefData, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    if m.role != "client_viewer":
        raise HTTPException(404, "Brief unavailable")
    b = db.scalar(brief_query(db, m).where(WorkforceBrief.id == bid))
    if not b:
        raise HTTPException(404, "Brief unavailable")
    # Compare-and-set also protects SQLite submissions; identical network retries are safe.
    from sqlalchemy import update

    if b.payload is None:
        changed = db.execute(
            update(WorkforceBrief)
            .where(WorkforceBrief.id == bid, WorkforceBrief.payload.is_(None))
            .values(payload=body.model_dump())
            .execution_options(synchronize_session=False)
        )
        db.commit()
        if changed.rowcount:
            return {"submitted": True}
        db.refresh(b)
    if b.payload == body.model_dump():
        return {"submitted": True}
    raise HTTPException(409, "Brief already submitted")


@router.post("/briefs/{bid}/run")
def start(tenant_id: str, bid: str, body: Start, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id, "editor")
    lock_document(db, "workforce-brief:" + bid)
    b = db.scalar(brief_query(db, m).where(WorkforceBrief.id == bid))
    if not b:
        raise HTTPException(404, "Brief unavailable")
    plan = CORE + [s for s in EXTRA if s in body.extra_skills]
    if body.workflow == "diamond-v1":
        if body.extra_skills:
            raise HTTPException(422, "Diamond template fixes its specialist set")
        if db.get_bind().dialect.name != "postgresql":
            raise HTTPException(409, "Diamond requires the PostgreSQL worker pool")
        plan = [*CORE, "seo"]
    prior = db.scalar(select(WorkforceRun).where(WorkforceRun.brief_id == bid, WorkforceRun.tenant_id == tenant_id))
    if prior:
        if prior.knowledge.get("workflow", "linear") != body.workflow or prior.plan != plan or prior.budget_microusd != body.budget_microusd:
            raise HTTPException(409, "Brief already queued with different terms")
        return {"id": prior.id, "state": prior.state}
    if not b.payload:
        raise HTTPException(409, "Waiting for the client's brief")
    brand = db.get(Brand, b.brand_id)
    if not brand.product_truth.strip():
        raise HTTPException(422, "Brand Kit needs verified product facts")
    if max(len(brand.product_truth), len(brand.brand_guidelines)) > 4000:
        raise HTTPException(422, "Summarize each Brand Kit field to 4000 characters for this workflow")
    facts = {"brand": {"label": brand.name, "excerpt": brand.product_truth}}
    facts.update({f"S{n}": s for n, s in enumerate(b.payload["sources"], 1)})
    knowledge = {
        "title": b.title,
        "objective": b.payload["objective"],
        "audience": b.payload["audience"],
        "offer": b.payload["offer"],
        "brand_rules": brand.brand_guidelines,
        "sources": facts,
        "prompt_version": PROMPT_VERSION,
    }
    if body.workflow != "linear":
        knowledge["workflow"] = body.workflow
        knowledge["workflow_revision"] = 1
    run = WorkforceRun(
        tenant_id=tenant_id,
        client_id=b.client_id,
        brand_id=b.brand_id,
        campaign_id=b.campaign_id,
        brief_id=b.id,
        plan=plan,
        knowledge=knowledge,
        budget_microusd=body.budget_microusd,
    )
    db.add(run)
    try:
        db.flush()
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user.id,
                subject_id=run.id,
                event="workforce.queued",
                details={"skills": plan, "budget_microusd": body.budget_microusd},
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if name == "dag_requires_pool":
            raise HTTPException(409, "Enroll this agency in the worker pool first") from None
        if name == "workforce_recipient_required" or "workforce_recipient_required" in str(exc.orig):
            raise HTTPException(409, "Brief recipient access was withdrawn") from None
        raise HTTPException(409, "Brief already queued; refresh") from None
    return {"id": run.id, "state": run.state}


@router.get("/runs")
def runs(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    if m.role == "client_viewer":
        raise HTTPException(404, "Runs unavailable")
    rows = db.scalars(select(WorkforceRun).where(WorkforceRun.tenant_id == tenant_id).order_by(WorkforceRun.created_at.desc()).limit(100))
    return [
        {
            "id": r.id,
            "brief_id": r.brief_id,
            "title": r.knowledge["title"],
            "state": r.state,
            "done": len(r.checkpoints),
            "skills": r.plan,
            "workflow": r.knowledge.get("workflow", "linear"),
        }
        for r in rows
    ]


@router.get("/runs/{rid}")
def report(tenant_id: str, rid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    if m.role == "client_viewer":
        raise HTTPException(404, "Run unavailable")
    run = db.scalar(select(WorkforceRun).where(WorkforceRun.tenant_id == tenant_id, WorkforceRun.id == rid))
    if not run:
        raise HTTPException(404, "Run unavailable")
    archived = (
        db.execute(
            select(ClientReview.id, ClientReview.version, ClientReview.digest)
            .join(ReviewEntry, ReviewEntry.review_id == ClientReview.id)
            .where(ClientReview.tenant_id == tenant_id, ClientReview.deliverable_id == run.deliverable_id, ReviewEntry.kind == "approved")
            .order_by(ClientReview.version)
        )
        .mappings()
        .all()
        if run.deliverable_id
        else []
    )
    return {
        **{
            k: getattr(run, k)
            for k in ("id", "state", "plan", "journal", "last_error", "budget_microusd", "reserved_microusd", "deliverable_id", "checkpoints")
        },
        "graph": db.scalar(text("select amc_ops.dag_report(:t,:r)"), {"t": tenant_id, "r": rid}) if run.knowledge.get("workflow") == "diamond-v1" else None,
        "source_registry": run.knowledge["sources"],
        "approved_assets": archived,
    }
