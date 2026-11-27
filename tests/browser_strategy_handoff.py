"""Exercise the signed-in Studio handoff on a live, disposable PostgreSQL worker commission."""

import json
import os
from pathlib import Path
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from agency_fixtures import postgres_api
from browser_visual_checks import contrast
from knowledge_fixtures import accepted
from strategy_runtime_fixtures import OBSERVATION, PRODUCT, UNSUPPORTED, commission_lab, prepare_review
from test_registry import PG


VIEWPORTS = ((1280, 850), (820, 1180), (390, 844))


def open_handoff(browser, origin, ctx, actor, size):
    width, height = size
    page = browser.new_page(viewport={"width": width, "height": height}, color_scheme="light", reduced_motion="reduce")
    tenant = ctx["scope"]["tenant_id"]
    page.goto(f"{origin}/?workspace={tenant}#/reviews")
    login = page.locator("#login-form")
    login.get_by_label("Email").fill(actor["email"])
    login.get_by_label("Mật khẩu").fill(actor["password"])
    login.get_by_role("button").click()
    expect(page.locator("#workspace")).to_be_visible()
    page.evaluate("location.hash='/reviews'")
    review = page.locator("#review-panel")
    review.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
    review.get_by_label("Bản làm việc").select_option(ctx["doc"].rsplit("/", 1)[1])
    studio = review.locator(".marketing-studio")
    studio.locator("summary").first.focus()
    studio.locator("summary").first.press("Enter")
    panel = studio.locator(".strategy-handoff")
    summary = panel.locator("summary").first
    summary.focus()
    expect(summary).to_be_focused()
    started = monotonic()
    summary.press("Enter")
    expect(panel.locator(".strategy-verdict")).to_be_visible()
    ms = round((monotonic() - started) * 1000)
    return page, panel, ms


def fill_decision(panel, ctx, evidence, state, release_review="aligned"):
    form = panel.locator(".strategy-decision-form")
    expect(form).to_be_visible()
    ref = {r["statement"]: r["handle"] for r in evidence["references"]}
    form.get_by_label("Kết luận về căn cứ").select_option(state)
    form.get_by_label("Ủy quyền phê duyệt").select_option(ctx["mandate"]["id"])
    form.get_by_label("Người nhận việc Content").select_option(ctx["recipient"]["id"])
    form.get_by_label("Phương án chiến lược").select_option("explain_use")
    form.get_by_label("Tài sản được đề nghị").select_option("web_use_guide")
    form.get_by_label("Quan sát làm căn cứ").select_option(ref[OBSERVATION])
    form.get_by_label("Loại bằng chứng quan sát").select_option("observed_behaviour")
    form.get_by_label("Trích nguyên văn đoạn quan sát").fill(OBSERVATION)
    form.get_by_label("Nguồn dữ kiện sản phẩm").select_option(ref[PRODUCT])
    form.get_by_label("Người có quyết định mua").fill(evidence["audience"])
    form.get_by_label("Tình huống mua").fill("Shift handover in one synthetic shop.")
    form.get_by_label("Diễn giải đối chiếu với nguồn").fill("The observation supports preparing an internal layout guide.")
    form.get_by_label("Giới hạn mẫu và khả năng suy rộng").fill("One observed shift; no claim about other sites.")
    brief = form.locator(".strategy-production-brief")
    expect(brief).to_contain_text("automatic worker tracking")
    expect(brief).to_contain_text("Tie the proposed asset to an observed task.")
    release = form.get_by_label("Quyết định chuyển nội dung brief")
    expect(release).to_have_value("")
    release.select_option(release_review)
    if release_review == "aligned":
        form.get_by_label("Tình huống cho người nhận").select_option("work_handover")
        form.get_by_label("Hướng viết cho người nhận").select_option("demonstrate_use")
    return form


def save(page, form):
    with page.expect_response(lambda r: r.url.endswith("/studio/content-handoff") and r.request.method == "POST") as result:
        form.get_by_role("button", name="Ghi quyết định nội bộ").press("Enter")
    return result.value.status


def snapshot(browser, origin, ctx, actor, folder, stage, expected_view):
    metrics = []
    for size in VIEWPORTS:
        width, height = size
        page, panel, ms = open_handoff(browser, origin, ctx, actor, size)
        try:
            heading = "Tạm giữ bàn giao" if stage == "hold" else "Được lập bản nháp nội bộ"
            expect(panel.get_by_role("heading", name=heading, exact=True)).to_be_visible()
            expect(panel.get_by_text("Có thể chuẩn bị nội bộ", exact=True)).to_be_visible()
            expect(panel.get_by_text(PRODUCT, exact=True).first).to_be_visible()
            expect(panel.get_by_text("Chưa có hợp đồng đo lường được duyệt", exact=True)).to_be_visible()
            if stage == "hold":
                expect(panel.get_by_text("Bổ sung căn cứ cho quyết định.", exact=True)).to_be_visible()
                expect(panel.get_by_text("Biên tập viên Strategy và chủ nguồn", exact=True)).to_be_visible()
                expect(panel.locator(".strategy-assignment")).to_have_count(0)
            else:
                expect(panel.get_by_text("Research, Strategy và nguồn của bản này", exact=True)).to_have_count(0)
                expect(panel.locator(".strategy-decision-form")).to_have_count(0)
                expect(panel.locator(".strategy-assignment")).to_contain_text("Hướng dẫn sử dụng trên trang sản phẩm")
                expect(panel.locator(".strategy-assignment")).to_contain_text(expected_view["work_order"]["message"])
                assignment = panel.locator(".strategy-assignment")
                assignment.evaluate("e=>e.scrollIntoView({block:'start'})")
                if width == VIEWPORTS[0][0]:
                    page.screenshot(path=folder / "recipient-order.png", animations="disabled")
                visible = assignment.inner_text()
                order = expected_view["work_order"]
                requirements = [
                    "Tải danh mục",
                    "Ngắn gọn",
                    "Prepare a practical guide for one shift handover.",
                    "automatic worker tracking",
                    "Tie the proposed asset to an observed task.",
                    order["brief"]["cta"],
                    order["brief"]["purpose"],
                    order["brief"]["objective"],
                    order["brief"]["audience"],
                    order["guidance"]["situation"],
                    order["guidance"]["direction"],
                    order["guidance"]["sample_scope"],
                    order["approval"],
                    "Chỉ chuẩn bị bản nháp nội bộ.",
                ]
                missing = [item for item in requirements if item not in visible]
                assert not missing, f"Missing in the signed-in recipient’s work order: {missing}"
                private = [
                    UNSUPPORTED,
                    OBSERVATION,
                    "Shift handover in one synthetic shop.",
                    "One observed shift; no claim about other sites.",
                    "The observation supports preparing an internal layout guide.",
                    ctx["mandate"]["id"],
                    ctx["reviewer"]["id"],
                ]
                assert all(value not in visible for value in private)
                if width == VIEWPORTS[0][0]:
                    (folder / "recipient-visible-order.txt").write_text(visible + "\n", encoding="utf8")
            summary = panel.locator("summary").first
            summary.focus()
            expect(summary).to_be_focused()
            assert summary.evaluate("e=>getComputedStyle(e).outlineStyle !== 'none'")
            for theme in ("light", "dark"):
                page.emulate_media(color_scheme=theme)
                expect(page.locator("html")).to_have_attribute("data-theme", theme)
                assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
                panel.evaluate("e=>e.scrollIntoView({block:'start'})")
                audit = contrast(page, ".strategy-handoff", theme)
                assert not audit["failed"], audit["failed"]
                image = f"{stage}-{width}-{theme}.png"
                page.screenshot(path=folder / image, animations="disabled")
                if stage == "draft":
                    constraints = panel.locator(".strategy-production-brief").get_by_text("Yêu cầu bắt buộc", exact=True)
                    constraints.evaluate("e=>e.scrollIntoView({block:'start'})")
                    page.screenshot(path=folder / f"recipient-requirements-{width}-{theme}.png", animations="disabled")
                metrics.append(
                    {
                        "status": stage,
                        "viewport": [width, height],
                        "theme": theme,
                        "focus": "keyboard summary",
                        "browser": browser.version,
                        "open_to_status_ms": ms,
                        "contrast": audit,
                        "image": image,
                        "document_id": ctx["doc"].rsplit("/", 1)[1],
                        "revision": expected_view["revision"],
                        "receipt": expected_view["decision"]["receipt_id"],
                    }
                )
        finally:
            page.wait_for_load_state("networkidle")
            page.close()
    return metrics


@PG
def test_content_handoff_in_staff_studio(tmp_path):
    folder = Path(os.getenv("AMC_STRATEGY_UI_EVIDENCE") or tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    with postgres_api() as api, commission_lab(api) as ctx, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        origin, path, reviewer = str(api.base_url).rstrip("/"), ctx["studio"] + "/content-handoff", ctx["reviewer"]

        def get():
            return accepted(api.get(path, headers=reviewer["headers"]))

        try:
            prepare_review(api, ctx)
            initial = get()
            assert initial["can_decide"] and initial["status"] == "needs_decision"
            page, panel, _ = open_handoff(browser, origin, ctx, reviewer, VIEWPORTS[0])
            research = panel.get_by_text("Research, Strategy và nguồn của bản này", exact=True)
            research.press("Enter")
            sources = research.locator("..")
            expect(sources.locator("blockquote", has_text=OBSERVATION)).to_be_visible()
            expect(sources.get_by_text(OBSERVATION, exact=True).first).to_be_visible()
            assert UNSUPPORTED not in sources.inner_text()
            sources.locator("article").first.evaluate("e=>e.scrollIntoView({block:'start'})")
            page.screenshot(path=folder / "reviewer-source-revisions.png", animations="disabled")
            research.press("Enter")
            trace = panel.get_by_text("Đề xuất của worker và dấu vết QA", exact=True)
            trace.press("Enter")
            expect(trace.locator("..")).to_contain_text(UNSUPPORTED)
            expect(trace.locator("..")).to_contain_text(initial["provenance"]["qa_receipt"])
            trace.evaluate("e=>e.scrollIntoView({block:'start'})")
            page.screenshot(path=folder / "worker-proposal-and-qa.png", animations="disabled")
            trace.press("Enter")
            # An editor produces a newer reviewed revision after this reviewer has read the form.
            form = fill_decision(panel, ctx, initial, "insufficient")
            prepare_review(api, ctx)
            newer = get()
            assert newer["revision"] > initial["revision"]
            assert save(page, form) == 412
            expect(form.get_by_role("status")).to_contain_text("Tải lại phiếu")
            form.get_by_role("status").scroll_into_view_if_needed()
            page.screenshot(path=folder / "stale-revision.png")
            panel.get_by_role("button", name="Tải lại phiếu bàn giao").click()
            assert save(page, fill_decision(panel, ctx, newer, "insufficient")) == 200
            expect(panel.get_by_role("heading", name="Tạm giữ bàn giao", exact=True)).to_be_visible()
            held = get()
            assert held["status"] == "hold" and not held["work_order"] and held["permitted_product_wording"]
            page.wait_for_load_state("networkidle")
            page.close()
            sessions = snapshot(browser, origin, ctx, reviewer, folder, "hold", held)

            prepare_review(api, ctx)
            conflicting = get()
            page, panel, _ = open_handoff(browser, origin, ctx, reviewer, VIEWPORTS[1])
            assert save(page, fill_decision(panel, ctx, conflicting, "supported", "conflict")) == 200
            expect(panel.get_by_text("Đối chiếu lại tình huống và hướng viết với brief đã ký trước khi giao việc.", exact=True)).to_be_visible()
            expect(panel.locator(".strategy-assignment")).to_have_count(0)
            panel.evaluate("e=>e.scrollIntoView({block:'start'})")
            page.screenshot(path=folder / "brief-conflict-hold.png", animations="disabled")
            page.wait_for_load_state("networkidle")
            page.close()

            prepare_review(api, ctx)
            candidate = get()
            assert candidate["revision"] > held["revision"]
            page, panel, _ = open_handoff(browser, origin, ctx, reviewer, VIEWPORTS[-1])
            assert save(page, fill_decision(panel, ctx, candidate, "supported")) == 200
            expect(panel.get_by_role("heading", name="Được lập bản nháp nội bộ")).to_be_visible()
            ready = get()
            assert ready["status"] == "draft_for_approval"
            page.wait_for_load_state("networkidle")
            page.close()
            recipient = ctx["recipient"]
            received = accepted(api.get(path, headers=recipient["headers"]))
            assert received["audience_mode"] == "recipient" and not received["can_decide"]
            assert "sources" not in received["work_order"] and not received.get("references")
            assert received["work_order"]["message"] == ready["work_order"]["message"]
            sessions.extend(snapshot(browser, origin, ctx, recipient, folder, "draft", received))
            (folder / "browser-measurements.json").write_text(
                json.dumps(
                    {
                        "backend": "PostgreSQL; real dispatcher and worker; deterministic specialist replies",
                        "run_id": ctx["run"]["id"],
                        "manifest_id": ctx["snap"]["id"],
                        "stale_request": {"read_revision": initial["revision"], "current_revision": newer["revision"], "status": 412},
                        "sessions": sessions,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf8",
            )
        finally:
            browser.close()
