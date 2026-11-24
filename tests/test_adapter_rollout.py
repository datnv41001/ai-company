"""Rollout regressions on scoped, synthetic PostgreSQL campaigns."""

import os
import json

import psycopg
import pytest

from app.pool_worker import report
from app.registry import release
from migrations.apply import publish_registry
from test_diamond import take_node
from test_registry import frozen_run, pool as registry_pool_fixture, registry_brief

pool = registry_pool_fixture

pytestmark = pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires PostgreSQL")


BAD_CONTRACTS = [
    {"outputs": ["page_title", "meta_description", "source_ids"]},
    {"outputs": ["page_title", "meta_description", "search_intent", "source_ids", "extra"]},
    {"wrong_field_type": "page_title"},
    {"wrong_item_type": "source_ids"},
    {"role_id": "ai-market-researcher"},
    {"adapter": "content@1"},
    {"predecessors": ["ads", "content"]},
    {"predecessors": ["research"]},
    {"contract_version": 31},
    {"skill_version": 31},
    {"outputs": ["page_title", "meta_description", {"name": "search_intent", "type": "integer"}, "source_ids"]},
]


def second_release(version=3):
    from app.registry_adapters import seo_v2_digest

    manifest = release()
    manifest["workflow_version"] = version
    manifest["contracts"]["seo"].update(adapter="seo@2", adapter_digest=seo_v2_digest(), skill_version=2, contract_version=2)
    return manifest


@pytest.mark.parametrize("change", BAD_CONTRACTS)
def test_bad_release_is_atomic_before_activation(change):
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
        # New identities avoid an existing v1 primary key masking a publish-time validation error.
        bad = second_release(31)
        contract = bad["contracts"]["seo"]
        if "wrong_field_type" in change or "wrong_item_type" in change:
            from copy import deepcopy
            from app.registry_adapters import output_schema, resolve

            schema = deepcopy(output_schema(resolve(contract)))
            if "wrong_field_type" in change:
                schema["properties"]["page_title"]["type"] = "integer"
            else:
                schema["properties"]["source_ids"]["items"]["type"] = "object"
            contract["output_schema"] = schema
        else:
            contract.update(change)
        before = [
            db.execute("select count(*) from amc_ops." + table).fetchone()
            for table in ("registry_releases", "registry_versions", "registry_grants", "attempts", "ledger")
        ]
        with pytest.raises(ValueError):
            publish_registry(db, bad)
        after = [
            db.execute("select count(*) from amc_ops." + table).fetchone()
            for table in ("registry_releases", "registry_versions", "registry_grants", "attempts", "ledger")
        ]
        assert before == after


def specialist(lab, rid, skill):
    w, job = take_node(lab)
    assert job["run"] == rid
    js = job["body"]["response_format"]["json_schema"]
    assert js["name"] == skill
    output = {k: "Notebook draft for students" for k in js["schema"]["required"]}
    output["source_ids"] = ["S1"]
    assert report(w.conn, job, [output, 100, 20]) and lab.consume()
    return job["body"]["messages"][0]["content"]


def test_changed_binary_leaves_work_for_compatible_dispatcher(pool, tmp_path):
    from pathlib import Path
    import shutil
    from dispatcher_build import turn

    lab = pool
    rid = frozen_run(lab)
    specialist(lab, rid, "content")
    root = Path(__file__).resolve().parents[1]
    for name in ("app", "migrations", "catalog"):
        shutil.copytree(root / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    gateway = tmp_path / "app/workforce_gateway.py"
    source = gateway.read_text(encoding="utf-8")
    gateway.write_text(source.replace("Avoid invented search volume.", "Use a verified source for rankings."), encoding="utf-8")
    for w in lab.workers:
        w.take()
    probe = turn(tmp_path, lab, "dispatch")
    assert not probe["worked"] and probe["digest"] != release()["contracts"]["seo"]["adapter_digest"]
    assert lab.owner.execute("select state from workforce_runs where id=%s", (rid,)).fetchone() == ("queued",)
    w, job = take_node(lab)
    raw = {"page_title": "Student notebooks", "meta_description": "Browse the A5 notebook", "search_intent": "A5 notebook", "source_ids": ["S1"]}
    assert report(w.conn, job, [raw, 100, 20])
    assert not turn(tmp_path, lab, "consume")["worked"]
    assert lab.owner.execute("select status from amc_ops.attempts where id=%s", (job["id"],)).fetchone() == ("reported",)
    assert lab.consume()
    assert lab.owner.execute("select state from workforce_runs where id=%s", (rid,)).fetchone() == ("awaiting_qa",)


def test_mid_run_adapter_rollout(pool):
    lab = pool
    rid = frozen_run(lab)
    specialist(lab, rid, "content")
    base, admin, _, _, campaign = lab.cases[0]

    def trace(run):
        return lab.api.get(base + "/workforce/runs/" + run, headers=admin["headers"]).json()

    before = trace(rid)["registry"]
    second = second_release()
    from app.registry_adapters import resolve, output_schema

    second["contracts"]["seo"]["output_schema"] = output_schema(resolve(second["contracts"]["seo"]))
    with lab.owner.transaction():
        publish_registry(lab.owner, second)
        publish_registry(lab.owner, second)
    assert second["contracts"]["seo"]["adapter_digest"] != release()["contracts"]["seo"]["adapter_digest"]
    v1_prompt = specialist(lab, rid, "seo")
    after = trace(rid)
    assert after["state"] == "awaiting_qa" and after["deliverable_id"]
    for key in ("workflow", "manifest_digest", "plan_digest"):
        assert after["registry"][key] == before[key]
    assert "literal search query" not in v1_prompt

    workflow = second["workflow_id"] + "@" + str(second["workflow_version"])
    lab.api.put(
        base + "/workforce/registry/" + campaign, headers=admin["headers"], json={"workflow": workflow, "action": "activate", "skills": second["required"]}
    ).raise_for_status()
    path, terms = registry_brief(lab)
    new = lab.api.post(path, headers=admin["headers"], json={**terms, "registry_workflow": workflow}).json()["id"]
    w, job = take_node(lab)
    from test_dynamic_plan import node

    assert report(w.conn, job, [{"nodes": [node("copy", "content"), node("meta", "seo", ["copy"])]}, 120, 30]) and lab.consume()
    specialist(lab, new, "content")
    assert "literal search query" in specialist(lab, new, "seo")
    done = trace(new)
    assert done["state"] == "awaiting_qa" and done["deliverable_id"] != after["deliverable_id"]
    print(json.dumps({"v1": after["registry"]["plan_digest"], "v2": done["registry"]["plan_digest"]}))
