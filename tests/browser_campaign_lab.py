"""Capture the normal Campaign Center on localhost with a verified synthetic staff user."""
import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from agency_fixtures import account, create
from browser_c3_content_gate import client, local_api  # noqa: F401 -- file-backed SQLite for concurrent requests
from c3_browser_themes import capture_themes


def test_campaign_center_lab(client, tmp_path):  # noqa: F811
    owner = account(client, "CampaignLab")
    base = "/api/tenants/" + owner["tenant"]
    customer = create(client, base + "/clients", owner, {"name": "Vật liệu mẫu Hà Nội"})
    brand = create(client, base + "/brands", owner, {"name": "Vật liệu công trình", "client_id": customer["id"]})
    campaign = create(client, base + "/campaigns", owner, {
        "brand_id": brand["id"], "name": "Gạch ốp công trình · RFQ", "objective": "Đánh giá hành trình báo giá",
        "brief": "Chạy chiến dịch thử với dữ liệu tổng hợp tại Hà Nội.",
    })
    out = Path(os.getenv("AMC_LAB_EVIDENCE", tmp_path / "campaign-center"))
    out.mkdir(parents=True, exist_ok=True)
    observations = []
    with local_api() as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for width, height in ((1280, 850), (820, 1180), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
                try:
                    page.goto(origin + "/?workspace=" + owner["tenant"] + "#/campaigns")
                    login = page.locator("#login-form")
                    login.get_by_label("Email").fill(owner["email"])
                    login.get_by_label("Mật khẩu").fill(owner["password"])
                    login.get_by_role("button").click()
                    lab = page.locator("#campaign-lab")
                    expect(lab).to_be_visible()
                    expect(lab.locator("select")).to_have_value(campaign["id"])
                    button = lab.get_by_role("button", name="Chạy kịch bản B2B")
                    button.focus()
                    started = monotonic()
                    with page.expect_response(lambda r: r.url.endswith("/execution-lab/replay")) as received:
                        button.press("Enter")
                    assert received.value.ok, received.value.status
                    result = received.value.json()
                    expect(lab.get_by_role("status")).to_contain_text("Đã hoàn tất")
                    render_ms = round((monotonic() - started) * 1000)
                    expect(lab.locator("details")).to_have_count(len(result["assets"]))
                    expect(lab.get_by_text(result["recommendation"], exact=True)).to_be_attached()
                    amount = page.evaluate("v => new Intl.NumberFormat('vi-VN').format(v)", result["report"]["confirmed_revenue_vnd"])
                    expect(lab.locator(".metric").filter(has_text="Doanh thu xác nhận")).to_contain_text(amount)
                    summary = lab.locator("summary").first
                    summary.focus()
                    summary.press("Enter")
                    expect(lab.get_by_text(result["assets"][0]["body"], exact=True)).to_be_visible()
                    lab.evaluate("e => e.scrollIntoView({block:'start'})")
                    capture_themes(page, out / f"campaign-{width}.png")
                    lab.get_by_role("heading", name="Phễu bán hàng mô phỏng").evaluate("e => e.scrollIntoView({block:'start'})")
                    capture_themes(page, out / f"measurement-{width}.png")
                    observations.append({"viewport": [width, height], "themes": ["light", "dark"],
                                         "render_ms": render_ms, "browser": browser.version,
                                         "payload": result["contract_version"], "scenario_digest": result["scenario_digest"]})
                finally:
                    page.close()
        finally:
            browser.close()
    (out / "sessions.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
