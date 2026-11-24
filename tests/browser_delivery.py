"""Browser acceptance against a disposable local server. Run outside pytest."""

import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright


def exercise():
    origin = os.environ["AMC_BROWSER_TEST_URL"]
    assert urlsplit(origin).hostname in ("localhost", "127.0.0.1")
    with httpx.Client(base_url=origin, timeout=15, trust_env=False) as api, sync_playwright() as pw:

        def post(path, body, token=None):
            headers = {"Authorization": "Bearer " + token} if token else {}
            res = api.post(path, json=body, headers=headers)
            assert res.is_success, (path, res.status_code)
            return res.json()

        def user(label):
            email, password = f"{label}-{uuid4().hex}@example.com", uuid4().hex
            reg = post("/api/auth/register", dict(email=email, password=password, organization_name=label, mode="agency"))
            return reg["access_token"], reg["tenant_id"], reg["user_id"], email, password

        token, tenant, _, admin_email, admin_password = user("Agency")
        edit, _, _, editor_email, editor_password = user("Editor")
        _, _, uid, email, password = user("Reader")
        base = "/api/tenants/" + tenant
        client = post(base + "/clients", {"name": "UI Client"}, token)
        brand = post(base + "/brands", {"client_id": client["id"], "name": "UI Brand", "product_truth":"Blue A5 notebook"}, token)
        camp = post(
            base + "/campaigns", {"brand_id": brand["id"], "name": "UI campaign", "brief": "Synthetic brief for QA", "objective": "Review content"}, token
        )
        post(base + "/members", dict(email=editor_email, role="editor"), token)
        post(base + "/members", dict(email=email, role="client_viewer", client_id=client["id"]), token)
        assert (
            api.put(
                base + f"/members/{uid}/review-rights", headers={"Authorization": "Bearer " + token}, json={"can_comment": True, "can_decide": True}
            ).status_code
            == 200
        )

        def share(title, seconds=1800):
            draft = post(
                base + "/deliverables",
                dict(campaign_id=camp["id"], title=title, content={"client_preview": "Exact customer preview", "secret_ref": "internal-only-canary"}),
                edit,
            )
            path = base + "/deliverables/" + draft["id"]
            post(path + "/submit", {}, edit)
            post(path + "/review", {"decision": "approved", "note": "internal QA", "expected_qa_revision": draft["qa_evidence"]["qa_revision"], "expected_content_digest": draft["qa_evidence"]["content_digest"]}, token)
            return post(path + "/share", {"expires_at": (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()}, token)

        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for width, height in [(1280, 850), (390, 844)]:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(origin + "/?workspace=" + tenant)
                form = page.locator("#login-form")
                form.locator('[name="email"]').fill(email)
                form.locator('[name="password"]').fill(password)
                form.locator("button").click()
                pane = page.locator("#review-panel")
                expect(pane.get_by_role("heading", name="Bàn giao và duyệt nội dung")).to_be_visible()
                expect(page.locator("#operations-panel")).to_be_hidden()
                if width == 1280:
                    expect(pane.get_by_text("Chưa có phiên bản nào được chia sẻ.")).to_be_visible()
                title = f"Brief {width}"
                share(title)
                page.locator("#refresh").click()
                pane.get_by_role("button", name=title + " · v1 · Chờ khách duyệt").click()
                expect(pane.locator("pre")).to_have_text("Exact customer preview")
                assert "internal-only-canary" not in pane.inner_text()
                pane.get_by_label("Ý kiến của bạn").fill("Bản này đã đúng brief")
                pane.get_by_role("button", name="Gửi bình luận").click()
                expect(pane.get_by_text("Bản này đã đúng brief", exact=False)).to_be_visible()
                pane.get_by_role("button", name="Duyệt phiên bản này").click()
                expect(pane.get_by_role("button", name=title + " · v1 · Khách đã duyệt")).to_be_visible()
                # Element identifiers help diagnose font-dependent wrapping on Linux and Windows.
                overflow = page.evaluate("""() => Array.from(document.querySelectorAll('body *'))
                    .filter(el => el.getBoundingClientRect().right > innerWidth + 0.5)
                    .map(el => [el.tagName, el.id, el.className])""")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), overflow
                page.route("**/reviews", lambda route: route.fulfill(status=503, body="unavailable"))
                page.locator("#refresh").click()
                expect(pane.get_by_text("Không tải được danh sách bản bàn giao.")).to_be_visible()
                page.unroute("**/reviews")
                pane.get_by_role("button", name="Thử lại").click()
                expect(pane.get_by_role("button", name=title + " · v1 · Khách đã duyệt")).to_be_visible()
                expired_title = f"Deadline {width}"
                share(expired_title, 2)
                time.sleep(2.1)
                page.locator("#refresh").click()
                pane.get_by_role("button", name=expired_title + " · v1 · Đã hết hạn").click()
                expect(pane.locator("pre")).to_be_visible()
                expect(pane.get_by_role("button", name="Duyệt phiên bản này")).to_have_count(0)
                page.goto(origin + "/?workspace=" + tenant + "&review=missing")
                form.locator('[name="email"]').fill(email)
                form.locator('[name="password"]').fill(password)
                form.locator("button").click()
                expect(pane.get_by_text("Không mở được bản bàn giao.", exact=False)).to_be_visible()
                print(f"PASS browser {width}x{height}: exact preview, comment, approval, retry, expiry, missing link")
                page.close()

            def login_page(email_address, passphrase, viewport):
                page = browser.new_page(viewport=viewport)
                page.goto(origin)
                form = page.locator("#login-form")
                form.locator('[name="email"]').fill(email_address)
                form.locator('[name="password"]').fill(passphrase)
                form.locator("button").click()
                return page

            for width, height in [(1280, 850), (390, 844)]:
                draft = post(
                    base + "/deliverables", {"title": "Initial price", "campaign_id": camp["id"], "content": {"client_preview": "Giá phải chăng."}}, edit
                )
                doc_path = base + "/deliverables/" + draft["id"]
                editor_page = login_page(editor_email, editor_password, {"width": width, "height": height})
                editor_page.locator("#workspace-select").select_option(tenant)
                form = editor_page.locator("#review-panel")
                form.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
                form.get_by_label("Bản làm việc").select_option(draft["id"])
                submit = form.get_by_role("button", name="Gửi QA", exact=True)
                title = form.get_by_label("Tiêu đề gửi khách")
                preview = form.get_by_label("Nội dung khách sẽ xem")
                title.fill("Unsaved title")
                expect(submit).to_be_disabled()
                expect(form.get_by_text("Hãy lưu thay đổi", exact=False)).to_be_visible()
                title.fill(draft["title"])
                expect(submit).to_be_enabled()
                preview.fill("Giá phải chăng. Nội dung bổ sung.")
                expect(submit).to_be_disabled()
                form.get_by_role("button", name="Lưu bản sửa").click()
                expect(submit).to_be_enabled()
                submit.click()
                expect(submit).to_have_count(0)
                editor_page.close()
                qa_page = login_page(admin_email, admin_password, {"width": width, "height": height})
                ops = qa_page.locator("#operations-panel")
                expect(ops).to_be_visible()
                ops.get_by_role("button", name="Cập nhật số liệu").click()
                expect(ops.get_by_text("Đang giữ (micro-USD)")).to_be_visible()
                assert ops.evaluate("(e) => e.scrollWidth <= e.clientWidth + 1")
                pane = qa_page.locator("#review-panel")
                pane.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
                pane.get_by_label("Bản làm việc").select_option(draft["id"])
                expect(pane.get_by_text("Cần bổ sung bằng chứng · Nội dung · Giá phải chăng.")).to_be_visible()
                expect(pane.get_by_text("Chưa có nguồn liên kết để đối chiếu.")).to_be_visible()
                api.patch(
                    doc_path + "/draft", headers={"Authorization": "Bearer " + edit}, json={"title": "Revised", "client_preview": "The best."}
                ).raise_for_status()
                revised = post(doc_path + "/submit", {}, edit)
                pane.get_by_role("button", name="QA duyệt", exact=True).click()
                expect(qa_page.locator("#notice")).to_contain_text("Hãy tải lại")
                qa_page.locator("#refresh").click()
                expect(pane.get_by_text("Cần bổ sung bằng chứng · Nội dung · The best.")).to_be_visible()
                expect(pane.get_by_text("Giá phải chăng.", exact=False)).to_have_count(0)
                expect(pane.get_by_text("SHA-256 " + revised["qa_evidence"]["content_digest"][:12], exact=False)).to_be_visible()
                for copy in ("Temporary revision.", "The best."):
                    api.patch(
                        doc_path + "/draft", headers={"Authorization": "Bearer " + edit}, json={"title": "Revised", "client_preview": copy}
                    ).raise_for_status()
                restored = post(doc_path + "/submit", {}, edit)
                assert restored["qa_evidence"]["content_digest"] == revised["qa_evidence"]["content_digest"]
                with qa_page.expect_response(lambda r: r.url.endswith(doc_path + "/review")) as decision:
                    pane.get_by_role("button", name="QA duyệt", exact=True).click()
                assert decision.value.status == 412
                qa_page.locator("#refresh").click()
                expect(pane.get_by_text(f"Lần lưu {restored['qa_revision']} ·", exact=False)).to_be_visible()
                pane.get_by_role("button", name="QA duyệt", exact=True).click()
                expect(pane.get_by_role("button", name="Chia sẻ phiên bản đã duyệt")).to_be_visible()
                qa_page.close()
                print(
                    f"PASS browser {width}x{height}: unsaved edits blocked, revision-specific findings, A-B-A stale decision refused and fresh decision accepted"
                )

            invite_token, _, invite_id, invited_email, invited_password = user("InvitedReviewer")
            api.put(base+"/operations/budget",headers={"Authorization":"Bearer "+token},json={"enabled":True,"ceiling":1000,"capacity":2}).raise_for_status()
            owner_page = login_page(admin_email, admin_password, {"width": 1280, "height": 850})
            admin_panel = owner_page.locator("#recipient-panel")
            admin_panel.get_by_text("Quản lý người nhận và lời mời", exact=True).click()
            invitation_form = admin_panel.locator("form")
            invitation_form.get_by_label("Email tài khoản đã đăng ký").fill(invited_email)
            invitation_form.get_by_label("Khách hàng", exact=True).select_option(client["id"])
            invitation_form.get_by_label("Thương hiệu", exact=True).select_option(brand["id"])
            invitation_form.get_by_label("Cho phép duyệt, từ chối hoặc yêu cầu sửa").check()
            invitation_form.get_by_role("button", name="Tạo lời mời trong ứng dụng").click()
            expect(admin_panel.get_by_text(invited_email.lower(), exact=False)).to_be_visible()
            reader = login_page(invited_email, invited_password, {"width":390,"height":844})
            reader.get_by_role("button", name="Chấp nhận lời mời").click()
            expect(reader.locator("#workspace-select")).to_have_value(tenant)
            expect(reader.get_by_text("Quản lý người nhận và lời mời", exact=True)).to_have_count(0)
            # Fresh grant now exists. Request the brief from the named recipient only.
            owner_page.locator("#refresh").click()
            ops = owner_page.locator("#workforce-panel")
            expect(ops.get_by_label("Người giao brief").locator("option").filter(has_text=invited_email.lower())).to_have_count(1)
            ops.get_by_text("Điều phối Marketing AI", exact=True).click()
            ops.get_by_label("Tên bộ tài sản").fill("Notebook launch")
            ops.get_by_label("Chiến dịch nhận brief").select_option(camp["id"])
            ops.get_by_label("Người giao brief").select_option(label=invited_email.lower())
            ops.get_by_role("button",name="Yêu cầu khách gửi brief").click()
            expect(ops.get_by_text("Notebook launch · Chờ brief")).to_be_visible()
            reader.locator("#refresh").click()
            intake = reader.locator("#workforce-panel")
            intake.get_by_text("Brief Marketing của bạn").click()
            intake.get_by_text("Notebook launch · Chờ brief").click()
            for name,value in [("Mục tiêu","Launch our notebook"),("Khách hàng mục tiêu","Students"),("Sản phẩm và đề nghị","A5 notebook"),
                               ("Tên nguồn","Brand card"),("Trích dẫn từ nguồn","Notebook with blue cover")]:
                intake.get_by_label(name,exact=True).fill(value)
            intake.get_by_role("button",name="Gửi brief").click()
            expect(intake.get_by_text("Notebook launch · Đã nhận brief")).to_be_visible()
            ops.get_by_role("button",name="Cập nhật tiến độ").click()
            ops.get_by_text("Notebook launch · Đã nhận brief").click()
            ops.get_by_role("button",name="Giao việc cho AI Director").click()
            expect(ops.get_by_text("Notebook launch · Đang chờ worker")).to_be_visible()
            print("PASS browser: named client submitted sourced brief; agency queued local inference")
            registry = "WF-13/landing-seo-draft@1"
            api.put(base+"/workforce/registry/"+camp["id"],headers={"Authorization":"Bearer "+token},
                    json={"workflow":registry,"action":"activate","skills":["director","content","seo"]}).raise_for_status()
            research_workflow="WF-03/research-strategy-draft@1"
            api.put(base+"/workforce/registry/"+camp["id"],headers={"Authorization":"Bearer "+token},
                    json={"workflow":research_workflow,"action":"activate","skills":["director","research","strategy"]}).raise_for_status()
            for template,title in ((research_workflow,"Research browser"),("diamond-v1","Diamond browser"),("dynamic-v1","Dynamic browser"),(registry,"Registry browser")):
                dag_brief=post(base+"/workforce/briefs",{"title":title,"campaign_id":camp["id"],"recipient_id":invite_id},token)
                api.put(base+"/workforce/briefs/"+dag_brief["id"]+"/submission",headers={"Authorization":"Bearer "+invite_token},
                        json={"objective":"Visit the store","audience":"University students","offer":"Notebook for students",
                              "sources":[{"label":"Brand card","excerpt":"A5 blue notebook"}]}).raise_for_status()
                owner_page.locator("#refresh").click()
                panel=owner_page.locator("#workforce-panel")
                panel.get_by_text(title+" · Đã nhận brief").click()
                brief_form=panel.get_by_text(title+" · Đã nhận brief",exact=True).locator("..")
                brief_form.get_by_label("Mẫu workflow").select_option(template)
                if template != "diamond-v1":
                    brief_form.get_by_label("Số node tối đa cùng chạy").select_option("2")
                brief_form.get_by_role("button",name="Giao việc cho AI Director").click()
                card=panel.get_by_role("heading",name=title+" · Đang chờ worker").locator("..")
                card.get_by_role("button",name="Xem kết quả và chi phí").click()
                for width,height in ((1280,850),(390,844)):
                    owner_page.set_viewport_size({"width":width,"height":height})
                    graph=card.get_by_role("region",name="Trạng thái workflow")
                    expect(graph.get_by_text("Mẫu "+("dynamic-v1" if "@" in template else template)+" · Phiên bản 1")).to_be_visible()
                    expect(graph.locator('[data-node="director"]')).to_contain_text("Sẵn sàng")
                    if template == "diamond-v1":
                        expect(graph.locator('[data-node="join"]')).to_contain_text("Content, SEO")
                    else:
                        expect(graph.get_by_text("Đang lập kế hoạch",exact=True)).to_be_visible()
                        expect(graph.get_by_text("Tối đa 2 node đồng thời",exact=True)).to_be_visible()
                        expect(graph.locator("li")).to_have_count(1)
                    if "@" in template:
                        expect(graph.get_by_text(template+" · Manifest",exact=False)).to_be_visible()
                    card.get_by_role("button",name="Xem lý do node chờ").click()
                    expect(card.get_by_text("Chưa đủ dữ liệu từ các replica",exact=True).first).to_be_visible()
                    expect(card.get_by_text("Thời điểm quan sát",exact=False)).to_be_visible()
                    assert graph.evaluate("(e) => e.scrollWidth <= e.clientWidth + 1")
                print(f"PASS {template} graph in Chromium at 1280px and 390px")
                if template == registry:
                    # The API suite covers real guarded commits. Inject one labelled report here
                    # to check its presentation at both widths without requiring a model in this job.
                    pattern = "**/workforce/runs/*"
                    def with_role_finding(route):
                        response = route.fetch()
                        data = response.json()
                        data["checkpoints"] = [{"skill":"content","output":{"text":"Student notebook","source_ids":["brand"]},
                            "quality":{"numbers_for_qa":[],"role_qa":{"scope":"node_checkpoint","node_id":"n01",
                            "policy":"content-qa@2","output_digest":"a"*64,"findings":[{"field":"call_to_action",
                            "rule_id":"cta_action","rule_version":2,"severity":"warning","source_ids":["brand"],
                            "evidence":{"text":"Student notebook"}}]}}}]
                        route.fulfill(response=response, json=data)
                    owner_page.route(pattern, with_role_finding)
                    try:
                        card.get_by_role("button",name="Xem kết quả và chi phí").click()
                        for width,height in ((1280,850),(390,844)):
                            owner_page.set_viewport_size({"width":width,"height":height})
                            expect(card.get_by_text("QA đầu ra AI · n01 · content-qa@2")).to_be_visible()
                            finding=card.get_by_text("call_to_action · Kiểm tra lời kêu gọi hành động",exact=True)
                            finding.click()
                            expect(card.get_by_text("Cần kiểm tra · cta_action@2")).to_be_visible()
                            expect(card.get_by_text("Nguồn đã dẫn: brand")).to_be_visible()
                            finding.click()
                        print("PASS original checkpoint QA finding and evidence in Chromium at 1280px and 390px")
                    finally:
                        owner_page.unroute(pattern, with_role_finding)

            first = share("Review operations")
            for n in range(25):
                share(f"Later {n}")
            reader.locator("#refresh").click()
            portal = reader.locator("#review-panel")
            target = portal.get_by_role("button", name="Review operations · v1 · Chờ khách duyệt")
            expect(target).to_have_count(0)
            portal.get_by_role("button", name="Xem thêm bản bàn giao").click()
            target.click()
            portal.get_by_role("button", name="Yêu cầu sửa").click()
            expect(reader.locator("#notice")).to_contain_text("lý do")
            portal.get_by_label("Ý kiến của bạn").fill("Vui lòng sửa tên sản phẩm")
            portal.get_by_role("button", name="Yêu cầu sửa").click()
            expect(portal.get_by_text("Vui lòng sửa tên sản phẩm", exact=False)).to_be_visible()
            result = api.get(base+"/reviews/"+first["id"],headers={"Authorization":"Bearer "+token}).json()
            assert result["status"] == "changes_requested"
            # Refresh replaces recipient rows asynchronously. Open the newly rendered row.
            old_panel = admin_panel.locator(":scope > details").element_handle()
            owner_page.locator("#refresh").click()
            owner_page.wait_for_function("(old) => !old.isConnected", arg=old_panel)
            row = admin_panel.locator("details details").filter(has_text=invited_email.lower())
            expect(row.locator("summary")).to_be_visible()
            row.locator("summary").click()
            row.get_by_label("Cho phép duyệt, từ chối hoặc yêu cầu sửa").uncheck()
            row.get_by_label("Cho phép bình luận").check()
            row.get_by_role("button", name="Lưu quyền").click()
            expect(row).not_to_have_attribute("open", "")
            row.locator("summary").click()
            expect(row.get_by_label("Cho phép bình luận")).to_be_checked()
            expect(row.get_by_label("Cho phép duyệt, từ chối hoặc yêu cầu sửa")).not_to_be_checked()
            owner_page.once("dialog", lambda dialog: dialog.accept())
            row.get_by_role("button", name="Thu hồi quyền xem").click()
            expect(row).to_have_count(0)
            reader.locator("#refresh").click()
            expect(reader.locator("#review-panel")).to_be_empty()
            reader.close()
            owner_page.close()
            print("PASS browser: invite, accept, paginate, reason, grant edit and revoke with existing session")
        finally:
            browser.close()


if __name__ == "__main__":
    exercise()
