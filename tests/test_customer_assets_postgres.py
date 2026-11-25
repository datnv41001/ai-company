"""Versioned Agency customer editions through the real registry, pool and RLS-protected portal."""

from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess

import pytest

from app import c3_assets, c3_customer_assets, c3_studio
from app.models import utcnow
from knowledge_fixtures import accepted
from test_c3_content_gate import approve
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_studio_postgres import agency_draft

pool = registry_pool
pytestmark = PG


@pytest.mark.parametrize("workflow", [c3_assets.RESEARCH, c3_assets.LANDING])
def test_versioned_customer_asset_receipts_on_postgres(pool, workflow):
    api = pool.api
    base, owner, customer, client_id, campaign_id = pool.cases[0]
    doc, _, snap = agency_draft(pool, workflow, rfq=True)
    studio = doc + "/studio"
    editor, reviewer = reader(api, owner, "editor"), reader(api, owner, "admin")
    proposal = accepted(api.get(studio, headers=editor["headers"]))
    edition = proposal["customer_edition"]
    # The editor selects the grounded plan instead of accepting the synthetic worker's raw wording.
    groups = c3_studio.compose(workflow, snap["projection"]) | edition["groups"]
    saved = accepted(
        api.patch(
            studio,
            headers=editor["headers"],
            json={
                "delivery_version": edition["version"],
                "expected_revision": proposal["revision"],
                "groups": groups,
            },
        )
    )
    submitted = accepted(api.post(doc + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision": saved["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    for group in groups:
        signed = accepted(
            api.post(
                studio + "/approvals",
                headers=reviewer["headers"],
                json={
                    "expected_revision": saved["revision"],
                    "expected_asset_digest": saved["asset_digests"][group],
                    "group": group,
                    "note": "Verified approved facts, scope and buyer action against the synthetic brief.",
                },
            )
        )
    accepted(approve(api, doc, owner, terms))
    shared = accepted(api.post(doc + "/share", headers=owner["headers"], json=terms | {"expires_at": (utcnow() + timedelta(days=2)).isoformat()}))
    portal = base + "/reviews/" + shared["id"]
    snapshot = accepted(api.get(portal, headers=customer["headers"]))
    assert api.get(portal, headers=pool.cases[1][2]["headers"]).status_code == 404
    assert snapshot["preview"] == saved["preview"]["body"] and snapshot["digest"] == terms["expected_content_digest"]
    assert "PRIVATE_SYNTHETIC" not in str(snapshot) and "Buyer needs require interviews" not in snapshot["preview"]
    expected_assets = c3_customer_assets.project(workflow, groups)
    decisions = {}
    for operation in ("c3_qa", "c3_share"):
        [(rid, receipt)] = pool.owner.execute(
            "select id, result from knowledge_commands where snapshot_id=%s and operation=%s", (snap["id"], operation)
        ).fetchall()
        decisions[operation] = rid
        manifest = receipt["customer_delivery"]
        assert manifest["scope"]["tenant_id"] == owner["tenant"] and manifest["scope"]["client_id"] == client_id
        assert manifest["scope"]["campaign_id"] == campaign_id
        assert receipt["qa_revision"] == saved["revision"] and receipt["content_digest"] == snapshot["digest"]
        assert set(manifest["assets"]) == set(edition["fields"]) == set(expected_assets)
        for group, fields in expected_assets.items():
            asset = manifest["assets"][group]
            assert asset["fields"] == fields and all(value in snapshot["preview"] for value in fields.values())
            assert asset["approval_receipt"] == signed["approvals"][group]["receipt"]
            field_evidence = receipt["customer_field_evidence"][group]
            assert set(field_evidence) == set(fields) and all(field_evidence.values())
    if directory := os.getenv("AMC_CUSTOMER_EDITION_EVIDENCE"):
        kind = "strategy" if workflow == c3_assets.RESEARCH else "landing"
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        artifact = {
            "provenance": "Synthetic Agency, restricted PostgreSQL runtime and distinct dispatcher and worker logins. Deterministic role replies and scripted QA.",
            "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True).strip(),
            "postgres": pool.owner.execute("show server_version").fetchone()[0],
            "workflow": workflow,
            "snapshot": {key: snapshot[key] for key in ("id", "version", "title", "preview", "digest")},
            "decisions": decisions,
            "staff_evidence": {
                key: receipt[key] for key in ("customer_delivery", "customer_field_evidence", "content_gate_digest", "manifest_digest", "release_digest")
            },
        }
        (out / f"postgres-{kind}.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
