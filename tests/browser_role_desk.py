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
from c3_browser_themes import capture_themes
from knowledge_fixtures import accepted
from test_campaign_appointments import service_campaign
from test_claim_desk import reader


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
