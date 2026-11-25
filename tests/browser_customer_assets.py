"""Capture the signed, populated customer edition under staff and scoped customer sessions."""

import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright
import pytest

from app import c3_assets
from browser_c3_content_gate import client, local_api  # noqa: F401 -- disposable HTTP database
from c3_browser_themes import capture_themes
from test_customer_assets import exercise_share, workforce  # noqa: F401 -- normal agency fixture


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_signed_rfq_strategy_in_browser(api, workforce, monkeypatch):  # noqa: F811
    out = Path(os.getenv("AMC_STUDIO_EVIDENCE", "knowledge-browser-evidence/marketing-studio")) / "signed-edition"
    out.mkdir(parents=True, exist_ok=True)

    def inspect(owner, customer, doc_id, snapshot):
        sessions = []
        with local_api() as origin, sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
            try:
                for actor, role in ((owner, "studio"), (customer, "portal")):
                    for width, height in ((1280, 850), (820, 1180), (390, 844)):
                        page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
                        try:
                            url = origin + "/?workspace=" + owner["tenant"]
                            page.goto(url + ("&review=" + snapshot["id"] if role == "portal" else "#/reviews"))
                            login = page.locator("#login-form")
                            login.get_by_label("Email").fill(actor["email"])
                            login.get_by_label("Mật khẩu").fill(actor["password"])
                            login.get_by_role("button").click()
                            expect(page.locator("#workspace")).to_be_visible()
                            started = monotonic()
                            if role == "portal":
                                page.evaluate("location.hash='/reviews'")
                                page.get_by_role("button", name=snapshot["title"] + " · v1", exact=False).click()
                                content = page.locator(".review-preview")
                                expect(content).to_have_text(snapshot["preview"])
                                assert not page.locator(".marketing-studio").count()
                                content.evaluate("e=>e.scrollIntoView({block:'start'})")
                            else:
                                page.evaluate("location.hash='/reviews'")
                                panel = page.locator("#review-panel")
                                panel.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
                                panel.get_by_label("Bản làm việc").select_option(doc_id)
                                studio = panel.locator(".marketing-studio")
                                studio.locator("summary").first.press("Enter")
                                studio.get_by_role("button", name="Chiến lược giao khách", exact=True).click()
                                expect(studio.get_by_label("Lựa chọn chiến lược", exact=True)).to_have_value(
                                    "Đề xuất giúp Xưởng nội thất đối chiếu quy cách của Bộ mẫu vải trước khi gửi yêu cầu báo giá.")
                                expect(studio.get_by_text("5/5 phần đã được duyệt", exact=False)).to_be_visible()
                                studio.get_by_text("Bản xem trước dành cho khách", exact=True).press("Enter")
                                expect(studio.locator(".studio-edition-preview")).to_contain_text("Yêu cầu báo giá")
                                studio.locator(".studio-nav").evaluate("e=>e.scrollIntoView({block:'start'})")
                            ready_ms = round((monotonic() - started) * 1000)
                            capture_themes(page, out / f"{role}-{width}.png")
                            sessions.append({"role": role, "viewport": [width,height], "themes": ["light","dark"],
                                             "browser": browser.version, "observed_ready_ms": ready_ms,
                                             "scroll_width": page.evaluate("document.documentElement.scrollWidth")})
                        finally:
                            page.close()
            finally:
                browser.close()
        (out / "sessions.json").write_text(json.dumps({"scope": "Synthetic signed SQLite RFQ edition",
            "digest": snapshot["digest"], "snapshot_version": snapshot["version"], "sessions": sessions}, indent=2) + "\n", encoding="utf8")

    exercise_share(api, workforce, monkeypatch, c3_assets.RESEARCH, inspect)
