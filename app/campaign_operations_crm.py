"""RFQ intake, Sales decisions and reconciled simulated revenue. No external adapter."""
from .campaign_operations_contracts import CompleteRFQ, RFQ, Sales, SessionEvent
from .knowledge_store import aware, conflict, parse_time, stamp
from .models import Membership


DISCRETE_UNITS = {"piece", "box", "machine", "visit", "participant", "subscription_month", "subscription_year", "service"}
DETAIL_UNITS = {
    "materials_v1": {"piece", "box", "m²", "tonne", "kg"},
    "service_v1": {"machine", "visit", "service"},
    "seats_v1": {"participant", "subscription_month", "subscription_year"},
}
FROM = {
    "assign": {"qualified"}, "reassign": {"assigned"}, "accept": {"assigned"}, "reject": {"received", "qualified", "assigned", "accepted", "quoted"},
    "quote": {"accepted"}, "order": {"quoted"}, "confirm": {"ordered"}, "refund": {"confirmed"},
    "cancel": {"assigned", "accepted", "quoted", "ordered", "confirmed"}, "correct": {"confirmed"},
}
STATES = {"assign": "assigned", "reassign":"assigned", "accept": "accepted", "reject": "rejected", "quote": "quoted",
          "order": "ordered", "confirm": "confirmed", "refund": "confirmed", "cancel": "cancelled", "correct": "confirmed"}


def quantity_fields(cmd, unit):
    if cmd.details and unit not in DETAIL_UNITS[cmd.details.schema_id]:
        conflict("The selected commercial detail contract does not apply to this selling unit")
    if cmd.quantity is not None and unit in DISCRETE_UNITS and cmd.quantity != cmd.quantity.to_integral_value():
        conflict("This approved selling unit requires a whole quantity")
    return {"quantity": format(cmd.quantity, "f") if cmd.quantity is not None else None,
            "location": cmd.location, "required_date": cmd.required_date.isoformat() if cmd.required_date else None,
            "contact_purpose": cmd.contact_purpose,
            **({"details": cmd.details.model_dump()} if cmd.details else {})}


def missing_fields(row):
    fields = [key for key in ("quantity", "location", "required_date") if not row[key]]
    if row["contact_purpose"] != "quote_request":
        fields.append("permission_to_respond")
    return fields


def observation(cmd, state, plan, store, *, recipient=None, coordinator=None):
    if isinstance(cmd, (RFQ, Sales, SessionEvent)) and cmd.occurred_at > aware(store.now()):
        conflict("A received event cannot occur in the future")
    if isinstance(cmd, SessionEvent):
        if cmd.session_id in state["sessions"]:
            conflict("Session already recorded; use the original idempotency key")
        if cmd.action_id is not None:
            action = state["actions"].get(cmd.action_id)
            if not action or action["plan_id"] != plan["id"] or action["state"] != "executed":
                conflict("Session attribution needs an executed action in this plan")
            if cmd.occurred_at < parse_time(action["executed_at"]):
                conflict("Session precedes simulated execution")
        return "sessions", cmd.session_id, {"id": cmd.session_id, "visitor": cmd.actor_key, "action_id": cmd.action_id,
                                           "occurred_at": stamp(cmd.occurred_at), "plan_id": plan["id"]}
    if isinstance(cmd, RFQ):
        if plan["buyer_action"]!="rfq" and "rfq" not in plan.get("secondary_conversions",[]):
            conflict("Quote intake requires a primary or explicitly approved secondary RFQ conversion")
        if cmd.product_id != plan["product_id"] or cmd.unit != plan["selling_unit"]:
            conflict("Product and selling unit must match the approved plan")
        if cmd.rfq_id in state["leads"]:
            conflict("RFQ identifier already exists; use the original request or correct the existing lead")
        row = {"id": cmd.rfq_id, "revision": 1, "plan_id": plan["id"], "session_id": cmd.session_id,
               "product_id": cmd.product_id, "unit": cmd.unit, "occurred_at": stamp(cmd.occurred_at),
               "last_event_at": stamp(cmd.occurred_at), **quantity_fields(cmd, cmd.unit),
               "assignee_id": None, "gross_vnd": 0, "refunded_vnd": 0, "sales_accepted": False,
               "quoted": False, "ordered": False, "confirmed": False, "feedback": []}
        row["missing"] = missing_fields(row)
        row["state"] = "received" if row["missing"] else "qualified"
        return "leads", cmd.rfq_id, row

    row = state["leads"].get(cmd.rfq_id)
    if not row or row["plan_id"] != plan["id"] or cmd.expected_revision != row["revision"]:
        conflict("RFQ is absent from this plan or its revision changed")
    row = {**row, "revision": row["revision"] + 1}
    if isinstance(cmd, CompleteRFQ):
        if row["state"] != "received":
            conflict("Only an incomplete request can be completed")
        row.update(quantity_fields(cmd, row["unit"]), missing=[], state="qualified")
        return "leads", cmd.rfq_id, row
    if row["state"] not in FROM[cmd.step] or cmd.occurred_at < parse_time(row["last_event_at"]):
        conflict("Invalid or out-of-order Sales transition")
    can_route=store.approver if coordinator is None else coordinator
    if not can_route and row["assignee_id"] != store.actor:
        conflict("Sales decisions require the assigned staff member or a campaign approver")
    if cmd.step in ("assign","reassign"):
        if recipient:
            eligible=cmd.assignee_id and recipient(cmd.assignee_id,"sales_recipient")
        else:
            assigned = store.db.get(Membership, {"tenant_id": store.scope["tenant_id"], "user_id": cmd.assignee_id}) if cmd.assignee_id else None
            eligible=assigned and assigned.role in ("admin","owner")
        if not can_route or not eligible or cmd.step=="reassign" and row["assignee_id"]==cmd.assignee_id:
            conflict("Assign a current staff member of this organization")
        row["assignee_id"] = cmd.assignee_id
    elif cmd.assignee_id is not None:
        conflict("Assignee is only set by the assignment command")
    if cmd.step in {"reject", "cancel", "correct", "refund", "accept","reassign"} and not cmd.reason:
        conflict("Record the Sales feedback or correction reason")
    if cmd.reason:
        row["feedback"] = [*row["feedback"], {"step": cmd.step, "text": cmd.reason, "actor": store.actor}]
    if cmd.step in ("confirm", "correct", "refund"):
        if not cmd.amount_vnd or (cmd.step == "correct" and cmd.amount_vnd < row["refunded_vnd"]):
            conflict("Valid confirmed or refunded VND amount required")
        if cmd.step == "refund":
            if row["refunded_vnd"] + cmd.amount_vnd > row["gross_vnd"]:
                conflict("Refund would exceed the confirmed total")
            row["refunded_vnd"] += cmd.amount_vnd
        else:
            row["gross_vnd"] = cmd.amount_vnd
    elif cmd.amount_vnd is not None:
        conflict("Amounts are recorded at order confirmation, correction or refund")
    if cmd.step in ("accept", "quote", "order", "confirm"):
        row[{"accept": "sales_accepted", "quote": "quoted", "order": "ordered", "confirm": "confirmed"}[cmd.step]] = True
    row.update(state=STATES[cmd.step], last_event_at=stamp(cmd.occurred_at))
    return "leads", cmd.rfq_id, row


def reconcile(state):
    from .campaign_operations_appointments import summary as appointment_summary
    leads, actions, sessions = state["leads"].values(), state["actions"], state["sessions"]
    confirmed = [lead for lead in leads if lead["confirmed"] and lead["state"] != "cancelled"]
    def attribution(lead):
        # Resolve delayed session intake at report time, with plan and occurrence-time checks.
        session = sessions.get(lead["session_id"])
        if not session or session["plan_id"] != lead["plan_id"] or parse_time(session["occurred_at"]) > parse_time(lead["occurred_at"]):
            return None
        return session["action_id"]
    revenue = sum(row["gross_vnd"] - row["refunded_vnd"] for row in confirmed)
    attributed = sum(row["gross_vnd"] - row["refunded_vnd"] for row in confirmed if attribution(row))
    breakdown = {}
    for row in confirmed:
        action = actions.get(attribution(row))
        if action:
            asset = action["deliverable_id"] + "@" + str(action["asset_revision"])
            breakdown[asset] = breakdown.get(asset, 0) + row["gross_vnd"] - row["refunded_vnd"]
    return {"synthetic": True, "appointments":appointment_summary(state) if "appointments" in state else {},
            "visitors": len({s["visitor"] for s in sessions.values()}), "sessions": len(sessions),
            "rfqs": len(leads), "qualified_leads": sum(not r["missing"] for r in leads),
            "sales_accepted": sum(r["sales_accepted"] for r in leads), "quotations": sum(r["quoted"] for r in leads),
            "orders": sum(r["ordered"] for r in leads), "confirmed_orders": len(confirmed),
            "cancelled_orders": sum(r["ordered"] and r["state"] == "cancelled" for r in leads),
            "refunds_vnd": sum(r["refunded_vnd"] for r in leads), "missing_attribution": sum(not attribution(r) for r in leads),
            "simulated_spend_vnd": sum(a["cost_vnd"] for a in actions.values() if a["state"] == "executed"),
            "confirmed_revenue_vnd": revenue, "attributed_revenue_vnd": attributed,
            "unattributed_revenue_vnd": revenue - attributed, "attributed_by_asset_vnd": breakdown}
