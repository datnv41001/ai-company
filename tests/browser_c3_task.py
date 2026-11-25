"""Submit an internal Marketing goal, select all three authority layers and queue through Chromium."""

import json
import os
from pathlib import Path
import sys

import httpx
from c3_browser_themes import capture_themes
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_knowledge import BASE, PROJECT, login, select_scope  # noqa: E402
from c3_task_fixtures import INTENT, LANDING, fixture  # noqa: E402

OUT = Path(os.getenv("AMC_KNOWLEDGE_EVIDENCE", "knowledge-browser-evidence"))


def exercise(api, browser, width, height):
    owner, base, client, brand, _, _, _, state, guide = fixture(api, PROJECT)
    api.put(base + "/operations/budget", headers=owner["headers"], json={"ceiling": 0, "capacity": 1, "enabled": True}).raise_for_status()
    page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
    try:
        login(page, owner, owner["tenant"])
        select_scope(page, client, brand)
        page.locator("[data-view=briefs]").click()
        page.locator("[data-brief]").first.click()
        panel = page.locator("#knowledge-marketing-workflow")
        panel.get_by_text("Chuẩn bị Marketing từ brief này", exact=True).click()
        entry = panel.locator("[data-task-entry]")
        entry.locator("summary").click()
        for key in ("purpose", "product", "audience", "channel", "region", "locale", "requirements", "exclusions", "acceptance_criteria"):
            value = INTENT[key]
            entry.locator(f"[name={key}]").fill("\n".join(value) if isinstance(value, list) else value)
        entry.locator("summary").evaluate("el=>el.scrollIntoView({block:'start'})")
        expect(entry.locator("[name=product]")).to_have_value(INTENT["product"])
        capture_themes(page, OUT / f"c3-task-author-{width}.png")
        with page.expect_response(lambda r: r.url.endswith("/workforce/internal-tasks")) as submission:
            entry.get_by_role("button", name="Xác nhận yêu cầu công việc").click()
        assert submission.value.status == 201, submission.value.text()
        task = submission.value.json()
        assert task["origin"] == "internal"
        entry.locator("summary").click()
        form = panel.locator("form")
        expect(form.locator("[name=brief]")).to_have_value(task["id"])
        expect(form.locator("[name=workflow]")).to_have_value(LANDING)
        for key in ("market", "kpi"):
            form.locator(f"select[name={key}]").select_option(state["params"][key])
        form.locator("input[name=claim]").first.check()
        check = form.get_by_role("button", name="Kiểm tra mức sẵn sàng")
        check.click()
        status = panel.locator(":scope > details > p[role=status]")
        expect(status).to_contain_text("hướng dẫn thương hiệu")
        queue = form.get_by_role("button", name="Xếp việc cho AI")
        expect(queue).to_be_disabled()
        form.locator("[name=guidelines]").select_option(guide["id"])
        check.click()
        form.get_by_role("button", name="Bật quy trình cho chiến dịch").click()
        expect(queue).to_be_enabled()
        with (
            page.expect_response(lambda r: r.url.endswith("/manifests")) as manifest,
            page.expect_response(lambda r: r.url.endswith("/" + task["id"] + "/run")) as result,
        ):
            queue.click()
        assert result.value.status == 200, result.value.text()
        snapshot = manifest.value.json()
        assert snapshot["projection"]["task_intent"] == INTENT
        assert snapshot["projection"]["brand_guidelines"]["digest"] == guide["digest"]
        run = result.value.json()
        expect(status).to_contain_text(run["id"])
        status.evaluate("el=>el.scrollIntoView({block:'center'})")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        assert "PRIVATE_SYNTHETIC" not in panel.inner_text()
        capture_themes(page, OUT / f"c3-task-queued-{width}.png")
        return {
            "viewport": [width, height],
            "mode": "inhouse",
            "origin": task["origin"],
            "workflow": LANDING,
            "state": run["state"],
            "manifest_digest": snapshot["digest"],
            "guide_digest": guide["digest"],
        }
    finally:
        page.close()


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as api, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            report = {"browser": browser.version, "cases": [exercise(api, browser, w, h) for w, h in ((1280, 850), (820, 1180), (390, 844))]}
            (OUT / "c3-task-browser.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
        finally:
            browser.close()


if __name__ == "__main__":
    run()
