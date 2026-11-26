"""Make the published rehearsal portable and detect mixed receipts or stale UI captures."""

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from app.knowledge_store import canonical, digest

ROOT = Path(__file__).resolve().parents[1] / "docs/evaluation/real-production"


@pytest.mark.parametrize("action", ["rfq", "appointment"])
def test_committed_production_bundle(action):
    screen = ROOT / "screens" / action
    session = json.loads((screen / "sessions.json").read_text(encoding="utf8"))
    for kind in ("creative", "landing"):
        folder = ROOT / action / kind
        receipt = json.loads((folder / "receipt.json").read_text(encoding="utf8"))
        assert receipt["plan_digest"] == session["plan_digest"] and receipt["digest"] == session["package_digests"][kind]
        issued = {k: v for k, v in receipt.items() if k not in ("digest", "created_by", "id", "measurement", "production_qa")}
        assert digest(canonical(issued)) == receipt["digest"]
        assert receipt["production_qa"]["digest"] == receipt["digest"] and receipt["production_qa"]["reviewer"] != receipt["created_by"]
        for name, meta in receipt["files"].items():
            payload = (folder / name).read_bytes()
            assert len(payload) == meta["bytes"] and hashlib.sha256(payload).hexdigest() == meta["sha256"]
        assert receipt["measurement"]["bytes"] == sum(f["bytes"] for f in receipt["files"].values())
    visits = json.loads((ROOT / action / "landing/sandbox-events.json").read_text(encoding="utf8"))
    assert [v["kind"] for v in visits] == ["session", action]
    assert visits[1]["value"]["session_id"] == visits[0]["entity_id"] and visits[1]["value"]["landing_digest"] == session["package_digests"]["landing"]
    for v in session["sessions"]:
        assert v["landing_viewport"] >= v["width"] * 0.85 and v["video_seconds"] == pytest.approx(6)
        for stage in ("creative", "landing"):
            for mode in ("", "-dark"):
                with Image.open(screen / f"{stage}-{v['width']}{mode}.png") as image:
                    assert image.size == (v["width"], v["height"])
