"""Chromium over a real localhost API and a disposable SQLite database with a synthetic C3 draft.

Run explicitly in a browser job. The separate published-pool API and model jobs cover PostgreSQL
and actual inference. No browser response is intercepted or synthesized.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import threading
import time
from uuid import uuid4

from c3_browser_themes import capture_themes
from playwright.sync_api import expect, sync_playwright
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
import uvicorn

from app.database import Base, get_db
from app.main import app
from identity_fixtures import invite_member, start_registration, verify_registration
from knowledge_fixtures import revision
from test_c3_content_gate import content_lab as evidence_fixture, submit_copy
from test_workforce import workforce as workforce_fixture

content_lab = evidence_fixture
workforce = workforce_fixture


@pytest.fixture
def client(tmp_path):
    # A browser requests independent panels concurrently. Give each request its own connection.
    db = create_engine("sqlite:///" + (tmp_path / "knowledge.sqlite").as_posix(), connect_args={"check_same_thread": False, "timeout": 20})

    @event.listens_for(db, "connect")
    def configure(conn, _):
        conn.execute("pragma foreign_keys=on")
        conn.execute("pragma journal_mode=wal")

    Base.metadata.create_all(db)

    def dependency():
        with Session(db) as session:
            yield session

    app.dependency_overrides[get_db] = dependency
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db)
        db.dispose()


@contextmanager
def local_api():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        # Chromium can close a media connection while the Windows event loop
        # still has its transport queued. Bound the disposable server's drain.
        service = uvicorn.Server(
            uvicorn.Config(app, log_level="error", access_log=False, proxy_headers=False, timeout_graceful_shutdown=4)
        )
        thread = threading.Thread(target=service.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            for _ in range(200):
                if service.started:
                    break
                time.sleep(0.025)
            assert service.started
            yield f"http://127.0.0.1:{sock.getsockname()[1]}"
        finally:
            service.should_exit = True
            thread.join(10)
            assert not thread.is_alive()


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_content_gate_browser(api, content_lab):
    owner, _, editor, path, data, snap = content_lab
    base = path.split("/deliverables/")[0]
    email, password = f"content-{uuid4().hex}@example.com", uuid4().hex
    qa = start_registration(api, email, password, organization_name="Synthetic Marketing qualification", mode="agency")
    verify_registration(api, email, qa)
    invite_member(api, base, owner["headers"], {"Authorization": "Bearer " + qa["access_token"]}, email=email, role="admin")
    revision(
        api,
        owner,
        data["path"],
        "browser-qualification",
        "qualification",
        {"approver_id": qa["user_id"], "category": "unclassified", "basis": "Synthetic materials reviewer", "valid_until": "2099-01-01T00:00:00Z"},
        visibility="restricted",
    )
    handle = next(f["id"] for f in snap["projection"]["facts"] if f["wording"] == "Matte surface")
    text = f"[{handle}] A matte finish for this sample — Indoor use only\nGiảm giá 25%."
    out = Path(os.getenv("AMC_KNOWLEDGE_EVIDENCE", "knowledge-browser-evidence")) / "content-evidence"
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with local_api() as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for width, height in ((1280, 850), (820, 1180), (390, 844)):
                terms = submit_copy(api, path, editor, text)
                page = browser.new_page(viewport={"width": width, "height": height})
                try:
                    page.goto(origin + "/?workspace=" + owner["tenant"] + "#/reviews")
                    login = page.locator("#login-form")
                    login.get_by_label("Email").fill(email)
                    login.get_by_label("Mật khẩu").fill(password)
                    login.get_by_role("button").click()
                    expect(page.locator("#workspace")).to_be_visible()
                    page.evaluate("location.hash='/reviews'")
                    pane = page.locator("#review-panel")
                    pane.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
                    pane.get_by_label("Bản làm việc").select_option(path.rsplit("/", 1)[1])
                    pane.get_by_text("Đối chiếu nội dung với bằng chứng", exact=True).click()
                    semantic = pane.locator(".claim-comparison").filter(has_text="A matte finish").first
                    expect(semantic.get_by_text("private locator", exact=False)).to_be_visible()
                    expect(pane.get_by_text("Cần sửa nội dung", exact=True)).to_be_visible()
                    expect(semantic.get_by_role("heading", name="Cần chuyên gia xác minh")).to_be_visible()
                    semantic.scroll_into_view_if_needed()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    capture_themes(page, out / f"claims-{width}.png")
                    semantic.get_by_label("Nguồn chứng minh nhận định").select_option(handle)
                    semantic.get_by_label("Giải thích nguồn hỗ trợ câu này như thế nào").fill(
                        "Compared finish and indoor use qualifier with the signed sample."
                    )
                    semantic.get_by_role("button", name="Ghi quyết định xác minh").click()
                    expect(pane.get_by_role("heading", name="Chuyên gia đã xác minh")).to_be_visible()
                    pane.get_by_role("button", name="QA duyệt", exact=True).click()
                    expect(page.locator("#notice")).to_contain_text("Chưa thể duyệt")
                    pane.get_by_text("Lịch sử phiên bản và quyết định", exact=True).click()
                    expect(pane.get_by_text("Xác minh nhận định · lần lưu " + str(terms["expected_qa_revision"]), exact=False)).to_be_visible()
                    results.append(
                        {
                            "width": width,
                            "height": height,
                            "revision": terms["expected_qa_revision"],
                            "semantic": "reviewed",
                            "contradiction": "approval_refused",
                        }
                    )
                finally:
                    page.close()
            (out / "acceptance.json").write_text(
                json.dumps({"browser": browser.version, "database": "disposable SQLite", "runs": results}, indent=2), encoding="utf8"
            )
        finally:
            browser.close()
