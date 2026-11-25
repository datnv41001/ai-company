"""Independent domain review of unresolved statements, scoped to the exact saved content."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import c3_boundaries as boundaries, c3_content_evidence as evidence
from .c3_projection import unpack
from .database import get_db
from .delivery import working_copy
from .knowledge_authority import eligible
from .knowledge_contracts import Input, Ref
from .knowledge_models import KnowledgeCommand, KnowledgeRevision
from .knowledge_store import Store, canonical, digest, conflict, missing
from .models import AuditEvent, User
from .c3_reviewer import active_approver
from .revision_qa import content_digest
from .security import current_user, require_tenant
from .workforce_models import WorkforceBrief


router = APIRouter(prefix="/api/tenants/{tenant_id}/deliverables/{did}/content-evidence", tags=["Content evidence"])


class Resolution(Input):
    expected_qa_revision: Annotated[int, Field(ge=1, strict=True)]
    expected_content_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    statement_id: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    handle: Annotated[str, Field(pattern=r"^F[1-9][0-9]?$")]
    qualification_revision: Ref
    reason: Annotated[str, Field(min_length=10, max_length=500)]


def chain(store, payload):
    pinned = payload["pins"]["dependencies"]
    result = {}
    for fact, rid in zip(payload["projection"]["facts"], sorted(payload["options"]["claims"]), strict=True):
        claim = store.get(KnowledgeRevision, rid)
        binding = store.get(KnowledgeRevision, claim.data["binding"])
        source = store.get(KnowledgeRevision, binding.data["source"])
        if any(row.digest != pinned.get(row.id) for row in (claim, binding, source)):
            conflict("The source or claim revision differs from the pinned evidence")
        result[fact["id"]] = dict(
            claim_revision=rid,
            source_revision=source.id,
            source_digest=source.digest,
            document=source.data["document"],
            locator=binding.data["locator"],
            statement=fact["wording"],
            qualifiers=fact["qualifiers"],
            category=fact["category"],
            price=fact.get("price"),
            applicability=fact.get("applicability"),
            quantity=fact.get("quantity"),
            placement=claim.data["assertion"]["placement"],
        )
    for key, revision in (("PRODUCT", payload["brief_pins"]["selections"]["product"]["id"]), ("MARKET", payload["options"]["market"])):
        row = store.get(KnowledgeRevision, revision)
        if pinned.get(row.id) != row.digest:
            conflict("The product or market differs from the manifest")
        result[key] = dict(
            claim_revision=None,
            source_revision=row.id,
            source_digest=row.digest,
            document=row.data["name"],
            locator=row.subject,
            statement=row.data["name"],
            qualifiers=[],
            category=row.kind,
        )
    return result


def approved_mandate(store, id_, actor, category, *, lock=False):
    row = store.get(KnowledgeRevision, id_)
    if (
        row.kind != "qualification"
        or row.data["approver_id"] != actor
        or row.data["category"] != category
        or not active_approver(store.db, store.scope["tenant_id"], actor, lock=lock)
    ):
        conflict("The reviewer needs an active qualification for this claim category")
    eligible(store, row, store.now(), {})
    return row


def receipt_scope(doc, signature):
    return dict(document_id=doc.id, qa_revision=doc.qa_revision, content_digest=signature, version=evidence.VERSION)


def current_report(store, snap, doc, run, signature, *, include_sources=False, lock_reviewers=False):
    report = evidence.assess_document(doc, run, signature)
    _, payload = unpack(store, snap.id)
    if snap.digest != run.knowledge["c3_manifest"]["digest"] or payload["projection"] != run.knowledge["c3_projection"]:
        conflict("The stored Marketing output context differs from its immutable manifest")
    sources = chain(store, payload)
    # The signed receipt is immutable. A later edit, reverted text, mandate withdrawal or
    # loss of membership must prevent it from satisfying a new live decision.
    decisions = store.db.scalars(
        store.query(KnowledgeCommand)
        .filter_by(snapshot_id=snap.id, operation="c3_resolve")
        .where(KnowledgeCommand.key.startswith(f"claim:{doc.qa_revision}:"))
        .order_by(KnowledgeCommand.effective_at.desc())
    )
    by_span = {}
    scope = receipt_scope(doc, signature)
    for receipt in decisions:
        data = receipt.result
        if all(data.get(k) == v for k, v in scope.items()):
            by_span.setdefault(data["statement_id"], []).append(receipt)
    for row in report["statements"]:
        if row["outcome"] == "unresolved":
            for choice in by_span.get(row["id"], ()):
                body = choice.result
                try:
                    approved_mandate(store, body["qualification_revision"], choice.actor, row["claim_type"], lock=lock_reviewers)
                except HTTPException as exc:
                    if exc.status_code in (404, 409):
                        continue
                    raise
                source = sources.get(body["handle"])
                if not source or (source["source_revision"], source["source_digest"]) != (body["source_revision"], body["source_digest"]):
                    continue
                row.update(outcome="reviewed", reason="qualified_review", handles=[body["handle"]], resolution_id=choice.id)
                break
        if include_sources:
            row["sources"] = [dict(handle=h, **sources[h]) for h in row["handles"] if h in sources]
    report["ready"] = all(row["outcome"] in ("verified", "editorial", "reviewed") for row in report["statements"])
    if include_sources:
        report["references"] = sources
    return report


def decision_evidence(store, snap, doc, run, signature):
    report = current_report(store, snap, doc, run, signature, include_sources=True, lock_reviewers=True)
    if not report["ready"]:
        conflict("Content evidence requires a correction or a qualified decision on unsupported claims")
    # Private per-span source revisions/digests remain reconstructible from the immutable
    # manifest and signed resolutions. Pin the exact full assessment in the decision.
    decision = {
        "content_gate_version": evidence.VERSION,
        "content_gate_digest": digest(canonical(report)),
        "content_sources": {key: {k: ref[k] for k in ("claim_revision", "source_revision", "source_digest")} for key, ref in report["references"].items()},
        "reviewed_statements": {r["id"]: r["resolution_id"] for r in report["statements"] if r.get("resolution_id")},
    }
    if (doc.content.get("studio") or {}).get("delivery_version"):
        from .c3_customer_assets import PUBLIC
        public = PUBLIC[run.knowledge["registry"]["workflow"]]
        decision["customer_field_evidence"] = {
            group: {field: [
                {k: row[k] for k in ("id", "claim_type", "outcome", "handles")}
                for row in report["statements"] if row["field"] == f"studio.{group}.{field}"
            ] for field in fields}
            for group, fields in public.items()
        }
    return decision


def staff_document(db, user, tenant_id, did):
    require_tenant(db, user, tenant_id, "editor")
    doc = working_copy(db, tenant_id, did)
    run = boundaries.run_for(db, doc)
    if not run:
        missing()
    sig = content_digest(doc.title, doc.content.get("client_preview", ""))
    return doc, run, sig


@router.get("")
def inspect_gate(tenant_id: str, did: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc, run, sig = staff_document(db, user, tenant_id, did)
    store = Store(db, user, run.tenant_id, run.client_id, run.brand_id, write=False)
    if not store.approver:
        public = evidence.assess_document(doc, run, sig)
        public["ready"] = all(row["outcome"] in ("verified", "editorial") for row in public["statements"])
        return public
    snap, _ = unpack(store, run.knowledge["c3_manifest"]["id"])
    report = current_report(store, snap, doc, run, sig, include_sources=True)
    commands = (
        store.query(KnowledgeCommand)
        .filter_by(snapshot_id=snap.id)
        .where(KnowledgeCommand.operation.in_(("c3_resolve", "c3_qa", "c3_share")))
        .order_by(KnowledgeCommand.effective_at.desc())
    )
    report["decisions"] = [
        dict(id=row.id, actor=row.actor, at=row.effective_at, operation=row.operation, **row.result)
        for row in db.scalars(commands)
        if row.result.get("document_id") == doc.id
    ]
    report["revisions"] = [
        dict(id=r.id, revision=r.details["qa_revision"], content_digest=r.details["content_digest"], evaluated_at=r.occurred_at)
        for r in db.scalars(
            select(AuditEvent)
            .filter_by(tenant_id=tenant_id, subject_id=doc.id, event="deliverable.qa_evaluated")
            .order_by(AuditEvent.occurred_at.desc())
            .limit(30)
        )
    ]
    choices = store.query(KnowledgeRevision).filter_by(kind="qualification").order_by(KnowledgeRevision.id)
    report["qualifications"] = [
        dict(id=r.id, category=r.data["category"]) for r in db.scalars(choices) if r.data["approver_id"] == user.id and store.summary(r)["state"] == "approved"
    ]
    return report


@router.get("/history/{event_id}")
def historical_report(tenant_id: str, did: str, event_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    doc, run, _ = staff_document(db, user, tenant_id, did)
    store = Store(db, user, run.tenant_id, run.client_id, run.brand_id, write=False)
    audit = db.scalar(select(AuditEvent).filter_by(tenant_id=tenant_id, subject_id=doc.id, id=event_id, event="deliverable.qa_evaluated"))
    if not audit:
        missing()
    # Return the stored assessment, including pre-contract legacy assessments, without
    # applying today's rules, current mandate or a new delivery decision to historical bytes.
    record = audit.details
    snap, payload = unpack(store, run.knowledge["c3_manifest"]["id"])
    return {
        "revision": record["qa_revision"],
        "digest": record["content_digest"],
        "evaluated_at": audit.occurred_at,
        "assessment": record.get("content_evidence"),
        "manifest_digest": snap.digest,
        "references": chain(store, payload),
    }


@router.post("/resolutions")
def resolve(tenant_id: str, did: str, body: Resolution, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    doc, run, sig = staff_document(db, user, tenant_id, did)
    if (body.expected_qa_revision, body.expected_content_digest) != (doc.qa_revision, sig):
        raise HTTPException(412, "The reviewed Marketing statement changed")
    brief = db.get(WorkforceBrief, run.brief_id)
    if doc.status != "submitted" or user.id in (doc.created_by, doc.last_editor_id) or boundaries.internal_author(brief) == user.id:
        raise HTTPException(403, "An independent reviewer must resolve a submitted revision")
    store, snap, _ = boundaries.checked(db, user, brief, run.knowledge["c3_manifest"], run.knowledge["registry"]["workflow"], "qa")
    report = evidence.assess_document(doc, run, sig)
    row = next((r for r in report["statements"] if r["id"] == body.statement_id), None)
    if not row or row["outcome"] != "unresolved":
        conflict("Only an unresolved semantic statement may receive a domain decision")
    approved_mandate(store, body.qualification_revision, user.id, row["claim_type"])
    _, payload = unpack(store, snap.id)
    source = chain(store, payload).get(body.handle)
    if not source or (row["handles"] and body.handle not in row["handles"]):
        conflict("Choose a pinned source corresponding to the citation in this statement")
    if row["claim_type"] in ("performance", "comparison", "regulated") and source["category"] != row["claim_type"]:
        conflict("A new approved source for this type of claim is required")
    if any(evidence.normalized(q) not in evidence.normalized(row["text"]) for q in source["qualifiers"]) or source["price"] or source["applicability"]:
        conflict("Use the complete approved declaration with all commercial terms and qualifiers")
    values = dict(
        receipt_scope(doc, sig),
        statement_id=row["id"],
        handle=body.handle,
        source_revision=source["source_revision"],
        source_digest=source["source_digest"],
        reason=body.reason,
        qualification_revision=body.qualification_revision,
    )
    key = f"claim:{doc.qa_revision}:" + digest(canonical(values))
    prior = db.scalar(store.query(KnowledgeCommand).filter_by(snapshot_id=snap.id, actor=user.id, key=key))
    if not prior:
        boundaries.record(store, snap, "resolve", key, values)
        db.commit()
    return values
