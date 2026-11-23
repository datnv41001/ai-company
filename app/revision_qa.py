"""Evidence for one persisted client-facing revision. All callers hold the document lock or create it."""

import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select

from .models import AuditEvent, utcnow
from .workforce_evidence import RULESET, assess
from .workforce_models import WorkforceRun


def content_digest(title, preview):
    payload = json.dumps({"title": title, "preview": preview}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evaluate(db, doc, actor):
    # The reverse FK is written by the scoped worker. Arbitrary draft JSON has no authority.
    run = db.scalar(
        select(WorkforceRun).where(WorkforceRun.tenant_id == doc.tenant_id, WorkforceRun.campaign_id == doc.campaign_id, WorkforceRun.deliverable_id == doc.id)
    )
    sources = run.knowledge["sources"] if run else {}
    cited = {key for step in (run.checkpoints if run else []) if step["skill"] != "director" for key in step["output"]["source_ids"] if key in sources}
    preview = doc.content.get("client_preview", "")
    if not isinstance(preview, str) or len(preview) > 30000:
        raise HTTPException(422, "Edit the client preview to text of at most 30000 characters")
    sections = {"title": doc.title, "client_preview": preview}
    result = assess({"sections": sections, "source_ids": sorted(cited)}, sources)
    report = {
        "qa_revision": doc.qa_revision,
        "content_digest": content_digest(doc.title, preview),
        "ruleset_version": RULESET,
        "evaluated_at": utcnow().isoformat(),
        "state": "current" if cited else "source_unavailable",
        "findings": result["claims"],
    }
    doc.qa_evidence = report
    db.add(AuditEvent(tenant_id=doc.tenant_id, user_id=actor, subject_id=doc.id, event="deliverable.qa_evaluated", details=report))
    return report
