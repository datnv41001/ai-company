"""A mismatched sidecar or a changed source cannot silently become a trusted video preview."""

from hashlib import sha256
import json

import pytest

from scripts.render_storyboard_preview import render


def board_fixture(path):
    board = {
        "version": "amc.storyboard/1",
        "brand": "Dựng thử",
        "product": "Bản minh họa nội bộ",
        "duration_seconds": 3,
        "format": "9:16",
        "rights": "synthetic_illustration_only",
        "shots": [
            {"start_s": 0, "end_s": 1, "caption": "Xem sơ đồ.", "visual_mode": "document"},
            {"start_s": 1, "end_s": 3, "caption": "Gửi đề nghị.", "visual_mode": "request"},
        ],
        "vtt": "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nXem sơ đồ.\n\n00:00:01.000 --> 00:00:03.000\nGửi đề nghị.\n",
    }
    path.write_text(json.dumps(board, ensure_ascii=False), encoding="utf8")
    return board


def test_approved_text_and_duration_survive_mobile_preview(tmp_path):
    source, out = tmp_path / "raw.json", tmp_path / "result"
    board = board_fixture(source)
    receipt = render(source, out, "rhythm")
    assert receipt["source_sha256"] == sha256(source.read_bytes()).hexdigest()
    assert receipt["duration_seconds"] == 3 and receipt["size"] == (540, 960)
    assert (out / "captions.vtt").read_text(encoding="utf8") == board["vtt"]
    assert b"V_VP8" in (out / "preview.webm").read_bytes()
    assert all(42 <= x0 < x1 <= 453 and 105 <= y0 < y1 <= 734 for row in receipt["shots"] for x0, y0, x1, y1 in row["glyph_boxes"])
    with pytest.raises(FileExistsError):
        render(source, out, "rhythm")


@pytest.mark.parametrize("mutation", ["caption", "timeline", "safe-area", "mode", "rights", "placement"])
def test_invalid_scene_cannot_create_handoff(tmp_path, mutation):
    source, out = tmp_path / "raw.json", tmp_path / "result"
    board = board_fixture(source)
    if mutation == "caption":
        board["vtt"] = board["vtt"].replace("Gửi đề nghị", "Đã xác nhận")
    elif mutation == "timeline":
        board["shots"][1]["start_s"] = 2
    elif mutation == "safe-area":
        board["brand"] = "w" * 400
    elif mutation == "rights":
        board["rights"] = "revoked"
    elif mutation == "placement":
        board["format"] = "16:9"
    else:
        board["shots"][1]["visual_mode"] = "stock-photo-url"
    source.write_text(json.dumps(board, ensure_ascii=False), encoding="utf8")
    with pytest.raises(ValueError):
        render(source, out, "route")
    assert not out.exists()
