"""The deliberately disclosed current assignment, separate from commercial evidence and source documents."""

from typing import Annotated, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.orm import Session

from .database import get_db
from .delivery import lock_document
from .models import AuditEvent, Brand, Campaign, Tenant, User
from .security import current_user, require_tenant
from .workforce_models import WorkforceBrief

router = APIRouter(prefix="/api/tenants/{tenant_id}/workforce", tags=["Marketing tasks"])
Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240, pattern=r"^[^\x00-\x1f\x7f]+$")]
Notes = Annotated[list[Line], Field(max_length=6)]
TASK_VERSION = "amc.task-intent/1"


class TaskIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Line
    deliverable_type: Literal["marketing_strategy", "landing_page"]
    audience: Line
    product: Line
    channel: Line
    region: Line
    locale: Line
    requirements: Annotated[Notes, Field(min_length=1)]
    exclusions: Notes
    acceptance_criteria: Annotated[Notes, Field(min_length=1)]


class InternalTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: UUID
    campaign_id: UUID
    intent: TaskIntent


@router.post("/internal-tasks", status_code=201)
def open_task(tenant_id: str, body: InternalTask, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "editor")
    tenant = db.get(Tenant, tenant_id)
    campaign = db.get(Campaign, str(body.campaign_id))
    if not tenant or tenant.mode != "inhouse" or not campaign or campaign.tenant_id != tenant_id:
        raise HTTPException(404, "Internal task scope unavailable")
    brand = db.get(Brand, campaign.brand_id)
    key = str(uuid5(NAMESPACE_URL, f"amc/task/{tenant_id}/{user.id}/{body.key}"))
    lock_document(db, "workforce-brief:" + key)
    payload = {"internal_task": True, "task_intent": body.intent.model_dump(), "task_version": TASK_VERSION}
    existing = db.get(WorkforceBrief, key)
    if existing and (existing.payload != payload or existing.campaign_id != campaign.id or existing.origin != "internal"):
        raise HTTPException(409, "This task key already belongs to a different assignment")
    if not existing:
        db.add(
            WorkforceBrief(
                id=key,
                tenant_id=tenant_id,
                client_id=brand.client_id,
                brand_id=brand.id,
                campaign_id=campaign.id,
                recipient_id=user.id,
                title=body.intent.purpose[:150],
                origin="internal",
                payload=payload,
            )
        )
        db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, subject_id=key, event="workforce.internal_task_created"))
        db.commit()
    return {"id": key, "campaign_id": campaign.id, "title": body.intent.purpose[:150], "submitted": True, "origin": "internal"}
