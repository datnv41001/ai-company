"""Bind an internally reviewed storyboard preview to an approved, scoped Studio destination."""

from base64 import b64encode
import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import Field
from sqlalchemy import select

from . import c3_boundaries, c3_projection, c3_reviewer, production_studios as studio
from .delivery import working_copy
from .knowledge_contracts import Input, Ref
from .knowledge_models import KnowledgeCommand
from .knowledge_store import canonical, conflict, digest, missing
from .revision_qa import content_digest
from .security import require_tenant
from .storyboard_preview import render_bytes

router = APIRouter(
    prefix="/api/tenants/{tenant_id}/deliverables/{did}/studio/production/{pid}/storyboard-distributions",
    tags=["Internal storyboard distribution"],
)
OP = "storyboard_distribution"
QA = "storyboard_preview_qa"


class Commission(Input):
    request_id: UUID
    storyboard_document_id: Ref
    expected_run_id: Ref
    expected_revision: Annotated[int, Field(gt=0, strict=True)]
    expected_content_digest: studio.Hash
    expected_landing_digest: studio.Hash
    style: Literal["parts", "route", "rhythm"]


def scope(db, user, tenant, did, pid, board_id, *, write):
    # All board editors acquire this document lock before scoped knowledge locks.
    require_tenant(db, user, tenant, "admin")
    board_doc = working_copy(db, tenant, board_id)
    landing, landing_run, store = studio.scope(db, user, tenant, did, write)
    run = c3_boundaries.run_for(db, board_doc)
    if not run or run.knowledge["registry"]["workflow"] not in ("WF-08/video-storyboard@1", "WF-08/video-storyboard@2"):
        missing()
    if (run.campaign_id, run.client_id, run.brand_id) != (landing_run.campaign_id, landing_run.client_id, landing_run.brand_id):
        missing()
    pkg = studio.get_package(store, landing, pid)
    if pkg.result["kind"] != "landing":
        missing()
    return board_doc, run, landing, landing_run, pkg, store


def pins(user, board_doc, run, landing, landing_run, pkg, store, *, write):
    db, tenant = store.db, store.scope["tenant_id"]
    plan = studio.verify_current(store, user, landing, landing_run, pkg, inspect_only=not write)
    landing_qa = studio.approval(store, pkg, lock=write)
    if not landing_qa:
        conflict("The current landing files require independent QA")
    signature = content_digest(board_doc.title, board_doc.content["client_preview"])
    if (run.state != "awaiting_qa" or board_doc.status != "approved" or board_doc.qa_revision != board_doc.qa_approved_revision
            or board_doc.qa_approved_digest != signature or board_doc.reviewed_by == board_doc.last_editor_id
            or not c3_reviewer.active_approver(db, tenant, board_doc.reviewed_by, lock=write)):
        conflict("The current storyboard edition requires independent QA")
    _, snapshot, proof = c3_boundaries.boundary(db, user, board_doc, signature, "replay_qa", inspect_only=not write)
    key = c3_boundaries.decision_key(run.id, board_doc.qa_revision, signature)
    decisions = store.query(KnowledgeCommand).filter_by(snapshot_id=snapshot.id, operation="c3_qa", actor=board_doc.reviewed_by)
    approved = next((r for r in db.scalars(decisions.where((KnowledgeCommand.key == key) | KnowledgeCommand.key.startswith(key + ":")))
                     if r.result == proof), None)
    if not approved:
        conflict("Missing QA decision for this storyboard manifest and edition")
    _, video_manifest = c3_projection.unpack(store, snapshot.id)
    _, page_manifest = c3_projection.unpack(store, landing_run.knowledge["c3_manifest"]["id"])
    # A page may have its own brief, but identities and signed knowledge must match.
    # In particular, equality of two public product/claim descriptions is insufficient.
    def shared(source):
        return [source["brief_pins"], {k: v for k, v in source["pins"].items() if k != "task"},
                {k: v for k, v in source["options"].items() if k not in ("workflow", "target")},
                source["projection"]["task_intent"]["buyer_action"]]
    if shared(video_manifest) != shared(page_manifest):
        conflict("Storyboard and destination require the same approved business brief, source revisions and buyer action")
    board = json.loads(board_doc.content["client_preview"])
    if board.get("rights") != "synthetic_illustration_only":
        conflict("Current rights do not authorize a synthetic preview")
    checkpoint = next((c for c in run.checkpoints if c["skill"] == "storyboard"), None)
    if not checkpoint or board["source_refs"]["manifest"] != run.knowledge["c3_manifest"]:
        conflict("Missing completed storyboard checkpoint")
    queue = db.scalar(store.query(KnowledgeCommand).filter_by(operation="c3_queue", key="queue:" + run.id, snapshot_id=snapshot.id))
    if (not queue or queue.result.get("run_id") != run.id or queue.result.get("manifest_digest") != snapshot.digest
            or queue.result.get("release_digest") != run.knowledge["registry"]["manifest_digest"]):
        conflict("Missing queue receipt for the exact storyboard manifest and registry release")
    return board, {
        "scope": {**store.scope, "campaign_id": run.campaign_id},
        "storyboard": {"run_id": run.id, "brief_id": run.brief_id, "document_id": board_doc.id, "manifest": run.knowledge["c3_manifest"],
                       "revision": board_doc.qa_revision, "content_digest": signature, "checkpoint_digest": digest(canonical(checkpoint)),
                       "board_digest": proof["storyboard_digest"], "qa_receipt": approved.id, "queue_receipt": queue.id},
        "landing": {"plan_id": plan["id"], "plan_digest": plan["digest"], "run_id": landing_run.id, "document_id": landing.id,
                    "manifest": landing_run.knowledge["c3_manifest"], "revision": landing.qa_revision,
                    "package_id": pkg.id, "package_digest": pkg.result["digest"], "file_digest": pkg.result["files"]["landing.html"]["sha256"],
                    "qa_receipt": landing_qa.id},
        "source_revisions_digest": digest(canonical(shared(video_manifest))),
        "distribution_mode": "authenticated_synthetic_only",
    }


def view(row):
    return {"id": row.id, **{k: v for k, v in row.result.items() if k not in ("payloads", "request")}}


@router.post("")
def create(tenant_id: str, did: str, pid: str, body: Commission, user: studio.Actor, db: studio.DB):
    context = scope(db, user, tenant_id, did, pid, body.storyboard_document_id, write=True)
    board_doc, run, _, _, pkg, store = context
    if (run.id, board_doc.qa_revision, content_digest(board_doc.title, board_doc.content["client_preview"]), pkg.result["digest"]) != (
        body.expected_run_id, body.expected_revision, body.expected_content_digest, body.expected_landing_digest
    ):
        raise HTTPException(412, "Reload the storyboard and landing before binding this preview")
    board, source = pins(user, *context, write=True)
    key = "distribution:" + body.request_id.hex
    request = digest(canonical([did, pid, body.model_dump(mode="json")]))
    prior = db.scalar(store.query(KnowledgeCommand).filter_by(actor=user.id, key=key))
    if prior:
        if prior.operation != OP or prior.result["request"] != request or any(prior.result[k] != v for k, v in source.items()):
            conflict("Request ID already used for a different storyboard distribution")
        return view(prior)
    try:
        files, renderer = render_bytes(canonical(board).encode(), body.style, "approved-storyboard.json")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    value = {**source, "preview": {"file_digest": renderer["files"]["preview.webm"], "renderer": renderer}}
    value["distribution_digest"] = digest(canonical(value))
    value.update(request=request, payloads={name: b64encode(data).decode("ascii") for name, data in files.items()})
    row = studio.append_document(store, run, OP, key, value)
    db.commit()
    return view(row)


def current(db, user, tenant, did, pid, ident, *, write):
    require_tenant(db, user, tenant, "admin")
    col = KnowledgeCommand.result
    board_id = db.scalar(select(col["storyboard"]["document_id"].as_string()).where(
        KnowledgeCommand.tenant_id == tenant, KnowledgeCommand.id == ident, KnowledgeCommand.operation == OP,
        col["landing"]["document_id"].as_string() == did, col["landing"]["package_id"].as_string() == pid))
    if not board_id:
        missing()
    context = scope(db, user, tenant, did, pid, board_id, write=write)
    store = context[-1]
    row = store.get(KnowledgeCommand, ident)
    _, now = pins(user, *context, write=write)
    if any(row.result[k] != v for k, v in now.items()):
        conflict("The storyboard or destination has changed since this preview was prepared")
    return row, store, context[1]


def verdict(store, row, *, lock):
    decisions = store.query(KnowledgeCommand).filter_by(operation=QA, key="preview-qa:" + row.id)
    return next((d for d in store.db.scalars(decisions.order_by(KnowledgeCommand.effective_at.desc()))
                 if d.actor != row.actor and d.result["digest"] == row.result["distribution_digest"]
                 and c3_reviewer.active_approver(store.db, store.scope["tenant_id"], d.actor, lock=lock)), None)


def resolve(db, user, tenant, landing_did, landing_pid, distribution_id, *, write=False):
    row, store, _ = current(db, user, tenant, landing_did, landing_pid, distribution_id, write=write)
    signed = verdict(store, row, lock=write)
    if not signed:
        conflict("An independent reviewer must approve the rendered creative and destination")
    return {**view(row), "preview_qa": {"receipt": signed.id, "reviewer": signed.actor}}


@router.get("/{ident}")
def read(tenant_id: str, did: str, pid: str, ident: str, user: studio.Actor, db: studio.DB):
    return resolve(db, user, tenant_id, did, pid, ident)


@router.get("/{ident}/files/{name}")
def file(tenant_id: str, did: str, pid: str, ident: str, name: str, user: studio.Actor, db: studio.DB):
    row, _, _ = current(db, user, tenant_id, did, pid, ident, write=False)
    if name not in row.result["payloads"]:
        missing()
    return {"base64": row.result["payloads"][name], "sha256": row.result["preview"]["renderer"]["files"][name]}


@router.post("/{ident}/approve")
def approve(tenant_id: str, did: str, pid: str, ident: str, body: studio.Verdict, user: studio.Actor, db: studio.DB):
    row, store, run = current(db, user, tenant_id, did, pid, ident, write=True)
    if row.result["distribution_digest"] != body.expected_digest:
        raise HTTPException(412, "Review the exact storyboard preview and destination")
    if user.id == row.actor or not c3_reviewer.active_approver(db, tenant_id, user.id, lock=True):
        conflict("A different active approver must review the preview")
    saved = verdict(store, row, lock=True)
    if saved:
        if saved.actor != user.id or saved.result["note"] != body.note:
            conflict("An active approval already exists for this preview")
    else:
        saved = studio.append_document(store, run, QA, "preview-qa:" + row.id, {"digest": body.expected_digest, "note": body.note})
        db.commit()
    return {"receipt": saved.id, "digest": body.expected_digest}


def intake(db, user, tenant, did, pid, ident, body):
    distribution = resolve(db, user, tenant, did, pid, ident, write=True)
    binding = {"id": ident, "digest": distribution["distribution_digest"], "run_id": distribution["storyboard"]["run_id"],
               "revision": distribution["storyboard"]["revision"], "preview_sha256": distribution["preview"]["file_digest"],
               "preview_qa": distribution["preview_qa"]["receipt"]}
    return studio.intake(tenant, did, pid, body, user, db, distribution=binding)


@router.post("/{ident}/visits")
def visit(tenant_id: str, did: str, pid: str, ident: str, body: studio.Visit, user: studio.Actor, db: studio.DB):
    return intake(db, user, tenant_id, did, pid, ident, body)


@router.post("/{ident}/submissions")
def submit(tenant_id: str, did: str, pid: str, ident: str, body: studio.ContractSubmit, user: studio.Actor, db: studio.DB):
    return intake(db, user, tenant_id, did, pid, ident, body)

