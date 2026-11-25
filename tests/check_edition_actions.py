"""Ordinary editing and approval requests to the already-running #40 API after cutover.

Run by check_studio_cutover.py --from-version 3 with the predecessor pipe fixture.
"""
from datetime import timedelta

from app import c3_assets, c3_studio
from app.models import utcnow
from knowledge_fixtures import accepted
from test_c3_content_gate import approve
from test_claim_desk import reader
from test_registry import pool as registry_pool
from test_studio_postgres import agency_draft

pool = registry_pool


def test_customer_edition_mixed_writers(pool, old_api):
    api = pool.api
    base, owner, customer, _, _ = pool.cases[0]
    doc, _, snap = agency_draft(pool, c3_assets.RESEARCH, rfq=True)
    studio = doc + "/studio"
    editor = reader(api, owner, "editor")
    reviewer = reader(api, owner, "admin")
    state = accepted(api.get(studio, headers=editor["headers"]))
    groups = c3_studio.compose(c3_assets.RESEARCH, snap["projection"])
    terms = {"expected_revision": state["revision"], "groups": groups}
    working = accepted(api.patch(studio, headers=editor["headers"], json=terms))
    submitted = accepted(api.post(doc + "/submit", headers=editor["headers"]))
    qa = {"expected_qa_revision": working["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    for group in groups:
        accepted(api.post(studio + "/approvals", headers=reviewer["headers"], json={
            "group": group, "expected_revision": working["revision"], "expected_asset_digest": working["asset_digests"][group],
            "note": "Confirmed group scope and evidence for the synthetic RFQ.",
        }))
    assert old_api("GET", studio, editor) == "200"
    assert old_api("POST", doc + "/review", owner, qa | {"decision": "approved", "note": "Confirmed the synthetic RFQ."}) == "55000"
    accepted(approve(api, doc, owner, qa))
    share = qa | {"expires_at": (utcnow() + timedelta(days=3)).isoformat()}
    assert old_api("POST", doc + "/share", owner, share) == "55000"
    assert api.post(doc + "/share", headers=owner["headers"], json=share).status_code == 409
    assert accepted(api.get(base + "/reviews", headers=customer["headers"])) == []
    edition = state["customer_edition"]
    ready = accepted(api.patch(studio, headers=editor["headers"], json={
        "expected_revision": working["revision"], "groups": groups | edition["groups"], "delivery_version": edition["version"],
    }))
    legacy_save = {"expected_revision": ready["revision"], "groups": groups}
    assert api.patch(studio, headers=editor["headers"], json=legacy_save).status_code == 409
    assert old_api("PATCH", studio, editor, legacy_save) == "55000"
    assert old_api("PATCH", doc + "/draft", editor, {"title": "RFQ working draft", "client_preview": "Updated strategy draft."}) == "55000"
    unchanged = accepted(api.get(studio, headers=editor["headers"]))
    assert all(unchanged[k] == ready[k] for k in ("revision", "delivery_version", "groups", "asset_digests", "preview"))
