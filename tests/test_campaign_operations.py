"""Fresh scoped campaigns and journal-backed Sales/measurement, on both storage engines."""
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from uuid import uuid4

import httpx
import pytest

from app import c3_assets
from campaign_planner_fixtures import CASES, prepare_inputs
from knowledge_fixtures import accepted
from test_claim_desk import reader


@contextmanager
def fresh_process():
    """Start a fresh app interpreter against the restricted loopback test database."""
    from app.database import engine
    assert engine.url.host in ("127.0.0.1", "localhost", "::1") and engine.url.database.startswith("amc_test")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        env=os.environ.copy(),
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10, trust_env=False) as http:
            for _ in range(180):
                assert process.poll() is None, "Test API process exited during startup"
                try:
                    if http.get("/api/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.1)
            else:
                pytest.fail("Fresh test API did not start")
            yield http
    finally:
        process.terminate()
        process.wait(15)


def test_scoped_rfq_pipeline_idempotency_and_commission_identity(api, agency):
    owner, base, ((customer, a), (second_customer, b)) = agency
    campaign, other = next(iter(a["campaigns"])), next(iter(b["campaigns"]))
    campaign_row = next(c for c in accepted(api.get(base + "/campaigns", headers=owner["headers"])) if c["id"] == campaign)
    brand = campaign_row["brand_id"]
    case = CASES[1]
    snaps, _ = prepare_inputs(api, owner, customer, next(iter(a["clients"])), brand, campaign, case, workflows=(c3_assets.LANDING,))
    root = base + "/campaigns/" + campaign
    path = root + "/sandbox"
    planner = root + "/engine/plans"
    def plan(rev, outcome):
        draft = accepted(api.post(planner, headers=owner["headers"], json={
            "key": uuid4().hex, "expected_revision": rev, "target_outcome": outcome, "budget_vnd": 30000,
            "duration_days": 30, "manifest_ids": [s["id"] for s in snaps]}))
        accepted(api.post(planner + "/" + draft["id"] + "/approve", headers=owner["headers"],
                          json={"key": uuid4().hex, "expected_digest": draft["digest"]}))
        return draft

    first = plan(0, case["kpi"])
    def send(kind, *, code=200, actor=owner, key=None, target=None, **fields):
        data = {"kind":kind, "request_id":key or uuid4().hex, "plan_id":first["id"], **fields}
        answer = api.post((target or path) + "/commands", headers=actor["headers"], json=data)
        assert answer.status_code == code, (kind, answer.status_code, answer.text[:650])
        return answer.json()
    def view():
        return accepted(api.get(path, headers=owner["headers"]))

    before = view()
    ids = {u["id"] for u in before["work_units"]}
    assert len(ids) == len(first["work_packages"]) and before["business_accepted_units"] == 0
    assert api.get(path, headers=customer["headers"]).status_code == api.get(path, headers=second_customer["headers"]).status_code == 404
    assert api.get("/api/tenants/" + second_customer["tenant"] + "/campaigns/" + campaign + "/sandbox",
                   headers=second_customer["headers"]).status_code == 404
    other_scope = base + "/campaigns/" + other + "/sandbox"
    assert accepted(api.get(other_scope, headers=owner["headers"]))["work_units"] == []
    now = datetime.now(timezone.utc)
    lead = {"rfq_id":"machine-quote", "product_id":first["product_id"], "unit":"machine", "quantity":"2", "location":None,
            "required_date":(now.date()+timedelta(days=3)).isoformat(), "contact_purpose":"quote_request", "occurred_at":now.isoformat()}
    lead["details"] = {"schema_id": "service_v1", "service_scope": "Inspection", "equipment_type": "Industrial pump"}
    send("rfq", **{**lead, "details":{"schema_id":"materials_v1","application":"Insulation"}}, code=409)
    send("rfq", **{**lead, "unit":"m²"}, code=409)
    send("rfq", **{**lead, "quantity":"0.5"}, code=409)
    send("rfq", **lead, target=other_scope, code=409)
    send("rfq", **lead, actor=second_customer, code=404)
    recorded = send("rfq", **lead, key="received-after-retry")
    assert recorded == send("rfq", **lead, key="received-after-retry")
    send("rfq", **lead, code=409)
    send("rfq", **{**lead,"quantity":"7"}, key="received-after-retry", code=409)
    send("sales", rfq_id=lead["rfq_id"], expected_revision=1, step="quote", occurred_at=now.isoformat(), code=409)
    send("complete_rfq", rfq_id=lead["rfq_id"], expected_revision=1, unit="box", quantity="3", location="Factory", required_date=lead["required_date"],
         contact_purpose="quote_request", code=422)
    send("complete_rfq", rfq_id=lead["rfq_id"], expected_revision=1, quantity="3", location="Factory", required_date=lead["required_date"],
         contact_purpose="quote_request")
    staff = reader(api, owner, "admin")
    def sales(step, revision, **fields):
        return send("sales", actor=staff, rfq_id=lead["rfq_id"], expected_revision=revision, step=step,
                    occurred_at=datetime.now(timezone.utc).isoformat(), **fields)
    sales("assign",2,assignee_id=staff["id"])
    sales("accept",3,reason="Sales can quote with this machine count")
    sales("quote",4)
    sales("order",5)
    sales("confirm",6,amount_vnd=500)
    sales("refund",7,amount_vnd=700,reason="Invalid refund",code=409)
    sales("refund",7,amount_vnd=100,reason="Partial refund of approved order")
    stats = view()["report"]
    assert (stats["rfqs"], stats["confirmed_revenue_vnd"], stats["unattributed_revenue_vnd"]) == (1,400,400)
    assert stats["attributed_revenue_vnd"] == stats["simulated_spend_vnd"] == 0
    send("propose_optimization", proposal_id="check-sources")
    send("approve_optimization", proposal_id="check-sources", code=409)
    send("approve_optimization", actor=staff, proposal_id="check-sources")
    send("labor", package_id="seo", phase="editing", seconds=60, allocated_cost_vnd=10, observation="Synthetic time allocation")
    send("close_unit_cost", package_id="seo", nonlabor_vnd=20, basis="Synthetic compute bill")
    assert view()["cost_per_business_accepted_vnd"] is None
    follow = plan(1, case["kpi"])
    assert ids == {u["id"] for u in view()["work_units"]}
    assert all(u["plan_id"] == follow["id"] for u in view()["work_units"])
    plan(2, snaps[0]["projection"]["objective"])
    assert len(view()["work_units"]) == 2 * len(ids)
    # An old plan cannot schedule new production, but cancelling an existing confirmed order still reconciles.
    send("rfq", **{**lead,"rfq_id":"obsolete"}, code=409)
    sales("cancel",8,reason="Buyer cancelled the confirmed order")
    stable = view()
    assert stable["report"]["confirmed_revenue_vnd"] == 0 and stable["report"]["cancelled_orders"] == 1
    assert len({r["id"] for r in stable["receipts"]}) == len(stable["receipts"])
    if getattr(api, "base_url", None) and str(api.base_url).startswith("http://127.0.0.1:"):
        from fastapi.security import HTTPAuthorizationCredentials
        from sqlalchemy import text
        from sqlalchemy.orm import Session
        from app.database import engine
        from app.security import current_user, require_tenant
        # Read the receipt directly with the normal restricted PostgreSQL login and signed actor.
        # This bypasses the route filter and exercises storage-layer isolation separately.
        for actor, visible in ((owner,True),(customer,False),(second_customer,False)):
            with Session(engine) as db:
                token = actor["headers"]["Authorization"].split(" ",1)[1]
                current = current_user(HTTPAuthorizationCredentials(scheme="Bearer",credentials=token), db)
                require_tenant(db, current, owner["tenant"])
                assert bool(db.scalar(text("SELECT count(*) FROM knowledge_commands WHERE id=:id"), {"id":recorded["id"]})) is visible
                assert not db.scalar(text("SELECT has_table_privilege(current_user,'knowledge_commands','UPDATE')"))
        # Commit in a separate OS process, drop its acknowledgement, terminate it, and retry in a fresh process.
        replay_body = {"kind":"labor", "package_id":"ad", "plan_id":follow["id"], "request_id":"hard-restart",
                       "phase":"editing", "seconds":17, "allocated_cost_vnd":5, "observation":"Restart receipt"}
        with fresh_process() as first_process:
            def submit(_):
                return accepted(first_process.post(path + "/commands", headers=owner["headers"], json=replay_body))
            with ThreadPoolExecutor(max_workers=2) as executor:
                original, duplicate = executor.map(submit, range(2))
            assert duplicate == original
        with fresh_process() as reopened:
            assert accepted(reopened.post(path + "/commands", headers=owner["headers"], json=replay_body)) == original
            restored = accepted(reopened.get(path, headers=owner["headers"]))
            assert len(stable["receipts"]) + 1 == len(restored["receipts"])
            assert restored["report"] == stable["report"]
            replay = reopened.post(path + "/commands", headers=owner["headers"], json={**lead,"kind":"rfq","request_id":"received-after-retry","plan_id":first["id"]})
            assert accepted(replay) == recorded


def test_paid_reservation_stale_approval_and_retry_limits(monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app import campaign_operations as ops
    from app.campaign_operations_contracts import DecideAction, Execute
    now = datetime.now(timezone.utc)
    store = SimpleNamespace(db=None, approver=True, scope={"tenant_id":"t"}, now=lambda: now)
    user, plan = SimpleNamespace(id="admin2"), {"id":"plan", "budget_vnd":100}
    action = {"id":"slot", "plan_id":"plan", "state":"scheduled", "scheduled_by":"admin1", "cost_vnd":70,
              "deliverable_id":"doc","asset_revision":2,"asset_digest":"a"*64,"due_at":(now-timedelta(minutes=1)).isoformat(),"attempts":0}
    state = {"actions":{"slot":action, "previous":{"id":"previous","plan_id":"old","state":"executed","cost_vnd":40}}}
    monkeypatch.setattr(ops, "current_asset", lambda *a, **kw: None)
    args = {"action_id":"slot","plan_id":"plan","request_id":"x"}
    def command(input_):
        return ops.action_command(input_,state,plan,store,user,"campaign")[2]
    with pytest.raises(HTTPException, match="budget"):
        command(DecideAction(kind="authorize",**args))
    plan["budget_vnd"] = 120
    state["actions"]["slot"] = command(DecideAction(kind="authorize",**args))
    monkeypatch.setattr(ops, "active_approver", lambda *a, **kw: False)
    with pytest.raises(HTTPException, match="withdrawn"):
        command(Execute(kind="execute",**args))
    monkeypatch.setattr(ops, "active_approver", lambda *a, **kw: True)
    for _ in range(3):
        state["actions"]["slot"] = command(Execute(kind="execute",outcome="temporary_failure",**args))
    with pytest.raises(HTTPException, match="retryable"):
        command(Execute(kind="execute",**args))
    assert command(DecideAction(kind="cancel",**args))["state"] == "cancelled"


def test_all_strategy_only_commissions_precede_generation_and_rollback_on_failure(api, agency, monkeypatch):
    from app import campaign_operations as ops
    from app.knowledge_store import conflict

    owner, base, ((customer, a), _) = agency
    campaign = next(iter(a["campaigns"]))
    brand = next(c["brand_id"] for c in accepted(api.get(base + "/campaigns", headers=owner["headers"])) if c["id"] == campaign)
    [snap], _ = prepare_inputs(api, owner, customer, next(iter(a["clients"])), brand, campaign, CASES[0], workflows=(c3_assets.RESEARCH,))
    root = base + "/campaigns/" + campaign
    path = root + "/engine/plans"
    sandbox = root + "/sandbox"
    original = ops.compose_assets
    observed = []
    original_append = ops.append
    def observe(*args, **kwargs):
        row = original_append(*args, **kwargs)
        observed.append((row["kind"], row["value"]["status"], row["sequence"]))
        return row
    monkeypatch.setattr(ops, "append", observe)
    def fail_after_commission(proposed):
        assert observed == [("commission", "requested", i + 1) for i in range(len(proposed["work_packages"]))]
        conflict("Synthetic composition failure")
    monkeypatch.setattr(ops, "compose_assets", fail_after_commission)
    draft = accepted(api.post(path, headers=owner["headers"], json={"key":uuid4().hex,"expected_revision":0,
        "manifest_ids":[snap["id"]],"budget_vnd":10000,"duration_days":21}))
    assert not draft.get("composed_assets") and not observed
    route = path + "/" + draft["id"] + "/approve"
    request = {"key":uuid4().hex,"expected_digest":draft["digest"]}
    failure = api.post(route, headers=owner["headers"], json=request)
    assert failure.status_code == 409 and "Synthetic composition failure" in failure.text
    assert not accepted(api.get(sandbox, headers=owner["headers"]))["receipts"]
    observed.clear()
    monkeypatch.setattr(ops, "compose_assets", original)
    approved = accepted(api.post(route, headers=owner["headers"], json=request))
    assert approved["digest"] == draft["digest"]
    assert accepted(api.post(route, headers=owner["headers"], json=request)) == approved
    read = accepted(api.get(sandbox, headers=owner["headers"]))
    assets = accepted(api.get(path + "/" + draft["id"] + "/production", headers=owner["headers"]))["assets"]
    total = len(draft["work_packages"])
    assert len(read["work_units"]) == total
    assert observed == ([("commission","requested",i + 1) for i in range(total)] +
                        [("generated","generated",total + i + 1) for i in range(4)])
    assert len(read["receipts"]) == len(observed)
    for asset in assets:
        unit = next(u for u in read["work_units"] if u["package_id"] == asset["kind"])
        assert unit["artifact_digest"] == asset["digest"] and unit["status"] == "generated"
        assert unit["manifest"]["id"] == asset["manifest"]["id"] == snap["id"]
