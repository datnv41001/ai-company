"""Exercise persisted simulated execution and new RFQ events on a genuinely approved landing document."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def exercise(api, base, owner, plan, landing_doc, terms, customer, *, approver, review_id=None):
    url = base + "/campaigns/" + plan["campaign_id"] + "/sandbox"
    receipt_log = []

    def post(kind, actor, *, status=200, request=None, **fields):
        payload = {"kind": kind, "plan_id": plan["id"], "request_id": request or uuid4().hex, **fields}
        response = api.post(url + "/commands", headers=actor["headers"], json=payload)
        assert response.status_code == status, (kind, status, response.status_code, response.text[:1200])
        if status != 200:
            return None
        event = response.json()
        receipt_log.append({"id": event["id"], "kind": kind, "entity_id": event["entity_id"], "status": event["value"].get("state")})
        return event

    def now():
        return datetime.now(timezone.utc).isoformat()

    def report():
        response = api.get(url, headers=owner["headers"])
        assert response.status_code == 200, response.text[:500]
        return response.json()

    action = "landing-" + uuid4().hex[:10]
    amount = min(20000, plan["budget_vnd"])
    schedule = dict(action_id=action, deliverable_id=landing_doc, expected_revision=terms["expected_qa_revision"],
                    expected_digest=terms["expected_content_digest"], due_at=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(), cost_vnd=amount)
    post("schedule", owner, status=409, **{**schedule, "expected_revision": schedule["expected_revision"] + 1})
    post("schedule", owner, **schedule)
    post("authorize", owner, status=409, action_id=action)
    post("authorize", approver, action_id=action)
    # A different campaign request cannot steal the authorized budget; simulate a lost acknowledgement on successful retry.
    post("execute", approver, action_id=action, outcome="temporary_failure")
    request = uuid4().hex
    done = post("execute", approver, request=request, action_id=action)
    replay = post("execute", approver, request=request, action_id=action)
    assert done == replay and done["value"]["attempts"] == 2
    assert report()["report"]["simulated_spend_vnd"] == amount

    second = {**schedule, "action_id": action + "-cancel", "cost_vnd": 0}
    post("schedule", owner, **second)
    post("cancel", owner, action_id=second["action_id"])
    post("execute", approver, status=409, action_id=second["action_id"])

    session_time = now()
    ref = "rfq-" + uuid4().hex[:8]
    sid = "session-" + uuid4().hex[:8]
    fields = {"rfq_id": ref, "product_id": plan["product_id"], "unit": plan["selling_unit"], "quantity": "4",
              "location": "Sandbox delivery zone", "required_date": (datetime.now(timezone.utc)+timedelta(days=14)).date().isoformat(),
              "contact_purpose": "quote_request", "session_id": sid, "occurred_at": now()}
    key = uuid4().hex
    first = post("rfq", owner, request=key, **fields)
    assert first == post("rfq", owner, request=key, **fields)
    assert report()["report"]["missing_attribution"] == 1
    post("session", owner, session_id=sid, actor_key="buyer-test", action_id=action, occurred_at=session_time)
    assert report()["report"]["missing_attribution"] == 0
    def sale(step, revision, **attrs):
        return post("sales", approver, rfq_id=ref, expected_revision=revision, step=step, occurred_at=now(), **attrs)
    sale("confirm", 1, amount_vnd=100000, status=409)
    sale("assign", 1, assignee_id=approver["id"])
    sale("accept", 2, reason="Synthetic request contains the quantity and delivery window for quotation.")
    sale("quote", 3)
    sale("order", 4)
    sale("confirm", 5, amount_vnd=180000)
    sale("refund", 6, amount_vnd=30000, reason="Synthetic partial refund after order confirmation.")
    sale("correct", 7, amount_vnd=160000, reason="Reconciled order amount from the synthetic Sales document.")
    assert report()["report"]["attributed_revenue_vnd"] == 130000
    post("rfq", owner, **{**fields, "rfq_id": ref + "-gap", "session_id": None, "location": None, "occurred_at": now()})
    post("sales", approver, rfq_id=ref + "-gap", expected_revision=1, step="reject", reason="Missing permitted delivery location.", occurred_at=now())
    if review_id:
        post("unit_receipt", owner, review_id=review_id, package_id="landing")
    proposal = uuid4().hex
    post("propose_optimization", owner, proposal_id=proposal)
    post("approve_optimization", approver, proposal_id=proposal)
    final = report()
    assert final["report"]["confirmed_revenue_vnd"] == final["report"]["attributed_revenue_vnd"] == 130000
    assert final["report"]["rfqs"] == 2 and final["report"]["sales_accepted"] == 1
    assert len(final["proposals"]) == 1 and final["proposals"][0]["status"] == "approved"
    assert final["cost_per_business_accepted_vnd"] is None
    assert api.get(url, headers=customer["headers"]).status_code == 404
    return {"commands": receipt_log, "state": final}
