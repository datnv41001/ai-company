"""Build a development-only staff packet from authorized HTTP readbacks. No product endpoint."""

from app import c3_assets, c3_studio
from app.knowledge_store import canonical, digest
from app.revision_qa import content_digest
from knowledge_fixtures import accepted


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_current(api, base, document_id, editor, reviewer):
    """Only capture a packet while the original staff sessions can read the same reviewed revision."""
    doc_path = f"{base}/deliverables/{document_id}"
    gate_path = doc_path + "/studio/content-handoff"
    gate = accepted(api.get(gate_path, headers=reviewer))
    proof = gate["provenance"]
    staff = accepted(api.get("/api/me", headers=editor))["id"]
    require(proof.get("qa_receipt") and proof.get("last_editor_id") == staff, "Current independent QA and assigned editor required")
    doc = accepted(api.get(doc_path, headers=editor))
    require((doc["id"], doc["campaign_id"]) == (proof["document_id"], gate["scope"]["campaign_id"]), "Wrong campaign")
    run = accepted(api.get(f"{base}/workforce/runs/{proof['run_id']}", headers=editor))
    scope = gate["scope"]
    manifest_url = f"{base}/clients/{scope['client_id']}/brands/{scope['brand_id']}/business-workspace/marketing/manifests/{proof['manifest']['id']}"
    manifest = accepted(api.get(manifest_url, headers=editor))
    studio = accepted(api.get(doc_path + "/studio", headers=editor))
    packet = assemble(gate, staff, run, studio, manifest)
    latest = accepted(api.get(gate_path, headers=reviewer))
    require(latest["revision"] == gate["revision"] and latest["provenance"].get("qa_receipt") == proof["qa_receipt"], "Evidence changed during capture")
    return packet


def assemble(gate, staff_id, report, studio, snapshot):
    proof = gate["provenance"]
    require(proof.get("qa_receipt") and proof["last_editor_id"] == staff_id, "Require current QA and the saved draft's editor")
    document = proof["document_id"]
    manifest = proof["manifest"]
    scope = gate["scope"]
    require(report["id"] == proof["run_id"] and report["deliverable_id"] == document, "Wrong run or document")
    expected_path = (
        f"/api/tenants/{scope['tenant_id']}/clients/{scope['client_id']}/brands/{scope['brand_id']}"
        f"/business-workspace/marketing/manifests/{manifest['id']}/provenance"
    )
    require(report.get("marketing_provenance") == expected_path, "Missing or different scoped manifest")
    require(
        (snapshot["id"], snapshot["digest"], snapshot["workflow"]) == (manifest["id"], manifest["digest"], c3_assets.RESEARCH),
        "Wrong manifest identity or workflow",
    )
    require(studio["mode"] == "saved" and studio["workflow"] == c3_assets.RESEARCH, "Require a saved Research Studio draft")
    artifacts = report["marketing_artifacts"]["sections"]
    current = artifacts["customer_preview"]["current"]
    rev = gate["revision"]
    require(current["document_id"] == document and rev == current["revision"] == studio["revision"], "Different draft revisions")
    signature = content_digest(studio["preview"]["title"], studio["preview"]["body"])
    require(signature == gate["content_digest"] == current["digest"], "Different preview digests")
    # Positive allowlist: a previous or future client edition isn't implicitly in scope.
    names = c3_studio.FIELDS[c3_assets.RESEARCH]
    require(set(studio["groups"]) == set(names), "Unexpected asset groups")
    groups = studio["groups"]
    for group, fields in groups.items():
        expected = digest(canonical([studio["version"], document, rev, manifest["digest"], group, fields]))
        require(studio["asset_digests"][group] == expected, "Edited group differs from its bound digest")
    notes = artifacts["research_notes"]["fields"]
    require(notes == proof["worker_proposals"]["research"], "Raw notes differ from the signed run checkpoint")
    control = c3_studio.compose(c3_assets.RESEARCH, snapshot["projection"])
    require(all(control[k] == studio["suggestions"][k] for k in names), "Deterministic readback differs")
    lineage = {
        "scope": scope,
        "document": document,
        "revision": rev,
        "preview_digest": signature,
        "brief": proof["brief_id"],
        "run": proof["run_id"],
        "manifest": manifest,
        "qa_receipt": proof["qa_receipt"],
        "release": proof["release"],
    }
    studio_hash, notes_hash = digest(canonical(groups)), digest(canonical(notes))
    return {
        "contract": "amc.development-staff-evaluation/1",
        "lineage": lineage,
        "studio_only": {"groups": groups, "sha256": studio_hash},
        "worker_research_notes": {"fields": notes, "sha256": notes_hash, "origin": "controlled first worker checkpoint, before editing"},
        "assembled_sha256": digest(canonical([lineage, studio_hash, notes_hash])),
        "deterministic_control": {"groups": control, "sha256": digest(canonical(control)), "worker_notes": None},
        "scope_of_use": "Public synthetic calibration only; D has no worker. A and C use the same assembly rule.",
    }
