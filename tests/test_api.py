from uuid import uuid4


def sign_up(client, label, mode="agency"):
    response = client.post("/api/auth/register", json={
        "email": f"{label}@example.com", "password": "AtLeast12Chars!", "organization_name": label, "mode": mode
    })
    assert response.status_code == 201, response.text
    return response.json()


def headers(identity):
    return {"Authorization": f"Bearer {identity['access_token']}"}


def setup_campaign(client, identity):
    tenant_id = identity["tenant_id"]
    client_resp = client.post(f"/api/tenants/{tenant_id}/clients", json={"name": "Client A", "sector": "Retail"}, headers=headers(identity))
    assert client_resp.status_code == 201, client_resp.text
    brand_resp = client.post(f"/api/tenants/{tenant_id}/brands", json={"client_id": client_resp.json()["id"], "name": "Brand A", "brand_guidelines": "Only verified claims"}, headers=headers(identity))
    assert brand_resp.status_code == 201, brand_resp.text
    campaign_resp = client.post(f"/api/tenants/{tenant_id}/campaigns", json={"brand_id": brand_resp.json()["id"], "name": "Launch 2026", "brief": "Launch a real product in 30 days using approved claims.", "objective": "Build a compliant campaign plan"}, headers=headers(identity))
    assert campaign_resp.status_code == 201, campaign_resp.text
    return client_resp.json(), brand_resp.json(), campaign_resp.json()


def test_health_is_explicitly_not_production_ready(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["production_ready"] is False


def test_registration_login_and_tenant_scope(client):
    alice = sign_up(client, "alice")
    bob = sign_up(client, "bob")
    _, alice_brand, alice_campaign = setup_campaign(client, alice)
    _, bob_brand, bob_campaign = setup_campaign(client, bob)
    tid = alice["tenant_id"]
    assert client.get(f"/api/tenants/{tid}/brands", headers=headers(bob)).status_code == 404
    assert client.get(f"/api/tenants/{tid}/campaigns/{alice_campaign['id']}", headers=headers(bob)).status_code == 404
    assert client.post(f"/api/tenants/{tid}/campaigns", headers=headers(alice), json={"brand_id": bob_brand["id"], "name": "Bad campaign", "brief": "This should not be accepted.", "objective": "Enforce tenant isolation"}).status_code == 404
    assert len(client.get(f"/api/tenants/{tid}/brands", headers=headers(alice)).json()) == 1
    assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": "AtLeast12Chars!"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": "WRONG"}).status_code == 401


def test_plan_is_deterministic_idempotent_and_not_fake_ai(client):
    owner = sign_up(client, "owner")
    _, _, campaign = setup_campaign(client, owner)
    url = f"/api/tenants/{owner['tenant_id']}/campaigns/{campaign['id']}/plan"
    first = client.post(url, headers=headers(owner))
    assert first.status_code == 200
    assert first.json()["llm_called"] is False
    assert first.json()["created_count"] == 7
    assert len(first.json()["tasks"]) == 7
    second = client.post(url, headers=headers(owner))
    assert second.json()["created_count"] == 0
    assert len(second.json()["tasks"]) == 7


def test_planned_roles_exist_in_role_catalog(client):
    owner = sign_up(client, "rolecheck")
    _, _, campaign = setup_campaign(client, owner)
    plan = client.post(
        f"/api/tenants/{owner['tenant_id']}/campaigns/{campaign['id']}/plan",
        headers=headers(owner),
    )
    catalog = client.get("/api/catalog/roles", headers=headers(owner))
    assert plan.status_code == catalog.status_code == 200
    registered = {role["id"] for role in catalog.json()}
    assert {task["role_slug"] for task in plan.json()["tasks"]} <= registered


def test_approval_requires_separate_human_and_is_tenant_scoped(client):
    owner = sign_up(client, "boss")
    reviewer = sign_up(client, "reviewer")
    other = sign_up(client, "other")
    _, _, campaign = setup_campaign(client, owner)
    tid = owner["tenant_id"]
    # Development membership bootstrap only; real product requires consent-based invitations.
    grant = client.post(f"/api/tenants/{tid}/members", headers=headers(owner), json={"email": "reviewer@example.com", "role": "admin"})
    assert grant.status_code == 201
    proposal = client.post(f"/api/tenants/{tid}/actions", headers=headers(owner), json={"campaign_id": campaign["id"], "action_kind": "adjust_ads_budget", "payload": {"amount": 250, "currency": "USD"}})
    assert proposal.status_code == 201
    action_id = proposal.json()["id"]
    url = f"/api/tenants/{tid}/actions/{action_id}/review"
    assert client.post(url, headers=headers(owner), json={"decision": "approved"}).status_code == 403
    assert client.post(url, headers=headers(other), json={"decision": "approved"}).status_code == 404
    assert client.post(url, headers=headers(reviewer), json={"decision": "approved"}).status_code == 200
    assert client.post(url, headers=headers(reviewer), json={"decision": "approved"}).status_code == 409
    execute = client.post(f"/api/tenants/{tid}/actions/{action_id}/execute", headers=headers(reviewer))
    assert execute.status_code == 501  # No unauthorized external write exists in bootstrap.
    events = client.get(f"/api/tenants/{tid}/audit", headers=headers(owner)).json()
    assert any(e["event"] == "external_action.reviewed" for e in events)


def test_deliverable_review_and_cross_tenant_boundary(client):
    owner = sign_up(client, "jane")
    reviewer = sign_up(client, "clara")
    outsider = sign_up(client, "stranger")
    _, _, campaign = setup_campaign(client, owner)
    tid = owner["tenant_id"]
    client.post(f"/api/tenants/{tid}/members", headers=headers(owner), json={"email": "clara@example.com", "role": "admin"})
    artifact = client.post(f"/api/tenants/{tid}/deliverables", headers=headers(owner), json={"campaign_id": campaign["id"], "title": "Campaign brief", "content": {"summary": "Draft", "source": "Owner brief"}})
    assert artifact.status_code == 201
    aid = artifact.json()["id"]
    assert client.post(f"/api/tenants/{tid}/deliverables/{aid}/submit", headers=headers(owner)).status_code == 200
    assert client.post(f"/api/tenants/{tid}/deliverables/{aid}/review", headers=headers(owner), json={"expected_qa_revision": artifact.json()["qa_evidence"]["qa_revision"], "expected_content_digest": artifact.json()["qa_evidence"]["content_digest"], "decision": "approved"}).status_code == 403
    assert client.post(f"/api/tenants/{tid}/deliverables/{aid}/review", headers=headers(outsider), json={"expected_qa_revision": artifact.json()["qa_evidence"]["qa_revision"], "expected_content_digest": artifact.json()["qa_evidence"]["content_digest"], "decision": "approved"}).status_code == 404
    r = client.post(f"/api/tenants/{tid}/deliverables/{aid}/review", headers=headers(reviewer), json={"expected_qa_revision": artifact.json()["qa_evidence"]["qa_revision"], "expected_content_digest": artifact.json()["qa_evidence"]["content_digest"], "decision": "approved", "note": "Reviewed"})
    assert r.status_code == 200 and r.json()["status"] == "approved"


def test_inhouse_mode_and_missing_llm_configuration(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    who = sign_up(client, "inhouse", "inhouse")
    tid = who["tenant_id"]
    clients = client.get(f"/api/tenants/{tid}/clients", headers=headers(who)).json()
    assert len(clients) == 1 and clients[0]["name"] == "Internal Marketing"
    brand = client.post(f"/api/tenants/{tid}/brands", headers=headers(who), json={"name": "Brand In House", "client_id": clients[0]["id"]}).json()
    campaign = client.post(f"/api/tenants/{tid}/campaigns", headers=headers(who), json={"brand_id": brand["id"], "name": "Brand Launch", "brief": "Create an accurate launch plan with verified claims.", "objective": "Plan a marketing campaign"}).json()
    r = client.post(f"/api/tenants/{tid}/campaigns/{campaign['id']}/strategy", headers=headers(who))
    assert r.status_code == 410
    assert client.get(f"/api/tenants/{tid}/deliverables", headers=headers(who)).json() == []


def test_anonymous_is_rejected_and_invalid_payload(client):
    assert client.get(f"/api/tenants/{uuid4()}/clients").status_code == 401
    assert client.post("/api/auth/register", json={"email": "nope", "password": "short", "organization_name": "X"}).status_code == 422


def test_viewer_cannot_write_but_can_read(client):
    owner = sign_up(client, "editorowner")
    viewer = sign_up(client, "readonly")
    tid = owner["tenant_id"]
    client.post(f"/api/tenants/{tid}/members", headers=headers(owner), json={"email": "readonly@example.com", "role": "viewer"})
    assert client.get(f"/api/tenants/{tid}/clients", headers=headers(viewer)).status_code == 200
    assert client.post(f"/api/tenants/{tid}/clients", headers=headers(viewer), json={"name": "Should Fail"}).status_code == 404
    assert client.get(f"/api/tenants/{tid}/audit", headers=headers(viewer)).status_code == 404


def test_auth_validation_keeps_submitted_credentials_out_of_response(client):
    marker = "demo-value"
    cases = [
        ("register", {"email": "review@example.com", "organization_name": "Review", "password": marker}),
        ("login", {"email": "review@example.com", "password": [marker]}),
        ("register", [{"password": marker}]),
    ]
    for endpoint, payload in cases:
        result = client.post(f"/api/auth/{endpoint}", json=payload)
        assert result.status_code == 422
        assert marker not in result.text
        assert isinstance(result.json()["detail"], list)


def test_retired_strategy_never_calls_provider_with_key_present(client, monkeypatch):
    import httpx
    owner = sign_up(client, "strategist")
    _, _, campaign = setup_campaign(client, owner)
    monkeypatch.setenv("OPENAI_API_KEY","synthetic-regression-marker")
    def forbid_network(*args, **kwargs):
        raise AssertionError("Legacy endpoint attempted an outbound HTTP call")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid_network)
    base = f"/api/tenants/{owner['tenant_id']}"
    for _ in range(2):
        assert client.post(base + f"/campaigns/{campaign['id']}/strategy",headers=headers(owner)).status_code == 410
    assert client.get(base+"/deliverables",headers=headers(owner)).json() == []


def test_role_and_workflow_spec_catalogs_are_not_claimed_implemented(client):
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    roles = json.loads((root / "catalog/agent_roles.json").read_text(encoding="utf-8"))
    workflows = json.loads((root / "catalog/workflows.json").read_text(encoding="utf-8"))
    assert len(roles) == 37
    assert len(workflows) == 24
    assert all(i["status"] == "specification_only" for i in roles + workflows)
    owner = sign_up(client, "catalog")
    r = client.get("/api/catalog/roles", headers=headers(owner))
    assert r.status_code == 200 and len(r.json()) == 37
    page = client.get("/")
    assert page.status_code == 200 and "AI Marketing Company" in page.text
