"""Current authority and immutable evidence at real queue, human QA and client delivery."""

from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from . import c3_content_evidence, c3_projection as projection
from .business_workspace import Workspace
from .knowledge_models import KnowledgeCommand
from .knowledge_store import canonical, conflict, digest
from .workforce_models import WorkforceBrief, WorkforceRun


def context(db, user, brief):
    scope = dict(tenant_id=brief.tenant_id, client_id=brief.client_id, brand_id=brief.brand_id)
    # Use the same client → brand → exact target lock order as internal brief capture.
    workspace = Workspace(SimpleNamespace(path_params=scope), user, db, write=True)
    return workspace, projection.store(workspace, True)


def checked(db, user, brief, manifest, workflow, stage):
    workspace, store = context(db, user, brief)
    snap, public = projection.recheck(store, workspace, manifest["id"], manifest["digest"], workflow, brief, stage)
    return store, snap, public


def record(store, snap, operation, key, result):
    store.insert(KnowledgeCommand, snap.visibility, key=key, operation="c3_" + operation, actor=store.actor,
                 request_digest=digest(canonical(result)), result=result, snapshot_id=snap.id,
                 effective_at=store.now(), queued_at=store.now() if operation == "queue" else None)


def run_for(db, doc):
    run = db.scalar(select(WorkforceRun).filter_by(tenant_id=doc.tenant_id, deliverable_id=doc.id))
    if c3_content_evidence.marketing_run(run):
        return run
    return None


def internal_author(brief):
    if brief and (getattr(brief, "origin", None) == "internal" or (brief.payload or {}).get("internal_task") is True):
        return brief.recipient_id
    return None


def boundary(db, user, doc, content_digest, stage):
    run = run_for(db, doc)
    if not run:
        return None
    brief = db.get(WorkforceBrief, run.brief_id)
    if not brief or (brief.tenant_id, brief.client_id, brief.brand_id, brief.campaign_id) != (doc.tenant_id, run.client_id, run.brand_id, doc.campaign_id):
        conflict("Deliverable is outside the pinned campaign")
    author = internal_author(brief)
    if author and (stage == "share" or author == user.id):
        conflict("Internal Marketing drafts require independent QA and cannot be shared through the client portal")
    binding = run.knowledge["registry"]
    ref = run.knowledge["c3_manifest"]
    store, snap, _ = checked(db, user, brief, ref, binding["workflow"], stage)
    from .registry import pin
    if pin(db, brief, binding["workflow"]) != binding:
        conflict("The approved campaign registry binding changed")
    values = {"run_id":run.id, "document_id":doc.id, "qa_revision":doc.qa_revision, "content_digest":content_digest,
              "manifest_digest":snap.digest, "release_digest":binding["manifest_digest"]}
    from .c3_evidence_review import decision_evidence
    values.update(decision_evidence(store, snap, doc, run, content_digest))
    if stage in ("share", "replay_qa"):
        key = decision_key(run.id, doc.qa_revision, content_digest)
        query = store.query(KnowledgeCommand).filter_by(snapshot_id=snap.id, operation="c3_qa", actor=doc.reviewed_by)
        row = db.scalar(query.where((KnowledgeCommand.key == key) | KnowledgeCommand.key.startswith(key + ":"))
                        .order_by(KnowledgeCommand.effective_at.desc()).limit(1))
        if row is None or row.result != values:
            conflict("A current approval for this manifest and deliverable revision is required")
    return store, snap, values


def decision_key(run_id, revision, content):
    return "qa:" + digest(canonical([run_id,revision,content]))


def record_approval(store, snap, values):
    # A changed assessment can require a second real decision on the same content revision.
    # Lost acknowledgements are handled by the already-approved document branch under its lock.
    key = decision_key(values["run_id"], values["qa_revision"], values["content_digest"])
    record(store, snap, "qa", key + ":" + uuid4().hex[:24], values)


def existing_share(db, user, doc, expires, run):
    if doc.status != "shared":
        return None
    brief = db.get(WorkforceBrief, run.brief_id)
    _, store = context(db, user, brief)
    key = share_key(run.id, doc.qa_revision, doc.qa_approved_digest, expires)
    saved = db.scalar(store.query(KnowledgeCommand).filter_by(actor=user.id, snapshot_id=run.knowledge["c3_manifest"]["id"], key=key, operation="c3_share"))
    return saved.result["review_id"] if saved else None


def share_key(run_id, revision, content, expires):
    from .knowledge_store import stamp
    return "share:" + digest(canonical([run_id,revision,content,stamp(expires)]))
