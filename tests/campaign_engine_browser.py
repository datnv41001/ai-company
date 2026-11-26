"""Capture the authenticated campaign workspace against the live, populated sandbox."""
import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from c3_browser_themes import capture_themes


def capture_campaign(origin, email, password, tenant, campaign, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sessions = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for width, height in ((1280, 850), (820, 1180), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
                try:
                    page.goto(origin + "/?workspace=" + tenant + "#/campaigns")
                    login = page.locator("#login-form")
                    login.get_by_label("Email").fill(email)
                    login.get_by_label("Mật khẩu").fill(password)
                    login.get_by_role("button").click()
                    engine = page.locator("#campaign-engine")
                    expect(engine).to_be_visible()
                    started = monotonic()
                    with page.expect_response(lambda r: r.url.endswith("/production")) as result:
                        engine.locator("#engine-select").select_option(campaign)
                    assert result.value.ok
                    production = result.value.json()
                    assert production["assets"] and production["runs"]
                    expect(page.locator("#engine-status")).to_have_text("Đã cập nhật dữ liệu sandbox.")
                    ready_ms = round((monotonic() - started) * 1000)
                    expect(engine).not_to_contain_text("undefined")
                    for asset in production["assets"]:
                        expect(engine.locator("summary").filter(has_text=asset["title"]).first).to_be_attached()
                    nav = engine.get_by_role("navigation", name="Các phần của chiến dịch")
                    for button in nav.get_by_role("button").all():
                        button.focus()
                        button.press("Enter")
                        expect(page.locator("#" + button.get_attribute("aria-controls"))).to_be_focused()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    engine.evaluate("e => e.scrollIntoView({block:'start'})")
                    capture_themes(page, directory / f"workspace-{width}.png")
                    funnel = engine.get_by_role("heading", name="Từ RFQ đến doanh thu sandbox")
                    funnel.evaluate("e => e.scrollIntoView({block:'start'})")
                    capture_themes(page, directory / f"funnel-{width}.png")
                    summary = engine.locator("summary").filter(has_text=production["assets"][0]["title"]).first
                    summary.focus()
                    summary.press("Enter")
                    expect(summary.locator("..")).to_have_attribute("open", "")
                    landing = next(asset for asset in production["assets"] if asset["kind"] == "landing")
                    inspect_suggestion(page, landing["deliverable_id"], directory / f"editor-{width}.png")
                    sessions.append({"viewport": [width, height], "chromium": browser.version, "campaign_id": campaign,
                                     "ready_ms": ready_ms, "run_ids": [r["id"] for r in production["runs"]],
                                     "themes": ["light", "dark"]})
                finally:
                    page.close()
        finally:
            browser.close()
    (directory / "sessions.json").write_text(json.dumps(sessions, indent=2) + "\n", encoding="utf-8")


def inspect_suggestion(page, doc_id, screenshot):
    page.evaluate("location.hash='/reviews'")
    panel = page.locator("#review-panel")
    panel.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
    panel.get_by_label("Bản làm việc").select_option(doc_id)
    studio = panel.locator(".marketing-studio")
    studio.locator("summary").first.press("Enter")
    studio.get_by_role("button", name="Nội dung trang", exact=True).click()
    field = studio.get_by_label("Giá trị cho người mua", exact=True)
    original = field.input_value()
    expect(studio.get_by_text("So sánh đề xuất theo hành trình mua", exact=True)).to_have_count(0)
    industry = studio.get_by_label("Ngành và loại sản phẩm áp dụng cho đề xuất")
    industry.select_option("other")
    expect(studio.get_by_text("Dùng quy trình chung cho tổ hợp này.", exact=False)).to_be_visible()
    expect(studio.get_by_text("So sánh đề xuất theo hành trình mua", exact=True)).to_have_count(0)
    industry.select_option("0")
    box = studio.locator("details").filter(has=page.get_by_text("So sánh đề xuất theo hành trình mua", exact=True)).last
    box.locator("summary").press("Enter")
    expect(box).to_contain_text(original)
    box.evaluate("e => e.scrollIntoView({block:'start'})")
    capture_themes(page, screenshot)
    box.get_by_role("button", name="Dùng và biên tập").click()
    assert field.input_value() != original
    field.fill(original + " Nội dung đang biên tập.")
    box.locator("summary").press("Enter")
    box.get_by_role("button", name="Bỏ qua đề xuất").click()
    expect(field).to_have_value(original + " Nội dung đang biên tập.")
