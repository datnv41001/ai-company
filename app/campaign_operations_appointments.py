"""Service appointments use their own consent, calendar and confirmed service outcome."""
from .campaign_operations_contracts import Appointment
from .campaign_operations_crm import DISCRETE_UNITS
from .knowledge_store import aware, conflict, parse_time, stamp
from .models import Membership


TRANSITIONS = {"confirm": ({"requested"}, "confirmed"), "assign": ({"confirmed"}, "assigned"),
               "reassign": ({"assigned"}, "assigned"), "reschedule": ({"confirmed","assigned"}, None),
               "complete": ({"assigned"}, "completed"), "cancel": ({"requested","confirmed","assigned"}, "cancelled"),
               "no_show": ({"assigned","confirmed"}, "no_show")}


def appointment(cmd, state, plan, store, *, recipient=None):
    occurred = aware(cmd.occurred_at)
    if occurred > aware(store.now()):
        conflict("Appointment event is in the future")
    prior = state["appointments"].get(cmd.appointment_id)
    if isinstance(cmd, Appointment):
        if plan["buyer_action"] != "appointment" or cmd.product_id != plan["product_id"] or cmd.unit != plan["selling_unit"]:
            conflict("Appointment requires the approved service, unit and buyer action")
        if (cmd.requested_for is not None and cmd.requested_for < occurred) or prior:
            conflict("Invalid appointment time or duplicate appointment ID")
        if cmd.quantity is not None and cmd.unit in DISCRETE_UNITS and cmd.quantity != cmd.quantity.to_integral_value():
            conflict("This service uses a whole selling unit")
        row = {"id":cmd.appointment_id, "plan_id":plan["id"], "revision":1, "state":"requested",
               "assignee_id":None, "confirmed_for":None, "history":[], **cmd.model_dump(mode="json",exclude={"kind","request_id","appointment_id"})}
    else:
        if not prior or prior["plan_id"] != plan["id"] or cmd.expected_revision != prior["revision"]:
            conflict("Appointment is absent or its revision changed")
        allowed, next_state = TRANSITIONS[cmd.step]
        if prior["state"] not in allowed or occurred < parse_time(prior["last_event_at"]):
            conflict("Invalid appointment transition or time")
        if cmd.step == "complete" and prior["assignee_id"] != store.actor:
            conflict("Only the assigned staff member may confirm the service they performed")
        if bool(cmd.assignee_id) != (cmd.step in {"assign","reassign"}) or bool(cmd.confirmed_for) != (cmd.step in {"confirm","reschedule"}):
            conflict("Use assignment and confirmed time only on their corresponding steps")
        row = {**prior,"state":next_state or prior["state"],"revision":prior["revision"]+1}
        if cmd.step in ("confirm","reschedule"):
            if cmd.confirmed_for < occurred:
                conflict("The confirmed service time precedes confirmation")
            row["confirmed_for"] = stamp(cmd.confirmed_for)
        if cmd.step in ("assign","reassign"):
            if recipient:
                eligible = recipient(cmd.assignee_id,"service_assignee")
            else:
                membership = store.db.get(Membership, {"tenant_id":store.scope["tenant_id"],"user_id":cmd.assignee_id})
                eligible = membership and membership.role in ("admin","owner")
            if not eligible or cmd.step=="reassign" and prior["assignee_id"]==cmd.assignee_id:
                conflict("Assign a staff member authorized to operate this campaign")
            row["assignee_id"] = cmd.assignee_id
        if cmd.step in ("no_show","complete") and occurred < parse_time(prior["confirmed_for"]):
            conflict("Service outcome cannot precede the confirmed appointment time")
        if cmd.step in ("cancel","no_show","complete","reschedule","reassign") and not cmd.feedback:
            conflict("Record service outcome and feedback")
    row["last_event_at"] = stamp(occurred)
    event={"event":row["state"],"actor":store.actor,"at":row["last_event_at"],"feedback":getattr(cmd,"feedback",None)}
    if getattr(cmd,"step",None) in {"assign","reassign","reschedule"}:
        event.update(step=cmd.step, assignee_id=row["assignee_id"], confirmed_for=row["confirmed_for"])
    row["history"] = [*row["history"], event]
    return "appointments",cmd.appointment_id,row


def summary(state):
    appointments = list(state["appointments"].values())
    attributed = 0
    for row in appointments:
        session = state["sessions"].get(row["session_id"])
        if session and session["plan_id"] == row["plan_id"] and session["action_id"] and parse_time(session["occurred_at"]) <= parse_time(row["occurred_at"]):
            attributed += 1
    return {"requests":len(appointments), "confirmed":sum(any(h["event"]=="confirmed" for h in a["history"]) for a in appointments),
            **{status:sum(a["state"]==status for a in appointments) for status in ("assigned","completed","cancelled","no_show")},
            "attributed":attributed,"unattributed":len(appointments)-attributed}
