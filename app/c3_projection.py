"""Immutable C2 business knowledge projections for two explicitly reviewed Marketing releases."""

import json
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select

from . import business_workspace as ws, c3_clarification, c3_marketing as marketing, knowledge_models as m
from . import measurement_integrity, storyboard_runtime, video_storyboard as video
from .business_knowledge import resolved
from .commercial_scope import same_placement
from .company_objectives import check_company_reference
from .knowledge_authority import eligible
from .knowledge_contracts import Amount, Command, Currency, Name, Ref, Target
from .knowledge_store import Store, aware, canonical, conflict, digest, missing, restrictive, stamp
from .knowledge_target import describe
from .workforce_models import WorkforceBrief
from .c3_tasks import ACTION_VERSION, COMMISSION_VERSION, INTENT_TYPES, TASK_VERSION

router = APIRouter(prefix=ws.BASE + ws.BRAND + "/marketing", tags=["Knowledge-backed Marketing"])
VERSION = "amc.marketing-manifest/1"
TASK_MANIFEST = "amc.marketing-manifest/2"
TASK_RESEARCH = "WF-03/research-strategy-draft@3"
TASK_LANDING = "WF-13/landing-seo-draft@6"
TASK_RELEASES = (TASK_RESEARCH, TASK_LANDING, *storyboard_runtime.RELEASES)
GENERIC_UNIT = "Approve a price or applicability revision with an exact selling unit, such as machine or participant"


class Selection(Command):
    workspace_brief_id: Ref
    target: Target
    workflow: Literal[marketing.RESEARCH, marketing.LANDING, TASK_RESEARCH, TASK_LANDING, video.RELEASE, storyboard_runtime.RELEASE]
    market: Ref
    kpi: Ref
    claims: Annotated[list[Ref], Field(min_length=1, max_length=12)]
    locale: Name
    region: Name
    channel: Name
    currency: Currency | None = None
    quantity: Amount | None = None
    guidelines: Ref | None = Field(default=None, exclude_if=lambda value: value is None)
    ttl_seconds: Annotated[int, Field(ge=1, le=900)] = 600


def corporate_profiles(workspace, pins):
    company, brand = workspace.profiles()
    if not company or not brand or (company.revision, brand.revision) != (pins["company_revision"], pins["brand_revision"]):
        conflict("Update company and brand profiles, then save a new internal brief against both current revisions")
    fields = ws.resolved(company, brand)
    if ws.completion(fields)["missing"]:
        conflict("Complete name, offer, audience and goal in the company or brand profile, then save the brief")
    return company, brand


def check_delivery_capacity(workflow, public):
    # The existing delivery API accepts 30,000 characters. Reserve the validated
    # maxima for both specialist checkpoints so a long source cannot strand a paid or leased job.
    fixed = len(marketing.render(workflow, public, {})["body"])
    checkpoint_max = sum(
        sum(len(marketing.LABELS[k]) + 3 + 200 for k in marketing.FIELDS[role]) + 64
        for role in marketing.ROLES[workflow]
    )
    if fixed + checkpoint_max > 30_000:
        conflict("Select fewer approved claims so every qualifier fits in one deliverable")


def materialize(s, workspace, pins, options, at):
    company, brand = corporate_profiles(workspace, pins)
    selections = pins.get("selections", {})
    if not {"product", "audience", "objective"} <= set(selections) or set(selections) - {"product", "audience", "objective", "kpi"}:
        conflict("Select a product or variant, audience and campaign objective in the internal brief")
    deps, claims = resolved(s, options["claims"], at)
    if len(set(options["claims"])) != len(options["claims"]):
        conflict("Select distinct claim revisions")

    def select_row(id_, kinds):
        row = s.get(m.KnowledgeRevision, id_)
        if row.kind not in kinds or row.visibility == "restricted":
            conflict("A selected field is outside its allowed kind or visibility")
        eligible(s, row, at, deps)
        return row

    selected = {slot: select_row(entry["id"], ws.brief_knowledge.KINDS[slot]) for slot, entry in selections.items()}
    if any(row.digest != selections[k]["digest"] for k, row in selected.items()):
        conflict("Internal brief selection changed")
    item, audience, objective = (selected[k] for k in ("product", "audience", "objective"))
    product = select_row(item.data["product"], ("product", "service")) if item.kind == "variant" else item
    market = select_row(options["market"], ("market",))
    kpi = select_row(options["kpi"], ("kpi",))
    if "kpi" in selected and selected["kpi"].id != kpi.id:
        conflict("Selected KPI differs from the immutable measurement revision in the internal brief")
    if kpi.data.get("measurement") and ("kpi" not in selected or options["workflow"] not in TASK_RELEASES):
        conflict("Pin this KPI in a new internal brief and select a task-aware Marketing workflow")
    if options["locale"] not in market.data["locales"] or audience.data.get("market") not in (None, market.id):
        conflict("Locale and audience must match the selected market")
    if objective.data.get("level") != "campaign" or objective.data.get("campaign_id") != options["target"]["campaign_id"] or kpi.data.get("objective") != objective.id:
        conflict("Select an approved objective and KPI for this exact campaign")
    parent = select_row(objective.data["parent"], ("objective",))
    if parent.data["level"] != "brand" or not parent.data.get("company_parent"):
        conflict("Attach the brand objective to a current shared company objective")
    root = check_company_reference(s, parent.data["company_parent"], require_approved=True)
    placement = dict(product=product.id, variant=item.id if item.kind == "variant" else None, market=market.id,
                     **{k:options[k] for k in ("locale", "region", "channel")})
    facts = []
    for i, entry in enumerate(claims, 1):
        if not same_placement(placement, entry["placement"]):
            conflict("Claim differs from the exact product, variant, market, locale, region or channel")
        if entry.get("price") and (entry["price"]["currency"] != options["currency"] or entry["quantity"] != options["quantity"]):
            conflict("Select the exact approved currency and quote quantity")
        facts.append({"id": f"F{i}", **{k:entry[k] for k in ("wording","qualifiers","category","price","quantity","applicability") if k in entry}})
    # Raw profile prose, authors, source titles/locators, documents and restricted dependencies never enter model inputs.
    public = {
        "company": company.payload.get("name", {}).get("value") or s.brand.name,
        "brand": ws.resolved(company, brand)["name"]["value"], "product": item.data["name"],
        "sku": item.data.get("sku"), "market": market.data["name"], "audience": audience.data["name"],
        "objective": objective.data["name"], "kpi": " · ".join(kpi.data[k] for k in ("name","unit","window","method")),
        **{k:options[k] for k in ("locale","region","channel")}, "facts": facts,
        "hypotheses": [audience.data["description"]],
        "gaps": ["Kiểm chứng nhu cầu với khách hàng trong thị trường đã chọn.", "Xác minh số liệu nền và kết quả bằng dữ liệu đo thực tế."],
    }
    task_pins = {}
    if options["workflow"] in TASK_RELEASES:
        if not options.get("guidelines"):
            conflict("Chọn bản hướng dẫn thương hiệu công khai đã được duyệt để ghim giọng văn và giới hạn.")
        rule = select_row(options["guidelines"], ("guidelines",))
        if rule.visibility != "public":
            conflict("Chỉ dùng hướng dẫn thương hiệu được phép đưa vào nội dung Marketing.")
        brief = s.db.get(WorkforceBrief, options["target"]["brief_id"])
        intent_data = brief.payload.get("task_intent") if brief and brief.payload else None
        if not intent_data:
            conflict("Yêu cầu người giao việc gửi brief mới có mục đích, phạm vi, đầu ra và tiêu chí chấp nhận.")
        version = brief.payload.get("task_version", TASK_VERSION)
        if version not in INTENT_TYPES:
            conflict("Phiên bản yêu cầu công việc chưa được hỗ trợ.")
        intent = INTENT_TYPES[version].model_validate(intent_data).model_dump(exclude_none=True)
        expected_kind = "marketing_strategy" if options["workflow"] == TASK_RESEARCH else "landing_page"
        if options["workflow"] in storyboard_runtime.RELEASES:
            expected_kind = "video_storyboard"
        if intent["deliverable_type"] != expected_kind:
            conflict("Loại bản giao của brief khác quy trình đã chọn. Chọn quy trình đúng hoặc làm rõ yêu cầu.")
        labels = {"audience":"nhóm khách hàng", "product":"sản phẩm", "channel":"kênh", "region":"địa bàn", "locale":"ngôn ngữ"}
        def normalize(value):
            return " ".join(value.split()).casefold()
        disagreements = [label for k,label in labels.items() if normalize(intent[k]) != normalize(public[k])]
        if disagreements:
            conflict("Brief và tri thức đã duyệt khác nhau về " + ", ".join(disagreements) +
                     ". Đối chiếu với người giao việc rồi chọn đúng dữ liệu hoặc gửi brief mới.")
        measurement = measurement_integrity.bind(kpi)
        if measurement:
            if intent.get("buyer_action") != "appointment":
                conflict("This measurement contract requires an approved appointment brief")
            public["measurement_contract"] = measurement
        public["task_intent"] = intent
        public["brand_guidelines"] = {"revision":rule.revision,"digest":rule.digest,
                                      "guidance":rule.data["guidance"],"tone":rule.data.get("tone"),
                                      "prohibited_claims":rule.data.get("prohibited_claims",[])}
        task_pins = {"guidelines":[rule.id,rule.digest], "task":[brief.id,version,digest(canonical(intent))]}
    private = {"company": [company.id, company.revision], "brand": [brand.id, brand.revision],
               "company_objective": [root.revision_id, root.digest], "dependencies": {id_:row.digest for id_,row in deps.items()}, **task_pins}
    if options["workflow"] in storyboard_runtime.RELEASES:
        try:
            video.concept(public)
        except ValueError as exc:
            conflict(str(exc))
    elif options["workflow"] in TASK_RELEASES:
        from .c3_releases import check_capacity
        check_capacity(options["workflow"], public)
    else:
        check_delivery_capacity(options["workflow"], public)
    return public, private, deps


def resolve_brief(workspace, key):
    row = workspace.db.scalar(workspace.owned_briefs().where(ws.Record.id == key))
    if not row:
        missing()
    return {k:row.payload[k] for k in ("company_revision","brand_revision","selections") if k in row.payload}


def store(workspace, write):
    return Store(workspace.db, workspace.user, workspace.tenant, workspace.client, workspace.brand, write=write)


@router.get("/choices")
def choices(kind: Literal["brief", "market", "kpi", "claim", "guidelines"], offset: int = Query(0, ge=0), workspace=Depends(ws.reader)):
    from .claim_desk import display
    s = store(workspace, False)
    size = 30
    if kind == "brief":
        stmt = select(WorkforceBrief).filter_by(**s.scope).where(WorkforceBrief.payload.is_not(None)).order_by(WorkforceBrief.id)
        rows = list(s.db.scalars(stmt.offset(offset).limit(size + 1)))
        items = [{"id":row.id,"label":row.title,"campaign_id":row.campaign_id,
                  "origin":row.origin,"deliverable_type":(row.payload.get("task_intent") or {}).get("deliverable_type")} for row in rows[:size]]
    else:
        stmt = s.query(m.KnowledgeRevision).filter_by(kind=kind).where(m.KnowledgeRevision.visibility != "restricted").order_by(m.KnowledgeRevision.id)
        rows = list(s.db.scalars(stmt.offset(offset).limit(size + 1)))
        items = []
        for row in rows[:size]:
            if s.summary(row)["state"] != "approved":
                continue
            if kind == "claim":
                published = display(s, row)
                if published:
                    items.append({"id":row.id, "label":published["wording"], "scope":published["placement"],
                                  "qualifiers":published["qualifiers"], "currency":(published.get("price") or {}).get("currency"),
                                  "quantity":published.get("quantity")})
            elif kind == "guidelines":
                if row.visibility == "public":
                    items.append({"id":row.id,"label":f"{row.subject} · v{row.revision}"})
            else:
                items.append({"id":row.id,"label":row.data["name"],"locales":row.data.get("locales",[])})
    return {"items":items, "next_offset":offset+size if len(rows)>size else None}


def build(s, workspace, body):
    at = s.now()
    target = describe(s, body.target, lock=True)
    if not target["submitted"]:
        conflict("Ask the selected recipient to submit the campaign brief")
    pins = resolve_brief(workspace, body.workspace_brief_id)
    legacy = body.workflow not in TASK_RELEASES
    target_brief = s.db.get(WorkforceBrief, body.target.brief_id) if legacy else None
    action_task = target_brief and (target_brief.payload or {}).get("task_version") in (ACTION_VERSION, COMMISSION_VERSION)
    if legacy and (body.guidelines or target["kind"] == "internal_task" or action_task):
        conflict("Chọn quy trình hiểu yêu cầu công việc để dùng nhiệm vụ nội bộ hoặc hướng dẫn thương hiệu.")
    options = body.model_dump(mode="json", exclude={"key","ttl_seconds"} | ({"guidelines"} if legacy else set()))
    public, private, deps = materialize(s, workspace, pins, options, at)
    if body.workflow in storyboard_runtime.RELEASES:
        if target["kind"] == "internal_task":
            conflict("This storyboard release is available for agency briefs")
        roles = {"storyboard":{"product":public["product"],"fact_handles":[f["id"] for f in public["facts"]],"rights":video.RIGHTS}}
        if body.workflow == storyboard_runtime.RELEASE:
            roles["content"] = {"product":public["product"], "audience":public["audience"], "task_digest":digest(canonical(public["task_intent"])),
                                "fact_handles":[f["id"] for f in public["facts"]]}
    elif legacy:
        roles = {r:marketing.role_view(r,public) for r in ("director", *marketing.ROLES[body.workflow])}
    else:
        from .c3_releases import WORKFLOWS, role_view
        roles = {r:role_view(body.workflow,r,public) for r in ("director",*WORKFLOWS[body.workflow])}
    payload = {"version":VERSION if legacy else TASK_MANIFEST, "as_of": stamp(at), "scope":s.scope, "target":target, "options":options,
               "brief_pins":pins, "pins":private, "projection":public, "roles":roles}
    return payload, deps, at


@router.post("/readiness")
def readiness(body: Selection, workspace=Depends(ws.writer)):
    s = store(workspace, True)
    try:
        build(s, workspace, body)
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        result = {"status":"needs_input", "guidance":[exc.detail]}
        generic_unit = exc.detail == GENERIC_UNIT
        if body.workflow in TASK_RELEASES and (generic_unit or (s.approver and exc.detail == "Revision lacks current approved authority")):
            result["clarifications"] = c3_clarification.issues(s, body.claims)
        return result
    return {"status":"ready", "guidance":[]}


@router.post("/clarifications/propose", status_code=201)
def propose_unit(selection: Selection, correction: c3_clarification.Proposal, workspace=Depends(ws.writer)):
    s = store(workspace, True)
    describe(s, selection.target, lock=True)
    resolve_brief(workspace, selection.workspace_brief_id)

    def check_selection():
        try:
            build(s, workspace, selection)
        except HTTPException as exc:
            if exc.status_code == 409 and exc.detail == GENERIC_UNIT:
                return
            raise
        conflict("Nhiệm vụ đã sẵn sàng. Kiểm tra lại thẻ giá cần sửa.")

    return c3_clarification.propose(s, correction, selection, check_selection)


@router.post("/clarifications/approve")
def approve_unit(decision: c3_clarification.Decision, workspace=Depends(ws.writer)):
    s = store(workspace, True)
    return c3_clarification.approve(s, decision)


@router.get("/clarifications")
def corrections(workspace_brief_id: Ref | None = None, offset: int = Query(0,ge=0), workspace=Depends(ws.reader)):
    if workspace_brief_id:
        resolve_brief(workspace, workspace_brief_id)
    return c3_clarification.inbox(store(workspace,False),offset,workspace_brief_id)


@router.post("/manifests", status_code=201)
def create(body: Selection, workspace=Depends(ws.writer)):
    s = store(workspace, True)

    def save(_):
        payload, deps, at = build(s, workspace, body)
        encoded = canonical(payload)
        visibility = restrictive("internal", *(r.visibility for r in deps.values()))
        snap = s.insert(m.KnowledgeSnapshot, visibility, canonical=encoded, digest=digest(encoded),
                        snapshot_as_of=at, preview_created_at=at, expires_at=at+timedelta(seconds=body.ttl_seconds),
                        campaign_id=body.target.campaign_id, brief_id=body.target.brief_id)
        for row in deps.values():
            s.insert(m.KnowledgeDependency, visibility, snapshot_id=snap.id, revision_id=row.id)
        return view(snap, payload), visibility, snap.id

    return s.command("marketing_manifest", body, save)


def view(snap, payload):
    return {"id":snap.id, "digest":snap.digest, "workflow":payload["options"]["workflow"], "version":payload["version"],
            "snapshot_as_of":stamp(snap.snapshot_as_of), "expires_at":stamp(snap.expires_at), "projection":payload["projection"]}


def unpack(s, id_):
    snap = s.get(m.KnowledgeSnapshot, id_)
    data = json.loads(snap.canonical)
    if data["version"] not in (VERSION,TASK_MANIFEST):
        missing()
    if digest(snap.canonical) != snap.digest or data["scope"] != s.scope:
        conflict("Manifest integrity differs")
    return snap, data


@router.get("/manifests/{manifest_id}")
def historical(manifest_id: str, workspace=Depends(ws.reader)):
    snap, data = unpack(store(workspace, False), manifest_id)
    return view(snap, data)


@router.get("/manifests/{manifest_id}/provenance")
def provenance(manifest_id: str, workspace=Depends(ws.reader)):
    """An authorized reviewer may trace a public handle back to its pinned private locator."""
    s = store(workspace, False)
    if not s.approver:
        missing()
    snap, data = unpack(s, manifest_id)
    pins = data["pins"]["dependencies"]
    entries = []
    for public, rid in zip(data["projection"]["facts"], sorted(data["options"]["claims"]), strict=True):
        claim = s.get(m.KnowledgeRevision, rid)
        bound = s.get(m.KnowledgeRevision, claim.data["binding"])
        source = s.get(m.KnowledgeRevision, bound.data["source"])
        if any(pins.get(row.id) != row.digest for row in (claim, bound, source)):
            conflict("The historical evidence chain differs from the recorded manifest")
        entries.append({"handle":public["id"], "claim_revision":claim.id, "binding_revision":bound.id,
                        "source_revision":source.id, "source_digest":source.digest, "document":source.data["document"],
                        "locator":bound.data["locator"]})
    return {"manifest_digest":snap.digest, "entries":entries}


def recheck(s, workspace, id_, expected, workflow, brief, stage, *, lock_target=True):
    snap, payload = unpack(s, id_)
    opts = payload["options"]
    if snap.digest != expected or opts["workflow"] != workflow or (snap.campaign_id, snap.brief_id) != (brief.campaign_id, brief.id):
        conflict("Manifest does not match this workflow and campaign brief")
    target = describe(s, Target.model_validate(opts["target"]), lock=lock_target)
    at = s.now()
    if target != payload["target"] or not target["submitted"] or (stage == "queue" and at >= aware(snap.expires_at)):
        conflict("Campaign, recipient, brief or queue expiry changed")
    public, private, _ = materialize(s, workspace, payload["brief_pins"], opts, at)
    if public != payload["projection"] or private != payload["pins"]:
        conflict("Knowledge dependencies changed. Prepare a new manifest.")
    return snap, public
