"""Chromium checks the actual read-only order, manual decisions and signed independent return."""

import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from agency_fixtures import postgres_api
from browser_product_guide import working_guide
from browser_strategy_handoff import VIEWPORTS
from browser_visual_checks import contrast
from knowledge_fixtures import accepted
from product_guide_fixtures import guide_case, qualification_cases
from test_product_guide_order_qa import produce
from test_product_guide_studio import version
from test_registry import PG


def reviewer_assess(panel, kind):
    controls = panel.locator(".guide-obligation-control select")
    for control in controls.all():
        control.select_option("met")
    panel.get_by_label("Trình tự theo nguồn và phiếu giao việc").select_option(kind)
    panel.get_by_label("Nhận xét đối chiếu nguồn").fill("Đã đối chiếu thứ tự, nguồn và từng yêu cầu trên đúng phiên bản.")


@PG
def test_order_in_real_chromium(tmp_path):
    folder = Path(os.getenv("AMC_GUIDE_ORDER_SCREENS") or tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    metrics = []
    case = qualification_cases()[0]
    with postgres_api() as api, guide_case(api, case=case) as ctx, sync_playwright() as pw:
        task, doc = produce(api, ctx)
        editor, qa = (ctx[k]["headers"] for k in ("recipient", "reviewer"))
        studio = doc + "/studio/product-guide"

        def inspect():
            return accepted(api.get(studio, headers=qa))

        view = inspect()
        checklist = accepted(api.patch(studio, headers=editor, json=version(view) | {"heading": "use_case", "layout": "checklist"}))
        accepted(api.post(doc + "/submit", headers=editor, json=version(checklist)))
        origin = str(api.base_url).rstrip("/")
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for size in VIEWPORTS:
                page, panel, ms = working_guide(browser, origin, ctx, ctx["reviewer"], view["document_id"], size)
                order = panel.locator(".guide-order")
                expect(order.get_by_text(case["requirements"][0], exact=True)).to_be_visible()
                expect(panel.get_by_role("button", name="Ghi quyết định QA")).to_be_disabled()
                controls = order.locator("select")
                assert controls.count() == len(view["work_order"]["obligations"])
                controls.nth(0).focus()
                controls.nth(0).press("Tab")
                expect(controls.nth(1)).to_be_focused()
                for theme in ("light", "dark"):
                    page.emulate_media(color_scheme=theme)
                    expect(page.locator("html")).to_have_attribute("data-theme", theme)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                    audit = contrast(page, ".guide-order", theme)
                    assert not audit["failed"], audit
                    requirement = order.get_by_text(case["requirements"][0], exact=True)
                    requirement.evaluate("e=>e.scrollIntoView({block:'center'})")
                    name = f"order-{size[0]}-{theme}.png"
                    page.screenshot(path=folder / name, animations="disabled")
                    metrics.append(
                        {
                            "viewport": list(size),
                            "theme": theme,
                            "screenshot": name,
                            "open_to_visible_ms": ms,
                            "contrast": audit,
                            "keyboard": "first obligation to second via Tab",
                        }
                    )
                page.close()
            page, panel, _ = working_guide(browser, origin, ctx, ctx["reviewer"], view["document_id"], VIEWPORTS[0])
            reviewer_assess(panel, "ordered")
            sign = panel.get_by_role("button", name="Ghi quyết định QA")
            expect(sign).to_be_disabled()
            expect(panel.get_by_text("Các bước phụ thuộc nhau.", exact=False)).to_be_visible()
            req = panel.locator(".guide-order dl > div").filter(has=panel.page.get_by_text(case["requirements"][0], exact=True)).locator("select")
            req.select_option("unsupported")
            panel.get_by_label("Kết luận", exact=True).select_option("rejected")
            expect(sign).to_be_enabled()
            sign.press("Enter")
            expect(panel.get_by_text("QA đã từ chối · Phiên bản 2", exact=True)).to_be_visible()
            returned = inspect()
            assert returned["order_review_receipt"] and returned["guide_review"]["obligations"]["requirements.1"] == "unsupported"
            page.close()
            page, panel, _ = working_guide(browser, origin, ctx, ctx["recipient"], view["document_id"], VIEWPORTS[-1])
            expect(panel.locator(".guide-order")).to_contain_text("Hướng dẫn chưa đáp ứng")
            panel.get_by_label("Cách trình bày các bước").select_option("numbered")
            panel.get_by_role("button", name="Lưu phiên bản").press("Enter")
            expect(panel.get_by_text("Bản nháp · Phiên bản 3", exact=True)).to_be_visible()
            panel.get_by_role("button", name="Gửi QA độc lập").press("Enter")
            expect(panel.get_by_text("Chờ QA độc lập · Phiên bản 3", exact=True)).to_be_visible()
            page.close()
            page, panel, _ = working_guide(browser, origin, ctx, ctx["reviewer"], view["document_id"], VIEWPORTS[0])
            reviewer_assess(panel, "ordered")
            started = monotonic()
            panel.get_by_role("button", name="Ghi quyết định QA").press("Enter")
            expect(panel.get_by_text("QA nội bộ đã duyệt · Phiên bản 3", exact=True)).to_be_visible()
            readback_ms = round((monotonic() - started) * 1000)
            signed = inspect()
            expect(panel.locator(".guide-order")).to_contain_text(signed["qa_receipt"])
            assert signed["guide_review"]["sequence"] == "ordered"
            panel.locator(".guide-order").get_by_text(signed["qa_receipt"], exact=False).evaluate("e=>e.scrollIntoView({block:'center'})")
            page.screenshot(path=folder / "numbered-qa-receipt.png", animations="disabled")
            (folder / "browser.json").write_text(
                json.dumps(
                    {
                        "browser": browser.version,
                        "case": case["case_id"],
                        "run": task["run_id"],
                        "manifest": task["manifest_id"],
                        "return_receipt": returned["order_review_receipt"],
                        "qa_receipt": signed["qa_receipt"],
                        "revision": signed["revision"],
                        "content_digest": signed["content_digest"],
                        "decision_to_readback_ms": readback_ms,
                        "readable_obligations": len(signed["work_order"]["obligations"]),
                        "renders": metrics,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            page.close()
        finally:
            browser.close()
