"""Exercise an editor's ordinary and controlled revisions against actual worker and QA receipts."""

from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from app import storyboard_editions as editions
from app import video_storyboard as video
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from test_c3_authority import doc_and_decision
from test_claim_desk import reader
from test_registry import PG
from test_video_storyboard import CASES, ROOT, start, work, pool as registry_pool

pool = registry_pool


def inputs(record):
    return {"expected_qa_revision": record["revision"], "expected_content_digest": record["content_digest"]}


@PG
def test_offline_hook_experiment_and_editor_handoff(pool):
    lab = pool
    api = lab.api
    base, owner, buyer, prep, _, queued = start(lab, CASES[-1])
    rid = queued["id"]
    states = []
    work(lab, rid, "director", states)
    work(lab, rid, "storyboard", states)
    run_url = base + "/workforce/runs/" + rid
    edition_url = run_url + "/storyboard-edition"
    trace = accepted(api.get(run_url, headers=owner["headers"]))
    raw = json.loads(trace["checkpoints"][-1]["output"]["text"])
    doc, old = doc_and_decision(lab, base, owner, rid)
    baseline = {k: old[k] for k in ("expected_qa_revision", "expected_content_digest")}
    staff = reader(api, owner, "editor")
    qa = reader(api, owner, "admin")

    def edit(fields, actor=owner):
        return api.post(edition_url, headers=actor["headers"], json=fields)

    assert api.patch(doc + "/draft", headers=owner["headers"], json={
        "title": "Storyboard", "client_preview": video.json_text(raw | {"rights": "third_party_licensed"}),
    }).status_code == 409
    for unscoped in (buyer, lab.cases[1][2], lab.y, staff):
        assert edit(baseline | {"hook_variant": "audience"}, unscoped).status_code in (403, 404)
    for forged in ({"rights": "real_photography"}, {"offer": "free"}, {"shot_edits": [{"shot": 2, "caption": "Bảo đảm kết quả."}]},
                   {"mode": "controlled_hook", "hook_variant": "audience", "durations": [6, 8, 4]},
                   {"mode": "controlled_hook", "hook_variant": "direct"}, {"shot_order": [3, 2, 1]}):
        assert edit(baseline | forged).status_code in (409, 422)

    condition = accepted(edit(baseline | {"mode": "controlled_hook", "hook_variant": "audience"}))
    variant = condition["storyboard"]
    comparison = condition["receipt"]["comparison"]
    assert comparison["changed_variables"] == ["hook"] and comparison["baseline_holds"] == comparison["candidate_holds"]
    assert comparison["landing"] == {"kind": "offline_no_landing"} and comparison["distribution"]["kind"] == "offline_no_delivery"
    assert comparison["outcome"] is None and comparison["observed_traffic"] == comparison["spend_microusd"] == 0
    assert raw["shots"][1:] == variant["shots"][1:] and raw["hook"] != variant["hook"]
    assert [(s["start_s"], s["end_s"]) for s in variant["shots"]] == [(0, 5), (5, 13), (13, 18)]
    assert variant["vtt"] == video.captions(variant["shots"])
    assert edit(baseline | {"hook_variant": "audience"}).status_code == 412

    def approve(record):
        accepted(api.post(doc + "/submit", headers=staff["headers"]))
        return accepted(api.post(doc + "/review", headers=qa["headers"], json=old | inputs(record)))

    approved_variant = approve(condition)
    assert approved_variant["reviewed_by"] == qa["id"]
    # Reword spoken direction, keep approved caption words, frame the demonstration
    # and move a second from the first to the last shot in ordinary editorial mode.
    shot = variant["shots"][1]
    adjusted = accepted(edit(inputs(condition) | {
        "shot_edits": [{"shot": 2, "narration": "look", "framing": "detail", "caption": shot["caption"]}],
        "editor_note": "Giữ nhịp ở thẻ cuối để người xem kịp chọn buổi.", "durations": [4, 8, 6], "shot_order": [1, 2, 3],
    }))
    edited = adjusted["storyboard"]
    assert edited["source_refs"] == raw["source_refs"] and edited["rights"] == raw["rights"] and edited["cta"] == raw["cta"]
    assert edited["shots"][1]["voice"] == "Hãy xem. " + shot["voice"]
    assert edited["shots"][1]["visual"].endswith(editions.FRAMING["detail"])
    assert edited["editorial"]["editor_note"] not in edited["vtt"]
    edit_report = adjusted["receipt"]["comparison"]
    assert {"visual", "body", "timeline"}.issubset(edit_report["changed_variables"])
    assert edit_report["classification"] == "editorial_revision"
    approved_editorial = approve(adjusted)
    assert approved_editorial["reviewed_by"] == qa["id"]
    # A later controlled edit holds the actual editor's choices, including their cue timing.
    latest = accepted(edit(inputs(adjusted) | {"mode": "controlled_hook", "hook_variant": "observation"}))
    assert latest["receipt"]["baseline_board_digest"] == editions.fingerprint(edited)
    assert latest["storyboard"]["shots"][1:] == edited["shots"][1:]
    assert latest["receipt"]["comparison"]["changed_variables"] == ["hook"]
    final_qa = approve(latest)
    manifest_history = accepted(api.get(trace["marketing_provenance"], headers=owner["headers"]))
    rows = lab.owner.execute(
        "select id, actor, result from knowledge_commands where operation='c3_qa' and snapshot_id=%s order by effective_at",
        (raw["source_refs"]["manifest"]["id"],),
    ).fetchall()
    approved = [{"id": key, "actor": actor, "decision": result} for key, actor, result in rows]
    assert [r["decision"]["content_digest"] for r in approved] == [x["content_digest"] for x in (condition, adjusted, latest)]
    assert all(r["actor"] == qa["id"] and r["decision"]["edition_receipt"] for r in approved)
    if folder := os.environ.get("AMC_STORYBOARD_EDITION_EVIDENCE"):
        output = Path(folder)
        output.mkdir(parents=True, exist_ok=True)
        package = {"raw": raw, "baseline": baseline, "first_candidate": condition, "editorial": adjusted,
                   "edited_baseline_candidate": latest, "workers": states, "independent_qa": [approved_variant, approved_editorial, final_qa],
                   "manifest_history": manifest_history, "qa_receipts": approved}
        (output / "rhythm-class-offline-comparison.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")
    accepted(withdraw(api, owner, prep))
    assert edit(inputs(latest) | {"hook_variant": "direct"}).status_code == 409


def test_equivalence_checks_cover_additional_fields_and_split_declaration_order():
    raw = json.loads((ROOT / "docs/evaluation/wf08-storyboard/rhythm-class/raw.json").read_text(encoding="utf8"))
    candidate = deepcopy(raw)
    candidate["hook"] = "Bạn thấy chi tiết nào?"
    candidate["shots"][0].update(voice=candidate["hook"], caption=candidate["hook"])
    candidate["vtt"] = video.captions(candidate["shots"])
    candidate["unexpected"] = "a changed creative element"
    with pytest.raises(ValueError, match="only the actual hook"):
        editions.comparison(raw, candidate, "controlled_hook", {}, {})
    assert "brief_and_direction" in editions.comparison(raw, candidate, "editorial", {}, {})["changed_variables"]

    def shot(source, caption):
        return dict(raw["shots"][1], source_ids=[source], voice=caption, caption=caption)

    shots = [raw["shots"][0], shot("F1", "Một."), shot("F1", "Phạm vi một."), shot("F2", "Hai."), raw["shots"][-1]]
    editions.validate_layout(shots, [3, 3, 3, 3, 6], 18)
    original = raw | {"shots": shots, "vtt": video.captions(shots)}
    projection = {"task_intent": {"exclusions": []}, "brand_guidelines": {"prohibited_claims": []}}
    def edit(order):
        request = editions.StoryboardEdit(expected_qa_revision=1, expected_content_digest="0" * 64, shot_order=order)
        return editions.apply_edits(original, request, projection, None)
    lead = editions.StoryboardEdit(expected_qa_revision=1, expected_content_digest="0" * 64, shot_edits=[{"shot": 4, "proof_lead": "read"}])
    captioned = editions.apply_edits(original, lead, projection, None)
    assert captioned["shots"][3]["voice"] == captioned["shots"][3]["caption"] == "Đọc thẻ. Hai."
    lead.shot_edits[0].proof_lead = "none"
    assert editions.apply_edits(captioned, lead, projection, None)["shots"][3]["caption"] == "Hai."
    reordered = edit([1, 4, 2, 3, 5])
    assert [s["voice"] for s in reordered["shots"][1:-1]] == ["Hai.", "Một.", "Phạm vi một."]
    with pytest.raises(ValueError, match="qualifiers together"):
        edit([1, 3, 4, 2, 5])
