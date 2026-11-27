"""Commission a new internal Content draft from an independently approved WF-03 Studio revision."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StringConstraints
from sqlalchemy import select

from . import c3_boundaries as boundaries, c3_evidence_review as evidence, c3_order_units, c3_projection
from .database import get_db
from .knowledge_contracts import Input, Ref
from .knowledge_models import KnowledgeCommand, KnowledgeRevision
from .knowledge_store import Store, canonical, conflict, digest, missing, stamp
from .models import Membership, User
from .c3_reviewer import active_approver
from .revision_qa import content_digest
from .security import current_user
from .workforce_models import WorkforceBrief


router = APIRouter()
VERSION = "amc.internal-strategy-handoff/1"
OP = "c3_strategy_decision"
OPTIONS = {
    "explain_use": ("Explain the product in use", "A concrete use case leaves other buying situations untested."),
    "explain_terms": ("Clarify the offer before purchase", "Commercial clarity may leave product use unexplained."),
}
# These are specifications for *new* drafts. Neither an existing creative nor its rights transfer.
ASSETS = {
    "web_use_guide": ("explain_use", ("web", "owned product page"), "Product-page use guide", "Explain a use case on the product page"),
    "web_terms_panel": ("explain_terms", ("web", "owned product page"), "Product-page terms panel", "Clarify product information before purchase"),
    "counter_use_card": ("explain_use", ("owned counter card",), "Counter demonstration card", "Help staff explain the use case at the counter"),
    "counter_terms_card": ("explain_terms", ("owned counter card",), "Counter information card", "Clarify product information at the counter"),
}
Handle = Annotated[str, Field(pattern=r"^F[1-9][0-9]?$")]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class Decision(Input):
    expected_revision: Annotated[int, Field(ge=1, strict=True)]
    expected_content_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    qualification_revision: Ref
    option: Literal["explain_use", "explain_terms"]
    asset_type: Literal["web_use_guide", "web_terms_panel", "counter_use_card", "counter_terms_card"] | None = None
    evidence_state: Literal["supported", "conflicting", "insufficient", "needs_clarification"]
    support_handle: Handle | None = None
    contrary_handle: Handle | None = None
    product_handle: Handle | None = None
    recipient_id: Ref | None = None
    observation_kind: Literal["observed_behaviour", "buyer_statement", "hypothesis"] = "hypothesis"
    observation_excerpt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1800)] | None = None
    interpretation: Note
    buyer_persona: Note
    buying_situation: Note
    sample_limit: Note


def available(db, run):
    return (run.knowledge["registry"]["workflow"] == c3_projection.TASK_RESEARCH and
            bool(boundaries.internal_author(db.get(WorkforceBrief, run.brief_id))))


def evaluate(body, references, projection, strategy):
    """Only exact released product wording can enter a new draft. Interpretation remains editorial."""
    reasons = []
    if body.evidence_state != "supported":
        reasons.append({"conflicting": "contradictory_evidence", "insufficient": "missing_evidence",
                        "needs_clarification": "clarify_commission"}[body.evidence_state])
    if body.contrary_handle and "contradictory_evidence" not in reasons:
        reasons.append("conflicting_source")
    if not body.support_handle:
        reasons.append("missing_observation")
    else:
        support = references[body.support_handle]
        if (support["category"] != "description" or not support["research_spans"] or body.observation_kind == "hypothesis"
                or not body.observation_excerpt or body.observation_excerpt not in support["excerpt"]):
            reasons.append("observation_unverified")
    if not body.product_handle:
        reasons.append("missing_product_fact")
    elif (body.product_handle in (body.support_handle, body.contrary_handle)
          or references[body.product_handle]["category"] != "description"
          or not references[body.product_handle]["positioning_spans"] or references[body.product_handle]["research_spans"]
          or body.support_handle and _source_entry(references[body.product_handle]) == _source_entry(references[body.support_handle])):
        reasons.append("source_purpose_mismatch")
    if body.buyer_persona.casefold() != projection["audience"].strip().casefold():
        reasons.append("buyer_scope_mismatch")
    if body.asset_type:
        asset_option, places, label, purpose = ASSETS[body.asset_type]
        if body.option != asset_option:
            reasons.append("asset_option_mismatch")
        if projection["channel"] not in places:
            reasons.append("asset_placement_mismatch")
    else:
        reasons.append("asset_required")
    if strategy["channel_choice"].strip().casefold() != projection["channel"].strip().casefold():
        reasons.append("strategy_placement_mismatch")
    if not body.recipient_id:
        reasons.append("recipient_required")
    if reasons:
        return reasons, None
    return [], {
        "recipient": "Content lead", "asset_type": body.asset_type, "asset": label, "purpose": purpose,
        "placement": projection["channel"], "option": body.option, "objective": projection["objective"],
        "audience": projection["audience"], "buyer_persona": body.buyer_persona,
        "message": references[body.product_handle]["complete_wording"],
        "sources": {"observation": references[body.support_handle], "product": references[body.product_handle]},
        "claim_limits": [body.sample_limit, "Use the complete product declaration with its qualifiers.",
                         "Buyer interpretation is limited to the recorded situation."],
        "approval": "Internal drafting only. A new asset requires its own independent QA and channel approval.",
    }


def _source_entry(reference):
    return reference["source_revision"], reference["locator"]


def _references(store, snap, doc, run, proof):
    report = evidence.current_report(store, snap, doc, run, proof["content_digest"], include_sources=True)
    if digest(canonical(report)) != proof["content_gate_digest"]:
        conflict("Reload the signed evidence assessment for this revision")
    reviewed_fields = {"studio.research.buyer_problem": {}, "studio.strategy.positioning": {}}
    for span in report["statements"]:
        if span["field"] in reviewed_fields and span["outcome"] in ("verified", "reviewed"):
            for handle in span["handles"]:
                reviewed_fields[span["field"]].setdefault(handle, []).append(span["id"])
    facts = run.knowledge["c3_projection"]
    result = {}
    for fact in facts["facts"]:
        handle = fact["id"]
        ref = report["references"][handle]
        source = store.get(KnowledgeRevision, ref["source_revision"])
        entry = next((e for e in source.data["entries"] if e["locator"] == ref["locator"]), None)
        if entry is None:
            conflict("The bound source excerpt cannot be reconstructed")
        result[handle] = dict(handle=handle, **ref, excerpt=entry["excerpt"], publisher=source.data["publisher"], recorded_at=stamp(source.created_at),
                              effective_from=source.data.get("valid_from"), effective_until=source.data.get("valid_until"),
                              research_spans=reviewed_fields["studio.research.buyer_problem"].get(handle, []),
                              positioning_spans=reviewed_fields["studio.strategy.positioning"].get(handle, []),
                              complete_wording=" ".join(c3_order_units.fact_lines(fact, facts)),
                              permitted_use="internal strategy review within the pinned placement")
    return result


def _base(doc, run, store):
    projection = run.knowledge["c3_projection"]
    bundle = doc.content.get("studio") or {}
    groups = bundle.get("groups", {})
    checkpoints = {c["skill"]: c["output"].get("sections", {}) for c in run.checkpoints if c.get("skill") in ("research", "strategy")}
    return {
        "version": VERSION, "status": "needs_review", "revision": doc.qa_revision,
        "content_digest": content_digest(doc.title, doc.content.get("client_preview", "")),
        "can_decide": False, "reasons": [], "next_owner": "Studio editor and independent QA",
        "internal_concept": "Prepare an internal outline of the buyer situation and questions for review.",
        "permitted_product_wording": [], "references": [], "qualifications": [], "recipients": [], "decision": None, "work_order": None,
        "audience_mode": "reviewer",
        "research": groups.get("research", {}), "strategy": groups.get("strategy", {}),
        "audience": projection["audience"], "placement": projection["channel"],
        "scope": {**store.scope, "campaign_id": run.campaign_id},
        "options": [dict(id=k, label=v[0], tradeoff=v[1]) for k, v in OPTIONS.items()],
        "assets": [dict(id=k, option=o, placement=p, label=label, purpose=use)
                   for k, (o, places, label, use) in ASSETS.items() for p in places if p == projection["channel"]],
        "measurement_status": "approved_definition_only" if projection.get("measurement_contract") else "planned_only",
        "measurement": {"pinned_kpi": projection.get("kpi"),
            "studio_fields": groups.get("measurement", {}), "execution_authorized": False},
        "provenance": {"brief_id": run.brief_id, "run_id": run.id, "document_id": doc.id,
                       "manifest": run.knowledge["c3_manifest"], "release": run.knowledge["registry"]["manifest_digest"],
                       "worker_proposals": checkpoints, "last_editor_id": doc.last_editor_id},
    }


def _hold(view, reason, owner):
    view.update(status="hold", reasons=[reason], next_owner=owner, can_decide=False, work_order=None)
    return view


def _limited(view):
    # The downstream commission includes only accepted product copy and draft instructions.
    # Research material, qualification details, raw model output and other staff's identity stay upstream.
    return {**view, "audience_mode": "recipient", "research": {}, "strategy": {}, "options": [], "assets": [],
            "references": [], "qualifications": [], "recipients": [], "scope": {}, "provenance": {},
            "measurement": {"execution_authorized": False}}


def _recipient_decision(view, receipt):
    view = _limited(view)
    _present_decision(view, receipt)
    view["decision"] = {"receipt_id": receipt.id, "at": stamp(receipt.effective_at)}
    if view["work_order"]:
        order = dict(view["work_order"])
        order.pop("sources")
        view["work_order"] = order
    return view


def _decide(tenant, did, user, db, body):
    # Same lock order as Studio: document, knowledge scope, manifest dependencies, reviewers.
    from .c3_studio_routes import scoped
    doc, run = scoped(db, user, tenant, did, "admin" if body else "editor")
    if not available(db, run):
        missing()
    brief = db.get(WorkforceBrief, run.brief_id)
    store = Store(db, user, tenant, run.client_id, run.brand_id, write=body is not None)
    view = _base(doc, run, store)
    if body and (view["revision"], view["content_digest"]) != (body.expected_revision, body.expected_content_digest):
        raise HTTPException(412, "The reviewed Studio revision changed")
    authors = {doc.created_by, doc.last_editor_id, boundaries.internal_author(brief)}
    independent = user.id not in authors
    if not store.approver or not independent:
        if body:
            raise HTTPException(403, "An independent current approver is required")
        return _hold(_limited(view), "independent_reviewer_required", "Independent Marketing reviewer")
    if (not doc.content.get("studio") or doc.status != "approved" or doc.qa_approved_revision != doc.qa_revision
            or doc.qa_approved_digest != view["content_digest"]):
        if body:
            conflict("Save and obtain independent QA for the current Studio revision first")
        return _hold(_limited(view), "save_and_approve", "Studio editor and independent QA")
    key = "strategy:" + digest(canonical([VERSION, doc.id, doc.qa_revision]))
    prior = db.scalar(store.query(KnowledgeCommand).filter_by(snapshot_id=run.knowledge["c3_manifest"]["id"], operation=OP, key=key))
    recipient_id = prior.result["request"].get("recipient_id") if prior else None
    if prior and not body and user.id not in (prior.actor, recipient_id):
        return _hold(_limited(view), "recipient_only", "Assigned Content lead")
    try:
        # Delivering a stored order is a live authorization boundary even on GET.
        # Use the existing lock sequence for delivery; replay never appends a QA decision.
        store, snap, proof = boundaries.boundary(db, user, doc, view["content_digest"], "replay_qa", inspect_only=not body and not prior)
    except HTTPException as err:
        if body or err.status_code not in (403, 404, 409):
            raise
        return _hold(_limited(view), "current_authority_required", "Knowledge owner and independent QA")
    view["provenance"].update(studio_approvals=proof["studio_approvals"], final_reviewer=doc.reviewed_by,
                              final_qa_digest=digest(canonical(proof)))
    prefix = boundaries.decision_key(run.id, doc.qa_revision, view["content_digest"])
    approvals = store.query(KnowledgeCommand).filter_by(snapshot_id=snap.id, operation="c3_qa", actor=doc.reviewed_by)
    qa_receipt = db.scalar(approvals.where((KnowledgeCommand.key == prefix) |
                      KnowledgeCommand.key.startswith(prefix + ":")).order_by(KnowledgeCommand.effective_at.desc()).limit(1))
    if qa_receipt is None or qa_receipt.result != proof:
        if body:
            conflict("The final QA receipt changed")
        return _hold(_limited(view), "current_authority_required", "Independent Marketing reviewer")
    view["provenance"]["qa_receipt"] = qa_receipt.id
    if prior:
        if body and (user.id != prior.actor or body.model_dump() != prior.result["request"]):
            conflict("This revision already has a different editorial decision. Save a new Studio revision.")
        try:
            evidence.approved_mandate(store, prior.result["request"]["qualification_revision"], prior.actor,
                                      "unclassified", lock=True)
        except HTTPException as err:
            if body or err.status_code not in (404, 409):
                raise
            return _hold(_limited(view), "qualification_withdrawn", "Knowledge owner and qualified reviewer")
        if recipient_id and not active_approver(db, tenant, recipient_id, lock=True):
            if body:
                conflict("The assigned recipient no longer has access to this restricted commission")
            return _hold(_limited(view), "recipient_authority_required", "Independent Marketing reviewer")
        if prior.result["qa_receipt"] != qa_receipt.id:
            if body:
                conflict("The QA decision changed. Save and review a fresh Studio revision.")
            return _hold(_limited(view), "current_authority_required", "Independent Marketing reviewer")
        if user.id == recipient_id:
            return _recipient_decision(view, prior)
        view["references"] = list(_references(store, snap, doc, run, proof).values())
        return _present_decision(view, prior)
    if body is None:
        for row in db.scalars(store.query(KnowledgeRevision).filter_by(kind="qualification")):
            if row.data["approver_id"] != user.id or row.data["category"] != "unclassified":
                continue
            try:
                evidence.approved_mandate(store, row.id, user.id, "unclassified")
            except HTTPException as err:
                if err.status_code not in (403, 404, 409):
                    raise
                continue
            view["qualifications"].append({"id": row.id, "category": "unclassified"})
        if not view["qualifications"]:
            return _hold(_limited(view), "qualified_decision_required", "Qualified Marketing reviewer")
        view["references"] = list(_references(store, snap, doc, run, proof).values())
        members = select(Membership).filter_by(tenant_id=tenant, client_id=None).where(Membership.role.in_(("admin", "owner")))
        view["recipients"] = [{"id": member.user_id, "role": member.role} for member in db.scalars(members.order_by(Membership.user_id))
                              if member.user_id not in authors | {user.id}]
        view.update(status="needs_decision", can_decide=True, reasons=["qualified_decision_required"],
                    next_owner="Qualified Marketing reviewer")
        return view
    evidence.approved_mandate(store, body.qualification_revision, user.id, "unclassified", lock=True)
    if body.recipient_id is not None and (body.recipient_id in authors | {user.id}
            or not active_approver(db, tenant, body.recipient_id, lock=True)):
        conflict("Select a different currently authorized Content recipient within this workspace")
    references = _references(store, snap, doc, run, proof)
    view["references"] = list(references.values())
    handles = [h for h in (body.support_handle, body.contrary_handle, body.product_handle) if h]
    if any(h not in references for h in handles):
        conflict("Select evidence from this commission and revision")
    reasons, order = evaluate(body, references, run.knowledge["c3_projection"], view["strategy"])
    data = {"version": VERSION, "request": body.model_dump(), "scope": view["scope"], "placement": view["placement"],
            "provenance": view["provenance"], "qa_receipt": qa_receipt.id, "revision": doc.qa_revision,
            "content_digest": view["content_digest"], "reasons": reasons, "work_order": order,
            "selected_references": {h: references[h] for h in handles}}
    receipt = store.insert(KnowledgeCommand, "restricted", key=key, operation=OP, actor=user.id,
                           request_digest=digest(canonical(data)), result=data, snapshot_id=snap.id,
                           effective_at=store.now(), queued_at=None)
    db.commit()
    return _present_decision(view, receipt)


def _present_decision(view, receipt):
    record = receipt.result
    order = record["work_order"]
    view.update(status="draft_for_approval" if order else "hold", decision={
        **record["request"], "actor": receipt.actor, "receipt_id": receipt.id, "at": stamp(receipt.effective_at),
        "selected_references": record["selected_references"]}, can_decide=False, reasons=record["reasons"],
        work_order=order, next_owner="Content lead" if order else "Strategy editor and knowledge owner")
    view["internal_concept"] = OPTIONS[record["request"]["option"]][0]
    product = record["selected_references"].get(record["request"]["product_handle"])
    if product and product["category"] == "description" and "source_purpose_mismatch" not in record["reasons"]:
        view["permitted_product_wording"] = [product["complete_wording"]]
    return view


@router.get("/content-handoff")
def inspect(tenant_id: str, did: str, user: User = Depends(current_user), db=Depends(get_db)):
    return _decide(tenant_id, did, user, db, None)


@router.post("/content-handoff")
def decide(tenant_id: str, did: str, body: Decision, user: User = Depends(current_user), db=Depends(get_db)):
    return _decide(tenant_id, did, user, db, body)
