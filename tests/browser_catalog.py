"""Use actual catalog forms on PostgreSQL, then check persisted money and authority via the scoped API."""

import json
import os
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_knowledge import BASE, OUT, authenticate, db_counts, login, post, select_scope, user


def enter_item(pane, kind, fields, approve=True):
    pane.get_by_label("Loại dữ liệu").select_option(kind)
    pane.get_by_role("button", name="Thêm mới", exact=True).click()
    for name, value in fields.items():
        control = pane.locator(f".catalog-form [name={name}]")
        if control.evaluate("e=>e.tagName") == "SELECT":
            if isinstance(value, tuple):
                match = control.locator("option").filter(has_text=value[0])
                expect(match).to_have_count(1)
                control.select_option(match.get_attribute("value"))
            else:
                control.select_option(value)
        else:
            control.fill(value)
    pane.get_by_role("button", name="Lưu bản nháp").click()
    expect(pane.get_by_role("status")).to_have_text("Đã lưu bản nháp.")
    if approve:
        pane.get_by_label("Lý do quyết định").fill("Đã so với bảng giá thử nghiệm")
        pane.get_by_role("button", name="Duyệt", exact=True).click()
        expect(pane.get_by_role("status")).to_have_text("Đã ghi quyết định vào lịch sử.")


def exercise(api, browser, width, height):
    owner = user(api, "catalog")
    tenant = owner["tenant_id"]
    prefix = "/api/tenants/" + tenant
    client = post(api, prefix + "/clients", owner, {"name": "Vật liệu Gạch Xanh"})["id"]
    brand = post(api, prefix + "/brands", owner, {"name": "Gạch sân vườn", "client_id": client})["id"]
    before = db_counts(tenant)
    page = browser.new_page(viewport={"width": width, "height": height}, locale="vi-VN")
    login(page, owner, tenant)
    select_scope(page, client, brand)
    page.locator("#catalog-drawer summary").click()
    pane = page.locator("#catalog-pane")

    enter_item(pane, "product", {"name": "Gạch nhám", "code": "TILE"})
    enter_item(pane, "market", {"name": "Bán lẻ Hà Nội", "code": "VN-HANOI", "locales": "vi-VN"})
    placement = {"product": ("Gạch nhám · TILE",), "market": ("Bán lẻ Hà Nội · VN-HANOI",), "locale": "vi-VN", "region": "VN-HN", "channel": "web"}
    enter_item(pane, "policy", {**placement, "warranty": "12 months", "buyer": "retail", "payment_type": "prepaid"})
    enter_item(
        pane,
        "offer",
        {
            **placement,
            "policy": ("12 months",),
            "currency": "USD",
            "amount": "12.34",
            "unit": "m²",
            "basis_quantity": "1",
            "moq": "2",
            "tier_min": "2",
            "tier_max": "20",
            "tax": "included",
            "condition_ids": ["prepaid"],
        },
    )
    expect(pane.locator(".catalog-detail dd").get_by_text("12.34", exact=True)).to_be_visible()
    pane.locator(".catalog-detail").evaluate("element => element.scrollIntoView({block:'start'})")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(OUT / f"catalog-{width}-offer.png"))
    catalog = prefix + f"/clients/{client}/brands/{brand}/catalog"
    cards = api.get(catalog + "/items", headers=owner["headers"], params={"kind": "offer"}).json()["items"]
    assert len(cards) == 1 and cards[0]["state"] == "approved"
    raw = api.get(catalog.replace("/catalog", "/knowledge") + "/revisions/" + cards[0]["id"], headers=owner["headers"]).json()["data"]["price"]
    assert raw["amount_minor"] == 1234 and raw["conditions"] == ["Prepaid"]
    enter_item(pane, "icp", {"name": "Thợ lát gạch", "description": "Đội thi công nhỏ", "basis": "hypothesis", "needs": "Giao đúng lịch"}, approve=False)
    expect(pane.get_by_text("Chưa liên kết chứng cứ.", exact=True)).to_be_visible()
    page.reload()
    authenticate(page, owner)
    select_scope(page, client, brand)
    page.locator("#catalog-drawer summary").click()
    pane.get_by_label("Loại dữ liệu").select_option("icp")
    pane.get_by_role("button", name="Thợ lát gạch", exact=True).click()
    expect(pane.get_by_text("Chưa liên kết chứng cứ.", exact=True)).to_be_visible()
    pane.locator(".catalog-detail").evaluate("element => element.scrollIntoView({block:'start'})")
    page.screenshot(path=str(OUT / f"catalog-{width}-audience.png"))
    after = db_counts(tenant)
    assert before == after and before["runs"] == before["ledger_entries"] == 0
    page.close()
    return {"viewport": [width, height], "amount_minor": raw["amount_minor"], "offer_state": cards[0]["state"], "before": before, "after": after}


if __name__ == "__main__":
    assert urlsplit(BASE).hostname in ("localhost", "127.0.0.1", "::1")
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=20, trust_env=False) as api, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        results = [exercise(api, browser, w, h) for w, h in ((1280, 850), (390, 844))]
        (OUT / "catalog-metrics.json").write_text(json.dumps({"chromium": browser.version, "runs": results}, indent=2), encoding="utf8")
        browser.close()
    print("PASS synthetic catalog and audience on both Chromium viewports; money and ledger verified")
