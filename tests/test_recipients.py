from agency_fixtures import account, create


def test_recipient_invitations_and_revocation(api, agency):
    admin, base, ((alice, a), (bob, b)) = agency
    new = account(api, "Invitee")
    client_id = next(iter(a["clients"]))
    brand_id = next(iter(a["brands"]))
    payload = {"email": new["email"], "client_id": client_id, "brand_id": brand_id, "can_decide": True, "can_comment": False}
    invitations = base + "/invitations"
    for outsider in (alice, new):
        for suffix in ("/invitations", "/recipients"):
            assert api.get(base + suffix, headers=outsider["headers"]).status_code == 404
        assert api.post(invitations, headers=outsider["headers"], json=payload).status_code == 404
    assert api.post(invitations, headers=admin["headers"], json={**payload, "brand_id": next(iter(b["brands"]))}).status_code == 404
    assert api.post(invitations, headers=admin["headers"], json={**payload, "email": alice["email"]}).status_code == 409

    def issue():
        return create(api, invitations, admin, payload)["id"]

    def accept(actor, iid):
        return api.post("/api/me/invitations/" + iid + "/accept", headers=actor["headers"])

    invite = issue()
    assert api.post(invitations, headers=admin["headers"], json=payload).status_code == 409
    assert api.get(base + "/clients", headers=new["headers"]).status_code == 404
    assert api.get("/api/me/invitations", headers=bob["headers"]).json() == []
    assert accept(bob, invite).status_code == 404
    assert api.delete(invitations + "/" + invite, headers=admin["headers"]).status_code == 204
    assert accept(new, invite).status_code == 404
    invite = issue()
    assert [i["id"] for i in api.get("/api/me/invitations", headers=new["headers"]).json()] == [invite]
    assert accept(new, invite).status_code == 204
    assert accept(new, invite).status_code == 404
    grants = api.get(base + "/recipients", headers=admin["headers"]).json()
    grant = next(g for g in grants if g["user_id"] == new["id"])
    assert grant == {
        "email": new["email"].lower(),
        "user_id": new["id"],
        "client_id": client_id,
        "brand_id": brand_id,
        "campaign_id": None,
        "can_comment": False,
        "can_decide": True,
    }
    assert {c["id"] for c in api.get(base + "/clients", headers=new["headers"]).json()} == {client_id}
    assert api.delete(base + "/members/" + new["id"] + "/client-scope", headers=admin["headers"]).status_code == 204
    assert api.get(base + "/reviews", headers=new["headers"]).status_code == 404
    assert accept(new, invite).status_code == 404


def test_expired_invitation_and_recipient_sql_boundary(api, agency):
    import os
    from contextlib import closing
    import psycopg
    from sqlalchemy import text
    from app.database import engine, get_db
    from app.main import app

    admin, base, ((alice, data), _) = agency
    invited = account(api, "Expiry")
    body = {"email": invited["email"], "client_id": next(iter(data["clients"])), "can_comment": True, "can_decide": False}
    iid = create(api, base + "/invitations", admin, body)["id"]
    if get_db in app.dependency_overrides:
        with closing(app.dependency_overrides[get_db]()) as dependency:
            session = next(dependency)
            session.execute(text("UPDATE portal_invitations SET expires_at='2020-01-01' WHERE id=:i"), {"i": iid})
            session.commit()
    else:
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
            owner.execute("UPDATE portal_invitations SET expires_at='2020-01-01' WHERE id=%s", (iid,))
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM portal_invitations")) == 0
            conn.execute(text("SELECT set_config('amc.user_id',:u,true),set_config('amc.tenant_id',:t,true)"), {"u": alice["id"], "t": admin["tenant"]})
            assert conn.scalar(text("SELECT count(*) FROM portal_invitations")) == 0
            assert conn.scalar(text("SELECT count(*) FROM amc_acl.recipient_emails(:t)"), {"t": admin["tenant"]}) == 0
            assert not conn.scalar(text("SELECT amc_acl.accept_portal_invitation(:i)"), {"i": iid})
    assert api.get("/api/me/invitations", headers=invited["headers"]).json() == []
    assert api.post("/api/me/invitations/" + iid + "/accept", headers=invited["headers"]).status_code == 404
    replacement = create(api, base + "/invitations", admin, body)["id"]
    assert replacement != iid
