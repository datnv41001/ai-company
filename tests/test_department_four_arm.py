"""Missing practitioners and a reused reviewer must never become acceptance evidence."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).parent / "evaluation/department"))
import four_arm_pilot as study  # noqa: E402


def test_commissioned_arms_and_blind_packets(tmp_path):
    kit = tmp_path / "kit"
    study.prepare(kit)
    design = json.loads((kit / "custodian.json").read_text())
    assert len(design) == 8
    with ZipFile(kit / "work-orders.zip") as orders, ZipFile(kit / "scorecards.zip") as cards:
        for brief in {k.split("/")[0] for k in design}:
            names = {v: k for k, v in design.items() if k.startswith(brief + "/")}
            assert set(names) == set(study.ARMS)
            assert orders.read(names["ai_assisted"] + "/starting.md") == orders.read(names["ai_plus_independent_qa"] + "/starting.md")
        assert not any(f.endswith(("preqa.json", "treatment.txt")) for f in cards.namelist())
    result = study.score(design, [], [], tmp_path)
    assert all(p["commissioned"] == 2 and p["business_accepted"] == 0 and p["unverified_decisions"] == 2
               and p["recorded_cost_per_business_accepted_vnd"] is None for p in result["arms"].values())


def test_d_needs_distinct_reviewer_bound_to_retained_files(tmp_path):
    import hashlib
    from pilot import ROLES, RUBRIC, blank

    name = "service/P-x"
    folder = tmp_path / name
    folder.mkdir(parents=True)
    (folder / "first.artifact").write_bytes(b"before")
    (folder / "delivered.artifact").write_bytes(b"after")
    final = hashlib.sha256(b"after").hexdigest()
    design = {name: "ai_plus_independent_qa"}
    rows = [blank("P-x", "service") | {"role": role, "actor_code": role, "consent_and_permitted_inputs": True,
            "decision_reason": "synthetic regression", "reference_to_delivered_revision": "r2", "delivered_artifact_sha256": final,
            "first_pass_accepted": False, "business_accepted": True, "sales_usefulness_0_2": 2, "usable_after_editing": True,
            "allocated_cost_vnd": 20, "cost_source": "synthetic regression", "rubric": {key: {"score_0_2": 2, "evidence": "section one"} for key in RUBRIC}}
            for role in ROLES]
    rows[0]["overhead"].update(model_vnd=2, compute_vnd=3, tools_vnd=4, other_vnd=0, includes_failed_attempts=True, receipt_refs=["synthetic"])
    review = {"name": name, "actor_code": "fourth-person", "consent": True, "first_sha256": hashlib.sha256(b"before").hexdigest(),
              "final_sha256": final, "findings_or_no_change_reason": "fixture correction", "qa_seconds": 10, "labor_vnd": 5, "cost_ref": "fixture"}
    pending = study.score(design, rows, [], tmp_path)["packages"][name]
    assert pending["verified_business_decision"] is None and pending["recorded_labor_cost_per_business_accepted_vnd"] is None
    accepted = study.score(design, rows, [review], tmp_path)["packages"][name]
    assert accepted["all_in_cost_per_business_accepted_vnd"] == 74 and accepted["recorded_labor_cost_per_business_accepted_vnd"] == 65
    with pytest.raises(ValueError, match="separate"):
        study.score(design, rows, [review | {"actor_code": "independent_reviewer"}], tmp_path)
    (folder / "first.artifact").write_bytes(b"changed")
    assert not study.score(design, rows, [review], tmp_path)["packages"][name]["preqa_verified"]
