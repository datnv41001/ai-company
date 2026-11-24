"""Invitation-first contracts on SQLite and the actual restricted PostgreSQL LOGIN.

PYTEST_DONT_REWRITE
"""

from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.access import set_context
from app.database import engine
from app.security import sign_actor

from agency_fixtures import account, create
from identity_fixtures import start_registration, capture


def identity(api, email=None):
    email = email or f"onb-{uuid4().hex}@example.com"
    reg = start_registration(api,email,uuid4().hex)
    assert reg["tenant_id"] is None
    return {"email":email,"headers":{"Authorization":"Bearer "+reg["access_token"]}}


def verify(api, actor):
    assert api.post("/api/auth/verify-email", headers=actor["headers"], json={"token": capture(actor["email"])}).status_code == 204


def link_secret(email, iid):
    return capture(email, invitation_id=iid).split("#invite=")[1]


def test_account_only_and_idempotent_workspace(api):
    user = identity(api)
    payload = {"organization_name": "Internal team", "mode": "inhouse", "request_id": str(uuid4())}

    def make(**overrides):
        return api.post("/api/me/workspaces", headers=user["headers"], json={**payload, **overrides})

    assert make().status_code == 403
    verify(api, user)
    assert api.get("/api/me", headers=user["headers"]).json()["tenants"] == []
    first = make()
    assert first.status_code == 201
    assert make().json() == first.json()
    assert make(organization_name="Different").status_code == 409
    tenant = first.json()["tenant_id"]
    assert [m["tenant_id"] for m in api.get("/api/me", headers=user["headers"]).json()["tenants"]] == [tenant]
    assert len(api.get(f"/api/tenants/{tenant}/clients", headers=user["headers"]).json()) == 1


def test_invitation_before_account_resend_and_consent(api):
    owner = account(api, "Agency")
    tenant = owner["tenant"]
    base = f"/api/tenants/{tenant}"
    client = create(api, base + "/clients", owner, {"name": "Synthetic client"})
    email = f"invited-{uuid4().hex}@example.com"
    invitations = base + "/invitations"
    terms = {"email": email, "client_id": client["id"], "can_decide": True}
    offer = create(api, invitations, owner, terms)
    secret = link_secret(email, offer["id"])

    def use(actor, value, action="", **extra):
        return api.post("/api/me/invitation-link" + action, headers=actor["headers"], json={"token": value, **extra})

    wrong = account(api, "Other")
    assert use(wrong, secret).status_code == use(wrong, secret, "/accept").status_code == 404
    invited = identity(api, email)
    assert use(invited, secret, "/accept").status_code == 403
    verify(api, invited)
    assert api.get("/api/me", headers=invited["headers"]).json()["tenants"] == []
    assert use(invited, secret).json()["client_id"] == client["id"]
    replacement = api.post(invitations + "/" + offer["id"] + "/resend", headers=owner["headers"])
    assert replacement.status_code == 201
    assert use(invited, secret, "/accept").status_code == 404
    iid = replacement.json()["id"]
    secret = link_secret(email, iid)
    assert use(invited, secret, "/accept", role="owner").status_code == 422
    assert use(invited, secret).json()["can_decide"] is True
    if os.getenv("AMC_TEST_PG") and api.__class__.__name__ != "TestClient":
        with ThreadPoolExecutor(2) as pool:
            codes = list(pool.map(lambda _: use(invited, secret, "/accept").status_code, range(2)))
        assert sorted(codes) == [204, 404]
    else:
        assert use(invited, secret, "/accept").status_code == 204
    assert use(invited, secret, "/accept").status_code == 404
    [membership] = api.get("/api/me", headers=invited["headers"]).json()["tenants"]
    assert (membership["tenant_id"], membership["role"], membership["client_id"]) == (tenant, "client_viewer", client["id"])
    events = api.get(base + "/audit", headers=owner["headers"]).json()
    assert sum(e["event"] == "portal.invitation_accepted" and e["subject_id"] == iid for e in events) == 1
    assert api.post(invitations, headers=owner["headers"], json=terms).status_code == 409


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_verified_actor_and_email_challenge_have_separate_authority(api):
    pending = identity(api)
    uid = api.get("/api/me", headers=pending["headers"]).json()["id"]
    with Session(engine) as db:
        set_context(db, actor=uid)
        sign_actor(db, uid)
        assert db.scalar(text("select amc_acl.authenticated_actor()"))
        assert db.scalar(text("select not amc_acl.challenge_authorized('redeem',digest) from identity_challenges where user_id=:u"), {"u": uid})
        assert not db.scalar(text("select has_function_privilege(current_user,'amc_acl.complete_verified_email(text)','EXECUTE')"))
        with pytest.raises(ProgrammingError) as denied:
            db.execute(text("update identity_challenges set digest=digest where user_id=:u"), {"u": uid})
        assert denied.value.orig.sqlstate == "42501"
        db.rollback()
        assert db.scalar(text("select current_setting('amc.user_id')")) == uid
        assert db.scalar(text("select amc_acl.authenticated_actor()")) is False
    verify(api, pending)


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_withdrawn_and_expired_links_keep_workspace_private(api):
    owner = account(api, "Agency")
    recipient = identity(api)
    verify(api, recipient)
    base = f"/api/tenants/{owner['tenant']}"
    terms = {"email": recipient["email"], "role": "viewer"}
    for condition in ("revoke", "expire"):
        offer = create(api, base + "/invitations", owner, terms)
        secret = link_secret(recipient["email"], offer["id"])
        if condition == "revoke":
            assert api.delete(base + "/invitations/" + offer["id"], headers=owner["headers"]).status_code == 204
        else:
            with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as publisher:
                publisher.execute("update portal_invitations set expires_at=now()-interval '1 second' where id=%s", (offer["id"],))
        for path in ("/api/me/invitation-link", "/api/me/invitation-link/accept"):
            assert api.post(path, headers=recipient["headers"], json={"token": secret}).status_code == 404
        assert api.get(base + "/clients", headers=recipient["headers"]).status_code == 404
    wrong = api.post("/api/me/invitation-link", headers=recipient["headers"], json={"token": "private-marker"})
    assert wrong.status_code == 422 and "private-marker" not in wrong.text


def test_multiple_workspaces_pending_and_cross_tenant_resend(api):
    first, second = account(api, "First"), account(api, "Second")
    reader = identity(api)
    verify(api, reader)
    offers = []
    for owner, role in ((first, "viewer"), (second, "editor")):
        path = "/api/tenants/" + owner["tenant"] + "/invitations"
        offers.append(create(api, path, owner, {"email": reader["email"], "role": role}))
    first_path = "/api/tenants/" + first["tenant"] + "/invitations/"
    assert api.post(first_path + offers[1]["id"] + "/resend", headers=first["headers"]).status_code == 404
    inbox = api.get("/api/me/invitations", headers=reader["headers"]).json()
    assert {i["id"] for i in inbox} == {i["id"] for i in offers}
    for offer in offers:
        assert api.post("/api/me/invitations/" + offer["id"] + "/accept", headers=reader["headers"]).status_code == 204
    memberships = api.get("/api/me", headers=reader["headers"]).json()["tenants"]
    assert {(m["tenant_id"], m["role"]) for m in memberships} == {(first["tenant"], "viewer"), (second["tenant"], "editor")}
