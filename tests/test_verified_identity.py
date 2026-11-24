"""User-visible identity contracts, including the runtime LOGIN and independent transactions."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import os
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text

from agency_fixtures import account, create
from app.database import engine


def register(api, mode="agency"):
    email = f"proof-{uuid4().hex}@example.com"
    result = api.post("/api/auth/register", json=dict(email=email, password=uuid4().hex, mode=mode, organization_name="Synthetic"))
    assert result.status_code == 201
    record = result.json()
    return email, record, {"Authorization": "Bearer " + record["access_token"]}


def capture(email):
    mailbox = Path(os.getenv("AMC_DEV_MAILBOX_DIR", ".dev-mailbox"))
    address = sha256(email.lower().encode()).hexdigest()
    return max((mailbox / address).glob("*.txt"), key=lambda p: p.stat().st_mtime_ns).read_text().strip()


def accept(api, identity, invitation, **kwargs):
    return api.post("/api/me/invitations/" + invitation + "/accept", headers=identity, **kwargs)


def test_new_owner_requires_private_single_use_proof(api):
    email, registration, headers = register(api, "inhouse")
    me = lambda: api.get("/api/me", headers=headers).json()
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
    reply = api.post(base + "/members", headers=owner["headers"], json={"email":recipient["email"], "role":"editor"})
    assert reply.status_code == 410
    assert api.get(base + "/clients", headers=recipient["headers"]).status_code == 404


def test_invitation_requires_verified_recipient_and_frozen_scope(api, agency):
    owner, base, ((_, data), _) = agency
    email, _, headers = register(api)
    body = {"email":email, "client_id":next(iter(data["clients"])), "can_decide":True, "can_comment":False}
    iid = create(api, base + "/invitations", owner, body)["id"]
    assert accept(api, headers, iid).status_code == 403
    assert api.get(base + "/clients", headers=headers).status_code == 404
    assert api.post("/api/auth/verify-email", headers=headers, json={"token":capture(email)}).status_code == 204
    assert accept(api, headers, iid, json={"role":"admin","tenant_id":owner["tenant"]}).status_code == 422
    assert accept(api, headers, iid).status_code == 204
    assert accept(api, headers, iid).status_code == 404


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_runtime_has_no_direct_membership_or_bootstrap_grant(api):
    with engine.connect() as c:
        assert c.scalar(text("SELECT current_user")) == "amc_runtime"
        for table in ("memberships", "portal_grants"):
            assert not c.scalar(text("SELECT has_table_privilege(current_user,:table,'INSERT')"), {"table":table})
        assert not c.scalar(text("SELECT has_function_privilege(current_user,'amc_acl.create_workspace(text,text,text)','EXECUTE')"))


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_accept_race_single_audit_and_issuer_authority(api, agency):
    owner, base, _ = agency
    staff, candidate = account(api, "Issuer"), account(api, "Candidate")
    def invite(issuer, recipient, role):
        return create(api, base + "/invitations", issuer, {"email":recipient["email"],"role":role})["id"]
    first = invite(owner, staff, "admin")
    gate = Barrier(2)
    def receive():
        gate.wait(timeout=10)
        return accept(api, staff["headers"], first).status_code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(f.result() for f in [pool.submit(receive),pool.submit(receive)]) == [204,404]
    second = invite(staff, candidate, "editor")
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as c:
        c.execute("UPDATE memberships SET role='viewer' WHERE tenant_id=%s AND user_id=%s",(owner["tenant"],staff["id"]))
    assert accept(api, candidate["headers"], second).status_code == 404
    assert api.get(base + "/clients", headers=candidate["headers"]).status_code == 404
    events = api.get(base + "/audit",headers=owner["headers"]).json()
    assert sum(e["subject_id"] == first and e["event"]=="portal.invitation_accepted" for e in events) == 1
