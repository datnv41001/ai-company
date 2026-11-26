"""Exercise the populated channel groups in a signed synthetic campaign."""

import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright
import pytest

from browser_c3_content_gate import client, local_api  # noqa: F401 -- file-backed sandbox HTTP fixture
from c3_browser_themes import capture_themes
from campaign_planner_fixtures import CASES
from test_channel_editions import lifecycle, sqlite_channel, workforce  # noqa: F401 -- real campaign scope


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_approved_channel_edition_browser(api, workforce, monkeypatch):  # noqa: F811
    doc, snap, plan, editor, other, _ = sqlite_channel(api, workforce, monkeypatch, CASES[0])
    owner, buyer, _, base, *_ = workforce
    out = Path(os.getenv("AMC_STUDIO_EVIDENCE", "knowledge-browser-evidence/marketing-studio")) / "channels"
    out.mkdir(parents=True, exist_ok=True)

    def capture(owner, buyer, did, snapshot, plan):
        sessions = []
        with local_api() as origin, sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
            try:
                for width, height in ((1280,850), (820,1180), (390,844)):
                    page = browser.new_page(viewport={"width":width,"height":height},reduced_motion="reduce")
                    try:
                        page.goto(origin + "/?workspace=" + owner["tenant"] + "#/reviews")
                        login = page.locator("#login-form")
                        login.get_by_label("Email").fill(owner["email"])
                        login.get_by_label("Mật khẩu").fill(owner["password"])
                        login.get_by_role("button").click()
                        expect(page.locator("#workspace")).to_be_visible()
                        page.evaluate("location.hash='/reviews'")
                        panel = page.locator("#review-panel")
                        panel.get_by_text("Soạn và bàn giao cho khách",exact=True).click()
                        panel.get_by_label("Bản làm việc").select_option(did)
                        studio = panel.locator(".marketing-studio")
                        started = monotonic()
                        studio.locator("summary").first.press("Enter")
                        nav = studio.locator(".studio-nav")
                        for name,field in (("Bài mạng xã hội","Trụ cột nội dung"),("Đề xuất quảng cáo","Phân bổ đề xuất"),("Lịch nội dung","Mốc đề xuất")):
                            nav.get_by_role("button", name=name,exact=True).press("Enter")
                            expect(studio.get_by_label(field,exact=True)).not_to_have_value("")
                        nav.get_by_role("button",name="Brief thiết kế",exact=True).press("Enter")
                        expect(studio.get_by_label("Nguồn tài sản",exact=True)).to_have_value(
                            "Bản giao chỉ gồm chỉ dẫn sản xuất. Chưa có tệp hình ảnh hoặc video được cấp phép.")
                        expect(studio).to_contain_text("Kế hoạch v1")
                        ready_ms = round((monotonic()-started)*1000)
                        nav.evaluate("e=>e.scrollIntoView({block:'start'})")
                        capture_themes(page,out/f"creative-{width}.png")
                        nav.get_by_role("button",name="Đề xuất quảng cáo",exact=True).click()
                        nav.evaluate("e=>e.scrollIntoView({block:'start'})")
                        capture_themes(page,out/f"ad-{width}.png")
                        sessions.append({"width":width,"height":height,"themes":["light","dark"],"browser":browser.version,
                                         "four_group_keyboard_ms":ready_ms,"scroll_width":page.evaluate("document.documentElement.scrollWidth")})
                    finally:
                        page.close()
            finally:
                browser.close()
        (out/"sessions.json").write_text(json.dumps({"source":"Signed synthetic HTTP/SQLite edition. No new inference.",
            "plan_digest":plan["digest"],"snapshot_digest":snapshot["digest"],"sessions":sessions}, indent=2)+"\n",encoding="utf8")

    lifecycle(api, base, owner, buyer, other, doc, snap, plan, editor, capture)
