"""Paired adversarial fixtures for Research → Strategy. These are open engineering expectations."""
import json
import os
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.strategy_study import baseline, cases, compare, export


@pytest.mark.parametrize(("name", "status", "choice", "channel", "measurement"), [
    ("route-shift", "proposed", "handoff", "supported", "supported"),
    ("route-storekeeper", "proposed", "audit", "unknown", "unknown"),
    ("route-corrected-observation", "proposed", "audit", "unknown", "unknown"),
    ("route-disagreement", "conflicting_evidence", None, "unknown", "unknown"),
    ("route-withdrawn-channel-expired-measure", "proposed", "handoff", "unknown", "unknown"),
    ("studio-first-visit", "proposed", "first_visit", "unknown", "unknown"),
    ("studio-clarify", "needs_clarification", None, "unknown", "unknown"),
    ("studio-unrepresented", "insufficient_evidence", None, "unknown", "unknown"),
    ("studio-foreign-record", "proposed", "first_visit", "unknown", "unknown"),
])
def test_same_task_two_arms(name, status, choice, channel, measurement):
    case = cases()[name]
    before, after = compare(case)
    raw_claim = case["controlled_replies"]["strategy"]["rationale"]
    assert before["staff_groups"]["strategy"]["rationale"] == raw_claim
    assert before["staff_findings"] == []
    assert before["model_calls"] == 0
    assert raw_claim not in json.dumps(after["department_handoff"])
    review = next(f for f in after["research"]["checkpoint_field_review"]
                  if f["role"] == "strategy" and f["field"] == "rationale")
    assert review["status"] == "needs_editor_review" and not review["literal_sources"]
    decision = after["strategy"]
    expected = {"status": status, "choice": choice, "channel": channel, "measurement": measurement}
    actual = {"status": decision["status"], "choice": decision["selected_option"],
              "channel": decision["channel"]["status"], "measurement": decision["measurement"]["status"]}
    if output := os.getenv("AMC_STRATEGY_CASE_RESULTS"):
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        record = {"case": name, "packet_sha256": before["packet_sha256"], "cutoff": after["as_of"],
                  "expected": expected, "actual": actual, "basis": decision["basis_sources"],
                  "standard_staff_findings": before["staff_findings"], "scripted_baseline_claim": raw_claim,
                  "claim_review": review, "handoff": after["department_handoff"]["status"]}
        (directory / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    assert actual == expected
    assert after["provenance"]["packet_sha256"] == before["packet_sha256"]
    assert after["department_handoff"]["approval"]["role"] == case["packet"]["brief"]["owner"]
    if not choice or channel != "supported":
        assert after["department_handoff"]["status"] == "hold"
        assert after["department_handoff"]["asset"] is None


def test_positive_source_control_and_counterevidence():
    case = cases()["studio-first-visit"]
    before, after = compare(case)
    research = after["research"]
    fields = {(field["role"], field["field"]): field for field in research["checkpoint_field_review"]}
    assert fields["research", "buyer_problem"]["literal_sources"] == ["studio-one"]
    quoted = next(row for row in research["observations"] if row["source_id"] == "studio-one")
    assert before["staff_groups"]["research"]["buyer_problem"] == quoted["quote"]
    assert any(row["source_id"] == "studio-two" and row["observed_action"] == "declined"
               for row in research["counterevidence"])
    assert [row["source_id"] for row in research["context_only"]] == ["studio-other"]
    assert "studio-other" not in after["strategy"]["basis_sources"]


def test_corrected_record_and_buyer_change_the_strategy_without_changing_decoder():
    variants = cases()
    before, first = compare(variants["route-shift"])
    for name in ("route-storekeeper", "route-corrected-observation"):
        assert variants[name]["controlled_replies"] == variants["route-shift"]["controlled_replies"]
        control, result = compare(variants[name])
        assert control["staff_groups"]["strategy"]["positioning"] == before["staff_groups"]["strategy"]["positioning"]
        assert result["strategy"]["selected_option"] != first["strategy"]["selected_option"]
    _, corrected = compare(variants["route-corrected-observation"])
    note = next(row for row in corrected["research"]["observations"] if row["source_id"] == "tray-one")
    assert note["revision"] == 2 and "inventory audit layout" in note["quote"]


def test_baseline_prompt_uses_same_permitted_observations_and_receives_upstream_checkpoint():
    source_case = cases()["studio-foreign-record"]
    before = baseline(source_case)
    for role in ("research", "strategy"):
        reference = before["request_contexts"][role]["reference"]
        facts = {f["id"]: f for f in reference["facts"]}
        assert set(facts) == {"studio-fact", "studio-one", "studio-two", "studio-other"}
        assert facts["studio-one"]["wording"] == source_case["packet"]["sources"][1]["excerpt"]
        assert "first_visit" in facts["studio-one"]["qualifiers"][0]
    assert before["request_contexts"]["strategy"]["predecessors"]["research"] == before["checkpoints"]["research"]
    _, after = compare(source_case)
    assert "other-client-observation" not in json.dumps([before, after])
    assert "foreign-client canary" not in json.dumps([before, after])


def test_export_preserves_its_first_outputs(tmp_path):
    destination = tmp_path / "comparison"
    export(destination)
    index = json.loads((destination / "index.json").read_bytes())
    assert {i["case"] for i in index} == set(cases())
    first = (destination / "route-shift/after.json").read_bytes()
    with pytest.raises(FileExistsError):
        export(destination)
    assert (destination / "route-shift/after.json").read_bytes() == first
    case = cases()["route-shift"]
    untouched = deepcopy(case)
    compare(case)
    assert case == untouched
