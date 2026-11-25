from copy import deepcopy
import json

import pytest

from app.campaign_lab import REVIEWS, SCENARIO, asset_pack, propose
from app.campaign_work_units import measure_lab_units


def test_commissioned_units_survive_replay_missing_output_and_edit():
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8"))
    assets = asset_pack(scenario, propose(scenario))
    key = scenario["scenario_id"]
    original = measure_lab_units(key, assets, reviews)
    assert original == measure_lab_units(key, assets + assets, reviews)
    assert original["fixture_accepted"] == original["requested"] == 6
    assert original["business_accepted"] == 0 and original["cost_per_business_accepted_vnd"] is None
    changed = deepcopy(assets[:-1])
    changed[0]["revision"] += 1
    result = measure_lab_units(key, changed, reviews)
    assert result["requested"] == 6 and result["fixture_accepted"] == 4
    assert result["rows"][0]["unit_id"] == original["rows"][0]["unit_id"]
    assert result["rows"][0]["accepted_revision"] is None
    assert result["rows"][-1]["status"] == "missing"
    with pytest.raises(ValueError, match="Ambiguous"):
        measure_lab_units(key, assets + changed, reviews)
