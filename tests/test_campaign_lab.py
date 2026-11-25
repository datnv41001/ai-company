import json
from copy import deepcopy

import pytest
from identity_fixtures import invite_member

from app.campaign_lab import REVIEWS, SCENARIO, SyntheticAdapter, asset_pack, propose, replay
from app.campaign_lab_measurement import reconcile
from test_api import headers, setup_campaign, sign_up


def adapter_inputs():
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8"))
    plan = propose(scenario)
    assets = asset_pack(scenario, plan)
    return scenario, plan, assets, reviews


def test_full_rfq_journey():
    run = replay()
    assert run["synthetic"] and run["real_spend_vnd"] == run["model_invocations"] == 0
    assert run["manual_minutes"] is None and run["runtime_ms"] > 0
    assert len(run["plan"]["workflow_contracts"]) == 6
    assert all(w["status"] == "specification_only" for w in run["plan"]["workflow_contracts"])
    assert len(run["assets"]) == 6 and {a["status"] for a in run["assets"]} == {"approved"}
    assert len({a["context_digest"] for a in run["assets"]}) == 1
    assert {a["id"]: a["state"] for a in run["actions"]} == {
        "landing-slot": "executed", "ad-slot": "executed", "social-slot": "cancelled"}
    ad = run["actions"][1]
    assert ad["attempts"] == 2 and ad["history"] == ["scheduled", "authorized", "failed", "executed"]
    report = run["report"]
    assert report["visitors"] == 3
    assert (report["sessions"], report["rfqs"], report["qualified_leads"], report["sales_handoffs"]) == (4, 5, 3, 3)
    assert (report["quotations"], report["orders"], report["cancelled_orders"]) == (3, 3, 1)
    assert report["missing_attribution"] == report["duplicates"] == 2
    assert report["incomplete_rfqs"] == 1 and "q1" in report["delayed_event_ids"]
    assert (report["confirmed_revenue_vnd"], report["attributed_revenue_vnd"], report["marketing_cost_vnd"]) == (
        10_000_000, 8_000_000, 1_200_000)
    assert next(r for r in run["leads"] if r["rfq_id"] == "rfq-5")["state"] == "rejected"
    assert all(bool(r["sales_payload"]) == r["handed_off"] for r in run["leads"])


def test_slot_requires_qa_scoped_approval_schedule_and_is_idempotent():
    scenario, plan, assets, reviews = adapter_inputs()
    adapter = SyntheticAdapter(plan, assets, reviews)
    slot = scenario["actions"][1]
    adapter.schedule(slot)
    key = slot["id"]
    with pytest.raises(ValueError, match="authorized and due"):
        adapter.execute(key, day=10)
    adapter.authorize(key)
    with pytest.raises(ValueError, match="authorized and due"):
        adapter.execute(key, day=1)
    assert adapter.schedule(slot)["state"] == "authorized"
    with pytest.raises(ValueError, match="different terms"):
        adapter.schedule({**slot, "cost_vnd": 0})
    adapter.assets["ad"]["body"] += "changed"
    with pytest.raises(ValueError, match="stale"):
        adapter.execute(key, day=4)
    adapter.assets["ad"]["body"] = next(a for a in asset_pack(scenario, plan) if a["id"] == "ad")["body"]
    receipt = adapter.execute(key, day=4)
    assert adapter.execute(key, day=5) == receipt
    assert adapter.spent == receipt["cost_vnd"] == 1_200_000


def test_cancelled_retry_exhausted_and_budget_never_execute():
    scenario, plan, assets, reviews = adapter_inputs()
    adapter = SyntheticAdapter(plan, assets, reviews)
    slot = scenario["actions"][1]
    key = slot["id"]
    adapter.schedule(slot)
    adapter.authorize(key)
    adapter.spent = plan["budget_vnd"]
    with pytest.raises(ValueError, match="ceiling"):
        adapter.execute(key, day=5)
    adapter.spent = 0
    for _ in range(2):
        assert adapter.execute(key, day=5, fail=True) is None
    with pytest.raises(ValueError, match="Retry limit"):
        adapter.execute(key, day=5)
    adapter.cancel(key)
    with pytest.raises(ValueError, match="authorized and due"):
        adapter.execute(key, day=5)
    assert adapter.spent == 0


def test_event_conflicts_and_invalid_transitions_are_visible():
    scenario, _, _, _ = adapter_inputs()
    event = next(e for e in scenario["events"] if e["type"] == "rfq")
    with pytest.raises(ValueError, match="Conflicting payload"):
        reconcile([event, {**event, "area_m2": 1}], {})
    with pytest.raises(ValueError, match="Conflicting RFQ"):
        reconcile([event, {**event, "event_id": "other", "area_m2": 1}], {})
    confirmed = {"event_id": "forged", "type": "confirmed", "at": 15,
                 "rfq_id": event["rfq_id"], "revenue_vnd": 42}
    report, _, exceptions = reconcile([event, confirmed], {})
    assert report["rfqs"] == 1 and report["orders"] == report["confirmed_revenue_vnd"] == 0
    assert any(reason["reason"] == "invalid_transition" for reason in exceptions)
    rows = deepcopy(scenario["events"])
    next(e for e in rows if e["event_id"] == "c1")["revenue_vnd"] = -1
    with pytest.raises(ValueError, match="positive integer"):
        reconcile(rows, {})


def test_scoped_replay_returns_fixture_only(client):
    alice, bob = sign_up(client, "lab-owner"), sign_up(client, "lab-other")
    agency_client, _, campaign = setup_campaign(client, alice)
    _, _, other = setup_campaign(client, bob)
    base = f"/api/tenants/{alice['tenant_id']}/campaigns/"
    url = base + campaign["id"] + "/execution-lab/replay"
    assert client.post(url).status_code == 401
    assert client.post(url, headers=headers(bob)).status_code == 404
    assert client.post(base + other["id"] + "/execution-lab/replay", headers=headers(alice)).status_code == 404
    invite_member(client, f"/api/tenants/{alice['tenant_id']}", headers(alice), headers(bob),
                  email="lab-other@example.com", role="client_viewer", client_id=agency_client["id"])
    assert client.post(url, headers=headers(bob)).status_code == 404
    resp = client.post(url, headers=headers(alice))
    assert resp.status_code == 200
    assert resp.json()["campaign_id"] == campaign["id"] and resp.json()["synthetic"]
    assert campaign["brief"] not in resp.text
    assert client.get(base + campaign["id"] + "/tasks", headers=headers(alice)).json() == []
