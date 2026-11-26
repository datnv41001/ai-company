"""The offline film handoff must keep signed source bytes and change only the opening caption."""

from pathlib import Path
import json
import sys
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).parent / "evaluation/department"))
from production_edits import FOLDER, check_bundle, check_price_and_readability, read, sha, tracks  # noqa: E402


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


def test_original_price_regression_remains_visible_on_both_rated_edits():
    with ZipFile(FOLDER / "blind/rated-edits-v1.zip") as rated:
        for case in ("index-tray", "receipt-map"):
            original = json.loads(rated.read(case + "/edit.json"))
            terms = read(FOLDER / case / "evidence.json")["intake"]["commercial_terms"]
            with pytest.raises(ValueError, match="indicative price"):
                check_price_and_readability(original, terms)


def test_blind_read_matches_original_controls_and_rated_shots():
    folder = FOLDER / "blind"
    assert sha((folder / "rated-edits-v1.zip").read_bytes()) == "6db86190f026bff5bf57b5d76a385c3d6c01d88c9600f95b01a66c2d9ef292e7"
    assert sha((folder / "reader.json").read_bytes()) == "42a707f37309348be0b5f196c7560e3e6f4a50d344c4b673d7d9c27ce07059b9"
    key = read(folder / "key.json")
    paper = {r["item"]: r for r in read(folder / "anonymous.json")}
    rows = read(folder / "reader.json")["items"]
    assert len(rows) == len(key) == 4 and {r["item"] for r in rows} == set(paper) == set(key)
    with ZipFile(folder / "rated-edits-v1.zip") as rated:
        for row in rows:
            item = row["item"]
            case, arm = key[item]
            assert row["score"] == sum(c["score"] for c in row["criteria"])
            if arm == "Y":
                original = json.loads(rated.read(case + "/edit.json"))
                assert paper[item]["material"]["shots"] == original["shots"]
                assert paper[item]["material"]["variants"] == list(original["hooks"].values())
            else:
                assert arm == "X"
                source = read(FOLDER / case / "evidence.json")["creative"]["master"]["scenes"]
                assert [(s["caption"], s["from"], s["to"]) for s in source] == [
                    (s["caption"], s["start"], s["end"]) for s in paper[item]["material"]["shots"]
                ]
