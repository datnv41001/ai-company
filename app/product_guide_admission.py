"""Commission an in-house guide only from the live recipient edition of a Strategy receipt."""

import json
from datetime import timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import Depends, HTTPException
from sqlalchemy import select

from . import c3_strategy_handoff as handoff
from .database import get_db
from .knowledge_contracts import GuideProcedure, Input
from .knowledge_models import KnowledgeCommand, KnowledgeRevision, KnowledgeSnapshot
from .knowledge_store import Store, canonical, conflict, digest, missing
from .models import AuditEvent, Tenant
from .security import current_user
from .workforce_models import WorkforceBrief, WorkforceRun

RELEASE = "WF-06/product-use-guide@1"
TASK_VERSION = "amc.product-use-guide/1"
MANIFEST_VERSION = "amc.product-guide-manifest/1"


class StartGuide(Input):
    receipt_id: UUID


def _parent(db, user, tenant, document, receipt_id, *, admission):
    if db.get_bind().dialect.name != "postgresql":
        conflict("Product guides require the PostgreSQL worker pool")
    org = db.get(Tenant, tenant)
    if not org or org.mode != "inhouse":
        missing()
    view = handoff._decide(tenant, document, user, db, None)
    if (view.get("decision") or {}).get("receipt_id") != receipt_id:
        missing()
    if not view.get("work_order"):
        conflict("The Strategy work order is no longer available")
    from .c3_studio_routes import scoped

    doc, parent = scoped(db, user, tenant, document, "editor")
    store = Store(db, user, tenant, parent.client_id, parent.brand_id, write=True)
    receipt = store.get(KnowledgeCommand, receipt_id)
    data = receipt.result
    recipient_id = data["request"]["recipient_id"]
    if user.id != recipient_id and (admission or user.id != receipt.actor):
        missing()
    if (
        receipt.operation != handoff.OP
        or data["version"] != handoff.VERSION
        or receipt.snapshot_id != parent.knowledge["c3_manifest"]["id"]
        or data["scope"] != {**store.scope, "campaign_id": parent.campaign_id}
        or data["revision"] != doc.qa_revision
    ):
        conflict("Strategy handoff no longer matches its source")
    order = handoff._recipient_decision(view, receipt)["work_order"]
    if order["asset_type"] != "web_use_guide" or order["placement"] not in handoff.ASSETS["web_use_guide"][1]:
        conflict("Only an in-house use guide on an approved product page can be commissioned")
    binding = {
        "strategy_document": doc.id,
        "revision": doc.qa_revision,
        "content_digest": data["content_digest"],
        "qa_receipt": data["qa_receipt"],
        "handoff_receipt": receipt.id,
        "strategy_run": parent.id,
        "source_manifest": receipt.snapshot_id,
        "source_manifest_digest": parent.knowledge["c3_manifest"]["digest"],
        "source_release_digest": parent.knowledge["registry"]["manifest_digest"],
    }
    return store, parent, receipt, order, binding


def _projection(store, receipt, order):
    data = receipt.result
    ref = data["selected_references"][data["request"]["product_handle"]]
    source = store.get(KnowledgeRevision, ref["source_revision"])
    if source.digest != ref["source_digest"] or store.summary(source)["state"] != "approved":
        conflict("The approved procedure source has changed")
    entry = next((e for e in source.data["entries"] if e["locator"] == ref["locator"]), None)
    if not entry or not entry.get("guide_procedure"):
        return None
    claim = entry["assertion"]
    steps = GuideProcedure.model_validate(entry["guide_procedure"]).steps
    wording = " ".join([claim["wording"], *claim["qualifiers"]])
    if (
        claim["category"] != "description"
        or claim["placement"]["channel"] != order["placement"]
        or entry["excerpt"] != wording
        or wording != order["message"]
        or " ".join(steps) != claim["wording"]
    ):
        conflict("The use instructions differ from the complete released wording")
    locale = claim["placement"]["locale"]
    return {
        "product": "Hướng dẫn sử dụng" if locale == "vi-VN" else "Product use guide",
        "locale": locale,
        "objective": order["objective"],
        "audience": order["audience"],
        "channel": order["placement"],
        "order": order,
        "task_intent": {**order["brief"], "deliverable_type": "web_use_guide"},
        "procedure": {"steps": steps, "limitations": claim["qualifiers"], "source": "P1", "wording": wording},
    }


def check_guide_access(db, user, run, *, write=False):
    """Human read, edit and QA replay upstream authorization in the actual caller session."""
    brief = db.get(WorkforceBrief, run.brief_id)
    if not brief or brief.origin != "internal" or (brief.payload or {}).get("task_version") != TASK_VERSION:
        missing()
    binding = brief.payload["guide_binding"]
    store, parent, _, _, live = _parent(db, user, run.tenant_id, binding["strategy_document"], binding["handoff_receipt"], admission=False)
    ref = run.knowledge["c3_manifest"]
    snap = store.get(KnowledgeSnapshot, ref["id"])
    data = json.loads(snap.canonical)
    if (
        binding != live
        or data.get("guide_binding") != live
        or snap.digest != ref["digest"]
        or snap.digest != digest(snap.canonical)
        or (snap.brief_id, snap.campaign_id) != (brief.id, parent.campaign_id)
        or data.get("version") != MANIFEST_VERSION
        or data["projection"] != run.knowledge["c3_projection"]
    ):
        conflict("The guide no longer matches its authorized manifest")
    from .registry import pin

    if pin(db, brief, RELEASE) != run.knowledge["registry"]:
        conflict("The guide registry binding has changed")
    return data["projection"]


def visible_brief(db, user, brief):
    if (brief.payload or {}).get("task_version") != TASK_VERSION:
        return True
    run = db.scalar(select(WorkforceRun).filter_by(brief_id=brief.id, tenant_id=brief.tenant_id))
    if run:
        try:
            check_guide_access(db, user, run)
            return True
        except HTTPException as err:
            if err.status_code not in (403, 404, 409):
                raise
    return False


def start_guide(tenant_id: str, did: str, body: StartGuide, user=Depends(current_user), db=Depends(get_db)):
    from . import workforce
    from .delivery import lock_document

    store, parent, receipt, order, binding = _parent(db, user, tenant_id, did, str(body.receipt_id), admission=True)
    public = _projection(store, receipt, order)
    if public is None:
        return {"status": "hold", "reasons": ["procedure_source_required"], "task_id": None, "run_id": None, "manifest_id": None}
    task_id = str(uuid5(NAMESPACE_URL, f"amc/{TASK_VERSION}/{tenant_id}/{receipt.id}/{user.id}"))
    lock_document(db, "workforce-brief:" + task_id)
    task = db.get(WorkforceBrief, task_id)
    if task:
        existing = db.scalar(select(WorkforceRun).filter_by(brief_id=task.id, tenant_id=tenant_id))
        if not existing or check_guide_access(db, user, existing) != public:
            conflict("Guide task exists with different admission evidence")
        return {"status": existing.state, "reasons": [], "task_id": task.id, "run_id": existing.id, "manifest_id": existing.knowledge["c3_manifest"]["id"]}
    task = WorkforceBrief(
        id=task_id,
        **store.scope,
        campaign_id=parent.campaign_id,
        recipient_id=user.id,
        title=public["product"],
        origin="internal",
        payload={"internal_task": True, "task_version": TASK_VERSION, "task_intent": public["task_intent"], "guide_binding": binding},
    )
    db.add(task)
    db.flush()
    now = store.now()
    encoded = canonical(
        {
            "version": MANIFEST_VERSION,
            "scope": {**store.scope, "campaign_id": parent.campaign_id},
            "brief_id": task_id,
            "workflow": RELEASE,
            "guide_binding": binding,
            "projection": public,
        }
    )
    snap = store.insert(
        KnowledgeSnapshot,
        "restricted",
        campaign_id=parent.campaign_id,
        brief_id=task.id,
        canonical=encoded,
        digest=digest(encoded),
        snapshot_as_of=now,
        preview_created_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, subject_id=task_id, event="workforce.product_guide_commissioned"))
    terms = workforce.Start(registry_workflow=RELEASE, knowledge_manifest={"id": snap.id, "digest": snap.digest}, workflow="dynamic-v1")
    # Task, manifest, registry pin, run and audit commit as one normal enqueue; authorization adds no spend.
    run = workforce.queue(db, user, tenant_id, task_id, terms, guide=(store, snap, public))
    return {"status": run["state"], "reasons": [], "task_id": task_id, "manifest_id": snap.id, "run_id": run["id"]}
