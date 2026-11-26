"""Frozen eligibility cases. These measure scope and preservation, not professional acceptance."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.c3_journey import VERSION, candidates


BRIEFS = json.loads((Path(__file__).resolve().parents[1] / "docs/evaluation/campaign-engine/eligibility-briefs.json").read_text(encoding="utf-8"))


def projection(case):
    _, product, audience, action, unit, _, _ = case
    return {"locale": BRIEFS["locale"], "channel": BRIEFS["channel"], "product": product, "audience": audience,
            "task_intent": {"buyer_action": action}, "facts": [{"id": "price-1", "price": {"unit": unit}},
                                                              {"id": "statement-2", "wording": "Thông tin có điều kiện."}]}


@pytest.mark.parametrize("case", BRIEFS["cases"], ids=lambda case: case[0])
def test_eligibility_on_new_brief(case):
    source = projection(case)
    before = deepcopy(source)
    offer = candidates(source)
    assert source == before
    assert offer["source_handles"] == ["price-1"] and offer["version"] == VERSION
    assert [(s["industry"], s["product_type"]) for s in offer["eligible"]] == ([(case[5], case[6])] if case[5] else [])
    for suggestion in offer["eligible"]:
        assert case[1] in suggestion["reason"] and case[2] in suggestion["reason"]
        assert suggestion["unit"] == case[4] and offer["action"] == case[3]
        assert {key: v["kind"] for key, v in suggestion["fields"].items()} == {
            "copy.value_proposition": "editorial", "client_strategy.activation": "editorial",
            "client_measurement.hypothesis": "hypothesis"}


@pytest.mark.parametrize("change", [{"channel": "email"}, {"locale": "en-US"},
                                   {"facts": [{"id": "a", "price": {"unit": "box"}}, {"id": "b", "price": {"unit": "piece"}}]}])
def test_general_workflow_when_scope_is_uncertain(change):
    assert not candidates(projection(BRIEFS["cases"][4]) | change)["eligible"]
