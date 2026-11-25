"""Drive the C2 workspace against a disposable PostgreSQL-backed localhost API."""

import json
import os
from pathlib import Path
import subprocess
from time import perf_counter, sleep
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
from playwright.sync_api import expect, sync_playwright
import psycopg

from identity_fixtures import invite_member, start_registration, verify_registration


PERSONAS = {
    "seller": ("Cửa hàng Mưa Nhẹ", "Áo mưa xanh cỡ L", "Người đi xe đạp", "Tăng đơn hàng trực tuyến"),
    "materials": ("Vật liệu Mái Xanh", "Tấm lợp 0,5 mm bán theo mét vuông", "Nhà thầu miền Nam", "Nhận yêu cầu báo giá sỉ"),
    "service": ("Chăm nhà An Nhiên", "Vệ sinh máy lạnh tại nhà", "Hộ gia đình tại Đà Nẵng", "Tăng lịch hẹn tại chỗ"),
    "agency": ("Khách hàng Sổ Mộc", "Sổ tay A5", "Cửa hàng văn phòng phẩm", "Tìm đối tác bán lẻ"),
    "inhouse": ("Đội Marketing Nắng", "Gói ưu đãi sinh viên", "Giả thuyết · sinh viên năm đầu", "Tăng đơn đăng ký qua email"),
}
FIELDS = ("name", "sells", "audience", "goal")
BRAND = "Thương hiệu chính"
OTHER = "Thương hiệu thứ hai"
LOST_STATUS = "Chưa nhận được xác nhận."
BASE = os.environ["AMC_BROWSER_TEST_URL"]
PROJECT = os.getenv("AMC_BROWSER_MAILBOX_PROJECT")
OUT = Path(os.getenv("AMC_KNOWLEDGE_EVIDENCE", "knowledge-browser-evidence"))


def db_counts(tenant):
    tenant = str(UUID(tenant))
    sql = f"""SELECT json_build_object(
      'postgres', current_setting('server_version'),
      'core_schema', (SELECT max(version) FROM public.amc_schema_versions),
      'workspace_schema', (SELECT max(version) FROM amc_business.versions),
      'runs', (SELECT count(*) FROM public.workforce_runs WHERE tenant_id='{tenant}'),
      'ledger_entries', (SELECT count(*) FROM amc_ops.ledger WHERE tenant='{tenant}'))::text"""
    if PROJECT:
        result = subprocess.run(
            ["docker", "compose", "-p", PROJECT, "exec", "-T", "db", "psql", "-XAt", "-v", "ON_ERROR_STOP=1", "-U", "amc", "-d", "amc"],
            input=sql,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
        return json.loads(db.execute(sql).fetchone()[0])


def user(api, prefix):
    email, password = f"c2-{prefix}-{uuid4().hex}@example.com", uuid4().hex
    auth = start_registration(api, email, password, organization_name="Không gian Marketing mẫu", mode="agency")
    verify_registration(api, email, auth, PROJECT)
    return {**auth, "email": email, "password": password, "headers": {"Authorization": "Bearer " + auth["access_token"]}}


def post(api, path, who, body):
    res = api.post(path, headers=who["headers"], json=body)
    assert res.status_code == 201, (path, res.status_code)
    return res.json()


def fixture(api, owner):
    prefix = "/api/tenants/" + owner["tenant_id"]
    rows = {}
    for code, values in PERSONAS.items():
        client = post(api, prefix + "/clients", owner, {"name": values[0]})["id"]
        brand = post(api, prefix + "/brands", owner, {"client_id": client, "name": BRAND})["id"]
        second = post(api, prefix + "/brands", owner, {"client_id": client, "name": OTHER})["id"] if code == "agency" else None
        rows[code] = (client, brand, second)
    return rows


def login(page, who, tenant):
    page.goto(BASE + "/?workspace=" + tenant)
    authenticate(page, who)


def authenticate(page, who):
    form = page.locator("#login-form")
    form.get_by_label("Email").fill(who["email"])
    form.get_by_label("Mật khẩu").fill(who["password"])
    for attempt in range(3):
        with page.expect_response(lambda r: r.url.endswith("/api/auth/login")) as observed:
            form.get_by_role("button").click()
        result = observed.value
        if result.status != 429:
            assert result.status == 200, result.status
            break
        assert attempt < 2, "Login admission remained closed after its advertised cooldowns"
        delay = int(result.headers["retry-after"])
        expect(page.locator("#notice")).to_contain_text("Vui lòng thử lại sau")
        sleep(delay + 0.2)
    expect(page.locator("#workspace")).to_be_visible()


def select_scope(page, client, brand):
    choose = page.locator("#knowledge-client")
    expect(choose).to_be_visible()
    if choose.input_value() != client:
        choose.select_option(client)
    select = page.locator("#knowledge-brand")
    if select.input_value() != brand:
        select.select_option(brand)
    expect(page.locator("#knowledge-edit")).to_be_visible()


def snapshot(page, tag, width, anchor="#knowledge-panel"):
    page.locator(anchor).evaluate("el => el.scrollIntoView({block:'start'})")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    page.screenshot(path=str(OUT / f"{tag}-{width}.png"), animations="disabled")


def save(page):
    page.locator("#knowledge-edit").get_by_role("button", name="Lưu thay đổi").click()
    expect(page.locator("#knowledge-status")).to_have_text("Đã lưu thay đổi.")


def drop_after_commit(page, endpoint):
    commits = []

    def drop(route):
        if route.request.method != "POST":
            route.continue_()
            return
        acknowledgement = route.fetch()
        assert acknowledgement.status == 201
        commits.append(acknowledgement.json())
        route.abort("connectionreset")

    page.route("**/" + endpoint, drop)
    return commits


def brief_from_profile(page, title):
    page.get_by_role("button", name="Brief nháp", exact=True).click()
    form = page.locator("#knowledge-new-brief")
    form.get_by_label("Tên brief").fill(title)
    # Two submissions from a single double activation share one in-flight intent.
    form.evaluate("f=>{f.requestSubmit();f.requestSubmit()}")


def read_view(api, owner, ids):
    tenant = owner["tenant_id"]
    client, brand, _ = ids
    result = api.get(f"/api/tenants/{tenant}/clients/{client}/brands/{brand}/business-workspace", headers=owner["headers"])
    assert result.status_code == 200
    return result.json()


def switch_tabs(page, title):
    page.get_by_role("button", name=title, exact=True).click()


def exercise_persona(browser, api, owner, ids, code, size):
    width = size["width"]
    p = browser.new_page(viewport=size)
    login(p, owner, owner["tenant_id"])
    select_scope(p, *ids[:2])
    start = perf_counter()
    name, product, audience, goal = PERSONAS[code]
    p.locator("#knowledge-client").focus()
    p.keyboard.press("Tab")
    expect(p.locator("#knowledge-brand")).to_be_focused()
    p.keyboard.press("Tab")
    expect(p.locator("[data-view=company]")).to_be_focused()
    for key, value in (("name", name), ("sells", product)):
        p.locator("#knowledge-" + key).fill(value)
    expect(p.locator("#knowledge-dirty")).to_contain_text("chưa lưu")
    save(p)
    expect(p.locator("#knowledge-progress")).to_contain_text("2/4")
    partial_time = perf_counter() - start
    p.reload()
    authenticate(p, owner)
    expect(p.locator("#knowledge-sells")).to_have_value(product)
    expect(p.locator("#knowledge-goal")).to_have_value("")
    title = "Nghiên cứu · " + name
    started_brief = perf_counter()
    if code == "seller":
        commits = drop_after_commit(p, "business-workspace/briefs")
    brief_from_profile(p, title)
    if code == "seller":
        expect(p.locator("#knowledge-status")).to_contain_text(LOST_STATUS)
        assert len(commits) == 1
        p.reload()
        authenticate(p, owner)
    expect(p.locator("#knowledge-open-title")).to_have_text(title)
    expect(p.locator(".knowledge-brief")).to_contain_text("KPI ban đầu · Chưa có số liệu")
    expect(p.locator(".knowledge-brief")).to_contain_text("Ai thường mua")
    brief_time = perf_counter() - started_brief
    snapshot(p, code + "-brief", width, ".knowledge-brief")
    server = read_view(api, owner, ids)
    assert server["company_revision"] == 1 and len(server["briefs"]) == 1
    switch_tabs(p, "Hồ sơ chung")
    started_finish = perf_counter()
    p.locator("#knowledge-audience").fill(audience)
    p.locator("#knowledge-goal").fill(goal)
    if code == "inhouse":
        recorded = drop_after_commit(p, "business-profile")
        p.locator("#knowledge-edit").get_by_role("button").click()
        expect(p.locator("#knowledge-status")).to_contain_text(LOST_STATUS)
        p.get_by_role("button", name="Kiểm tra kết quả").click()
        expect(p.locator("#knowledge-status")).to_have_text("Đã lưu thay đổi.")
        assert len(recorded) == 1
    else:
        save(p)
    expect(p.locator("#knowledge-progress")).to_contain_text("4/4")
    completed = partial_time + perf_counter() - started_finish
    snapshot(p, code + "-setup", width)
    server = read_view(api, owner, ids)
    assert server["company_revision"] == 2 and server["completion"]["filled"] == 4
    p.close()
    fresh = browser.new_page(viewport=size)
    login(fresh, owner, owner["tenant_id"])
    select_scope(fresh, *ids[:2])
    expect(fresh.locator("#knowledge-audience")).to_have_value(audience)
    switch_tabs(fresh, "Brief nháp")
    fresh.get_by_role("button", name=title).click()
    expect(fresh.locator(".knowledge-brief")).to_contain_text("Ai thường mua")
    expect(fresh.locator(".knowledge-brief")).not_to_contain_text(audience)
    fresh.close()
    return {
        "persona": code,
        "viewport": size,
        "partial_setup_seconds": round(partial_time, 3),
        "four_field_setup_active_seconds": round(completed, 3),
        "first_draft_action_seconds": round(brief_time, 3),
        "elapsed_first_open_to_draft_seconds": round(started_brief + brief_time - start, 3),
        "same_person_retyped_company_fields_for_second_brand": 0 if code == "agency" else None,
        "draft_count": len(server["briefs"]),
        "company_revision": server["company_revision"],
    }


def extra_cases(browser, api, owner, reader, rows, size):
    width = size["width"]
    tenant = owner["tenant_id"]
    p = browser.new_page(viewport=size)
    login(p, owner, tenant)
    client, brand, second = rows["agency"]
    select_scope(p, client, brand)
    switch_tabs(p, "Theo thương hiệu")
    p.locator("#knowledge-name-mode").select_option("override")
    p.locator("#knowledge-edit").get_by_role("button").click()
    expect(p.locator("#knowledge-name")).to_be_focused()
    p.locator("#knowledge-name").fill("Sổ Mộc bán lẻ")
    p.locator("#knowledge-audience-mode").select_option("empty")
    save(p)
    expect(p.locator("#knowledge-progress")).to_contain_text("3/4")
    assert read_view(api, owner, rows["agency"])["fields"]["audience"]["mode"] == "empty"
    p.locator("#knowledge-brand").select_option(second)
    expect(p.locator("#knowledge-progress")).to_contain_text("4/4")
    switch_tabs(p, "Theo thương hiệu")
    expect(p.locator("#knowledge-name-mode")).to_have_value("inherit")
    expect(p.locator("#knowledge-content")).to_contain_text(PERSONAS["agency"][0])
    snapshot(p, "agency-inherit", width)
    p.locator("#knowledge-brand").select_option(brand)
    switch_tabs(p, "Theo thương hiệu")
    p.locator("#knowledge-name-mode").select_option("inherit")
    save(p)
    v = read_view(api, owner, rows["agency"])
    assert v["fields"]["name"]["value"] == PERSONAS["agency"][0] and v["fields"]["name"]["override_revision"] == 2

    # Hold a *real* API read after response receipt. Releasing it exercises the
    # generation guard independently of the browser's AbortController behavior.
    p.evaluate(
        """needle => {
      const original = window.fetch;
      window.fetch = async (...args) => {
        const res = await original(...args);
        if (!window.heldRead && String(args[0]).endsWith(needle)) {
          window.heldRead = true;
          await new Promise(done => {window.releaseKnowledgeRead = done;});
        }
        return res;
      };
    }""",
        "/brands/" + second + "/business-workspace",
    )
    p.locator("#knowledge-brand").select_option(second)
    p.wait_for_function("typeof window.releaseKnowledgeRead === 'function'")
    select_scope(p, *rows["service"][:2])
    p.evaluate("() => window.releaseKnowledgeRead()")
    expect(p.locator("#knowledge-name")).to_have_value(PERSONAS["service"][0])
    # The authorized client selector still lists the agency client by name.
    # Only the active workspace content and its field values should have changed.
    expect(p.locator("#knowledge-content")).not_to_contain_text("Sổ Mộc")
    expect(p.locator("#knowledge-sells")).to_have_value(PERSONAS["service"][1])
    p.close()

    p, other = [browser.new_page(viewport=size) for _ in range(2)]
    for page in (p, other):
        login(page, owner, tenant)
        select_scope(page, *rows["inhouse"][:2])
    p.locator("#knowledge-goal").fill("Mục tiêu từ tab thứ nhất")
    save(p)
    other.locator("#knowledge-goal").fill("Bản riêng của người đang sửa")
    other.locator("#knowledge-edit").get_by_role("button").click()
    diff = other.locator(".knowledge-diff")
    expect(diff).to_contain_text("Mục tiêu từ tab thứ nhất")
    expect(diff).to_contain_text("Bản riêng của người đang sửa")
    snapshot(other, "inhouse-conflict", width, "#knowledge-content")
    other.get_by_role("button", name="Áp dụng các trường đã chọn").click()
    expect(other.locator("#knowledge-status")).to_be_focused()
    diff.get_by_role("checkbox").check()
    other.get_by_role("button", name="Áp dụng các trường đã chọn").click()
    expect(other.locator("#knowledge-status")).to_have_text("Đã lưu thay đổi.")
    assert read_view(api, owner, rows["inhouse"])["company_revision"] == 4
    p.close()
    other.close()

    port = browser.new_page(viewport=size)
    login(port, reader, tenant)
    select_scope(port, *rows["service"][:2])
    expect(port.locator("#knowledge-edit")).to_contain_text("quyền xem")
    path = "/api/tenants/" + tenant + "/members/" + reader["user_id"] + "/client-scope"
    changed = api.put(path, headers=owner["headers"], json={"client_id": rows["service"][0]})
    assert changed.status_code == 200
    port.locator("#refresh").click()
    expect(port.locator("#knowledge-status")).to_contain_text("Quyền xem hồ sơ đã thay đổi")
    expect(port.locator("#knowledge-edit")).to_have_count(0)
    port.locator("#switch-account").click()
    authenticate(port, reader)
    if port.locator("#workspace-select").input_value() != tenant:
        port.locator("#workspace-select").select_option(tenant)
    expect(port.locator("#knowledge-panel")).to_be_hidden()
    assert PERSONAS["service"][1] not in port.locator("#knowledge-panel").inner_text()
    port.close()

    switching = browser.new_page(viewport=size)
    login(switching, owner, tenant)
    select_scope(switching, *rows["service"][:2])
    switching.evaluate(
        """needle => {
      const original=window.fetch;
      window.fetch=async (...args) => {
        const result=await original(...args);
        if (String(args[0]).endsWith(needle)) {
          window.previousUserReadArrived=true;
          await new Promise(resolve => window.addEventListener('pagehide',resolve,{once:true}));
        }
        return result;
      };
    }""",
        "/brands/" + rows["materials"][1] + "/business-workspace",
    )
    switching.locator("#knowledge-client").select_option(rows["materials"][0])
    switching.wait_for_function("window.previousUserReadArrived === true")
    switching.locator("#switch-account").click()
    authenticate(switching, reader)
    expect(switching.locator("#knowledge-panel")).to_be_hidden()
    assert PERSONAS["materials"][1] not in switching.locator("body").inner_text()
    assert PERSONAS["service"][1] not in switching.evaluate("JSON.stringify(sessionStorage)")
    switching.close()


def run():
    assert urlsplit(BASE).hostname in ("localhost", "127.0.0.1", "::1")
    OUT.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report = {
        "tested_revision": sha,
        "synthetic": True,
        "timing_method": "Automated Chromium interaction and API waits, excludes human think time.",
        "personas": [],
        "database": [],
    }
    with httpx.Client(base_url=BASE, timeout=20, trust_env=False) as api, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        report["chromium_version"] = browser.version
        for width, height in ((1280, 850), (390, 844)):
            size = {"width": width, "height": height}
            owner = user(api, "agency")
            reader = user(api, "viewer")
            invite_member(api, "/api/tenants/" + owner["tenant_id"], owner["headers"], reader["headers"], email=reader["email"], role="viewer")
            rows = fixture(api, owner)
            before = db_counts(owner["tenant_id"])
            for code in PERSONAS:
                report["personas"].append(exercise_persona(browser, api, owner, rows[code], code, size))
                print(f"PASS {code} {width}x{height}", flush=True)
            extra_cases(browser, api, owner, reader, rows, size)
            after = db_counts(owner["tenant_id"])
            assert before == after and before["runs"] == before["ledger_entries"] == 0
            report["database"].append({"viewport": size, "before": before, "after": after})
            print(f"PASS context, inheritance, conflict, permission and PostgreSQL readback {width}x{height}", flush=True)
        browser.close()
    (OUT / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run()
