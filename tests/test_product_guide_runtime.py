"""Contract regressions for the internal guide; admission and clocked authority are exercised with PostgreSQL separately."""

from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import psycopg
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access import set_context
from app.database import engine
from app import product_guide_runtime as guide
from app.security import sign_actor
from app.dynamic_plan import InvalidPlan
from app.pool_worker import run_job
from app.registry_compatibility import validate_manifest
from app.workforce_gateway import GatewayError
from agency_fixtures import account, create, postgres_api
from c3_task_fixtures import internal_workspace
from migrations.apply import publish_registry


def projection(locale="en-US"):
    steps = ["Place the reference card in the top slot.", "Slide the identification strip under the tab."]
    limitations = ["Use dry paper only."]
    wording = "Use on a flat desk. " + " ".join([*steps, *limitations])
    return {
        "locale": locale,
        "product": "Index stand",
        "audience": "Office staff",
        "procedure": {"source": "P1", "wording": wording, "steps": steps, "limitations": limitations},
        "order": {
            "message": wording,
            "placement": "owned product page",
            "guidance": {"situation": "Setting up a desk index."},
            "brief": {
                "audience": "Office staff",
                "cta": "Download the catalogue",
                "requirements": ["Keep both steps."],
                "acceptance_criteria": ["Keep the paper limitation."],
                "editorial_style": "plain",
                "exclusions": ["Price claims"],
            },
        },
    }


def test_guide_release_has_its_own_immutable_versions():
    stored = json.loads((Path(__file__).parents[1] / "catalog/product-use-guide-v1.json").read_bytes())
    assert stored == guide.release_manifest()
    validate_manifest(stored)
    altered = deepcopy(stored)
    altered["contracts"]["content"]["timeout_seconds"] += 1
    with pytest.raises(ValueError, match="Product guide release"):
        validate_manifest(altered)
    assert stored["required"] == ["director", "content"] and stored["required_outputs"] == ["content"]


def test_director_routes_to_one_bound_specialist_without_inference():
    manifest = guide.release_manifest()
    binding = {"workflow": guide.RELEASE, "contracts": manifest["contracts"], "skills": manifest["required"]}
    run = SimpleNamespace(knowledge={"registry": binding})
    body = guide.request(run, None, node=SimpleNamespace(skill="director"))
    raw, inputs, outputs = run_job(None, body)
    assert (inputs, outputs) == (0, 0)
    layout, fingerprint = guide.plan(raw, ["content"], binding)
    assert len(fingerprint) == 64 and layout["required"] == ["content"]
    (node,) = layout["nodes"]
    assert node["parents"] == [] and node["binding"]["skill_version"] == guide.VERSIONS["content"]
    assert layout["join"] == [node["node_id"]]
    with pytest.raises(InvalidPlan):
        guide.plan({"assignment": "Send this guide to customers"}, ["content"], binding)


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="Real campaign registry and PostgreSQL grants required")
def test_disabling_guide_preserves_existing_release_and_campaign_grants():
    catalog = Path(__file__).parents[1] / "catalog"
    historical = json.loads((catalog / "research-strategy-v3.json").read_bytes())
    old = historical["workflow_id"] + "@" + str(historical["workflow_version"])
    with postgres_api() as api, psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as conn:
        owner, base, _, _, campaign = internal_workspace(api)
        url = base + "/workforce/registry/" + campaign
        headers = owner["headers"]

        def change(workflow, mode, skills):
            reply = api.put(url, headers=headers, json={"workflow": workflow, "action": mode, "skills": skills})
            reply.raise_for_status()

        publish_registry(conn, historical)
        change(old, "activate", historical["required"])
        prior = next(row for row in api.get(url, headers=headers).json() if row["workflow"] == old)
        manifest = guide.release_manifest()
        publish_registry(conn, manifest)
        publish_registry(conn, manifest)
        change(guide.RELEASE, "activate", manifest["required"])
        change(guide.RELEASE, "disable", manifest["required"])
        rows = {row["workflow"]: row for row in api.get(url, headers=headers).json()}
        assert rows[old] == prior
        assert rows[guide.RELEASE]["manifest"] == manifest
        assert rows[guide.RELEASE]["grants"] == {"director": "disable", "content": "disable"}


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="Real agency registry and PostgreSQL grants required")
def test_agency_admin_cannot_activate_internal_guide():
    with postgres_api() as api, psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as conn:
        manifest = guide.release_manifest()
        publish_registry(conn, manifest)
        conn.commit()
        agency = account(api, "Agency")
        base = "/api/tenants/" + agency["tenant"]
        client = create(api, base + "/clients", agency, {"name": "Example business"})
        brand = create(api, base + "/brands", agency, {"client_id": client["id"], "name": "Example stationery"})
        campaign = create(
            api,
            base + "/campaigns",
            agency,
            {"brand_id": brand["id"], "name": "Product guide", "brief": "Prepare an instructional panel", "objective": "Explain the example product."},
        )
        path = base + "/workforce/registry/" + campaign["id"]
        denied = api.put(path, headers=agency["headers"], json={"workflow": guide.RELEASE, "skills": manifest["required"], "action": "activate"})
        assert denied.status_code == 409 and "in-house" in denied.json()["detail"]
        with Session(engine) as db:
            set_context(db, actor=agency["id"], tenant=agency["tenant"])
            sign_actor(db, agency["id"])
            with pytest.raises(IntegrityError) as denied_grant:
                db.execute(
                    text("SELECT amc_ops.change_registry(:tenant,:campaign,:release,'activate',ARRAY['director','content'])"),
                    {"tenant": agency["tenant"], "campaign": campaign["id"], "release": guide.RELEASE},
                )
            assert denied_grant.value.orig.sqlstate == "23514"
            assert denied_grant.value.orig.diag.constraint_name == "guide_inhouse_activation"
        rows = api.get(path, headers=agency["headers"]).json()
        assert next(row for row in rows if row["workflow"] == guide.RELEASE)["grants"] == {}


@pytest.mark.parametrize("locale", ["en-US", "vi-VN"])
def test_guide_preview_preserves_steps_limits_and_source_mapping(locale):
    p = projection(locale)
    p["order"]["private_test_value"] = "PRIVATE-TEST-LOCATOR"
    run = SimpleNamespace(knowledge={"c3_projection": p, "private_notes": "PRIVATE-TEST-LOCATOR"})
    body = guide.request(run, "local", node=SimpleNamespace(skill="content"))
    assert "PRIVATE-TEST-LOCATOR" not in json.dumps(body)
    raw = {"heading": "product", "layout": "checklist"}
    output = guide.validate(raw, "content", [], {"P1": {}}, {"workflow": guide.RELEASE})
    assert output["raw_reply"] == raw and output["source_ids"] == ["P1"]
    edition = guide.compose(p, output["raw_reply"])
    preview = guide.preview(edition)
    assert edition["qa_status_at_generation"] == "awaiting_editor_submission"
    assert preview["title"] == guide.titles(p)["product"]
    assert edition["steps"] == p["procedure"]["steps"] and edition["source_map"]["steps"] == ["P1", "P1"]
    assert p["procedure"]["wording"] in preview["body"]
    assert preview["body"].endswith(p["order"]["brief"]["cta"])
    updated = guide.compose(p, {"heading": "use_case", "layout": "numbered"})
    assert guide.preview(updated) != preview and updated["source_map"] == edition["source_map"]
    assert "1. " + edition["steps"][0] in guide.preview(updated)["body"]


@pytest.mark.parametrize(
    "bad", [{"heading": "Fastest setup", "layout": "numbered"}, {"heading": "product", "layout": "numbered", "steps": ["Invented"]}, {}, None]
)
def test_content_reply_cannot_replace_source_or_inject_copy(bad):
    with pytest.raises(GatewayError, match="invalid_contract_output"):
        guide.validate(bad, "content", [], {"P1": {}}, {"workflow": guide.RELEASE})


def test_source_title_is_an_editor_only_verbatim_step_with_all_limits_kept():
    p = projection()
    step = "Do not slide the strip while the tab is closed."
    p["procedure"]["steps"][1] = step
    p["procedure"]["wording"] = p["order"]["message"] = " ".join([*p["procedure"]["steps"], *p["procedure"]["limitations"]])
    selection = {"heading": "source", "layout": "checklist", "custom_title": "Guide: " + step}
    edition = guide.compose(p, selection)
    assert edition["source_map"]["title"] == "P1" and guide.preview(edition)["title"] == selection["custom_title"]
    assert all(x in guide.preview(edition)["body"] for x in p["procedure"]["limitations"])
    with pytest.raises(ValueError, match="complete approved instruction"):
        guide.compose(p, selection | {"custom_title": step.removeprefix("Do not ")})
    with pytest.raises(GatewayError, match="invalid_contract_output"):
        guide.validate(selection, "content", [], {"P1": {}}, {"workflow": guide.RELEASE})
