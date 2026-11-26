"""The custodian keeps treatment identities separate; blank observations produce no acceptance denominator."""

import importlib.util
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
