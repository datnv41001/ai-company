"""A joined strategy/channel edition validates its edited KPI again at signature and delivery."""

from datetime import timedelta
import json
import os
from pathlib import Path

import pytest

from app import c3_assets, c3_studio, measurement_integrity
from app.models import utcnow
from test_c3_content_gate import approve
from knowledge_fixtures import accepted
from test_channel_editions import sqlite_channel
from test_claim_desk import reader
from test_measurement_integrity import HISTORICAL, definition
from test_workforce import workforce as workforce_fixture

workforce = workforce_fixture


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_edited_measurement_refused_then_repaired_and_shared(api, workforce, monkeypatch):
    case = HISTORICAL["case"] | {"measurement": definition("appointment.confirmed_per_requested", 21)}
    doc, snap, plan, editor, other, _ = sqlite_channel(api, workforce, monkeypatch, case, wf=c3_assets.RESEARCH)
    owner, buyer, _, base, *_ = workforce
    studio = doc + "/studio"
    original = accepted(api.get(studio, headers=owner["headers"]))
    edition = original["channel_edition"]
    contract = plan["measurement_contract"]
    assert edition["plan"]["measurement_contract"] == contract
    groups = c3_studio.compose(snap["workflow"], snap["projection"]) | edition["groups"]
    old = HISTORICAL["published_groups"]
    edits = {group: dict(fields) for group, fields in groups.items()}
    edits["client_measurement"]["method"] = old["client_measurement"]["method"]
    edits["measurement"]["measurement_method"] = old["measurement"]["measurement_method"]
    edits["ad"]["measurement"] = edits["client_measurement"]["method"]

    def save(before, data):
        return accepted(
            api.patch(
                studio,
                headers=owner["headers"],
                json={"expected_revision": before["revision"], "groups": data, "delivery_version": edition["version"], "expected_plan_digest": plan["digest"]},
            )
        )

    damaged = save(original, edits)
    accepted(api.post(doc + "/submit", headers=editor["headers"]))
    reviewer = reader(api, owner, "admin")
    reasons = [r for r in damaged["quality_issues"] if r["reason"] == "primary_measurement_mismatch"]
    assert {(r["group"], r["field"]) for r in reasons} == {("measurement", "measurement_method"), ("client_measurement", "method"), ("ad", "measurement")}
    for reason in reasons:
        group = reason["group"]
        blocked = api.post(
            studio + "/approvals",
            headers=reviewer["headers"],
            json={
                "expected_revision": damaged["revision"],
                "group": group,
                "expected_asset_digest": damaged["asset_digests"][group],
                "note": "Đối chiếu kết quả cuối với nguồn KPI.",
            },
        )
        assert blocked.status_code == 409
    groups["client_measurement"]["method"] += "\n" + measurement_integrity.secondary_statement("vi-VN")
    fixed = save(damaged, groups)
    assert not [r for r in fixed["quality_issues"] if r["reason"] == "primary_measurement_mismatch"]

    def evidence(actor, recipient, did, shared, final_plan):
        snapshot = accepted(api.get(base + "/reviews/" + shared["id"], headers=recipient["headers"]))
        assert snapshot["status"] == "approved" and groups["client_measurement"]["method"] in shared["preview"]
        assert old["client_measurement"]["method"] not in shared["preview"]
        if output := os.getenv("AMC_KPI_EVIDENCE"):
            report = {
                "mode": "real SQLite review and customer lifecycle with a seeded synthetic worker completion; no inference",
                "plan_id": final_plan["id"],
                "contract": contract,
                "doc_id": did,
                "rejected_revision": damaged["revision"],
                "rejected_fields": reasons,
                "corrected_revision": fixed["revision"],
                "customer_snapshot_id": shared["id"],
                "customer_snapshot_digest": shared["digest"],
                "decision": snapshot["status"],
                "title": shared["title"],
                "preview": shared["preview"],
            }
            Path(output).mkdir(parents=True, exist_ok=True)
            (Path(output) / "luong-ro-signed.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    submitted = accepted(api.post(doc + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision": fixed["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    for group in groups:
        accepted(
            api.post(
                studio + "/approvals",
                headers=reviewer["headers"],
                json={
                    "expected_revision": fixed["revision"],
                    "group": group,
                    "expected_asset_digest": fixed["asset_digests"][group],
                    "note": "Đã so sánh nội dung với nguồn được duyệt.",
                },
            )
        )
    accepted(approve(api, doc, reviewer, terms))
    shared = accepted(api.post(doc + "/share", headers=owner["headers"], json={**terms, "expires_at": (utcnow() + timedelta(days=1)).isoformat()}))
    assert api.get(base + "/reviews/" + shared["id"], headers=other["headers"]).status_code == 404
    accepted(api.put(base + "/members/" + buyer["id"] + "/review-rights", headers=owner["headers"], json={"can_comment": True, "can_decide": True}))
    accepted(
        api.post(
            base + "/reviews/" + shared["id"] + "/events",
            headers=buyer["headers"],
            json={"kind": "approved", "digest": shared["digest"], "request_key": "synthetic-final-kpi-decision"},
        )
    )
    evidence(owner, buyer, doc.rsplit("/", 1)[1], shared, plan)
