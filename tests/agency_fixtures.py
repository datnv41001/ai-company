"""Acceptance contract on SQLite and on an explicitly selected local PostgreSQL test database."""
import os
import socket
import threading
import time
from uuid import uuid4

import pytest
import httpx
import uvicorn

from identity_fixtures import start_registration, verify_registration
from identity_fixtures import invite_member
from app.database import engine
from app.main import app


@pytest.fixture(params=["sqlite", "postgres"])
def api(request):
    if request.param == "sqlite":
        yield request.getfixturevalue("client")
        return
    if os.environ.get("AMC_TEST_PG") != "1":
        pytest.skip("Set AMC_TEST_PG=1 to run PostgreSQL acceptance tests")
    assert engine.dialect.name == "postgresql"
    assert engine.url.host in ("localhost", "127.0.0.1", "::1")
    assert engine.url.database.startswith("amc_test")
    # Normal get_db dependency and app lifespan; nothing replaces the PostgreSQL session.
    assert not app.dependency_overrides
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{sock.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False, proxy_headers=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]})
        thread.start()
        try:
            for _ in range(200):
                if server.started or not thread.is_alive():
                    break
                time.sleep(0.025)
            assert server.started
            with httpx.Client(base_url=url, timeout=10, trust_env=False) as real:
                yield real
        finally:
            server.should_exit = True
            thread.join(10)
            assert not thread.is_alive()


def account(api, label):
    email = f"{label}-{uuid4().hex}@example.com"
    body = dict(email=email, password=uuid4().hex, organization_name=label, mode="agency")
    info = start_registration(api, **body)
    verify_registration(api,email,info)
    login = api.post("/api/auth/login", json={"email": email, "password": body["password"]})
    assert login.status_code == 200
    return dict(id=info["user_id"], tenant=info["tenant_id"], email=email,
                headers={"Authorization": "Bearer " + login.json()["access_token"]})


def create(api, path, actor, payload):
    response = api.post(path, headers=actor["headers"], json=payload)
    assert response.status_code == 201, (path, response.status_code, response.text)
    return response.json()


def make_client_data(api, base, owner, label):
    client = create(api, base + "/clients", owner, {"name": "Client " + label})
    brands = []
    campaigns = []
    tasks = set()
    deliverables = set()
    actions = set()
    for n in range(2):
        brand = create(api, base + "/brands", owner, {"client_id": client["id"], "name": f"Brand {label} {n}"})
        campaign = create(api, base + "/campaigns", owner, {"brand_id": brand["id"], "name": f"Campaign {label} {n}",
                          "brief": "Synthetic marketing brief", "objective": "Verify reader scope"})
        plan = api.post(base + f"/campaigns/{campaign['id']}/plan", headers=owner["headers"])
        assert plan.status_code == 200
        task_ids = {t["id"] for t in plan.json()["tasks"]}
        assert len(task_ids) == 7
        tasks.update(task_ids)
        artifact = create(api, base + "/deliverables", owner, {"campaign_id": campaign["id"], "title": "Draft " + label, "content": {"brief": label}})
        action = create(api, base + "/actions", owner, {"campaign_id": campaign["id"], "action_kind": "publish_social", "payload": {"draft": label}})
        brands.append(brand["id"])
        campaigns.append(campaign["id"])
        deliverables.add(artifact["id"])
        actions.add(action["id"])
    return {"clients": {client["id"]}, "brands": set(brands), "campaigns": set(campaigns),
            "work_tasks": tasks, "deliverables": deliverables, "actions": actions}


@pytest.fixture
def agency(api):
    owner, alice, bob = [account(api, name) for name in ("Agency", "ReaderA", "ReaderB")]
    base = "/api/tenants/" + owner["tenant"]
    a = make_client_data(api, base, owner, "A")
    b = make_client_data(api, base, owner, "B")
    for actor, data in ((alice, a), (bob, b)):
        invite_member(api, base, owner["headers"], actor["headers"], email=actor["email"], role="client_viewer", client_id=next(iter(data["clients"])))
    return owner, base, ((alice, a), (bob, b))
