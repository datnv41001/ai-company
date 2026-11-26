"""A mismatched sidecar or a changed source cannot silently become a trusted video preview."""

from hashlib import sha256
import json
from pathlib import Path

import pytest

from scripts.render_storyboard_preview import render, visual_direction


def test_operator_style_cannot_authorize_a_product_demonstration():
    statement, qualifier = "Vách ngăn có thể tháo rời", "Áp dụng cho mẫu tiêu chuẩn."
    shot = {"purpose": "proof", "visual_mode": "mechanism", "caption": statement + ". " + qualifier, "source_ids": ["F2"]}
    fact = {"wording": statement, "qualifiers": [qualifier]}
    board = {"source_refs": {"declarations": {"F2": fact}}, "shots": [shot]}
    assert visual_direction(board, shot, "parts") == ("removable_divider", ["F2"])
    assert visual_direction(board, shot | {"source_ids": ["F7"]}, "parts")[0] == "opening"
    assert visual_direction(board, shot | {"caption": statement}, "parts")[0] == "opening"
    fact["wording"] = "Vách ngăn được gắn cố định"
    assert visual_direction(board, shot, "parts")[0] == "opening"


@pytest.mark.parametrize("case", ["index-tray", "receipt-map", "rhythm-class"])
def test_delivered_preview_matches_reviewed_runtime_revision(case):
    evaluation = Path(__file__).resolve().parents[1] / "docs/evaluation"
    source = evaluation / "wf08-storyboard" / case
    media = evaluation / "storyboard-preview" / case
    exported = (source / "reviewed.json").read_bytes()
    board = json.loads(exported)
    run = json.loads((source / "receipt.json").read_bytes())
    rendered = json.loads((media / "render.json").read_bytes())
    decoded = json.loads((media / "decoder.json").read_bytes())
    assert run["reviewed_state"] == "approved" and run["reviewed_revision"] > run["original_revision"]
    assert board["source_refs"]["manifest"] == run["manifest"]
    assert rendered["source_sha256"] == sha256(exported).hexdigest()
    for filename in ("preview.webm", "poster.png", "captions.vtt"):
        assert rendered["files"][filename] == sha256((media / filename).read_bytes()).hexdigest()
    assert rendered["files"]["preview.webm"] == decoded["video_sha256"]
    assert sha256((media / "decoded-shots.png").read_bytes()).hexdigest() == decoded["contact_sheet_sha256"]
    assert (media / "captions.vtt").read_bytes().decode() == board["vtt"]
    assert decoded["decoded"] == {"width": 540, "height": 960, "duration": board["duration_seconds"]}
    assert decoded["times_s"] == [s["start_s"] + 0.5 for s in board["shots"]]
    assert len(set(decoded["sample_sha256_rgb"])) == len(board["shots"])
    treatments = [s["illustration"] for s in rendered["shots"]]
    expected = {
        "index-tray": {"removable_divider"},
        "receipt-map": {"deliverable_map", "pending_confirmation"},
        "rhythm-class": {"pulse_strength", "session_selection"},
    }
    assert expected[case] <= set(treatments)
    for shot in rendered["shots"]:
        if shot["illustration"] in {"removable_divider", "deliverable_map", "pending_confirmation", "pulse_strength"}:
            assert shot["illustration_source_ids"] and set(shot["illustration_source_ids"]) <= board["source_refs"]["declarations"].keys()
    if case == "rhythm-class":
        assert "outgoing_request" not in treatments
        assert "Chưa có giá được duyệt" not in board["vtt"]


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
