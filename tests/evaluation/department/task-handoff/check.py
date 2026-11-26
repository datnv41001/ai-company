"""Replay O-09 diagnostics and source-aware synthetic fixtures. No provider or database access."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import zipfile

from clarification import draft, project, resolve, route, verify

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "handoff-v2"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def archived():
    path = OLD / "FIRST-RUN.zip"
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != "743453b38d7738aca5931494cf1d204a3c610e7c5ce5af297538013a9bba51a3":
        raise ValueError("Historical first-run archive changed")
    with zipfile.ZipFile(path) as archive:
        answers = {row["id"]: row for row in json.loads(archive.read("qwen.json"))}
    gold = {row["id"]: row for row in load(OLD / "gold.json")}
    scores = load(OLD / "metrics.json")
    rows = {row["id"]: row for row in scores["qwen"]["cases"]}
    assert len(rows) == 24 and set(rows) == set(gold) == set(answers)
    counts = {}
    for decision in ("ask", "ready", "clarify_policy"):
        ids = [i for i in gold if gold[i]["expected"] == decision]
        counts[decision] = {"n": len(ids), "raw_type": sum(answers[i]["decision"] == decision for i in ids),
                            "full": sum(rows[i]["exact"] for i in ids)}
    readers = load(OLD / "blind-read/summary.json")["readers"]
    return {"archive_sha256": digest, "control_exact": scores["control"]["total"]["exact"],
            "rules_exact": scores["rules"]["total"]["exact"], "qwen_by_gold": counts,
            "raw_type_only": sum(c["raw_type"] for c in counts.values()), "full_contract": scores["qwen"]["total"]["exact"],
            "invalid_contract": sum(not x["valid"] for x in rows.values()),
            "additional_asks_passing_all_per_reader": [r["arms"]["qwen"]["additional_correct_asks_passing_all"] for r in readers]}


def source_case(fixtures, spec):
    field = spec["field"]
    scope = fixtures["scope"]
    return {"id": spec["id"], "scope": scope, "locale": spec["locale"], "current_policy_revision": 4,
            "as_of": fixtures["as_of"],
            "policy": dict(fixtures["policies"][field], field=field, approved=True, revision=4,
                           since="2026-11-01", until="2026-11-30", scope=scope, ref=field+"-policy/r4"),
            "crm": {"ref": spec["id"]+"/crm/r1", "scope": scope, "value": spec["old"],
                    "recorded_at": "2026-11-24", "valid_until": spec.get("expiry", "2026-11-30")},
            "buyer": {"ref": spec["id"]+"/message/r1", "scope": scope, "text": spec["message"],
                      "recorded_at": spec.get("when", "2026-11-26")}}


def regressions():
    fixtures = load(HERE / "source-cases.json")
    traces = {}
    for row in fixtures["scenarios"]:
        case = source_case(fixtures, row)
        original = deepcopy(case)
        projection = project(case)
        fact = resolve(case, projection)
        decision, recipient, _ = route(case["policy"], fact)
        trace = verify(case, draft(case, decision))
        expected = row["expected"]
        assert (decision, fact["current"], fact["status"]) == (expected["decision"], expected["current"], expected["status"])
        assert case == original and trace["confirmation"] == "human_review_required" and trace["recipient"] == recipient
        traces[row["id"]] = trace
    return traces


def rejected(call):
    try:
        call()
    except ValueError:
        return True
    raise AssertionError("Expected an invalid projection or proposal to be rejected")


def guard_checks():
    fixtures = load(HERE / "source-cases.json")
    sample = source_case(fixtures, next(x for x in fixtures["scenarios"] if x["id"] == "withdraw-existing"))
    guards = {}
    for name, target, key, value in [
        ("foreign_policy", "policy", "scope", "other"), ("foreign_crm", "crm", "scope", "other"),
        ("foreign_message", "buyer", "scope", "other"), ("stale_policy", "policy", "revision", 3),
        ("unapproved_policy", "policy", "approved", False), ("expired_policy", "policy", "until", "2026-11-25"),
        ("missing_record_ref", "buyer", "ref", ""),
    ]:
        changed = deepcopy(sample)
        changed[target][key] = value
        guards[name] = rejected(lambda: project(changed))
    guards["well_shaped_false_ready"] = rejected(lambda: verify(sample, draft(sample, "ready")))
    irrelevant = dict(draft(sample, "ask"), field="shoe", question="What is your shoe size?")
    guards["well_shaped_irrelevant_ask"] = rejected(lambda: verify(sample, irrelevant))
    return guards


def replay():
    return {"historical": archived(), "fixture_traces": regressions(), "guard_checks": guard_checks()}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, help="Exclusive-create a new JSON receipt")
    args = p.parse_args()
    result = json.dumps(replay(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as out:
            out.write(result)
    else:
        print(result)
