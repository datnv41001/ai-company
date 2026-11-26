"""Authenticated run detail from a real synthetic PostgreSQL Content → Storyboard execution."""

import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from app import storyboard_runtime as runtime
from browser_c3_content_gate import local_api
from browser_visual_checks import contrast
from c3_browser_themes import capture_themes
from test_registry import PG, pool as registry_pool
from test_storyboard_brief import TAG, case_input
from test_video_storyboard import start, work

pool = registry_pool


@PG
def test_staff_read_checked_content_handoff(pool, tmp_path):
    case, intent = case_input(TAG, prepare=True)
    base, owner, buyer, _, snap, queued = start(pool, case, release=runtime.RELEASE, intent_overrides=intent)
    for skill in ("director", "content", "storyboard"):
        work(pool, queued["id"], skill, [])
    url = f"{base}/workforce/runs/{queued['id']}"
    report = pool.api.get(url, headers=owner["headers"]).json()
    assert pool.api.get(url, headers=buyer["headers"]).status_code == 404
    output = report["checkpoints"][1]["output"]
    plan = json.loads(output["sections"]["content_handoff"])
    assert plan["manifest"]["digest"] == snap["digest"]
    folder = Path(os.getenv("AMC_WORKFORCE_SCREENS") or tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    sessions = []
    with local_api() as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for width, height in ((1280, 850), (820, 1180), (390, 844)):
                page = browser.new_page(viewport={"width": width, "height": height}, color_scheme="light", reduced_motion="reduce")
                try:
                    page.goto(origin + "/?workspace=" + owner["tenant"] + "#/workforce")
                    login = page.locator("#login-form")
                    login.get_by_label("Email").fill(owner["email"])
                    login.get_by_label("Mật khẩu").fill(owner["password"])
                    login.get_by_role("button").press("Enter")
                    expect(page.locator("#workspace")).to_be_visible()
                    page.evaluate("location.hash='/workforce'")
                    panel = page.locator("#workforce-panel")
                    header = panel.get_by_role("heading", name=case["product"] + " · ", exact=False)
                    row = header.locator("..")
                    started = monotonic()
                    with page.expect_response(lambda r: r.url.endswith(url) and r.status == 200):
                        row.get_by_role("button", name="Xem kết quả và chi phí").press("Enter")
                    content = row.get_by_role("region", name="Bàn giao nội dung cho storyboard")
                    expect(content).to_contain_text(plan["channel_copy"]["opening"])
                    expect(content).to_contain_text(plan["channel_copy"]["action"])
                    expect(content).to_contain_text(case["wording"])
                    expect(content).to_contain_text(case["qualifier"])
                    expect(content).to_contain_text(case["audience"])
                    expect(content).to_contain_text(case["objective"])
                    expect(row.get_by_role("heading", name="Storyboard", exact=True)).to_be_visible()
                    elapsed = round((monotonic() - started) * 1000)
                    summary = content.locator("summary")
                    summary.focus()
                    summary.press("Enter")
                    expect(content.get_by_text(output["handoff_digest"], exact=True)).to_be_visible()
                    expect(content.get_by_text(plan["question_to_validate"], exact=True)).to_be_visible()
                    summary.press("Enter")
                    content.evaluate("element => element.scrollIntoView({block: 'start'})")
                    capture_themes(page, folder / f"content-handoff-{width}.png")
                    audits = []
                    for scheme in ("light", "dark"):
                        page.emulate_media(color_scheme=scheme)
                        expect(page.locator("html")).to_have_attribute("data-theme", scheme)
                        audit = contrast(page, ".content-handoff", scheme)
                        assert not audit["failed"], audit
                        audits.append(audit)
                    editor = row.locator("[data-board-editor]")
                    editor.locator("summary").press("Enter")
                    selector = editor.locator("[name=mode]")
                    selector.select_option("controlled_hook")
                    hook = "direct" if width == 820 else "style_alternate"
                    editor.locator("[name=hook_variant]").select_option(hook)
                    editor.evaluate("e=>e.scrollIntoView({block:'start'})")
                    capture_themes(page, folder / f"storyboard-editor-{width}.png")
                    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith(url + "/storyboard-edition")) as saved:
                        editor.locator("[data-board-save]").press("Enter")
                    assert saved.value.ok, saved.value.text()
                    edited = saved.value.json()
                    expect(editor.get_by_role("status")).to_contain_text("Đã lưu phiên bản")
                    assert edited["storyboard"]["content_handoff_digest"] == output["handoff_digest"]
                    assert edited["storyboard"]["brief_fulfillment"]["ready_for_qa"]
                    sessions.append(dict(width=width, height=height, open_to_verified_copy_ms=elapsed,
                                         scroll_width=page.evaluate("document.documentElement.scrollWidth"), contrast=audits,
                                         themes=["light","dark"], keyboard="Enter opens report, toggles evidence and saves a hook edit",
                                         edited_revision=edited["revision"], edited_digest=edited["content_digest"]))
                finally:
                    page.close()
        finally:
            browser.close()
    receipt = dict(run_id=queued["id"], document_id=report["deliverable_id"], manifest_digest=snap["digest"],
                   content_digest=output["handoff_digest"], browser=browser.version, sessions=sessions)
    (folder / "browser-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")
