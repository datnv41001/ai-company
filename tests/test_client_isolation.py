"""Acceptance contract on SQLite and on an explicitly selected local PostgreSQL test database."""
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
import httpx
import uvicorn
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

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
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
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
    result = api.post("/api/auth/register", json=body)
    assert result.status_code == 201, result.status_code
    info = result.json()
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
        create(api, base + "/members", owner, {"email": actor["email"], "role": "client_viewer", "client_id": next(iter(data["clients"]))})
    return owner, base, ((alice, a), (bob, b))


def test_client_reads_are_exact_and_symmetric(api, agency):
    owner, base, readers = agency
    for index, (reader, expected) in enumerate(readers):
        other = readers[1 - index][1]
        headers = reader["headers"]
        for resource in ("clients", "brands", "campaigns", "deliverables", "actions"):
            result = api.get(f"{base}/{resource}", headers=headers)
            assert result.status_code == 200
            assert {r["id"] for r in result.json()} == expected[resource]
        task_ids = set()
        for cid in expected["campaigns"]:
            assert api.get(f"{base}/campaigns/{cid}", headers=headers).json()["id"] == cid
            tasks = api.get(f"{base}/campaigns/{cid}/tasks", headers=headers)
            assert tasks.status_code == 200
            task_ids.update(t["id"] for t in tasks.json())
        assert task_ids == expected["work_tasks"]
        for cid in other["campaigns"]:
            for suffix in ("", "/tasks"):
                assert api.get(f"{base}/campaigns/{cid}{suffix}", headers=headers).status_code == 404
        assert api.get(base + "/audit", headers=headers).status_code == 404
        assert api.post(base + "/clients", headers=headers, json={"name": "New client"}).status_code == 404
        assert api.get(f"/api/tenants/{readers[1-index][0]['tenant']}/brands", headers=headers).status_code == 404
    visible = api.get(base + "/campaigns", headers=owner["headers"])
    assert {c["id"] for c in visible.json()} == readers[0][1]["campaigns"] | readers[1][1]["campaigns"]


def test_scope_changes_and_revocation_apply_to_existing_session(api, agency):
    owner, base, ((alice, a), (bob, b)) = agency
    tenant = owner["tenant"]
    admin = owner["headers"]
    scope_path = base + f"/members/{alice['id']}/client-scope"
    b_client = next(iter(b["clients"]))
    assert api.put(scope_path, headers=alice["headers"], json={"client_id": b_client}).status_code == 404
    assert api.put(scope_path, headers=admin, json={"client_id": b_client}).status_code == 200
    assert {x["id"] for x in api.get(base + "/clients", headers=alice["headers"]).json()} == b["clients"]
    assert api.delete(scope_path, headers=admin).status_code == 204
    assert api.get(base + "/clients", headers=alice["headers"]).status_code == 404
    assert tenant not in {m["tenant_id"] for m in api.get("/api/me", headers=alice["headers"]).json()["tenants"]}
    assert api.get(base + "/clients", headers=bob["headers"]).status_code == 200
    events = api.get(base + "/audit", headers=admin).json()
    assert {"member.client_scope_changed", "member.client_scope_revoked"} <= {e["event"] for e in events}


def test_explicit_mapping_of_existing_viewer(api, agency):
    owner, base, ((_, a), _) = agency
    reader = account(api, "InternalReader")
    create(api, base + "/members", owner, {"email": reader["email"], "role": "viewer"})
    assert len(api.get(base + "/clients", headers=reader["headers"]).json()) == 2
    client_id = next(iter(a["clients"]))
    other_client = create(api, f"/api/tenants/{reader['tenant']}/clients", reader, {"name": "Separate client"})
    path = base + f"/members/{reader['id']}/client-scope"
    assert api.put(path, headers=owner["headers"], json={"client_id": other_client["id"]}).status_code == 404
    assert api.put(path, headers=owner["headers"], json={"client_id": client_id}).status_code == 200
    assert [x["id"] for x in api.get(base + "/clients", headers=reader["headers"]).json()] == [client_id]
    for payload in ({"role": "client_viewer"}, {"role": "viewer", "client_id": client_id}):
        assert api.post(base + "/members", headers=owner["headers"], json={"email": reader["email"], **payload}).status_code == 422


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_postgres_rls_without_api_filters(api, agency):
    owner, _, readers = agency
    resources = {"clients":"clients", "brands":"brands", "campaigns":"campaigns", "work_tasks":"work_tasks",
                 "deliverables":"deliverables", "actions":"action_requests"}
    # Alternate actors on the same physical connection and clear transactions by commit/rollback.
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT current_user")) == "amc_runtime"
        for index, (reader, expected) in enumerate(readers):
            assert conn.scalar(text("SELECT count(*) FROM campaigns")) == 0
            conn.execute(text("SELECT set_config('amc.user_id',:u,true),set_config('amc.tenant_id',:t,true)"),
                         {"u": reader["id"], "t": owner["tenant"]})
            for key, table in resources.items():
                assert set(conn.scalars(text(f"SELECT id FROM {table}"))) == expected[key]
            assert conn.scalar(text("SELECT count(*) FROM audit_events")) == 0
            assert conn.execute(text("UPDATE campaigns SET status=status")).rowcount == 0
            with pytest.raises(ProgrammingError) as denied, conn.begin_nested():
                conn.execute(text("INSERT INTO clients (id, tenant_id, name, sector) VALUES (:id,:t,'Denied','Test')"),
                             {"id": str(uuid4()), "t": owner["tenant"]})
            assert denied.value.orig.sqlstate == "42501"
            if index == 0:
                conn.commit()
            else:
                conn.rollback()
        for table in resources.values():
            assert conn.scalar(text(f"SELECT count(*) FROM {table}")) == 0


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_concurrent_client_sessions(api, agency):
    _, base, readers = agency

    def read(reader_data):
        reader, expected = reader_data
        for resource in ("clients", "campaigns", "deliverables", "actions"):
            reply = api.get(f"{base}/{resource}", headers=reader["headers"])
            assert reply.status_code == 200
            assert {r["id"] for r in reply.json()} == expected[resource]

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(read, readers * 4))


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_pg_registration_and_workspace_choices(api):
    email, password = f"inhouse-{uuid4().hex}@example.com", uuid4().hex
    result = api.post("/api/auth/register", json=dict(email=email, password=password, organization_name="In-house", mode="inhouse"))
    assert result.status_code == 201
    owner = account(api, "AgencySecond")
    base = "/api/tenants/" + owner["tenant"]
    client = create(api, base + "/clients", owner, {"name": "Named client"})
    create(api, base + "/members", owner, {"email": email, "role": "client_viewer", "client_id": client["id"]})
    login = api.post("/api/auth/login", json={"email": email, "password": password}).json()
    assert {(m["organization_name"], m["mode"], m["role"]) for m in login["tenants"]} == {
        ("In-house","inhouse","owner"), ("AgencySecond","agency","client_viewer")}
    own = api.get(f"/api/tenants/{result.json()['tenant_id']}/clients",
                  headers={"Authorization": "Bearer " + login["access_token"]})
    assert [c["name"] for c in own.json()] == ["Internal Marketing"]
