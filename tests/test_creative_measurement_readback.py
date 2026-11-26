"""Qualification of historical landing intake and the proposed 21-day creative experiment."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests/evaluation/department"))
from creative_measurement import readback  # noqa: E402


def packet(case):
    return json.loads((ROOT / "docs/evaluation/campaign-production-review" / case / "evidence.json").read_text(encoding="utf-8"))


def test_recorded_intake_and_kpi_have_different_denominators():
    tray = readback(packet("index-tray"))
    survey = readback(packet("receipt-map"))
    assert [tray[k] for k in ("visit", "inquiry", "qualified_rfq", "sales_acceptance", "quote", "order", "confirmed_revenue_vnd")] == [1, 1, 0, 0, 0, 0, 0]
    assert tray["primary_measurement"] is None and tray["window"] == "approved_plan_lifetime"
    assert survey["appointment_request"] == 1 and survey["confirmed_appointment"] == 0
    assert survey["primary_measurement"]["denominator"] == 1 and survey["primary_measurement"]["numerator"] == 0
    for observation in (tray, survey):
        assert observation["assignee_at_submission"] is None and observation["creative_effect_estimate"] is None


def test_refuse_mismatched_edition():
    changed = packet("receipt-map")
    changed["events"][1]["value"]["landing_source"]["brand_id"] = "different-brand"
    with pytest.raises(ValueError, match="mismatch"):
        readback(changed)


def test_refuse_invented_primary_kpi_and_changed_confirmation():
    changed = packet("receipt-map")
    changed["intake"]["primary_measurement"]["numerator"] = 1
    with pytest.raises(ValueError, match="disagrees"):
        readback(changed)
    tray = packet("index-tray")
    tray["intake"]["primary_measurement"] = {"window_days": 21}
    with pytest.raises(ValueError, match="No approved primary KPI"):
        readback(tray)
