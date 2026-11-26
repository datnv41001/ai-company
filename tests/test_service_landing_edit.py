"""Replay the pump-service edit through Studio QA and Landing Production."""

from base64 import b64decode
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app import c3_order_units, c3_studio, campaign_channels
from app.models import utcnow
from campaign_planner_fixtures import CASES, facts
from knowledge_fixtures import accepted, revision
from test_c3_content_gate import approve
from test_channel_editions import sqlite_channel, workforce  # noqa: F401
from test_claim_desk import reader


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_service_landing_edit(api, workforce, monkeypatch):  # noqa: F811
    case = next(case for case in CASES if case["id"] == "pump-service")
    # Recreate a pre-intake proposal and its original digest, then exercise approval, edit and replay normally.
    from app import campaign_planner, c3_actions
    from app.knowledge_store import canonical, digest
    current_compose = campaign_planner.compose_plan
    # This exercise reproduces the archived pre-intake writer byte-for-byte.
    monkeypatch.setitem(c3_actions.ACTIONS["appointment"], "vi", "Đặt lịch")

    def archived_proposal(*args):
        plan = current_compose(*args)
        plan.pop("intake_contract")
        plan.pop("digest")
        return {**plan, "digest": digest(canonical(plan))}

    monkeypatch.setattr(campaign_planner, "compose_plan", archived_proposal)
    doc, snap, plan, editor, _, _ = sqlite_channel(api, workforce, monkeypatch, case)
    owner, buyer, _, base, _, scope, *_ = workforce
    reviewer = reader(api, owner, "admin")
    studio = doc + "/studio"
    production = studio + "/production"

    def post(actor, path, body):
        return api.post(path, headers=actor["headers"], json=body)

    def save(actor, view, fields):
        return accepted(api.patch(studio, headers=actor["headers"], json={
            "expected_revision": view["revision"], "delivery_version": campaign_channels.VERSION,
            "expected_plan_digest": plan["digest"], "groups": fields,
        }))

    def sign(view, group):
        return post(reviewer, studio + "/approvals", {
            "expected_revision": view["revision"], "group": group, "expected_asset_digest": view["asset_digests"][group],
            "note": "Đã đối chiếu quyền lợi, điều kiện và giá với nguồn của phiên bản này.",
        })

    def prepare(view, previous_version):
        return post(owner, production, {
            "kind": "landing", "expected_revision": view["revision"], "expected_plan_digest": plan["digest"],
            "expected_version": previous_version, "expected_groups": {g: view["asset_digests"][g] for g in ("copy", "seo")},
        })

    def download(package):
        url = production + "/" + package["id"] + "/files/landing.html"
        html = b64decode(accepted(api.get(url, headers=owner["headers"]))["base64"])
        assert sha256(html).hexdigest() == package["files"]["landing.html"]["sha256"]
        return html

    def review_and_render(view, previous_version):
        submitted = accepted(api.post(doc + "/submit", headers=editor["headers"]))
        terms = {"expected_qa_revision": view["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
        resolved = []
        if previous_version:
            report = accepted(api.get(doc + "/content-evidence", headers=reviewer["headers"]))
            rows = [r for r in report["statements"] if r["outcome"] == "unresolved"]
            assert {r["field"] for r in rows} == {"client_preview", "studio.copy.commercial_terms"}
            source, = [h for h, src in report["references"].items() if src["statement"] == case["wording"]]
            mandate = revision(api, owner, f"{base}/clients/{scope.client}/brands/{scope.brand}/knowledge",
                               "service-copy-review", "qualification", {"approver_id": reviewer["id"], "category": "unclassified",
                               "basis": "Synthetic service editorial review", "valid_until": "2099-01-01T00:00:00Z"}, visibility="restricted")
            for row in rows:
                assert row["text"] == case["qualifier"]
                accepted(post(reviewer, doc + "/content-evidence/resolutions", terms | {
                    "statement_id": row["id"], "handle": source, "qualification_revision": mandate["id"],
                    "reason": "Đã đối chiếu điều kiện tại xưởng với nguồn ghim của phiếu kiểm tra.",
                }))
            report = accepted(api.get(doc + "/content-evidence", headers=reviewer["headers"]))
            assert report["ready"]
            resolved = [r for r in report["statements"] if r["outcome"] == "reviewed"]
        for group in view["groups"]:
            signed = accepted(sign(view, group))
        accepted(approve(api, doc, reviewer, terms))
        package = accepted(prepare(view, previous_version))
        assert package["studio_revision"] == view["revision"] and package["version"] == previous_version + 1
        assert package["group_receipts"] == {g: signed["approvals"][g]["receipt"] for g in ("copy", "seo")}
        html = download(package)
        url = production + "/" + package["id"]
        verdict = {"expected_digest": package["digest"], "note": "Đã kiểm tra bản HTML, điều kiện và biểu mẫu đặt lịch."}
        assert post(owner, url + "/approve", verdict).status_code == 409
        receipt = accepted(post(reviewer, url + "/approve", verdict))
        assert receipt["digest"] == package["digest"]
        visit = accepted(post(owner, url + "/visits", {"request_id": uuid4().hex}))
        form = {"quantity": 1, "place": "north", "days": 7}
        submission = accepted(post(owner, url + "/submissions", form | {"request_id": uuid4().hex, "visit_id": visit["entity_id"]}))
        assert submission["kind"] == "appointment" and submission["value"]["landing_digest"] == package["digest"]
        assert submission["value"]["session_id"] == visit["entity_id"]
        evidence = {"document_qa": terms, "package": package, "file_qa": receipt, "reviewer": reviewer["id"], "resolved": resolved,
                    "form": form, "visit_receipt": visit["id"], "appointment_receipt": submission["id"]}
        return html, evidence

    proposal = accepted(api.get(studio, headers=owner["headers"]))
    groups = c3_studio.compose(snap["workflow"], snap["projection"]) | proposal["channel_edition"]["groups"]
    # Replay the delivered wording. Fact IDs can otherwise change the order of the proposed terms.
    archive = Path(__file__).resolve().parents[1] / "docs/evaluation/real-production/appointment/landing"
    archived = json.loads((archive / "receipt.json").read_text(encoding="utf8"))
    archived_terms = archived["master"]["sections"]["commercial_terms"]
    assert sorted(groups["copy"]["commercial_terms"].splitlines()) == sorted(archived_terms.splitlines())
    groups["copy"]["commercial_terms"] = archived_terms
    original = save(owner, proposal, groups)
    before, first = review_and_render(original, 0)
    assert sha256(before).hexdigest() == archived["files"]["landing.html"]["sha256"]
    shared = accepted(post(owner, doc + "/share", first["document_qa"] | {"expires_at": (utcnow() + timedelta(days=1)).isoformat()}))
    benefit = groups["copy"]["benefit"]
    terms = groups["copy"]["commercial_terms"]
    assert terms.startswith(benefit + "\n") and benefit == case["wording"] + " " + case["qualifier"]
    revised_terms = terms.removeprefix(case["wording"] + " ")
    revised = save(editor, original, groups | {"copy": groups["copy"] | {"commercial_terms": revised_terms}})
    assert revised["revision"] == original["revision"] + 1 and not revised["approvals"]
    assert sign(original, "copy").status_code == 412
    assert prepare(revised, 1).status_code == 409
    after, second = review_and_render(revised, 1)
    assert first["package"]["digest"] != second["package"]["digest"]
    assert first["package"]["id"] != second["package"]["id"] and download(first["package"]) == before
    portal = accepted(api.get(base + "/reviews/" + shared["id"], headers=buyer["headers"]))
    assert portal["digest"] == shared["digest"] and portal["preview"] == shared["preview"]
    assert terms in shared["preview"]
    sentence = case["wording"].encode()
    assert before.count(sentence) == 2 and after.count(sentence) == 1
    assert before.count(terms.encode()) == 1
    assert after == before.replace(terms.encode(), revised_terms.encode())
    assert "270.000 VND / 1 máy, đã gồm thuế".encode() in after
    assert second["package"]["master"]["sections"]["commercial_terms"] == revised_terms
    assert first["package"]["master"]["unit"] == second["package"]["master"]["unit"] == "machine"

    if output := os.getenv("AMC_SERVICE_EDIT_EVIDENCE"):
        folder = Path(output)
        folder.mkdir(parents=True, exist_ok=True)
        for name, html in (("before", before), ("after", after)):
            (folder / (name + ".html")).write_bytes(html)
        evidence = {"source": "synthetic Studio API rehearsal", "historical_snapshot_digest": portal["digest"],
                    "before": first, "after": second}
        (folder / "receipts.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


def test_terms_require_all_restrictions_and_the_full_qualified_benefit():
    case = next(case for case in CASES if case["id"] == "pump-service")
    description, price = facts(case)
    qualifiers = [case["qualifier"], "SKU BOM-KT.", "Khu vực: HN."]
    description.update(category="description", qualifiers=qualifiers)
    projection = {"facts": [description, price], "locale": "vi-VN", "task_intent": {"buyer_action": "appointment"}}
    restrictions = " ".join(qualifiers)
    full_benefit = f"{case['wording']} {restrictions}"
    price_line = " ".join(c3_order_units.fact_lines(price, projection))
    fields = {"benefit": full_benefit, "commercial_terms": f"{restrictions}\n{price_line}"}
    assert c3_studio.includes_declarations("commercial_terms", fields, projection)
    for clause in [*qualifiers, *c3_order_units.fact_lines(price, projection)]:
        reduced = fields["commercial_terms"].replace(clause, "").strip()
        assert not c3_studio.includes_declarations("commercial_terms", fields | {"commercial_terms": reduced}, projection), clause
    assert not c3_studio.includes_declarations("commercial_terms", fields | {"benefit": case["wording"]}, projection)
    assert not c3_studio.includes_declarations("commercial_terms", fields, projection | {"task_intent": {"buyer_action": "rfq"}})
    for category in ("warranty", "availability", "payment", "regulated", "performance", "comparison"):
        protected = projection | {"facts": [description | {"category": category}, price]}
        assert not c3_studio.includes_declarations("commercial_terms", fields, protected), category
    assert not c3_studio.includes_declarations("evidence", {"evidence": fields["commercial_terms"]}, projection)
