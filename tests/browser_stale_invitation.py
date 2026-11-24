"""Observe a real old browser page and a separately authenticated issuer."""
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import psycopg
from playwright.sync_api import expect

from identity_fixtures import capture


def database_state(tenant, other, uid, old, new):
    # Only server-generated UUIDs reach this read-only query in the disposable database.
    t, b, u, i, j = [str(UUID(v)) for v in (tenant, other, uid, old, new)]
    query = f"""SELECT json_build_object(
        'states',(SELECT json_agg(state ORDER BY id='{i}' DESC) FROM portal_invitations WHERE id IN ('{i}','{j}')),
        'members',(SELECT count(*) FROM memberships WHERE tenant_id='{t}' AND user_id='{u}'),
        'grants',(SELECT count(*) FROM portal_grants WHERE tenant_id='{t}' AND user_id='{u}'),
        'accepted',(SELECT count(*) FROM audit_events WHERE tenant_id='{t}' AND event='portal.invitation_accepted'
                    AND subject_id IN ('{i}','{j}')),
        'other',(SELECT role FROM memberships WHERE tenant_id='{b}' AND user_id='{u}'))"""
    project = os.getenv("AMC_BROWSER_MAILBOX_PROJECT")
    if project:
        raw = subprocess.check_output(["docker", "compose", "-p", project, "exec", "-T", "db",
                                       "psql", "-XqtA", "-v", "ON_ERROR_STOP=1", "-U", "amc", "-d", "amc", "-c", query])
        return json.loads(raw)
    dsn = os.getenv("AMC_BROWSER_ASSERT_DSN")
    if dsn:
        with psycopg.connect(dsn) as db:
            assert db.info.host in ("127.0.0.1", "localhost", "::1") and db.info.dbname.startswith("amc_test")
            return db.execute(query).fetchone()[0]
    return None


def exercise_stale(browser, origin, viewport, user, issuer_token, tenant, client, brand, campaign):
    token, other, uid, email, password = user("ExistingWorkspaceB")
    project = os.getenv("AMC_BROWSER_MAILBOX_PROJECT")
    auth = {"Authorization":"Bearer " + token}
    path = f"/api/tenants/{tenant}/invitations"
    with httpx.Client(base_url=origin, headers={"Authorization":"Bearer " + issuer_token}, trust_env=False) as issuer:
        def open_consent(iid):
            page = browser.new_page(viewport=viewport)
            url = capture(email, project, iid)
            page.goto(origin + "/#" + urlsplit(url).fragment)
            form = page.locator("#login-form")
            form.get_by_label("Email").fill(email)
            form.get_by_label("Mật khẩu").fill(password)
            form.get_by_role("button").click()
            panel = page.locator("#recipient-panel > section")
            expect(panel).to_contain_text(campaign["name"])
            return page, panel

        def assert_state(states, count):
            value = database_state(tenant, other, uid, old, new)
            if value is not None:
                assert value == {"states":states, "members":count, "grants":count, "accepted":count, "other":"owner"}

        def screenshot(page, stage):
            if directory := os.getenv("AMC_ONBOARDING_SCREENSHOTS"):
                Path(directory).mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(Path(directory) / f"resend-{viewport['width']}-{stage}.png"))

        prior_b = issuer.get(f"/api/tenants/{other}/clients", headers=auth)
        prior_b.raise_for_status()
        terms = dict(email=email, client_id=client["id"], brand_id=brand["id"],
                     campaign_id=campaign["id"], can_comment=True, can_decide=False)
        issued = issuer.post(path, json=terms)
        issued.raise_for_status()
        old = issued.json()["id"]
        page, panel = open_consent(old)
        replaced = issuer.post(f"{path}/{old}/resend")
        replaced.raise_for_status()
        new = replaced.json()["id"]
        assert new != old
        for iid in (old, new):
            secret = urlsplit(capture(email, project, iid)).fragment.removeprefix("invite=")
            assert issuer.post("/api/me/invitation-link/accept", json={"token":secret}).status_code == 404
        with page.expect_response(lambda response: response.url.endswith("/invitation-link/accept")) as rejected:
            panel.get_by_role("button", name="Chấp nhận lời mời").click()
        assert rejected.value.status == 404
        expect(page.locator("#link-hint")).to_contain_text("Lời mời này không còn hiệu lực")
        expect(page.get_by_role("button", name="Chấp nhận lời mời")).to_have_count(0)
        expect(page.locator("#notice")).to_contain_text("chưa thay đổi")
        screenshot(page, "stale")
        assert_state(["revoked","pending"], 0)
        me = issuer.get("/api/me", headers=auth).json()
        assert [(m["tenant_id"],m["role"]) for m in me["tenants"]] == [(other,"owner")]
        page.close()
        page, panel = open_consent(new)
        panel.get_by_role("button", name="Chấp nhận lời mời").click()
        expect(page.locator("#workspace-select")).to_have_value(tenant)
        expect(page.locator("#workspace-select option")).to_have_count(2)
        assert_state(["revoked","accepted"], 1)
        grants = issuer.get(f"/api/tenants/{tenant}/recipients").json()
        [grant] = [g for g in grants if g["user_id"] == uid]
        for key in ("client_id","brand_id","campaign_id","can_comment","can_decide"):
            assert grant[key] == terms[key]
        assert issuer.get(f"/api/tenants/{other}/clients", headers=auth).json() == prior_b.json()
        screenshot(page, "accepted")
        page.close()
