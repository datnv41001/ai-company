"""Scoped campaign plans. Each immutable proposal pins the same approved inputs used by Workforce."""

import json
from types import SimpleNamespace
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import c3_customer_assets, c3_projection, campaign_channels, workforce
from .c3_studio_routes import asset_digest, signoffs
from .business_workspace import Workspace
from .database import get_db
from .knowledge_contracts import Input, Key, Name, Ref
from .knowledge_models import KnowledgeCommand, KnowledgeSnapshot
from .knowledge_store import Store, conflict, missing
from .models import Brand, Campaign, Deliverable, User, new_id
from .revision_qa import content_digest
from .security import current_user, require_tenant
from .workforce_models import WorkforceBrief, WorkforceRun
from .campaign_planner_pack import KINDS, compose_plan

router = APIRouter(prefix="/api/tenants/{tenant_id}/campaigns/{campaign_id}/engine", tags=["Campaign planner"])


class Proposal(Input):
    key: Key
    expected_revision: Annotated[int, Field(ge=0)]
    manifest_ids: Annotated[list[Ref], Field(min_length=1, max_length=2)]
    budget_vnd: Annotated[int, Field(strict=True, ge=0, le=1_000_000_000)]
    ai_budget_microusd_per_run: Annotated[int, Field(strict=True, ge=0, le=1_000_000)] = 10000
    duration_days: Annotated[int, Field(strict=True, ge=1, le=180)]
    channels: Annotated[list[Name], Field(min_length=1, max_length=4)] | None = None
    target_outcome: Name | None = None
    secondary_rfq: bool = False
    optimization_basis: Annotated[str, Field(min_length=1, max_length=600)] | None = None


class Approval(Input):
    key: Key
    expected_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def campaign_store(db, user, tenant_id, campaign_id, *, write):
    require_tenant(db, user, tenant_id, "editor" if write else "viewer")
    row = db.execute(
        select(Campaign, Brand)
        .join(Brand, Brand.id == Campaign.brand_id)
        .where(Campaign.tenant_id == tenant_id, Campaign.id == campaign_id, Brand.tenant_id == tenant_id)
    ).first()
    if not row:
        missing()
    scope = dict(tenant_id=tenant_id, client_id=row[1].client_id, brand_id=row[1].id)
    Workspace(SimpleNamespace(path_params=scope), user, db, write=write)
    return Store(db, user, **scope, write=write)


def history(store, campaign_id):
    # Decisions are pointers. Every proposal and approval fits the same visibility
    # class so an actor cannot accidentally select an older visible "active" revision.
    records = store.query(KnowledgeCommand).where(
        KnowledgeCommand.operation.in_(("campaign_plan", "campaign_plan_approve")), KnowledgeCommand.result["campaign_id"].as_string() == campaign_id
    )
    proposals, approvals, assets = {}, {}, {}
    for command in store.db.scalars(records):
        value = command.result
        if command.operation == "campaign_plan":
            proposals[value["id"]] = value
        else:
            assets[value["id"]] = value["composed_assets"]
            approvals[value["id"]] = {"actor": command.actor, "receipt": command.id, "at": command.effective_at.isoformat()}
    rows = sorted(proposals.values(), key=lambda row: row["revision"], reverse=True)
    active = next((row["id"] for row in rows if row["id"] in approvals), None)
    return [
        {
            **row,
            "status": "approved" if row["id"] == active else "proposed" if i == 0 else "superseded",
            "approval": approvals.get(row["id"]),
            "composed_assets": assets.get(row["id"], []),
        }
        for i, row in enumerate(rows)
    ]


def selection(store, cid, mid, *, stage):
    snap, body = c3_projection.unpack(store, mid)
    workflow = body["options"]["workflow"]
    if snap.campaign_id != cid or workflow not in KINDS:
        missing()
    brief = store.db.get(WorkforceBrief, snap.brief_id)
    ws = Workspace(SimpleNamespace(path_params=store.scope), store.db.get(User, store.actor), store.db, write=False)
    _, public = c3_projection.recheck(store, ws, snap.id, snap.digest, workflow, brief, stage)
    if not public["task_intent"].get("buyer_action"):
        conflict("Select an approved task with an explicit buyer action")
    return snap, body, public


def check_requirements(plan, projection):
    intent = projection["task_intent"]
    limits = intent.get("campaign_limits")
    if limits and (plan["duration_days"] > limits["max_duration_days"] or plan["budget_vnd"] > limits["max_media_budget_vnd"]):
        conflict("Thời hạn hoặc trần truyền thông vượt phạm vi đã ghim. Hãy duyệt brief và manifest mới.")
    outcomes = {projection["objective"], projection["kpi"], projection["kpi"].split(" · ")[0],
                intent["purpose"], *intent["acceptance_criteria"]}
    if plan["target_outcome"] not in outcomes:
        conflict("Kết quả đề xuất khác mục tiêu, KPI hoặc tiêu chí đã duyệt. Hãy duyệt brief và manifest mới.")
    if {c.casefold() for c in plan["channels"]} != {projection["channel"].casefold()}:
        conflict("Kênh sản xuất khác kênh đã duyệt. Hãy duyệt brief và manifest mới.")


def commissioned_brief(store, brief_id):
    records = store.query(KnowledgeCommand).filter_by(operation="c3_commission").where(
        KnowledgeCommand.result["brief_id"].as_string() == brief_id)
    return store.db.scalar(records.limit(1)) is not None


def execution_terms(store, snap, projection, budget):
    marker = commissioned_brief(store, snap.brief_id)
    if not marker and not store.approver:
        return None
    if marker and not store.approver:
        conflict("Quản trị viên cần xếp việc từ kế hoạch chiến dịch đã duyệt.")
    plans = history(store, snap.campaign_id)
    active = next((p for p in plans if p["status"] == "approved"), None)
    refs = active["manifests"].values() if active else []
    if not any(r["id"] == snap.id and r["digest"] == snap.digest for r in refs):
        if marker or any(p["approval"] and any(r["brief_id"] == snap.brief_id for r in p["manifests"].values()) for p in plans):
            conflict("Brief đã được giao theo kế hoạch khác. Chọn đúng manifest hoặc duyệt brief mới.")
        return None
    check_requirements(active, projection)
    cap = active.get("ai_budget_microusd_per_run", 10000)
    if budget != cap:
        conflict("Hạn mức sản xuất AI phải khớp với kế hoạch đã duyệt.")
    return {"plan_id": active["id"], "revision": active["revision"], "plan_digest": active["digest"],
            "manifest_id": snap.id, "manifest_digest": snap.digest, "target_outcome": active["target_outcome"],
            "channel": projection["channel"], "duration_days": active["duration_days"],
            "simulated_media_budget_vnd": active["budget_vnd"], "ai_budget_microusd_per_run": cap}


def active_plan(store, campaign_id, *, revalidate=True):
    current = next((row for row in history(store, campaign_id) if row["status"] == "approved"), None)
    if not current:
        conflict("Campaign has no approved plan")
    if revalidate:
        for ref in current["manifests"].values():
            selection(store, campaign_id, ref["id"], stage="operate")
    return current


@router.get("/planner")
def planner(tenant_id: str, campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = campaign_store(db, user, tenant_id, campaign_id, write=False)
    choices = []
    stmt = s.query(KnowledgeSnapshot).filter_by(campaign_id=campaign_id).order_by(KnowledgeSnapshot.snapshot_as_of.desc()).limit(100)
    for snapshot in db.scalars(stmt):
        body = json.loads(snapshot.canonical)
        if body.get("version") != c3_projection.TASK_MANIFEST:
            continue
        public = body["projection"]
        if public["task_intent"].get("buyer_action"):
            choices.append(
                {
                    "id": snapshot.id,
                    "digest": snapshot.digest,
                    "brief_id": snapshot.brief_id,
                    "workflow": body["options"]["workflow"],
                    **{k: public[k] for k in ("audience", "product", "objective")},
                    "buyer_action": public["task_intent"]["buyer_action"],
                    **({"channel": public["channel"], "kpi": public["kpi"].split(" · ")[0],
                        "limits": public["task_intent"].get("campaign_limits")} if s.approver else {}),
                }
            )
    rows = history(s, campaign_id)
    return {
        "choices": choices,
        "revisions": rows,
        "active": next((r for r in rows if r["status"] == "approved"), None),
        "proposed": next((r for r in rows if r["status"] == "proposed"), None),
    }


@router.post("/plans", status_code=201)
def propose(tenant_id: str, campaign_id: str, body: Proposal, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = campaign_store(db, user, tenant_id, campaign_id, write=True)
    # Campaign plans combine cross-department evidence, budget and potentially
    # restricted manifests. The first release keeps all revisions in admin scope.
    if not s.approver:
        missing()

    def make(_):
        rows = history(s, campaign_id)
        if body.expected_revision != (rows[0]["revision"] if rows else 0):
            conflict("Campaign plan has changed. Reload its latest revision")
        selected = [selection(s, campaign_id, mid, stage="queue") for mid in sorted(body.manifest_ids)]
        if len({p[1]["options"]["workflow"] for p in selected}) != len(selected):
            conflict("Choose at most one manifest per production workflow")
        return compose_plan(s, campaign_id, selected, body, new_id()), "restricted", None

    inputs = body.model_dump(mode="json")
    if not inputs["secondary_rfq"]:
        inputs.pop("secondary_rfq")
    # Existing retries used the implicit 10,000 µUSD ceiling before it was configurable.
    if inputs["ai_budget_microusd_per_run"] == 10000:
        del inputs["ai_budget_microusd_per_run"]
    return s.command("campaign_plan", body, make, target=campaign_id, fingerprint_input=inputs)


@router.post("/plans/{plan_id}/approve")
def approve(tenant_id: str, campaign_id: str, plan_id: str, body: Approval, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = campaign_store(db, user, tenant_id, campaign_id, write=True)
    if not s.approver:
        missing()

    def accept(_):
        rows = history(s, campaign_id)
        if not rows or rows[0]["id"] != plan_id or rows[0]["digest"] != body.expected_digest or rows[0]["status"] != "proposed":
            conflict("Approve the current proposed revision and digest")
        plan = rows[0]
        commissioned = {r["brief_id"]: r for row in rows if row["approval"] for r in row["manifests"].values()}
        current = next((r for r in rows if r["status"] == "approved"), {})
        carried = list(current.get("manifests", {}).values())
        for ref in plan["manifests"].values():
            if ref["brief_id"] in commissioned and ref not in carried:
                conflict("This brief already belongs to a commissioned plan. Prepare a new brief for the next revision")
            snap, _, projection = selection(s, campaign_id, ref["id"], stage="queue")
            check_requirements(plan, projection)
            if db.scalar(select(WorkforceRun.id).filter_by(tenant_id=tenant_id, campaign_id=campaign_id, brief_id=ref["brief_id"])):
                conflict("A commissioned workflow requires a fresh brief before production")
            # Publish only an opaque reservation under the brief's scope. Plan details stay restricted.
            s.insert(KnowledgeCommand, "internal", key="commission:" + plan_id + ":" + snap.id,
                     operation="c3_commission", actor=s.actor, request_digest=plan["digest"],
                     result={"brief_id": ref["brief_id"]}, snapshot_id=None, effective_at=s.now(), queued_at=None)
        from .campaign_operations import commission_plan_units

        assets = commission_plan_units(s, campaign_id, plan)
        return (
            {
                "id": plan_id,
                "campaign_id": campaign_id,
                "revision": plan["revision"],
                "digest": plan["digest"],
                "status": "approved",
                "composed_assets": assets,
            },
            "restricted",
            None,
        )

    return s.command("campaign_plan_approve", body, accept, target=[campaign_id, plan_id])


@router.post("/plans/{plan_id}/runs/{kind}")
def queue(
    tenant_id: str, campaign_id: str, plan_id: str, kind: Literal["strategy", "landing"], user: User = Depends(current_user), db: Session = Depends(get_db)
):
    # Workforce.start owns the commit, including the C3 queue receipt. Take the
    # same brief lock first as a direct Workforce request to preserve lock order.
    from .delivery import lock_document

    before = campaign_store(db, user, tenant_id, campaign_id, write=False)
    row = active_plan(before, campaign_id, revalidate=False)
    ref = row["manifests"].get(kind)
    if row["id"] != plan_id or not ref:
        conflict("Selected workflow is outside the approved plan")
    lock_document(db, "workforce-brief:" + ref["brief_id"])
    s = campaign_store(db, user, tenant_id, campaign_id, write=True)
    if active_plan(s, campaign_id)["id"] != plan_id:
        conflict("Plan superseded during queue")
    args = workforce.Start(
        workflow="dynamic-v1",
        max_parallel_nodes=1,
        budget_microusd=row.get("ai_budget_microusd_per_run", 10000),
        registry_workflow=ref["workflow"],
        knowledge_manifest={"id": ref["id"], "digest": ref["digest"]},
    )
    # Check an idempotent retry while the scoped transaction and locks are still active.
    # Workforce.start commits a new run and its receipt atomically.
    existing = db.scalar(select(WorkforceRun.id).filter_by(**s.scope, campaign_id=campaign_id, brief_id=ref["brief_id"]))
    if existing:
        from .campaign_operations import production_bindings
        if (plan_id, ref["id"]) not in production_bindings(s, campaign_id):
            conflict("Lượt chạy hiện hữu không thuộc kế hoạch. Hãy tạo brief và manifest mới.")
    return workforce.start(tenant_id, ref["brief_id"], args, user, db)


@router.get("/plans/{plan_id}/production")
def production(tenant_id: str, campaign_id: str, plan_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = campaign_store(db, user, tenant_id, campaign_id, write=False)
    revisions = history(s, campaign_id)
    plan = next((row for row in revisions if row["id"] == plan_id), None)
    if not plan:
        missing()
    runs, assets = [], []
    if plan["approval"]:
        assets.extend(plan["composed_assets"])
        from .campaign_operations import production_bindings

        bindings = production_bindings(s, campaign_id)
        for kind, ref in plan["manifests"].items():
            owned = bindings.get((plan_id, ref["id"]))
            if not owned:
                continue
            run, queue_receipt = owned
            runs.append(
                {
                    "kind": kind,
                    "queue_receipt": queue_receipt,
                    "commission": run.knowledge.get("campaign_commission"),
                    "manifest": ref,
                    **{k: getattr(run, k) for k in ("id", "state", "deliverable_id", "last_error", "budget_microusd", "reserved_microusd", "journal")},
                    "checkpoint_count": len(run.checkpoints),
                    "registry": run.knowledge["registry"],
                }
            )
            doc = db.get(Deliverable, run.deliverable_id) if run.deliverable_id else None
            if doc:
                body = doc.content.get("client_preview", "")
                bundle = doc.content.get("studio") or {}
                metadata = {
                    "deliverable_id": doc.id,
                    "revision": doc.qa_revision,
                    "document_digest": content_digest(doc.title, body),
                    "status": doc.status,
                    "plan_id": plan_id,
                    "plan_revision": plan["revision"],
                    "manifest": ref,
                    "run_id": run.id,
                    "product_id": plan["product_id"],
                    "buyer_action": plan["buyer_action"],
                    "guideline_digest": plan["brand_guidelines"]["digest"],
                    "registry": run.knowledge["registry"],
                }
                if bundle.get("delivery_version") in (c3_customer_assets.VERSION, campaign_channels.VERSION):
                    ctx = bundle.get("channel_context")
                    grouped = c3_customer_assets.project(ref["workflow"], bundle["groups"], ctx)
                    receipts = signoffs(db, doc, run)
                    slots = {"client_strategy": "strategy", "client_measurement": "measurement", "copy": "landing", "seo": "seo",
                             **{group: group for group in campaign_channels.FIELDS}}
                    if ctx:
                        # The immutable planner proposals remain in plan history. Show
                        # each commissioned package once in the current production list.
                        assets[:] = [a for a in assets if a["kind"] not in campaign_channels.FIELDS]
                    for group, fields in grouped.items():
                        slot = slots[group]
                        assets.append(
                            {
                                **metadata,
                                "id": slot,
                                "kind": slot,
                                "title": c3_customer_assets.labels(run.knowledge["c3_projection"]["locale"])[group],
                                "body": "\n".join(fields.values()),
                                "fields": fields,
                                "digest": asset_digest(doc, run, group, fields),
                                "approval_receipt": receipts.get(group, {}).get("receipt"),
                                **({"plan_digest": ctx["plan_digest"], "queue_receipt": ctx["queue_receipt"]} if ctx else {}),
                                "provenance": "staff_saved_studio_revision",
                            }
                        )
                else:
                    assets.append(
                        {
                            **metadata,
                            "id": kind,
                            "kind": kind,
                            "title": doc.title,
                            "body": body,
                            "digest": metadata["document_digest"],
                            "provenance": "workforce_draft" if doc.qa_revision <= 1 else "staff_saved_revision",
                        }
                    )
    return {"runs": runs, "assets": assets, "plan_id": plan_id, "plan_digest": plan["digest"]}
