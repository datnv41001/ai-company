"""Customer editions use the real Studio, QA, sharing and portal APIs on synthetic accounts."""

from datetime import timedelta
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import c3_assets, c3_customer_assets, registry
from app.knowledge_models import KnowledgeCommand
from app.models import Deliverable, utcnow
from app.workforce_models import WorkforceRun
from c3_fixtures import capture, prepared
from c3_task_fixtures import INTENT
from knowledge_fixtures import accepted, revision
from test_c3_content_gate import approve
from test_claim_desk import reader
from test_workforce import DATA, workforce as workforce_fixture
from test_c3_skill_library import projection

workforce = workforce_fixture


def test_customer_strategy_excludes_staff_prose_and_preserves_business_decisions():
    p = projection("materials")
    p["task_intent"]["buyer_action"] = "rfq"
    groups = c3_customer_assets.strategy(p)
    p["task_intent"]["buyer_action"] = "sample_request"
    samples = c3_customer_assets.strategy(p)
    assert groups["client_strategy"]["next_decision"] != samples["client_strategy"]["next_decision"]
    assert groups["client_measurement"]["method"] != samples["client_measurement"]["method"]
    p["task_intent"]["buyer_action"] = "rfq"
    groups["research"] = {"evidence": "Private research diary and restricted locator"}
    visible = c3_customer_assets.preview(c3_assets.RESEARCH, groups, p)
    assert "Private research" not in visible["body"] and "PRIVATE" not in visible["body"]
    groups["client_strategy"]["activation"] = p["task_intent"]["purpose"]
    groups["client_measurement"]["method"] = groups["client_strategy"]["decision"]
    problems = {(r["field"], r["reason"]) for r in c3_customer_assets.issues(c3_assets.RESEARCH, groups, p)}
    assert {("activation", "private_context"), ("method", "repetition")} <= problems


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
@pytest.mark.parametrize("workflow", [c3_assets.RESEARCH, c3_assets.LANDING])
def test_share_exact_customer_edition(api, workforce, monkeypatch, workflow):
    exercise_share(api, workforce, monkeypatch, workflow)


def exercise_share(api, workforce, monkeypatch, workflow, inspect_ui=None):
    owner, client, unrelated, base, root, scope, engine, brief = workforce
    kind = "marketing_strategy" if workflow == c3_assets.RESEARCH else "landing_page"
    intent = INTENT | {"product": "Bộ mẫu vải", "audience": "Xưởng nội thất", "deliverable_type": kind,
                       "purpose": "Thông tin nghiệp vụ riêng của đội dự án", "buyer_action": "rfq", "editorial_style": "plain"}
    accepted(api.put(root + "/briefs/" + brief["id"] + "/submission", headers=client["headers"], json=DATA | {"task_intent": intent}))
    state = prepared(api, owner, base, scope.client, scope.brand, scope.campaign, brief["id"], workflow,
                     case={"product": intent["product"], "audience": intent["audience"], "facts": [{"wording": "Bề mặt mờ", "qualifiers": ["Dùng trong nhà"]}]})
    guide = revision(api, owner, state["path"], "voice", "guidelines", {"guidance": "Viết rõ và ngắn gọn."})
    state["params"]["guidelines"] = guide["id"]
    snap = capture(api, owner, state)
    editor = reader(api, owner, "editor")
    binding = {"workflow": workflow, "manifest_digest": "e" * 64}
    # SQLite lacks the PostgreSQL registry publisher. Only the completed worker link is seeded.
    monkeypatch.setattr(registry, "pin", lambda *args: binding)
    with Session(engine) as db:
        doc = Deliverable(tenant_id=scope.tenant, campaign_id=scope.campaign, title=intent["product"],
                          content={"client_preview": intent["product"]}, created_by=editor["id"])
        db.add(doc)
        db.flush()
        path = base + "/deliverables/" + doc.id
        db.add(WorkforceRun(tenant_id=scope.tenant, client_id=scope.client, brand_id=scope.brand, campaign_id=scope.campaign,
                            brief_id=brief["id"], deliverable_id=doc.id, plan=[], budget_microusd=0, state="awaiting_qa",
                            knowledge={"title": intent["product"], "registry": binding, "c3_projection": snap["projection"], "sources": {},
                                       "c3_manifest": {"id": snap["id"], "digest": snap["digest"]}}))
        db.commit()
    studio = path + "/studio"
    proposal = accepted(api.get(studio, headers=editor["headers"]))
    legacy = accepted(api.patch(studio, headers=editor["headers"], json={"groups": proposal["groups"], "expected_revision": proposal["revision"]}))
    submitted = accepted(api.post(path + "/submit", headers=editor["headers"]))
    old_terms = {"expected_qa_revision": legacy["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    for group in legacy["groups"]:
        accepted(api.post(studio + "/approvals", headers=owner["headers"], json={
            "group": group, "expected_revision": legacy["revision"], "expected_asset_digest": legacy["asset_digests"][group],
            "note": "Reviewed internal working asset for this synthetic case.",
        }))
    accepted(approve(api, path, owner, old_terms))
    refused = api.post(path + "/share", headers=owner["headers"], json=old_terms | {"expires_at": (utcnow()+timedelta(days=1)).isoformat()})
    assert refused.status_code == 409 and "customer asset edition" in refused.text
    edition = proposal["customer_edition"]
    groups = proposal["groups"] | edition["groups"]
    saved = accepted(api.patch(studio, headers=editor["headers"],
                               json={"delivery_version": edition["version"], "groups": groups, "expected_revision": legacy["revision"]}))
    assert saved["delivery_version"] == c3_customer_assets.VERSION
    assert api.patch(path + "/draft", headers=editor["headers"],
                     json={"title": "Replacement", "client_preview": "Unsanctioned body"}).status_code == 409
    assert api.patch(studio, headers=editor["headers"], json={"groups": groups, "expected_revision": saved["revision"]}).status_code == 409
    submitted = accepted(api.post(path + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision": saved["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    pending = [s for s in saved["findings"] if s["outcome"] not in ("editorial", "verified")]
    assert not pending, [(s["field"], s["text"], s["outcome"]) for s in pending]
    for group in groups:
        signed = accepted(api.post(studio + "/approvals", headers=owner["headers"], json={
            "group": group, "expected_revision": saved["revision"], "expected_asset_digest": saved["asset_digests"][group],
            "note": "Đã đối chiếu đầu ra và phạm vi nguồn của bản giao thử.",
        }))
    accepted(approve(api, path, owner, terms))
    shared = accepted(api.post(path + "/share", headers=owner["headers"], json=terms | {"expires_at": (utcnow() + timedelta(days=5)).isoformat()}))
    portal = base + "/reviews/" + shared["id"]
    assert api.get(portal, headers=unrelated["headers"]).status_code == 404
    output = accepted(api.get(portal, headers=client["headers"]))
    assert output["preview"] == saved["preview"]["body"]
    assert intent["purpose"] not in output["preview"] and "Buyer needs require interviews" not in output["preview"]
    assets = c3_customer_assets.project(workflow, groups)
    for fields in assets.values():
        assert all(value in output["preview"] for value in fields.values())
    with Session(engine) as db:
        cmd = db.scalar(select(KnowledgeCommand).filter_by(operation="c3_share", snapshot_id=snap["id"]))
        evidence = cmd.result
    manifest = evidence["customer_delivery"]
    assert set(manifest["assets"]) == set(edition["fields"])
    for group, item in manifest["assets"].items():
        assert item["fields"] == assets[group] and item["approval_receipt"] == signed["approvals"][group]["receipt"]
    assert evidence["content_digest"] == output["digest"] and evidence["content_sources"] and evidence["content_gate_digest"]
    for group, fields in assets.items():
        field_map = evidence["customer_field_evidence"][group]
        assert set(field_map) == set(fields) and all(field_map.values())
    assert manifest["scope"] == {f"{k}_id": getattr(scope, k) for k in ("tenant", "client", "brand", "campaign")}
    if inspect_ui:
        inspect_ui(owner, client, path.rsplit("/", 1)[1], output)
    # A later save and re-approval can only create a different working revision.
    changed = {k: dict(v) for k, v in groups.items()}
    first_group = next(iter(assets))
    first_field = next(iter(assets[first_group]))
    changed[first_group][first_field] = "Bản chỉnh mới"
    revised = accepted(api.patch(studio, headers=editor["headers"], json={
        "groups": changed, "delivery_version": edition["version"], "expected_revision": saved["revision"],
    }))
    assert not revised["approvals"]
    historical = accepted(api.get(portal, headers=client["headers"]))
    assert (historical["preview"], historical["digest"]) == (output["preview"], output["digest"])
    if directory := os.getenv("AMC_CUSTOMER_EDITION_EVIDENCE"):
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        artifact = {"provenance": "Synthetic SQLite API acceptance; worker association seeded, no model or practitioner invocation.",
                    "workflow": workflow, "snapshot": {k: output[k] for k in ("id", "version", "title", "preview", "digest")},
                    "staff_receipt": {"id": cmd.id, **evidence}}
        (out / f"{kind}.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
