"""Replay the language comparison and keep all matched handoffs in the denominator."""
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPARTMENT = ROOT / "tests/evaluation/department"
DATA = DEPARTMENT / "handoff-v1"
sys.path.insert(0, str(DEPARTMENT))
from handoff_baseline import predict  # noqa: E402
from handoff_score import load, score  # noqa: E402


def test_sealed_control_and_matched_design():
    frozen = {
        "inputs": "8165c72fe3db8352c2654c1cd8e675391cfe08346d117277d23a4f0eec0fb29e",
        "labels": "cbe3c76f563abe4f91a2c24efb5e324a7a05c69a2200024874e90b8c5a4b4cf8",
        "baseline": "1db95d8754cd76515511a92cebd9f1658ca3c2e200b595a17809d658e15ac5b1",
    }
    for name, expected in frozen.items():
        assert hashlib.sha256((DATA / (name + ".json")).read_bytes()).hexdigest() == expected
    cards, labels, predictions = [load(DATA / (name + ".json")) for name in frozen]
    assert predict(cards) == predictions
    result = score(cards, labels, predictions)
    assert result == load(DATA / "scores.json")
    assert result["total"] == {"cases": 24, "exact": 14, "invalid_or_missing": 0, "unsafe_ready": 8}
    assert result["matched"] == {"both": 7, "vi_only": 0, "en_only": 0, "neither": 5}
    with pytest.raises(ValueError, match="Duplicate"):
        score(cards, labels, predictions + predictions[:1])
    assert score(cards, labels, [])["total"]["invalid_or_missing"] == 24


def test_historical_obligation_table_matches_original_reader():
    folder = ROOT / "docs/evaluation/department-study/advisory"
    records = load(folder / "SPECIALIST-READ.json")["readings"]
    report = (folder / "OBLIGATIONS.md").read_text(encoding="utf-8")
    for role in {r["task"] for r in records}:
        for brief in {r["brief"] for r in records}:
            old, revised = sorted((r for r in records if r["task"] == role and r["brief"] == brief), key=lambda r: r["arm"])
            marks = ["".join(map(str, row["marks"])) for row in (old, revised)]
            assert f"{marks[0]} → {marks[1]}, `{old['id']}` → `{revised['id']}`" in report
