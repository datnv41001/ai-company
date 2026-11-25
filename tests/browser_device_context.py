"""Chromium acceptance for genuine cookie commits in one shared browser profile."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright


def exercise_device_context(browser, origin, viewport):
    assert urlsplit(origin).hostname in ("localhost", "127.0.0.1")
    accounts = [(f"device-{uuid4().hex}@example.com", uuid4().hex) for _ in range(2)]
    with httpx.Client(base_url=origin, trust_env=False) as http:
        for email, password in accounts:
            assert http.post("/api/auth/register", json={"email": email, "password": password}).status_code == 202

    def sign_in(page, account):
        page.goto(origin)
        form = page.locator("#login-form")
        form.get_by_label("Email").fill(account[0])
        form.get_by_label("Mật khẩu").fill(account[1])
        with page.expect_response("**/api/auth/login") as logged:
            form.get_by_role("button").click()
        expect(page.locator("#verify-address")).to_have_text(account[0])
        payload = logged.value.json()["access_token"].split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "==="))["sid"]

    def age_access(page):
        # Exercise the normal tab renewal threshold without sleeping five minutes.
        page.clock.set_fixed_time(datetime.now(timezone.utc) + timedelta(minutes=6))

    def grant(context, sid):
        selected = {c["name"]: c["value"] for c in context.cookies(origin)}
        raw = selected["__Host-amc-refresh-" + sid]
        return selected["__Host-amc-context"], hashlib.sha256(raw.encode()).digest()

    def open_devices(page):
        page.locator("#device-panel summary").click()

    def renew_and_display(page):
        age_access(page)
        with page.expect_response("**/api/auth/refresh") as refreshed:
            open_devices(page)
        assert refreshed.value.status == 200
        expect(page.locator("#device-list")).to_contain_text("Phiên hiện tại")

    for race in ("stale_tab", "late_refresh", "logout", "same_account"):
        context = browser.new_context(viewport=viewport)
        try:
            a, b = context.new_page(), context.new_page()
            sid_a = sign_in(a, accounts[0])
            if race == "same_account":
                sid_b = sign_in(b, accounts[0])
                assert sid_b != sid_a
                renew_and_display(a)
                renew_and_display(b)
                continue

            if race == "stale_tab":
                sid_b = sign_in(b, accounts[1])
                original = grant(context, sid_b)
                age_access(a)
                open_devices(a)
                expect(a.locator("#notice")).to_contain_text("đã thay đổi")
                # Send the tab's intended family with the active browser jar.
                # An unmodified B grant must still be accepted immediately after.
                status = a.evaluate("""async ([old, current]) => {
                    const csrf = document.cookie.split('; ').find(v => v.startsWith('__Host-amc-csrf-'+current+'=')).split('=')[1];
                    const response = await fetch('/api/auth/refresh', {method:'POST', headers:{'X-AMC-CSRF':csrf,'X-AMC-Session':old}});
                    return response.status;
                }""", [sid_a, sid_b])
                assert status == 409 and grant(context, sid_b) == original
                renew_and_display(b)
                continue

            held = []
            dispatched = []
            a.on("request", lambda request: dispatched.append(urlsplit(request.url).path))
            def hold_after_commit(route):
                actual = route.fetch()
                assert actual.status == 200
                held.append((route, actual))
            a.route("**/api/auth/refresh", hold_after_commit)
            age_access(a)
            open_devices(a)
            for _ in range(250):
                if held:
                    break
                a.wait_for_timeout(20)
            assert held, "Refresh must reach the real API and commit before the next operation"
            route, actual = held.pop()
            if race == "late_refresh":
                sid_b = sign_in(b, accounts[1])
                original = grant(context, sid_b)
                route.fulfill(response=actual)
                expect(a.locator("#notice")).to_contain_text("đã thay đổi")
                assert grant(context, sid_b) == original
                expect(a.locator("#device-list li")).to_have_count(0)
                renew_and_display(b)
            else:
                a.locator("#switch-account").click()
                route.fulfill(response=actual)
                expect(a.locator("#login-form")).to_be_visible()
                expect(a.locator("#device-panel")).to_be_hidden()
                assert "/api/auth/logout" in dispatched
                assert not any(c["name"] == "__Host-amc-refresh-"+sid_a for c in context.cookies(origin))
            assert "/api/me/sessions" not in dispatched, "An invalidated tab resumed a protected request"
        finally:
            context.close()
    print(f"PASS device contexts at {viewport['width']}px: stale tab, reordered response, logout race and two same-account tabs")


if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for w, h in ((1280, 850), (390, 844)):
                exercise_device_context(browser, os.environ["AMC_BROWSER_TEST_URL"], {"width":w, "height":h})
        finally:
            browser.close()
