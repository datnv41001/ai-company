"""Executable RED boundary for four Strategy assets and staff-only evaluation calibration."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agency_fixtures import account, create, postgres_api
from app import c3_assets, c3_strategy_handoff
from app.c3_tasks import INTENT_TYPES
from c3_fixtures import withdraw
from content_handoff_packet import assemble, read_current
from identity_fixtures import invite_member
from knowledge_fixtures import accepted
from strategy_runtime_fixtures import INTENT, OBSERVATION, PRODUCT, commission_lab, prepare_review, studio_save
from test_claim_desk import reader
from test_strategy_runtime_handoff import immutable_counts, terms

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {"web_use_guide", "web_terms_panel", "counter_use_card", "counter_terms_card"}
PG = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Requires isolated PostgreSQL dispatcher and scoped sessions")


def export(name, data):
    if folder := os.environ.get("AMC_CONTENT_HANDOFF_EVIDENCE"):
        path = Path(folder) / (name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.mark.parametrize("asset", sorted(ASSETS))
def test_registry_preserves_distinct_deliverable_types(asset):
    assert set(c3_strategy_handoff.ASSETS) == ASSETS
    for model in INTENT_TYPES.values():
        with pytest.raises(ValidationError) as error:
            model.model_validate(INTENT | {"deliverable_type": asset})
        assert any(e["loc"] == ("deliverable_type",) and e["type"] == "literal_error" for e in error.value.errors())
    landing = json.loads((ROOT / "catalog/landing-seo-v6.json").read_bytes())
    assert landing["workflow_id"] + "@" + str(landing["workflow_version"]) == c3_assets.LANDING
    assert landing["required"] == ["director", "content", "seo"]
    assert set(c3_assets.COPY) <= set(landing["contracts"]["content"]["outputs"])
    assert set(c3_assets.SEO) <= set(landing["contracts"]["seo"]["outputs"])


def counts(ctx):
    conn, campaign = ctx["lab"].owner, ctx["scope"]["campaign_id"]
    return {
        **immutable_counts(ctx),
        "tasks": conn.execute("SELECT count(*) FROM workforce_briefs WHERE campaign_id=%s", (campaign,)).fetchone()[0],
        "manifests": conn.execute("SELECT count(*) FROM knowledge_snapshots WHERE campaign_id=%s", (campaign,)).fetchone()[0],
    }


@PG
@pytest.mark.parametrize("complete_excerpt", [True, False], ids=["released-terms", "protected-partial-excerpt"])
def test_signed_recipient_order_and_assembled_readback(complete_excerpt):
    notes = "Replay two handovers. If both need specifications first, propose terms. If both need sorting help, keep guide. If mixed, hold for owner."
    limit = "For indoor sorting only."
    wording = PRODUCT + " " + limit
    excerpt = wording if complete_excerpt else PRODUCT
    facts = [{"wording": OBSERVATION, "qualifiers": [], "excerpt": OBSERVATION}, {"wording": PRODUCT, "qualifiers": [limit], "excerpt": excerpt}]
    with postgres_api() as api, commission_lab(api, source_facts=facts, controlled={"research": {"evidence_needed": notes}}) as ctx:
        owner, qa, recipient = (ctx[k]["headers"] for k in ("owner", "reviewer", "recipient"))
        endpoint = ctx["studio"] + "/content-handoff"
        assert accepted(api.get(endpoint, headers=recipient))["work_order"] is None
        before_edit = accepted(api.get(ctx["studio"], headers=owner))
        reviewed = prepare_review(api, ctx, positioning=wording)
        ready = accepted(api.get(endpoint, headers=qa))
        request = terms(ready, ctx, product_excerpt=excerpt)
        before = counts(ctx)
        signed = accepted(api.post(endpoint, headers=qa, json=request))
        actual = accepted(api.get(endpoint, headers=recipient))
        order = actual["work_order"]
        if not complete_excerpt:
            assert signed["reasons"] == ["brief_disclosure_blocked"] and order is None
            assert counts(ctx) == before
            export(
                "partial-excerpt",
                {
                    "status": signed["status"],
                    "reasons": signed["reasons"],
                    "work_order": None,
                    "document_id": ready["provenance"]["document_id"],
                    "revision": ready["revision"],
                    "receipt": signed["decision"]["receipt_id"],
                },
            )
            return
        assert order is not None, signed["reasons"]
        assert order == {k: v for k, v in signed["work_order"].items() if k != "sources"}
        assert actual["decision"]["receipt_id"] == signed["decision"]["receipt_id"]
        assert order["message"] == wording and order["placement"] == INTENT["channel"]
        for key in ("purpose", "audience", "buyer_action", "editorial_style", "requirements", "exclusions", "acceptance_criteria"):
            assert order["brief"][key] == INTENT[key]
        assert order["brief"]["cta"] == "Download the catalogue" and order["measurement"] == {"status": "planned_only", "execution_authorized": False}
        assert order["claim_limits"] and order["asset_type"] == "web_use_guide" and counts(ctx) == before
        assert all(s not in json.dumps(actual) for s in (OBSERVATION, "private locator", ctx["mandate"]["id"], request["interpretation"]))
        assert accepted(api.post(endpoint, headers=qa, json=request)) == signed
        stranger = reader(api, ctx["owner"], "admin")
        assert accepted(api.get(endpoint, headers=stranger["headers"]))["work_order"] is None
        task = {"key": str(uuid4()), "campaign_id": ctx["scope"]["campaign_id"], "intent": dict(INTENT)}
        red = {}
        for asset in sorted(ASSETS):
            task["intent"]["deliverable_type"] = asset
            result = api.post(ctx["base"] + "/workforce/internal-tasks", headers=recipient, json=task)
            assert result.status_code == 422
            fields = [e["loc"] for e in result.json()["detail"] if e["type"] == "literal_error" and e["loc"][-1] == "deliverable_type"]
            assert fields
            red[asset] = {"status": 422, "rejected_fields": fields}
        task["intent"]["deliverable_type"] = actual["work_order"]["asset_type"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(api.post, ctx["base"] + "/workforce/internal-tasks", headers=recipient, json=task) for _ in range(2)]
            assert [f.result(timeout=15).status_code for f in futures] == [422, 422]
        # Try the real release with the original signed task; do not invent a landing commission.
        opts = ctx["state"]["params"] | {"key": str(uuid4()), "workflow": c3_assets.LANDING}
        mismatch = api.post(ctx["state"]["marketing"] + "/manifests", headers=owner, json=opts)
        assert mismatch.status_code == 409 and "Loại bản giao" in mismatch.json()["detail"]
        assert counts(ctx) == before
        run = accepted(api.get(ctx["report_url"], headers=owner))
        manifest = accepted(api.get(ctx["state"]["marketing"] + "/manifests/" + ctx["snap"]["id"], headers=owner))
        studio = accepted(api.get(ctx["studio"], headers=owner))
        staff = accepted(api.get("/api/me", headers=owner))["id"]
        doc_id = ctx["doc"].rsplit("/", 1)[1]
        packet = read_current(api, ctx["base"], doc_id, owner, qa)
        assert packet == assemble(signed, staff, run, studio, manifest)
        with pytest.raises(ValueError):
            read_current(api, ctx["base"], doc_id, recipient, qa)
        foreign = account(api, "Outsider")
        for url in (ctx["report_url"], ctx["studio"], endpoint):
            assert api.get(url, headers=foreign["headers"]).status_code in (403, 404)
        assert packet["worker_research_notes"]["fields"]["evidence_needed"] == notes
        assert packet["worker_research_notes"]["fields"]["buyer_problem"] == before_edit["groups"]["research"]["buyer_problem"]
        assert packet["studio_only"]["groups"]["research"]["buyer_problem"] == OBSERVATION
        assert notes not in json.dumps([studio["preview"], actual["work_order"], packet["studio_only"]])
        assert signed["provenance"]["qa_receipt"] == accepted(api.get(endpoint, headers=qa))["provenance"]["qa_receipt"]
        assert packet["lineage"]["revision"] == reviewed["studio"]["revision"]
        for key, bad in (("id", str(uuid4())), ("deliverable_id", str(uuid4())), ("marketing_provenance", "/different/scope")):
            with pytest.raises(ValueError):
                assemble(signed, staff, run | {key: bad}, studio, manifest)
        with pytest.raises(ValueError):
            assemble(signed, staff, run, studio, manifest | {"digest": "0" * 64})
        with pytest.raises(ValueError):
            assemble(signed, ctx["recipient"]["id"], run, studio, manifest)
        tampered = deepcopy(run)
        tampered["marketing_artifacts"]["sections"]["research_notes"]["fields"]["evidence_needed"] += "other run"
        with pytest.raises(ValueError):
            assemble(signed, staff, tampered, studio, manifest)
        assert notes not in json.dumps(actual)
        export("assembled", packet)
        export(
            "admission",
            {
                "study": "controlled upstream WF-03, no downstream Content worker",
                "lineage": packet["lineage"],
                "handoff_receipt": actual["decision"]["receipt_id"],
                "strategy_attempts": {k: v["completed_attempt_id"] for k, v in ctx["requests"].items()},
                "recipient_order": actual["work_order"],
                "internal_task_api": red,
                "same_key_concurrent": [422, 422],
                "original_task_on_wf13": {"status": 409, "detail": mismatch.json()["detail"]},
                "before": before,
                "after": counts(ctx),
                "content_task": None,
                "content_manifest": None,
                "content_run": None,
                "content_asset": None,
                "content_qa": None,
            },
        )
        updated = studio_save(api, ctx, studio["groups"])
        assert updated["revision"] > studio["revision"] and accepted(api.get(endpoint, headers=recipient))["work_order"] is None
        with pytest.raises(ValueError):
            assemble(signed, staff, run, updated, manifest)
        assert api.post(endpoint, headers=qa, json=request).status_code == 412
        prepare_review(api, ctx, positioning=wording)
        current = accepted(api.get(endpoint, headers=qa))
        accepted(api.post(endpoint, headers=qa, json=terms(current, ctx, product_excerpt=excerpt)))
        accepted(withdraw(api, ctx["owner"], ctx["state"]))
        withheld = accepted(api.get(endpoint, headers=recipient))
        assert not withheld["references"] and withheld["work_order"] is None
        assert not accepted(api.get(endpoint, headers=qa))["provenance"].get("qa_receipt")
        with pytest.raises(ValueError):
            read_current(api, ctx["base"], doc_id, owner, qa)


@PG
def test_agency_cannot_use_internal_admission():
    with postgres_api() as api:
        owner = account(api, "Agency")
        base = "/api/tenants/" + owner["tenant"]
        client = create(api, base + "/clients", owner, {"name": "Synthetic client"})
        brand = create(api, base + "/brands", owner, {"client_id": client["id"], "name": "Synthetic brand"})
        campaign = create(
            api,
            base + "/campaigns",
            owner,
            {"brand_id": brand["id"], "name": "Synthetic campaign", "brief": "Research the buyer decision", "objective": "Prepare a product guide"},
        )
        rejected = api.post(
            base + "/workforce/internal-tasks", headers=owner["headers"], json={"key": str(uuid4()), "campaign_id": campaign["id"], "intent": INTENT}
        )
        assert rejected.status_code == 404 and rejected.json()["detail"] == "Internal task scope unavailable"
        customer = account(api, "Buyer")
        invite_member(api, base, owner["headers"], customer["headers"], email=customer["email"], role="client_viewer", client_id=client["id"])
        brief = create(
            api,
            base + "/workforce/briefs",
            owner,
            {"campaign_id": campaign["id"], "recipient_id": customer["id"], "title": "Terms on an existing product page"},
        )
        response = api.put(
            base + "/workforce/briefs/" + brief["id"] + "/task-submission", headers=customer["headers"], json=INTENT | {"deliverable_type": "web_terms_panel"}
        )
        assert response.status_code == 422
        assert any(e["loc"][-1] == "deliverable_type" and e["type"] == "literal_error" for e in response.json()["detail"])
        export(
            "agency",
            {
                "scope": {"tenant": owner["tenant"], "client": client["id"], "brand": brand["id"], "campaign": campaign["id"]},
                "internal_commission_status": rejected.status_code,
                "agency_brief": brief["id"],
                "customer_request": "web_terms_panel",
                "submission_status": response.status_code,
                "content_admitted": False,
            },
        )
