"""State and ordering contracts for authorized invitation operations on synthetic records.
PYTEST_DONT_REWRITE
"""
from concurrent.futures import ThreadPoolExecutor
import os

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agency_fixtures import account, create
from app.access import set_context
from app.database import engine
from app.models import User
from app.recipients import accept, replace_invitation
from app.security import sign_actor
from test_verified_identity import check_acceptance_rows, wait_for_lock


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
@pytest.mark.parametrize(("first", "second", "expected"), [
    ("accept", "resend", 404), ("resend", "accept", 404),
    ("resend", "resend", 404), ("accept", "issue", 409),
])
def test_recipient_commands_have_one_serial_order(api, first, second, expected):
    owner, reader = account(api, "Issuing"), account(api, "ExistingB")
    t = owner["tenant"]
    base = f"/api/tenants/{t}"
    path = base + "/invitations"
    cid = create(api, base + "/clients", owner, {"name": "Client A"})["id"]
    terms = {"email": reader["email"], "client_id": cid}
    iid = create(api, path, owner, terms)["id"]
    actor = reader if first == "accept" else owner
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as monitor, ThreadPoolExecutor(1) as pool:
        with engine.begin() as conn, Session(conn, join_transaction_mode="create_savepoint") as db:
            assert conn.scalar(text("SELECT current_user")) == "amc_runtime"
            set_context(db, actor=actor["id"])
            sign_actor(db, actor["id"])
            user = db.get(User, actor["id"])
            if first == "accept":
                accept(iid, None, user, db)
            else:
                replacement = replace_invitation(t, iid, user, db)["id"]
            if second == "resend":
                pending = pool.submit(api.post, f"{path}/{iid}/resend", headers=owner["headers"])
            elif second == "issue":
                pending = pool.submit(api.post, path, headers=owner["headers"], json=terms)
            else:
                pending = pool.submit(api.post, f"/api/me/invitations/{iid}/accept", headers=reader["headers"])
            wait_for_lock(monitor, conn.scalar(text("SELECT pg_backend_pid()")))
        assert pending.result(timeout=10).status_code == expected
        state = check_acceptance_rows(monitor, t, reader["id"], iid, first == "accept")
        assert state == ("accepted" if first == "accept" else "revoked")
        rows = monitor.execute("select id from portal_invitations where tenant_id=%s and email=lower(%s) and state='pending'",
                               (t, reader["email"])).fetchall()
        assert rows == ([] if first == "accept" else [(replacement,)])
        assert monitor.execute("select role from memberships where tenant_id=%s and user_id=%s",
                               (reader["tenant"], reader["id"])).fetchone() == ("owner",)


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_signed_runtime_and_historical_pending_cleanup(api):
    owner, other, reader = account(api, "AgencyA"), account(api, "Other"), account(api, "WorkspaceB")
    base = f"/api/tenants/{owner['tenant']}"
    cid = create(api, base + "/clients", owner, {"name": "Client A"})["id"]
    pending = create(api, base + "/invitations", owner, {"email":reader["email"], "client_id":cid})
    untouched = create(api, f"/api/tenants/{other['tenant']}/invitations", other, {"email":reader["email"], "role":"viewer"})
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as fixture:
        # A historical import can contain an issued offer alongside an existing member.
        fixture.execute("insert into memberships(tenant_id,user_id,role,client_id) values(%s,%s,'client_viewer',%s)",
                        (owner["tenant"],reader["id"],cid))
    with Session(engine) as db:
        set_context(db, actor=owner["id"], tenant=owner["tenant"], email=reader["email"])
        sign_actor(db, owner["id"])
        assert db.scalar(text("select current_user")) == "amc_runtime"
        assert db.scalar(text("select amc_acl.authenticated_actor()")) is True
        assert not db.scalar(text("select has_table_privilege(current_user,'public.memberships','DELETE')"))
        assert db.scalar(text("select has_function_privilege(current_user,'amc_acl.revoke_client_member(text,text)','EXECUTE')"))
        with pytest.raises(IntegrityError) as conflict:
            # This trigger runs before ordinary uniqueness checks; it must reject a member.
            db.execute(text("""insert into portal_invitations
                select (jsonb_populate_record(null::portal_invitations, to_jsonb(i) ||
                jsonb_build_object('id',gen_random_uuid()::text,'link_digest',repeat('f',64)))).*
                from portal_invitations i where id=:iid"""), {"iid":pending["id"]})
        assert conflict.value.orig.sqlstate == "23505"
        assert conflict.value.orig.diag.message_primary == "Recipient already belongs to workspace"
    assert api.delete(f"{base}/members/{reader['id']}/client-scope", headers=owner["headers"]).status_code == 204
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as monitor:
        assert check_acceptance_rows(monitor, owner["tenant"], reader["id"], pending["id"], False) == "revoked"
        assert monitor.execute("select state from portal_invitations where id=%s", (untouched["id"],)).fetchone() == ("pending",)
        assert monitor.execute("select role from memberships where tenant_id=%s and user_id=%s",
                               (reader["tenant"], reader["id"])).fetchone() == ("owner",)


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_delivery_failure_keeps_original_offer(api, monkeypatch):
    owner, reader = account(api, "AgencyA"), account(api, "WorkspaceB")
    path = f"/api/tenants/{owner['tenant']}/invitations"
    offer = create(api, path, owner, {"email":reader["email"], "role":"viewer"})
    from app import recipients

    def unavailable(*args):
        raise OSError("Synthetic mailbox unavailable")

    monkeypatch.setattr(recipients, "deliver_invitation", unavailable)
    assert api.post(f"{path}/{offer['id']}/resend", headers=owner["headers"]).status_code == 500
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as monitor:
        assert monitor.execute("select id,state from portal_invitations where tenant_id=%s and email=lower(%s)",
                               (owner["tenant"],reader["email"])).fetchall() == [(offer["id"],"pending")]
        assert monitor.execute("select count(*) from audit_events where subject_id=%s and event='portal.invitation_revoked'",
                               (offer["id"],)).fetchone() == (0,)


@pytest.mark.parametrize("bound", [True, False])
def test_sqlite_offboarding_keeps_history_and_other_workspace(tmp_path, bound):
    from sqlalchemy import create_engine
    from app.database import Base
    from app.delivery_models import PortalInvitation
    from app.recipients import revoke_pending
    from app.models import utcnow

    local = create_engine("sqlite:///" + str(tmp_path / "history.db"))
    Base.metadata.create_all(local)
    with Session(local) as db:
        for tenant, state in (("one","pending"),("other","pending"),("one","accepted")):
            db.add(PortalInvitation(id=tenant + state, tenant_id=tenant, state=state, role="viewer",
                                    user_id="member" if bound else None, email="Review@Example.com",
                                    invited_by="issuer", workspace_name=tenant, can_comment=False, can_decide=False, expires_at=utcnow()))
        db.flush()
        revoke_pending(db, "one", "member", "review@example.com")
        db.commit()
        assert db.get(PortalInvitation, "onepending").state == "revoked"
        assert db.get(PortalInvitation, "otherpending").state == "pending"
        assert db.get(PortalInvitation, "oneaccepted").state == "accepted"
    local.dispose()


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_repeated_offboarding_takes_one_lock_order(api):
    owner, reader = account(api, "Agency"), account(api, "Independent")
    t = owner["tenant"]
    base = f"/api/tenants/{t}"
    cid = create(api, base + "/clients", owner, {"name":"Client"})["id"]
    offer = create(api, base + "/invitations", owner, {"email":reader["email"], "client_id":cid})
    assert api.post(f"/api/me/invitations/{offer['id']}/accept", headers=reader["headers"]).status_code == 204
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as monitor, ThreadPoolExecutor(1) as pool:
        with engine.begin() as conn, Session(conn, join_transaction_mode="create_savepoint") as db:
            set_context(db, actor=owner["id"], tenant=t)
            sign_actor(db, owner["id"])
            assert db.scalar(text("select amc_acl.revoke_client_member(:t,:u)"), {"t":t,"u":reader["id"]})
            db.commit()  # Release the session savepoint while the outer transaction retains its locks.
            second = pool.submit(api.delete, f"{base}/members/{reader['id']}/client-scope", headers=owner["headers"])
            wait_for_lock(monitor, conn.scalar(text("select pg_backend_pid()")))
        assert second.result(timeout=10).status_code == 404
        assert monitor.execute("select count(*) from audit_events where tenant_id=%s and subject_id=%s and event='member.client_scope_revoked'",
                               (t, reader["id"])).fetchone() == (1,)
        assert monitor.execute("select count(*) from portal_grants where tenant_id=%s and user_id=%s", (t,reader["id"])).fetchone() == (0,)
