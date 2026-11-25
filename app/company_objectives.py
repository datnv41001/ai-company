"""Client-owned objectives with immutable authoring and exact parent authority for brand/campaign work."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import aliased

from .business_workspace import BASE, Counter, reader, writer
from .knowledge_contracts import Input, Key, Name, Ref
from .knowledge_store import canonical, conflict, digest, missing, signed_document, stamp
from .models import new_id
from .objective_models import CompanyObjective as Row


router = APIRouter(prefix=BASE + "/company-objectives", tags=["shared company objectives"])


class CompanySave(Input):
    key: Key
    expected_revision: Counter
    subject: Ref | None = None
    name: Name
    owner: Name


class CompanyDecision(Input):
    key: Key
    expected_sequence: Counter
    expected_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    state: Literal["approved", "disputed", "withdrawn", "superseded"]
    reason: Name


def rows(tenant, client):
    return select(Row).filter_by(tenant_id=tenant, client_id=client)


def root_revision(db, tenant, client, revision_id):
    row = db.scalar(rows(tenant, client).filter_by(sequence=0, id=revision_id))
    if not row:
        missing()
    return row


def lock_subject(db, root, *, shared):
    if db.get_bind().dialect.name == "postgresql":
        # Terminal lock acquired after the normal client or brand/membership guards.
        # Decisions never take a brand lock; parent checks can run across brands in parallel.
        function = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
        db.execute(text(f"SELECT {function}(hashtextextended(:key,3))"), {"key": "objective:" + root.tenant_id + ":" + root.client_id + ":" + root.subject})


def latest_decision(db, root):
    return db.scalar(rows(root.tenant_id, root.client_id).filter_by(revision_id=root.id).order_by(Row.sequence.desc()).limit(1))


def current_state(db, root, last):
    if last.state == "approved" and db.scalar(
        rows(root.tenant_id, root.client_id).filter_by(subject=root.subject, state="approved").where(Row.revision > root.revision).limit(1)
    ):
        return "superseded"
    return last.state


def check_company_reference(store, revision_id, *, require_approved):
    root = root_revision(store.db, store.scope["tenant_id"], store.scope["client_id"], revision_id)
    if require_approved:
        lock_subject(store.db, root, shared=True)
        if current_state(store.db, root, latest_decision(store.db, root)) != "approved":
            conflict("The selected company objective revision no longer has approved authority")
    return root


def view(row, *, state=None):
    return dict(
        id=row.revision_id,
        event_id=row.id,
        subject=row.subject,
        kind="company_objective",
        scope="company",
        tenant_id=row.tenant_id,
        client_id=row.client_id,
        revision=row.revision,
        sequence=row.sequence,
        digest=row.digest,
        state=state or row.state,
        label=row.name,
        data={"name": row.name, "owner": row.owner_name},
        reason=row.reason,
        created_at=stamp(row.created_at),
    )


def append(s, body, operation, target, make_values):
    fingerprint = digest(canonical([operation, target, body.model_dump(mode="json")]))
    prior = s.db.scalar(rows(s.tenant, s.client).filter_by(actor=s.actor, command_key=body.key))
    if prior:
        if prior.request_digest != fingerprint:
            conflict("Command key already used for different inputs")
        return view(prior)
    now = s.db.scalar(text("SELECT clock_timestamp()")) if s.postgres else datetime.now(timezone.utc)
    values = make_values() | dict(tenant_id=s.tenant, client_id=s.client, actor=s.actor, command_key=body.key, request_digest=fingerprint, created_at=now)
    if s.postgres:
        s.db.execute(text("SELECT amc_business.append_objective(:doc,:proof)"), signed_document(s.db, s.actor, Row.__tablename__, values))
    else:
        s.db.execute(Row.__table__.insert().values(**values))
    s.db.commit()
    return view(Row(**values))


@router.post("", status_code=201)
def revise(body: CompanySave, s=Depends(writer)):
    def make():
        subject = body.subject or new_id()
        latest = s.db.scalar(rows(s.tenant, s.client).filter_by(subject=subject, sequence=0).order_by(Row.revision.desc()).limit(1))
        if body.subject and not latest:
            missing()
        if (latest.revision if latest else 0) != body.expected_revision:
            conflict("Company objective changed. Reload before editing")
        revision = body.expected_revision + 1
        rid = new_id()
        signature = digest(canonical([s.tenant, s.client, subject, revision, body.name, body.owner]))
        return dict(
            id=rid,
            revision_id=rid,
            subject=subject,
            revision=revision,
            sequence=0,
            state="draft",
            name=body.name,
            owner_name=body.owner,
            digest=signature,
            reason="",
        )

    return append(s, body, "revise", None, make)


@router.get("")
def list_objectives(
    q: str = Query("", max_length=100),
    after: str = Query("", max_length=36),
    limit: int = Query(20, ge=1, le=50),
    approved_only: bool = False,
    s=Depends(reader),
):
    base = rows(s.tenant, s.client)
    candidates = base.with_only_columns(Row.subject, func.max(Row.revision).label("latest"))
    candidates = candidates.where(Row.state == "approved") if approved_only else candidates.where(Row.sequence == 0)
    heads = candidates.group_by(Row.subject).subquery()
    query = base.join(heads, (heads.c.subject == Row.subject) & (heads.c.latest == Row.revision)).where(Row.sequence == 0, Row.subject > after)
    if approved_only:
        log = aliased(Row)
        state = select(log.state).where(log.revision_id == Row.id).order_by(log.sequence.desc()).limit(1).scalar_subquery()
        query = query.where(state == "approved")
    if q.strip():
        query = query.where(Row.name.icontains(q.strip(), autoescape=True))
    found = list(s.db.scalars(query.order_by(Row.subject).limit(limit + 1)))
    result = []
    for root in found[:limit]:
        event = latest_decision(s.db, root)
        result.append(view(event, state=current_state(s.db, root, event)))
    return {"items": result, "next": found[limit - 1].subject if len(found) > limit else None}


@router.get("/commands/{key}")
def receipt(key: str, s=Depends(reader)):
    r = s.db.scalar(rows(s.tenant, s.client).filter_by(actor=s.actor, command_key=key))
    if not r:
        missing()
    return view(r)


@router.get("/{revision_id}")
def detail(revision_id: str, s=Depends(reader)):
    root = root_revision(s.db, s.tenant, s.client, revision_id)
    last = latest_decision(s.db, root)
    return view(last, state=current_state(s.db, root, last))


@router.get("/{revision_id}/events")
def history(revision_id: str, s=Depends(reader)):
    root = root_revision(s.db, s.tenant, s.client, revision_id)
    return [view(e) for e in s.db.scalars(rows(s.tenant, s.client).filter_by(revision_id=root.id).order_by(Row.sequence))]


@router.post("/{revision_id}/events")
def decide(revision_id: str, body: CompanyDecision, s=Depends(writer)):
    if s.role not in ("admin", "owner"):
        missing()
    root = root_revision(s.db, s.tenant, s.client, revision_id)

    def make():
        lock_subject(s.db, root, shared=False)
        last = latest_decision(s.db, root)
        state = current_state(s.db, root, last)
        allowed = {
            "draft": {"approved", "withdrawn", "disputed"},
            "approved": {"withdrawn", "superseded", "disputed"},
            "disputed": {"withdrawn", "superseded"},
            "superseded": {"withdrawn"},
        }
        if body.expected_digest != root.digest or body.expected_sequence != last.sequence or body.state not in allowed.get(state, set()):
            conflict("Company objective decision changed or is ineligible")
        if body.state == "approved" and s.db.scalar(
            rows(s.tenant, s.client).filter_by(subject=root.subject, sequence=0).where(Row.revision > root.revision).limit(1)
        ):
            conflict("Approve the current company objective draft")
        return dict(
            id=new_id(),
            revision_id=root.id,
            subject=root.subject,
            revision=root.revision,
            sequence=last.sequence + 1,
            state=body.state,
            name=root.name,
            owner_name=root.owner_name,
            digest=root.digest,
            reason=body.reason,
        )

    return append(s, body, "decision", root.id, make)
