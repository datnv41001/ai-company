"""Client delivery API. Snapshots and their journal are append-only."""

from datetime import timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import and_, select, text, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .revision_qa import content_digest, evaluate
from .workforce_evidence import RULESET
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
    expected_qa_revision: int | None = Field(default=None, ge=1, strict=True)
    expected_content_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


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


def render(db, member, review):
    events = event_list(db, review)
    item = {k: getattr(review, k) for k in ("id", "deliverable_id", "client_id", "brand_id", "campaign_id", "version", "title", "digest")}
    item.update(status=status(review, events), expires_at=as_utc(review.expires_at))
    comment, decide = capabilities(db, member)
    item.update(
        preview=review.preview,
        can_comment=comment,
        can_decide=decide,
        can_cancel=member.role in ("editor", "admin", "owner"),
        history=[{"id": e.id, "actor_id": e.actor_id, "kind": e.kind, "note": e.note, "digest": e.digest, "at": as_utc(e.created_at)} for e in events],
    )
    return item


@router.get("/reviews")
def reviews(tenant_id: str, response: Response, limit: int = Query(25, ge=1, le=100),
            cursor: str | None = Query(None, min_length=1, max_length=36),
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    member = require_tenant(db, user, tenant_id)
    scoped = scope_query(db, member)
    r, e = ClientReview, ReviewEntry
    if cursor:
        # Resolve the cursor under the current grant, including after a revocation.
        anchor = db.execute(scoped.with_only_columns(r.created_at, r.id).where(r.id == cursor)).one_or_none()
        if anchor is None:
            raise HTTPException(422, "Cursor unavailable; refresh the list")
        scoped = scoped.where(tuple_(r.created_at, r.id) < tuple_(*anchor))
    columns = (r.id, r.deliverable_id, r.client_id, r.brand_id, r.campaign_id, r.version, r.title, r.digest, r.expires_at)
    # Only one terminal entry can exist. Comments and snapshot payloads stay out of the list query.
    query = scoped.with_only_columns(*columns, e.kind).outerjoin(
        e, and_(e.review_id == r.id, e.kind != "comment")
    ).order_by(r.created_at.desc(), r.id.desc()).limit(limit + 1)
    rows = db.execute(query).mappings().all()
    if len(rows) > limit:
        response.headers["X-Next-Cursor"] = rows[limit - 1]["id"]
    result = []
    now = utcnow()
    for row in rows[:limit]:
        item = dict(row)
        item["expires_at"] = as_utc(item["expires_at"])
        item["status"] = item.pop("kind") or ("expired" if item["expires_at"] <= now else "pending")
        result.append(item)
    return result


@router.get("/reviews/{rid}")
def view_review(tenant_id: str, rid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    return render(db, m, find_review(db, m, rid))


def validate_scope(db, tenant_id, client_id, body):
    brand = campaign = None
    if body.brand_id:
        brand = db.get(Brand, body.brand_id)
        if not brand or (brand.tenant_id, brand.client_id) != (tenant_id, client_id):
            raise not_found()
    if body.campaign_id:
        campaign = db.get(Campaign, body.campaign_id)
        if not body.brand_id or not campaign or (campaign.tenant_id, campaign.brand_id) != (tenant_id, body.brand_id):
            raise not_found()
    return brand, campaign


@router.put("/members/{uid}/review-rights")
def rights(tenant_id: str, uid: str, body: Rights, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    member = db.get(Membership, (tenant_id, uid), with_for_update=True)
    if not member or member.role != "client_viewer":
        raise not_found()
    validate_scope(db, tenant_id, member.client_id, body)
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
    if doc.content.get("studio") and doc.content["studio"]["groups"].get("copy"):
        raise HTTPException(409, "Edit the buyer-facing copy in Marketing Studio to keep its version and preview together")
    save_working_revision(db, doc, user.id, body.title, body.client_preview)
    db.commit()
    return {"id": did, "status": "draft"}


def save_working_revision(db, doc, actor, title, preview):
    """Caller holds the working-copy lock and commits all revision-specific events together."""
    did = doc.id
    previous = db.scalar(select(ClientReview).where(ClientReview.deliverable_id == did).order_by(ClientReview.version.desc()).limit(1))
    if previous and status(previous, event_list(db, previous)) == "pending":
        # The document lock also guards decisions. A decision committed first stays final.
        append(db, previous, actor, "cancelled", "Agency bắt đầu sửa bản làm việc.", str(uuid4()))
    doc.title, doc.content = title, {**doc.content, "client_preview": preview}
    # The same bytes can recur after multiple edits. Only this save owns the new revision.
    doc.qa_revision += 1
    doc.qa_approved_revision = None
    doc.qa_approved_digest = None
    evaluate(db, doc, actor)
    doc.last_editor_id, doc.status, doc.reviewed_by, doc.review_note = actor, "draft", None, None
    db.add(AuditEvent(tenant_id=doc.tenant_id, user_id=actor, subject_id=did, event="deliverable.edited", details={}))


def append(db, review, actor, kind, note, key):
    db.add(ReviewEntry(tenant_id=review.tenant_id, review_id=review.id, digest=review.digest, actor_id=actor, kind=kind, note=note, request_key=key))
    db.flush()


@router.post("/deliverables/{did}/share", status_code=201)
def share(tenant_id: str, did: str, body: Share, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from . import c3_boundaries
    m = require_tenant(db, user, tenant_id, "admin")
    doc = working_copy(db, tenant_id, did)
    if run := c3_boundaries.run_for(db, doc):
        if body.expected_qa_revision is None or body.expected_content_digest is None:
            raise HTTPException(422, "The Marketing share request requires the reviewed revision and content digest")
        if body.expected_qa_revision != doc.qa_revision or body.expected_content_digest != content_digest(doc.title, doc.content.get("client_preview", "")):
            raise HTTPException(412, "The reviewed Marketing asset changed. Reload before sharing.")
        if existing := c3_boundaries.existing_share(db, user, doc, body.expires_at, run):
            return render(db, m, find_review(db, m, existing))
    if doc.status != "approved" or not doc.reviewed_by:
        raise HTTPException(409, "Independent QA approval is required")
    preview = doc.content.get("client_preview")
    if not isinstance(preview, str) or not preview.strip() or len(preview) > 30000:
        raise HTTPException(422, "Provide a client preview and complete QA before sharing")
    digest = content_digest(doc.title, preview)
    report = doc.qa_evidence or {}
    if (
        doc.qa_approved_revision != doc.qa_revision
        or report.get("qa_revision") != doc.qa_revision
        or doc.qa_approved_digest != digest
        or report.get("content_digest") != digest
        or report.get("ruleset_version") != RULESET
        or report.get("state") not in {"current", "source_unavailable"}
    ):
        raise HTTPException(409, "Independent QA must review this revision before sharing")
    if body.expires_at <= utcnow():
        raise HTTPException(422, "Deadline must be in the future")
    gate = c3_boundaries.boundary(db, user, doc, digest, "share")
    campaign = db.get(Campaign, doc.campaign_id)
    brand = db.get(Brand, campaign.brand_id)
    previous = db.scalar(select(ClientReview).where(ClientReview.deliverable_id == did).order_by(ClientReview.version.desc()).limit(1))
    if previous and status(previous, event_list(db, previous)) in ("pending", "expired"):
        append(db, previous, user.id, "superseded", "", str(uuid4()))
    review = ClientReview(
        tenant_id=tenant_id,
        client_id=brand.client_id,
        brand_id=brand.id,
        campaign_id=campaign.id,
        deliverable_id=did,
        version=previous.version + 1 if previous else 1,
        digest=digest,
        title=doc.title,
        preview=preview,
        qa_by=doc.reviewed_by,
        requested_by=user.id,
        expires_at=body.expires_at.astimezone(timezone.utc),
    )
    db.add(review)
    db.flush()  # The PostgreSQL policy checks the still-approved working copy.
    if gate:
        store, snap, values = gate
        key = c3_boundaries.share_key(values["run_id"], doc.qa_revision, digest, body.expires_at)
        c3_boundaries.record(store, snap, "share", key, {**values, "review_id":review.id})
    doc.status = "shared"
    db.add(
        AuditEvent(
            tenant_id=tenant_id, user_id=user.id, subject_id=review.id, event="review.shared", details={"digest": review.digest, "version": review.version, "qa_revision": doc.qa_approved_revision}
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
    allowed = {"comment": comment, "cancelled": m.role in ("editor", "owner", "admin")}.get(body.kind, decide)
    if not allowed:
        raise not_found()
    if body.digest != review.digest:
        raise HTTPException(409, "Content digest does not match this version")
    events = event_list(db, review)
    replay = next((e for e in events if e.actor_id == user.id and e.request_key == body.request_key), None)
    if replay:
        if (replay.kind, replay.note) != (body.kind, body.note):
            raise HTTPException(409, "Idempotency key already used for another decision")
        return render(db, m, review)
    if body.kind in ("rejected", "changes_requested") and len(body.note.strip()) < 5:
        raise HTTPException(422, "Vui lòng nêu lý do cụ thể (ít nhất 5 ký tự).")
    if body.kind == "comment" and not body.note.strip():
        raise HTTPException(422, "Write a comment")
    if status(review, events) != "pending":
        raise HTTPException(409, "Review is closed or expired")
    try:
        append(db, review, user.id, body.kind, body.note, body.request_key)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Review already closed or event conflicted") from None
    return render(db, m, review)
