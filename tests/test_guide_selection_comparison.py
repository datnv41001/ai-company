"""The development arms isolate selector effects while retaining source and CTA."""

import json

import pytest

from app import product_guide_runtime as guide
from app.workforce_gateway import GatewayError
from evaluation.compare_guide_selections import QUALITY, compare, digest, released_projection


def test_committed_evidence_reproduces_on_the_released_contract():
    result = compare()
    assert result == json.loads((QUALITY / "results.json").read_text(encoding="utf-8"))
    schema = result["content_contract"]
    assert set(schema["properties"]) == set(schema["required"]) == {"heading", "layout"}
    assert schema["additionalProperties"] is False
    assert len(schema["properties"]["heading"]["enum"]) * len(schema["properties"]["layout"]["enum"]) == 4
    assert result["model_invocations"] == result["observed_practitioners"] == 0
    assert result["inference_usage"] is result["inference_latency"] is None


def test_three_arms_on_both_locales_and_complete_source():
    result = compare()
    fixtures = json.loads((QUALITY / "cases.json").read_text(encoding="utf-8"))
    assert {case["locale"] for case in fixtures} == {"en-US", "vi-VN"}
    for row, fixture in zip(result["cases"], fixtures, strict=True):
        assert row["case_id"] == fixture["case_id"]
        projection = released_projection(fixture)
        assert row["projection_sha256"] == digest(projection)
        assert all(row["brief"][key] == fixture[key] for key in ("purpose", "requirements", "exclusions", "acceptance_criteria"))
        assert [arm["arm"] for arm in row["arms"]] == ["deterministic", "editor_fixture", "controlled_model"]
        for arm in row["arms"]:
            checks = arm["checks"].copy()
            format_ok = checks.pop("visible_format_meets_explicit_requirement")
            assert all(checks.values()) and arm["page_sha256"] == digest(arm["page"])
            assert format_ok is (fixture["procedure_kind"] == "independent" or arm["arm"] != "controlled_model")
            assert arm["source_map"]["steps"] == ["P1"] * len(fixture["steps"])
            assert arm["source_map"]["limitations"] == ["P1"] * len(fixture["qualifiers"])
            assert arm["source_map"]["cta"] == "strategy_brief"
            assert arm["status_at_generation"] == "awaiting_editor_submission"
        default, editor, model = row["arms"]
        assert editor["page_sha256"] != default["page_sha256"]
        assert (editor["page"] == model["page"]) is (fixture["procedure_kind"] == "independent")


def test_content_reply_cannot_replace_instructions():
    raw = {"heading": "product", "layout": "numbered", "steps": ["Invented instruction."]}
    with pytest.raises(GatewayError):
        guide.validate(raw, "content", [], {"P1": {}}, {"workflow": guide.RELEASE})
