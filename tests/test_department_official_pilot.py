"""Synthetic private commissions. No stored actor, key, real outcome or production interaction."""

from copy import deepcopy
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).parent / "evaluation/department"))
import official_pilot as study  # noqa: E402
from pilot import ROLES, RUBRIC, blank  # noqa: E402


def issue(tmp):
    materials = tmp / "materials"
    materials.mkdir()
    vault = tmp / "custody"
    roster = {}
    for journey in study.JOURNEYS:
        directory = materials / journey
        directory.mkdir()
        for filename in ("brief", "ai", "control"):
            (directory / (filename + ".md")).write_text(f"Authorized synthetic {journey} document variant {len(filename)}.", encoding="utf-8")
        roster[journey] = {
            arm: {role: "participant-" + str(list((*ROLES, "production_qa")).index(role)) for role in study.roles_for(arm)} for arm in study.ARMS
        }
    (materials / "roster.json").write_text(json.dumps(roster))
    lock = study.issue(vault, materials)
    orders = study.load(vault, lock)["orders"]
    return vault, lock, orders


def marks():
    return {k: {"score_0_2": 1, "evidence": "Synthetic paragraph."} for k in RUBRIC}


def initial_decision(order, initial):
    return {
        "reference": initial,
        "actor_code": order["roles"]["independent_reviewer"],
        "accepted": False,
        "unblinded": False,
        "consent": True,
        "reason": "The synthetic CTA lacks the delivery area.",
        "rubric": marks(),
    }


def exercise(vault, lock, alias, order):
    folder = vault / alias
    path = vault.parent / "scratch.md"
    path.write_bytes(b"Synthetic manual draft" if order["arm"] == "manual" else (folder / "starting.md").read_bytes())
    initial = study.capture(vault, lock, alias, "initial", path)
    study.first_grade(vault, lock, alias, initial_decision(order, initial))
    path.write_text("Synthetic CTA with delivery area.", encoding="utf-8")
    edited = study.capture(vault, lock, alias, "edited", path)
    final = study.capture(vault, lock, alias, "delivered", path)
    forms = []
    for role in ROLES:
        form = blank("", "") | {
            "role": role,
            "actor_code": order["roles"][role],
            "reference": final,
            "unblinded": False,
            "consent_and_permitted_inputs": True,
            "decision_reason": "Synthetic final assessment.",
            "business_accepted": True,
            "allocated_cost_vnd": 10,
            "cost_source": "synthetic allocation",
            "usable_after_editing": True,
            "sales_usefulness_0_2": 2,
            "rubric": marks(),
        }
        if role == "marketer":
            form["overhead"].update(compute_vnd=1, model_vnd=0, tools_vnd=1, other_vnd=0, includes_failed_attempts=True, receipt_refs=["test-record"])
        forms.append(form)
    out = {
        "status": "completed",
        "observations": forms,
        "edited_decision": {"actor_code": order["roles"]["marketer"], "reference": edited, "decision": "submitted", "reason": "Checked buyer conditions"},
    }
    if order["arm"] == study.ARMS[-1]:
        out["production_qa"] = {
            "actor_code": order["roles"]["production_qa"],
            "input": edited,
            "output": final,
            "consent": True,
            "decision": "approved",
            "findings_or_no_change_reason": "Checked the revised area.",
            "qa_seconds": 10,
            "labor_vnd": 5,
            "cost_ref": "test basis",
        }
    return out


def dispositions(orders):
    return {alias: {"status": "pending", "reason": "Awaiting practitioner"} for alias in orders}


def test_fresh_independent_design_and_blind_packet(tmp_path):
    v, lock, orders = issue(tmp_path)
    v2 = tmp_path / "custody-2"
    orders2 = study.load(v2, study.issue(v2, tmp_path / "materials"))["orders"]
    assert len(orders) == 8 and not set(orders) & set(orders2)
    alias, order = next(iter(orders.items()))
    source = tmp_path / "source.md"
    source.write_bytes((v / alias / "starting.md").read_bytes() or b"QA synthetic proposal.")
    ref = study.capture(v, lock, alias, "initial", source)
    output = tmp_path / (ref["card"] + ".zip")
    study.packet(v, lock, alias, "initial", output)
    with ZipFile(output) as f:
        assert set(f.namelist()) == {"brief.md", "artifact.md", "rubric.md", "card.json", "scorecard.json"}
        assert json.loads(f.read("card.json")) == ref and f.read("artifact.md") == source.read_bytes()
        assert all(alias.encode() not in f.read(s) and b"participant-" not in f.read(s) for s in f.namelist())
    with pytest.raises(FileExistsError):
        study.packet(v, lock, alias, "initial", output)
    with pytest.raises(ValueError, match="Git checkouts"):
        study.issue(study.ROOT / "test-custody", tmp_path / "materials")
    require_lock = (v / "design.json").read_bytes()
    changed = json.loads(require_lock)
    changed["orders"].pop(alias)
    (v / "design.json").write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="escrowed"):
        study.load(v, lock)
    with pytest.raises(ValueError, match="eight"):
        study.load(v, study.sha((v / "design.json").read_bytes()))
    (v / "design.json").write_bytes(require_lock)
    subset = dispositions(orders)
    del subset[alias]
    with pytest.raises(ValueError, match="eight"):
        study.report(v, lock, subset)
    # A new alias cannot blind copies of publicly mapped exact starting drafts.
    with ZipFile(study.KIT.parent / "PILOT-ABCD/work-orders.zip") as public:
        starting = next(p for p in public.namelist() if p.endswith("/starting.md"))
        (tmp_path / "materials/rfq/ai.md").write_bytes(public.read(starting))
    with pytest.raises(ValueError, match="Public fixture|disclosure"):
        study.issue(tmp_path / "public-reissue", tmp_path / "materials")


def test_original_bytes_first_grade_and_separate_revision(tmp_path):
    v, lock, orders = issue(tmp_path)
    alias = next(k for k, o in orders.items() if o["arm"] == "control")
    order, source = orders[alias], tmp_path / "candidate.md"
    source.write_text("Different edited artifact")
    with pytest.raises(ValueError, match="commissioned unchanged"):
        study.capture(v, lock, alias, "initial", source)
    with pytest.raises(ValueError, match="Missing initial"):
        study.capture(v, lock, alias, "delivered", source)
    source.write_bytes((v / alias / "starting.md").read_bytes())
    ref = study.capture(v, lock, alias, "initial", source)
    with pytest.raises(ValueError, match="Seal the first-pass"):
        study.capture(v, lock, alias, "edited", source)
    form = initial_decision(order, ref)
    for error in ({"revision": 3}, {"card": order["cards"]["delivered"]}, {"sha256": "1" * 64}):
        with pytest.raises(ValueError, match="First-pass"):
            study.first_grade(v, lock, alias, form | {"reference": ref | error})
    study.first_grade(v, lock, alias, form)
    with pytest.raises(FileExistsError):
        study.first_grade(v, lock, alias, form | {"accepted": True})
    source.write_text("Changed after grading")
    with pytest.raises(ValueError, match="Missing edited"):
        study.capture(v, lock, alias, "delivered", source)
    (v / alias / "initial/artifact.md").write_text("Different retained bytes")
    with pytest.raises(ValueError, match="initial digest"):
        study.report(v, lock, dispositions(orders))
    (v / alias / "initial/artifact.md").unlink()
    with pytest.raises(ValueError, match="Missing initial"):
        study.report(v, lock, dispositions(orders))


def test_official_denominator_keeps_failure_rejection_missing_cost_and_exposure(tmp_path):
    v, lock, orders = issue(tmp_path)
    result = dispositions(orders)
    rejected, accepted = [k for k, o in orders.items() if o["arm"] == "control"]
    failed, survivor = [k for k, o in orders.items() if o["arm"] == "manual"]
    for k in (rejected, accepted, survivor):
        result[k] = exercise(v, lock, k, orders[k])
    result[rejected]["observations"][-1]["business_accepted"] = False
    result[failed] = {
        "status": "failed",
        "reason": "Producer withdrew before delivery",
        "cost": {**dict.fromkeys(study.COSTS, 0), "labor_vnd": 9, "receipt_refs": ["cost-register"], "includes_failed_attempts": True},
    }
    report = study.report(v, lock, result)
    assert report["commissioned"] == 8 and report["mode"] == "official_locked_design"
    assert report["arms"]["control"]["recorded_cost_per_business_accepted_vnd"] == 64
    assert report["arms"]["control"]["first_pass_accepted"] == 0
    assert report["arms"]["manual"]["recorded_cost_per_business_accepted_vnd"] == 41
    assert report["arms"]["ai_assisted"]["unverified_decisions"] == 2
    result[failed]["cost"]["model_vnd"] = None
    result[accepted]["observations"][0]["overhead"]["tools_vnd"] = None
    report = study.report(v, lock, result)
    assert all(report["arms"][arm]["recorded_cost_per_business_accepted_vnd"] is None for arm in ("manual", "control"))
    result[accepted]["observations"][-1]["unblinded"] = True
    report = study.report(v, lock, result)
    assert report["arms"]["control"]["business_accepted"] == 0 and report["arms"]["control"]["dispositions"]["unblinded"] == 1
    assert report["arms"]["control"]["first_pass_scored"] == 1


def test_d_requires_distinct_bound_edited_and_delivered_qa(tmp_path):
    v, lock, orders = issue(tmp_path)
    alias = next(k for k, o in orders.items() if o["arm"] == study.ARMS[-1])
    order = orders[alias]
    result = dispositions(orders)
    result[alias] = exercise(v, lock, alias, order)

    def check():
        return study.report(v, lock, result)["packages"][order["brief"] + "/" + alias]

    assert check()["preqa_verified"] and check()["recorded_total_vnd"] == 37
    original = result[alias].pop("production_qa")
    with pytest.raises(ValueError, match="independent production QA"):
        check()
    for change in ({"actor_code": order["roles"]["independent_reviewer"]}, {"input": original["output"]}, {"decision": "returned"}):
        result[alias]["production_qa"] = original | change
        with pytest.raises(ValueError, match="independent production QA"):
            check()
    result[alias]["production_qa"] = original
    result[alias]["observations"][1]["reference"] = original["input"]
    with pytest.raises(ValueError, match="Delivered observation"):
        check()
    overlap = deepcopy(study.read(v / "design.json"))
    overlap["orders"][alias]["roles"]["production_qa"] = order["roles"]["marketer"]
    with pytest.raises(ValueError, match="remain independent"):
        study.validate_design(overlap)
