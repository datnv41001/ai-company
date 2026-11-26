"""Replay the frozen evidence, without inference, whenever its inputs or scoring change."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests/evaluation/department"))
from advisory_score import evaluate  # noqa: E402
from pack_advisory import reconcile  # noqa: E402


def test_archived_claims_quotes_specialist_drafts_and_scoring():
    folder = ROOT / "docs/evaluation/department-study/advisory"
    scores = evaluate(folder / "FIRST-RUN.zip")
    assert scores == json.loads((folder / "SCORES.json").read_text(encoding="utf-8"))
    assert {key: row["calls"] for key, row in scores["usage"].items()} == {"inputs": 60, "stress-inputs": 24, "specialists": 12}
    for split in scores["slices"].values():
        assert sum(name.startswith("category/") for name in split) == 12
        assert {"language/vi", "language/en"} <= set(split)


def test_reader_decisions_match_all_sealed_candidates(tmp_path):
    folder = ROOT / "docs/evaluation/department-study/advisory"
    with ZipFile(folder / "BLIND-READ.zip") as z:
        for name in ("cards.json", "key.json", "verdicts.json"):
            (tmp_path / name).write_bytes(z.read(name))
    joined = reconcile(folder / "FIRST-RUN.zip", tmp_path / "cards.json", tmp_path / "key.json", tmp_path / "verdicts.json")
    assert joined == json.loads((folder / "SPECIALIST-READ.json").read_text(encoding="utf-8"))
