"""Exercise the signed internal instruction form with a keyboard at three viewport sizes."""
import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from agency_fixtures import postgres_api
from c3_browser_themes import capture_themes
from strategy_runtime_fixtures import commission_lab
from test_research_instruction import EN, EN_STEP, submit


def test_internal_research_decision_in_browser(tmp_path):
    out = Path(os.environ.get("AMC_RES_QA_SCREENS", tmp_path))
    out.mkdir(parents=True, exist_ok=True)
    metrics = []
    with postgres_api() as api, commission_lab(api) as ctx, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        for width, height in ((1280,850),(820,1180),(390,844)):
            saved, _ = submit(api, ctx, EN + " " + EN_STEP)
            page = browser.new_page(viewport={"width":width,"height":height}, color_scheme="light", reduced_motion="reduce")
            actor = ctx["reviewer"]
            page.goto(str(api.base_url).rstrip("/") + "/?workspace=" + ctx["scope"]["tenant_id"] + "#/reviews")
            login = page.locator("#login-form")
            login.get_by_label("Email").fill(actor["email"])
            login.get_by_label("Mật khẩu").fill(actor["password"])
            login.get_by_role("button").click()
            expect(page.locator("#workspace")).to_be_visible()
            page.evaluate("location.hash='/reviews'")
            pane = page.locator("#review-panel")
            pane.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
            pane.get_by_label("Bản làm việc").select_option(ctx["doc"].rsplit("/",1)[1])
            start = monotonic()
            pane.get_by_text("Đối chiếu nội dung với bằng chứng", exact=True).click()
            row = pane.locator(".claim-comparison").filter(has=page.get_by_text(EN, exact=True))
            action = row.get_by_role("button", name="Xác nhận hướng dẫn nội bộ")
            expect(action).to_be_visible()
            elapsed_ms = round((monotonic()-start)*1000)
            assert not row.get_by_label("Nguồn chứng minh nhận định").count()
            row.get_by_label("Lý do phân loại").fill("Câu hỏi đề nghị thuật lại một bước đã làm trong lần mua trước.")
            action.focus()
            expect(action).to_be_focused()
            capture_themes(page, out / f"instruction-{width}.png")
            action.press("Enter")
            expect(row.get_by_text("Đã phân loại cho kế hoạch nghiên cứu nội bộ.")).to_be_visible()
            metrics.append(dict(width=width,height=height,revision=saved["revision"],open_to_form_ms=elapsed_ms,
                                accepted_dom=row.inner_text(),horizontal_overflow=page.evaluate("document.documentElement.scrollWidth-innerWidth")))
            page.wait_for_load_state("networkidle")
            page.goto("about:blank")
            page.close()
        browser.close()
    (out/"dom.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
