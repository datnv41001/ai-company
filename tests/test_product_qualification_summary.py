"""Synthetic evidence contracts only; these tests never read the sealed qualification brief set."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent / "evaluation/c3"))
import product_qualification_summary as summary  # noqa: E402

CHECKOUT = "a" * 40
PIN = "b" * 64
META = {
    "checkout": CHECKOUT,
    "cases_sha256": PIN,
    "model_sha256": summary.WEIGHTS,
    "provider": "llama.cpp loopback",
    "build": "synthetic-test",
    "worker_concurrency": 1,
}
CATALOG = {"WF-03": {f"s{i}": str(i) * 64 for i in range(4)}, "WF-13": {f"s{i}": str(i) * 64 for i in range(4, 7)}}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf8")


def case(cid, kind):
    roles = ["director", "research", "strategy"] if kind == "WF-03" else ["director", "content", "seo"]
    target = roles[-1] if kind == "WF-03" else "content"
    field = ["strategy", "positioning"] if kind == "WF-03" else ["seo", "meta_description"]
    groups = {field[0]: {field[1]: "draft"}}
    text_digest = summary.digest({"title": "synthetic", "preview": "example"})
    attempts = [
        {"attempt_id": cid + r, "schema": "c3_skills_" + r, "request_sha256": PIN, "raw_output": {"ok": True}, "input_tokens": 5, "output_tokens": 3}
        for r in roles
    ]
    composed = {"groups": groups, "field_findings": []}
    control = composed | {
        "raw_output": {},
        "scope": target,
        "max_invocations": 1,
        "provider_fee_usd": 0,
        "same_user_input_digest": PIN,
        "schema_digest": PIN,
        "control_user_input_digest": PIN,
        "control_schema_digest": PIN,
        "control_request_digest": "1" * 64,
        "treatment_request_digest": "2" * 64,
        "treatment_attempt_request_sha256": PIN,
        "paired_treatment_attempt_id": cid + target,
        "seconds": 1.2,
        "input_tokens": 4,
        "output_tokens": 2,
    }
    sections = dict.fromkeys(("research_notes", "strategy_decisions", "buyer_copy", "seo_fields", "evidence_report", "measurement_plan"), {})
    sections["customer_preview"] = {"current": {"digest": text_digest}}
    doc = {"id": cid + "-draft", "qa_revision": 1, "title": "synthetic", "body": "example", "digest": text_digest, "status": "draft"}
    edit = {
        "before": {"revision": 1, "groups": groups},
        "after": {"revision": 2, "status": "draft", "groups": {field[0]: {field[1]: "edited"}}},
        "field": field,
        "kind": "scripted staff edit",
        "qa_evidence": {"content_digest": PIN, "content_evidence": {"qa_revision": 2, "content_digest": PIN, "statements": [{"outcome": "unresolved"}]}},
    }
    inputs = META | {
        "case": cid,
        "workflow": summary.WF[kind],
        "arm": "improved",
        "run_id": cid + "-t",
        "state": "awaiting_qa",
        "origin": "internal",
        "task_id": cid + "-task",
        "projection_digest": PIN,
        "guideline": {"digest": PIN},
        "task_intent": {"buyer_action": "rfq"},
        "skill_digests": CATALOG[kind],
        "runtime_s": 3.2,
        "automated_journey_seconds": 9.3,
        "attempts": attempts,
        "input_tokens": 15,
        "output_tokens": 9,
        "unmetered_attempts": 0,
        "provider_fee_usd": 0,
        "deliverable": doc,
        "runtime_fingerprint": PIN,
        "binding": {"workflow": summary.WF[kind], "manifest_digest": PIN},
        "manifest": {"digest": PIN},
        "staff": {"sections": sections},
        "edited_example": edit,
        "deterministic": {"model_calls": 0, "groups": {field[0]: {field[1]: ""}}, "field_findings": [{"reason": "missing"}]},
        "composed": composed,
        "matched_instruction_control": control,
    }
    other = inputs | {"arm": "projected", "workflow": summary.OLD[kind], "run_id": cid + "-p"}
    return inputs, other


def series(folder, mode, assigned):
    return summary.series(folder, mode, CHECKOUT, assigned, PIN, CATALOG)


def setup_folder(folder):
    save(folder / "conditions.json", META)
    save(folder / "skill-digests.json", CATALOG["WF-03"] | CATALOG["WF-13"])


def test_offline_complete_paired_receipts(tmp_path):
    setup_folder(tmp_path)
    assigned = {f"synthetic-{n}": ("WF-03" if n % 2 else "WF-13") for n in range(10)}
    for cid, kind in assigned.items():
        row, old = case(cid, kind)
        save(tmp_path / cid / "result.json", row)
        save(tmp_path / cid / "previous/result.json", old)
    report = series(tmp_path, "study", assigned)
    assert report["complete"] and report["assigned"] == report["drafts"] == report["edits_with_current_qa"] == 10
    assert report["matched_role_controls"] == report["generic_vs_full_method"]["paired_drafts"] == 10
    assert report["observed_treatment_usage"]["attempts"] == report["observed_previous_usage"]["attempts"] == 30
    assert report["observed_control_tokens"] == {"input_tokens": 40, "output_tokens": 20}
    assert report["previous_release_drafts"] == report["both_releases_generated"] == 10
    assert report["deterministic_vs_full_method"]["different_fields"] == 10
    assert len(report["release_pins_on_drafted_cases"]) == 7
    assert all(r["edit"]["evidence_outcomes"] == {"unresolved": 1} for r in report["cases"].values())


def test_partially_written_series_keeps_missing_denominator_and_distinct_control(tmp_path):
    setup_folder(tmp_path)
    row, _ = case("one", "WF-03")
    assigned = {"one": "WF-03"} | {f"missing-{i}": "WF-13" for i in range(9)}
    save(tmp_path / "one/result.json", row)
    report = series(tmp_path, "study", assigned)
    assert not report["complete"] and report["observed"] == 1 and len(report["missing_or_invalid_case_ids"]) == 9
    assert report["assigned"] == 10 and report["technical_pairs"] == 0 and report["matched_role_controls"] == 1
    assert "one/previous" in report["errors"]
    row["matched_instruction_control"]["control_user_input_digest"] = "3" * 64
    save(tmp_path / "one/result.json", row)
    report = series(tmp_path, "study", assigned)
    assert not report["complete"] and report["matched_role_controls"] == 0 and "one/matched-control" in report["errors"]


def test_recovery_accounts_for_confirmed_terms_and_time(tmp_path):
    setup_folder(tmp_path)
    assigned = {"one": "WF-03"} | {f"missing-{i}": "WF-13" for i in range(19)}
    row, _ = case("one", "WF-03")
    row["correction"] = {
        "initial_status": "needs_input",
        "unit_before": "service",
        "unit_confirmed": "visit",
        "claim": "c2",
        "original_claim": "c1",
        "offer": "o2",
        "original_offer": "o1",
        "source": "s",
        "binding": "b",
        "source_excerpt": "per visit",
        "original_offer_digest": PIN,
        "timing_seconds": dict(seed_and_task=1, clarify_and_propose=2, approve=3, resume=4),
    }
    save(tmp_path / "one/result.json", row)
    report = series(tmp_path, "recovery", assigned)
    assert not report["complete"] and report["corrected"] == 1 and report["assigned"] == 20
    assert report["median_correction_stage_s"] == row["correction"]["timing_seconds"]
    assert report["confirmed_units"] == {"visit": 1} and report["technical_pairs"] == 0


@pytest.mark.parametrize("field", ["checkout", "guideline", "skill_digests", "edited_example", "input_tokens"])
def test_mixed_or_stale_receipts_never_complete(tmp_path, field):
    setup_folder(tmp_path)
    row, _ = case("one", "WF-13")
    broken = {"checkout": "0" * 40, "guideline": {}, "skill_digests": {}, "edited_example": deepcopy(row["edited_example"]), "input_tokens": 14}
    broken["edited_example"]["after"]["revision"] = 1
    row[field] = broken[field]
    save(tmp_path / "one/result.json", row)
    report = series(tmp_path, "smoke", {"one": "WF-13"})
    assert not report["complete"] and report["observed"] == 0 and "one" in report["errors"]


def test_cli_emits_partial_report_and_unmeasured_human_outcomes(tmp_path, monkeypatch):
    path = tmp_path / "report.json"
    sizes = {"study": 10, "recovery": 20, "smoke": 2}
    monkeypatch.setattr(summary, "pins", lambda root: CATALOG)
    monkeypatch.setattr(summary, "plan", lambda root, mode: ({str(i): "WF-03" for i in range(sizes[mode])}, PIN))
    monkeypatch.setattr(sys, "argv", ["summary", str(tmp_path), "--checkout", CHECKOUT, "--out", str(path), "--require-complete"])
    with pytest.raises(SystemExit, match="Incomplete evidence"):
        summary.main()
    report = json.loads(path.read_bytes())
    assert not report["complete"] and report["checkout"] == CHECKOUT
    assert {k: v["assigned"] for k, v in report["series"].items()} == sizes
    assert all(report[k] is None for k in ("human_accepted", "expert_evidence_support", "stronger_model_advantage", "time_saved_vs_manual"))
