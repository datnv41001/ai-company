"""Propose, approve and operate two different customer campaigns through the normal web UI."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright
import pytest

from agency_fixtures import agency, api  # noqa: F401 -- genuine, separated clients
from browser_c3_content_gate import client, local_api  # noqa: F401 -- file-backed browser database
from campaign_planner_fixtures import CASES, prepare_inputs
from knowledge_fixtures import accepted
from app import c3_assets
from c3_browser_themes import capture_themes


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_campaign_commands_and_scope_switch(api, agency):  # noqa: F811
    owner, base, members = agency
    campaigns = accepted(api.get(base + "/campaigns", headers=owner["headers"]))
    ids = []
    for (customer, scope), case in zip(members, CASES, strict=True):
        cid = next(iter(scope["campaigns"]))
        brand = next(c["brand_id"] for c in campaigns if c["id"] == cid)
        prepare_inputs(api, owner, customer, next(iter(scope["clients"])), brand, cid, case)
        ids.append(cid)
    with local_api() as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            page = browser.new_page(viewport={"width": 820, "height": 1180})
            page.goto(origin + "/?workspace=" + owner["tenant"] + "#/campaigns")
            login = page.locator("#login-form")
            login.get_by_label("Email").fill(owner["email"])
            login.get_by_label("Mật khẩu").fill(owner["password"])
            login.get_by_role("button").click()
            panel = page.locator("#campaign-engine")
            campaign = panel.locator("#engine-select")
            for cid, case in zip(ids, CASES, strict=True):
                campaign.select_option(cid)
                panel.get_by_text("Lập kế hoạch từ hồ sơ đã duyệt", exact=True).click()
                form = panel.locator("form").filter(has=page.get_by_role("button", name="Lưu đề xuất"))
                checks = form.get_by_role("checkbox")
                expect(checks).to_have_count(2)
                for check in checks.all():
                    check.check()
                form.get_by_label("Kết quả mong muốn").fill(case["kpi"])
                form.get_by_role("button").click()
                panel.get_by_text("Xem bản chờ duyệt v1", exact=True).click()
                panel.get_by_role("button", name="Duyệt phiên bản 1").click()
                panel.get_by_text("Ghi nhận yêu cầu báo giá", exact=True).click()
                intake = panel.locator("form").filter(has=page.get_by_role("button", name="Ghi nhận RFQ sandbox"))
                intake.get_by_label("Mã yêu cầu").fill("rfq-" + case["id"])
                intake.get_by_label("Số lượng", exact=False).fill("3")
                intake.get_by_label("Địa bàn giao").fill("Khu tổng hợp")
                intake.get_by_label("Ngày cần hàng").fill("2027-04-25")
                intake.get_by_label("Mục đích liên hệ do khách chọn").select_option("quote_request")
                intake.get_by_role("button").click()
                expect(panel.locator("summary").filter(has_text="rfq-" + case["id"])).to_contain_text("Đủ điều kiện")
                expect(panel.locator(".metric").filter(has_text="Yêu cầu báo giá sandbox").locator("strong")).to_have_text("1")
            expect(panel).not_to_contain_text("rfq-" + CASES[0]["id"])
            campaign.select_option(ids[0])
            expect(panel.locator("summary").filter(has_text="rfq-" + CASES[0]["id"])).to_be_attached()
            expect(panel).not_to_contain_text("rfq-" + CASES[1]["id"])
        finally:
            browser.close()


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_pending_plan_and_settlement_from_previous_revision(api, agency, tmp_path):  # noqa: F811
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.campaign_operations import append, entries
    from app.campaign_planner import campaign_store
    from app.models import User

    owner, base, ((customer, scope), _) = agency
    cid = next(iter(scope["campaigns"]))
    campaign = next(c for c in accepted(api.get(base + "/campaigns", headers=owner["headers"])) if c["id"] == cid)
    case = CASES[0]
    snaps, _ = prepare_inputs(api, owner, customer, next(iter(scope["clients"])), campaign["brand_id"], cid, case)
    root = base + "/campaigns/" + cid
    def propose(workflow, rev, days):
        snap = next(s for s in snaps if s["workflow"] == workflow)
        return accepted(api.post(root + "/engine/plans", headers=owner["headers"], json={
            "expected_revision":rev,"key":uuid4().hex,"duration_days":days,"budget_vnd":50000,"target_outcome":case["kpi"],
            "manifest_ids":[snap["id"]],
        }))
    first = propose(c3_assets.LANDING, 0, 14)
    accepted(api.post(root + "/engine/plans/" + first["id"] + "/approve", headers=owner["headers"],
                      json={"key":uuid4().hex,"expected_digest":first["digest"]}))
    when = datetime.now(timezone.utc)
    def event(kind, **values):
        return accepted(api.post(root + "/sandbox/commands", headers=owner["headers"], json={
            "kind":kind, "request_id":uuid4().hex,"plan_id":first["id"],"occurred_at":when.isoformat(), **values,
        }))
    rfq = "historical-rfq"
    event("rfq",rfq_id=rfq,product_id=first["product_id"],unit=first["selling_unit"],quantity="3",
          location="Synthetic depot",required_date=(when.date()+timedelta(days=8)).isoformat(),contact_purpose="quote_request")
    for rev,(step,fields) in enumerate((("assign",{"assignee_id":owner["id"]}),("accept",{"reason":"Synthetic complete request"}),
                                         ("quote",{}),("order",{}),("confirm",{"amount_vnd":90000})), start=1):
        event("sales",rfq_id=rfq,expected_revision=rev,step=step,**fields)
    # The model journey covers creation from signed C3 deliverables. This fixture specifically exercises
    # cancelling persisted legacy work in the UI, so seed one outstanding schedule without running a model here.
    db_engine = create_engine("sqlite:///" + (tmp_path / "knowledge.sqlite").as_posix())
    action_id = "historical-schedule"
    try:
        with Session(db_engine) as db:
            store = campaign_store(db, db.get(User,owner["id"]), owner["tenant"], cid, write=True)
            value = {"id":action_id,"plan_id":first["id"],"plan_digest":first["digest"],"state":"scheduled",
                     "scheduled_by":owner["id"],"cost_vnd":20000,"due_at":when.isoformat(), "attempts":0}
            append(store,cid,first["id"],"schedule","actions",action_id,value,len(entries(store,cid))+1,
                   "browser-fixture-"+uuid4().hex,"c"*64)
            db.commit()
    finally:
        db_engine.dispose()
    second = propose(c3_assets.RESEARCH, 1, 37)
    with local_api() as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            page = browser.new_page(viewport={"width":850,"height":1150})
            page.goto(origin + "/?workspace=" + owner["tenant"] + "#/campaigns")
            login = page.locator("#login-form")
            login.get_by_label("Email").fill(owner["email"])
            login.get_by_label("Mật khẩu").fill(owner["password"])
            login.get_by_role("button").click()
            panel = page.locator("#campaign-engine")
            panel.locator("#engine-select").select_option(cid)
            pending = panel.locator("details").filter(has=page.get_by_role("button",name="Duyệt phiên bản 2",include_hidden=True))
            pending.locator(":scope > summary").click()
            ref = second["manifests"]["strategy"]
            for value in (second["product"],second["audience"],second["objective"],second["measurement_plan"]["kpi"],
                          "37 ngày",ref["brief_id"],ref["id"],ref["digest"],second["digest"],*[pkg["criteria"] for pkg in second["work_packages"]]):
                expect(pending).to_contain_text(value)
            expect(pending).not_to_contain_text(first["manifests"]["landing"]["brief_id"])
            pending.get_by_role("button",name="Duyệt phiên bản 2").click()
            expect(panel.locator(".metric").filter(has_text="Kế hoạch được duyệt")).to_contain_text("v2")
            lead = panel.locator("details").filter(has=page.locator("summary").filter(has_text=rfq))
            lead.locator(":scope > summary").click()
            lead.get_by_label("Bước Sales").select_option("refund")
            lead.get_by_label("Phản hồi của Sales").fill("Đối soát đơn thử đã xác nhận ở phiên bản trước")
            lead.get_by_label("Số tiền khi xác nhận").fill("30000")
            lead.get_by_role("button",name="Lưu quyết định Sales").click()
            expect(panel.locator(".engine-row").filter(has_text="Doanh thu sau điều chỉnh")).to_contain_text("60.000")
            action = panel.locator(".engine-row").filter(has_text=action_id)
            expect(action.get_by_role("button", name="Cho phép chạy")).to_have_count(0)
            action.get_by_role("button",name="Hủy lịch").click()
            expect(action).to_contain_text("Đã hủy")
            state = accepted(api.get(root + "/sandbox",headers=owner["headers"]))
            assert state["actions"][0]["state"] == "cancelled" and state["actions"][0]["plan_id"] == first["id"]
            assert state["leads"][0]["refunded_vnd"] == 30000 and state["leads"][0]["plan_id"] == first["id"]
        finally:
            browser.close()


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_service_appointment_from_campaign_dashboard(api,agency,tmp_path):  # noqa: F811
    from test_campaign_appointments import service_campaign
    owner,root,plan,_,_=service_campaign(api,agency)
    now=datetime.now(timezone.utc)
    when=(now+timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    with local_api() as origin,sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            page=browser.new_page(viewport={"width":1280,"height":900})
            page.goto(origin+"/?workspace="+owner["tenant"]+"#/campaigns")
            login=page.locator("#login-form")
            login.get_by_label("Email").fill(owner["email"])
            login.get_by_label("Mật khẩu").fill(owner["password"])
            login.get_by_role("button").click()
            panel=page.locator("#campaign-engine")
            panel.locator("#engine-select").select_option(plan["campaign_id"])
            panel.get_by_text("Yêu cầu lịch dịch vụ",exact=True).click()
            form=panel.locator("form").filter(has=page.get_by_role("button",name="Ghi nhận lịch hẹn"))
            form.get_by_label("Mã lịch hẹn").fill("BH-102")
            form.get_by_label("Giờ mong muốn").fill(when)
            form.get_by_label("Nơi phục vụ").fill("Xưởng mô phỏng miền Trung")
            form.get_by_label("Nội dung dịch vụ").fill("Kiểm tra rung động máy bơm và bàn giao phiếu kết quả.")
            consent=form.get_by_role("checkbox")
            consent.focus()
            page.keyboard.press("Space")
            form.get_by_role("button").click()
            detail=panel.locator("details").filter(has=page.get_by_text("BH-102 · Đã yêu cầu",exact=True))
            detail.locator(":scope > summary").click()
            detail.get_by_text("Xác nhận lịch hẹn",exact=True).click()
            detail.get_by_label("Giờ hẹn đã thống nhất").fill(when)
            detail.get_by_role("button",name="Lưu xác nhận lịch hẹn").click()
            accepted_row=panel.get_by_text("BH-102 · Đã xác nhận",exact=True)
            accepted_row.click()
            expect(panel.get_by_text("Nhận phụ trách lịch",exact=True)).to_be_visible()
            state=accepted(api.get(root+"/sandbox",headers=owner["headers"]))
            assert state["appointment_summary"]["confirmed"]==1 and state["report"]["rfqs"]==0
            directory=Path(os.getenv("AMC_DEPT_OPS_EVIDENCE",tmp_path))/"ui"
            directory.mkdir(exist_ok=True,parents=True)
            for width,height in ((1280,900),(820,1180),(390,844)):
                page.set_viewport_size({"width":width,"height":height})
                accepted_row.evaluate("e=>e.scrollIntoView({block:'center'})")
                capture_themes(page,directory/f"appointment-{width}.png")
        finally:
            browser.close()
