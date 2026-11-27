"""Git-reviewed workflow releases and campaign-scoped runtime bindings."""

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db
from .models import Campaign, User
from .security import current_user, require_tenant

router = APIRouter(prefix="/api/tenants/{tenant_id}/workforce/registry")
MANIFEST = Path(__file__).resolve().parents[1] / "catalog" / "landing-seo-v1.json"


def release():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class Activation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow: str = Field(max_length=120)
    action: Literal["activate", "disable", "revoke"]
    skills: list[str] = Field(min_length=1, max_length=5)


def campaign_access(db, user, tenant, campaign, role):
    m = require_tenant(db, user, tenant, role)
    c = db.get(Campaign, campaign)
    if m.role == "client_viewer" or not c or c.tenant_id != tenant:
        raise HTTPException(404, "Campaign unavailable")


@router.get("/{campaign}")
def versions(tenant_id: str, campaign: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    campaign_access(db, user, tenant_id, campaign, "viewer")
    if db.get_bind().dialect.name != "postgresql":
        return []
    rows = db.execute(
        text("""
        select r.workflow, r.digest as manifest_digest, r.manifest,
            coalesce((select jsonb_object_agg(g.skill,g.mode) from amc_ops.registry_grants g
                where g.tenant=:t and g.campaign=:c and g.workflow=r.workflow),'{}') as grants
        from amc_ops.registry_releases r order by r.workflow
    """),
        {"t": tenant_id, "c": campaign},
    )
    return [dict(row) for row in rows.mappings()]


@router.put("/{campaign}")
def activate(tenant_id: str, campaign: str, body: Activation, db: Session = Depends(get_db), user: User = Depends(current_user)):
    campaign_access(db, user, tenant_id, campaign, "admin")
    if db.get_bind().dialect.name != "postgresql":
        raise HTTPException(409, "Registry requires PostgreSQL")
    ok = db.scalar(
        text("select amc_ops.change_registry(:t,:c,:w,:mode,cast(:skills as text[]))"),
        {"t": tenant_id, "c": campaign, "w": body.workflow, "mode": body.action, "skills": body.skills},
    )
    if not ok:
        raise HTTPException(422, "Unknown release or skill")
    db.commit()
    return {"action": body.action, "skills": body.skills}


def pin(db, brief, workflow):
    from . import storyboard_runtime
    from .registry_adapters import resolve

    binding = db.scalar(text("select amc_ops.registry_pin(:t,:c,:w)"), {"t": brief.tenant_id, "c": brief.campaign_id, "w": workflow})
    if not binding:
        raise HTTPException(409, "Required workflow skills are unavailable")
    # Old draft @2 databases retain their immutable release rows. Do not queue
    # or approve work from those rows using the revised semantic adapter.
    if workflow == storyboard_runtime.RELEASE and not all(resolve(c) for c in binding["contracts"].values()):
        raise HTTPException(409, "The draft storyboard binding requires its original runtime")
    return binding
