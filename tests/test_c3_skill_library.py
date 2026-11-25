"""Skill release, privacy and commercial-language regressions on synthetic briefs."""

from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from fastapi import HTTPException

from app import c3_assets as assets, c3_marketing as historical, c3_releases as releases, c3_skill_library as library
from app import registry_compatibility
from app.registry_adapters import Adapter
from app.workforce_gateway import GatewayError
from scripts.build_c3_releases import manifest

ROOT = Path(__file__).resolve().parents[1]
CASES = {c["id"]: c for c in json.loads((ROOT / "tests/evaluation/c3/cases.json").read_text(encoding="utf-8"))["cases"]}


def projection(case):
    data = deepcopy(CASES[case])
    for i, f in enumerate(data["facts"], 1):
        f["id"] = f"F{i}"
        f["qualifiers"] = [f["qualifiers"]]
    data.update(task_intent={"purpose": "PRIVATE PURPOSE", "requirements": ["PRIVATE TASK"], "region": data["region"],
                             "exclusions": ["FORBIDDEN PROMISE"], "acceptance_criteria": ["PRIVATE ACCEPTANCE"]},
                brand_guidelines={"guidance": "PRIVATE STYLE", "prohibited_claims": ["CLAIM TO WITHHOLD"]})
    return data


@pytest.mark.parametrize("stage,ref", [(s, r) for s, refs in library.PACKS.items() for r in refs])
def test_each_versioned_skill_executes_its_own_output_contract(stage, ref):
    entry = library.method(ref)
    all_methods = [library.method(r) for r in library.PACKS[stage]]
    good = {k: v for m in all_methods for k, v in m["examples"]["good"].items()} | {"source_ids": ["F1"]}
    actual = library.validate(good, stage, [], {"F1": {}})
    assert actual["marketing_skills"][ref] == library.method_digest(entry)
    assert actual["raw_reply"] == good
    assert all(actual["sections"][k] == entry["examples"]["good"][k] for k in entry["output_schema"]["required"])
    assert entry["method"] and entry["rubric"] and entry["prohibited"] and entry["applicability"]
    assert all(("#" * 2 + " " + r) in (ROOT / "docs/research/KNOWLEDGE_CARDS.md").read_text(encoding="utf-8") for r in entry["references"])
    bad = dict(good)
    del bad[entry["output_schema"]["required"][0]]
    with pytest.raises(GatewayError):
        library.validate(bad, stage, [], {"F1": {}})
    with pytest.raises(GatewayError):
        library.validate(good | {"source_ids": ["absent"]}, stage, [], {"F1": {}})


@pytest.mark.parametrize("release,file", [(assets.RESEARCH, "research-strategy-v3"), (assets.LANDING, "landing-seo-v6"),
                                           (historical.RESEARCH, "research-strategy-v2"), (historical.LANDING, "landing-seo-v5")])
def test_reproducible_release_and_method_pins(release, file, monkeypatch):
    expected = json.loads((ROOT / "catalog" / (file + ".json")).read_text(encoding="utf-8"))
    assert manifest(release) == expected
    if not releases.is_current(release):
        assert "marketing_methods" not in expected
        return
    # Pure contract check. The real publisher additionally requires the approved runtime fingerprint.
    monkeypatch.setattr(registry_compatibility, "resolve", lambda c: Adapter(c["skill_id"], c["skill_version"], c["adapter_digest"], library.request, library.validate))
    registry_compatibility.validate_manifest(expected)
    changed = deepcopy(expected)
    next(iter(changed["marketing_methods"].values()))["method"] = "changed"
    with pytest.raises(ValueError, match="skill library"):
        registry_compatibility.validate_manifest(changed)
    changed = deepcopy(expected)
    changed["contracts"]["director"]["marketing_methods"] = {"new@9": "x"}
    with pytest.raises(ValueError, match="skill pin"):
        registry_compatibility.validate_manifest(changed)


def test_role_prompts_and_seven_asset_boundary():
    data = projection("materials")
    data["brand_guidelines"]["tone"] = "thân thiện"
    knowledge = {"registry": {"workflow": assets.LANDING}, "sources": {"F1": {}, "F2": {}}, "c3_projection": data}
    for stage in ("director", "content", "seo"):
        body = library.request(SimpleNamespace(knowledge=knowledge), "local", node=SimpleNamespace(skill=stage),
                               assignment="PRIVATE DIRECTOR ASSIGNMENT")
        visible = body["messages"][1]["content"]
        assert ("PRIVATE TASK" in visible) == (stage == "director")
        assert ("PRIVATE STYLE" in visible) == (stage == "director")
        assert ("PRIVATE DIRECTOR ASSIGNMENT" in visible) == (stage == "director")
        if stage in ("content","seo"):
            assert "friendly tone" in visible
    generated = {field: "Send the area for your quote" for field in assets.COPY}
    generated["headline"] = "Gạch GB-6060 tại Hà Nội"
    generated["value_proposition"] = data["objective"] + " for our team"
    generated["benefit"] = "We make this FORBIDDEN PROMISE"
    checkpoints = {"content": {"sections": generated, "source_ids": ["F1", "F2"]},
                   "seo": {"sections": {"page_title": "PRIVATE ACCEPTANCE", "meta_description": "CLAIM TO WITHHOLD"}}}
    result = assets.artifacts(assets.LANDING, data, checkpoints)
    assert set(result) == {"research_notes","strategy_decisions","buyer_copy","seo_fields","evidence_report","measurement_plan","customer_preview"}
    assert set(result["buyer_copy"]) == {"headline","call_to_action"} and not result["seo_fields"]
    preview = result["customer_preview"]
    text = preview["body"] + preview["title"]
    assert all(v in text for v in ("210.000 VND / 1 m²", "50 m²", "đã gồm thuế", "chưa gồm vận chuyển", "Hà Nội", "1,44 m²"))
    assert all(v not in text for v in (data["objective"], "PRIVATE", "FORBIDDEN", "F1", "F2", data["hypotheses"][0]))
    assert "FORBIDDEN PROMISE" in checkpoints["content"]["sections"]["benefit"]
    assert result["evidence_report"]["suggested_handles"]["content"] == ["F1","F2"]


def test_wf03_strategy_and_measurement_are_internal_and_distinct():
    data = projection("materials")
    stages = {}
    for role in assets.ROLES[assets.RESEARCH]:
        sections = {k:v for r in library.PACKS[role] for k, v in library.method(r)["examples"]["good"].items()}
        stages[role] = {"sections": sections, "source_ids": ["F1"]}
    result = assets.artifacts(assets.RESEARCH, data, stages)
    assert set(result["strategy_decisions"]) == {"positioning","rationale","channel_choice","test_hypothesis"}
    assert "buyer_problem" in result["research_notes"]["fields"]
    assert set(result["measurement_plan"]) == {"selected_kpi","measurable_action","measurement_method"}
    assert not result["buyer_copy"] and not result["seo_fields"]
    visible = json.dumps(result["customer_preview"])
    assert all(v not in visible for v in result["strategy_decisions"].values())


def test_service_price_requires_approved_unit_and_unsupported_locale_fails_closed():
    data = projection("service")
    releases.check_capacity(historical.LANDING, data)
    with pytest.raises(HTTPException, match="exact selling unit"):
        releases.check_capacity(assets.LANDING, data)
    price = next(f for f in data["facts"] if "price" in f)
    price["price"]["unit"] = "machine"
    releases.check_capacity(assets.LANDING, data)
    body = assets.render(assets.LANDING, data, {})["body"]
    assert "180.000 VND / 1 máy" in body and "Chưa gồm linh kiện hoặc nạp gas." in body
    assert "Hải Châu" in body and "suất dịch vụ" not in body
    data["task_intent"]["exclusions"] = ["linh kiện"]
    with pytest.raises(HTTPException, match="exclusion conflicts"):
        releases.check_capacity(assets.LANDING, data)
    with pytest.raises(HTTPException, match="supported asset locale"):
        releases.check_capacity(assets.LANDING, data | {"locale":"fr-CA"})


def test_english_currency_format_units_and_order_limits():
    fact = {"id":"F1","quantity":"2.5","price":{"amount_minor":123456,"currency":"USD","unit":"kg","basis_quantity":"1",
            "tax":"excluded","moq":"2","tier_min":"2.5","tier_max":"5","conditions":["Pickup only."]},
            "qualifiers":["Pickup only."],"applicability":{"buyer":"wholesale","unit":"kg","minimum":"2.5"}}
    en = " ".join(assets.fact_lines(fact, {"locale":"en-US"}))
    vi = " ".join(assets.fact_lines(fact, {"locale":"vi-VN"}))
    assert "1,234.56 USD / 1 kg, tax excluded" in en and "Applies from 2.5 kg to 5 kg" in en
    assert "1.234,56 USD / 1 kg, chưa gồm thuế" in vi and "Áp dụng từ 2,5 kg đến 5 kg" in vi
    assert "Buyer: wholesale." in en and "Nhóm mua: bán sỉ." in vi
    assert en.count("Pickup only.") == vi.count("Pickup only.") == 1


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="PostgreSQL publisher")
def test_both_releases_publish_seven_immutable_method_rows_atomically():
    from migrations.apply import publish_registry
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
        for release in assets.ROLES:
            publish_registry(db, manifest(release))
            publish_registry(db, manifest(release))
        expected = {library.method(r)["id"]:library.method(r) for pack in library.PACKS.values() for r in pack}
        selected = db.execute("select id,definition from amc_ops.registry_versions where kind='marketing_skill' and version=1 and id=any(%s)",(list(expected),))
        assert dict(selected.fetchall()) == expected
