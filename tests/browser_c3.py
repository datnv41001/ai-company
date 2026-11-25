"""A real operator prepares, checks, activates and queues a knowledge-backed brief in Chromium."""

import json
import os
from pathlib import Path
import sys

import httpx
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_knowledge import BASE, login, select_scope, user  # noqa: E402
from c3_fixtures import prepared  # noqa: E402
from agency_fixtures import create  # noqa: E402
from identity_fixtures import invite_member  # noqa: E402
from test_workforce import DATA  # noqa: E402

OUT = Path(os.getenv("AMC_KNOWLEDGE_EVIDENCE", "knowledge-browser-evidence"))


def exercise(api, browser, width, height):
    owner, client_user = (user(api, prefix) for prefix in ("c3-owner", "c3-client"))
    for actor in (owner, client_user):
        actor.update(id=actor["user_id"], tenant=actor["tenant_id"])
    base = "/api/tenants/" + owner["tenant"]
    client = create(api, base + "/clients", owner, {"name": "Xưởng gốm An Nhiên"})["id"]
    brand = create(api, base + "/brands", owner, {"client_id": client, "name": "Gốm An Nhiên"})["id"]
    campaign = create(
        api,
        base + "/campaigns",
        owner,
        {"brand_id": brand, "name": "Bộ mẫu mùa thu", "brief": "Chuẩn bị trang giới thiệu bộ mẫu", "objective": "Nhận đăng ký tư vấn"},
    )["id"]
    invite_member(api, base, owner["headers"], client_user["headers"], email=client_user["email"], role="client_viewer", client_id=client)
    bid = create(api, base + "/workforce/briefs", owner, {"campaign_id": campaign, "recipient_id": client_user["id"], "title": "Brief bộ mẫu đã gửi"})["id"]
    api.put(base + "/workforce/briefs/" + bid + "/submission", headers=client_user["headers"], json=DATA).raise_for_status()
    api.put(base + "/operations/budget", headers=owner["headers"], json={"ceiling": 0, "capacity": 1, "enabled": True}).raise_for_status()
    state = prepared(api, owner, base, client, brand, campaign, bid)
    page = browser.new_page(viewport={"width": width, "height": height})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        login(page, owner, owner["tenant"])
        select_scope(page, client, brand)
        page.locator("[data-view=briefs]").click()
        page.locator("[data-brief]").first.click()
        panel = page.locator("#knowledge-marketing-workflow")
        panel.locator("summary").click()
        queue = panel.get_by_role("button", name="Xếp việc cho AI")
        expect(queue).to_be_disabled()
        panel.get_by_role("button", name="Kiểm tra mức sẵn sàng").click()
        expect(panel.get_by_role("status")).to_contain_text("Chọn brief")
        for name, key in (("brief", bid), ("market", state["params"]["market"]), ("kpi", state["params"]["kpi"])):
            panel.locator(f"select[name={name}]").select_option(key)
        panel.locator("input[name=claim]").first.check()
        panel.locator("[name=workflow]").select_option(state["params"]["workflow"])
        check = panel.get_by_role("button", name="Kiểm tra mức sẵn sàng")
        check.click()
        activate = panel.get_by_role("button", name="Bật quy trình cho chiến dịch")
        expect(activate).to_be_visible()
        activate.click()
        expect(queue).to_be_enabled()
        OUT.mkdir(parents=True, exist_ok=True)
        queue.scroll_into_view_if_needed()
        page.screenshot(path=OUT / f"c3-ready-{width}.png", animations="disabled")
        with page.expect_response(lambda r: r.url.endswith("/briefs/" + bid + "/run")) as queued:
            queue.click()
        assert queued.value.status == 200, queued.value.text()
        rid = queued.value.json()["id"]
        expect(panel.get_by_role("status")).to_contain_text(rid)
        expect(queue).to_be_disabled()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=OUT / f"c3-queued-{width}.png", animations="disabled")
        assert "private locator" not in panel.inner_text()
        source = panel.get_by_text("Đối chiếu mã nguồn với tài liệu gốc", exact=True)
        source.click()
        expect(panel.locator("li").filter(has_text="private locator")).to_contain_text("F1")
        source.click()
        expect(panel.locator("li").filter(has_text="private locator")).to_have_count(0)
        return {"width": width, "height": height, "run": rid, "workflow": state["params"]["workflow"], "state": queued.value.json()["state"]}
    except Exception:
        print("Browser diagnostics", errors, page.locator("#notice").inner_text(), flush=True)
        raise
    finally:
        page.close()


if __name__ == "__main__":
    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as api, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            report = {"browser": browser.version, "cases": [exercise(api, browser, w, h) for w, h in ((1280, 850), (390, 844))]}
            (OUT / "c3-browser.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        finally:
            browser.close()
