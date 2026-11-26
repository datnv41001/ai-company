"""Verify the actual decoder, responsive asset canvas and synthetic form in Chromium."""

import json
import os
from base64 import b64decode
from hashlib import sha256
from pathlib import Path
import subprocess

from playwright.sync_api import expect, sync_playwright
import pytest

from browser_c3_content_gate import client, local_api  # noqa: F401 -- file database for concurrent localhost requests
from c3_browser_themes import capture_themes
from campaign_planner_fixtures import CASES
from test_channel_editions import workforce  # noqa: F401
from test_production_studios import rehearsal


def approved_ad_preview(page, plan, landing, out, width):
    page.evaluate("location.hash='/campaigns'")
    engine = page.locator("#campaign-engine")
    engine.locator("#engine-select").select_option(plan["campaign_id"])
    pack_path = "/engine/plans/" + plan["id"] + "/content-pack"
    pack_button = engine.get_by_text("Bộ nội dung và kế hoạch quảng cáo", exact=True)
    with page.expect_response(lambda response: response.url.endswith(pack_path) and response.status == 200) as initial:
        pack_button.press("Enter")
    pack = initial.value.json()
    destination = pack["advertising"]["destination"]
    meta = landing["files"]["landing.html"]
    assert destination["status"] == "approved" and destination["package_id"] == landing["id"]
    assert destination["package_digest"] == landing["digest"] and destination["file_digest"] == meta["sha256"]
    assert destination["studio_revision"] == landing["studio_revision"] and destination["deliverable_id"] == landing["did"]
    engine.get_by_text("Advertising Studio · Mẫu quảng cáo tìm kiếm", exact=True).press("Enter")
    preview = engine.get_by_role("button", name="Xem trang đích đã duyệt", exact=True)
    expect(preview).to_be_visible()
    expect(engine.get_by_text("Trang đích sandbox đã duyệt", exact=True)).to_be_visible()
    preview.evaluate("e=>e.scrollIntoView({block:'center'})")
    capture_themes(page, out / f"ads-ready-{width}.png")
    writes = []

    def watch(request):
        if request.method not in ("GET", "HEAD", "OPTIONS") and any(part in request.url for part in ("/sandbox/commands", "/submissions", "/visits")):
            writes.append(request.url)

    page.on("request", watch)
    try:
        with (
            page.expect_response(lambda response: response.url.endswith(pack_path)) as live,
            page.expect_response(lambda response: response.url.endswith(destination["download_url"])) as file,
        ):
            preview.press("Enter")
        assert live.value.json()["advertising"]["destination"] == destination
        assert file.value.status == 200
        envelope = file.value.json()
        raw = b64decode(envelope["base64"], validate=True)
        assert sha256(raw).hexdigest() == envelope["sha256"] == meta["sha256"]
        assert len(raw) == envelope["bytes"] == meta["bytes"]
        host = engine.locator('iframe[title="Bản xem trang đích sandbox"]')
        frame = host.content_frame
        headline = landing["master"]["sections"]["headline"]
        expect(frame.locator("h1")).to_have_text(headline)
        assert host.get_attribute("srcdoc").encode("utf-8") == raw
        assert host.get_attribute("sandbox") == "" and host.get_attribute("referrerpolicy") == "no-referrer"
        assert frame.locator("title").text_content() == landing["master"]["seo"]["page_title"]
        assert frame.locator('meta[name="description"]').get_attribute("content") == landing["master"]["seo"]["meta_description"]
        expect(frame.get_by_role("link", name=landing["master"]["sections"]["call_to_action"])).to_have_attribute("href", "#request")
        host.evaluate("e=>e.scrollIntoView({block:'center'})")
        capture_themes(page, out / f"ads-landing-{width}.png")
        assert not writes
    finally:
        page.remove_listener("request", watch)
    return {
        "width": width,
        "plan_digest": pack["plan_digest"],
        "destination": destination,
        "file_bytes": len(raw),
        "iframe_html_sha256": sha256(raw).hexdigest(),
        "headline": headline,
        "sandbox_event_writes": len(writes),
    }


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_production_browser(api, workforce, monkeypatch, case):  # noqa: F811
    out = Path(os.getenv("AMC_PRODUCTION_SCREENS", "knowledge-browser-evidence/marketing-studio/production")) / case["buyer_action"]
    out.mkdir(parents=True, exist_ok=True)
    observations = []
    advertising = []

    def capture(owner, doc, plan, exports):
        with local_api() as origin, sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
            try:
                for width, height in ((1280, 850), (820, 1180), (390, 844)):
                    page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
                    try:
                        page.goto(origin + "/?workspace=" + owner["tenant"] + "#/reviews")
                        login = page.locator("#login-form")
                        login.get_by_label("Email").fill(owner["email"])
                        login.get_by_label("Mật khẩu").fill(owner["password"])
                        login.get_by_role("button").click()
                        expect(page.locator("#workspace")).to_be_visible()
                        page.evaluate("location.hash='/reviews'")
                        panel = page.locator("#review-panel")
                        panel.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
                        panel.get_by_label("Bản làm việc").select_option(doc.rsplit("/", 1)[1])
                        studio = panel.locator(".marketing-studio")
                        studio.locator("summary").first.press("Enter")
                        nav = studio.locator(".studio-nav")
                        nav.get_by_role("button", name="Brief thiết kế", exact=True).press("Enter")
                        prod = studio.locator(".production-studio")
                        prod.locator("summary").first.press("Enter")
                        expect(prod.locator("figure img")).to_be_visible()
                        prod.get_by_label("Tỉ lệ xem").select_option("portrait" if width == 390 else "landscape")
                        expect(prod.locator("figcaption")).to_contain_text("portrait" if width == 390 else "landscape")
                        prod.locator("figure").evaluate("e=>e.scrollIntoView({block:'center'})")
                        capture_themes(page, out / f"creative-{width}.png")
                        prod.get_by_text("Storyboard, phụ đề và video sáu giây", exact=True).click()
                        video = prod.locator("video")
                        video.evaluate("async v=>{if(v.readyState<2)await new Promise((ok,fail)=>{v.onloadeddata=ok;v.onerror=fail})}")
                        duration = video.evaluate("v=>v.duration")
                        assert 5.9 <= duration <= 6.1 and video.evaluate("v=>v.videoWidth") == 640
                        changed = video.evaluate("""async v=>{
                          const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;
                          const ctx=c.getContext('2d');
                          const sample=()=>{ctx.drawImage(v,0,0);return c.toDataURL();};const first=sample();
                          await new Promise((ok,fail)=>{const t=setTimeout(()=>fail(Error('seek timeout')),7000);
                            v.addEventListener('seeked',()=>{clearTimeout(t);ok()},{once:true});v.currentTime=3.5});
                          return sample()!==first;
                        }""")
                        assert changed
                        nav.get_by_role("button", name="Nội dung trang", exact=True).press("Enter")
                        prod = studio.locator(".production-studio")
                        prod.locator("summary").first.press("Enter")
                        frame = prod.frame_locator("iframe")
                        expect(frame.locator("h1")).to_be_visible()
                        prod.get_by_role("button", name="Xem trang toàn màn hình").click()
                        large = prod.get_by_role("dialog").frame_locator("iframe")
                        expect(large.locator("h1")).to_be_visible()
                        page_width = large.locator("html").evaluate("e=>e.clientWidth")
                        assert width * 0.85 <= page_width <= width
                        assert large.locator(".grid").evaluate("e=>getComputedStyle(e).gridTemplateColumns.split(' ').length") == (1 if width == 390 else 2)
                        capture_themes(page, out / f"landing-{width}.png")
                        page.keyboard.press("Escape")
                        assert frame.locator('meta[name="description"]').get_attribute("content") == exports["landing"]["master"]["seo"]["meta_description"]
                        if width == 390:
                            prod.get_by_role("button", name="Bắt đầu phiên thử").click()
                            expect(prod).to_contain_text("Đã ghi một lượt mở trang tổng hợp")
                            q = frame.locator('[name="quantity"]')
                            q.fill("0")
                            frame.get_by_role("button").click()
                            assert not q.evaluate("e=>e.validity.valid")
                            q.fill("2")
                            frame.get_by_role("button").click()
                            expect(frame.get_by_role("status")).to_contain_text("Đã ghi nhận")
                            capture_themes(page, out / "form-390.png")
                        if case["buyer_action"] == "appointment":
                            page.goto(origin + "/?workspace=" + owner["tenant"] + "#/campaigns")
                            engine = page.locator("#campaign-engine")
                            engine.locator("select").first.select_option(plan["campaign_id"])
                            metric = engine.locator("[data-primary-kpi]")
                            expected = "2" if width == 390 else "1"
                            for label, value in (("Có nguồn trang đích", expected), ("Có nguồn media", "0"),
                                                 ("Chưa rõ nguồn media", expected), ("Thiếu nguồn", "0")):
                                row = metric.locator(".engine-row").filter(has=page.get_by_text(label, exact=True))
                                expect(row.locator(".state-chip")).to_have_text(value)
                            for theme in ("light", "dark"):
                                page.emulate_media(color_scheme=theme)
                                expect(page.locator("html")).to_have_attribute("data-theme", theme)
                                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                                metric.screenshot(path=out / f"attribution-{width}-{theme}.png", animations="disabled")
                        observations.append(
                            {
                                "width": width,
                                "height": height,
                                "video_seconds": duration,
                                "decoder": "VP8",
                                "browser": browser.version,
                                "viewport_scroll_width": page.evaluate("document.documentElement.scrollWidth"),
                                "landing_viewport": page_width,
                            }
                        )
                        advertising.append(approved_ad_preview(page, plan, exports["landing"], out, width))
                    finally:
                        page.close()
            finally:
                browser.close()
        (out / "sessions.json").write_text(
            json.dumps(
                {"synthetic": True, "plan_digest": plan["digest"], "package_digests": {k: i["digest"] for k, i in exports.items()}, "sessions": observations},
                indent=2,
            )
            + "\n",
            encoding="utf8",
        )
        (out / "advertising.json").write_text(
            json.dumps(
                {
                    "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                    "test_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
                    "synthetic": True,
                    "browser": observations[0]["browser"],
                    "sessions": advertising,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf8",
        )

    rehearsal(api, workforce, monkeypatch, case, capture)
