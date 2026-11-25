"""Pure replay of the synthetic CRM event contract. Amounts are integer VND."""
from .knowledge_store import canonical


TRANSITIONS = {
    "sales_handoff": ({"qualified"}, "handed_off"),
    "quotation": ({"handed_off"}, "quoted"),
    "order": ({"quoted"}, "ordered"),
    "confirmed": ({"ordered"}, "confirmed"),
    "cancelled": ({"ordered", "confirmed"}, "cancelled"),
    "rejected": ({"received", "qualified", "handed_off", "quoted"}, "rejected"),
}


def reconcile(events, actions):
    """Event time wins over receipt order. Invalid transitions remain visible for reconciliation."""
    receipts = {key: a["receipt"] for key, a in actions.items() if a["state"] == "executed"}
    seen, unique, exceptions = {}, [], []
    duplicates = 0
    latest = 0
    delayed = []
    for n, event in enumerate(events):
        event_id = event["event_id"]
        stamp = canonical(event)
        if event_id in seen:
            if seen[event_id] != stamp:
                raise ValueError("Conflicting payload for event " + event_id)
            duplicates += 1
            continue
        if type(event["at"]) is not int or event["at"] < 1:
            raise ValueError("Invalid occurrence day")
        if event["at"] < latest:
            delayed.append(event_id)
        latest = max(latest, event["at"])
        seen[event_id] = stamp
        unique.append((event["at"], n, event))

    sessions, leads, submissions = {}, {}, {}
    for at, _, event in sorted(unique):
        kind = event["type"]
        if kind == "session":
            session_id = event["session_id"]
            if session_id in sessions:
                raise ValueError("Conflicting session " + session_id)
            slot = event["action_id"]
            receipt = receipts.get(slot)
            attributed = bool(receipt and receipt["day"] <= at)
            sessions[session_id] = {"action_id": slot if attributed else None, "event_id": event["event_id"],
                                    "visitor_id": event["visitor_id"]}
            if slot and not attributed:
                exceptions.append({"event_id": event["event_id"], "reason": "unverified_execution"})
            continue
        lead_id = event["rfq_id"]
        if kind == "rfq":
            # Customer-supplied request ID is the second dedup key across retries with a new event ID.
            submission = {k: v for k, v in event.items() if k not in {"event_id", "at"}}
            if lead_id in leads:
                if submissions[lead_id] != submission:
                    raise ValueError("Conflicting RFQ submission " + lead_id)
                duplicates += 1
                continue
            submissions[lead_id] = submission
            required = ("district", "required_by")
            complete = (type(event.get("area_m2")) is int and event["area_m2"] > 0
                        and all(isinstance(event.get(k), str) and event[k].strip() for k in required))
            qualified = bool(complete and event.get("consent_to_quote") is True)
            state = "qualified" if qualified else "received"
            session = sessions.get(event.get("session_id"), {})
            leads[lead_id] = {"rfq_id": lead_id, "session_id": event.get("session_id"),
                              "action_id": session.get("action_id"), "state": state, "qualified": qualified,
                              "complete": complete, "handed_off": False, "quoted": False, "ordered": False,
                              "revenue_vnd": 0, "sales_payload": None, "history": [event["event_id"]]}
            if not session.get("action_id"):
                exceptions.append({"event_id": event["event_id"], "reason": "missing_attribution"})
            if not qualified:
                exceptions.append({"event_id": event["event_id"], "reason": "missing_fields_or_consent"})
            continue
        if kind not in TRANSITIONS:
            raise ValueError("Unknown CRM event type")
        lead = leads.get(lead_id)
        previous, state = TRANSITIONS[kind]
        if lead is None or lead["state"] not in previous:
            exceptions.append({"event_id": event["event_id"], "reason": "invalid_transition"})
            continue
        if kind == "confirmed":
            amount = event.get("revenue_vnd")
            if type(amount) is not int or amount <= 0:
                raise ValueError("Confirmed revenue requires a positive integer VND amount")
            lead["revenue_vnd"] = amount
        elif kind == "cancelled":
            lead["revenue_vnd"] = 0
        elif state in {"handed_off", "quoted", "ordered"}:
            lead[state] = True
            if state == "handed_off":
                request = submissions[lead_id]
                lead["sales_payload"] = {
                    "source_request_id": lead_id, "idempotency_key": event["event_id"],
                    "area_m2": request["area_m2"], "district": request["district"],
                    "required_by": request["required_by"], "consent_scope": "respond_to_rfq",
                    "recipient": "fixture:sales-desk",
                }
        lead["state"] = state
        lead["history"].append(event["event_id"])

    rows = list(leads.values())
    report = {
        "visitors": len({s["visitor_id"] for s in sessions.values()}),
        "sessions": len(sessions), "rfqs": len(rows), "qualified_leads": sum(r["qualified"] for r in rows),
        "sales_handoffs": sum(r["handed_off"] for r in rows), "quotations": sum(r["quoted"] for r in rows),
        "orders": sum(r["ordered"] for r in rows), "confirmed_orders": sum(r["state"] == "confirmed" for r in rows),
        "cancelled_orders": sum(r["state"] == "cancelled" for r in rows),
        "confirmed_revenue_vnd": sum(r["revenue_vnd"] for r in rows),
        "attributed_revenue_vnd": sum(r["revenue_vnd"] for r in rows if r["action_id"]),
        "marketing_cost_vnd": sum(receipt["cost_vnd"] for receipt in receipts.values()),
        "duplicates": duplicates, "delayed_event_ids": delayed, "incomplete_rfqs": sum(not r["complete"] for r in rows),
        "missing_attribution": sum(not r["action_id"] for r in rows),
        "received_events": len(events), "qualified_definition": "area_m2, district, required_by and consent_to_quote",
    }
    return report, rows, exceptions
