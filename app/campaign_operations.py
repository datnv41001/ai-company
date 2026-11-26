"""Durable sandbox operations. A campaign uses the existing brand lock and signed append journal."""
import os
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import c3_boundaries, campaign_channels, measurement_integrity
from .c3_reviewer import active_approver
from .campaign_operations_contracts import Appointment, AppointmentDecision, ActionTarget, CompleteRFQ, CostClose, DecideAction, Execute, Labor, Optimization, ReconcileCost, RFQ, Sales, SandboxCommand, Schedule, SessionEvent
from . import campaign_operations_appointments as appointments, campaign_operations_capabilities as capabilities, campaign_operations_cost as costs
from .campaign_operations_crm import observation, reconcile, secondary_rfq_funnel
from .campaign_planner import active_plan, campaign_store, history
from .campaign_planner_pack import compose_assets
from .database import get_db
from .delivery import working_copy
from .delivery_models import ClientReview, ReviewEntry
from .knowledge_models import KnowledgeCommand
from .knowledge_store import aware, canonical, conflict, digest, missing, parse_time, stamp
from .models import Deliverable, User, new_id
from .revision_qa import content_digest
from .security import current_user
from .workforce_models import WorkforceRun


router = APIRouter(prefix="/api/tenants/{tenant_id}/campaigns/{campaign_id}/sandbox", tags=["Campaign sandbox"])
OP = "campaign_sandbox_v2"
BUCKETS = ("actions", "leads", "sessions", "work_units", "proposals", "appointments")
GROUP = {"strategy": "client_strategy", "measurement": "client_measurement", "landing": "copy", "seo": "seo",
         **{group: group for group in campaign_channels.FIELDS}}


def entries(store, cid):
    return list(store.db.scalars(store.query(KnowledgeCommand).where(KnowledgeCommand.operation.in_(("campaign_sandbox_v1", OP)))
                .where(KnowledgeCommand.result["campaign_id"].as_string() == cid)))


def state_of(rows):
    state = {name: {} for name in BUCKETS}
    for event in sorted((r.result for r in rows), key=lambda e: e["sequence"]):
        state[event["entity"]][event["entity_id"]] = event["value"]
    return state


def append(store, cid, pid, kind, entity, ident, value, sequence, key, fingerprint):
    receipt = new_id()
    at = store.now()
    event = {"id": receipt, "campaign_id": cid, "plan_id": pid, "sequence": sequence, "kind": kind,
             "entity": entity, "entity_id": ident, "value": value, "actor": store.actor, "recorded_at": stamp(at)}
    store.insert(KnowledgeCommand, "restricted", id=receipt, operation=OP, actor=store.actor, key=key,
                 request_digest=fingerprint, result=event, snapshot_id=None, effective_at=at, queued_at=None)
    return event


def production_bindings(store, cid):
    """Bind each run to the commission in force when C3 durably queued it."""
    approved = [(aware(parse_time(p["approval"]["at"])), p) for p in history(store, cid) if p["approval"]]
    runs = {r.id: r for r in store.db.scalars(select(WorkforceRun).filter_by(**store.scope, campaign_id=cid))}
    if not approved or not runs:
        return {}
    receipts = store.query(KnowledgeCommand).filter_by(operation="c3_queue").where(
        KnowledgeCommand.result["run_id"].as_string().in_(runs))
    bindings = {}
    for receipt in store.db.scalars(receipts):
        run = runs[receipt.result["run_id"]]
        # Read approvals in descending revision order. A standalone run queued after its plan
        # was retired cannot retroactively credit that plan, even with the same exact brief.
        at = aware(receipt.queued_at)
        owner = next((p for start, p in approved if start <= at), None)
        if not owner:
            continue
        # Pre-commission receipts retain their historical attribution. New receipts must
        # prove the plan reached this run even when an editor independently queues a brief.
        if "campaign_plan_digest" in receipt.result and receipt.result["campaign_plan_digest"] != owner["digest"]:
            continue
        manifest = {"id": receipt.snapshot_id, "digest": receipt.result["manifest_digest"]}
        if manifest != run.knowledge.get("c3_manifest"):
            continue
        for ref in owner["manifests"].values():
            if ref["brief_id"] == run.brief_id and ref["id"] == manifest["id"] and ref["digest"] == manifest["digest"]:
                bindings[(owner["id"], ref["id"])] = (run, receipt.id)
    return bindings


def commission_plan_units(store, campaign_id, plan):
    """Called inside plan approval before its commit and before any workflow can start."""
    rows = entries(store, campaign_id)
    state = state_of(rows)
    commissioned = {}
    for seq, pkg in enumerate(plan["work_packages"], start=len(rows) + 1):
        slot = pkg["id"]
        # Renewing the same plan/scope is a revision. Commissioning a different brief, audience,
        # target or acceptance contract is a new outcome, even in the same campaign and category.
        key = digest(canonical([store.scope, campaign_id, slot, plan["objective_revision"], plan["audience_revision"],
                                plan["product_id"], plan["target_outcome"], plan["buyer_action"],
                                plan["manifests"], pkg["criteria"], pkg["complexity"]]))
        prior = state["work_units"].get(key, {})
        manifest_kind = "strategy" if slot in {"strategy", "measurement"} else "landing"
        manifest = plan["manifests"].get(manifest_kind) or plan["manifests"]["strategy"]
        row = {"id": key, "package_id": slot, "scope": {**store.scope, "campaign_id": campaign_id}, "plan_id": plan["id"],
               "category": pkg["kind"], "assigned_role": pkg["role"], "complexity": pkg["complexity"],
               "expected_output": pkg["kind"], "criteria": pkg["criteria"], "commissioned_at": prior.get("commissioned_at") or stamp(store.now()),
               "status": "requested", "manifest": manifest, "origin": None, "artifact_digest": None,
               "artifact_revision": None, "acceptance": prior.get("acceptance"),
               "labor": prior.get("labor", []), "cost_statement": None, "plan_revision": plan["revision"]}
        append(store, campaign_id, plan["id"], "commission", "work_units", key, row, seq,
               "commission:" + digest(canonical([campaign_id, plan["id"], key])), digest(canonical(pkg)))
        commissioned[slot] = row
    issued = len(rows) + len(commissioned)
    retained = {u["id"] for u in commissioned.values()}
    abandoned = [u for u in state["work_units"].values() if u["id"] not in retained and u["package_id"] in GROUP and u["status"] == "requested"]
    bindings = production_bindings(store, campaign_id) if abandoned else {}
    for old in abandoned:
        if (old["plan_id"], old["manifest"]["id"]) in bindings:
            continue
        issued += 1
        incomplete = {**old, "status": "incomplete", "superseded_by": plan["id"]}
        append(store, campaign_id, old["plan_id"], "superseded_unstarted", "work_units", old["id"], incomplete, issued,
               "superseded:" + digest(canonical([plan["id"], old["id"]])), digest(canonical(incomplete)))
    # Production starts after all requested receipts exist. Failure anywhere rolls back the entire approval.
    assets = compose_assets(plan)
    for seq, asset in enumerate(assets, start=issued + 1):
        unit = commissioned[asset["kind"]]
        row = {**unit, "status": "generated", "origin": asset["provenance"], "manifest": asset["manifest"],
               "artifact_digest": asset["digest"], "artifact_revision": asset["revision"]}
        append(store, campaign_id, plan["id"], "generated", "work_units", unit["id"], row, seq,
               "generated:" + digest(canonical([campaign_id, plan["id"], unit["id"]])), asset["digest"])
    return assets


def current_asset(store, user, cid, plan, did, revision, signature, *, gate):
    doc = store.db.get(Deliverable, did)
    if not doc or (doc.tenant_id, doc.campaign_id) != (store.scope["tenant_id"], cid):
        missing()
    run = c3_boundaries.run_for(store.db, doc)
    if not run or not any(run.brief_id == ref["brief_id"] and run.knowledge["c3_manifest"] == {"id": ref["id"], "digest": ref["digest"]}
                          for ref in plan["manifests"].values()):
        conflict("Document does not belong to a commissioned workflow of this plan")
    if (doc.status not in ("approved", "shared") or doc.qa_revision != doc.qa_approved_revision or doc.qa_revision != revision
            or not doc.reviewed_by or doc.qa_approved_digest != signature or content_digest(doc.title, doc.content.get("client_preview", "")) != signature):
        conflict("Simulated action needs current independent QA on the exact document revision")
    if gate:
        c3_boundaries.boundary(store.db, user, doc, signature, "replay_qa")
    return doc


def action_command(cmd, state, plan, store, user, cid, *, dispatched=False):
    actions = state["actions"]
    if isinstance(cmd, Schedule):
        if cmd.action_id in actions:
            conflict("Action ID already commissioned")
        doc = current_asset(store, user, cid, plan, cmd.deliverable_id, cmd.expected_revision, cmd.expected_digest, gate=False)
        target = capabilities.bind(store, doc, cmd.target) if cmd.target else None
        return "actions", cmd.action_id, {"id": cmd.action_id, "plan_id": plan["id"], "plan_digest": plan["digest"],
                "deliverable_id": cmd.deliverable_id, "asset_revision": cmd.expected_revision, "asset_digest": cmd.expected_digest,
                "cost_vnd": cmd.cost_vnd, "due_at": stamp(cmd.due_at), "state": "scheduled", "scheduled_by": user.id,
                "authorized_by": None, "attempts": 0, "execution_receipt": None, "executed_at": None,
                "target":target, "execution_mode":target["mode"] if target else "manual"}
    old = actions.get(cmd.action_id)
    if not old or old["plan_id"] != cmd.plan_id:
        missing()
    row = dict(old)
    if cmd.kind == "cancel":
        if row["state"] not in {"scheduled", "authorized", "failed"}:
            conflict("Only pending sandbox work can be cancelled")
        row["state"] = "cancelled"
        return "actions", row["id"], row
    doc = current_asset(store, user, cid, plan, row["deliverable_id"], row["asset_revision"], row["asset_digest"], gate=True)
    target = row.get("target")
    if target:
        typed = ActionTarget.model_validate({k:target[k] for k in ActionTarget.model_fields})
        if capabilities.bind(store,doc,typed) != target:
            conflict("Scheduled capability or its group approval changed")
    if cmd.kind == "authorize":
        if row["state"] != "scheduled" or not store.approver or row["scheduled_by"] == user.id:
            conflict("A different campaign approver must authorize the scheduled action")
        row.update(state="authorized", authorized_by=user.id)
    else:
        if (row.get("execution_mode") == "scheduled") != dispatched:
            conflict("Use the execution path authorized for this sandbox action")
        if row["state"] not in {"authorized", "failed"} or row["attempts"] >= 3 or aware(store.now()) < parse_time(row["due_at"]):
            conflict("Execution is not due or is no longer retryable")
        if not active_approver(store.db, store.scope["tenant_id"], row["authorized_by"], lock=True):
            conflict("Execution authority was withdrawn")
        row["attempts"] += 1
        if cmd.outcome == "temporary_failure":
            row["state"] = "failed"
        else:
            row.update(state="executed", execution_receipt=new_id(), executed_at=stamp(store.now()),
                       executed_via="local_dispatcher" if dispatched else "manual_sandbox")
            if target:
                row["sandbox_output"] = capabilities.perform(store,doc,target)
    # The scope lock serializes budget reservations. Old revisions cannot run, but completed spend survives every replan.
    committed = sum(a["cost_vnd"] for a in actions.values() if a["id"] != row["id"] and
                    (a["state"] == "executed" or (a["plan_id"] == cmd.plan_id and a["state"] in {"authorized", "failed"})))
    if committed + row["cost_vnd"] > plan["budget_vnd"]:
        conflict("Approval would exceed the simulated campaign budget")
    return "actions", row["id"], row


def work_receipt(cmd, state, plan, store, cid, rows):
    unit = next((item for item in state["work_units"].values() if item["plan_id"] == plan["id"]
                 and cmd.package_id in (item["id"], item["package_id"])), None)
    if not unit or unit["plan_id"] != plan["id"]:
        missing()
    row = dict(unit)
    if isinstance(cmd, ReconcileCost):
        witnessed = dict(unit)
        enrich_units(store,cid,[witnessed])
        row["meter"] = costs.verify(cmd,witnessed,rows)
        return "work_units",unit["id"],row
    if isinstance(cmd, Labor):
        row["labor"] = [*row["labor"], {"actor": store.actor, "phase": cmd.phase, "seconds": cmd.seconds,
                         "allocated_cost_vnd": cmd.allocated_cost_vnd, "observation": cmd.observation, "at": stamp(store.now())}]
        row["cost_statement"] = None
        return "work_units", unit["id"], row
    if isinstance(cmd, CostClose):
        if not row["labor"] or any(item["allocated_cost_vnd"] is None for item in row["labor"]):
            conflict("Record and price observed effort before closing this unit's production cost")
        row["cost_statement"] = {"actor": store.actor, "at": stamp(store.now()), "basis": cmd.basis,
                                 "nonlabor_vnd": cmd.nonlabor_vnd, "manual_baseline_seconds": cmd.manual_baseline_seconds,
                                 "total_vnd": sum(r["allocated_cost_vnd"] for r in row["labor"]) + cmd.nonlabor_vnd}
        return "work_units", unit["id"], row
    rev = store.db.scalar(select(ClientReview).filter_by(**store.scope, campaign_id=cid, id=cmd.review_id))
    if not rev or unit["package_id"] not in GROUP:
        missing()
    binding = production_bindings(store, cid).get((plan["id"], unit["manifest"]["id"]))
    if not binding or binding[0].deliverable_id != rev.deliverable_id:
        conflict("The shared document was not produced for this commissioned outcome")
    entry = store.db.scalar(select(ReviewEntry).filter_by(tenant_id=store.scope["tenant_id"], review_id=rev.id, digest=rev.digest)
                            .where(ReviewEntry.kind.in_(("approved", "rejected", "changes_requested"))))
    # Snapshot evidence is historical; an edit since sharing must not invalidate a legitimate customer decision.
    decisions = store.query(KnowledgeCommand).filter_by(operation="c3_share", snapshot_id=unit["manifest"]["id"])
    share = store.db.scalar(decisions.where(KnowledgeCommand.result["review_id"].as_string() == rev.id))
    if (not entry or not share or share.result.get("content_digest") != rev.digest
            or share.result.get("run_id") != binding[0].id or share.result.get("document_id") != rev.deliverable_id):
        conflict("Need the scoped client decision on a shared, evidence-bound revision")
    edition = share.result.get("customer_delivery", {})
    if unit["package_id"] in campaign_channels.FIELDS:
        ctx = edition.get("channel_context", {})
        if ctx.get("plan_digest") != plan["digest"] or ctx.get("queue_receipt") != binding[1]:
            conflict("The channel asset was not delivered for this plan and queue receipt")
    asset = edition.get("assets", {}).get(GROUP[unit["package_id"]])
    if not asset or edition.get("scope") != {**store.scope, "campaign_id": cid}:
        conflict("Delivery decision does not include this commissioned asset")
    group = GROUP[unit["package_id"]]
    if any(r.result["kind"] == "unit_receipt" and GROUP.get(r.result["value"]["package_id"]) == group and
           r.result["value"]["acceptance"]["share_receipt"] == share.id for r in rows):
        conflict("This shared asset group already has a recorded decision")
    previous = unit.get("acceptance")
    if previous and previous["at"] >= stamp(entry.created_at):
        conflict("A newer client decision has already been recorded")
    status = "rejected" if entry.kind != "approved" else "fixture_accepted"
    # Only explicitly enrolled sandbox campaigns can classify a genuine participant's portal acceptance as business evidence.
    enrollment = f"{store.scope['tenant_id']}/{cid}/{entry.actor_id}"
    if status == "fixture_accepted" and enrollment in os.getenv("AMC_PRACTITIONER_ACCEPTORS", "").split(","):
        status = "business_accepted"
    row.update(status=status, acceptance={"status": status, "review_id": rev.id, "entry_id": entry.id, "actor": entry.actor_id,
               "share_receipt": share.id, "group": group, "run_id": binding[0].id, "queue_receipt": binding[1],
               "at": stamp(entry.created_at), "plan_id": plan["id"], "revision": edition["revision"],
               "elapsed_seconds": max(0, (aware(entry.created_at) - parse_time(row["commissioned_at"])).total_seconds()),
               "artifact_digest": asset["digest"], "snapshot_digest": rev.digest})
    return "work_units", unit["id"], row


def enrich_units(store, cid, units):
    bindings = production_bindings(store, cid)
    for unit in units:
        ref = unit.get("manifest")
        if not ref or unit["package_id"] not in GROUP:
            continue
        binding = bindings.get((unit["plan_id"], ref["id"]))
        if not binding:
            continue
        run, receipt_id = binding
        channel = unit["package_id"] in campaign_channels.FIELDS
        doc = store.db.get(Deliverable, run.deliverable_id) if run.deliverable_id else None
        if channel:
            studio = doc.content.get("studio", {}) if doc else {}
            if studio.get("channel_context", {}).get("plan_id") != unit["plan_id"] or unit["package_id"] not in studio.get("groups", {}):
                continue
        unit.update(run_id=run.id, run_state=run.state, queue_receipt=receipt_id)
        if not channel:
            unit.update(worker_attempts=run.attempts, last_error=run.last_error,
                        worker_journal=run.journal, reserved_microusd=run.reserved_microusd)
        if unit["acceptance"] and unit["acceptance"]["plan_id"] == unit["plan_id"]:
            unit["status"] = unit["acceptance"]["status"]
        elif doc and doc.campaign_id == cid:
            unit.update(status="qa_passed" if doc.status in ("approved", "shared") and doc.qa_approved_revision == doc.qa_revision else "generated",
                        artifact_revision=doc.qa_revision, artifact_digest=content_digest(doc.title, doc.content.get("client_preview", "")),
                        origin="workforce_draft" if doc.qa_revision == 1 else "staff_saved_revision")
            if channel:
                from .c3_studio_routes import asset_digest
                group = unit["package_id"]
                unit.update(artifact_digest=asset_digest(doc, run, group, studio["groups"][group]), origin="staff_saved_channel_edition")
        elif run.state == "failed":
            unit["status"] = "incomplete"


def optimization(evidence):
    if not evidence:
        return {"basis": "no_approved_plan", "recommendation": "Chọn kế hoạch đã duyệt để đối chiếu kết quả."}
    if evidence["buyer_action"] == "appointment":
        service = evidence.get("primary_measurement") or evidence["appointments"]
        if not service.get("denominator", service.get("requests")):
            return {"basis": "no_eligible_appointments", "recommendation": "Đối chiếu biên nhận lịch hẹn đủ điều kiện trong phạm vi đo trước khi thay đổi kế hoạch."}
        if service["no_show"] or service["cancelled"]:
            return {"basis":"appointment_exceptions","recommendation":"Đối chiếu lịch hủy và khách vắng mặt với thời điểm xác nhận trước khi đổi quy trình nhắc lịch."}
        return {"basis":"appointment_followup","recommendation":"Đối chiếu lịch đã xác nhận và phản hồi sau dịch vụ trước khi tăng số lịch tiếp nhận."}
    if evidence["buyer_action"] != "rfq":
        return {"basis": "unmeasured_journey", "recommendation": "Xác nhận biên nhận và định nghĩa KPI cho hành trình đã duyệt."}
    if not evidence["rfqs"]:
        return {"basis": "no_rfqs", "recommendation": "Kiểm tra biểu mẫu và nguồn lượt vào trước khi tăng ngân sách."}
    if evidence["missing_attribution"]:
        return {"basis": "missing_attribution", "recommendation": "Đối soát mã phiên và biên nhận thực thi để xác định nguồn yêu cầu báo giá."}
    if evidence["rfqs"] > evidence["qualified_leads"]:
        return {"basis": "incomplete_requests", "recommendation": "Kiểm tra các trường thương mại còn thiếu trước khi chuyển yêu cầu sang Sales."}
    return {"basis": "sales_followup", "recommendation": "Đối chiếu phản hồi Sales với đơn xác nhận trước khi đề xuất thay đổi kênh."}


def optimization_evidence(state, plan, cutoff, scope):
    if not plan:
        return None
    evidence = {"version": "plan-optimization/2", "campaign_id": plan["campaign_id"], "plan_id": plan["id"],
                "plan_digest": plan["digest"], "buyer_action": plan["buyer_action"], "period": "plan_lifetime",
                "as_of_inclusive": stamp(cutoff), "kpi": plan["measurement_plan"]["kpi"], "source": "no_measurement_adapter"}
    if contract := plan.get("measurement_contract"):
        expected = {**scope, "campaign_id": plan["campaign_id"], "plan_id": plan["id"], "plan_digest": plan["digest"]}
        primary = measurement_integrity.evaluate(contract, plan["id"], state, cutoff, plan["locale"], landing_scope=expected)
        evidence.update(period="measurement_window", source=primary["source"], primary_measurement=primary)
    elif plan["buyer_action"] == "appointment":
        evidence.update(source="sandbox_appointment_receipts", appointments=appointments.summary(plan_rows(state, plan, ("appointments", "sessions"))))
    elif plan["buyer_action"] == "rfq":
        report = reconcile(plan_rows(state, plan, ("leads", "sessions", "actions")))
        evidence.update(source="sandbox_rfq_receipts", **{k: report[k] for k in ("rfqs", "qualified_leads", "missing_attribution")})
    return evidence


def plan_rows(state, plan, buckets):
    return {key: {rid: row for rid, row in state[key].items() if row["plan_id"] == plan["id"]} for key in buckets}


def measurement_inputs_digest(state, plan):
    # Event revisions matter even when two changes cancel out in the headline totals.
    buckets = {"appointment": ("appointments", "sessions"), "rfq": ("leads", "sessions", "actions")}
    inputs = plan_rows(state, plan, buckets.get(plan["buyer_action"], ()))
    return digest(canonical({"plan_digest": plan["digest"], "inputs": inputs}))


def optimize_command(cmd, state, store, plan):
    proposals = state["proposals"]
    if cmd.kind == "propose_optimization":
        if cmd.proposal_id in proposals:
            conflict("Proposal ID already exists")
        report = optimization_evidence(state, plan, store.now(), store.scope)
        value = {"id": cmd.proposal_id, "plan_id": plan["id"], "status": "proposed", "author": store.actor,
                 **optimization(report), "evidence": report, "report_digest": digest(canonical(report)),
                 "measurement_inputs_digest": measurement_inputs_digest(state, plan)}
    else:
        value = proposals.get(cmd.proposal_id)
        if not value or value["plan_id"] != plan["id"] or value["status"] != "proposed" or value["author"] == store.actor:
            conflict("A different approver must review the proposed optimization package")
        # Legacy recommendations were made on campaign-wide data and remain visible
        # in history. A new scoped decision is required before issuing a work package.
        if value["evidence"].get("version") != "plan-optimization/2":
            conflict("Create a new proposal with scoped measurement evidence")
        report = optimization_evidence(state, plan, parse_time(value["evidence"]["as_of_inclusive"]), store.scope)
        if value["report_digest"] != digest(canonical(report)) or value.get("measurement_inputs_digest") != measurement_inputs_digest(state, plan):
            conflict("Measurement changed. Create and review a fresh proposal")
        value = {**value, "status": "approved", "approved_by": store.actor,
                 "work_package": {"id": cmd.proposal_id, "role": "marketing_analyst", "outcome": value["recommendation"],
                                  "criteria": "Đối soát lại báo cáo và ghi nhận ngoại lệ còn mở.", "budget_vnd": 0}}
    return "proposals", cmd.proposal_id, value


@router.get("")
def view(tenant_id: str, campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db),
         measurement_plan_id: str | None = Query(default=None, max_length=64)):
    store = campaign_store(db, user, tenant_id, campaign_id, write=False)
    if not store.approver:
        missing()
    rows = entries(store, campaign_id)
    state = state_of(rows)
    plans = history(store, campaign_id)
    if measurement_plan_id:
        selected = next((p for p in plans if p["id"] == measurement_plan_id and p["approval"]), None)
        if not selected:
            missing()
    else:
        selected = next((p for p in plans if p["status"] == "approved"), None)
    evidence = optimization_evidence(state, selected, store.now(), store.scope)
    report = {"aggregate_scope": "campaign_lifetime", **reconcile(state)}
    if evidence and "primary_measurement" in evidence:
        report["primary_measurement"] = evidence["primary_measurement"]
    if secondary := secondary_rfq_funnel(selected, state):
        report["secondary_rfq_funnel"] = secondary
    units = list(state["work_units"].values())
    enrich_units(store, campaign_id, units)
    accepted = sum((u["acceptance"] or {}).get("status") == "business_accepted" for u in units)
    allocated = [labor["allocated_cost_vnd"] for u in units for labor in u["labor"]]
    coverage = costs.summarize(units)
    return {"synthetic": True, "campaign_id": campaign_id, **{k: list(v.values()) for k, v in state.items()}, "report": report,
            "optimization": {**optimization(evidence), "evidence": evidence}, "requested_units": len(units), "business_accepted_units": accepted,
            "recorded_allocated_cost_vnd": sum(v for v in allocated if v is not None) if any(v is not None for v in allocated) else None,
            **coverage,"appointment_summary":appointments.summary(state),
            "receipts": [{"id": r.id, "kind": r.result["kind"], "actor": r.actor, "at": stamp(r.effective_at),
                          "sequence": r.result["sequence"], "entity_id": r.result["entity_id"]} for r in sorted(rows, key=lambda x: x.result["sequence"])]}


@router.post("/commands")
def command(tenant_id: str, campaign_id: str, body: SandboxCommand, user: Annotated[User, Depends(current_user)],
            db: Annotated[Session, Depends(get_db)]):
    return apply_command(tenant_id,campaign_id,body,user,db)


def apply_command(tenant_id, campaign_id, body, user, db, *, dispatched=False):
    before = campaign_store(db, user, tenant_id, campaign_id, write=False)
    if not before.approver:
        missing()
    # The Studio/share path locks the document before acquiring client/brand locks. Keep that order for execution.
    did = body.deliverable_id if isinstance(body, Schedule) else None
    if isinstance(body, (DecideAction, Execute)) and body.kind != "cancel":
        action = state_of(entries(before, campaign_id))["actions"].get(body.action_id)
        did = action["deliverable_id"] if action else None
    if did:
        if not db.scalar(select(Deliverable.id).filter_by(id=did, tenant_id=tenant_id, campaign_id=campaign_id)):
            missing()
        working_copy(db, tenant_id, did)
    store = campaign_store(db, user, tenant_id, campaign_id, write=True)
    if not store.approver:
        missing()
    rows = entries(store, campaign_id)
    key = "sandbox:" + digest(canonical([campaign_id, body.request_id]))
    payload = body.model_dump(mode="json")
    if isinstance(body,Schedule) and body.target is None:
        payload.pop("target",None)  # Preserve retries of document schedules written by the earlier contract.
    fingerprint = digest(canonical(["local_dispatcher",payload] if dispatched else payload))
    existing = next((r for r in rows if r.key == key), None)
    if existing:
        if existing.actor != user.id or existing.request_digest != fingerprint:
            conflict("Request ID belongs to another actor or payload")
        return existing.result
    state = state_of(rows)
    if body.kind in {"cancel", "sales", "complete_rfq", "session", "labor", "close_unit_cost", "unit_receipt","appointment_decision","verify_unit_cost"}:
        # Settling previously booked work, including refunds, survives replans or source expiry.
        plan = next((p for p in history(store, campaign_id) if p["id"] == body.plan_id and p["approval"]), None)
        if not plan:
            missing()
    else:
        plan = active_plan(store, campaign_id)
    if body.plan_id != plan["id"]:
        conflict("Campaign revision is no longer active")
    if isinstance(body, (Schedule, DecideAction, Execute)):
        kind, ident, value = action_command(body, state, plan, store, user, campaign_id, dispatched=dispatched)
    elif isinstance(body,(Appointment,AppointmentDecision)):
        kind, ident, value = appointments.appointment(body,state,plan,store)
    elif isinstance(body, (RFQ, SessionEvent, Sales, CompleteRFQ)):
        kind, ident, value = observation(body, state, plan, store)
    elif isinstance(body, Optimization):
        kind, ident, value = optimize_command(body, state, store, plan)
    else:
        kind, ident, value = work_receipt(body, state, plan, store, campaign_id, rows)
    event = append(store, campaign_id, body.plan_id, body.kind, kind, ident, value, len(rows) + 1, key, fingerprint)
    db.commit()
    return event


def dispatch_service(request):
    secret = os.getenv("AMC_SANDBOX_DISPATCH_KEY","")
    supplied = request.headers.get("X-AMC-Sandbox-Dispatch","")
    if (not request.client or request.client.host not in {"127.0.0.1","::1"} or len(secret) < 32
            or not hmac.compare_digest(secret.encode(),supplied.encode())):
        missing()


@router.get("/dispatch-ready")
def dispatch_ready(tenant_id: str,campaign_id: str,request: Request,after: str="",limit: int=Query(10,ge=1,le=25),
                   user: User=Depends(current_user),db: Session=Depends(get_db)):
    dispatch_service(request)
    store = campaign_store(db,user,tenant_id,campaign_id,write=False)
    if not store.approver:
        missing()
    active = next((p for p in history(store,campaign_id) if p["approval"]),None)
    if not active:
        return []
    now = aware(store.now())
    rows = state_of(entries(store,campaign_id))["actions"].values()
    due = [a for a in rows if a["plan_id"]==active["id"] and a.get("execution_mode")=="scheduled"
           and a["state"] in ("authorized","failed") and a["attempts"]<3 and parse_time(a["due_at"])<=now]
    ordered = sorted(due,key=lambda a:(a["id"] <= after,a["id"]))
    return [{"action_id":a["id"],"plan_id":a["plan_id"],"attempts":a["attempts"]} for a in ordered[:limit]]


@router.post("/dispatch")
def dispatch(tenant_id: str,campaign_id: str,request: Request,body: Execute,user: User=Depends(current_user),db: Session=Depends(get_db)):
    dispatch_service(request)
    if body.outcome != "success":
        conflict("Dispatcher executes only a real local sandbox operation")
    return apply_command(tenant_id,campaign_id,body,user,db,dispatched=True)
