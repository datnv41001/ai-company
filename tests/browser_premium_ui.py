"""Exercise the authenticated AMC command center on a loopback PostgreSQL fixture."""

import base64
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
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_knowledge import BASE, PROJECT, authenticate, db_counts, post
from identity_fixtures import invite_member, start_registration, verify_registration


OUT = Path(os.getenv("AMC_PREMIUM_EVIDENCE", "premium-ui-evidence"))
MATRIX = {"desktop": (1440, 900), "tablet": (820, 1180), "mobile": (390, 844)}
AUDIT = Path(__file__).with_name("premium_accessibility.js").read_text("utf8")
OWNER_NAME = "Mộc Studio"
EMPTY_NAME = "Studio một thành viên"


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
    owner = account(api, "minh", OWNER_NAME)
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
    return dict(owner=owner, recipient=recipient, tenant=tenant, empty=empty, base=base, clients=clients, brands=brands, campaigns=campaigns)


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
    control.select_option(campaign["id"])
    expect(page.locator("#command-objective")).to_have_text(campaign["objective"])
    expect(page.locator("#command-center")).not_to_have_attribute("aria-busy", "true")


def check_dashboard(page, f, dataset):
    counts = {
        "campaign": len(dataset["campaigns"]),
        "deliverable": len(dataset["deliverables"]),
        "review": sum(d["status"] == "submitted" for d in dataset["deliverables"]),
        "approved": sum(d["status"] == "approved" for d in dataset["deliverables"]),
    }
    for key, value in counts.items():
        expect(page.locator("#command-" + key + "-count")).to_have_text(str(value))
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


def keyboard(page):
    toggle = page.locator("#menu-toggle")
    if toggle.is_visible():
        toggle.focus()
        page.keyboard.press("Enter")
        expect(toggle).to_have_attribute("aria-expanded", "true")
        sidebar = page.locator("#workspace-sidebar")
        assert sidebar.evaluate("el=>el.contains(document.activeElement)")
        for _ in range(3):
            page.keyboard.press("Tab")
            assert sidebar.evaluate("el=>el.contains(document.activeElement)")
        page.keyboard.press("Escape")
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(toggle).to_be_focused()
        return "drawer opened, focus contained, Escape returned focus"
    link = page.locator("#knowledge-nav")
    link.focus()
    page.keyboard.press("Enter")
    assert page.locator("#knowledge-title").is_visible()
    assert page.evaluate("window.location.hash==='#knowledge-title' || document.activeElement.id==='knowledge-title'")
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
    page.locator("#command-campaign").select_option(cold["id"])
    expect(page.locator("#command-center")).to_have_attribute("aria-busy", "true")
    page.wait_for_function("window.__amcRouteHeld === true")
    running = no_motion(page)
    assert not running, running
    expect(page.locator("#command-status")).to_contain_text("Đang tải")
    held[0].continue_()
    expect(page.locator("#command-progress-label")).to_have_text("—")
    expect(page.locator("#command-center")).not_to_have_attribute("aria-busy", "true")
    assert not page.locator("#command-progress").evaluate("n=>n.hasAttribute('value')")
    page.unroute(pattern)
    choose_campaign(page, f["campaigns"][0])
    page.route(pattern, lambda route: route.abort("connectionfailed"), times=1)
    page.locator("#command-campaign").select_option(cold["id"])
    expect(page.locator("#command-status")).to_contain_text("thử lại")
    expect(page.locator("#command-tasks")).not_to_contain_text("Complete client discovery")
    page.locator("#command-refresh").click()
    expect(page.locator("#command-progress-caption")).to_contain_text("Chưa có nhiệm vụ")
    choose_campaign(page, f["campaigns"][0])
    return "real GET paused, network failure then successful readback"


def measurements(page):
    return page.evaluate("""()=>{
       const n=performance.getEntriesByType('navigation')[0], resources=performance.getEntriesByType('resource');
       const fcp=performance.getEntriesByName('first-contentful-paint')[0];
       return {document_dom_content_loaded_ms:Math.round(n.domContentLoadedEventEnd),document_load_ms:Math.round(n.loadEventEnd),
         document_first_contentful_paint_ms:fcp?Math.round(fcp.startTime):null,document_lcp_ms:window.__amcLcp||null,
         same_origin_requests:resources.filter(e=>new URL(e.name).origin===location.origin).length,
         static_transfer_bytes:resources.filter(e=>new URL(e.name).pathname.startsWith('/static/')).reduce((s,e)=>s+e.transferSize,0),
         cumulative_layout_shift:window.__amcCls??null};
    }""")


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
      window.__amcCls=0;
      new PerformanceObserver(list=>{for(const e of list.getEntries())if(!e.hadRecentInput)window.__amcCls+=e.value;}).
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
        selector.select_option(theme)
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        page.reload()
        expect(selector).to_have_value(theme)
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        audits = [contrast(page, "#auth", view)]
        start = perf_counter()
        authenticate(page, f["owner"])
        expect(page.locator("#command-center")).to_be_visible()
        counts = check_dashboard(page, f, dataset)
        ready_ms = round((perf_counter() - start) * 1000)
        settle(page)
        screenshot = capture(page, view + "-overview")
        reflow(page)
        audits.append(contrast(page, "#command-center", view))
        if page.locator("#workspace-sidebar").is_visible() and not page.locator("#menu-toggle").is_visible():
            audits.append(contrast(page, "#workspace-sidebar", view))
        assert not no_motion(page)
        perf = measurements(page)
        perf["login_to_verified_dashboard_ms"] = ready_ms
        start = perf_counter()
        choose_campaign(page, f["campaigns"][1])
        expect(page.locator("#command-progress-label")).to_have_text("—")
        perf["switch_campaign_ms"] = round((perf_counter() - start) * 1000)
        choose_campaign(page, f["campaigns"][0])
        result = {"device": dev, "theme": theme, "viewport": [w, h], "counts": counts, "performance": perf, "screenshots": [screenshot], "contrast": audits}
        result["keyboard"] = keyboard(page)
        if dev == "desktop" and theme == "light":
            result["network_states"] = task_network(page, f)
        page.locator("#knowledge-client").select_option(f["clients"][0]["id"])
        expect(page.locator("#knowledge-name")).to_have_value(f["clients"][0]["name"])
        result["screenshots"].append(capture(page, view + "-knowledge", top="#knowledge-panel"))
        reflow(page)
        audits.append(contrast(page, "#knowledge-panel", view))
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
        page.locator("#workspace-select").select_option(f["empty"])
        expect(page.locator("#command-campaign-count")).to_have_text("0")
        expect(page.locator("#command-deliverable-count")).to_have_text("0")
        expect(page.locator("#command-center")).not_to_contain_text(f["campaigns"][0]["name"])
        expect(page.locator("#command-campaign")).to_be_disabled()
        assert not page.locator("#command-progress").evaluate("n=>n.hasAttribute('value')")
        assert not request_json(api, "GET", "/api/tenants/" + f["empty"] + "/campaigns", f["owner"])
        capture(page, "solo-dark-empty")
        page.set_viewport_size({"width": 320, "height": 700})
        assert reflow(page) == 320
        page.locator("#workspace-select").select_option(f["tenant"])
        expect(page.locator("#command-campaign-count")).to_have_text("3")
        reflow(page)
        page.locator("#switch-account").click()
        scoped = browser.new_context(viewport={"width": 820, "height": 1180}, locale="vi-VN")
        try:
            portal = scoped.new_page()
            task_requests = []
            portal.on("request", lambda req: task_requests.append(req.url) if req.url.endswith("/tasks") else None)
            portal.goto(BASE + "/?workspace=" + f["tenant"])
            authenticate(portal, f["recipient"])
            expect(portal.locator("#command-center")).to_be_hidden()
            expect(portal.locator("#knowledge-panel")).to_be_hidden()
            expect(portal.locator("#workspace")).not_to_contain_text(f["campaigns"][2]["name"])
            assert not task_requests
        finally:
            scoped.close()
        return {"system_preference": True, "checks_at_320px": 2, "empty_totals_zero": True, "recipient_staff_task_requests": 0}
    finally:
        ctx.close()


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

    ordered = [next(v for v in views if v["theme"] == theme and v["device"] == dev) for theme in ("light", "dark") for dev in MATRIX]
    page.set_content(
        '<meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#e9eef4;color:#172433;padding:22px;font:16px system-ui}main{display:grid;grid-template-columns:1.65fr 1fr .75fr;gap:18px}figure{margin:0}figcaption{font-weight:600;margin:0 0 6px}img{object-fit:contain;object-position:top left;width:100%;height:545px;display:block}</style><h1>AMC · AI Command Center</h1><main>'
        + "".join(map(tile, ordered))
        + "</main>",
        wait_until="load",
    )
    page.screenshot(path=str(OUT / "overview-contact.png"))
    page.close()


def run():
    assert urlsplit(BASE).hostname in {"localhost", "127.0.0.1", "::1"}
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "tested_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "synthetic": True,
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
            assert db_counts(f["tenant"]) == before and before["runs"] == before["ledger_entries"] == 0
            report["postgresql"] = before
            contact_sheet(browser, report["views"])
            failures = [{"view": a["view"], "surface": a["surface"], **row} for v in report["views"] for a in v["contrast"] for row in a["failed"]]
            report["failed_contrast_count"] = len(failures)
            write()
            assert not failures, failures[:8]
        finally:
            browser.close()
    print("PASS real-data command center on desktop, tablet and mobile in both color modes")


if __name__ == "__main__":
    run()
