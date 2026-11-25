"""Capture completed Marketing Studio work via ordinary Chromium/HTTP, with receipt attribution."""

import gzip
import json
import os
from time import monotonic
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright
import httpx
import pytest
from sqlalchemy.orm import Session

from app import c3_assets
from app.models import Deliverable
from app.revision_qa import evaluate
from app.workforce_models import WorkforceRun
from browser_c3_content_gate import client, local_api  # noqa: F401 -- file-scoped HTTP/SQLite fixture
from c3_browser_themes import capture_themes
from identity_fixtures import invite_member, start_registration, verify_registration
from test_workforce import workforce as workforce_fixture

workforce = workforce_fixture
ROOT = Path(__file__).resolve().parents[1]


def capture_completed(browser, origin, tenant, email, password, document_id, workflow, out):
    """Works against either the live disposable PostgreSQL model run or a labelled synthetic receipt replay."""
    strategy = workflow == c3_assets.RESEARCH
    prefix = "wf03" if strategy else "wf13"
    sessions = []
    for i, (width, height) in enumerate(((1280, 850), (820, 1180), (390, 844))):
        page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
        try:
            page.goto(origin + f"/?workspace={tenant}#/reviews")
            login = page.locator("#login-form")
            login.get_by_label("Email").fill(email)
            login.get_by_label("Mật khẩu").fill(password)
            login.get_by_role("button").click()
            expect(page.locator("#workspace")).to_be_visible()
            page.evaluate("location.hash='/reviews'")
            pane = page.locator("#review-panel")
            pane.get_by_text("Soạn và bàn giao cho khách", exact=True).click()
            pane.get_by_label("Bản làm việc").select_option(document_id)
            panel = pane.locator(".marketing-studio")
            started = monotonic()
            panel.locator("summary").first.focus()
            panel.locator("summary").first.press("Enter")
            nav = panel.locator(".studio-nav")
            nav.get_by_role("button", name="Chiến lược" if strategy else "Nội dung trang", exact=True).click()
            field = panel.get_by_label("Cách triển khai" if strategy else "Giá trị cho người mua", exact=True)
            expect(field).not_to_have_value("")
            open_ms = round((monotonic() - started) * 1000)
            if i == 0:
                revised = (
                    "So sánh hai cách trình bày cùng một dữ kiện, rồi ghi nhận hành động đã chọn trong nhiệm vụ."
                    if strategy
                    else "Đối chiếu các điều kiện áp dụng được nêu dưới đây trước khi lựa chọn."
                )
                field.fill(revised)
                with page.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/studio")) as saved:
                    panel.get_by_role("button", name="Lưu bản biên tập").click()
                assert saved.value.ok, saved.value.text()
                expect(field).to_have_value(revised)
            public = panel.locator("details").filter(has=page.get_by_text("Bản xem trước dành cho khách", exact=True)).first
            public.locator("summary").first.focus()
            public.locator("summary").first.press("Enter")
            expect(public.locator("h5")).to_be_visible()
            public.locator("summary").first.press("Enter")
            assert page.evaluate("document.documentElement.scrollWidth") == width
            nav.evaluate("e=>e.scrollIntoView({block:'start'})")
            expect(panel.get_by_role("heading", name="Nguồn được duyệt")).to_be_attached()
            capture_themes(page, out / f"{prefix}-completed-{width}.png")
            if not strategy:
                nav.get_by_role("button", name="SEO", exact=True).click()
                expect(panel.get_by_label("Tiêu đề SEO", exact=True)).not_to_have_value("")
                nav.evaluate("e=>e.scrollIntoView({block:'start'})")
                capture_themes(page, out / f"{prefix}-seo-{width}.png")
            sessions.append(
                {
                    "viewport": [width, height],
                    "browser": browser.version,
                    "themes": ["light", "dark"],
                    "scroll_width": page.evaluate("document.documentElement.scrollWidth"),
                    "keyboard_open_to_fields_ms": open_ms,
                }
            )
        finally:
            page.close()
    return sessions


def capture_live(base_url, actor, run_id, workflow, output_dir):
    if urlsplit(base_url).hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Use a disposable loopback HTTP server")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=base_url, trust_env=False, timeout=30) as api:
        headers = actor.get("headers")
        if not headers:
            login = api.post("/api/auth/login", json={"email": actor["email"], "password": actor["password"]})
            login.raise_for_status()
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        report = api.get(f"/api/tenants/{actor['tenant']}/workforce/runs/{run_id}", headers=headers)
        report.raise_for_status()
        row = report.json()
        assert row["marketing_artifacts"]["workflow"] == workflow and row["deliverable_id"]
        path = f"/api/tenants/{actor['tenant']}/deliverables/{row['deliverable_id']}/studio"
        initial = api.get(path, headers=headers)
        initial.raise_for_status()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
            try:
                sessions = capture_completed(browser, base_url, actor["tenant"], actor["email"], actor["password"], row["deliverable_id"], workflow, out)
            finally:
                browser.close()
        current = api.get(path, headers=headers)
        current.raise_for_status()
        assert current.json()["revision"] == initial.json()["revision"] + 1
        result = {
            "run_id": run_id,
            "workflow": workflow,
            "document": row["deliverable_id"],
            "source": "live model workflow and PostgreSQL",
            "initial_revision": initial.json()["revision"],
            "edited_revision": current.json()["revision"],
            "sessions": sessions,
        }
        (out / ("wf03-live.json" if workflow == c3_assets.RESEARCH else "wf13-live.json")).write_text(json.dumps(result, indent=2), encoding="utf8")
        return result


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_completed_receipt_replay(api, workforce):
    owner, assigned, _, base, _, scope, engine, _ = workforce
    email, password = f"studio-{uuid4().hex}@example.com", uuid4().hex
    actor = start_registration(api, email, password, organization_name="Studio synthetic editor", mode="agency")
    verify_registration(api, email, actor)
    invite_member(api, base, owner["headers"], {"Authorization": "Bearer " + actor["access_token"]}, email=email, role="editor")
    source = ROOT / "docs/evaluation/c3-holdout-v1/first-pass.jsonl.gz"
    cases = {r["id"]: r for r in json.loads((ROOT / "tests/evaluation/c3/holdout-v1.json").read_text(encoding="utf8"))["cases"]}
    with gzip.open(source, "rt", encoding="utf8") as stream:
        rows = [r["record"] for line in stream if (r := json.loads(line))["series"] == "paired-upgraded" and r["record"]["case"] in ("agency-01", "agency-02")]
    out = Path(os.environ.get("AMC_STUDIO_EVIDENCE", "knowledge-browser-evidence/marketing-studio"))
    out.mkdir(parents=True, exist_ok=True)
    results = []
    with local_api() as origin, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            for rec in rows:
                assert rec["state"] == "awaiting_qa" and rec["deliverable"]["id"] and rec["input_tokens"]
                case = cases[rec["case"]]
                response = api.post(
                    base + "/workforce/briefs",
                    headers=owner["headers"],
                    json={"campaign_id": scope.campaign, "recipient_id": assigned["id"], "title": case["product"]},
                )
                assert response.status_code == 201, response.text
                brief = response.json()
                p = {**case, "task_intent": {}}
                facts = []
                # Bind handles to the content actually recorded by the Qwen run, not the order of fixture IDs.
                for f in case["facts"]:
                    fact = {**f, "category": f.get("category", "description"), "qualifiers": [f["qualifiers"]]}
                    published = " ".join(c3_assets.fact_lines(fact, p))
                    matches = [r for r in rec["assets"]["evidence_report"]["facts"] if r["text"] == published]
                    assert len(matches) == 1
                    facts.append({**fact, "id": matches[0]["handle"]})
                p["facts"] = facts
                steps = []
                for attempt in rec["attempts"]:
                    if "raw_output" not in attempt:
                        continue
                    role = attempt["schema"].split("_")[-1]
                    if role not in c3_assets.ROLES[rec["workflow"]]:
                        continue
                    raw = attempt["raw_output"]
                    fields = {k: v for k, v in raw.items() if k != "source_ids"}
                    steps.append({"skill": role, "output": {"sections": fields, "source_ids": raw["source_ids"], "text": "\n".join(fields.values())}})
                assert {s["skill"] for s in steps} == set(c3_assets.ROLES[rec["workflow"]])
                with Session(engine) as db:
                    output = rec["deliverable"]
                    doc = Deliverable(
                        tenant_id=scope.tenant,
                        campaign_id=scope.campaign,
                        title=output["title"],
                        content={"client_preview": output["body"]},
                        created_by=owner["id"],
                        status="submitted",
                    )
                    db.add(doc)
                    db.flush()
                    run = WorkforceRun(
                        tenant_id=scope.tenant,
                        client_id=scope.client,
                        brand_id=scope.brand,
                        campaign_id=scope.campaign,
                        brief_id=brief["id"],
                        deliverable_id=doc.id,
                        plan=[],
                        budget_microusd=0,
                        state="awaiting_qa",
                        checkpoints=steps,
                        knowledge={"title": case["product"], "registry": rec["binding"], "c3_projection": p, "sources": {}, "c3_manifest": rec["manifest"]},
                    )
                    db.add(run)
                    db.flush()
                    evaluate(db, doc, owner["id"])
                    did = doc.id
                    db.commit()
                sessions = capture_completed(browser, origin, scope.tenant, email, password, did, rec["workflow"], out)
                results.append(
                    {
                        "workflow": rec["workflow"],
                        "source_checkout": rec["checkout"],
                        "source_run": rec["run_id"],
                        "source_document": output["id"],
                        "model_sha256": rec["model_sha256"],
                        "sessions": sessions,
                    }
                )
        finally:
            browser.close()
    assert len(results) == 2
    (out / "replay-acceptance.json").write_text(
        json.dumps(
            {
                "provenance": "Saved real local-Qwen replies replayed into disposable SQLite; live HTTP/browser edits; no new inference in this job.",
                "cases": results,
            },
            indent=2,
        ),
        encoding="utf8",
    )
