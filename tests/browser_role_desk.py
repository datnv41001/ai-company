"""A scoped service staff viewer settles an actual synthetic assignment through Chromium."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
from time import monotonic
from uuid import uuid4

import pytest
from playwright.sync_api import expect,sync_playwright

from browser_c3_content_gate import client,local_api  # noqa: F401
from browser_visual_checks import contrast, no_motion
from c3_browser_themes import capture_themes
from knowledge_fixtures import accepted
from test_campaign_appointments import service_campaign
from test_claim_desk import reader
from test_channel_editions import workforce  # noqa: F401
from test_production_studios import rehearsal


@pytest.mark.parametrize("api",["sqlite"],indirect=True)
def test_service_employee_inbox_and_switch(api,agency):
    owner,root,plan,_,other=service_campaign(api,agency)
    operator,staff=reader(api,owner,"viewer"),reader(api,owner,"viewer")
    for member,role in [(operator,"marketing_operator"),(staff,"service_assignee")]:
        accepted(api.post(root+"/business-desk/grants",headers=owner["headers"],json={"subject":member["id"],"role":role,"enabled":True,
                                                                                  "expected_revision":0,"key":uuid4().hex}))
    when=datetime.now(timezone.utc)-timedelta(days=1)
    def time_at(h):return (when+timedelta(hours=h)).isoformat()
    common={"appointment_id":"bao-tri-03","plan_id":plan["id"]}
    accepted(api.post(root+"/sandbox/commands",headers=owner["headers"],json={"kind":"appointment","request_id":uuid4().hex,**common,
        "contract":"service-appointment/1","product_id":plan["product_id"],"unit":plan["selling_unit"],"quantity":"2","location":"Xưởng thử nghiệm",
        "service_scope":"Kiểm tra máy bơm tuần hoàn","contact_purpose":"appointment_request","occurred_at":time_at(0),"requested_for":time_at(3)}))
    for i,(step,extra) in enumerate([("confirm",{"confirmed_for":time_at(3)}),("assign",{"assignee_id":staff["id"]})],1):
        accepted(api.post(root+"/business-desk/marketing_operator/decisions",headers=operator["headers"],json={"kind":"appointment_decision",
            "request_id":uuid4().hex,"step":step,"expected_revision":i,"occurred_at":time_at(i),**common,**extra}))
    with local_api() as origin,sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            page=browser.new_page(viewport={"width":1280,"height":850})
            page.goto(origin+"/?workspace="+owner["tenant"]+"#/campaigns")
            login=page.locator("#login-form")
            login.get_by_label("Email").fill(staff["email"])
            login.get_by_label("Mật khẩu").fill(staff["password"])
            login.get_by_role("button").click()
            panel=page.locator("#campaign-role-desk")
            selector=panel.get_by_label("Chiến dịch bàn giao")
            started=monotonic()
            selector.select_option(root.rsplit("/",1)[1])
            expect(panel.get_by_role("heading",name="Lịch dịch vụ · bao-tri-03")).to_be_visible()
            timing={"local_inbox_ms":round((monotonic()-started)*1000),"viewports":[]}
            expect(panel.get_by_text("Xưởng thử nghiệm",exact=True)).to_be_visible()
            field=panel.get_by_label("Nhận xét và lý do")
            field.fill("Đã kiểm tra máy bơm tại xưởng thử nghiệm.")
            for label,w,h in (("desktop",1280,850),("tablet",820,1000),("mobile",390,844)):
                page.set_viewport_size({"width":w,"height":h})
                field.focus()
                expect(field).to_be_focused()
                panel.evaluate("el => el.scrollIntoView({block:'start'})")
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                timing["viewports"].append({"width":w,"height":h,"content_width":page.evaluate("document.documentElement.scrollWidth")})
                if path:=os.getenv("AMC_DESK_SCREENSHOTS"):
                    folder=Path(path)
                    folder.mkdir(parents=True,exist_ok=True)
                    capture_themes(page,folder/("service-"+label+".png"))
            started=monotonic()
            panel.get_by_role("button",name="Ghi nhận").click()
            expect(panel.get_by_text("Hoàn thành · Lần cập nhật 4")).to_be_visible()
            timing["local_decision_visible_ms"]=round((monotonic()-started)*1000)
            selector.select_option(other.rsplit("/",1)[1])
            expect(panel.get_by_text("Tài khoản chưa được giao vai trò trong chiến dịch này.")).to_be_visible()
            expect(panel).not_to_contain_text("bao-tri-03")
            assert accepted(api.get(root+"/sandbox",headers=owner["headers"]))["appointment_summary"]["completed"]==1
            if path:=os.getenv("AMC_DESK_SCREENSHOTS"):
                (Path(path)/"browser-observations.json").write_text(json.dumps(timing,indent=2)+"\n",encoding="utf8")
        finally:
            browser.close()


@pytest.mark.parametrize("api",["sqlite"],indirect=True)
def test_assigned_sales_consultation(api,workforce,monkeypatch,tmp_path):  # noqa: F811
    cases=json.loads((Path(__file__).parent/"evaluation/department/briefs-v1.json").read_text(encoding="utf-8"))["cases"]
    case=next(c for c in cases if c["id"]=="index-tray")
    out=Path(os.getenv("AMC_DESK_SCREENSHOTS",tmp_path))/"consultation"
    out.mkdir(parents=True,exist_ok=True)
    def inspect(owner,doc,plan,exports):
        root=doc.split("/deliverables/")[0]+"/campaigns/"+plan["campaign_id"]
        desk=root+"/business-desk"
        assigned=reader(api,owner,"viewer")
        for actor,role in ((owner,"marketing_operator"),(assigned,"sales_recipient")):
            accepted(api.post(desk+"/grants",headers=owner["headers"],json={"subject":actor["id"],"role":role,
                     "enabled":True,"expected_revision":0,"key":uuid4().hex}))
        inquiry=next(x for x in accepted(api.get(root+"/sandbox",headers=owner["headers"]))["leads"] if x.get("intake"))
        assert inquiry["state"]=="received" and inquiry["missing"]==["commercial_moq"]
        with local_api() as origin,sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
            try:
                def open_workspace(actor):
                    page=browser.new_page(viewport={"width":1280,"height":900})
                    page.goto(origin+"/?workspace="+owner["tenant"]+"#/campaigns")
                    login=page.locator("#login-form")
                    login.get_by_label("Email").fill(actor["email"])
                    login.get_by_label("Mật khẩu").fill(actor["password"])
                    login.get_by_role("button").click()
                    panel=page.locator("#campaign-role-desk")
                    panel.get_by_label("Chiến dịch bàn giao").select_option(plan["campaign_id"])
                    return page,panel
                manager,route=open_workspace(owner)
                card=route.locator("article").filter(has=manager.get_by_role("heading",name="Yêu cầu báo giá · "+inquiry["id"]))
                card.get_by_label("Thao tác").select_option("refer")
                card.get_by_label("Mã người nhận").fill(assigned["id"])
                card.get_by_role("button",name="Ghi nhận").click()
                expect(card).to_contain_text("Đang tư vấn · Lần cập nhật 2")
                page,panel=open_workspace(assigned)
                lead=panel.locator("article")
                expect(lead).to_have_count(1)
                lead.get_by_label("Nội dung tư vấn").fill("Khách đã xác nhận bổ sung số lượng.")
                qty=lead.get_by_label("Số lượng khách bổ sung")
                qty.fill("5")
                start=monotonic()
                for width,height in ((1280,900),(820,1000),(390,844)):
                    page.set_viewport_size({"width":width,"height":height})
                    qty.focus()
                    expect(qty).to_be_focused()
                    lead.scroll_into_view_if_needed()
                    for mode in ("light","dark"):
                        page.emulate_media(color_scheme=mode)
                        expect(page.locator("html")).to_have_attribute("data-theme",mode)
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                        lead.screenshot(path=out/f"sales-{width}-{mode}.png",animations="disabled")
                mark=monotonic()
                lead.get_by_role("button",name="Ghi nhận").press("Enter")
                expect(lead).to_contain_text("Đủ điều kiện, chờ giao Sales · Lần cập nhật 3")
                expect(lead).to_contain_text("Hồ sơ hiện tại · 5")
                expect(lead.get_by_role("button",name="Ghi nhận")).to_have_count(0)
                elapsed=round((monotonic()-mark)*1000)
                engine=manager.locator("#campaign-engine")
                engine.locator("#engine-select").select_option(plan["campaign_id"])
                block=engine.locator("section").filter(has=manager.get_by_role("heading",name="Yêu cầu từ biểu mẫu đã duyệt")).last
                expect(block.locator(".engine-row").filter(has_text="RFQ đã đủ điều kiện")).to_contain_text("1")
                expect(block.locator(".engine-row").filter(has_text="Báo giá đã phát hành")).to_contain_text("0")
                chooser=route.locator("#desk-campaign")
                chooser.select_option("")
                chooser.select_option(plan["campaign_id"])
                select=card.locator("form select").first
                select.select_option("cancel")
                reason=card.locator("form input[required]")
                expect(reason).to_have_count(1)
                reason.fill("Buyer withdrew the synthetic request after their requirements changed.")
                readings=[]
                selector=f'#desk-cases article:has(h4:has-text("{inquiry["id"]}"))'
                def audit_withdrawal(stage):
                    for width,height in ((1280,900),(820,1000),(390,844)):
                        manager.set_viewport_size({"width":width,"height":height})
                        for mode in ("light","dark"):
                            manager.emulate_media(color_scheme=mode,reduced_motion="reduce")
                            expect(manager.locator("html")).to_have_attribute("data-theme",mode)
                            card.scroll_into_view_if_needed()
                            assert manager.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                            assert card.evaluate("el => el.scrollWidth <= el.clientWidth+1")
                            audit=contrast(manager,selector,f"{width}-{mode}-{stage}")
                            assert not audit["failed"] and not audit["unresolved"], audit
                            assert not no_motion(manager)
                            readings.append({"stage":stage,"viewport":[width,height],"theme":mode,
                                             "text_samples":audit["checked"],"minimum_ratio":audit["minimum_ratio"],
                                             "contrast_failures":0,"unresolved":0,"running_motion":0,"reflow":True})
                            if stage=="withdrawn":
                                card.screenshot(path=out/f"withdrawal-{width}-{mode}.png",animations="disabled")
                audit_withdrawal("before_submit")
                reason.focus()
                reason.press("Tab")
                expect(card.locator("form button")).to_be_focused()
                started=monotonic()
                manager.keyboard.press("Enter")
                expect(card).to_contain_text("Buyer withdrew the synthetic request")
                expect(card.locator("form")).to_have_count(0)
                withdrawn_ms=round((monotonic()-started)*1000)
                audit_withdrawal("withdrawn")
                (out/"withdrawal-observations.json").write_text(json.dumps({
                    "synthetic":True,"browser":browser.version,"scope":"Rendered RFQ card before and after coordinator withdrawal",
                    "keyboard":"Tab from required reason to submit; Enter to withdraw",
                    "submit_to_withdrawn_ms":withdrawn_ms,"readings":readings},indent=2)+"\n",encoding="utf-8",newline="\n")
                (out/"observations.json").write_text(json.dumps({"viewports":[390,820,1280],"themes":["light","dark"],
                    "keyboard_submit":True,"local_decision_to_qualified_ms":elapsed,"capture_seconds":round(monotonic()-start,3)}),encoding="utf-8")
            finally:
                browser.close()
    rehearsal(api,workforce,monkeypatch,case,inspect)
