"""Recover a real synthetic price card as two separate signed-in users across three viewports."""

import json
import os
from pathlib import Path
import re

import pytest
from playwright.sync_api import expect, sync_playwright

from browser_c3_content_gate import client as live_client, local_api
from c3_browser_themes import capture_themes
from c3_task_fixtures import internal_workspace
from evaluation.c3.recovery_fixture import attestation, start_recovery
from screen_navigation import screen, select_workspace
from test_c3_clarification import CASES

client = live_client


def open_brand(page, url, account, tenant, client_id, brand):
    page.goto(url + "/?workspace=" + tenant)
    form = page.locator("#login-form")
    form.get_by_label("Email").fill(account["email"])
    form.get_by_label("Mật khẩu").fill(account["password"])
    form.get_by_role("button").click()
    screen(page, "knowledge")
    if page.locator("#workspace-select").input_value() != tenant:
        select_workspace(page, tenant)
        screen(page, "knowledge")
    page.locator("#knowledge-client").select_option(client_id)
    page.locator("#knowledge-brand").select_option(brand)


def open_brief(page):
    page.locator("[data-view=briefs]").click()
    page.locator("[data-brief]").first.click()
    panel = page.locator("#knowledge-marketing-workflow")
    panel.get_by_text("Chuẩn bị Marketing từ brief này", exact=True).click()
    return panel


def exercise(api, browser, origin, out, width, height):
    owner, base, customer, brand, campaign = internal_workspace(api)
    case = next(c for c in CASES if c["id"] == "service-01")
    setup, _ = start_recovery(api, case, owner, base, customer, brand, campaign)
    selected = setup["params"]
    viewport = {"width": width, "height": height}
    author = browser.new_page(viewport=viewport)
    approver = browser.new_page(viewport=viewport)
    try:
        open_brand(author, origin, owner, owner["tenant"], customer, brand)
        panel = open_brief(author)
        form = panel.locator("form")
        for field in ("brief", "workflow", "market", "kpi", "guidelines"):
            value = selected["target"]["brief_id"] if field == "brief" else selected[field]
            form.locator(f"select[name={field}]").select_option(value)
        for rid in selected["claims"]:
            form.locator(f"input[name=claim][value='{rid}']").check()
        for field in ("currency", "quantity", "locale", "region", "channel"):
            form.locator(f"input[name={field}]").fill(str(selected[field]))
        with author.expect_response(lambda r: r.url.endswith("/readiness")) as blocked:
            form.get_by_role("button", name="Kiểm tra mức sẵn sàng").click()
        (issue,) = blocked.value.json()["clarifications"]
        answer = attestation(case, issue)
        inputs = panel.get_by_role("region", name="Làm rõ dữ liệu thương mại")
        expect(inputs.get_by_label("Đơn vị ghi trong chứng từ")).to_have_value("")
        inputs.get_by_label("Đơn vị ghi trong chứng từ").select_option(answer["unit"])
        for caption, key in [("Tên chứng từ xác nhận", "document"), ("Vị trí trong chứng từ", "locator"), ("Trích đoạn xác nhận đơn vị", "excerpt")]:
            inputs.get_by_label(caption).fill(answer[key])
        inputs.get_by_role("checkbox").check()
        inputs.get_by_role("group").scroll_into_view_if_needed()
        capture_themes(author, out / f"clarify-{width}.png")
        with author.expect_response(lambda r: r.url.endswith("/clarifications/propose")) as proposed:
            inputs.get_by_role("button", name="Lưu đề xuất điều chỉnh").click()
        assert proposed.value.status == 201, proposed.value.text()
        expect(inputs).to_contain_text("Người duyệt độc lập")

        open_brand(approver, origin, setup["commercial_reviewer"], owner["tenant"], customer, brand)
        approver.locator("[data-view=claims]").click()
        desk = approver.locator("#knowledge-claim-desk")
        desk.get_by_role("button", name="Duyệt đơn vị bán").click()
        expect(desk.get_by_text(answer["excerpt"], exact=False).first).to_be_visible()
        reason = desk.get_by_label("Lý do duyệt đơn vị bán")
        reason.fill("Đã đối chiếu bảng giá mẫu và đơn vị tính theo lượt.")
        reason.scroll_into_view_if_needed()
        capture_themes(approver, out / f"approve-{width}.png")
        with approver.expect_response(lambda r: r.url.endswith("/clarifications/approve")) as approved:
            desk.get_by_role("button", name="Xác nhận giá và đơn vị").click()
        assert approved.value.ok, approved.value.text()
        replacement = approved.value.json()["claim"]

        # A fresh application session retrieves the author's saved selection from the server.
        author.close()
        author = browser.new_page(viewport=viewport)
        open_brand(author, origin, owner, owner["tenant"], customer, brand)
        panel = open_brief(author)
        panel.get_by_role("button", name="Tiếp tục sau khi sửa đơn vị bán").click()
        with author.expect_response(lambda r: r.url.endswith("/readiness")) as ready:
            panel.get_by_role("button", name=re.compile("dùng giá đã duyệt")).click()
        assert ready.value.json()["status"] == "ready"
        selection = ready.value.request.post_data_json
        expected_claims = [replacement if value == issue["claim"] else value for value in selected["claims"]]
        # The manifest assigns evidence handles in sorted revision-ID order.
        assert sorted(selection["claims"]) == sorted(expected_claims)
        snap = api.post(setup["marketing"] + "/manifests", headers=owner["headers"], json=selection)
        assert snap.status_code in (200, 201), snap.text
        expect(panel.locator(f"input[value='{replacement}']")).to_be_checked()
        panel.get_by_role("button", name="Tiếp tục sau khi sửa đơn vị bán").scroll_into_view_if_needed()
        capture_themes(author, out / f"resumed-{width}.png")
        return {"viewport": viewport, "machine_state": "ready", "attested_unit": answer["unit"], "manifest": snap.json()["digest"]}
    finally:
        author.close()
        approver.close()


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_clarification_browser(api):
    out = Path(os.environ.get("AMC_KNOWLEDGE_EVIDENCE", "knowledge-browser-evidence")) / "unit-clarification"
    out.mkdir(parents=True, exist_ok=True)
    with local_api() as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            report = {
                "browser": browser.version,
                "synthetic": True,
                "cases": [exercise(api, browser, origin, out, w, h) for w, h in ((1280, 850), (820, 1180), (390, 844))],
            }
            (out / "acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        finally:
            browser.close()
