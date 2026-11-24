from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from identity_fixtures import invite_member, verify_registration
from app.database import engine
from agency_fixtures import account, create


def test_client_reads_are_exact_and_symmetric(api, agency):
    owner, base, readers = agency
    for index, (reader, expected) in enumerate(readers):
        other = readers[1 - index][1]
        headers = reader["headers"]
        for resource in ("clients", "brands", "campaigns", "deliverables", "actions"):
            result = api.get(f"{base}/{resource}", headers=headers)
            assert result.status_code == 200
            assert {r["id"] for r in result.json()} == (expected[resource] if resource == "clients" else set())
        for cid in expected["campaigns"]:
            for suffix in ("", "/tasks"):
                assert api.get(f"{base}/campaigns/{cid}{suffix}", headers=headers).status_code == 404
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
    invite_member(api, base, owner["headers"], reader["headers"], email=reader["email"], role="viewer")
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
                assert set(conn.scalars(text(f"SELECT id FROM {table}"))) == (expected[key] if key == "clients" else set())
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
            assert {r["id"] for r in reply.json()} == (expected[resource] if resource == "clients" else set())

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
    verify_registration(api,email,result.json())
    invite_member(api, base, owner["headers"], {"Authorization":"Bearer "+result.json()["access_token"]}, email=email, role="client_viewer", client_id=client["id"])
    login = api.post("/api/auth/login", json={"email": email, "password": password}).json()
    assert {(m["organization_name"], m["mode"], m["role"]) for m in login["tenants"]} == {
        ("In-house","inhouse","owner"), ("AgencySecond","agency","client_viewer")}
    own = api.get(f"/api/tenants/{result.json()['tenant_id']}/clients",
                  headers={"Authorization": "Bearer " + login["access_token"]})
    assert [c["name"] for c in own.json()] == ["Internal Marketing"]
