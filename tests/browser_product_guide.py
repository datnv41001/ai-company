"""Live Chromium acceptance for the recipient, editor and independent guide reviewer."""

import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from agency_fixtures import postgres_api
from browser_strategy_handoff import VIEWPORTS, open_handoff
from browser_visual_checks import contrast
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from product_guide_fixtures import activate_guide, advance_guide, guide_case
from test_registry import PG


def working_guide(browser, origin, ctx, actor, did, size):
    page = browser.new_page(viewport={"width": size[0], "height": size[1]}, color_scheme="light", reduced_motion="reduce")
    page.goto(f"{origin}/?workspace={ctx['scope']['tenant_id']}#/reviews")
    login = page.locator("#login-form")
    login.get_by_label("Email").fill(actor["email"])
    login.get_by_label("Mật khẩu").fill(actor["password"])
    login.get_by_role("button").click()
    expect(page.locator("#workspace")).to_be_visible()
    page.evaluate("location.hash='/reviews'")
    review = page.locator("#review-panel")
    review.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
    started = monotonic()
    review.get_by_label("Bản làm việc").select_option(did)
    panel = review.locator(".product-guide-studio")
    expect(panel.locator(".guide-component")).to_be_visible()
    return page, panel, round((monotonic() - started) * 1000)


def capture(page, panel, folder, name, theme):
    page.emulate_media(color_scheme=theme)
    expect(page.locator("html")).to_have_attribute("data-theme", theme)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    audit = contrast(page, ".product-guide-studio", theme)
    assert not audit["failed"], audit["failed"]
    anchor = panel.locator(".guide-component") if page.viewport_size["width"] < 600 else panel
    anchor.evaluate("e => e.scrollIntoView({block: 'start'})")
    page.screenshot(path=folder / name, animations="disabled")
    return audit


@PG
def test_guide_in_live_studio(tmp_path):
    folder = Path(os.environ.get("AMC_PRODUCT_GUIDE_SCREENS", tmp_path))
    folder.mkdir(parents=True, exist_ok=True)
    metrics = []
    with postgres_api() as api, sync_playwright() as pw:
        origin = str(api.base_url).rstrip("/")
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            with guide_case(api, instructions=True) as ctx:
                activate_guide(api, ctx)
                page, handoff, _ = open_handoff(browser, origin, ctx, ctx["recipient"], VIEWPORTS[0])
                start = handoff.get_by_role("button", name="Bắt đầu soạn hướng dẫn")
                start.focus()
                expect(start).to_be_focused()
                with page.expect_response(lambda res: res.url.endswith("/content-handoff/product-guide") and res.request.method == "POST") as reply:
                    start.press("Enter")
                assert reply.value.ok
                admitted = reply.value.json()
                assert admitted["status"] == "queued"
                advance_guide(ctx)
                handoff.get_by_role("button", name="Kiểm tra tiến độ hướng dẫn").click()
                expect(handoff.locator(".guide-component")).to_be_visible()
                data = api.get(ctx["base"] + "/workforce/runs/" + admitted["run_id"], headers=ctx["recipient"]["headers"]).json()
                did = data["deliverable_id"]
                page.close()
                for size in VIEWPORTS:
                    width, height = size
                    page, panel, elapsed = working_guide(browser, origin, ctx, ctx["recipient"], did, size)
                    focus = panel.get_by_label("Tiêu đề", exact=True)
                    focus.focus()
                    focus.press("Tab")
                    expect(panel.get_by_label("Cách trình bày các bước")).to_be_focused()
                    for theme in ("light", "dark"):
                        name = f"guide-{width}-{theme}.png"
                        audit = capture(page, panel, folder, name, theme)
                        metrics.append(
                            {
                                "viewport": [width, height],
                                "theme": theme,
                                "preview": name,
                                "open_to_preview_ms": elapsed,
                                "contrast": audit,
                                "keyboard_next": "layout",
                                "browser": browser.version,
                            }
                        )
                    page.close()
                page, panel, _ = working_guide(browser, origin, ctx, ctx["recipient"], did, VIEWPORTS[0])
                old = panel.locator(".guide-component h4").inner_text()
                title = panel.get_by_label("Tiêu đề", exact=True)
                title.fill("Unsupported product promise")
                expect(panel.get_by_role("button", name="Lưu phiên bản")).to_be_disabled()
                step = panel.locator(".guide-component li").first.inner_text()
                title.fill(step)
                panel.get_by_label("Cách trình bày các bước").select_option("checklist")
                assert panel.locator(".guide-component h4").inner_text() != old
                expect(panel.get_by_role("button", name="Gửi QA độc lập")).to_be_disabled()
                with page.expect_response(lambda res: res.url.endswith("/studio/product-guide") and res.request.method == "PATCH") as saved:
                    panel.get_by_role("button", name="Lưu phiên bản").press("Enter")
                assert saved.value.ok and saved.value.json()["guide"]["title"] == step
                revision = saved.value.json()["revision"]
                panel.locator(".guide-source summary").press("Enter")
                expect(panel.locator(".guide-source blockquote")).to_have_text(ctx["order"]["message"])
                panel.screenshot(path=folder / "editor-saved.png", animations="disabled")
                panel.get_by_role("button", name="Gửi QA độc lập").press("Enter")
                expect(panel.get_by_role("status")).to_contain_text("Chờ QA độc lập")
                page.close()
                page, panel, _ = working_guide(browser, origin, ctx, ctx["reviewer"], did, VIEWPORTS[0])
                expect(panel.get_by_label("Tiêu đề", exact=True)).to_have_count(0)
                for control in panel.locator(".guide-obligation-control select").all():
                    control.select_option("met")
                panel.get_by_label("Trình tự theo nguồn và phiếu giao việc").select_option("independent")
                panel.get_by_label("Nhận xét đối chiếu nguồn").fill("Reviewed the steps, limitation and CTA against the signed product declaration.")
                with page.expect_response(lambda res: res.url.endswith("/review") and res.request.method == "POST") as signed:
                    panel.get_by_role("button", name="Ghi quyết định QA").press("Enter")
                assert signed.value.ok and signed.value.json()["qa_approved_revision"] == revision
                expect(panel.get_by_role("status")).to_contain_text("QA nội bộ đã duyệt")
                current = accepted(api.get(ctx["base"] + f"/deliverables/{did}/studio/product-guide", headers=ctx["reviewer"]["headers"]))
                assert current["qa_receipt"] and current["content_digest"] == signed.value.json()["qa_approved_digest"]
                panel.locator(".guide-source summary").press("Enter")
                expect(panel.locator(".guide-source")).to_contain_text(current["qa_receipt"])
                panel.screenshot(path=folder / "independent-qa.png", animations="disabled")
                accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
                panel.get_by_role("button", name="Kiểm tra lại phiên bản").click()
                expect(panel.get_by_role("alert")).to_be_visible()
                expect(panel.locator(".guide-component")).to_have_count(0)
                page.close()
            with guide_case(api, instructions=False) as ctx:
                page, handoff, _ = open_handoff(browser, origin, ctx, ctx["recipient"], VIEWPORTS[-1])
                handoff.get_by_role("button", name="Bắt đầu soạn hướng dẫn").press("Enter")
                hold = handoff.get_by_role("status").filter(has_text="Cần nguồn được duyệt")
                expect(hold).to_be_visible()
                hold.evaluate("e=>e.scrollIntoView({block:'center'})")
                page.screenshot(path=folder / "source-hold-mobile.png", animations="disabled")
                page.close()
            (folder / "browser.json").write_text(
                json.dumps(
                    {
                        "run": admitted["run_id"],
                        "document": did,
                        "approved_revision": revision,
                        "qa_receipt": current["qa_receipt"],
                        "content_digest": current["content_digest"],
                        "edited_title": current["guide"]["title"],
                        "source_handle": current["guide"]["source_map"]["title"],
                        "preview_hidden_after_mandate_withdrawal": True,
                        "sizes": metrics,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        finally:
            browser.close()
