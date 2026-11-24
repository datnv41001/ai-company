"""Invitation-first contracts on SQLite and the actual restricted PostgreSQL LOGIN.

PYTEST_DONT_REWRITE
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4


from agency_fixtures import account, create
from identity_fixtures import capture


def identity(api, email=None):
    email = email or f"onb-{uuid4().hex}@example.com"
    response = api.post("/api/auth/register", json={"email": email, "password": uuid4().hex})
    assert response.status_code == 201
    assert response.json()["tenant_id"] is None
    return {"email": email, "headers": {"Authorization": "Bearer " + response.json()["access_token"]}}


def verify(api, actor):
    assert api.post("/api/auth/verify-email", headers=actor["headers"], json={"token": capture(actor["email"])}).status_code == 204


def link_secret(email, iid):
    root = Path(os.getenv("AMC_DEV_MAILBOX_DIR", ".dev-mailbox"))
    directory = root / sha256(email.lower().encode()).hexdigest() / "invitations"
    return (directory / (iid + ".txt")).read_text().strip().split("#invite=")[1]


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
    client = create(api, base+"/clients", owner, {"name":"Synthetic client"})
    email = f"invited-{uuid4().hex}@example.com"
    invitations = base+"/invitations"
    terms = {"email":email, "client_id":client["id"], "can_decide":True}
    offer = create(api, invitations, owner, terms)
    secret = link_secret(email, offer["id"])
    def use(actor, value, action="", **extra):
        return api.post("/api/me/invitation-link"+action, headers=actor["headers"], json={"token":value, **extra})
    wrong = account(api, "Other")
    assert use(wrong, secret).status_code == use(wrong, secret,"/accept").status_code == 404
    invited = identity(api, email)
    assert use(invited,secret,"/accept").status_code == 403
    verify(api,invited)
    assert api.get("/api/me",headers=invited["headers"]).json()["tenants"] == []
    assert use(invited,secret).json()["client_id"] == client["id"]
    replacement = api.post(invitations+"/"+offer["id"]+"/resend", headers=owner["headers"])
    assert replacement.status_code == 201
    assert use(invited,secret,"/accept").status_code == 404
    iid = replacement.json()["id"]
    secret = link_secret(email, iid)
    assert use(invited,secret,"/accept",role="owner").status_code == 422
    assert use(invited,secret).json()["can_decide"] is True
    if os.getenv("AMC_TEST_PG") and api.__class__.__name__ != "TestClient":
        with ThreadPoolExecutor(2) as pool:
            codes = list(pool.map(lambda _: use(invited,secret,"/accept").status_code,range(2)))
        assert sorted(codes) == [204,404]
    else:
        assert use(invited,secret,"/accept").status_code == 204
    assert use(invited,secret,"/accept").status_code == 404
    [membership] = api.get("/api/me", headers=invited["headers"]).json()["tenants"]
    assert (membership["tenant_id"],membership["role"],membership["client_id"]) == (tenant,"client_viewer",client["id"])
    events = api.get(base+"/audit",headers=owner["headers"]).json()
    assert sum(e["event"]=="portal.invitation_accepted" and e["subject_id"]==iid for e in events) == 1
    assert api.post(invitations,headers=owner["headers"],json=terms).status_code == 409
