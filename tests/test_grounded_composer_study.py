"""Synthetic regression of composer boundaries. Mutate inputs, never historical receipts."""
import json
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests/evaluation/c3"))
from grounded_composer_study import WF, compose, evaluate, flat  # noqa: E402
from buyer_journey_playbooks import journey_for  # noqa: E402


def inputs():
    case = {"workflow": "WF-13", "product": "Mẫu thử", "buyer_action": "rfq", "audience": "nhà phân phối",
            "region": "Quận A", "channel": "web", "locale": "vi-VN", "facts": [
                {"id": "material", "wording": "Mẫu thử dùng giấy.", "qualifiers": "Áp dụng tại Quận A."},
                {"id": "price", "wording": "Giá tổng hợp.", "qualifiers": "Theo số hộp.", "price": {"unit": "box"}}]}
    declaration = "Mẫu thử dùng giấy. Áp dụng tại Quận A."
    terms = declaration + "\nGiá tổng hợp. Theo số hộp."
    groups = {"copy": {"headline": "Giấy", "value_proposition": "Xem quy cách.", "benefit": declaration,
                       "commercial_terms": terms, "call_to_action": "Yêu cầu báo giá"},
              "seo": {"page_title": "Quy cách", "meta_description": "Giấy.", "search_intent": "Vật liệu."}}
    intent = {k: case[k] for k in ("buyer_action", "locale", "audience", "channel", "region", "product")}
    return case, {"workflow": WF["WF-13"], "task_intent": intent, "deterministic": {"groups": groups}}


def test_terms_cta_field_count_and_original_survive_bounded_correction():
    case, record = inputs()
    initial = deepcopy(record["deterministic"]["groups"])
    record["composed"] = {"groups": {"copy": {"benefit": "Cam kết có hàng ngay. F1"}}}
    result = compose(case, record)
    groups = result["groups"]
    assert groups["copy"]["benefit"] == initial["copy"]["benefit"]
    assert result["correction"]["attempts"] == 1
    assert result["correction"]["original"] == record["composed"]["groups"]["copy"]["benefit"]
    assert "Cam kết" not in str(groups)
    assert groups["copy"]["commercial_terms"] == initial["copy"]["commercial_terms"]
    assert groups["copy"]["call_to_action"] == initial["copy"]["call_to_action"]
    assert record["deterministic"]["groups"] == initial and flat(groups).keys() == flat(initial).keys()
    assert "số hộp" in result["action"]["buyer_step"]
    assert result["field_types"]["seo"]["search_intent"] == "hypothesis"


def test_preserve_exact_qualified_fact_and_block_missing_or_ambiguous_inputs():
    case, record = inputs()
    assert compose(case, record)["correction"] is None
    with pytest.raises(ValueError, match="Task origin mismatch"):
        compose({**case, "region": "Changed"}, record)
    with pytest.raises(ValueError, match="Buyer action outside"):
        journey_for("new-unreviewed-action", "box")
    change = deepcopy(record)
    del change["deterministic"]["groups"]["copy"]["call_to_action"]
    with pytest.raises(ValueError, match="Field contract"):
        compose(case, change)
    record["deterministic"]["groups"]["copy"]["commercial_terms"] = "Mẫu thử dùng giấy."
    with pytest.raises(ValueError, match="scoped material"):
        compose(case, record)


def test_checked_in_report_keeps_assigned_failure_denominator_and_distinct_decisions():
    report = json.loads((ROOT / "docs/evaluation/buyer-journey-v1/REGRESSION.json").read_bytes())
    assert report["historical_states"] == {"awaiting_qa": 8, "failed": 2}
    assert report["assigned"] == report["offline_candidates"] == 10 and report["historical_model_pairs"] == 8
    assert sum(r["historical_model_attempt_count"] for r in report["rows"]) == 30
    assert report["new_model_invocations"] == 0 and report["human_acceptance"] is None
    assert report["commercial_qa"] == "not_run"
    for row in report["rows"]:
        candidate = row["candidate"]
        base = flat(row["original_groups"]["deterministic"])
        fields = flat(candidate["groups"])
        assert base.keys() == fields.keys() and all(fields.values())
        field = candidate["protected_field"]
        assert fields[field] == base[field]
        if row["historical_state"] == "failed":
            assert row["original_groups"]["model_assisted"] is None
            assert row["model_assisted_comparison"] is None


def test_refuse_altered_historical_receipt(tmp_path):
    case = tmp_path / "v2-01"
    case.mkdir()
    (case / "result.json").write_text('{"case":"v2-01"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Unrecognized result bytes"):
        evaluate(tmp_path)
