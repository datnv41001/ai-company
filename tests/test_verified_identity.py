"""User-visible identity contracts, including the runtime LOGIN and independent transactions."""

from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier
import time
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from identity_fixtures import capture
from agency_fixtures import account, create
from app.database import engine
from app.access import set_context
from app.models import User
from app.recipients import accept as accept_route, withdraw
from app.security import sign_actor


def register(api, mode="agency"):
    email = f"proof-{uuid4().hex}@example.com"
    result = api.post("/api/auth/register", json=dict(email=email, password=uuid4().hex, mode=mode, organization_name="Synthetic"))
    assert result.status_code == 201
    record = result.json()
    return email, record, {"Authorization": "Bearer " + record["access_token"]}


def accept(api, identity, invitation, **kwargs):
    return api.post("/api/me/invitations/" + invitation + "/accept", headers=identity, **kwargs)


def test_new_owner_requires_private_single_use_proof(api):
    email, registration, headers = register(api, "inhouse")

    def me():
        return api.get("/api/me", headers=headers).json()

    assert me()["tenants"] == []
    proof = capture(email)
    assert len(proof) >= 43 and proof not in str(registration) and proof not in str(me())
    _, _, other = register(api)

    def verify(actor):
        return api.post("/api/auth/verify-email", headers=actor, json={"token": proof}).status_code

    assert verify(other) == 400
    assert verify(headers) == 204
    assert verify(headers) == 400
    assert me()["email_verified"] is True
    assert [(m["tenant_id"], m["role"]) for m in me()["tenants"]] == [(registration["tenant_id"], "owner")]


def test_retired_direct_grant(api, agency):
    owner, base, _ = agency
    recipient = account(api, "Staff")
    reply = api.post(base + "/members", headers=owner["headers"], json={"email": recipient["email"], "role": "editor"})
    assert reply.status_code == 410
    assert api.get(base + "/clients", headers=recipient["headers"]).status_code == 404


def test_invitation_requires_verified_recipient_and_frozen_scope(api, agency):
    owner, base, ((_, data), _) = agency
    email, _, headers = register(api)
    body = {"email": email, "client_id": next(iter(data["clients"])), "can_decide": True, "can_comment": False}
    iid = create(api, base + "/invitations", owner, body)["id"]
    assert api.get("/api/me/invitations", headers=headers).json() == []
    assert accept(api, headers, iid).status_code == 403
    assert api.get(base + "/clients", headers=headers).status_code == 404
    assert api.post("/api/auth/verify-email", headers=headers, json={"token": capture(email)}).status_code == 204
    assert accept(api, headers, iid, json={"role": "admin", "tenant_id": owner["tenant"]}).status_code == 422
    assert accept(api, headers, iid).status_code == 204
    assert accept(api, headers, iid).status_code == 404


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_runtime_has_no_direct_membership_or_bootstrap_grant(api):
    with engine.connect() as c:
        assert c.scalar(text("SELECT current_user")) == "amc_runtime"
        assert c.execute(text("select rolsuper,rolbypassrls from pg_roles where rolname=current_user")).one() == (False, False)
        assert not c.scalar(text("select has_column_privilege(current_user,'users','verified_at','UPDATE')"))
        assert not c.scalar(text("select has_column_privilege(current_user,'users','verified_at','INSERT')"))
        assert not c.scalar(text("select has_table_privilege(current_user,'amc_acl.identity_key','SELECT')"))
        for table in ("memberships", "portal_grants"):
            assert not c.scalar(text("SELECT has_table_privilege(current_user,:table,'INSERT')"), {"table": table})
        assert not c.scalar(text("SELECT has_function_privilege(current_user,'amc_acl.create_workspace(text,text,text)','EXECUTE')"))


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_accept_race_single_audit_and_issuer_authority(api, agency):
    owner, base, _ = agency
    staff, candidate = account(api, "Issuer"), account(api, "Candidate")

    def invite(issuer, recipient, role):
        return create(api, base + "/invitations", issuer, {"email": recipient["email"], "role": role})["id"]

    first = invite(owner, staff, "admin")
    gate = Barrier(2)

    def receive():
        gate.wait(timeout=10)
        return accept(api, staff["headers"], first).status_code

    with ThreadPoolExecutor(2) as pool:
        assert sorted(f.result() for f in [pool.submit(receive), pool.submit(receive)]) == [204, 404]
    assert api.post(base + "/invitations", headers=staff["headers"], json={"email": candidate["email"], "role": "admin"}).status_code == 403
    second = invite(staff, candidate, "editor")
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as c:
        c.execute("UPDATE memberships SET role='viewer' WHERE tenant_id=%s AND user_id=%s", (owner["tenant"], staff["id"]))
    assert accept(api, candidate["headers"], second).status_code == 404
    assert api.get(base + "/clients", headers=candidate["headers"]).status_code == 404
    events = api.get(base + "/audit", headers=owner["headers"]).json()
    assert sum(e["subject_id"] == first and e["event"] == "portal.invitation_accepted" for e in events) == 1


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
@pytest.mark.parametrize("first", ["accept", "revoke"])
def test_accept_and_revoke_lock_order(api, agency, first):
    owner, base, ((_, data), _) = agency
    reader = account(api, "Race")
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as monitor:

        def effects():
            return monitor.execute(
                "select (select count(*) from amc_ops.attempts),(select count(*) from amc_ops.ledger),(select count(*) from workforce_runs)"
            ).fetchone()

        before = effects()
        iid = create(api, base + "/invitations", owner, {"email": reader["email"], "client_id": next(iter(data["clients"]))})["id"]
        with engine.connect() as conn, conn.begin() as transaction, Session(conn, join_transaction_mode="create_savepoint") as db:
            # Run the real handler under the first outer transaction. Its commit
            # releases the savepoint while the invitation row stays locked.
            actor = reader if first == "accept" else owner
            set_context(db, actor=actor["id"], tenant=owner["tenant"])
            sign_actor(db, actor["id"])
            user = db.get(User, actor["id"])
            if first == "accept":
                accept_route(iid, None, user, db)

                def second():
                    return api.delete(base + "/invitations/" + iid, headers=owner["headers"])
            else:
                withdraw(owner["tenant"], iid, user, db)

                def second():
                    return accept(api, reader["headers"], iid)

            pid = conn.scalar(text("SELECT pg_backend_pid()"))
            with ThreadPoolExecutor(1) as pool:
                waiting = pool.submit(second)
                try:
                    timeout = time.monotonic() + 6
                    while not monitor.execute(
                        "select exists(select from pg_stat_activity where datname=current_database() and %s=any(pg_blocking_pids(pid)))", (pid,)
                    ).fetchone()[0]:
                        assert time.monotonic() < timeout, "Second transaction did not contend for the row"
                        time.sleep(0.02)
                finally:
                    transaction.commit()
                assert waiting.result(timeout=8).status_code == 404
        expected = int(first == "accept")
        for table in ("memberships", "portal_grants"):
            count = monitor.execute(f"select count(*) from {table} where tenant_id=%s and user_id=%s", (owner["tenant"], reader["id"])).fetchone()[0]
            assert count == expected
        assert monitor.execute("select count(*) from audit_events where subject_id=%s and event='portal.invitation_accepted'", (iid,)).fetchone() == (expected,)
        assert before == effects()


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_expired_and_replaced_email_proof(api):
    email, reg, headers = register(api)
    old = capture(email)
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
        digest = owner.execute("select digest from identity_challenges where user_id=%s", (reg["user_id"],)).fetchone()[0]
        from hashlib import sha256

        assert digest == sha256(old.encode()).hexdigest()
        owner.execute("update identity_challenges set expires_at=now()-interval '1 minute' where user_id=%s", (reg["user_id"],))
    assert api.post("/api/auth/verify-email", headers=headers, json={"token": old}).status_code == 400
    assert api.post("/api/auth/request-verification", headers=headers).status_code == 204
    new = capture(email)
    assert new != old
    assert api.post("/api/auth/verify-email", headers=headers, json={"token": old}).status_code == 400
    assert api.post("/api/auth/verify-email", headers=headers, json={"token": new}).status_code == 204


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_legacy_inhouse_owner_verifies_without_another_workspace(api):
    from app.security import hash_password

    password = uuid4().hex
    uid, tenant = str(uuid4()), str(uuid4())
    address = f"legacy-{uid}@example.com"
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
        owner.execute("insert into users(id,email,password_hash,created_at) values(%s,%s,%s,now())", (uid, address, hash_password(password)))
        owner.execute("insert into tenants values(%s,'Legacy internal','inhouse',now())", (tenant,))
        owner.execute("insert into memberships(tenant_id,user_id,role) values(%s,%s,'owner')", (tenant, uid))
    login = api.post("/api/auth/login", json={"email": address, "password": password}).json()
    headers = {"Authorization": "Bearer " + login["access_token"]}
    assert login["email_verified"] is False
    assert [m["tenant_id"] for m in login["tenants"]] == [tenant]
    base = "/api/tenants/" + tenant
    assert api.get(base + "/clients", headers=headers).status_code == 200
    staff = account(api, "InhouseStaff")
    terms = {"email": staff["email"], "role": "editor"}
    assert api.post(base + "/invitations", headers=headers, json=terms).status_code == 403
    assert api.post("/api/auth/request-verification", headers=headers).status_code == 204
    assert api.post("/api/auth/verify-email", headers=headers, json={"token": capture(address)}).status_code == 204
    invite = api.post(base + "/invitations", headers=headers, json=terms)
    assert invite.status_code == 201
    assert accept(api, staff["headers"], invite.json()["id"]).status_code == 204
    assert [m["tenant_id"] for m in api.get("/api/me", headers=headers).json()["tenants"]] == [tenant]
