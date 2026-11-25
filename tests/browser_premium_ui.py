"""Exercise the authenticated AMC command center on a loopback PostgreSQL fixture."""

import base64
from hashlib import sha256
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import struct
import subprocess
from time import perf_counter
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
import psycopg
from playwright.sync_api import expect, sync_playwright

from screen_navigation import menu, screen, select_workspace, switch_account
from browser_knowledge import BASE, PROJECT, authenticate, db_counts, post
from identity_fixtures import invite_member, start_registration, verify_registration


OUT = Path(os.getenv("AMC_PREMIUM_EVIDENCE", "premium-ui-evidence"))
MATRIX = {"desktop": (1440, 900), "laptop": (1280, 850), "tablet": (820, 1180), "mobile": (390, 844), "compact": (320, 700)}
AUDIT = Path(__file__).with_name("premium_accessibility.js").read_text("utf8")
OWNER_NAME = "Mộc Studio"
EMPTY_NAME = "Studio một thành viên · Trung tâm Thương hiệu và Truyền thông Việt Nam"


def request_json(api, method, path, who, body=None):
    response = api.request(method, path, headers=who["headers"], json=body)
    assert response.is_success, (method, path, response.status_code)
    return response.json()


def account(api, label, org=None):
    email, password = f"{label}.{uuid4().hex[:8]}@example.com", uuid4().hex
    reg = start_registration(api, email, password, **({"organization_name": org, "mode": "agency"} if org else {}))
    verify_registration(api, email, reg, PROJECT)
    return {**reg, "email": email, "password": password, "headers": {"Authorization": "Bearer " + reg["access_token"]}}


def fixture(api):
    owner = account(api, "minh.truongphong.truyenthong.thuonghieu", OWNER_NAME)
    editor = account(api, "linh")
    recipient = account(api, "an")
    tenant = owner["tenant_id"]
    base = "/api/tenants/" + tenant
    invite_member(api, base, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    empty = post(api, "/api/me/workspaces", owner, {"organization_name": EMPTY_NAME, "mode": "inhouse", "request_id": str(uuid4())})["tenant_id"]
    clients = []
    brands = []
    for company, brand in (("Xưởng Gốm Mây", "Gốm Mây"), ("Nếp Nhà", "Nếp Living")):
        client = post(api, base + "/clients", owner, {"name": company, "sector": "Thiết kế và bán lẻ"})
        clients.append(client)
        brands.append(post(api, base + "/brands", owner, {"client_id": client["id"], "name": brand}))
    invite_member(api, base, owner["headers"], recipient["headers"], email=recipient["email"], role="client_viewer", client_id=clients[0]["id"])
    campaigns = []
    for name, objective, brand in (
        ("Bộ sưu tập Mùa Hạ", "Giới thiệu dòng gốm thủ công và thu thập phản hồi.", brands[0]),
        ("Kể chuyện xưởng gốm", "Lên kế hoạch nội dung về quá trình hoàn thiện từng sản phẩm.", brands[0]),
        ("Nếp Nhà · Mở cửa không gian mới", "Thu thập đăng ký tham quan từ khách hàng trong khu vực.", brands[1]),
    ):
        campaigns.append(post(api, base + "/campaigns", owner, {"name": name, "objective": objective, "brief": objective, "brand_id": brand["id"]}))
    planned = campaigns[0]
    plan = request_json(api, "POST", base + f"/campaigns/{planned['id']}/plan", owner, {})
    assert plan["llm_called"] is False and plan["created_count"] > 0
    for title, state, campaign in (
        ("Lịch nội dung tuần ra mắt", "approved", planned),
        ("Hướng dẫn hình ảnh bộ sưu tập", "submitted", planned),
        ("Dàn ý bài giới thiệu nghệ nhân", "draft", planned),
        ("Thông báo mở cửa không gian mới", "draft", campaigns[2]),
    ):
        draft = post(
            api,
            base + "/deliverables",
            editor,
            {"title": title, "campaign_id": campaign["id"], "content": {"client_preview": "Bản thảo nội bộ để nhóm đối chiếu thông điệp."}},
        )
        path = base + "/deliverables/" + draft["id"]
        if state != "draft":
            request_json(api, "POST", path + "/submit", editor, {})
        if state == "approved":
            request_json(
                api,
                "POST",
                path + "/review",
                owner,
                {
                    "decision": "approved",
                    "note": "Đã đối chiếu bản thảo nội bộ.",
                    "expected_qa_revision": draft["qa_evidence"]["qa_revision"],
                    "expected_content_digest": draft["qa_evidence"]["content_digest"],
                },
            )
    # Share one real company profile across the two campaigns of the same brand.
    ppath = base + "/clients/" + clients[0]["id"] + "/business-profile"
    post(
        api,
        ppath,
        owner,
        {
            "key": uuid4().hex,
            "expected_revision": 0,
            "fields": {
                "name": "Xưởng Gốm Mây",
                "sells": "Gốm gia dụng thủ công",
                "audience": "Người yêu thiết kế nội thất",
                "goal": "Tăng đăng ký tham quan xưởng.",
            },
        },
    )
    catalog = base + "/clients/" + clients[0]["id"] + "/brands/" + brands[0]["id"] + "/catalog/items"
    request_json(
        api,
        "POST",
        catalog,
        owner,
        {"key": uuid4().hex, "expected_revision": 0, "kind": "product", "code": "MUA-HA", "visibility": "internal", "data": {"name": "Bộ gốm Mùa Hạ"}},
    )
    return dict(owner=owner, editor=editor, recipient=recipient, tenant=tenant, empty=empty, base=base, clients=clients, brands=brands, campaigns=campaigns)


def source_data(api, f):
    who, root = f["owner"], f["base"]
    items = {k: request_json(api, "GET", root + "/" + k, who) for k in ("campaigns", "deliverables", "clients", "brands", "actions")}
    selected = f["campaigns"][0]["id"]
    items["tasks"] = request_json(api, "GET", root + f"/campaigns/{selected}/tasks", who)
    items["roles"] = request_json(api, "GET", "/api/catalog/roles", who)
    return items


def settle(page):
    page.evaluate("async()=>{await document.fonts.ready; await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))}")


def capture(page, name, *, top=None):
    if top:
        page.locator(top).first.evaluate("el=>el.scrollIntoView({block:'start',behavior:'instant'})")
    else:
        page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    settle(page)
    dest = OUT / (name + ".png")
    page.screenshot(path=str(dest), animations="disabled", caret="hide")
    assert tuple(page.viewport_size[k] for k in ("width", "height")) == struct.unpack(">II", dest.read_bytes()[16:24])
    return dest.name


def reflow(page):
    result = page.evaluate("""()=>({width:innerWidth,content:document.documentElement.scrollWidth,
        offenders:[...document.querySelectorAll('main button, main input, main select, main h1, main h2, main h3')].filter(e=>{
          if(!e.checkVisibility({checkVisibilityCSS:true,checkOpacity:true}))return false;
          const box=e.getBoundingClientRect();return box.width>0 && (box.left < -1 || box.right>innerWidth+1);
        }).map(e=>e.id||e.tagName).slice(0,10)})""")
    assert result["content"] <= result["width"] + 1 and not result["offenders"], result
    return result["width"]


def choose_campaign(page, campaign):
    control = page.locator("#command-campaign")
    expect(control).to_be_visible()
    if control.input_value() != campaign["id"]:
        control.select_option(campaign["id"])
    expect(page.locator("#command-objective")).to_have_text(campaign["objective"])
    expect(page.locator("#command-center")).not_to_have_attribute("aria-busy", "true")


def current_approval(doc):
    evidence = doc.get("qa_evidence") or {}
    return bool(
        doc["status"] == "approved"
        and doc.get("reviewed_by")
        and doc["qa_revision"] == doc.get("qa_approved_revision") == evidence.get("qa_revision")
        and doc.get("qa_approved_digest")
        and doc["qa_approved_digest"] == evidence.get("content_digest")
    )


def check_dashboard(page, f, dataset):
    counts = {
        "campaign": len(dataset["campaigns"]),
        "deliverable": len(dataset["deliverables"]),
        "review": sum(d["status"] == "submitted" or (d["status"] == "approved" and not current_approval(d)) for d in dataset["deliverables"]),
        "approved": sum(map(current_approval, dataset["deliverables"])),
    }
    for key, value in counts.items():
        expect(page.locator("#command-" + key + "-count")).to_have_text(str(value))
    expect(page.locator("#command-client-total")).to_contain_text(f"Agency · {len(dataset['clients'])} khách hàng · {len(dataset['brands'])} thương hiệu")
    choose_campaign(page, f["campaigns"][0])
    tasks = dataset["tasks"]
    expect(page.locator("#command-tasks li")).to_have_count(len(tasks))
    expect(page.locator("#command-flow li")).to_have_count(len(tasks))
    for task in tasks:
        expect(page.locator("#command-tasks")).to_contain_text(task["title"])
    completed = sum(t["status"] in {"done", "succeeded", "completed"} for t in tasks)
    meter = page.locator("#command-progress")
    assert meter.evaluate("n=>[n.value,n.max]") == [completed, len(tasks)]
    expect(page.locator("#command-progress-label")).to_have_text(f"{round(100 * completed / len(tasks))}%")
    roles = {r["id"]: r for r in dataset["roles"]}
    grouped = Counter(roles[t["role_slug"]]["group"] for t in tasks if t["role_slug"] in roles)
    assert grouped
    for dept, count in grouped.items():
        row = page.locator("#command-departments li").filter(has=page.get_by_text(dept, exact=True))
        expect(row).to_contain_text(f"{count} việc")
    scoped = [d for d in dataset["deliverables"] if d["campaign_id"] == f["campaigns"][0]["id"]]
    expect(page.locator("#command-outcomes li")).to_have_count(len(scoped))
    for doc in scoped:
        expect(page.locator("#command-outcomes")).to_contain_text(doc["title"])
        outcome = page.locator("#command-outcomes li").filter(has_text=doc["title"])
        if doc.get("qa_evidence", {}).get("state") == "source_unavailable":
            expect(outcome).to_contain_text("Chưa có nguồn để đối chiếu")
        if current_approval(doc):
            expect(outcome).to_contain_text("Có thể yêu cầu chia sẻ")
    expect(page.locator("#command-runs")).to_contain_text("Chưa thấy lượt xử lý")
    expect(page.locator("#command-outcomes")).not_to_contain_text("Thông báo mở cửa không gian mới")
    return {
        **counts,
        "tasks": len(tasks),
        "finished": completed,
        "outcomes_for_selected_campaign": len(scoped),
        "departments": dict(grouped),
        "clients": len(dataset["clients"]),
        "brands": len(dataset["brands"]),
    }


def keyboard(page, view, screenshots):
    toggle = page.locator("#menu-toggle")
    start = toggle if toggle.is_visible() else page.locator("#knowledge-nav")
    page.locator(".skip-link").focus()
    for _ in range(24):
        page.keyboard.press("Tab")
        if start.evaluate("n=>n===document.activeElement"):
            break
    expect(start).to_be_focused()
    assert start.evaluate("""n=>{const s=getComputedStyle(n);return n.matches(':focus-visible') &&
       ((s.outlineStyle!=='none' && parseFloat(s.outlineWidth)>=1) || s.boxShadow!=='none')}""")
    if toggle.is_visible():
        page.keyboard.press("Enter")
        expect(toggle).to_have_attribute("aria-expanded", "true")
        sidebar = page.locator("#workspace-sidebar")
        assert sidebar.evaluate("el=>el.contains(document.activeElement)")
        links = sidebar.locator("a[href]:visible, button:visible:enabled, select:visible:enabled")
        first, last = links.first, links.last
        first.focus()
        page.keyboard.press("Shift+Tab")
        expect(last).to_be_focused()
        page.keyboard.press("Tab")
        expect(first).to_be_focused()
        if view == "mobile-light":
            screenshots.append(capture(page, view + "-navigation"))
        page.keyboard.press("Escape")
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(toggle).to_be_focused()
        return "Tab reached visible focus, drawer wrapped in both directions, Escape returned focus"
    page.keyboard.press("Enter")
    assert page.locator("#knowledge-title").is_visible()
    expect(page.locator("#knowledge-nav")).to_have_attribute("aria-current", "page")
    expect(page.locator("#knowledge-panel")).to_be_focused()
    page.go_back()
    expect(page.locator("#command-center")).to_be_visible()
    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    return "workspace navigation activated by keyboard"


def contrast(page, selector, view):
    result = page.locator(selector).evaluate(AUDIT)
    assert result["checked"], (view, selector)
    rows = result["checked"]
    return {
        "surface": selector,
        "view": view,
        "checked": len(rows),
        "minimum_ratio": round(min(r["ratio"] for r in rows), 3),
        "failed": [r for r in rows if not r["pass"]],
        "unresolved": result["unresolved"],
    }


def no_motion(page):
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    # Steady layout and actively loading UI are both sampled by the caller.
    return page.evaluate("""()=>document.getAnimations().filter(a=>a.playState==='running' && (
      Number(a.effect?.getComputedTiming().activeDuration)>20 || a.effect?.getComputedTiming().iterations===Infinity)).
      map(a=>({name:a.animationName||a.transitionProperty||'animation',target:a.effect?.target?.id||a.effect?.target?.tagName}))""")


def task_network(page, f):
    cold = f["campaigns"][1]
    pattern = "**/campaigns/" + cold["id"] + "/tasks"
    held = []

    def hold(route):
        held.append(route)
        page.evaluate("window.__amcRouteHeld=true")

    page.route(pattern, hold)
    control = page.locator("#command-campaign")
    control.focus()

    def geometry():
        return page.evaluate("""()=>Object.fromEntries(['command-campaign','command-plan-link','command-tasks','command-outcomes'].map(id=>{
          const rect=document.getElementById(id).getBoundingClientRect();return [id,Math.round(rect.top+scrollY)]}))""")

    positions = [geometry()]
    start = page.evaluate("performance.now()")
    control.select_option(cold["id"])
    expect(page.locator("#command-center")).to_have_attribute("aria-busy", "true")
    page.wait_for_function("window.__amcRouteHeld === true")
    running = no_motion(page)
    assert not running, running
    expect(page.locator("#command-status")).to_contain_text("Đang tải")
    positions.append(geometry())
    page.evaluate("window.scrollBy({top:64,behavior:'instant'})")
    scroll = page.evaluate("scrollY")
    # Hold the real read past the 500 ms recent-input window.
    page.wait_for_timeout(650)
    held[0].continue_()
    expect(page.locator("#command-progress-label")).to_have_text("—")
    expect(page.locator("#command-center")).not_to_have_attribute("aria-busy", "true")
    assert not page.locator("#command-progress").evaluate("n=>n.hasAttribute('value')")
    expect(control).to_be_focused()
    settle(page)
    positions.append(geometry())
    delta = {k: max(pos[k] for pos in positions) - min(pos[k] for pos in positions) for k in positions[0]}
    assert max(delta.values()) <= 2, (page.viewport_size, positions)
    assert abs(scroll - page.evaluate("scrollY")) <= 2
    shifts = page.evaluate(
        """start=>{const all=window.__amcShifts.filter(e=>e.t>=start);
      const score=recent=>all.filter(e=>e.recent===recent).reduce((sum,e)=>sum+e.v,0);
      return {unexpected_sum:score(false),recent_input_sum:score(true),entries:all.length}}""",
        start,
    )
    assert shifts["unexpected_sum"] <= 0.1, shifts
    page.unroute(pattern)
    choose_campaign(page, f["campaigns"][0])
    page.route(pattern, lambda route: route.abort("connectionfailed"), times=1)
    page.locator("#command-campaign").select_option(cold["id"])
    expect(page.locator("#command-status")).to_contain_text("thử lại")
    expect(page.locator("#command-tasks")).not_to_contain_text("Complete client discovery")
    page.locator("#command-refresh").click()
    expect(page.locator("#command-progress-caption")).to_contain_text("Chưa có nhiệm vụ")
    choose_campaign(page, f["campaigns"][0])
    return {"task_read": "real delayed GET, failure and successful retry", "document_position_change_px": delta, "scroll_and_focus_retained": True, **shifts}


def measurements(page):
    return page.evaluate("""()=>{
       const n=performance.getEntriesByType('navigation')[0], resources=performance.getEntriesByType('resource');
       const fcp=performance.getEntriesByName('first-contentful-paint')[0];
       const shifts=window.__amcShifts.filter(e=>!e.recent), login=performance.getEntriesByName('amc-login')[0].startTime,
             ready=performance.getEntriesByName('amc-dashboard-ready')[0].startTime;
       function cls(entries) {
         let best=0,score=0,first=-Infinity,last=-Infinity;
         for(const e of entries){if(e.t-last>=1000 || e.t-first>=5000){score=0; first=e.t;}
           score+=e.v;last=e.t;best=Math.max(best,score);}return Number(best.toFixed(4));
       }
       const phase=t=>t<login?'login_page':t<ready?'login_to_dashboard':'dashboard_idle';
       return {document_dom_content_loaded_ms:Math.round(n.domContentLoadedEventEnd),document_load_ms:Math.round(n.loadEventEnd),
         document_first_contentful_paint_ms:fcp?Math.round(fcp.startTime):null,document_lcp_ms:window.__amcLcp||null,
         same_origin_requests:resources.filter(e=>new URL(e.name).origin===location.origin).length,
         static_transfer_bytes:resources.filter(e=>new URL(e.name).pathname.startsWith('/static/')).reduce((s,e)=>s+e.transferSize,0),
         cumulative_layout_shift:cls(shifts), cls_by_phase:Object.fromEntries(['login_page','login_to_dashboard','dashboard_idle']
           .map(k=>[k,cls(shifts.filter(e=>phase(e.t)===k))])),dashboard_idle_observation_ms:Math.round(performance.now()-ready),
         layout_shift_sources:shifts.map(e=>({phase:phase(e.t),ms:Math.round(e.t),score:e.v,elements:e.sources}))};
    }""")


def navigation_and_density(page, f, dev, theme, shots):
    nav = page.locator("#workspace-sidebar")
    dept = page.locator("#command-departments details").first
    dept.locator("summary").click()
    expect(dept.locator(".assignment").first).to_be_visible()
    expect(dept).to_contain_text("Nhiệm vụ kế hoạch")
    if dev in ("desktop", "mobile") and theme == "dark":
        shots.append(capture(page, f"{dev}-{theme}-department", top="#command-departments"))
    dept.locator("summary").click()
    cap = page.locator(".capability-list")
    cap.locator("summary").click()
    expect(cap).to_contain_text("WF-13/")
    expect(cap).to_contain_text("Chưa đủ quyền")
    cap.locator("summary").click()
    page.evaluate("scrollTo({top:0,behavior:'instant'})")
    menu(page, "account")
    expect(page.locator("#who")).to_have_text(f["owner"]["email"])
    reflow(page)
    page.keyboard.press("Escape")
    menu(page, "scope")
    page.locator("#toolbar-brand").select_option(f["brands"][1]["id"])
    expect(page.locator("#command-campaign option")).to_have_count(1)
    page.keyboard.press("Escape")
    expect(page.locator("#command-objective")).to_have_text(f["campaigns"][2]["objective"])
    expect(page.locator("#command-campaign-count")).to_have_text("3")
    expect(page.locator("#command-outcomes")).not_to_contain_text("Lịch nội dung tuần ra mắt")
    filtered = page.url
    screen(page, "knowledge")
    expect(page.locator("#command-center")).to_be_hidden()
    expect(page.locator("#knowledge-brand")).to_have_value(f["brands"][1]["id"])
    expect(nav.locator("[data-route=knowledge]")).to_have_attribute("aria-current", "page")
    page.go_back()
    expect(page.locator("#command-center")).to_be_visible()
    expect(page).to_have_url(filtered)
    expect(page.locator("#command-campaign")).to_have_value(f["campaigns"][2]["id"])
    page.go_forward()
    expect(page.locator("#knowledge-panel")).to_be_visible()
    screen(page, "overview")
    menu(page, "scope")
    page.locator("#toolbar-brand").select_option("")
    page.keyboard.press("Escape")
    choose_campaign(page, f["campaigns"][0])
    if not page.locator("#menu-toggle").is_visible():
        toggle = page.locator("#rail-toggle")
        width = nav.bounding_box()["width"]
        toggle.click()
        assert nav.bounding_box()["width"] < width
        expect(toggle).to_have_attribute("aria-expanded", "false")
        toggle.click()
    else:
        assert page.locator(".topbar").bounding_box()["height"] <= 64
    targets = page.locator("#account-trigger, #scope-trigger, #command-refresh, #command-campaign")
    assert all(min(t.bounding_box()["width"], t.bounding_box()["height"]) >= 44 for t in targets.all())
    if dev == "laptop" and theme == "light":
        cdp = page.context.new_cdp_session(page)
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 2})
        assert page.evaluate("visualViewport.scale") >= 1.99
        menu(page, "scope")
        expect(page.locator("#toolbar-brand")).to_be_visible()
        page.keyboard.press("Escape")
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 1})
        cdp.detach()
    return {
        "history": "Back/Forward restore view, exact campaign and approved brand filter",
        "header_height_px": round(page.locator(".topbar").bounding_box()["height"]),
        "touch_target_min_px": 44,
        "pinch_zoom_tested": dev == "laptop" and theme == "light",
    }


def run_view(browser, dev, theme, f, dataset):
    w, h = MATRIX[dev]
    ctx = browser.new_context(
        viewport={"width": w, "height": h},
        device_scale_factor=1,
        locale="vi-VN",
        timezone_id="Asia/Ho_Chi_Minh",
        color_scheme="light" if theme == "dark" else "dark",
        reduced_motion="reduce",
    )
    ctx.add_init_script(
        """()=>{
      new PerformanceObserver(list=>{const e=list.getEntries().at(-1);if(e)window.__amcLcp=Math.round(e.startTime)}).
        observe({type:'largest-contentful-paint',buffered:true});
      window.__amcShifts=[];
      new PerformanceObserver(list=>{for(const e of list.getEntries())window.__amcShifts.push({
        t:e.startTime,v:e.value,recent:e.hadRecentInput,sources:e.sources?.map(s=>s.node?.id||s.node?.tagName||null)||[]});}).
        observe({type:'layout-shift',buffered:true});
    }""".replace("()=>{", "(()=>{", 1)
        + ")()"
    )
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    view = dev + "-" + theme
    source = BASE.rstrip("/") + "/?workspace=" + f["tenant"]
    try:
        page.goto(source)
        selector = page.locator("#theme-mode")
        menu(page, "account")
        selector.select_option(theme)
        page.keyboard.press("Escape")
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        page.reload()
        expect(selector).to_have_value(theme)
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        audits = [contrast(page, "#auth", view)]
        page.evaluate("performance.mark('amc-login')")
        start = perf_counter()
        authenticate(page, f["owner"])
        expect(page.locator("#command-center")).to_be_visible()
        expect(page.locator("#command-campaign-count")).to_have_text(str(len(dataset["campaigns"])))
        expect(page.locator("#command-center")).not_to_have_attribute("aria-busy", "true")
        ready_ms = round((perf_counter() - start) * 1000)
        settle(page)
        page.evaluate("performance.mark('amc-dashboard-ready')")
        # Observe the loaded layout before any deliberate scroll or navigation.
        page.wait_for_timeout(1100)
        perf = measurements(page)
        assert perf["cumulative_layout_shift"] <= 0.1, (view, perf["layout_shift_sources"])
        counts = check_dashboard(page, f, dataset)
        screenshot = capture(page, view + "-overview")
        reflow(page)
        audits.append(contrast(page, "#command-center", view))
        if page.locator("#workspace-sidebar").is_visible() and not page.locator("#menu-toggle").is_visible():
            audits.append(contrast(page, "#workspace-sidebar", view))
        assert not no_motion(page)
        perf["login_to_verified_dashboard_ms"] = ready_ms
        start = perf_counter()
        choose_campaign(page, f["campaigns"][1])
        expect(page.locator("#command-progress-label")).to_have_text("—")
        perf["switch_campaign_ms"] = round((perf_counter() - start) * 1000)
        choose_campaign(page, f["campaigns"][0])
        result = {"device": dev, "theme": theme, "viewport": [w, h], "counts": counts, "performance": perf, "screenshots": [screenshot], "contrast": audits}
        result["interaction"] = navigation_and_density(page, f, dev, theme, result["screenshots"])
        result["keyboard"] = keyboard(page, view, result["screenshots"])
        if theme == "light":
            result["network_states"] = task_network(page, f)
        screen(page, "knowledge")
        page.locator("#knowledge-client").select_option(f["clients"][0]["id"])
        expect(page.locator("#knowledge-name")).to_have_value(f["clients"][0]["name"])
        result["screenshots"].append(capture(page, view + "-knowledge", top="#knowledge-panel"))
        reflow(page)
        audits.append(contrast(page, "#knowledge-panel", view))
        if dev == "mobile" and theme == "dark":
            page.locator("#catalog-drawer summary").click()
            expect(page.locator("#catalog-pane")).to_contain_text("Bộ gốm Mùa Hạ")
            reflow(page)
            audits.append(contrast(page, "#catalog-pane", view))
            result["screenshots"].append(capture(page, view + "-catalog", top="#catalog-drawer"))
            page.locator("#catalog-drawer summary").click()
        screen(page, "overview")
        result["screenshots"].append(capture(page, view + "-work", top="#command-flow"))
        assert not errors, errors
        return result
    finally:
        ctx.close()


def mode_and_scope(browser, api, f):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce", color_scheme="light", locale="vi-VN")
    page = ctx.new_page()
    try:
        page.goto(BASE + "/?workspace=" + f["tenant"])
        expect(page.locator("#theme-mode")).to_have_value("system")
        expect(page.locator("html")).to_have_attribute("data-theme", "light")
        page.emulate_media(color_scheme="dark")
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        authenticate(page, f["owner"])
        select_workspace(page, f["empty"])
        expect(page.locator("#command-campaign-count")).to_have_text("0")
        expect(page.locator("#command-deliverable-count")).to_have_text("0")
        expect(page.locator("#command-center")).not_to_contain_text(f["campaigns"][0]["name"])
        expect(page.locator("#command-campaign")).to_be_disabled()
        assert not page.locator("#command-progress").evaluate("n=>n.hasAttribute('value')")
        assert not request_json(api, "GET", "/api/tenants/" + f["empty"] + "/campaigns", f["owner"])
        capture(page, "solo-dark-empty")
        page.set_viewport_size({"width": 320, "height": 700})
        assert reflow(page) == 320
        link = page.locator("#command-new-link")
        root = "/api/tenants/" + f["empty"]
        # In-house provisioning already creates the internal client used for the first brand.
        companies = request_json(api, "GET", root + "/clients", f["owner"])
        assert len(companies) == 1 and not request_json(api, "GET", root + "/brands", f["owner"])
        company = companies[0]
        expect(link).to_have_attribute("href", "#brand-form")
        brand = post(api, root + "/brands", f["owner"], {"name": "Hạt Mầm Studio", "client_id": company["id"]})
        page.locator("#command-refresh").click()
        expect(link).to_have_attribute("href", "#campaign-form")
        goal = "Tăng đăng ký buổi trải nghiệm sản phẩm mới."
        business = post(api, root + "/campaigns", f["owner"], {"name": "Tuần trải nghiệm", "brand_id": brand["id"], "objective": goal, "brief": goal})
        page.locator("#command-refresh").click()
        expect(page.locator("#command-campaign-count")).to_have_text("1")
        choose_campaign(page, business)
        expect(page.locator("#command-client-total")).to_have_text("Marketing nội bộ · 1 thương hiệu")
        expect(page.locator("#command-scope")).to_contain_text(brand["name"])
        expect(page.locator("#command-center")).not_to_contain_text(f["campaigns"][2]["name"])
        membership_modes = {m["tenant_id"]: m["mode"] for m in request_json(api, "GET", "/api/me", f["owner"])["tenants"]}
        assert membership_modes == {f["tenant"]: "agency", f["empty"]: "inhouse"}
        page.set_viewport_size({"width": 820, "height": 1180})
        page.emulate_media(color_scheme="light")
        capture(page, "business-light-tablet")
        page.set_viewport_size({"width": 320, "height": 700})
        select_workspace(page, f["tenant"])
        expect(page.locator("#command-campaign-count")).to_have_text("3")
        reflow(page)
        legacy_transition(page, api, f)
        switch_account(page)
        scoped = browser.new_context(viewport={"width": 820, "height": 1180}, locale="vi-VN")
        try:
            portal = scoped.new_page()
            task_requests = []
            portal.on("request", lambda req: task_requests.append(req.url) if req.url.endswith("/tasks") else None)
            portal.goto(BASE + "/?workspace=" + f["tenant"] + "#/overview?brand=" + f["brands"][1]["id"] + "&campaign=" + f["campaigns"][2]["id"])
            authenticate(portal, f["recipient"])
            expect(portal.locator("#command-center")).to_be_hidden()
            expect(portal.locator("#knowledge-panel")).to_be_hidden()
            expect(portal.locator("#knowledge-client, #knowledge-brand, #knowledge-content input")).to_have_count(0)
            expect(portal.locator("#knowledge-status")).to_be_empty()
            expect(portal.locator("#workspace")).not_to_contain_text(f["campaigns"][2]["name"])
            assert not task_requests
            assert "#/reviews" in portal.url and f["brands"][1]["id"] not in portal.url
        finally:
            scoped.close()
        return {
            "system_preference": True,
            "checks_at_320px": 2,
            "empty_totals_zero": True,
            "recipient_staff_task_requests": 0,
            "server_modes": sorted(membership_modes.values()),
            "inhouse_setup": ["provisioned_internal_client", "brand", "campaign", "objective"],
            "legacy_qa": "New PostgreSQL migration-shaped fixture, current assessment, independent reapproval, dashboard refresh",
        }
    finally:
        ctx.close()


def legacy_transition(page, api, f):
    campaign = f["campaigns"][0]
    row = post(
        api,
        f["base"] + "/deliverables",
        f["editor"],
        {"campaign_id": campaign["id"], "title": "Bản giao trước khi cập nhật QA", "content": {"client_preview": "Thông tin cho đội nội bộ."}},
    )
    # Reproduce the legacy row covered by check_postgres_upgrade. Guard each identifier
    # and the original draft status; this fixture exists only inside our disposable tenant.
    tid, did, reviewer = (str(UUID(x)) for x in (f["tenant"], row["id"], f["owner"]["user_id"]))
    sql = f"""UPDATE public.deliverables SET status='approved', reviewed_by='{reviewer}', qa_evidence=NULL
               WHERE id='{did}' AND tenant_id='{tid}' AND status='draft' RETURNING id"""
    if PROJECT:
        assert PROJECT == "amc-acceptance"
        res = subprocess.run(
            ["docker", "compose", "-p", PROJECT, "exec", "-T", "db", "psql", "-XAtq", "-v", "ON_ERROR_STOP=1", "-U", "amc", "-d", "amc"],
            input=sql,
            text=True,
            capture_output=True,
            check=True,
        )
        assert res.stdout.strip() == did
    else:
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
            assert db.info.dbname.startswith("amc_test")
            assert str(db.execute(sql).fetchone()[0]) == did
    path = f["base"] + "/deliverables/" + did
    legacy = request_json(api, "GET", path, f["owner"])
    assert legacy["status"] == "approved" and not current_approval(legacy) and not legacy["qa_evidence"]
    page.locator("#command-refresh").click()
    expect(page.locator("#command-deliverable-count")).to_have_text("5")
    choose_campaign(page, campaign)
    outcome = page.locator("#command-outcomes li").filter(has_text=row["title"])
    expect(outcome).to_contain_text("Chờ QA")
    expect(page.locator("#command-review-count")).to_have_text("2")
    expect(page.locator("#command-approved-count")).to_have_text("1")
    fresh = request_json(api, "POST", path + "/assessment", f["owner"], {})
    assert not current_approval(fresh) and fresh["qa_evidence"]["qa_revision"] == fresh["qa_revision"]
    page.locator("#command-refresh").click()
    expect(outcome).to_contain_text("Chờ QA")
    accepted = request_json(
        api,
        "POST",
        path + "/review",
        f["owner"],
        {
            "decision": "approved",
            "expected_qa_revision": fresh["qa_revision"],
            "expected_content_digest": fresh["qa_evidence"]["content_digest"],
            "note": "Đã đối chiếu bản hiện tại.",
        },
    )
    assert current_approval(accepted)
    page.locator("#command-refresh").click()
    expect(page.locator("#command-review-count")).to_have_text("1")
    expect(page.locator("#command-approved-count")).to_have_text("2")
    expect(outcome).to_contain_text("Đã qua QA")


def contact_sheet(browser, views):
    page = browser.new_page(viewport={"width": 1600, "height": 1280}, device_scale_factor=1)

    def tile(view):
        p = OUT / view["screenshots"][0]
        return (
            "<figure><figcaption>"
            + escape(view["device"] + " · " + view["theme"] + " · " + "×".join(map(str, view["viewport"])))
            + '</figcaption><img src="data:image/png;base64,'
            + base64.b64encode(p.read_bytes()).decode("ascii")
            + '"></figure>'
        )

    ordered = [next(v for v in views if v["theme"] == theme and v["device"] == dev) for theme in ("light", "dark") for dev in ("desktop", "tablet", "mobile")]
    page.set_content(
        '<meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#e9eef4;color:#172433;padding:22px;font:16px system-ui}main{display:grid;grid-template-columns:1.65fr 1fr .75fr;gap:18px}figure{margin:0}figcaption{font-weight:600;margin:0 0 6px}img{object-fit:contain;object-position:top left;width:100%;height:545px;display:block}</style><h1>AMC · AI Command Center</h1><main>'
        + "".join(map(tile, ordered))
        + "</main>",
        wait_until="load",
    )
    page.screenshot(path=str(OUT / "overview-contact.png"))
    page.close()


def compare_screens(browser):
    baseline = Path(__file__).resolve().parents[1] / "docs/ui-evidence/pr34-before"
    manifest = json.loads((baseline / "manifest.json").read_text(encoding="utf8"))
    assert manifest["revision"] == "0953285c1c6a70a5c473effb5a69501500e717b5"
    page = browser.new_page(viewport={"width": 1460, "height": 950}, device_scale_factor=1)
    try:
        for size in ("desktop", "tablet", "mobile"):
            name = size + "-light-overview.png"
            old = (baseline / name).read_bytes()
            assert sha256(old).hexdigest() == manifest["images"][name]["sha256"]
            panels = []
            for title, data in (("Trước", old), ("Sau", (OUT / name).read_bytes())):
                img = base64.b64encode(data).decode("ascii")
                panels.append(f'<figure><figcaption>{title}</figcaption><img src="data:image/png;base64,{img}"></figure>')
            html = (
                '<meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;padding:20px;background:#eef1ed;color:#142d24;'
                "font:18px system-ui}h1{font-size:24px;margin:0 0 12px}main{display:grid;grid-template-columns:1fr 1fr;gap:16px}"
                "figure{margin:0}figcaption{margin:0 0 8px;font-weight:bold}img{display:block;max-width:100%;max-height:840px;"
                "object-fit:contain;object-position:top left}</style><h1>AMC · " + size + "</h1><main>" + "".join(panels) + "</main>"
            )
            page.set_content(html, wait_until="load")
            page.screenshot(path=str(OUT / ("before-after-" + size + ".png")))
    finally:
        page.close()


def foreground_membership(browser, api, f):
    viewer = account(api, "thu")
    invite_member(api, f["base"], f["owner"]["headers"], viewer["headers"], email=viewer["email"], role="viewer")
    scope = f["base"] + "/members/" + viewer["user_id"] + "/client-scope"
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    held = {}

    def collection(route):
        if "collection" in held:
            route.continue_()
            return
        held["collection"] = (route, route.fetch())
        page.evaluate("window.__amcCollectionHeld=true")

    def identity(route):
        if "identity" in held:
            route.continue_()
            return
        held["identity"] = route
        page.evaluate("window.__amcIdentityHeld=true")

    try:
        page.goto(BASE + "/?workspace=" + f["tenant"])
        page.route("**" + f["base"] + "/actions", collection)
        authenticate(page, viewer)
        page.wait_for_function("window.__amcCollectionHeld === true")
        expect(page.locator("#workspace-loading")).to_be_visible()
        expect(page.locator("#command-center")).to_be_hidden()
        expect(page.locator("#campaigns-list")).to_be_hidden()
        assert page.locator("#workspace").bounding_box()["height"] >= 800
        capture(page, "desktop-cold-loading")
        initial, answer = held.pop("collection")
        initial.fulfill(response=answer)
        page.evaluate("window.__amcCollectionHeld=false")
        expect(page.locator("#command-campaign-count")).to_have_text("3")
        choose_campaign(page, f["campaigns"][2])
        screen(page, "knowledge")
        page.locator("#knowledge-client").select_option(f["clients"][1]["id"])
        expect(page.locator("#knowledge-brand")).to_have_value(f["brands"][1]["id"])
        page.locator("#refresh").click()
        page.wait_for_function("window.__amcCollectionHeld === true")
        # Dispatch both lifecycle states deterministically. Both HTTP responses are real.
        page.evaluate(
            """()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true}); document.dispatchEvent(new Event('visibilitychange'))}"""
        )
        page.route("**/api/me", identity)
        page.evaluate(
            """()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>false}); document.dispatchEvent(new Event('visibilitychange'))}"""
        )
        page.wait_for_function("window.__amcIdentityHeld === true")
        request_json(api, "PUT", scope, f["owner"], {"client_id": f["clients"][0]["id"]})
        old_route, authorized_before_change = held["collection"]
        with page.expect_response(lambda response: response.url.endswith(f["base"] + "/actions")) as finished:
            old_route.fulfill(response=authorized_before_change)
        finished.value.finished()
        settle(page)
        expect(page.locator("#command-center")).not_to_contain_text(f["campaigns"][2]["name"])
        assert not page.locator("#campaigns-list button[data-action]:visible").count()
        held["identity"].continue_()
        expect(page.locator("body")).to_have_attribute("data-access", "portal")
        expect(page.locator("#knowledge-status")).to_contain_text("Quyền xem hồ sơ đã thay đổi")
        expect(page.locator("#knowledge-status")).to_be_visible()
        expect(page.locator("#command-center")).to_be_hidden()
        for container in ("#knowledge-context", "#knowledge-content", "#knowledge-progress", "#knowledge-org"):
            expect(page.locator(container)).to_be_empty()
        expect(page.locator("#knowledge-client, #knowledge-brand, #knowledge-claim-desk")).to_have_count(0)
        expect(page.locator("#catalog-drawer")).to_be_hidden()
        expect(page.locator("#workspace")).not_to_contain_text(f["brands"][1]["name"])
        expect(page.locator("#workspace")).not_to_contain_text(f["campaigns"][2]["name"])
        current = request_json(api, "GET", "/api/me", viewer)
        assert any(m["tenant_id"] == f["tenant"] and m["role"] == "client_viewer" for m in current["tenants"])
        return "Delayed real collection and membership reads, changed viewer to client portal, no stale private campaign restored"
    finally:
        page.close()


def run():
    assert urlsplit(BASE).hostname in {"localhost", "127.0.0.1", "::1"}
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "tested_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "synthetic": True,
        "measurement_notes": "Loopback PostgreSQL and headless Chromium, device scale 1, no network or CPU throttling. Document timings cover the reloaded login page. Dashboard readiness includes login, API reads and assertions. Campaign switch is a separate interaction.",
        "contrast_scope": "Rendered text pairs in the named surfaces, normal text 4.5:1 and large text 3:1 (WCAG 2.2 SC 1.4.3).",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "views": [],
    }

    def write():
        (OUT / "ui-acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")

    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as api, sync_playwright() as pw:
        f = fixture(api)
        before = db_counts(f["tenant"])
        dataset = source_data(api, f)
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        report["chromium_version"] = browser.version
        try:
            for dev in MATRIX:
                for theme in ("light", "dark"):
                    view = run_view(browser, dev, theme, f, dataset)
                    report["views"].append(view)
                    write()
                    print(f"Captured and verified {dev} {theme}", flush=True)
            report["scope_and_reflow"] = mode_and_scope(browser, api, f)
            report["foreground_membership"] = foreground_membership(browser, api, f)
            assert db_counts(f["tenant"]) == before and before["runs"] == before["ledger_entries"] == 0
            report["postgresql"] = before
            contact_sheet(browser, report["views"])
            compare_screens(browser)
            failures = [{"view": a["view"], "surface": a["surface"], **row} for v in report["views"] for a in v["contrast"] for row in a["failed"]]
            report["failed_contrast_count"] = len(failures)
            unresolved = [row for v in report["views"] for a in v["contrast"] for row in a["unresolved"]]
            report["unresolved_contrast_count"] = len(unresolved)
            required = {f"{dev}-{theme}-{surface}.png" for dev in MATRIX for theme in ("light", "dark") for surface in ("overview", "work", "knowledge")}
            required.add("desktop-cold-loading.png")
            required.update(
                {"before-after-desktop.png", "before-after-tablet.png", "before-after-mobile.png", "desktop-dark-department.png", "mobile-dark-department.png"}
            )
            required.update(
                {"mobile-light-navigation.png", "mobile-dark-catalog.png", "overview-contact.png", "business-light-tablet.png", "solo-dark-empty.png"}
            )
            report["screenshots"] = sorted(required)
            write()
            assert not failures, failures[:8]
            assert not unresolved, unresolved[:8]
            assert all((OUT / image).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for image in required)
            assert json.loads((OUT / "ui-acceptance.json").read_text(encoding="utf8")) == report
        finally:
            browser.close()
    print("PASS real-data command center on desktop, tablet and mobile in both color modes")


if __name__ == "__main__":
    run()
