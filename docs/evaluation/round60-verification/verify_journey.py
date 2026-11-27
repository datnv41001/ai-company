"""Verify one synthetic AMC distribution using only its exported bytes and receipts."""
from hashlib import sha256
import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_bytes())


def digest(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode()).hexdigest()


def cue_time(value):
    hours, minutes, seconds, ms = map(int, re.fullmatch(r"(\d\d):(\d\d):(\d\d)\.(\d{3})", value).groups())
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + ms


def verify(folder):
    receipt = read(folder / "receipt.json")
    dist = receipt["distribution"]
    raw = read(folder / "worker-board.json")
    board = read(folder / "approved-edition.json")
    story, landing, qa = (dist[k] for k in ("storyboard", "landing", "preview_qa"))
    assert dist["distribution_digest"] == digest({k: v for k, v in dist.items() if k not in {"id", "distribution_digest", "preview_qa"}})
    assert receipt["states"][0]["id"] == story["run_id"] != landing["run_id"]
    assert raw["source_refs"] == board["source_refs"] and raw["source_refs"]["manifest"] == story["manifest"]
    checkpoint = receipt["raw_checkpoint"]
    assert checkpoint["skill"] == "storyboard" and digest(checkpoint) == story["checkpoint_digest"]
    assert json.loads(checkpoint["output"]["text"]) == raw and checkpoint["output"]["storyboard_digest"] == digest(raw)
    assert digest(board) == story["board_digest"] == dist["preview"]["renderer"]["source_sha256"]
    assert raw["rights"] == board["rights"] == "synthetic_illustration_only"
    assert raw["cta"] == board["cta"] and raw["buyer_action"] == board["buyer_action"]
    assert story["revision"] > 1 and story["queue_receipt"] and story["qa_receipt"] and qa["receipt"] and qa["reviewer"]
    if "edition_receipt" in receipt:
        edition = receipt["edition_receipt"]
        for key in ("run_id", "document_id", "revision", "board_digest", "content_digest"):
            assert edition[key] == story[key], key
        assert edition["baseline_board_digest"] == digest(raw) and edition["baseline_revision"] < edition["revision"]
        documents = receipt["qa_documents"]
        assert json.loads(documents["raw"]["preview"]) == raw
        assert json.loads(documents["approved"]["preview"]) == board
        assert digest(documents["raw"]) == edition["baseline_content_digest"]
        assert digest(documents["approved"]) == edition["content_digest"] == story["content_digest"]
    if "content_checkpoint" in receipt:
        assert receipt["release"] == 2
        content = read(folder / "content-handoff.json")
        c = receipt["content_checkpoint"]
        assert c["skill"] == "content" and c["plan_revision"] == checkpoint["plan_revision"]
        assert json.loads(c["output"]["sections"]["content_handoff"]) == content
        assert digest(content) == c["output"]["text"] == c["output"]["handoff_digest"]
        assert raw["content_handoff_digest"] == board["content_handoff_digest"] == digest(content)
        assert content["manifest"] == story["manifest"] and content["role"] == "ai-copywriter-content-strategist"
        assert all(content[k] == receipt["task_intent"][k] for k in ("purpose","channel","audience","editorial_style"))
        assert all(d["source_id"] in raw["source_refs"]["declarations"] for d in content["channel_copy"]["declarations"])
        assert content["channel_copy"]["opening"] == raw["hook"] and content["channel_copy"]["action"] == raw["cta"]
        selected = [d for d in content["channel_copy"]["declarations"] if d["source_id"] == content["message_source_id"]]
        assert len(selected) == 1 and selected[0]["lines"][0] == raw["source_refs"]["declarations"][content["message_source_id"]]["wording"]
    media = dist["preview"]["renderer"]
    assert set(media["files"]) == {"poster.png", "captions.vtt", "preview.webm"}
    for name, expected in media["files"].items():
        assert sha256((folder / name).read_bytes()).hexdigest() == expected, name
    assert media["files"]["preview.webm"] == dist["preview"]["file_digest"]
    assert media["size"] == [540, 960] and media["audio_tracks"] == 0 and media["frames_per_second"] == 1
    assert sha256((folder / "landing.html").read_bytes()).hexdigest() == landing["file_digest"]
    vtt = (folder / "captions.vtt").read_text(encoding="utf8")
    assert vtt == board["vtt"]
    header, *cues = vtt.strip().split("\n\n")
    assert header == "WEBVTT"
    for i, (block, shot, frame) in enumerate(zip(cues, board["shots"], media["shots"], strict=True), 1):
        number, interval, *caption = block.splitlines()
        assert int(number) == i and "\n".join(caption) == shot["caption"]
        a, b = map(cue_time, interval.split(" --> "))
        assert a == shot["start_s"] * 1000 == frame["from_s"] * 1000
        assert b == shot["end_s"] * 1000 == frame["to_s"] * 1000
    assert media["duration_seconds"] == board["shots"][-1]["end_s"]
    visit, sub, crm = (receipt[k] for k in ("visit", "submission", "crm"))
    assert visit["value"]["landing_source"] == sub["value"]["landing_source"] == crm["value"]["landing_source"]
    source = visit["value"]["landing_source"]
    for key, value in dist["scope"].items():
        assert source[key] == value
    for key in ("plan_id", "plan_digest", "package_id", "package_digest", "file_digest", "document_id"):
        assert source[key] == landing[key], key
    assert source["studio_revision"] == landing["revision"]
    assert source["storyboard_distribution"] == dict(id=dist["id"], digest=dist["distribution_digest"],
        run_id=story["run_id"], revision=story["revision"], preview_sha256=media["files"]["preview.webm"], preview_qa=qa["receipt"])
    assert visit["plan_id"] == sub["plan_id"] == landing["plan_id"]
    assert sub["value"]["session_id"] == crm["value"]["session_id"] == visit["entity_id"]
    assert sub["entity_id"] == crm["value"]["id"] and sub["sequence"] > visit["sequence"]
    authority, metric = receipt["measurement_authority"], receipt["measurement"]
    assert authority["approved_plan_id"] == landing["plan_id"] and authority["plan_digest"] == landing["plan_digest"]
    for key in ("id", "digest"):
        assert authority["landing_manifest"][key] == landing["manifest"][key]
    assert authority["sandbox_evidence"]["plan_id"] == landing["plan_id"] and authority["plan_approval"]["receipt"]
    assert metric["window"] == "approved_plan_lifetime" and metric["valid_submissions"] == metric["landing_visits"] == 1
    assert metric["inquiries"] == 1 and metric["qualified_rfqs"] == metric["orders"] == 0
    assert receipt["primary_kpi"] is None and receipt["creative_effectiveness"] is None and receipt["paid_media_spend"] == 0
    expected = {"other_customer": 404, "foreign_tenant": 404, "stale_revision": 412, "self_approval": 409,
                "unsigned_preview": 409, "replay_as_unbound_submission": 409, "reused_request_changed_style": 409}
    if receipt["release"] == 2:
        expected.update(agency_owner_cross_client_source=404, stale_distribution_after_edit=409)
        assert receipt["offline_comparison"]["changed_variables"] == ["hook"]
    else:
        expected["withdrawn_source"] = 409
    assert expected.items() <= receipt["rejected"].items()
    return {"scope": dist["scope"], "storyboard": story, "landing": landing, "source_revisions_digest": dist["source_revisions_digest"],
            "source_claims": raw["source_refs"]["declarations"], "source_guidelines_digest": raw["source_refs"]["guidelines"],
            "source_pin_coverage": "The API receipt binds the approved shared source projection digest and each manifest ID/digest. This export contains the content and storyboard sources. Recomputing both complete manifest projections independently requires rerunning the pinned PostgreSQL test.",
            "preview_qa": qa, "distribution_id": dist["id"], "distribution_digest": dist["distribution_digest"],
            "worker_board_sha256_canonical": digest(raw), "approved_board_sha256_canonical": digest(board),
            "content_handoff_digest": board.get("content_handoff_digest"), "preview_sha256": media["files"]["preview.webm"],
            "visit_id": visit["id"], "session_id": visit["entity_id"], "submission_id": sub["id"], "crm_id": crm["value"]["id"],
            "measurement": metric, "rejected": receipt["rejected"]}


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print(json.dumps(verify(Path(arg)), ensure_ascii=True))
