"""The custodian keeps treatment identities separate; blank observations produce no acceptance denominator."""

import importlib.util
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

SCRIPT = Path(__file__).parent / "evaluation/department/pilot.py"
SPEC = importlib.util.spec_from_file_location("department_pilot", SCRIPT)
PILOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PILOT)


def test_packets_separate_labels_and_refuse_shared_reviewer_identity(tmp_path):
    corpus = json.loads((PILOT.ROOT / "tests/evaluation/department/briefs-v1.json").read_text(encoding="utf-8"))
    for case in corpus["cases"]:
        for arm in ("control", "qwen05", "qwen7", "qwen15"):
            path = tmp_path / case["id"] / arm
            path.mkdir(parents=True)
            for stage in ("first", "reviewed"):
                (path / (stage + "-package.json")).write_text(
                    json.dumps({"strategy": {"decision": "Synthetic sample"}, "channel_status": arm}), encoding="utf-8"
                )
    output = tmp_path / "pilot"
    PILOT.pack(tmp_path, output)
    key = PILOT.read(output / "custodian.json")
    assert len(key) == 10 and set(key.values()) == {"manual", "control", "qwen05", "qwen7", "qwen15"}
    with ZipFile(output / "02-candidates.zip") as blind:
        assert "custodian.json" not in blind.namelist()
        assert len(blind.read("ORDER.txt").decode().splitlines()) == 8
        assert all("qwen" not in blind.read(name).decode().lower() for name in blind.namelist() if name.endswith(("first.md", "reviewed.md")))
    for zipname in ("01-manual.zip", "02-candidates.zip"):
        with ZipFile(output / zipname) as packet:
            for name in packet.namelist():
                if "/observation-" in name:
                    assert json.loads(packet.read(name))["delivered_artifact_sha256"] is None
    assert all(not x["observations"] and x["recorded_labor_cost_per_business_accepted_vnd"] is None for x in PILOT.check(key, []).values())
    brief, alias = next(iter(key)).split("/")
    form = PILOT.blank(alias, brief)
    form.update(
        role="marketer",
        actor_code="fixture-role",
        consent_and_permitted_inputs=True,
        decision_reason="Synthetic check",
        reference_to_delivered_revision="fixture",
        usable_after_editing=True,
    )
    with pytest.raises(ValueError, match="independent"):
        PILOT.check(key, [form, dict(form, role="independent_reviewer")])


def test_cost_includes_rejected_work_and_unknowns_stay_open():
    rows = {
        "p1": {"arm": "control", "recorded_total_vnd": 100, "verified_business_decision": True},
        "p2": {"arm": "control", "recorded_total_vnd": 40, "verified_business_decision": False},
    }
    assert PILOT.by_arm(rows)["control"]["recorded_cost_per_business_accepted_vnd"] == 140
    rows["p2"]["recorded_total_vnd"] = None
    assert PILOT.by_arm(rows)["control"]["recorded_cost_per_business_accepted_vnd"] is None
    rows["p2"]["recorded_total_vnd"] = 40
    rows["p2"]["verified_business_decision"] = None
    assert PILOT.by_arm(rows)["control"]["recorded_cost_per_business_accepted_vnd"] is None
    rows["p2"]["verified_business_decision"] = False
    rows["p1"]["verified_business_decision"] = False
    assert PILOT.by_arm(rows)["control"]["recorded_cost_per_business_accepted_vnd"] is None


def test_reconcile_three_roles_and_retained_source_bytes(tmp_path):
    name = "service/P-test"
    key = {name: "control"}
    artifact = tmp_path / name / "delivered.artifact"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes("Đã sửa tại revision 2.\r\n".encode())
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    forms = [
        PILOT.blank("P-test", "service") | dict(
            role=role, actor_code=role, consent_and_permitted_inputs=True, decision_reason="Fixture",
            reference_to_delivered_revision="edition-2", delivered_artifact_sha256=digest,
            first_pass_accepted=False, usable_after_editing=True, business_accepted=True, sales_usefulness_0_2=2,
            rubric={k: {"score_0_2": 1, "evidence": "fixture section"} for k in PILOT.RUBRIC},
        ) for role in PILOT.ROLES
    ]

    def result(rows):
        return PILOT.check(key, rows, tmp_path)[name]

    assert result(forms)["verified_business_decision"] is True
    assert result(forms)["artifact_verification"]["retained_sha256"] == digest
    assert result(forms[:-1])["artifact_verification"]["status"] == "missing_roles"
    legacy = [dict(form) for form in forms]
    for form in legacy:
        del form["delivered_artifact_sha256"]
    for old in (legacy, [legacy[0], *forms[1:]]):
        entry = result(old)
        assert entry["observations"]["sales_or_owner"]["business_accepted"] is True
        assert entry["artifact_verification"]["status"] == "missing_declared_digest"
        assert entry["verified_business_decision"] is None
        assert PILOT.by_arm({name: entry})["control"]["business_accepted"] == 0
    for edit in ({"reference_to_delivered_revision": "edition-1"}, {"delivered_artifact_sha256": "f" * 64}):
        entry = result([forms[0] | edit, *forms[1:]])
        assert entry["artifact_verification"]["status"] == "different_submitted_revisions"
        assert entry["verified_business_decision"] is None
    with pytest.raises(ValueError, match="SHA-256"):
        result([forms[0] | {"delivered_artifact_sha256": "not-a-hash"}, *forms[1:]])
    assert PILOT.check(key, forms)[name]["artifact_verification"]["status"] == "artifact_unavailable"
    artifact.write_bytes(b"changed after review")
    assert result(forms)["artifact_verification"]["status"] == "artifact_mismatch"
    artifact.unlink()
    assert result(forms)["artifact_verification"]["status"] == "artifact_unavailable"
