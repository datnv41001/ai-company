"""Read-only RFQ explanation for verified synthetic fixtures. No application or database adapter.

Callers supply an already scoped, allowlisted offline fixture. This module is not an
authorization boundary for reading production journals or for approving qualification.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json


SCOPE_KEYS = ("tenant_id", "client_id", "brand_id", "campaign_id")
ARCHIVE_COMMIT = "db862100aabf76641fe93fd207868c095f9027eb"
ARCHIVE_PATH = "docs/evaluation/round60-verification/artifacts/journey/wf08-v2/receipt.json"
ARCHIVE_SHA256 = "78bf3434b29df64d1fd7777f6ea884174d2a92c6c4c69a435c3c3b11748e7d61"
DISCRETE = {"piece", "box", "machine", "visit", "participant", "subscription_month", "subscription_year", "service"}
STAGES = {"sales_acceptance": "sales_accepted", "quote": "quoted", "order": "ordered", "confirmed_revenue": "confirmed"}


def _time(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if not isinstance(dt, datetime) or dt.utcoffset() is None:
        raise ValueError("An offset-aware timestamp is required")
    return dt.astimezone(timezone.utc)


def _number(value):
    try:
        number = Decimal(str(value))
        if number.is_finite() and number > 0:
            return number
    except InvalidOperation:
        pass
    return None


def _visible(events, scope, cutoff):
    by_id, by_sequence = {}, {}
    for event in events:
        if _time(event["recorded_at"]) > cutoff:
            continue
        source = event["value"].get("landing_source") or {}
        if any(k in envelope and envelope[k] != scope[k]
               for envelope in (event, event.get("scope", {}), source) for k in SCOPE_KEYS):
            raise ValueError("Receipt scope mismatch")
        if (event["campaign_id"] != scope["campaign_id"] or not event.get("id")
                or event["entity_id"] != event["value"]["id"] or event["plan_id"] != event["value"]["plan_id"]
                or not isinstance(event["sequence"], int) or event["sequence"] <= 0):
            raise ValueError("Receipt identity, plan or sequence mismatch")
        if event["id"] in by_id:
            if event != by_id[event["id"]]:
                raise ValueError("Contradictory receipt replay")
            continue
        if event["sequence"] in by_sequence:
            raise ValueError("Journal sequence collision")
        by_id[event["id"]] = event
        by_sequence[event["sequence"]] = event
    return [by_sequence[k] for k in sorted(by_sequence)]


def _attribution(scope, submission, events):
    row = submission["value"]
    source = row.get("landing_source") or {}
    visit = next((e for e in events if e["entity"] == "sessions" and e["kind"] == "session"
                  and e["entity_id"] == row.get("session_id") and e["plan_id"] == submission["plan_id"]), None)
    contract = row.get("intake") or {}
    def bound(value):
        return (source.get("package_id") and source["package_id"] == value.get("landing_package")
                and source.get("package_digest") and source["package_digest"] == value.get("landing_digest"))
    linked = (visit and visit["value"].get("landing_source") == source
              and all(source.get(k) == scope[k] for k in SCOPE_KEYS)
              and source.get("plan_id") == submission["plan_id"]
              and source.get("plan_digest") and source.get("document_id") and source.get("studio_revision")
              and source.get("intake_contract_digest") and source["intake_contract_digest"] == contract.get("contract_digest")
              and bound(row) and bound(visit["value"])
              and visit["value"].get("occurred_at") and row.get("occurred_at")
              and _time(visit["value"]["occurred_at"]) <= _time(row["occurred_at"]))
    if not linked:
        return {"status": "unlinked", "submission_receipt": submission["id"]}
    # Two events carrying the same pointer can link the visit and submission.
    # Corroborating the creative requires its distinct distribution receipt.
    return {"status": "landing_to_submission", "creative": None,
            "plan_digest": source["plan_digest"], "document_id": source["document_id"],
            "landing_revision": source["studio_revision"], "landing_package": source["package_id"],
            "package_digest": source["package_digest"], "intake_contract_digest": source["intake_contract_digest"],
            "visit_receipt": visit["id"], "submission_receipt": submission["id"]}


def _commercial(scope, event, cutoff, policy):
    row = event["value"]
    intake = row.get("intake") or {}
    source = row.get("landing_source") or {}
    # The native receipt records a threshold snapshot. It does not store an independently
    # approved policy, expiry, SKU, or a qualification decision.
    moqs = row.get("minimum_order_quantities", [])
    result = {"status": "unknown_moq", "recorded_minimums": list(moqs), "unit": row.get("unit"),
              "receipt_id": event["id"], "plan_id": event["plan_id"], "contract_digest": intake.get("contract_digest"),
              "contract_revision": intake.get("revision"), "policy": None,
              "consent": "recorded_at_intake" if (intake.get("consent") or {}).get("granted") is True else "unknown"}
    consent = intake.get("consent") or {}
    quantity = _number(row.get("quantity"))
    mapped_units = {f.get("unit") for f in intake.get("fields", []) if f.get("maps_to") == "quantity" and f.get("unit")}
    policy_visible = policy is not None and _time(policy["recorded_at"]) <= cutoff
    status = None
    if policy_visible:
        if (policy["scope"] != scope or policy["plan_id"] != event["plan_id"] or policy["product_id"] != row.get("product_id")
                or policy.get("provenance") != "synthetic_sales_operations_fixture"):
            raise ValueError("Policy fixture scope, product or provenance mismatch")
        result["policy"] = {k: policy.get(k) for k in ("id", "revision", "recorded_at", "valid_from", "valid_until",
                                                        "unit", "mode", "minimum", "status")}
        if policy.get("status") != "active":
            status = "policy_revoked"
        elif cutoff < _time(policy["valid_from"]) or (policy.get("valid_until") and cutoff >= _time(policy["valid_until"])):
            status = "policy_outside_validity"
        elif policy.get("unit") != row.get("unit"):
            status = "unit_mismatch"
        elif policy.get("mode") == "not_applicable":
            status = "conflicting_moq" if moqs else "explicit_no_minimum"
        elif policy.get("mode") == "minimum":
            if not _number(policy.get("minimum")):
                status = "unknown_moq"
            elif moqs and any(_number(m) != _number(policy["minimum"]) for m in moqs):
                status = "conflicting_moq"
            else:
                moqs = [policy["minimum"]]
        else:
            status = "unknown_moq"
    if (row.get("contact_purpose") != "quote_request" or consent.get("granted") is False
            or consent.get("purpose") not in (None, "quote_request")
            or (consent.get("revoked_at") and _time(consent["revoked_at"]) <= cutoff)
            or (consent.get("valid_until") and cutoff >= _time(consent["valid_until"]))):
        result["consent"] = "unavailable"
        status = "consent_unavailable"
    elif source.get("revoked_at") and _time(source["revoked_at"]) <= cutoff:
        status = "source_revoked"
    elif mapped_units and mapped_units != {row.get("unit")}:
        status = "unit_mismatch"
    elif not row.get("unit") or not quantity or (row["unit"] in DISCRETE and quantity != quantity.to_integral_value()):
        status = "invalid_quantity_or_unit"
    if status is None:
        thresholds = {_number(m) for m in moqs}
        if None in thresholds or not thresholds:
            status = "unknown_moq"
        elif len(thresholds) > 1:
            status = "conflicting_moq"
        else:
            status = "below_minimum" if quantity < thresholds.pop() else "meets_recorded_minimum"
    result["status"] = status
    return result


def _history(events):
    history, milestones = [], {k: None for k in STAGES}
    plan = events[0]["plan_id"]
    product = events[0]["value"]["product_id"]
    for revision, event in enumerate(events, 1):
        row = event["value"]
        if (row["revision"] != revision or event["plan_id"] != plan or row["product_id"] != product
                or (revision == 1) != (event["kind"] == "rfq")
                or event["kind"] not in ("rfq", "complete_rfq", "consultation", "sales")):
            raise ValueError("Incomplete or contradictory inquiry history")
        # CompleteRFQ copies both timestamps from the earlier row. Neither dates this amendment.
        occurred = row.get("occurred_at") if revision == 1 else (
            row.get("last_event_at") if event["kind"] in ("consultation", "sales") else None)
        if occurred and _time(occurred) > _time(event["recorded_at"]):
            raise ValueError("Business event time exceeds its journal record")
        item = {"receipt_id": event["id"], "sequence": event["sequence"], "revision": revision,
                "kind": event["kind"], "step": event.get("step"), "state": row["state"],
                "recorded_at": event["recorded_at"], "occurred_at": occurred}
        history.append(item)
        for name, flag in STAGES.items():
            if row[flag] and milestones[name] is None:
                expected_state = {"sales_acceptance": "accepted", "quote": "quoted",
                                  "order": "ordered", "confirmed_revenue": "confirmed"}[name]
                if event["kind"] != "sales" or row["state"] != expected_state:
                    raise ValueError("Commercial milestone lacks its own Sales receipt")
                milestones[name] = event["id"]
        if row.get("confirmed"):
            # Preserve original amounts as well as later corrections/refunds.
            item.update(sandbox_gross_vnd=row["gross_vnd"], sandbox_refunded_vnd=row["refunded_vnd"])
    terminal = events[-1]["value"]["state"] in ("cancelled", "rejected")
    stages = {k: {"status": "sandbox_recorded" if ident else "no_receipt", "receipt_id": ident}
              for k, ident in milestones.items()}
    for stage in stages.values():
        if terminal and stage["receipt_id"]:
            stage["current_disposition"] = events[-1]["value"]["state"]
    if stages["confirmed_revenue"]["receipt_id"]:
        row = events[-1]["value"]
        stages["confirmed_revenue"]["sandbox_net_vnd"] = 0 if terminal else row["gross_vnd"] - row["refunded_vnd"]
    return history, stages


def _action(commercial, row):
    status = commercial["status"]
    if row["state"] in ("rejected", "cancelled"):
        return {"owner": "Sales Operations", "action": "Keep the closed inquiry in history."}
    if status == "consent_unavailable":
        return {"owner": "Sales Operations", "action": "Hold contact; verify consent and permitted purpose."}
    if status == "below_minimum":
        return {"owner": "Offer owner / Sales Operations",
                "action": "Verify the recorded minimum and who may authorize an exception before routing."}
    if status not in ("explicit_no_minimum", "meets_recorded_minimum"):
        return {"owner": "Offer owner", "action": "Resolve the commercial condition, unit and applicable source."}
    if row["missing"]:
        return {"owner": "Sales Operations", "action": "Review missing intake fields and permitted follow-up."}
    if row["state"] in ("accepted", "quoted", "ordered", "confirmed"):
        return {"owner": "Authorized Sales recipient", "action": "Review the latest recorded Sales step and any correction."}
    return {"owner": "Sales Operations", "action": "Review evidence and route through the existing authorized desk."}


def build_card(*, scope, inquiry_id, events, recorded_as_of, generated_at, policy=None):
    """Project one scoped synthetic case. A cutoff restricts evidence, never grants access."""
    scope = {k: scope[k] for k in SCOPE_KEYS}
    if not all(isinstance(v, str) and v for v in scope.values()) or not inquiry_id:
        raise ValueError("A complete case scope is required")
    cutoff, generated = _time(recorded_as_of), _time(generated_at)
    if cutoff > generated:
        raise ValueError("Cutoff exceeds report time")
    visible = _visible(events, scope, cutoff)
    leads = [e for e in visible if e["entity"] == "leads" and e["entity_id"] == inquiry_id]
    if not leads:
        raise LookupError("No inquiry known at this recorded cutoff")
    history, milestones = _history(leads)
    latest = leads[-1]
    row = latest["value"]
    commercial = _commercial(scope, latest, cutoff, policy)
    commercial["origin_receipt_id"] = leads[0]["id"]
    feedback = {"observation": {"receipt_id": latest["id"], "revision": row["revision"], "quantity": row["quantity"],
                                "unit": row["unit"], "condition": commercial["status"]},
                "missing_evidence": ["Buyer explanation", "Comparable inquiries under the same offer and intake revision"],
                "hypotheses": [], "owner": "Marketing operator with offer owner",
                "verification": "Compare permitted, de-identified intake observations under the same contract revision.",
                "proposed_next_step": "Request a scoped review of the offer and intake wording."}
    if commercial["status"] == "below_minimum":
        feedback.update(hypotheses=["The intake wording may leave the minimum unclear.", "A buyer may be requesting a sample."],
                        verification="Review the exact published wording, then compare independent inquiries and permitted buyer explanations.")
    attribution = _attribution(scope, leads[0], visible)
    unknowns = ["Official qualification decision", "Real commercial documents and revenue",
                "Buyer motivation", "Current consent outside the archived receipts"]
    if not row.get("sku"):
        unknowns.append("SKU")
    if commercial["policy"] is None:
        unknowns.append("Approved policy revision and effective interval")
    if any(event["occurred_at"] is None for event in history):
        unknowns.append("Business time of undated amendment")
    if attribution["status"] != "creative_to_submission":
        unknowns.append("Complete creative-to-submission lineage")
    return {"contract": "rfq-qualification/1", "contract_status": "proposed", "environment": "synthetic_offline",
            "scope": scope, "inquiry_id": inquiry_id, "revision": row["revision"],
            "recorded_as_of": cutoff.isoformat(), "generated_at": generated.isoformat(),
            "request": {k: row.get(k) for k in ("product_id", "sku", "unit", "quantity", "location", "required_date", "contact_purpose")},
            "rule": {"status": "incomplete" if row["missing"] else "complete", "missing": list(row["missing"]),
                     "recorded_state": row["state"], "receipt_id": latest["id"]},
            "commercial": commercial, "qualification": {"status": "no_authorized_receipt", "receipt_id": None,
                                                         "decision_owner": "Sales Operations or authorized delegate"},
            "assignment": {"assignee_id": row.get("assignee_id"), "receipt_id": latest["id"]},
            "milestones": milestones, "attribution": attribution, "history": history, "feedback": feedback,
            "next_step": _action(commercial, row), "unknowns": unknowns}


def _canonical_digest(value):
    # Match the existing knowledge_store.canonical convention without importing product runtime.
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def with_plan_provenance(card, plan):
    """Resolve product labels only from the pinned synthetic extraction of an observed plan."""
    receipt, request, attribution = card["commercial"], card["request"], card["attribution"]
    approval, contract = plan["approval"], plan["intake_contract"]
    cutoff = _time(card["recorded_as_of"])
    if _time(approval["at"]) > cutoff:
        return card
    # Approval.at is the existing command's effective_at. The inquiry independently
    # carries this plan digest at a known journal sequence; do not call effective_at recorded_at.
    snapshot = plan["plan_snapshot"]
    if (_canonical_digest(snapshot) != plan["digest"] or snapshot["scope"] != card["scope"]
            or snapshot["campaign_id"] != card["scope"]["campaign_id"] or snapshot["id"] != plan["plan_id"]
            or snapshot["selling_unit"] != request["unit"] or snapshot["intake_contract"] != contract
            or snapshot["manifests"]["landing"] != plan["manifest"]
            or any(snapshot[k] != plan[k] for k in ("revision", "product_id", "product", "sku"))
            or not approval.get("receipt") or not approval.get("actor")
            or attribution["status"] not in ("landing_to_submission", "creative_to_submission")
            or attribution.get("plan_digest") != plan["digest"]
            or not (plan["plan_id"] == receipt["plan_id"] == contract["plan_id"])
            or not (plan["product_id"] == request["product_id"] == contract["subject"])
            or not (plan["revision"] == receipt["contract_revision"] == contract["revision"])
            or contract["version"] != "business-intake/1" or contract["action"] != "rfq"
            or contract["unit"] != request["unit"] or contract["source"] != plan["manifest"]
            or contract["qualification"]["minimum_order_quantities"] != receipt["recorded_minimums"]
            or not (contract["digest"] == receipt["contract_digest"] == attribution["intake_contract_digest"])
            or contract["digest"] != _canonical_digest({k: v for k, v in contract.items() if k != "digest"})):
        raise ValueError("Synthetic plan, subject or intake contract linkage mismatch")
    metadata = {"plan_id": plan["plan_id"], "plan_revision": plan["revision"], "plan_digest": plan["digest"],
                "approval_receipt": approval["receipt"], "approval_effective_at": approval["at"],
                "plan_digest_observed_by": card["history"][0]["recorded_at"],
                "observing_submission_receipt": attribution["submission_receipt"], "manifest": plan["manifest"]}
    return {**card, "request": {**request, "product_name": plan["product"], "sku": plan["sku"]},
            "plan_provenance": metadata,
            "unknowns": [item for item in card["unknowns"] if item != "SKU" or not plan["sku"]]}


def archived_khe_gon(data, *, generated_at=None):
    """Pin raw archive bytes before parsing; the accepted receipt is never modified."""
    if sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Archive digest mismatch")
    receipt = json.loads(data)
    visit, submission = receipt["visit"], receipt["submission"]
    scope = receipt["distribution"]["scope"]
    card = build_card(scope=scope, inquiry_id=submission["entity_id"], events=[visit, submission],
                      recorded_as_of=submission["recorded_at"], generated_at=generated_at or datetime.now(timezone.utc))
    distribution = receipt["distribution"]
    landing, board = distribution["landing"], distribution["storyboard"]
    authority = receipt["measurement_authority"]
    source = submission["value"]["landing_source"]
    creative = {"id": distribution["id"], "digest": distribution["distribution_digest"],
                "run_id": board["run_id"], "revision": board["revision"],
                "preview_sha256": distribution["preview"]["file_digest"], "preview_qa": distribution["preview_qa"]["receipt"]}
    if (card["attribution"]["status"] != "landing_to_submission"
            or any(source.get(k) != landing[k] for k in ("plan_id", "plan_digest", "package_id", "package_digest", "file_digest", "document_id"))
            or source["studio_revision"] != landing["revision"] or source["storyboard_distribution"] != creative
            or authority["approved_plan_id"] != landing["plan_id"] or authority["plan_digest"] != landing["plan_digest"]
            or any(authority["landing_manifest"][k] != v for k, v in landing["manifest"].items())):
        raise ValueError("Pinned archive creative or authority linkage mismatch")
    card["attribution"].update(status="creative_to_submission", creative=creative, landing_manifest=landing["manifest"])
    card["unknowns"].remove("Complete creative-to-submission lineage")
    card["request"]["product_name"] = receipt["task_intent"]["product"]
    card["evidence_source"] = {"commit": ARCHIVE_COMMIT, "path": ARCHIVE_PATH, "sha256": ARCHIVE_SHA256}
    card["archived_measurement"] = {"intake_funnel": receipt["measurement"], "primary_measurement": receipt["primary_kpi"]}
    return card
