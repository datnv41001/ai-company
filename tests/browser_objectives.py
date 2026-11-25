"""Author all three objective scopes through the real catalog on native desktop/mobile Chromium."""

import json
import os
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_catalog import enter_item
from browser_knowledge import BASE, OUT, db_counts, login, post, select_scope, snapshot, user


def exercise(api, browser, width, height):
    owner = user(api, "objectives")
    tenant = owner["tenant_id"]
    base = "/api/tenants/" + tenant
    client = post(api, base + "/clients", owner, {"name": "Công ty gạch"})["id"]
    first, second = [post(api, base + "/brands", owner, {"name": name, "client_id": client})["id"] for name in ("Gạch sân vườn", "Gạch trong nhà")]
    campaign = post(
        api, base + "/campaigns", owner, {"name": "Mùa xây nhà", "brand_id": first, "brief": "Nhóm khách xây nhà", "objective": "Nhận yêu cầu báo giá"}
    )
    before = db_counts(tenant)
    page = browser.new_page(viewport={"width": width, "height": height}, locale="vi-VN")
    login(page, owner, tenant)
    pane = page.locator("#catalog-pane")

    def open_brand(brand):
        select_scope(page, client, brand)
        drawer = page.locator("#catalog-drawer")
        if drawer.get_attribute("open") is None:
            drawer.locator("summary").click()
        expect(pane.get_by_label("Loại dữ liệu")).to_be_visible()

    open_brand(first)
    enter_item(pane, "company_objective", {"name": "Tăng yêu cầu báo giá", "owner": "Trưởng kinh doanh"})
    enter_item(pane, "objective", {"name": "Báo giá gạch vườn", "level": "brand", "company_parent": ("Tăng yêu cầu báo giá",), "owner": "Nhóm sân vườn"})
    enter_item(
        pane,
        "objective",
        {"name": "Báo giá tháng ba", "level": "campaign", "parent": ("Báo giá gạch vườn",), "campaign_id": ("Mùa xây nhà",), "owner": "Nhóm chiến dịch"},
    )
    expect(pane.locator("dd").get_by_text("Mùa xây nhà", exact=True)).to_be_visible()
    snapshot(page, "campaign-objective", width, ".catalog-detail")
    open_brand(second)
    enter_item(pane, "objective", {"name": "Báo giá nội thất", "level": "brand", "company_parent": ("Tăng yêu cầu báo giá",), "owner": "Nhóm nội thất"})
    expect(pane.locator("dd").get_by_text("Tăng yêu cầu báo giá", exact=True)).to_be_visible()
    snapshot(page, "shared-company-objective", width, ".catalog-detail")

    def cards(brand):
        return api.get(f"{base}/clients/{client}/brands/{brand}/catalog/items", headers=owner["headers"], params={"kind": "objective"}).json()["items"]

    a, b = cards(first), cards(second)
    assert len(a) == 2 and len(b) == 1 and all(r["state"] == "approved" for r in a + b)
    assert campaign["brand_id"] == first and before == db_counts(tenant)
    page.close()
    return {"width": width, "company_targets": 1, "first_brand_targets": len(a), "second_brand_targets": len(b), "counters": before}


if __name__ == "__main__":
    assert urlsplit(BASE).hostname in ("localhost", "127.0.0.1", "::1")
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=20, trust_env=False) as api, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        result = [exercise(api, browser, w, h) for w, h in ((1280, 850), (390, 844))]
        (OUT / "objective-metrics.json").write_text(json.dumps({"chromium": browser.version, "viewports": result}, indent=2), encoding="utf8")
        browser.close()
    print("PASS shared company objectives, two brands and campaign on both Chromium viewports")
