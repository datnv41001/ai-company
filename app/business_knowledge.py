"""Internal C1 commands. Durable authorization receipts never enqueue, publish or bill."""

from datetime import timedelta
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from . import knowledge_models as m
from .database import get_db
from .knowledge_authority import change_state, check_assertion, eligible, invalid, new_revision, scoped_references
from .knowledge_contracts import AuthorizeIn, Command, EventIn, Kind, PreviewIn, RevisionIn, Target
from .knowledge_target import describe
from .knowledge_store import Store, aware, canonical, conflict, digest, missing, restrictive, stamp
from .security import current_user

router = APIRouter(prefix="/api/tenants/{tenant_id}/clients/{client_id}/brands/{brand_id}/knowledge", tags=["business knowledge"])


def reader(tenant_id: str, client_id: str, brand_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return Store(db, user, tenant_id, client_id, brand_id, write=False)


def writer(tenant_id: str, client_id: str, brand_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    return Store(db, user, tenant_id, client_id, brand_id, write=True)


@router.post("/revisions", status_code=201)
def revise(body: RevisionIn, s=Depends(writer)):
    if body.subject in ("legacy-truth", "legacy-guidelines"):
        conflict("Legacy import owns this subject; create a separately reviewed replacement")
    return s.command("revision", body, lambda at: (new_revision(s, body, at), body.visibility, None))


@router.get("/revisions/{revision_id}")
def detail(revision_id: str, s=Depends(reader)):
    row = s.get(m.KnowledgeRevision, revision_id)
    if not s.approver and row.kind in ("source", "binding", "claim"):
        refs = scoped_references(s, row.data)
        if row.kind == "claim":
            scoped_references(s, refs["binding", row.data["binding"]].data)
    return {**s.summary(row), "data": row.data, "created_at": stamp(row.created_at), "author": row.author}


@router.get("/revisions")
def revisions(kind: Kind, limit: int = Query(30, ge=1, le=100), s=Depends(reader)):
    rows = s.db.scalars(s.query(m.KnowledgeRevision).filter_by(kind=kind).order_by(m.KnowledgeRevision.created_at.desc(), m.KnowledgeRevision.id).limit(limit))
    return [s.summary(row) for row in rows]


@router.post("/revisions/{revision_id}/events")
def transition(revision_id: str, body: EventIn, s=Depends(writer)):
    row = s.get(m.KnowledgeRevision, revision_id)
    if not s.approver:
        missing()
    return s.command("event", body, lambda at: (change_state(s, row, body, at), row.visibility, None), target=revision_id)


@router.get("/revisions/{revision_id}/events")
def history(revision_id: str, s=Depends(reader)):
    row = s.get(m.KnowledgeRevision, revision_id)
    preferred = s.db.scalar(s.query(m.KnowledgeLink).filter_by(revision_id=revision_id, relation="preferred_authority"))
    rows = s.db.scalars(s.query(m.KnowledgeEvent).filter_by(revision_id=revision_id).order_by(m.KnowledgeEvent.sequence))
    return [
        dict(
            sequence=r.sequence,
            event="knowledge.approved" if r.state == "approved" else "knowledge.invalidated",
            state=r.state,
            **({"reason":r.reason,"actor":r.actor} if s.approver or row.kind not in ("source","binding","claim") else {}),
            effective_at=stamp(r.effective_at),
            **({"preferred_revision": preferred.target_id} if preferred and r.state == "superseded" else {}),
        )
        for r in rows
    ]


@router.get("/revisions/{revision_id}/impact")
def impact(revision_id: str, limit: int = Query(30, ge=1, le=100), s=Depends(reader)):
    s.get(m.KnowledgeRevision, revision_id)
    # Resolve audience at read time. A source link never grants access to a more restricted snapshot.
    rows = s.db.scalars(
        s.query(m.KnowledgeSnapshot)
        .join(m.KnowledgeDependency, m.KnowledgeDependency.snapshot_id == m.KnowledgeSnapshot.id)
        .where(m.KnowledgeDependency.revision_id == revision_id)
        .order_by(m.KnowledgeSnapshot.preview_created_at.desc(), m.KnowledgeSnapshot.id)
        .limit(limit + 1)
    ).all()
    return {"snapshots": [{"id": r.id, "digest": r.digest} for r in rows[:limit]], "more": len(rows) > limit}


@router.post("/import-legacy")
def legacy(body: Command, s=Depends(writer)):
    def execute(at):
        rows = []
        for name, kind, value in (("guidelines", "guidelines", s.brand.brand_guidelines), ("truth", "source", s.brand.product_truth)):
            if value and value.strip():
                data = (
                    {"guidance": value}
                    if kind == "guidelines"
                    else {"publisher": "Legacy brand record", "document": "product_truth", "entries": [], "valid_until": stamp(at), "legacy_text": value}
                )
                subject = "legacy-" + name
                prior = s.db.scalar(s.query(m.KnowledgeRevision).filter_by(subject=subject).order_by(m.KnowledgeRevision.revision.desc()).limit(1))
                match = prior and (prior.data.get("guidance") == value.strip() if kind == "guidelines" else prior.data.get("legacy_text") == value.strip())
                if match:
                    rows.append(s.summary(prior, at))
                else:
                    request = RevisionIn(
                        key=body.key, subject=subject, kind=kind, expected_revision=prior.revision if prior else 0, visibility="internal", data=data
                    )
                    rows.append(new_revision(s, request, at))
        return {"revisions": rows}, "internal", None

    return s.command("import_legacy", body, execute)


def resolved(s, claims, at):
    deps = {}
    marketing = []
    for rid in sorted(claims):
        record = s.get(m.KnowledgeRevision, rid)
        if record.kind != "claim" or record.visibility != "public":
            conflict("Only approved public wording can enter a Marketing projection")
        eligible(s, record, at, deps)
        assertion = record.data["assertion"]
        check_assertion(s, assertion, at)
        # Restricted full documents, excerpts, supplier terms and actor data stay in the dependency index.
        item = {
            "claim_revision": rid,
            "wording": assertion["wording"],
            "qualifiers": assertion["qualifiers"],
            "category": assertion["category"],
            "placement": assertion["placement"],
        }
        if assertion["category"] == "price":
            item.update(price=assertion["price"], quantity=assertion["quantity"])
        if assertion.get("applicability"):
            item["applicability"] = assertion["applicability"]
        marketing.append(item)
    return deps, marketing


@router.post("/previews", status_code=201)
def preview(body: PreviewIn, s=Depends(writer)):
    target = {}

    def materialize(at):
        if len(set(body.claims)) != len(body.claims):
            invalid("Duplicate claim revision")
        deps, claims = resolved(s, body.claims, at)
        canonical_text = canonical({"version": 1, "scope": s.scope, "target": target, "snapshot_as_of": stamp(at), "claims": claims})
        created = s.now()
        vis = restrictive(*(r.visibility for r in deps.values()))
        snap = s.insert(
            m.KnowledgeSnapshot,
            vis,
            canonical=canonical_text,
            digest=digest(canonical_text),
            snapshot_as_of=at,
            preview_created_at=created,
            expires_at=created + timedelta(seconds=body.ttl_seconds),
            campaign_id=body.target.campaign_id if body.target else None,
            brief_id=body.target.brief_id if body.target else None,
        )
        for row in deps.values():
            s.insert(m.KnowledgeDependency, vis, snapshot_id=snap.id, revision_id=row.id)
        return snapshot_view(snap), vis, snap.id

    return s.command("preview", body, materialize, prepare=lambda: target.update(describe(s, body.target, lock=True)))


def snapshot_view(snap):
    return dict(
        id=snap.id,
        digest=snap.digest,
        canonical=snap.canonical,
        snapshot_as_of=stamp(snap.snapshot_as_of),
        preview_created_at=stamp(snap.preview_created_at),
        expires_at=stamp(snap.expires_at),
        target=json.loads(snap.canonical)["target"],
    )


def check_snapshot(s, snap, at, target):
    if digest(snap.canonical) != snap.digest:
        conflict("Snapshot integrity check failed")
    payload = json.loads(snap.canonical)
    if payload["version"] != 1:
        missing()
    deps, claims = resolved(s, [r["claim_revision"] for r in payload["claims"]], at)
    recorded = s.db.scalars(s.query(m.KnowledgeDependency).filter_by(snapshot_id=snap.id)).all()
    if target != payload["target"] or claims != payload["claims"] or payload["scope"] != s.scope or {r.revision_id for r in recorded} != deps.keys():
        conflict("Knowledge dependencies changed")


@router.get("/snapshots/{snapshot_id}")
def snapshot(snapshot_id: str, s=Depends(reader)):
    snap = s.get(m.KnowledgeSnapshot, snapshot_id)
    problem = None
    try:
        target = Target(campaign_id=snap.campaign_id, brief_id=snap.brief_id) if snap.brief_id else None
        check_snapshot(s, snap, s.now(), describe(s, target, lock=False))
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        problem = exc.detail
    return {**snapshot_view(snap), "current_authority_issue": problem}


@router.post("/authorize")
def authorize(body: AuthorizeIn, s=Depends(writer)):
    if body.operation in ("qa", "share") and not s.approver:
        missing()

    snap = s.get(m.KnowledgeSnapshot, body.snapshot_id)
    expected = (snap.campaign_id, snap.brief_id)
    supplied = (body.target.campaign_id, body.target.brief_id) if body.target else (None, None)
    if expected != supplied:
        conflict("Snapshot target differs; a brand foundation receipt cannot authorize campaign work")
    target = {}

    def command(at):
        if snap.digest != body.digest:
            conflict("Digest changed")
        previous = {"qa": "queue", "share": "qa"}.get(body.operation)
        if previous:
            if not body.previous_receipt:
                conflict("Missing prior authority receipt")
            receipt = s.get(m.KnowledgeCommand, body.previous_receipt)
            if receipt.operation != previous or receipt.snapshot_id != snap.id or receipt.result.get("digest") != snap.digest:
                conflict("Prior receipt covers a different operation or snapshot")
        elif body.previous_receipt or at >= aware(snap.expires_at):
            conflict("Invalid or expired queue preview")
        check_snapshot(s, snap, at, target)
        if body.target and not target["submitted"]:
            conflict("Brief has not been submitted")
        return (
            dict(operation=body.operation, snapshot_id=snap.id, digest=snap.digest, target=target, previous_receipt=body.previous_receipt),
            snap.visibility,
            snap.id,
        )

    return s.command(body.operation, body, command, prepare=lambda: target.update(describe(s, body.target, lock=True)))


@router.get("/receipts/{receipt_id}")
def receipt(receipt_id: str, s=Depends(reader)):
    row = s.get(m.KnowledgeCommand, receipt_id)
    if row.operation not in ("queue", "qa", "share"):
        missing()
    return row.result
