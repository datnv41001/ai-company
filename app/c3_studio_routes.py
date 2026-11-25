"""Staff-only editing and explicit signoff for a versioned Marketing Studio bundle."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import c3_assets, c3_boundaries, c3_customer_assets, c3_evidence_review, c3_order_units, c3_studio
from .database import get_db
from .delivery import save_working_revision, working_copy
from .knowledge_contracts import Input
from .knowledge_models import KnowledgeCommand
from .knowledge_store import Store, canonical, conflict, digest, missing
from .models import AuditEvent, Brand, Campaign, Membership, User
from .revision_qa import content_digest
from .security import current_user, require_tenant
from .workforce_models import WorkforceBrief

router = APIRouter(prefix="/api/tenants/{tenant_id}/deliverables/{did}/studio", tags=["Marketing Studio"])
Text = Annotated[str, Field(max_length=30000)]


class StudioEdit(Input):
    expected_revision: Annotated[int, Field(ge=1, strict=True)]
    groups: dict[str, dict[str, Text]]
    delivery_version: Literal["amc.customer-marketing-assets/1"] | None = None


class StudioApproval(Input):
    expected_revision: Annotated[int, Field(ge=1, strict=True)]
    expected_asset_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    group: Annotated[str, Field(min_length=1, max_length=20)]
    note: Annotated[str, Field(min_length=10, max_length=500)]


def scoped(db, user, tenant, did, role):
    require_tenant(db, user, tenant, role)
    doc = working_copy(db, tenant, did)
    run = c3_boundaries.run_for(db, doc)
    if not run or run.state != "awaiting_qa" or run.knowledge["registry"]["workflow"] not in c3_assets.ROLES:
        missing()
    campaign = db.get(Campaign, doc.campaign_id)
    brand = db.get(Brand, campaign.brand_id) if campaign else None
    if not brand or (campaign.tenant_id, campaign.id, brand.tenant_id, brand.id, brand.client_id) != (
        tenant,
        run.campaign_id,
        tenant,
        run.brand_id,
        run.client_id,
    ):
        missing()
    return doc, run


def proposals(run):
    return c3_studio.compose(run.knowledge["registry"]["workflow"], run.knowledge["c3_projection"], {s["skill"]: s["output"] for s in run.checkpoints})


def asset_digest(doc, run, group, fields):
    contract = (doc.content.get("studio") or {}).get("delivery_version", c3_studio.VERSION)
    return digest(canonical([contract, doc.id, doc.qa_revision, run.knowledge["c3_manifest"]["digest"], group, fields]))


def signoffs(db, doc, run):
    groups = doc.content["studio"]["groups"]
    snapshot = run.knowledge["c3_manifest"]["id"]
    commands = db.scalars(
        select(KnowledgeCommand)
        .filter_by(tenant_id=run.tenant_id, client_id=run.client_id, brand_id=run.brand_id, snapshot_id=snapshot, operation="c3_studio_qa")
        .where(KnowledgeCommand.key.startswith(f"asset:{doc.id}:{doc.qa_revision}:"))
        .order_by(KnowledgeCommand.effective_at, KnowledgeCommand.id)
    )
    current = {}
    for row in commands:
        group = row.result["group"]
        if group in groups and row.result["asset_digest"] == asset_digest(doc, run, group, groups[group]):
            role = db.scalar(select(Membership.role).filter_by(tenant_id=run.tenant_id, user_id=row.actor))
            if role in ("admin", "owner") and row.actor not in (doc.created_by, doc.last_editor_id):
                current.setdefault(group, {"receipt": row.id, "actor": row.actor, "note": row.result["note"]})
    return current


def require_all_approved(db, doc, run):
    if bundle := doc.content.get("studio"):
        signed = signoffs(db, doc, run)
        if set(signed) != set(bundle["groups"]):
            conflict("Independent Marketing Studio signoff is required for every asset of this revision")
        return {group: r["receipt"] for group, r in signed.items()}


def present(db, doc, run):
    workflow = run.knowledge["registry"]["workflow"]
    bundle = doc.content.get("studio")
    groups = bundle["groups"] if bundle else proposals(run)
    projection = run.knowledge["c3_projection"]
    edition = (bundle or {}).get("delivery_version")
    controls = c3_studio.compose(workflow, projection)
    customer = c3_customer_assets.strategy(projection) if workflow == c3_assets.RESEARCH else {}
    hints = c3_studio.quality_issues(workflow, groups, projection)
    if edition:
        hints.extend(c3_customer_assets.issues(workflow, groups, projection))
    history = db.scalars(
        select(AuditEvent)
        .filter_by(tenant_id=doc.tenant_id, subject_id=doc.id, event="studio.saved")
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    )
    return {
        "version": c3_studio.VERSION,
        "workflow": workflow,
        "revision": doc.qa_revision,
        "mode": "saved" if bundle else "proposal",
        "status": doc.status,
        "groups": groups,
        "delivery_version": edition,
        "customer_edition": {
            "version": c3_customer_assets.VERSION,
            "groups": customer,
            "fields": c3_customer_assets.PUBLIC[workflow],
            "labels": c3_customer_assets.labels(projection["locale"]),
            "title": projection["product"],
        },
        "suggestions": {**controls, **customer},
        "history": [dict(revision=row.details["revision"], at=row.occurred_at, groups=row.details["groups"]) for row in history],
        "asset_digests": {g: asset_digest(doc, run, g, v) for g, v in groups.items()},
        "approvals": signoffs(db, doc, run) if bundle else {},
        "quality_issues": hints,
        "references": [
            {"handle": f["id"], "text": " ".join(c3_order_units.fact_lines(f, run.knowledge["c3_projection"]))} for f in run.knowledge["c3_projection"]["facts"]
        ],
        "findings": (doc.qa_evidence or {}).get("content_evidence", {}).get("statements", []),
        "preview": {"title": doc.title, "body": doc.content.get("client_preview", "")},
    }


@router.get("")
def view(tenant_id: str, did: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc, run = scoped(db, user, tenant_id, did, "editor")
    result = present(db, doc, run)
    store = Store(db, user, run.tenant_id, run.client_id, run.brand_id, write=False)
    if store.approver and result["mode"] == "saved":
        snapshot_id = run.knowledge["c3_manifest"]["id"]
        resolved = store.query(KnowledgeCommand).filter_by(operation="c3_resolve", snapshot_id=snapshot_id)
        if db.scalar(resolved.where(KnowledgeCommand.key.startswith(f"claim:{doc.qa_revision}:")).limit(1)):
            from .c3_projection import unpack

            snap, _ = unpack(store, snapshot_id)
            report = c3_evidence_review.current_report(store, snap, doc, run, content_digest(doc.title, result["preview"]["body"]))
            result["findings"] = report["statements"]
    return result


@router.patch("")
def save(tenant_id: str, did: str, body: StudioEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc, run = scoped(db, user, tenant_id, did, "editor")
    if body.expected_revision != doc.qa_revision:
        raise HTTPException(412, "The Marketing asset changed. Reload this revision.")
    workflow = run.knowledge["registry"]["workflow"]
    edition = body.delivery_version
    if (doc.content.get("studio") or {}).get("delivery_version") and not edition:
        conflict("Include the current customer edition when editing this revision")
    schema = {**c3_studio.FIELDS[workflow], **(c3_customer_assets.PUBLIC[workflow] if edition else {})}
    groups = body.groups
    if set(groups) != set(schema) or any(set(groups[g]) != set(schema[g]) for g in schema):
        raise HTTPException(422, "Submit all fields of the current Marketing asset contract")
    if any(len(text) > 5000 for fields in groups.values() for key, text in fields.items() if key not in ("commercial_terms", "evidence")):
        raise HTTPException(422, "Keep editorial fields within 5000 characters")
    original = {"title": doc.title, "body": doc.content.get("client_preview", "")}
    preview = c3_customer_assets.preview(workflow, groups, run.knowledge["c3_projection"]) if edition else c3_studio.preview(workflow, groups, original)
    if not preview["title"].strip() or len(preview["title"]) > 160 or len(preview["body"]) > 30000:
        raise HTTPException(422, "Provide a headline up to 160 characters and preview up to 30000 characters")
    origin = (doc.content.get("studio") or {}).get("origin", "editor")
    bundle = {"version": c3_studio.VERSION, "origin": origin, "groups": groups}
    if edition:
        bundle["delivery_version"] = edition
    doc.content = {**doc.content, "studio": bundle}
    save_working_revision(db, doc, user.id, preview["title"], preview["body"])
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            user_id=user.id,
            subject_id=did,
            event="studio.saved",
            details={"revision": doc.qa_revision, "groups": groups, "version": c3_studio.VERSION, "delivery_version": edition},
        )
    )
    db.flush()
    response = present(db, doc, run)
    db.commit()
    return response


@router.post("/approvals")
def review_asset(tenant_id: str, did: str, body: StudioApproval, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc, run = scoped(db, user, tenant_id, did, "admin")
    groups = (doc.content.get("studio") or {}).get("groups", {})
    if body.group not in groups:
        conflict("Save this Marketing asset before review")
    signature = asset_digest(doc, run, body.group, groups[body.group])
    if doc.qa_revision != body.expected_revision or signature != body.expected_asset_digest:
        raise HTTPException(412, "The reviewed asset changed")
    brief = db.get(WorkforceBrief, run.brief_id)
    if user.id in (doc.created_by, doc.last_editor_id, c3_boundaries.internal_author(brief)):
        raise HTTPException(403, "Independent review is required")
    if len(body.note.strip()) < 10:
        raise HTTPException(422, "Explain the evidence and relevance of the asset")
    if existing := signoffs(db, doc, run).get(body.group):
        if existing["actor"] == user.id and existing["note"] == body.note.strip():
            return present(db, doc, run)
        conflict("This revision already has an independent signoff for the asset")
    if doc.status != "submitted":
        conflict("Submit the current working revision before independent review")
    workflow = run.knowledge["registry"]["workflow"]
    projection = run.knowledge["c3_projection"]
    issues = c3_studio.quality_issues(workflow, groups, projection)
    if doc.content["studio"].get("delivery_version"):
        issues.extend(c3_customer_assets.issues(workflow, groups, projection))
    if any(row["group"] == body.group for row in issues):
        conflict("Correct missing, duplicated or mismatched fields before signing")
    store, snap, _ = c3_boundaries.checked(db, user, brief, run.knowledge["c3_manifest"], workflow, "qa")
    report = c3_evidence_review.current_report(store, snap, doc, run, content_digest(doc.title, doc.content.get("client_preview", "")))
    rows = [s for s in report["statements"] if s["field"].startswith(f"studio.{body.group}.")]
    if {s["field"].split(".")[-1] for s in rows} != set(groups[body.group]) or any(s["outcome"] not in ("verified", "editorial", "reviewed") for s in rows):
        conflict("Review the evidence of every field before signing this asset")
    key = f"asset:{doc.id}:{doc.qa_revision}:{body.group}"
    record = {"document_id": doc.id, "group": body.group, "revision": doc.qa_revision, "asset_digest": signature, "note": body.note.strip()}
    prior = db.scalar(store.query(KnowledgeCommand).filter_by(snapshot_id=snap.id, operation="c3_studio_qa", key=key, actor=user.id))
    if prior and record != prior.result:
        conflict("This reviewer already signed a different decision")
    if not prior:
        c3_boundaries.record(store, snap, "studio_qa", key, record)
        db.flush()
    response = present(db, doc, run)
    response["findings"] = report["statements"]
    db.commit()
    return response
