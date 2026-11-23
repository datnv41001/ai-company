"""Browser acceptance against a disposable local server. Run outside pytest."""

import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright


def exercise():
    origin = os.environ["AMC_BROWSER_TEST_URL"]
    assert urlsplit(origin).hostname in ("localhost", "127.0.0.1")
    with httpx.Client(base_url=origin, timeout=15, trust_env=False) as api, sync_playwright() as pw:

        def post(path, body, token=None):
            headers = {"Authorization": "Bearer " + token} if token else {}
            res = api.post(path, json=body, headers=headers)
            assert res.is_success, (path, res.status_code)
            return res.json()

        def user(label):
            email, password = f"{label}-{uuid4().hex}@example.com", uuid4().hex
            reg = post("/api/auth/register", dict(email=email, password=password, organization_name=label, mode="agency"))
            return reg["access_token"], reg["tenant_id"], reg["user_id"], email, password

        token, tenant, _, _, _ = user("Agency")
        edit, _, _, editor_email, _ = user("Editor")
        _, _, uid, email, password = user("Reader")
        base = "/api/tenants/" + tenant
        client = post(base + "/clients", {"name": "UI Client"}, token)
        brand = post(base + "/brands", {"client_id": client["id"], "name": "UI Brand"}, token)
        camp = post(
            base + "/campaigns", {"brand_id": brand["id"], "name": "UI campaign", "brief": "Synthetic brief for QA", "objective": "Review content"}, token
        )
        post(base + "/members", dict(email=editor_email, role="editor"), token)
        post(base + "/members", dict(email=email, role="client_viewer", client_id=client["id"]), token)
        assert (
            api.put(
                base + f"/members/{uid}/review-rights", headers={"Authorization": "Bearer " + token}, json={"can_comment": True, "can_decide": True}
            ).status_code
            == 200
        )

        def share(title, seconds=1800):
            draft = post(
                base + "/deliverables",
                dict(campaign_id=camp["id"], title=title, content={"client_preview": "Exact customer preview", "secret_ref": "internal-only-canary"}),
                edit,
            )
            path = base + "/deliverables/" + draft["id"]
            post(path + "/submit", {}, edit)
            post(path + "/review", {"decision": "approved", "note": "internal QA"}, token)
            return post(path + "/share", {"expires_at": (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()}, token)

        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for width, height in [(1280, 850), (390, 844)]:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(origin + "/?workspace=" + tenant)
                form = page.locator("#login-form")
                form.locator('[name="email"]').fill(email)
                form.locator('[name="password"]').fill(password)
                form.locator("button").click()
                pane = page.locator("#review-panel")
                expect(pane.get_by_role("heading", name="Bàn giao và duyệt nội dung")).to_be_visible()
                if width == 1280:
                    expect(pane.get_by_text("Chưa có phiên bản nào được chia sẻ.")).to_be_visible()
                title = f"Brief {width}"
                share(title)
                page.locator("#refresh").click()
                pane.get_by_role("button", name=title + " · v1 · Chờ khách duyệt").click()
                expect(pane.locator("pre")).to_have_text("Exact customer preview")
                assert "internal-only-canary" not in pane.inner_text()
                pane.get_by_label("Ý kiến của bạn").fill("Bản này đã đúng brief")
                pane.get_by_role("button", name="Gửi bình luận").click()
                expect(pane.get_by_text("Bản này đã đúng brief", exact=False)).to_be_visible()
                pane.get_by_role("button", name="Duyệt phiên bản này").click()
                expect(pane.get_by_role("button", name=title + " · v1 · Khách đã duyệt")).to_be_visible()
                # Element identifiers help diagnose font-dependent wrapping on Linux and Windows.
                overflow = page.evaluate("""() => Array.from(document.querySelectorAll('body *'))
                    .filter(el => el.getBoundingClientRect().right > innerWidth + 0.5)
                    .map(el => [el.tagName, el.id, el.className])""")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), overflow
                page.route("**/reviews", lambda route: route.fulfill(status=503, body="unavailable"))
                page.locator("#refresh").click()
                expect(pane.get_by_text("Không tải được danh sách bản bàn giao.")).to_be_visible()
                page.unroute("**/reviews")
                pane.get_by_role("button", name="Thử lại").click()
                expect(pane.get_by_role("button", name=title + " · v1 · Khách đã duyệt")).to_be_visible()
                expired_title = f"Deadline {width}"
                share(expired_title, 2)
                time.sleep(2.1)
                page.locator("#refresh").click()
                pane.get_by_role("button", name=expired_title + " · v1 · Đã hết hạn").click()
                expect(pane.locator("pre")).to_be_visible()
                expect(pane.get_by_role("button", name="Duyệt phiên bản này")).to_have_count(0)
                page.goto(origin + "/?workspace=" + tenant + "&review=missing")
                form.locator('[name="email"]').fill(email)
                form.locator('[name="password"]').fill(password)
                form.locator("button").click()
                expect(pane.get_by_text("Không mở được bản bàn giao.", exact=False)).to_be_visible()
                print(f"PASS browser {width}x{height}: exact preview, comment, approval, retry, expiry, missing link")
                page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    exercise()
