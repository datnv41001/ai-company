"""Human edits and independent QA for the guide produced by a scoped WF-06 run."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import product_guide_runtime as guide
from .database import get_db
from .delivery import save_working_revision, working_copy
from .knowledge_contracts import Input
from .knowledge_models import KnowledgeCommand, KnowledgeSnapshot
from .knowledge_store import Store, canonical, conflict, digest, missing
from .models import User
from .product_guide_admission import check_guide_access
from .revision_qa import content_digest
from .security import current_user, require_tenant
from .workforce_models import WorkforceBrief, WorkforceRun


router = APIRouter(prefix="/api/tenants/{tenant_id}/deliverables/{did}/studio/product-guide", tags=["Marketing Studio"])


class GuideRevision(Input):
    expected_qa_revision: Annotated[int, Field(strict=True, ge=1)]
    expected_content_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    def check(self, doc):
        if (doc.qa_revision, content_digest(doc.title, doc.content["client_preview"])) != (self.expected_qa_revision, self.expected_content_digest):
            raise HTTPException(412, "Reload the guide before saving or submitting this edition")


class GuideEdit(GuideRevision):
    heading: Literal["product", "use_case", "source"]
    layout: Literal["numbered", "checklist"]
    custom_title: Annotated[str, Field(min_length=1, max_length=160)] | None = None


def subject_runs(db, tenant, ids):
    """Resolve protected subjects from actual producer rows, never from freely editable asset metadata."""
    if not ids:
        return {}
    rows = db.scalars(
        select(WorkforceRun).where(
            WorkforceRun.tenant_id == tenant,
            WorkforceRun.knowledge["registry"]["workflow"].as_string() == guide.RELEASE,
            or_(WorkforceRun.deliverable_id.in_(ids), WorkforceRun.id.in_(ids), WorkforceRun.brief_id.in_(ids)),
        )
    )
    return {key: run for run in rows for key in (run.deliverable_id, run.id, run.brief_id) if key}


def can_read(db, user, run):
    try:
        check_guide_access(db, user, run, write=False)
    except HTTPException as exc:
        if exc.status_code in (403, 404, 409, 412):
            return False
        raise
    return True


def readable(db, user, tenant, rows, *, key="id"):
    records = list(rows)
    bindings = subject_runs(db, tenant, {getattr(r, key) for r in records})
    denied = {r.id for r in set(bindings.values()) if not can_read(db, user, r)}
    return [r for r in records if (run := bindings.get(getattr(r, key))) is None or run.id not in denied]


def for_document(db, tenant, did):
    return subject_runs(db, tenant, [did]).get(did)


def check_document(db, user, doc, *, edit=False, review=False):
    run = for_document(db, doc.tenant_id, doc.id)
    if run is not None:
        check_guide_access(db, user, run, write=edit or review)
        editor = db.get(WorkforceBrief, run.brief_id).recipient_id
        if (edit and user.id != editor) or (review and user.id == editor):
            raise HTTPException(403, "The assigned editor and independent reviewer have separate responsibilities")
    return run


def current_edition(doc, run, projection):
    if run.state != "awaiting_qa" or not any(c["skill"] == "content" for c in run.checkpoints):
        conflict("The Content worker has not produced this guide")
    try:
        edition = doc.content["product_guide"]
        expected = guide.compose(projection, edition["choices"])
        preview = guide.preview(expected)
    except (KeyError, ValueError, TypeError):
        conflict("The guide cannot be reconstructed from the current authorized source")
    if edition != expected or (doc.title, doc.content.get("client_preview")) != (preview["title"], preview["body"]):
        conflict("Reload the current guide and its source-bound edition")
    return expected


def qa_material(db, user, doc, run, signature, edition, *, write):
    brief = db.get(WorkforceBrief, run.brief_id)
    store = Store(db, user, run.tenant_id, run.client_id, run.brand_id, write=write)
    ref = run.knowledge["c3_manifest"]
    snap = store.get(KnowledgeSnapshot, ref["id"])
    if snap.digest != ref["digest"] or snap.brief_id != run.brief_id or snap.campaign_id != run.campaign_id:
        missing()
    values = {
        "run_id": run.id,
        "document_id": doc.id,
        "qa_revision": doc.qa_revision,
        "content_digest": signature,
        "manifest_digest": snap.digest,
        "release_digest": run.knowledge["registry"]["manifest_digest"],
        "brief_id": run.brief_id,
        "strategy_handoff_receipt": brief.payload["guide_binding"]["handoff_receipt"],
        "guide_digest": digest(canonical(edition)),
    }
    return store, snap, values


def approved_receipt(store, snap, values, actor):
    from .c3_boundaries import decision_key

    key = decision_key(values["run_id"], values["qa_revision"], values["content_digest"])
    query = store.query(KnowledgeCommand).filter_by(snapshot_id=snap.id, operation="c3_qa", actor=actor)
    approval = store.db.scalar(query.where(KnowledgeCommand.key.startswith(key + ":")).order_by(KnowledgeCommand.effective_at.desc()).limit(1))
    if not approval or approval.result != values:
        conflict("A current independent Content QA receipt is required")
    return approval.id


def proof(db, user, doc, run, signature, stage):
    if stage == "share":
        conflict("This internal guide has no publication or portal approval")
    projection = check_guide_access(db, user, run, write=True)
    editor = db.get(WorkforceBrief, run.brief_id).recipient_id
    if user.id in (editor, doc.created_by, doc.last_editor_id):
        raise HTTPException(403, "The Content reviewer must be independent of this edition")
    edition = current_edition(doc, run, projection)
    material = qa_material(db, user, doc, run, signature, edition, write=True)
    if stage == "replay_qa":
        approved_receipt(*material, user.id)
    return material


def view(db, user, doc, run, projection):
    edition = current_edition(doc, run, projection)
    is_editor = user.id == db.get(WorkforceBrief, run.brief_id).recipient_id
    signature = content_digest(doc.title, doc.content["client_preview"])
    qa_receipt = None
    if doc.status == "approved":
        if (doc.qa_approved_revision, doc.qa_approved_digest) != (doc.qa_revision, signature):
            conflict("Reload the current approved guide")
        material = qa_material(db, user, doc, run, signature, edition, write=False)
        qa_receipt = approved_receipt(*material, doc.reviewed_by)
    return {
        "document_id": doc.id,
        "run_id": run.id,
        "status": doc.status,
        "revision": doc.qa_revision,
        "content_digest": signature,
        "qa_receipt": qa_receipt,
        "guide": edition,
        "titles": guide.titles(projection),
        "source_titles": guide.source_titles(projection),
        "can_edit": is_editor,
        "can_review": not is_editor and user.id not in (doc.created_by, doc.last_editor_id) and doc.status == "submitted",
    }


def open_guide(db, tenant, did, user, *, edit=False):
    require_tenant(db, user, tenant, "editor")
    doc = working_copy(db, tenant, did)
    run = for_document(db, tenant, did)
    if not run:
        missing()
    projection = check_guide_access(db, user, run, write=edit)
    if edit and user.id != db.get(WorkforceBrief, run.brief_id).recipient_id:
        raise HTTPException(403, "Only the assigned Content recipient may edit this guide")
    return doc, run, projection


@router.get("")
def inspect(tenant_id: str, did: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return view(db, user, *open_guide(db, tenant_id, did, user))


@router.patch("")
def edit(tenant_id: str, did: str, body: GuideEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc, run, projection = open_guide(db, tenant_id, did, user, edit=True)
    body.check(doc)
    current_edition(doc, run, projection)
    selection = body.model_dump(include={"heading", "layout", "custom_title"}, exclude_none=True)
    try:
        edition = guide.compose(projection, selection)
    except ValueError as exc:
        raise HTTPException(422, "Choose a complete released source step or one of its approved title variants") from exc
    preview = guide.preview(edition)
    doc.content = {**doc.content, "product_guide": edition}
    save_working_revision(db, doc, user.id, preview["title"], preview["body"])
    result = view(db, user, doc, run, projection)
    db.commit()
    return result
