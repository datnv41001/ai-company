"""Cross-module customer journeys on five fresh organizations per real Chromium viewport."""

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_catalog import enter_item
from browser_claim_desk import ensure_private_state
from browser_knowledge import BASE, PROJECT, authenticate, db_counts, login, post, save, select_scope, user
from identity_fixtures import invite_member, start_registration, verify_registration
from knowledge_fixtures import accepted, call, revision


OUT = Path(os.environ.get("AMC_C2_ACCEPTANCE_EVIDENCE", "knowledge-center-evidence"))
CASES = {
    "seller": ("Cửa hàng Mưa Nhẹ", "Áo mưa xanh cỡ L", "Người đạp xe", "Tăng đơn hàng áo mưa", "Bề mặt mờ"),
    "materials": ("Mái Xanh B2B", "Tấm lợp 0,5 mm", "Nhà thầu mái nhà", "Tăng báo giá theo mét vuông", "Bề mặt mờ"),
    "service": ("Chăm nhà Nắng", "Vệ sinh máy lạnh", "Hộ dân Đà Nẵng", "Tăng lịch hẹn tại chỗ", "Dịch vụ tại chỗ"),
    "agency": ("Khách hàng Sổ Mộc", "Sổ tay A5", "Cửa hàng văn phòng", "Tìm thêm đại lý", "Bo tròn"),
    "inhouse": ("Học cùng Nắng", "Gói học trực tuyến", "Sinh viên năm đầu", "Tăng đăng ký theo email", "Dịch vụ trực tuyến"),
}


def setup_scope(api, code):
    company = CASES[code][0]
    mode = "agency" if code == "agency" else "inhouse"
    address = f"journey-{code}-{uuid4().hex}@example.com"
    password = uuid4().hex
    auth = start_registration(api, address, password, organization_name=company, mode=mode)
    verify_registration(api, address, auth, PROJECT)
    owner = {**auth, "email": address, "password": password, "headers": {"Authorization": "Bearer " + auth["access_token"]}}
    tenant = auth["tenant_id"]
    base = "/api/tenants/" + tenant
    client = post(api, base + "/clients", owner, {"name": company})["id"]
    brand = post(api, base + "/brands", owner, {"client_id": client, "name": company + " · Chính"})["id"]
    return owner, tenant, client, brand, base + f"/clients/{client}/brands/{brand}"


def get(api, path, actor, **params):
    reply = api.get(path, headers=actor["headers"], params=params)
    assert reply.status_code == 200, (path, reply.status_code)
    return reply.json()


def capture(page, viewport, persona, moment, element):
    element.evaluate("node=>node.scrollIntoView({block:'start'})")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    name = f"{persona}-{viewport['width']}-{moment}.png"
    page.screenshot(path=str(OUT / name), animations="disabled")
    return name


def open_catalog(page):
    drawer = page.locator("#catalog-drawer")
    if not drawer.evaluate("node=>node.open"):
        drawer.locator("summary").click()
    pane = page.locator("#catalog-pane")
    expect(pane.get_by_label("Loại dữ liệu")).to_be_visible()
    return pane


def catalog_record(api, prefix, who, kind, *, code=None, label=None):
    rows = get(api, prefix + "/catalog/items", who, kind=kind)["items"]
    hits = [r for r in rows if (code is None or r.get("code") == code) and (label is None or r["label"] == label)]
    assert len(hits) == 1, (kind, len(hits))
    return hits[0]


def claim_fixture(api, who, prefix, wording, placement, *, private=False, approve=True):
    """Synthetic source material, bound to the same catalog revisions entered through the UI."""
    k = prefix + "/knowledge"
    assertion = {"placement": placement, "category": "description", "wording": wording, "qualifiers": []}
    nonce = uuid4().hex
    markers = [nonce + x for x in ("-document", "-issuer", "-locator", "-excerpt", "-review")]
    visibility = "restricted" if private else "public"
    source = revision(
        api,
        who,
        k,
        "sheet-" + nonce,
        "source",
        {
            "publisher": markers[1] if private else "Nhóm kiểm thử",
            "document": markers[0] if private else "Phiếu đối chiếu sản phẩm mẫu",
            "valid_until": "2099-01-01T00:00:00Z",
            "entries": [{"locator": markers[2] if private else "Mục A", "excerpt": markers[3] if private else wording, "assertion": assertion}],
        },
        visibility,
    )
    bound = revision(
        api, who, k, "row-" + nonce, "binding", {"source": source["id"], "locator": markers[2] if private else "Mục A", "assertion": assertion}, visibility
    )
    claim = revision(api, who, k, "statement-" + nonce, "claim", {"binding": bound["id"], "assertion": assertion}, approve=False)
    if approve:
        accepted(
            call(
                api,
                who,
                k,
                "/revisions/" + claim["id"] + "/events",
                state="approved",
                expected_sequence=0,
                expected_digest=claim["digest"],
                reason=markers[4] if private else "Đã kiểm tra phiếu tổng hợp",
            )
        )
    return claim, source, [*markers, source["id"], bound["id"]]


def open_claim(page, claim):
    page.get_by_role("button", name="Nguồn và nhận định", exact=True).click()
    desk = page.locator("#knowledge-claim-desk")
    desk.get_by_label("Chọn nhận định").select_option(claim["id"])
    return desk


def current_brief(api, prefix, owner):
    briefs = get(api, prefix + "/business-workspace", owner)["briefs"]
    assert len(briefs) == 1
    return get(api, prefix + "/business-workspace/briefs/" + briefs[0]["id"], owner)


def create_brief(page, title, choices):
    page.get_by_role("button", name="Brief nháp", exact=True).click()
    form = page.locator("#knowledge-new-brief")
    form.get_by_label("Tên brief").fill(title)
    if choices:
        form.get_by_role("button", name="Chọn dữ liệu từ danh mục").click()
        for field, label in choices.items():
            select = form.locator("#brief-" + field)
            opt = select.locator("option").filter(has_text=label)
            expect(opt).to_have_count(1)
            select.select_option(value=opt.get_attribute("value"))
    form.get_by_role("button", name="Tạo brief nháp").click()
    expect(page.locator("#knowledge-open-title")).to_have_text(title)


def offer_scenarios(api, owner, base, pane, prod, market, code):
    scope = {"product": prod["id"], "market": market["id"], "region": "VN-DN" if code == "service" else "VN-HN", "channel": "web", "locale": "vi-VN"}
    enter_item(
        pane, "policy", {**scope, "buyer": "wholesale" if code == "materials" else "retail", "warranty": "12 months" if code == "materials" else "6 months"}
    )
    policy = catalog_record(api, base, owner, "policy")
    terms = {"policy": policy["id"], "currency": "VND", "unit": "m²" if code == "materials" else "service", "basis_quantity": "1", "tax": "included"}
    if code == "materials":
        for amount, minimum, maximum in (("125000", "200", "399"), ("115000", "400", "799")):
            enter_item(pane, "offer", {**scope, **terms, "amount": amount, "moq": "200", "tier_min": minimum, "tier_max": maximum})
        offers = get(api, base + "/catalog/items", owner, kind="offer")["items"]
        prices = [get(api, base + "/knowledge/revisions/" + item["id"], owner)["data"]["price"] for item in offers]
        assert sorted((p["amount_minor"], p["tier_min"], p["tier_max"]) for p in prices) == [(115000, 400, 799), (125000, 200, 399)]
        assert all(p["moq"] == 200 and p["currency"] == "VND" and p["unit"] == "m²" for p in prices)
        return {"tiers_checked": len(prices), "minimum_order": 200, "selling_unit": "m²"}
    future = datetime.now(timezone.utc) + timedelta(days=5)

    def local_field(value):
        return value.strftime("%Y-%m-%dT%H:%M")

    enter_item(
        pane,
        "offer",
        {
            **scope,
            **terms,
            "amount": "250000",
            "moq": "1",
            "tier_min": "1",
            "valid_from": local_field(future),
            "valid_until": local_field(future + timedelta(days=10)),
        },
    )
    row = catalog_record(api, base, owner, "offer")
    assert row["state"] == "pending_effective", row["state"]
    return {"future_offer_state": row["state"], "region": scope["region"]}


def editor_projection(api, browser, size, owner, t, c, b, prefix, claim, source, markers, wording):
    editor = user(api, "scoped-editor")
    invite_member(api, "/api/tenants/" + t, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    page = browser.new_page(viewport=size)
    observed = []

    def network(response):
        if response.request.resource_type == "fetch" and "/api/tenants/" in response.url:
            observed.append(response.text())

    page.on("response", network)
    try:
        login(page, editor, t)
        select_scope(page, c, b)
        desk = open_claim(page, claim)
        expect(desk.get_by_role("heading", name="Câu chữ công khai còn hiệu lực")).to_be_visible()
        expect(desk).to_contain_text(wording)
        expect(desk).to_contain_text("Chi tiết bằng chứng nằm ngoài phạm vi hiển thị")
        ensure_private_state(page, markers, observed)
        picture = capture(page, size, "service", "public-wording", desk)
        accepted(
            call(
                api,
                owner,
                prefix + "/knowledge",
                "/revisions/" + source["id"] + "/events",
                state="disputed",
                expected_sequence=1,
                expected_digest=source["digest"],
                reason="Đang đối chiếu lại dữ kiện tổng hợp",
            )
        )
        desk.get_by_role("button", name="Kiểm tra lại hiệu lực").click()
        expect(desk).to_contain_text("Chưa đủ điều kiện dùng câu này")
        ensure_private_state(page, markers, observed)
        return {"filtered_response_count": len(observed), "forbidden_markers_checked": len(markers), "source_dispute_invalidated": True, "screenshot": picture}
    finally:
        page.close()


def agency_switch(api, page, owner, t, c, brand, base, sku):
    other_client = post(api, "/api/tenants/" + t + "/clients", owner, {"name": "Khách hàng Giấy Mới"})["id"]
    other_brand = post(api, "/api/tenants/" + t + "/brands", owner, {"client_id": other_client, "name": "Giấy Mới · Chính"})["id"]
    sibling = post(api, "/api/tenants/" + t + "/brands", owner, {"client_id": c, "name": "Sổ Mộc · Cộng tác"})["id"]
    other_prefix = f"/api/tenants/{t}/clients/{other_client}/brands/{other_brand}"
    page.reload()
    authenticate(page, owner)
    select_scope(page, other_client, other_brand)
    pane = open_catalog(page)
    other_name = "Sổ vuông của Giấy Mới"
    enter_item(pane, "product", {"name": other_name, "code": sku})
    second = catalog_record(api, other_prefix, owner, "product", code=sku)
    first = catalog_record(api, base, owner, "product", code=sku)
    assert first["id"] != second["id"]
    select_scope(page, c, sibling)
    expect(page.locator("#knowledge-name")).to_have_value(CASES["agency"][0])
    select_scope(page, c, brand)
    pane = open_catalog(page)
    page.evaluate(
        """path=>{
      const fetchOriginal=window.fetch;
      window.fetch=async (...args)=>{
        const response=await fetchOriginal(...args);
        if (!window.heldCatalog && String(args[0]).includes(path)) {
          window.heldCatalog=true;
          const bytes=await response.arrayBuffer();
          await new Promise(release=>{window.releaseCatalog=release;});
          // Deliver precisely what PostgreSQL-backed HTTP returned, even after the old
          // request was canceled. Observe consumption before checking the visible state.
          const delayed=new Response(bytes,{status:response.status,headers:response.headers});
          const parse=delayed.json.bind(delayed);
          delayed.json=async ()=>{
            const result=await parse();
            setTimeout(()=>{window.catalogBodyConsumed=true;},0);
            return result;
          };
          return delayed;
        }
        return response;
      };
    }""",
        base + "/catalog/items/" + first["id"],
    )
    pane.get_by_label("Loại dữ liệu").select_option("product")
    pane.get_by_role("button", name=first["label"], exact=True).click()
    page.wait_for_function("Boolean(window.releaseCatalog)")
    select_scope(page, other_client, other_brand)
    pane = open_catalog(page)
    pane.get_by_label("Loại dữ liệu").select_option("product")
    pane.get_by_role("button", name=other_name, exact=True).click()
    expect(pane.locator(".catalog-detail")).to_contain_text(other_name)
    page.evaluate("() => window.releaseCatalog()")
    page.wait_for_function("window.catalogBodyConsumed === true")
    expect(pane.locator(".catalog-detail")).not_to_contain_text(first["label"])
    expect(pane.locator(".catalog-detail")).to_contain_text(other_name)
    select_scope(page, c, brand)
    return {"same_code_distinct_revisions": True, "sibling_inherited_company_name": True, "late_catalog_read_fenced": True}


def exercise(api, browser, size, code):
    owner, t, c, b, base = setup_scope(api, code)
    company, product_name, audience, objective, wording = CASES[code]
    report = {"persona": code, "viewport": size, "screenshots": []}
    original = get(api, "/api/me", owner)["tenants"]
    mode = "agency" if code == "agency" else "inhouse"
    assert len(original) == 1 and original[0]["tenant_id"] == t and original[0]["mode"] == mode
    report["workspace_mode"] = mode
    before = db_counts(t)
    deliveries_before = {kind: get(api, "/api/tenants/" + t + "/" + kind, owner) for kind in ("actions", "deliverables")}
    assert not any(deliveries_before.values())
    page = browser.new_page(viewport=size, locale="vi-VN", timezone_id="UTC")
    try:
        login(page, owner, t)
        select_scope(page, c, b)
        start = perf_counter()
        for key, val in zip(("name", "sells", "audience", "goal"), CASES[code][: 2 if code == "seller" else 4]):
            page.locator("#knowledge-" + key).fill(val)
        save(page)
        report["setup_seconds"] = round(perf_counter() - start, 3)
        brief_title = "Nghiên cứu · " + company
        choice_labels = {}
        if code == "seller":
            create_brief(page, brief_title, {})
            report["first_draft_seconds"] = round(perf_counter() - start, 3)
            assert get(api, "/api/tenants/" + t + "/recipients", owner) == []
            draft = current_brief(api, base, owner)
            assert draft["missing"] == ["audience", "goal"] and not draft.get("selections")
            report["solo_first_draft"] = {"original_workspaces": len(original), "portal_recipients": 0, "filled_fields": 2}
            report["screenshots"].append(capture(page, size, code, "partial-brief", page.locator(".knowledge-brief")))
            page.get_by_role("button", name="Hồ sơ chung", exact=True).click()
        pane = open_catalog(page)
        sku = "SHARED-A5" if code == "agency" else "SKU-" + code.upper()
        kind = "service" if code in ("service", "inhouse") else "product"
        enter_item(pane, kind, {"name": product_name, "code": sku})
        prod = catalog_record(api, base, owner, kind, code=sku)
        enter_item(pane, "market", {"name": "Thị trường Việt Nam", "code": "VN-TEST", "locales": "vi-VN"})
        market = catalog_record(api, base, owner, "market", code="VN-TEST")
        variant = None
        if code == "seller":
            enter_item(pane, "variant", {"name": "Xanh cỡ L", "code": "RAIN-BLUE-L", "product": prod["id"]})
            variant = catalog_record(api, base, owner, "variant", code="RAIN-BLUE-L")
        if code in ("materials", "service"):
            report["commerce"] = offer_scenarios(api, owner, base, pane, prod, market, code)
        if code == "agency":
            report["isolation"] = agency_switch(api, page, owner, t, c, b, base, sku)
            pane = open_catalog(page)
        if code == "inhouse":
            enter_item(pane, "icp", {"name": audience, "description": "Giả thuyết của nhóm Marketing", "basis": "hypothesis", "needs": "Học linh hoạt"})
            icp = catalog_record(api, base, owner, "icp", label=audience)
            expect(pane).to_contain_text("Chưa liên kết chứng cứ.")
            enter_item(pane, "objective", {"name": objective, "owner": "Trưởng nhóm Marketing", "level": "brand"})
            goal = catalog_record(api, base, owner, "objective", label=objective)
            enter_item(
                pane,
                "kpi",
                {
                    "name": "Lượt đăng ký đủ điều kiện",
                    "objective": goal["id"],
                    "unit": "count",
                    "method": "Đếm trong CRM",
                    "window": "30 ngày",
                    "owner": "Phụ trách phân tích",
                    "target": "100",
                },
                approve=False,
            )
            kpi = catalog_record(api, base, owner, "kpi", label="Lượt đăng ký đủ điều kiện")
            kd = get(api, base + "/catalog/items/" + kpi["id"], owner)
            assert {"baseline", "actual"} <= set(kd["missing_fields"]) and kd["data"]["target"] == "100"
            report["kpi"] = {
                "target": "100",
                "missing": kd["missing_fields"],
                "audience_evidence_state": get(api, base + "/catalog/items/" + icp["id"], owner)["evidence_state"],
            }
            choice_labels = {"product": product_name, "audience": audience, "objective": objective}
        elif code != "seller":
            choice_labels = {"product": product_name}
        report["screenshots"].append(capture(page, size, code, "catalog", pane.locator(".catalog-detail") if code != "agency" else pane))
        placement = {
            "product": prod["id"],
            "variant": variant["id"] if variant else None,
            "market": market["id"],
            "locale": "vi-VN",
            "channel": "email" if code == "inhouse" else "web",
            "region": "VN-DN" if code == "service" else "VN-HN",
        }
        fixture_start = perf_counter()
        claim, source, markers = claim_fixture(api, owner, base, wording, placement, private=code == "service", approve=code != "materials")
        report["evidence_fixture_seconds"] = round(perf_counter() - fixture_start, 3)
        desk = open_claim(page, claim)
        if code == "materials":
            section = desk.locator("section").filter(has=page.get_by_role("heading", name="Duyệt nhận định", exact=True))
            section.get_by_label("Quyết định", exact=True).select_option("approved")
            section.get_by_label("Lý do quyết định").fill("Đã đối chiếu bề mặt tấm lợp với phiếu mẫu")
            section.get_by_role("button", name="Ghi quyết định").click()
            expect(page.locator("#knowledge-status")).to_contain_text("Đã ghi quyết định")
        expect(desk).to_contain_text(wording)
        expect(desk).to_contain_text(product_name)
        if code == "service":
            report["limited_editor"] = editor_projection(api, browser, size, owner, t, c, b, base, claim, source, markers, wording)
        else:
            report["screenshots"].append(capture(page, size, code, "claim", desk))
        if code != "seller":
            create_brief(page, brief_title, choice_labels)
            report["first_draft_seconds"] = round(perf_counter() - start, 3)
        draft = current_brief(api, base, owner)
        for key, label in choice_labels.items():
            pinned = draft["selections"][key]
            assert pinned["label"] == label and pinned["digest"] and pinned["revision"] > 0
        if code == "inhouse":
            assert draft["selections"]["audience"]["basis"] == "hypothesis"
        report["pinned_selection_kinds"] = sorted(draft.get("selections", {}))
        page.reload()
        authenticate(page, owner)
        page.get_by_role("button", name="Brief nháp", exact=True).click()
        page.get_by_role("button", name=brief_title, exact=True).click()
        expect(page.locator("#knowledge-open-title")).to_have_text(brief_title)
        for label in choice_labels.values():
            expect(page.locator(".knowledge-brief")).to_contain_text(label)
        assert current_brief(api, base, owner) == draft
        report["screenshots"].append(capture(page, size, code, "pinned-brief", page.locator(".knowledge-brief")))
        assert get(api, "/api/me", owner)["tenants"] == original
        assert db_counts(t) == before and before["runs"] == before["ledger_entries"] == 0
        for kind, prior in deliveries_before.items():
            assert get(api, "/api/tenants/" + t + "/" + kind, owner) == prior
        report["external_actions_created"] = 0
        report["deliverables_created"] = 0
        report["database"] = before
        return report
    finally:
        page.close()


def run():
    assert urlsplit(BASE).hostname in {"localhost", "127.0.0.1", "::1"}
    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "tested_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "synthetic": True,
        "journeys": [],
        "timing": "Wall time from first field entry through saved brief, including API/fixture work, readback, and any authentication wait. Automated interaction on synthetic data.",
    }
    with httpx.Client(base_url=BASE, timeout=30, trust_env=False) as api, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        result["chromium_version"] = browser.version
        try:
            for width, height in ((1280, 850), (390, 844)):
                for code in CASES:
                    journey = exercise(api, browser, {"width": width, "height": height}, code)
                    result["journeys"].append(journey)
                    (OUT / "journeys.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"PASS joined {code} {width}x{height}", flush=True)
        finally:
            browser.close()
    assert len(result["journeys"]) == 10


if __name__ == "__main__":
    run()
