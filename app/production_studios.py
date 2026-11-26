"""Internal, immutable production packages using existing Studio QA and campaign journals."""

from base64 import b64encode
from datetime import timedelta
from hashlib import sha256
from time import perf_counter
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StrictBool, StrictInt, StrictStr
from sqlalchemy import JSON, cast, func, select, type_coerce
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from . import c3_boundaries, c3_reviewer, c3_studio_routes, campaign_operations as operations
from . import campaign_operations_appointments as appointments
from . import campaign_operations_crm as crm, production_creative, production_landing
from .business_intake import validate_answers
from .campaign_operations_contracts import Appointment, IntakeAppointment, RFQ, SessionEvent
from .campaign_planner import active_plan, campaign_store
from .database import get_db
from .knowledge_contracts import Input
from .knowledge_models import KnowledgeCommand
from .knowledge_store import canonical, conflict, digest, missing
from .models import Deliverable, User
from .revision_qa import content_digest
from .security import current_user

router = APIRouter(prefix="/api/tenants/{tenant_id}/deliverables/{did}/studio/production", tags=["Sandbox production"])
KIND_GROUPS = {"creative": ("copy", "creative_brief"), "landing": ("copy", "seo")}
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Color = Annotated[str, Field(pattern=r"^#[A-Fa-f0-9]{6}$")]


class Prepare(Input):
    kind: Literal["creative", "landing"]
    expected_revision: Annotated[int, Field(gt=0, strict=True)]
    expected_plan_digest: Hash
    expected_groups: dict[str, Hash]
    expected_version: Annotated[int, Field(ge=0, strict=True)]
    palette: Literal["forest", "cobalt"] = "forest"
    colors: tuple[Color, Color, Color] | None = None
    motif: Literal["arches", "planes"] = "arches"
    layout: Literal["art_first", "text_first"] = "art_first"


class Verdict(Input):
    expected_digest: Hash
    note: Annotated[str, Field(min_length=10, max_length=360)]


class Visit(Input):
    request_id: UUID


class Submit(Visit):
    visit_id: Hash
    quantity: Annotated[int, Field(strict=True, ge=1, le=100)]
    place: Literal["north", "south"]
    days: Literal[2, 7]


class ContractSubmit(Visit):
    visit_id: Hash
    contract_digest: Hash
    consent: StrictBool
    answers: Annotated[dict[str, StrictInt | StrictStr], Field(max_length=7)]


def scope(db, user, tenant, did, write):
    doc, run = c3_studio_routes.scoped(db, user, tenant, did, "admin")
    store = campaign_store(db, user, tenant, run.campaign_id, write=write)
    if not store.approver:
        missing()
    return doc, run, store


def packages(store, doc, kind=None):
    # Keep encoded files in immutable storage. Listing or checking the latest
    # revision must not allocate every previous export in API process memory.
    col = KnowledgeCommand.result
    slim = cast(col, JSONB).op("-")("payloads") if store.postgres else type_coerce(func.json_remove(col, "$.payloads"), JSON)
    query = (
        select(KnowledgeCommand.id, KnowledgeCommand.actor, slim.label("result"))
        .filter_by(**store.scope)
        .where(KnowledgeCommand.operation.in_(("studio_production", "studio_landing_v2")))
        .where(col["did"].as_string() == doc.id)
    )
    if kind is not None:
        query = query.where(col["kind"].as_string() == kind)
    return store.db.execute(query.order_by(col["version"].as_integer().desc()).limit(1 if kind else 50)).all()


def get_package(store, doc, pid):
    row = store.get(KnowledgeCommand, pid)
    if row.operation not in {"studio_production", "studio_landing_v2"} or row.result["did"] != doc.id:
        missing()
    return row


def public(row):
    return {"id": row.id, "created_by": row.actor, **{k: v for k, v in row.result.items() if k != "payloads"}}


def group_gate(store, user, doc, run, kind, *, inspect_only=False):
    plan = active_plan(store, run.campaign_id, revalidate=False)
    ctx = (doc.content.get("studio") or {}).get("channel_context")
    if not ctx or ctx["plan_digest"] != plan["digest"]:
        conflict("Production requires a channel edition commissioned by this plan")
    signature = content_digest(doc.title, doc.content["client_preview"])
    operations.current_asset(store, user, run.campaign_id, plan, doc.id, doc.qa_revision, signature, gate=False)
    # Replay the original decision once. It already revalidates the active plan,
    # source lineage, registry contracts and every independent group receipt.
    _, _, decision = c3_boundaries.boundary(store.db, user, doc, signature, "replay_qa", inspect_only=inspect_only)
    groups = {group: asset["fields"] for group, asset in decision["customer_delivery"]["assets"].items()}
    signs = decision["studio_approvals"]
    required = KIND_GROUPS[kind]
    if any(group not in groups or group not in signs for group in required):
        conflict("The approved page or creative source groups are missing")
    return plan, groups, {g: c3_studio_routes.asset_digest(doc, run, g, groups[g]) for g in required}, {g: signs[g] for g in required}


def append_document(store, run, operation, key, result):
    return store.insert(
        KnowledgeCommand,
        "restricted",
        key=key,
        operation=operation,
        actor=store.actor,
        request_digest=digest(canonical(result)),
        result=result,
        snapshot_id=run.knowledge["c3_manifest"]["id"],
        effective_at=store.now(),
        queued_at=None,
    )


def approval(store, pkg, lock=False):
    rows = store.query(KnowledgeCommand).filter_by(operation="studio_product_qa", key="prod-qa:" + pkg.id)
    return next(
        (
            r
            for r in store.db.scalars(rows)
            if r.result["digest"] == pkg.result["digest"]
            and r.actor != pkg.actor
            and c3_reviewer.active_approver(store.db, store.scope["tenant_id"], r.actor, lock=lock)
        ),
        None,
    )


def verify_current(store, user, doc, run, pkg, *, inspect_only=False):
    item = pkg.result
    plan, _, groups, receipts = group_gate(store, user, doc, run, item["kind"], inspect_only=inspect_only)
    latest = next(iter(packages(store, doc, item["kind"])), None)
    if (
        not latest
        or latest.id != pkg.id
        or doc.qa_revision != item["studio_revision"]
        or plan["digest"] != item["plan_digest"]
        or groups != item["groups"]
        or receipts != item["group_receipts"]
    ):
        conflict("Reload the current production package and independent Studio approvals")
    return plan


def approved_landing_destination(store, user, plan):
    """Discover a current internal destination without producing a file, visit or approval."""
    ref = plan.get("manifests", {}).get("landing")
    if not ref or not store.approver or store.actor != user.id:
        return None
    cid = plan["campaign_id"]
    binding = operations.production_bindings(store, cid).get((plan["id"], ref["id"]))
    if not binding:
        return None
    run, _ = binding
    if (run.tenant_id, run.client_id, run.brand_id) != (store.scope["tenant_id"], store.scope["client_id"], store.scope["brand_id"]):
        return None
    doc = store.db.get(Deliverable, run.deliverable_id)
    if not doc or doc.campaign_id != cid:
        return None
    pkg = next(iter(packages(store, doc, "landing")), None)
    if not pkg or pkg.result["plan_digest"] != plan["digest"] or not approval(store, pkg):
        return None
    try:
        verified = verify_current(store, user, doc, run, pkg, inspect_only=True)
    except HTTPException as exc:
        if exc.status_code in (403, 404, 409, 412):
            return None
        raise
    if verified["id"] != plan["id"] or verified["digest"] != plan["digest"] or verified["manifests"]["landing"] != ref:
        return None
    return {
        "deliverable_id": doc.id,
        "package_id": pkg.id,
        "package_digest": pkg.result["digest"],
        "studio_revision": doc.qa_revision,
        "file_digest": pkg.result["files"]["landing.html"]["sha256"],
        "download_url": f"/api/tenants/{run.tenant_id}/deliverables/{doc.id}/studio/production/{pkg.id}/files/landing.html",
    }


@router.get("")
def history(tenant_id: str, did: str, user: Actor, db: DB):
    doc, _, store = scope(db, user, tenant_id, did, False)
    return [
        {
            "id": row.id,
            "kind": row.result["kind"],
            "version": row.result["version"],
            "digest": row.result["digest"],
            "created_by": row.actor,
            "studio_revision": row.result["studio_revision"],
            "files": row.result["files"],
            "design": {k: row.result["master"][k] for k in ("palette", "motif", "layout", "colors")} if row.result["kind"] == "creative" else None,
            "approval": None if not (signed := approval(store, row)) else {"id": signed.id, "actor": signed.actor},
        }
        for row in packages(store, doc)
    ]


@router.post("")
def prepare(tenant_id: str, did: str, body: Prepare, user: Actor, db: DB):
    doc, run, store = scope(db, user, tenant_id, did, True)
    plan, groups, hashes, receipts = group_gate(store, user, doc, run, body.kind)
    if body.expected_plan_digest != plan["digest"] or body.expected_revision != doc.qa_revision or body.expected_groups != hashes:
        raise HTTPException(412, "Studio or plan revision changed")
    if body.kind == "landing" and plan["buyer_action"] not in ("rfq", "appointment"):
        conflict("This page requires a commissioned RFQ or appointment")
    if body.kind == "landing" and not plan["selling_unit"]:
        conflict("Approve the product selling unit before producing a transactional landing page")
    options = body.model_dump(include={"palette", "layout", "motif", "colors"}, exclude_none=True) if body.kind == "creative" else {}
    signature = digest(canonical([body.kind, doc.qa_revision, plan["digest"], hashes, receipts, options]))
    prior = next(iter(packages(store, doc, body.kind)), None)
    version = prior.result["version"] if prior else 0
    if prior and prior.result["inputs"] == signature and body.expected_version in (version, version - 1):
        return public(prior)
    if version != body.expected_version:
        raise HTTPException(412, "A new production master was saved")
    projection = run.knowledge["c3_projection"]
    started = perf_counter()
    if body.kind == "creative":
        master, files = production_creative.produce(groups, projection, options)
    else:
        master, files = production_landing.produce(groups, plan, projection)
    inventory = {name: {"mime": mime, "bytes": len(data), "sha256": sha256(data).hexdigest()} for name, (mime, data) in files.items()}
    if sum(f["bytes"] for f in inventory.values()) > 2_000_000:
        raise HTTPException(422, "The rendering exceeds the local package size limit")
    value = {
        "did": did,
        "version": version + 1,
        "kind": body.kind,
        "studio_revision": doc.qa_revision,
        "manifest": run.knowledge["c3_manifest"],
        "plan_id": plan["id"],
        "plan_digest": plan["digest"],
        "groups": hashes,
        "group_receipts": receipts,
        "inputs": signature,
        "master": master,
        "files": inventory,
    }
    value["digest"] = digest(canonical(value))
    value["measurement"] = {
        "render_ms": round((perf_counter() - started) * 1000, 2),
        "bytes": sum(f["bytes"] for f in inventory.values()),
        "external_calls": 0,
        "full_cost_vnd": None,
    }
    value["payloads"] = {name: b64encode(data).decode("ascii") for name, (_, data) in files.items()}
    operation = "studio_landing_v2" if master.get("intake_contract") else "studio_production"
    row = append_document(store, run, operation, "prod:" + digest(canonical([did, body.kind, version + 1])), value)
    db.commit()
    return public(row)


@router.get("/{pid}/files/{filename}")
def artifact(tenant_id: str, did: str, pid: str, filename: str, user: Actor, db: DB):
    doc, _, store = scope(db, user, tenant_id, did, False)
    item = get_package(store, doc, pid).result
    if filename not in item["files"]:
        missing()
    return {**item["files"][filename], "base64": item["payloads"][filename]}


@router.post("/{pid}/approve")
def approve(tenant_id: str, did: str, pid: str, body: Verdict, user: Actor, db: DB):
    doc, run, store = scope(db, user, tenant_id, did, True)
    pkg = get_package(store, doc, pid)
    verify_current(store, user, doc, run, pkg)
    if body.expected_digest != pkg.result["digest"]:
        raise HTTPException(412, "Review the exact rendered files")
    if user.id == pkg.actor or not c3_reviewer.active_approver(db, tenant_id, user.id, lock=True):
        conflict("A different active reviewer must inspect the produced files")
    previous = approval(store, pkg, lock=True)
    if previous:
        if previous.actor != user.id or previous.result["note"] != body.note:
            conflict("An active decision already exists for these files")
        return {"receipt": previous.id, "digest": pkg.result["digest"]}
    row = append_document(store, run, "studio_product_qa", "prod-qa:" + pid, {"digest": pkg.result["digest"], "note": body.note})
    db.commit()
    return {"receipt": row.id, "digest": body.expected_digest}


def intake(tenant, did, pid, body, user, db):
    doc, run, store = scope(db, user, tenant, did, True)
    pkg = get_package(store, doc, pid)
    if pkg.result["kind"] != "landing":
        missing()
    plan = verify_current(store, user, doc, run, pkg)
    if not approval(store, pkg, lock=True):
        conflict("Independently review the produced landing page before recording a sandbox event")
    contract = pkg.result["master"].get("intake_contract")
    if contract != plan.get("intake_contract"):
        conflict("Review the landing package issued for the current intake contract")
    mapped = {}
    if isinstance(body, (Submit, ContractSubmit)):
        if bool(contract) != isinstance(body, ContractSubmit):
            raise HTTPException(422, "Use the form issued with this approved page")
        if contract:
            mapped = validate_answers(contract, body.contract_digest, body.answers, body.consent)
    rows = operations.entries(store, run.campaign_id)
    state = operations.state_of(rows)
    scope_key = [pid, user.id]
    visitor = digest(canonical(["synthetic-visitor", *scope_key]))
    key = "lp:" + digest(canonical([*scope_key, str(body.request_id)]))
    fp = digest(canonical(body.model_dump(mode="json")))
    prior = next((r for r in rows if r.key == key), None)
    if prior:
        if prior.request_digest != fp:
            conflict("Request ID already used with different selections")
        return prior.result
    at = store.now()
    landing_source = {
        **store.scope, "campaign_id": run.campaign_id, "plan_id": plan["id"], "plan_digest": plan["digest"],
        "document_id": doc.id, "studio_revision": doc.qa_revision, "package_id": pid,
        "package_version": pkg.result["version"], "package_digest": pkg.result["digest"],
        "file_digest": pkg.result["files"]["landing.html"]["sha256"],
    }
    identity = digest(canonical([*scope_key, str(body.request_id)]))
    common = {"plan_id": plan["id"], "request_id": body.request_id.hex, "occurred_at": at}
    if contract:
        landing_source["intake_contract_digest"] = contract["digest"]
    if isinstance(body, (Submit, ContractSubmit)):
        visit = state["sessions"].get(body.visit_id)
        if not visit or visit["plan_id"] != plan["id"] or visit["visitor"] != visitor:
            conflict("Open this approved synthetic page before submitting the form")
        if visit.get("landing_package") != pid or visit.get("landing_digest") != pkg.result["digest"]:
            conflict("Visit and form must use the same approved landing package")
        if visit.get("landing_source") and visit["landing_source"] != landing_source:
            conflict("Visit and form must use the same approved landing revision")
        fixture_id = digest(canonical(["landing-form", pid, body.visit_id]))
        if not contract:
            mapped = {"quantity": body.quantity, "location": body.place,
                      "requested_for" if plan["buyer_action"] == "appointment" else "required_date": body.days}
        location = {"north": "Synthetic site A", "south": "Synthetic site B"}.get(mapped.get("location"))
        inputs = {
            "product_id": plan["product_id"],
            "unit": plan["selling_unit"],
            "quantity": mapped.get("quantity"),
            "location": location,
            "session_id": body.visit_id,
        }
        if plan["buyer_action"] == "appointment":
            command = IntakeAppointment if contract else Appointment
            cmd = command(
                **common,
                **inputs,
                kind="appointment",
                appointment_id=fixture_id,
                contract="service-intake/2" if contract else "service-appointment/1",
                contact_purpose="appointment_request",
                service_scope=plan["product"] if contract else "Synthetic service assessment",
                requested_for=at + timedelta(days=int(mapped["requested_for"])) if "requested_for" in mapped else None,
            )
            entity, ident, value = appointments.appointment(cmd, state, plan, store)
        else:
            required_date = (at + timedelta(days=int(mapped["required_date"]))).date() if "required_date" in mapped else None
            cmd = RFQ(**common, **inputs, kind="rfq", rfq_id=fixture_id, contact_purpose="quote_request", required_date=required_date)
            entity, ident, value = crm.observation(cmd, state, plan, store)
        if contract:
            value["intake"] = {"contract_digest": contract["digest"], "revision": contract["revision"],
                               "answers": body.answers, "fields": contract["fields"], "mapped": mapped,
                               "consent": {"purpose": contract["consent"]["purpose"], "granted": body.consent}}
    else:
        cmd = SessionEvent(**common, kind="session", session_id=identity, actor_key=visitor)
        entity, ident, value = crm.observation(cmd, state, plan, store)
    event = operations.append(
        store,
        run.campaign_id,
        plan["id"],
        cmd.kind,
        entity,
        ident,
        {**value, "landing_package": pid, "landing_digest": pkg.result["digest"], "landing_source": landing_source},
        len(rows) + 1,
        key,
        fp,
    )
    db.commit()
    return event


@router.post("/{pid}/visits")
def visit(tenant_id: str, did: str, pid: str, body: Visit, user: Actor, db: DB):
    return intake(tenant_id, did, pid, body, user, db)


@router.post("/{pid}/submissions")
def submit(tenant_id: str, did: str, pid: str, body: ContractSubmit | Submit, user: Actor, db: DB):
    return intake(tenant_id, did, pid, body, user, db)
