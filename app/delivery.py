"""Client delivery API. Snapshots and their journal are append-only."""

import hashlib
import json
from datetime import timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .delivery_models import ClientReview, PortalGrant, ReviewEntry
from .models import AuditEvent, Brand, Campaign, Deliverable, Membership, User, utcnow
from .security import current_user, require_tenant

router = APIRouter(prefix="/api/tenants/{tenant_id}", tags=["Client delivery"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Edit(Input):
    title: str = Field(min_length=2, max_length=160)
    client_preview: str = Field(min_length=1, max_length=30000)


class Share(Input):
    expires_at: AwareDatetime


class Rights(Input):
    can_comment: bool
    can_decide: bool
    brand_id: str | None = None
    campaign_id: str | None = None


class Decision(Input):
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_key: str = Field(min_length=8, max_length=80)
    kind: Literal["comment", "approved", "changes_requested", "rejected", "cancelled"]
    note: str = Field(default="", max_length=2000)


def not_found():
    return HTTPException(404, "Review or resource not available")


def lock_document(db, doc_id):
    # One lock order for sharing, editing and decisions. Also used by the PG insert trigger.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:doc,3))"), {"doc": doc_id})
    elif db.get_bind().dialect.name == "sqlite":
        connection = db.connection()
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")


def working_copy(db, tenant, doc_id):
    lock_document(db, doc_id)
    doc = db.scalar(select(Deliverable).where(Deliverable.id == doc_id, Deliverable.tenant_id == tenant).with_for_update())
    if doc is None:
        raise not_found()
    return doc


def event_list(db, review):
    return db.scalars(select(ReviewEntry).where(ReviewEntry.review_id == review.id).order_by(ReviewEntry.created_at, ReviewEntry.id)).all()


def as_utc(value):
    # SQLite discards timezone info; PostgreSQL may return the server timezone.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def status(review, events):
    closed = next((e.kind for e in events if e.kind != "comment"), None)
    if closed:
        return closed
    return "expired" if as_utc(review.expires_at) <= utcnow() else "pending"


def scope_query(db, member):
    stmt = select(ClientReview).where(ClientReview.tenant_id == member.tenant_id)
    if member.role != "client_viewer":
        return stmt
    grant = db.get(PortalGrant, (member.tenant_id, member.user_id))
    if grant is None or grant.client_id != member.client_id:
        return stmt.where(False)
    stmt = stmt.where(ClientReview.client_id == member.client_id)
    if grant.brand_id:
        stmt = stmt.where(ClientReview.brand_id == grant.brand_id)
    if grant.campaign_id:
        stmt = stmt.where(ClientReview.campaign_id == grant.campaign_id)
    return stmt


def find_review(db, member, rid):
    review = db.scalar(scope_query(db, member).where(ClientReview.id == rid))
    if review is None:
        raise not_found()
    return review


def capabilities(db, member):
    if member.role == "client_viewer":
        grant = db.get(PortalGrant, (member.tenant_id, member.user_id))
        return bool(grant and grant.can_comment), bool(grant and grant.can_decide)
    return member.role in ("editor", "admin", "owner"), False


def render(db, member, review, detail=True):
    events = event_list(db, review)
    item = {k: getattr(review, k) for k in ("id", "deliverable_id", "client_id", "brand_id", "campaign_id", "version", "title", "digest")}
    item.update(status=status(review, events), expires_at=as_utc(review.expires_at))
    if detail:
        comment, decide = capabilities(db, member)
        item.update(
            preview=review.preview,
            can_comment=comment,
            can_decide=decide,
            can_cancel=member.role in ("admin", "owner"),
            history=[{"id": e.id, "actor_id": e.actor_id, "kind": e.kind, "note": e.note, "digest": e.digest, "at": as_utc(e.created_at)} for e in events],
        )
    return item


@router.get("/reviews")
def reviews(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    rows = db.scalars(scope_query(db, m).order_by(ClientReview.created_at.desc(), ClientReview.id))
    return [render(db, m, row, False) for row in rows]


@router.get("/reviews/{rid}")
def view_review(tenant_id: str, rid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    return render(db, m, find_review(db, m, rid))


@router.put("/members/{uid}/review-rights")
def rights(tenant_id: str, uid: str, body: Rights, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    member = db.get(Membership, (tenant_id, uid), with_for_update=True)
    if not member or member.role != "client_viewer":
        raise not_found()
    if body.brand_id:
        brand = db.get(Brand, body.brand_id)
        if not brand or (brand.tenant_id, brand.client_id) != (tenant_id, member.client_id):
            raise not_found()
    if body.campaign_id:
        campaign = db.get(Campaign, body.campaign_id)
        if not body.brand_id or not campaign or (campaign.tenant_id, campaign.brand_id) != (tenant_id, body.brand_id):
            raise not_found()
    grant = db.get(PortalGrant, (tenant_id, uid))
    if grant is None:
        raise not_found()
    for k, v in body.model_dump().items():
        setattr(grant, k, v)
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, subject_id=uid, event="review.rights_changed", details=body.model_dump()))
    db.commit()
    return body


@router.patch("/deliverables/{did}/draft")
def edit_draft(tenant_id: str, did: str, body: Edit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "editor")
    doc = working_copy(db, tenant_id, did)
    doc.title, doc.content = body.title, {**doc.content, "client_preview": body.client_preview}
    doc.last_editor_id, doc.status, doc.reviewed_by, doc.review_note = user.id, "draft", None, None
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, subject_id=did, event="deliverable.edited", details={}))
    db.commit()
    return {"id": did, "status": "draft"}


def append(db, review, actor, kind, note, key):
    db.add(ReviewEntry(tenant_id=review.tenant_id, review_id=review.id, digest=review.digest, actor_id=actor, kind=kind, note=note, request_key=key))
    db.flush()


@router.post("/deliverables/{did}/share", status_code=201)
def share(tenant_id: str, did: str, body: Share, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id, "admin")
    doc = working_copy(db, tenant_id, did)
    if doc.status != "approved" or not doc.reviewed_by:
        raise HTTPException(409, "Independent QA approval is required")
    preview = doc.content.get("client_preview")
    if not isinstance(preview, str) or not preview.strip() or len(preview) > 30000:
        raise HTTPException(422, "Provide a client preview and complete QA before sharing")
    if body.expires_at <= utcnow():
        raise HTTPException(422, "Deadline must be in the future")
    campaign = db.get(Campaign, doc.campaign_id)
    brand = db.get(Brand, campaign.brand_id)
    previous = db.scalar(select(ClientReview).where(ClientReview.deliverable_id == did).order_by(ClientReview.version.desc()).limit(1))
    if previous and status(previous, event_list(db, previous)) in ("pending", "expired"):
        append(db, previous, user.id, "superseded", "", str(uuid4()))
    payload = json.dumps({"title": doc.title, "preview": preview}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    review = ClientReview(
        tenant_id=tenant_id,
        client_id=brand.client_id,
        brand_id=brand.id,
        campaign_id=campaign.id,
        deliverable_id=did,
        version=previous.version + 1 if previous else 1,
        digest=hashlib.sha256(payload.encode()).hexdigest(),
        title=doc.title,
        preview=preview,
        qa_by=doc.reviewed_by,
        requested_by=user.id,
        expires_at=body.expires_at.astimezone(timezone.utc),
    )
    db.add(review)
    db.flush()  # The PostgreSQL policy checks the still-approved working copy.
    doc.status = "shared"
    db.add(
        AuditEvent(
            tenant_id=tenant_id, user_id=user.id, subject_id=review.id, event="review.shared", details={"digest": review.digest, "version": review.version}
        )
    )
    db.commit()
    return render(db, m, review)


@router.post("/reviews/{rid}/events")
def record(tenant_id: str, rid: str, body: Decision, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    review = find_review(db, m, rid)
    lock_document(db, review.deliverable_id)
    actor = user.id
    db.expire_all()
    m = db.get(Membership, (tenant_id, actor))
    if m is None:
        raise not_found()
    review = find_review(db, m, rid)
    comment, decide = capabilities(db, m)
    allowed = {"comment": comment, "cancelled": m.role in ("owner", "admin")}.get(body.kind, decide)
    if not allowed:
        raise not_found()
    if body.kind == "comment" and not body.note.strip():
        raise HTTPException(422, "Write a comment")
    if body.digest != review.digest:
        raise HTTPException(409, "Content digest does not match this version")
    events = event_list(db, review)
    replay = next((e for e in events if e.actor_id == user.id and e.request_key == body.request_key), None)
    if replay:
        if (replay.kind, replay.note) != (body.kind, body.note):
            raise HTTPException(409, "Idempotency key already used for another decision")
        return render(db, m, review)
    if status(review, events) != "pending":
        raise HTTPException(409, "Review is closed or expired")
    try:
        append(db, review, user.id, body.kind, body.note, body.request_key)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Review already closed or event conflicted") from None
    return render(db, m, review)
