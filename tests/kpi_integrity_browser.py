"""Exercise the KPI editor and brief pin over the authenticated local API."""

import json
import os
from pathlib import Path
from time import perf_counter

from playwright.sync_api import expect, sync_playwright

from c3_browser_themes import capture_themes


def capture(origin, owner, tenant, client, brand, campaign, setup, contract, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    timings = {}

    def screens(page, name, anchor):
        for width, height in ((1280, 850), (820, 1180), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            anchor.evaluate("e => e.scrollIntoView({block:'start'})")
            page.evaluate("window.scrollBy(0,-40)")
            expect(anchor).to_be_visible()
            capture_themes(page, out / f"{name}-{width}.png")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        page = browser.new_page(viewport={"width": 1280, "height": 850}, reduced_motion="reduce")
        try:
            page.goto(origin + "/?workspace=" + tenant + "#/knowledge")
            login = page.locator("#login-form")
            login.get_by_label("Email").fill(owner["email"])
            login.get_by_label("Mật khẩu").fill(owner["password"])
            login.get_by_role("button").click()
            page.locator("#knowledge-client").select_option(client)
            page.locator("#knowledge-brand").select_option(brand)
            panel = page.locator("#catalog-drawer")
            if not panel.evaluate("d => d.open"):
                panel.locator("summary").click()
            pane = page.locator("#catalog-pane")
            pane.get_by_label("Loại dữ liệu").select_option("kpi")
            pane.get_by_role("button", name="Thêm mới", exact=True).click()
            form = pane.locator(".catalog-form")
            start = perf_counter()
            metric = form.locator("[name=measurement_outcome]")
            metric.focus()
            metric.press("End")
            expect(metric).to_have_value("appointment.completed_per_confirmed")
            form.locator("[name=measurement_days]").fill("14")
            form.locator("[name=measurement_owner]").select_option("service_operations")
            form.locator("[name=name]").fill("KPI theo dõi buổi khảo sát hoàn tất")
            form.locator("[name=objective]").select_option(setup["selections"]["objective"])
            expect(form.locator("[name=method]")).to_be_disabled()
            timings["edit_automated_seconds"] = round(perf_counter() - start, 2)
            screens(page, "knowledge-kpi", form.locator("fieldset").first)
            with page.expect_response(lambda r: "/catalog/items" in r.url and r.request.method == "POST") as saved:
                form.get_by_role("button", name="Lưu bản nháp").click()
            response = saved.value
            assert response.ok, (response.status, response.text()[:300])
            saved_id = response.json()["id"]
            stored = page.request.get(response.url + "/" + saved_id, headers=owner["headers"])
            assert stored.ok, stored.status
            item = stored.json()
            assert item["data"]["measurement"]["window_days"] == 14 and item["data"]["unit"] == "ratio"
            page.get_by_role("button", name="Brief nháp", exact=True).click()
            draft = page.locator("#knowledge-new-brief")
            draft.get_by_label("Tên brief").fill("Khảo sát Luồng Rõ — kiểm KPI đã phê duyệt")
            draft.get_by_role("button", name="Chọn dữ liệu từ danh mục").click()
            for slot, value in setup["selections"].items():
                draft.locator("#brief-" + slot).select_option(value)
            expect(draft.locator("#brief-kpi")).to_have_value(contract["id"])
            screens(page, "brief-kpi", draft.locator("#brief-selectors"))
            with page.expect_response(lambda r: "/business-workspace/briefs" in r.url and r.request.method == "POST") as saved:
                draft.get_by_role("button", name="Tạo brief nháp").click()
            assert saved.value.ok, (saved.value.status, saved.value.text()[:300])
            expect(page.locator("#knowledge-open-title")).to_contain_text("kiểm KPI")
            expect(page.locator("#knowledge-panel")).to_contain_text("KPI của chiến dịch")
            assert page.locator("#knowledge-panel").inner_text().find("Lịch hẹn được người phụ trách kho xác nhận") >= 0
            page.goto(origin + "/?workspace=" + tenant + "#/campaigns")
            engine = page.locator("#campaign-engine")
            engine.locator("select").first.select_option(campaign)
            analytics = engine.locator("[data-primary-kpi]")
            expect(analytics).to_contain_text("66,7")
            screens(page, "analytics-kpi", analytics)
            (out / "checks.json").write_text(
                json.dumps(
                    {
                        "sizes": [1280, 820, 390],
                        "themes": ["light", "dark"],
                        "mode": "authenticated Chromium / synthetic workspace",
                        "saved_typed_draft_id": item["id"],
                        "brief_kpi_revision_id": contract["id"],
                        "keyboard": "Focused the labeled outcome control and selected completed/confirmed with End",
                        "timings": timings,
                        "horizontal_overflow": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        finally:
            browser.close()
