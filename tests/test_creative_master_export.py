"""The editable master actually recreates the encoded images and film offline."""

import json
from copy import deepcopy
from pathlib import Path

from app.production_creative import render


def test_master_round_trip_and_non_destructive_edit():
    original = json.loads((Path(__file__).resolve().parents[1] / "docs/evaluation/real-production/rfq/creative/master.json").read_text(encoding="utf8"))
    before = render(deepcopy(original))
    replay = render(json.loads(before["master.json"][1]))
    assert before == replay
    modified = deepcopy(original)
    modified["layout"] = "text_first" if modified["layout"] == "art_first" else "art_first"
    modified["scenes"][1]["caption"] = "Bản thử nghiệm biên tập."
    after = render(modified)
    assert before["source.png"] == after["source.png"]
    for key in ("landscape.png", "square.png", "portrait.png", "preview.webm", "captions.vtt", "master.json"):
        assert before[key] != after[key]
