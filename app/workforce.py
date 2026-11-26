"""Brief intake, operator authorization for spending, and asset provenance."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .delivery import lock_document
from .delivery_models import ClientReview, PortalGrant, ReviewEntry
from .models import AuditEvent, Brand, Campaign, Deliverable, User
from .storyboard_editions import StoryboardEdit
from .security import current_user, require_tenant
from .workforce_gateway import CORE, EXTRA, PROMPT_VERSION
from . import workforce_authority  # noqa: F401 - install SQLite triggers on fresh schema
from .workforce_models import WorkforceBrief, WorkforceRun
from .c3_tasks import ActionIntent, SubmittedIntent, task_payload

router = APIRouter(prefix="/api/tenants/{tenant_id}/workforce", tags=["Marketing workforce"])
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]
Paragraph = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1800)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenBrief(Input):
    campaign_id: str
    recipient_id: str
    title: Short


class Source(Input):
    label: Short
    excerpt: Paragraph


class BriefData(Input):
    objective: Paragraph
    audience: Paragraph
    offer: Paragraph
    sources: list[Source] = Field(min_length=1, max_length=4)
    task_intent: SubmittedIntent | None = None


class ManifestID(Input):
    id: str = Field(min_length=36, max_length=36)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class Start(Input):
    knowledge_manifest: ManifestID | None = None
    registry_workflow: str | None = Field(default=None, min_length=1, max_length=120)
    max_parallel_nodes: Literal[1, 2] = 1
    workflow: Literal["linear", "diamond-v1", "dynamic-v1"] = "linear"
    extra_skills: list[Literal["seo", "creative", "ads", "analytics"]] = Field(default_factory=list, max_length=4)
    budget_microusd: int = Field(default=0, ge=0, le=1_000_000)


def brief_query(db, member):
    q = select(WorkforceBrief).where(WorkforceBrief.tenant_id == member.tenant_id)
    if member.role == "client_viewer":
        grant = db.get(PortalGrant, (member.tenant_id, member.user_id))
        if not grant or grant.client_id != member.client_id:
            return q.where(False)
        q = q.where(WorkforceBrief.origin == "agency", WorkforceBrief.recipient_id == member.user_id, WorkforceBrief.client_id == grant.client_id)
        if grant.brand_id:
            q = q.where(WorkforceBrief.brand_id == grant.brand_id)
        if grant.campaign_id:
            q = q.where(WorkforceBrief.campaign_id == grant.campaign_id)
    return q


def public_brief(b):
    return {"id": b.id, "title": b.title, "submitted": b.payload is not None, "campaign_id": b.campaign_id,
            **({"origin":"internal"} if b.origin == "internal" else {})}


@router.get("/briefs")
def briefs(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    member = require_tenant(db, user, tenant_id)
    return [public_brief(b) for b in db.scalars(brief_query(db, member).order_by(WorkforceBrief.created_at.desc()))]


@router.post("/briefs", status_code=201)
def open_brief(tenant_id: str, body: OpenBrief, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    campaign = db.get(Campaign, body.campaign_id)
    grant = db.get(PortalGrant, (tenant_id, body.recipient_id))
    if not campaign or campaign.tenant_id != tenant_id or not grant:
        raise HTTPException(404, "Campaign or recipient unavailable")
    brand = db.get(Brand, campaign.brand_id)
    if grant.client_id != brand.client_id or grant.brand_id not in (None, brand.id) or grant.campaign_id not in (None, campaign.id):
        raise HTTPException(404, "Campaign or recipient unavailable")
    brief = WorkforceBrief(tenant_id=tenant_id, client_id=brand.client_id, brand_id=brand.id, **body.model_dump())
    db.add(brief)
    db.flush()
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, subject_id=brief.id, event="workforce.brief_requested"))
    db.commit()
    return public_brief(brief)


@router.put("/briefs/{bid}/submission")
def submit(tenant_id: str, bid: str, body: BriefData, user: User = Depends(current_user), db: Session = Depends(get_db)):
    payload = body.model_dump(exclude_none=True)
    if isinstance(body.task_intent, ActionIntent):
        payload.update(task_payload(body.task_intent))
    return save_submission(db,user,tenant_id,bid,payload)


@router.put("/briefs/{bid}/task-submission")
def submit_task(tenant_id: str, bid: str, body: SubmittedIntent, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return save_submission(db,user,tenant_id,bid,task_payload(body))


def save_submission(db,user,tenant_id,bid,payload):
    m = require_tenant(db, user, tenant_id)
    if m.role != "client_viewer":
        raise HTTPException(404, "Brief unavailable")
    b = db.scalar(brief_query(db, m).where(WorkforceBrief.id == bid))
    if not b:
        raise HTTPException(404, "Brief unavailable")
    # Compare-and-set also protects SQLite submissions; identical network retries are safe.
    from sqlalchemy import update

    if b.payload is None:
        changed = db.execute(
            update(WorkforceBrief)
            .where(WorkforceBrief.id == bid, WorkforceBrief.payload.is_(None))
            .values(payload=payload)
            .execution_options(synchronize_session=False)
        )
        db.commit()
        if changed.rowcount:
            return {"submitted": True}
        db.refresh(b)
    if b.payload == payload:
        return {"submitted": True}
    raise HTTPException(409, "Brief already submitted")


@router.post("/briefs/{bid}/run")
def start(tenant_id: str, bid: str, body: Start, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from . import c3_boundaries, c3_marketing, storyboard_runtime
    if body.registry_workflow in storyboard_runtime.RELEASES and (body.max_parallel_nodes != 1 or body.budget_microusd != 0):
        raise HTTPException(422, "This sequential local storyboard release requires a zero provider budget")
    from .c3_projection import TASK_RELEASES
    backed = body.registry_workflow in c3_marketing.ROLES or body.registry_workflow in TASK_RELEASES
    if backed != bool(body.knowledge_manifest):
        raise HTTPException(422, "Knowledge-backed releases require an exact business knowledge manifest")
    m = require_tenant(db, user, tenant_id, "editor")
    lock_document(db, "workforce-brief:" + bid)
    b = db.scalar(brief_query(db, m).where(WorkforceBrief.id == bid))
    if not b:
        raise HTTPException(404, "Brief unavailable")
    if b.payload and "sources" not in b.payload and body.registry_workflow not in TASK_RELEASES:
        raise HTTPException(409, "Nhiệm vụ này cần quy trình Marketing và manifest yêu cầu công việc đã ghim.")
    if body.max_parallel_nodes == 2 and body.workflow != 'dynamic-v1':
        raise HTTPException(422, 'Two leases require a dynamic workflow')
    plan = CORE + [s for s in EXTRA if s in body.extra_skills]
    if body.workflow == "diamond-v1":
        if body.extra_skills:
            raise HTTPException(422, "Diamond template fixes its specialist set")
        if db.get_bind().dialect.name != "postgresql":
            raise HTTPException(409, "Diamond requires the PostgreSQL worker pool")
        plan = [*CORE, "seo"]
    if body.registry_workflow and body.workflow != 'dynamic-v1':
        raise HTTPException(422, 'Registry workflows require dynamic planning')
    required = sorted({'content', *body.extra_skills})
    if body.workflow == 'dynamic-v1':
        if db.get_bind().dialect.name != 'postgresql':
            raise HTTPException(409, 'Dynamic planning requires the PostgreSQL worker pool')
        if not body.registry_workflow and set(required) - {'content', 'seo'}:
            raise HTTPException(422, 'Dynamic catalog v1 supports Content and SEO assets')
        plan = ['director']
    prior = db.scalar(select(WorkforceRun).where(WorkforceRun.brief_id == bid, WorkforceRun.tenant_id == tenant_id))
    if prior:
        if backed and prior.knowledge.get("c3_manifest") != body.knowledge_manifest.model_dump():
            raise HTTPException(409, "Brief already queued against a different Marketing manifest")
        if body.registry_workflow:
            required = prior.knowledge.get("required_outputs", [])
            if set(body.extra_skills) - set(required):
                raise HTTPException(409, "Extra skills differ from the pinned workflow")
        same_plan = prior.knowledge.get("required_outputs") == required if body.workflow == "dynamic-v1" else prior.plan == plan
        if prior.knowledge.get('registry', {}).get('workflow') != body.registry_workflow:
            raise HTTPException(409, 'Brief already queued with different registry terms')
        if prior.knowledge.get("workflow", "linear") != body.workflow or prior.knowledge.get('max_parallel_nodes', 1) != body.max_parallel_nodes or not same_plan or prior.budget_microusd != body.budget_microusd:
            raise HTTPException(409, "Brief already queued with different terms")
        return {"id": prior.id, "state": prior.state}
    if not b.payload:
        raise HTTPException(409, "Waiting for the client's brief")
    if b.payload.get("task_intent") and body.registry_workflow not in TASK_RELEASES:
        from .campaign_planner import commissioned_brief
        _, store = c3_boundaries.context(db, user, b)
        if commissioned_brief(store, bid):
            raise HTTPException(409, "Công việc đã được giao. Hãy dùng manifest đã duyệt trong kế hoạch.")
    brand = db.get(Brand, b.brand_id)
    if not backed and not brand.product_truth.strip():
        raise HTTPException(422, "Brand Kit needs verified product facts")
    if not backed and max(len(brand.product_truth), len(brand.brand_guidelines)) > 4000:
        raise HTTPException(422, "Summarize each Brand Kit field to 4000 characters for this workflow")
    if not backed:
        facts = {"brand": {"label": brand.name, "excerpt": brand.product_truth}}
        facts.update({f"S{n}": s for n, s in enumerate(b.payload["sources"], 1)})
        knowledge = {"title": b.title, "objective":b.payload["objective"], "audience":b.payload["audience"],
                     "offer":b.payload["offer"], "brand_rules":brand.brand_guidelines,"sources":facts,"prompt_version":PROMPT_VERSION}
    if body.registry_workflow:
        from .registry import pin
        from .registry_compatibility import required_outputs
        if backed:
            store, snap, public = c3_boundaries.checked(db, user, b, body.knowledge_manifest.model_dump(), body.registry_workflow, "queue")
            if body.registry_workflow in storyboard_runtime.RELEASES:
                from .c3_order_units import fact_lines
                facts = {f["id"]:{"label":f["id"],"excerpt":" ".join(fact_lines(f,public))} for f in public["facts"]}
            elif body.registry_workflow in TASK_RELEASES:
                from .c3_releases import fact_text
                facts = {fact["id"]: {"label":fact["id"],"excerpt":fact_text(body.registry_workflow,fact,public)} for fact in public["facts"]}
            else:
                facts = {fact["id"]: {"label": fact["id"], "excerpt": c3_marketing.fact_line(fact)} for fact in public["facts"]}
            knowledge = {"title": public["product"], "objective":public["objective"], "audience":public["audience"],
                         "offer":public["product"], "brand_rules":"", "sources":facts, "prompt_version":PROMPT_VERSION,
                         "c3_manifest":body.knowledge_manifest.model_dump(), "c3_projection":public}
            if body.registry_workflow in TASK_RELEASES:
                knowledge.update(objective=public["task_intent"]["purpose"],brand_rules=public["brand_guidelines"]["guidance"],
                                 internal_task=b.origin == "internal")
                from .campaign_planner import execution_terms
                commission = None if body.registry_workflow in storyboard_runtime.RELEASES else execution_terms(store, snap, public, body.budget_microusd)
                if commission:
                    knowledge["campaign_commission"] = commission
        binding = pin(db, b, body.registry_workflow)
        manifest = db.scalar(text("select manifest from amc_ops.registry_releases where workflow=:w and digest=:d"),
                             {"w":body.registry_workflow, "d":binding["manifest_digest"]})
        required = required_outputs(manifest)
        if set(body.extra_skills) - set(required):
            raise HTTPException(422, "Extra skills differ from the selected release")
        knowledge["registry"] = binding
    if body.workflow == "dynamic-v1":
        knowledge["required_outputs"] = required
        if body.max_parallel_nodes == 2:
            knowledge["max_parallel_nodes"] = 2
    if body.workflow != "linear":
        knowledge["workflow"] = body.workflow
        knowledge["workflow_revision"] = 1
    run = WorkforceRun(
        tenant_id=tenant_id,
        client_id=b.client_id,
        brand_id=b.brand_id,
        campaign_id=b.campaign_id,
        brief_id=b.id,
        plan=plan,
        knowledge=knowledge,
        budget_microusd=body.budget_microusd,
    )
    db.add(run)
    try:
        db.flush()
        if backed:
            c3_boundaries.record(store, snap, "queue", "queue:"+run.id,
                {"run_id":run.id, "manifest_digest":snap.digest, "release_digest":binding["manifest_digest"],
                 "campaign_plan_digest":knowledge.get("campaign_commission", {}).get("plan_digest")})
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user.id,
                subject_id=run.id,
                event="workforce.queued",
                details={"skills": plan, "budget_microusd": body.budget_microusd},
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if name == "dag_requires_pool":
            raise HTTPException(409, "Enroll this agency in the worker pool first") from None
        if name == "workforce_recipient_required" or "workforce_recipient_required" in str(exc.orig):
            raise HTTPException(409, "Brief recipient access was withdrawn") from None
        raise HTTPException(409, "Brief already queued; refresh") from None
    return {"id": run.id, "state": run.state}


def display_state(run, graph):
    if run.state == "queued" and graph and any(n["status"] == "running" for n in graph["nodes"]):
        return "running"
    return run.state


@router.post("/runs/{rid}/storyboard-edition")
def edit_storyboard(tenant_id: str, rid: str, body: StoryboardEdit, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from . import c3_boundaries, storyboard_editions as editions, storyboard_runtime as runtime
    from .delivery import working_copy, save_working_revision
    from .revision_qa import content_digest
    from .registry import pin
    from .video_storyboard import json_text

    require_tenant(db, user, tenant_id, "editor")
    run = db.scalar(select(WorkforceRun).filter_by(tenant_id=tenant_id, id=rid))
    if not runtime.is_run(run) or not run.deliverable_id:
        raise HTTPException(404, "Storyboard unavailable")
    connected = None
    if body.distribution:
        from .storyboard_distribution import resolve
        connected = resolve(db, user, tenant_id, **body.distribution.model_dump(), write=True)
        if (connected["storyboard"]["run_id"], connected["storyboard"]["document_id"]) != (rid, run.deliverable_id):
            raise HTTPException(404, "Distribution unavailable for this storyboard")
    doc = working_copy(db, tenant_id, run.deliverable_id)
    if (doc.qa_revision, content_digest(doc.title, doc.content["client_preview"])) != (body.expected_qa_revision, body.expected_content_digest):
        raise HTTPException(412, "Reload the current storyboard revision")
    brief = db.get(WorkforceBrief, run.brief_id)
    ref = run.knowledge["c3_manifest"]
    release = run.knowledge["registry"]["workflow"]
    store, snap, projection = c3_boundaries.checked(db, user, brief, ref, release, "edit")
    if pin(db, brief, release) != run.knowledge["registry"]:
        raise HTTPException(409, "The storyboard binding is no longer current")
    landing = {"kind": "offline_no_landing"}
    distribution = {"kind": "offline_no_delivery", "channel": projection["channel"], "audience": projection["audience"]}
    if connected:
        source = connected["storyboard"]
        if (source["run_id"], source["document_id"], source["revision"], source["content_digest"]) != (
            rid, doc.id, doc.qa_revision, body.expected_content_digest
        ):
            raise HTTPException(412, "Distribution does not cite the baseline revision under review")
        landing = {"kind": "approved_at_baseline", **connected["landing"]}
        distribution = {"kind": connected["distribution_mode"], "id": body.distribution.distribution_id, "digest": connected["distribution_digest"]}
    try:
        before, _ = editions.checked_board(store, doc, run, projection, ref, runtime, for_qa=False)
        board = editions.apply_edits(before, body, projection, lambda variant: runtime.compose(projection, ref, variant, release=release))
        if release == runtime.RELEASE:
            from .storyboard_brief import assessment
            board["brief_fulfillment"] = assessment(projection, board)
        comparison = editions.comparison(before, board, body.mode, landing, distribution)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(409, str(exc)) from exc
    save_working_revision(db, doc, user.id, run.knowledge["title"], json_text(board))
    receipt = {
        "run_id": rid, "document_id": doc.id, "revision": doc.qa_revision, "content_digest": doc.qa_evidence["content_digest"],
        "baseline_revision": body.expected_qa_revision, "baseline_content_digest": body.expected_content_digest,
        "baseline_board_digest": editions.fingerprint(before), "board_digest": editions.fingerprint(board),
        "edits": body.model_dump(exclude_none=True), "comparison": comparison,
    }
    c3_boundaries.record(store, snap, "storyboard_edit", f"board:{doc.id}:{doc.qa_revision}", receipt)
    db.commit()
    return {"document_id": doc.id, "revision": doc.qa_revision, "content_digest": doc.qa_evidence["content_digest"], "storyboard": board, "receipt": receipt}


def display_plan(run, graph):
    if graph and graph.get("contract"):
        return ["director", *(n["skill_type"] for n in graph["contract"]["nodes"])]
    return run.plan


@router.get("/runs")
def runs(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_tenant(db, user, tenant_id)
    if m.role == "client_viewer":
        raise HTTPException(404, "Runs unavailable")
    rows = db.scalars(select(WorkforceRun).where(WorkforceRun.tenant_id == tenant_id).order_by(WorkforceRun.created_at.desc()).limit(100))
    summaries = []
    for r in rows:
        graph = None
        if r.knowledge.get("workflow") == "dynamic-v1":
            graph = db.scalar(text("select amc_ops.dag_report(:t,:r)"), {"t": tenant_id, "r": r.id})
        summaries.append({
            "id": r.id,
            "brief_id": r.brief_id,
            "title": r.knowledge["title"],
            "state": display_state(r, graph),
            "done": len(r.checkpoints),
            "skills": display_plan(r, graph),
            "workflow": r.knowledge.get("workflow", "linear"),
        })
    return summaries


def marketing_artifacts(run, doc):
    """Project staff work from frozen checkpoints and the latest editable preview from its document."""
    from . import c3_assets, c3_content_evidence, c3_order_units, c3_skill_library
    from .revision_qa import content_digest

    workflow = run.knowledge["registry"]["workflow"]
    outcomes = {step["skill"]: step["output"] for step in run.checkpoints}
    sections = c3_order_units.artifacts(workflow, run.knowledge["c3_projection"], outcomes)
    generated = sections["customer_preview"] if doc else None
    if doc and (doc.content.get("studio") or {}).get("origin") == "worker":
        from . import c3_studio
        groups = c3_studio.compose(workflow,run.knowledge["c3_projection"],outcomes)
        generated = c3_studio.preview(workflow,groups,generated)
    current = None
    bound = False
    if doc:
        body = doc.content.get("client_preview", "")
        digest = content_digest(doc.title, body)
        current = {"title": doc.title, "body": body, "revision": doc.qa_revision, "digest": digest, "document_id": doc.id}
        evidence = (doc.qa_evidence or {}).get("content_evidence") or {}
        bound = (evidence.get("version"), evidence.get("qa_revision"), evidence.get("content_digest"), evidence.get("manifest_digest")) == (
            c3_content_evidence.VERSION, doc.qa_revision, digest, run.knowledge["c3_manifest"]["digest"]
        )
    sections["customer_preview"] = {"generated": generated, "current": current}
    issues = []
    for role in c3_assets.ROLES[workflow]:
        if role not in outcomes:
            continue
        fields = outcomes[role]["sections"]
        previously_seen = {}
        for key in c3_skill_library.fields(role):
            value = c3_assets.normalized(fields.get(key, ""))
            if not value:
                issues.append({"role":role, "field":key, "reason":"missing"})
                continue
            visible = {"content": sections["buyer_copy"], "seo": sections["seo_fields"]}.get(role)
            if visible is not None and key not in visible:
                issues.append({"role":role, "field":key, "reason":"withheld"})
            if value in previously_seen:
                issues.append({"role":role, "field":key, "reason":"same_text", "other_field":previously_seen[value]})
            else:
                previously_seen[value] = key
    return {"workflow":workflow, "sections":sections, "completed_roles":list(outcomes),
            "editorial_status":"unreviewed_suggestions", "field_issues":issues,
            "evidence_coverage":{"fields":["title","client_preview"], "current_assessment":bound}}


@router.get("/runs/{rid}")
def report(tenant_id: str, rid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .c3_assets import ROLES as separated_releases
    m = require_tenant(db, user, tenant_id)
    if m.role == "client_viewer":
        raise HTTPException(404, "Run unavailable")
    run = db.scalar(select(WorkforceRun).where(WorkforceRun.tenant_id == tenant_id, WorkforceRun.id == rid))
    if not run:
        raise HTTPException(404, "Run unavailable")
    extra = {}
    if run.knowledge.get("registry", {}).get("workflow") in separated_releases:
        doc = None
        if run.deliverable_id:
            doc = db.scalar(select(Deliverable).join(Campaign, Campaign.id == Deliverable.campaign_id)
                            .join(Brand, Brand.id == Campaign.brand_id)
                            .where(Deliverable.id == run.deliverable_id, Deliverable.tenant_id == tenant_id,
                                   Campaign.tenant_id == tenant_id, Campaign.id == run.campaign_id,
                                   Brand.tenant_id == tenant_id, Brand.id == run.brand_id, Brand.client_id == run.client_id))
            if doc is None:
                raise HTTPException(404, "Run unavailable")
        extra["marketing_artifacts"] = marketing_artifacts(run, doc)
    archived = (
        db.execute(
            select(ClientReview.id, ClientReview.version, ClientReview.digest)
            .join(ReviewEntry, ReviewEntry.review_id == ClientReview.id)
            .where(ClientReview.tenant_id == tenant_id, ClientReview.deliverable_id == run.deliverable_id, ReviewEntry.kind == "approved")
            .order_by(ClientReview.version)
        )
        .mappings()
        .all()
        if run.deliverable_id
        else []
    )
    graph = db.scalar(text("select amc_ops.dag_report(:t,:r)"), {"t": tenant_id, "r": rid}) if run.knowledge.get("workflow") in ("diamond-v1", "dynamic-v1") else None
    if graph and run.knowledge.get("max_parallel_nodes") == 2:
        graph["max_parallel_nodes"] = 2
    return {
        **{
            k: getattr(run, k)
            for k in ("id", "state", "plan", "journal", "last_error", "budget_microusd", "reserved_microusd", "deliverable_id", "checkpoints")
        },
        "graph": graph,
        "registry": (graph or {}).get("registry", {"status":"legacy_v13"}),
        "plan": display_plan(run, graph),
        "state": display_state(run, graph),
        "source_registry": run.knowledge["sources"],
        **extra,
        **({"marketing_provenance": f"/api/tenants/{tenant_id}/clients/{run.client_id}/brands/{run.brand_id}"
              f"/business-workspace/marketing/manifests/{run.knowledge['c3_manifest']['id']}/provenance"}
           if m.role in ("owner", "admin") and run.knowledge.get("c3_manifest") else {}),
        "approved_assets": archived,
    }


@router.get("/runs/{rid}/wait-diagnostics")
def wait_diagnostics(tenant_id: str, rid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .scheduler_telemetry import inspect_waits
    membership = require_tenant(db,user,tenant_id)
    if membership.role not in ("owner","admin") or db.get_bind().dialect.name != "postgresql":
        raise HTTPException(404,"Diagnostics unavailable")
    snapshot = db.scalar(text("select amc_ops.wait_snapshot(:t,:r)"),{"t":tenant_id,"r":rid})
    if not snapshot:
        raise HTTPException(404,"Diagnostics unavailable")
    return inspect_waits(snapshot)
