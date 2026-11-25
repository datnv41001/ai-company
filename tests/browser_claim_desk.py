"""Synthetic approval and editor privacy acceptance against a real loopback PostgreSQL API."""

import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_knowledge import BASE, drop_after_commit, login, select_scope, user
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, bundle, call, revision


def fixture(api):
    owner, editor = [user(api, kind) for kind in ("claim-owner", "claim-editor")]
    for actor in (owner, editor):
        actor.update(tenant=actor["tenant_id"], id=actor["user_id"])
    t = owner["tenant"]
    invite_member(api, "/api/tenants/" + t, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    _, path, src, public, _ = bundle(api, owner)
    data = api.get(path + "/revisions/" + src["id"], headers=owner["headers"]).json()["data"]
    assertion = data["entries"][0]["assertion"]
    secret = uuid4().hex
    markers = [secret + "-document", secret + "-issuer", secret + "-locator", secret + "-excerpt", secret + "-notes"]
    private = revision(
        api,
        owner,
        path,
        "private-" + secret[:6],
        "source",
        data | {"document": markers[0], "publisher": markers[1], "entries": [{"locator": markers[2], "excerpt": markers[3], "assertion": assertion}]},
        "restricted",
    )
    bound = revision(
        api, owner, path, "secret-link-" + secret[:6], "binding", {"source": private["id"], "locator": markers[2], "assertion": assertion}, "restricted"
    )
    claim = revision(api, owner, path, "approved-phrase-" + secret[:6], "claim", {"binding": bound["id"], "assertion": assertion}, approve=False)
    accepted(
        call(
            api, owner, path, "/revisions/" + claim["id"] + "/events", state="approved", expected_sequence=0, expected_digest=claim["digest"], reason=markers[4]
        )
    )
    return dict(
        owner=owner,
        editor=editor,
        tenant=t,
        client=path.split("/")[5],
        brand=path.split("/")[7],
        path=path,
        public=public,
        claim=claim,
        source=src,
        private=private,
        markers=[*markers, private["id"], bound["id"]],
    )


def open_desk(page, actor, tenant, client, brand):
    login(page, actor, tenant)
    select_scope(page, client, brand)
    page.get_by_role("button", name="Nguồn và nhận định", exact=True).click()
    desk = page.locator("#knowledge-claim-desk")
    expect(desk.get_by_label("Chọn nhận định")).to_be_visible()
    return desk


def ensure_private_state(page, markers, observed):
    assert observed and all(not any(m in body for m in markers) for body in observed)
    state = page.evaluate("""() => [document.documentElement.outerHTML,JSON.stringify(localStorage),JSON.stringify(sessionStorage),
                                 JSON.stringify(history.state),document.cookie,location.href].join(' ' )""")
    assert not any(m in state for m in markers)
    # Inspect Chromium's retained JS heap without sending canaries into the page,
    # writing a heap dump, or recording any private response as an artifact.
    cdp = page.context.new_cdp_session(page)
    tail = ""
    leaked = False
    overlap = max(map(len, markers))

    def scan(event):
        nonlocal tail, leaked
        piece = tail + event["chunk"]
        leaked |= any(m in piece for m in markers)
        tail = piece[-overlap:]

    try:
        cdp.on("HeapProfiler.addHeapSnapshotChunk", scan)
        cdp.send("HeapProfiler.takeHeapSnapshot", {"reportProgress": False})
    finally:
        cdp.detach()
    assert not leaked, "A restricted evidence marker was retained in the editor's JS heap"


def exercise(browser, api, width, height):
    fixture_data = fixture(api)
    f = fixture_data
    editor_page = browser.new_page(viewport={"width": width, "height": height})
    bodies = []

    def observe(response):
        if "/knowledge/" in response.url and response.request.resource_type == "fetch":
            bodies.append(response.text())

    editor_page.on("response", observe)
    try:
        desk = open_desk(editor_page, f["editor"], f["tenant"], f["client"], f["brand"])
        desk.get_by_label("Chọn nhận định").select_option(f["claim"]["id"])
        expect(desk).to_contain_text("Matte surface")
        expect(desk).to_contain_text("Chi tiết bằng chứng nằm ngoài phạm vi hiển thị")
        expect(desk.get_by_text("Tile · Vietnam · HN · vi-VN · web", exact=True)).to_be_visible()
        ensure_private_state(editor_page, f["markers"], bodies)
        capture = os.getenv("AMC_CLAIM_SCREENSHOTS")
        if capture:
            out = Path(capture)
            out.mkdir(parents=True, exist_ok=True)
            desk.scroll_into_view_if_needed()
            editor_page.screenshot(path=str(out / f"claim-editor-{width}.png"))

        manager = browser.new_page(viewport={"width": width, "height": height})
        try:
            view = open_desk(manager, f["owner"], f["tenant"], f["client"], f["brand"])
            view.get_by_label("Nguồn chứng cứ").select_option(f["source"]["id"])
            view.get_by_label("Vị trí trong nguồn").select_option("row 2")
            expect(view.get_by_label("Câu dùng cho Marketing")).to_have_value("Matte surface")
            view.get_by_label("Điều kiện kèm theo, mỗi dòng một điều kiện").fill("Not in the selected source")
            view.get_by_role("button", name="Lưu bản nháp", exact=True).click()
            expect(manager.locator("#knowledge-status")).to_contain_text("Đối chiếu")
            view.get_by_label("Điều kiện kèm theo, mỗi dòng một điều kiện").fill("")
            if width == 1280:
                commits = drop_after_commit(manager, "claim-desk/drafts")
                with manager.expect_request_failed(lambda req: req.url.endswith("/claim-desk/drafts")):
                    view.get_by_role("button", name="Lưu bản nháp", exact=True).click()
                assert len(commits) == 1
                manager.unroute("**/claim-desk/drafts")
                view = open_desk(manager, f["owner"], f["tenant"], f["client"], f["brand"])
                expect(manager.locator("#knowledge-status")).to_contain_text("Đã tìm thấy kết quả lưu")
                expect(view.get_by_label("Chọn nhận định")).to_have_value(commits[0]["id"])
            else:
                view.get_by_role("button", name="Lưu bản nháp", exact=True).click()
                expect(manager.locator("#knowledge-status")).to_contain_text("Đã lưu bản nháp")
            for heading in ("Xác nhận đối chiếu nguồn", "Duyệt nhận định"):
                section = view.locator("section").filter(has=manager.get_by_role("heading", name=heading, exact=True))
                section.get_by_label("Quyết định", exact=True).select_option("approved")
                section.get_by_label("Lý do quyết định").fill("Đã đối chiếu với nguồn tổng hợp")
                section.get_by_role("button", name="Ghi quyết định").click()
                expect(manager.locator("#knowledge-status")).to_contain_text("Đã ghi quyết định")
            expect(view.get_by_role("heading", name="Lịch sử")).to_be_visible()
            if capture:
                view.scroll_into_view_if_needed()
                manager.screenshot(path=str(out / f"claim-review-{width}.png"))
        finally:
            manager.close()

        private = f["private"]
        accepted(
            call(
                api,
                f["owner"],
                f["path"],
                "/revisions/" + private["id"] + "/events",
                state="disputed",
                expected_sequence=1,
                expected_digest=private["digest"],
                reason="Source pending verification",
            )
        )
        desk.get_by_role("button", name="Kiểm tra lại hiệu lực").click()
        expect(desk).to_contain_text("Chưa đủ điều kiện dùng câu này")
        ensure_private_state(editor_page, f["markers"], bodies)
        assert editor_page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        print(
            f"PASS claim desk {width}px: source selection, qualifier mismatch, approval, dispute invalidation and editor response/DOM/storage/JS heap privacy"
        )
    finally:
        editor_page.close()


if __name__ == "__main__":
    assert urlsplit(BASE).hostname in ("127.0.0.1", "localhost")
    with httpx.Client(base_url=BASE, timeout=20, trust_env=False) as api, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for width, height in ((1280, 850), (390, 844)):
                exercise(browser, api, width, height)
        finally:
            browser.close()
