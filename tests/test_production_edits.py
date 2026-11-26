"""The offline film handoff must keep signed source bytes and change only the opening caption."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent / "evaluation/department"))
from production_edits import FOLDER, check_bundle, read, tracks  # noqa: E402


def test_archived_production_edits_match_approved_files():
    check_bundle(FOLDER)
    for case in ("index-tray", "receipt-map"):
        variants = tracks(read(FOLDER / case / "edit.json"))
        a, b = (s.splitlines() for s in variants.values())
        assert [idx for idx, lines in enumerate(zip(a, b, strict=True)) if lines[0] != lines[1]] == [3]


def test_rejects_ambiguous_timeline_and_uncontrolled_variant():
    edit = read(FOLDER / "receipt-map/edit.json")
    with pytest.raises(ValueError, match="continuous"):
        tracks(edit | {"shots": [edit["shots"][0], edit["shots"][1] | {"start": 7}]})
    with pytest.raises(ValueError, match="opening line"):
        tracks(edit | {"shots": [edit["shots"][0], edit["shots"][1] | {"caption": "{hook}"}]})
