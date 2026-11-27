"""Reconcile the locked reviewer scores and released first-call journal. Offline only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

import rs01_verify
from rs01_pack import DIMENSIONS, FLAGS
from rs01_study import DOC, MODEL, ROLES, ROOT, encoded

SCORE_HASH = "da97785dc1bc9850021b35c9ea101267db7c8c53c6cf4276cced66517da54bec"
PREREG = "47b7b9633e44e5d25162fa560b366ab8cfaaeb72"
SCORE_COMMIT = "2dca5fcc0470bd25ed9e17d581df34d3ea5ee400"
BLIND_CANDIDATE = "ef158fac6ea634c7f415fd3a608cbce0e100db9a"


def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory=" + ROOT.as_posix(), *args], cwd=ROOT)


def read(path):
    return json.loads(path.read_bytes())


def verified_scores():
    path = DOC / "AMC-AI-RS-01-SCORES-LOCKED.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SCORE_HASH
    scores = read(path)
    assert scores["reviewer_session"] == "AMC-AI-RS-01-BLIND-REVIEW-20261127-01"
    return scores


def aggregate(scores, mapping):
    pairs = []
    totals = {arm: Counter() for arm in "AB"}
    breakdown = {arm: Counter() for arm in "AB"}
    hard = {arm: Counter() for arm in "AB"}
    ids = [pair["case"] for pair in scores["pairs"]]
    assert len(ids) == 4 and set(ids) == set(mapping)
    for pair in scores["pairs"]:
        case = pair["case"]
        left = mapping[case]
        labels = {"Left": left, "Right": "B" if left == "A" else "A"}
        assert set(pair["sides"]) == set(labels)
        row = {"case": case, "labels": labels, "arms": {}}
        for side, values in pair["sides"].items():
            arm = labels[side]
            assert values["rateable"] is True
            assert set(values["scores"]) == set(DIMENSIONS)
            points = {d: values["scores"][d]["score"] for d in DIMENSIONS}
            assert all(type(n) is int and n in (0, 1, 2) for n in points.values())
            fields = [e["field"] for e in values["meaningful_edits"]]
            assert len(fields) == len(set(fields))
            flags = values["hard_failures"]
            assert set(flags) == set(FLAGS) and all(type(f) is bool for f in flags.values())
            unsupported = len(values["unsupported_claims"])
            counts = dict(score=sum(points.values()), edits=len(fields), unsupported_entries=unsupported,
                          dossiers_with_unsupported=int(unsupported > 0))
            totals[arm].update(counts)
            hard[arm].update({flag: int(value) for flag, value in flags.items()})
            breakdown[arm].update(points)
            row["arms"][arm] = dict(**counts, criteria=points, edited_fields=fields, hard_failures=flags)
        pairs.append(row)

    def outcomes(key, direction):
        diffs = [direction * (p["arms"]["B"][key] - p["arms"]["A"][key]) for p in pairs]
        return dict(wins=sum(i > 0 for i in diffs), ties=diffs.count(0), losses=sum(i < 0 for i in diffs))

    edits = outcomes("edits", -1)
    gates = dict(fewer_edits_in_three_pairs=edits["wins"] >= 3,
                 no_increase_in_contradicted_claim_flags=hard["B"]["contradicted_source"] <= hard["A"]["contradicted_source"],
                 no_lost_constraint_in_B=hard["B"]["lost_constraint"] == 0)
    return dict(pairs=pairs, arm_totals=totals, criterion_totals=breakdown, hard_failure_dossier_counts=hard,
                B_vs_A=dict(meaningful_edits=edits, rubric_score=outcomes("score", 1)), gates=gates,
                threshold_met=all(gates.values()))


def reconcile():
    scores = verified_scores()  # The raw score lock precedes reading the mapping.
    assert git("rev-parse", SCORE_COMMIT + "^").decode().strip() == BLIND_CANDIDATE
    assert git("rev-parse", BLIND_CANDIDATE + "^").decode().strip() == PREREG
    manifest = read(DOC/"MANIFEST.json")
    for item in manifest["files"]:
        data = git("show", BLIND_CANDIDATE + ":" + item["path"])
        assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
    lock, summary = read(DOC/"LOCK.json"), read(DOC/"RESULTS.json")
    archive = DOC/"ordered-evidence.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == summary["ordered_evidence_plaintext_sha256"]
    expected = {"journal.json", "started.json", "mapping.json"} | {
        f"call-{i:02}.{suffix}" for i in range(1, 25) for suffix in ("intent", "raw", "json")}
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(archive) as z:
        assert set(z.namelist()) == expected and len(z.namelist()) == len(expected) and z.testzip() is None
        mapping = json.loads(z.read("mapping.json"))
        commitment = hashlib.sha256(encoded(mapping)).hexdigest()
        assert commitment == lock["mapping_commitment"] == summary["mapping_commitment"]
        z.extractall(tmp)
        rs01_verify.main(Path(tmp))  # request replay, first output equality, blind pack digests
        result = aggregate(scores, {p["id"]: p["left"] for p in mapping["pairs"]})
        journal = json.loads(z.read("journal.json"))
        assert journal["checkout"] == json.loads(z.read("started.json"))["checkout"] == PREREG
        assert lock["machine"]["model_sha256"] == MODEL == summary["model_sha256"]
        order = [(p["id"], arm, role) for p in mapping["pairs"]
                 for arm in (p["first"], "B" if p["first"] == "A" else "A") for role in ROLES]
        assert Counter(p["first"] for p in mapping["pairs"]) == {"A": 2, "B": 2}
        calls = journal["calls"]
        assert [(c["case"], c["arm"], c["role"]) for c in calls] == order
        last = 0
        in_tokens, out_tokens = [], []
        for i, c in enumerate(calls, 1):
            assert json.loads(z.read(f"call-{i:02}.json")) == c
            intent = json.loads(z.read(f"call-{i:02}.intent"))
            raw = json.loads(z.read(f"call-{i:02}.raw"))
            assert all(c[k] == v for stage in (intent, raw) for k, v in stage.items())
            u = json.loads(c["response_text"])
            assert u["model"] == c["request"]["model"] == "amc-local"
            assert c["request"]["seed"] == lock["seed"] == 42 and c["request"]["temperature"] == lock["temperature"] == 0
            assert c["http_status"] == 200 and c["finish"] == u["choices"][0]["finish_reason"] == "stop" and "error" not in c
            assert last <= c["elapsed_start"] <= c["elapsed_end"] <= journal["wall_seconds"]
            last = c["elapsed_end"]
            n_in, n_out = u["usage"]["prompt_tokens"], u["usage"]["completion_tokens"]
            assert n_in == c["input_preflight"] == c["input_tokens"] and 0 < n_in <= lock["input_cap"]
            assert 0 < n_out == c["output_tokens"] <= c["request"]["max_tokens"] == lock["output_cap"]
            assert n_in + lock["output_cap"] <= lock["machine"]["context"]
            in_tokens.append(n_in)
            out_tokens.append(n_out)
        assert sum(in_tokens) == journal["input_tokens"] == summary["input_tokens"] <= lock["input_total"]
        assert sum(out_tokens) == journal["output_tokens"] == summary["output_tokens"] <= lock["output_total"]
        assert journal["wall_seconds"] == summary["wall_seconds"] <= lock["seconds"]
        assert len(calls) == len(set(order)) == lock["calls"] and journal["stop"] is None
        telemetry = dict(calls=len(calls), incomplete_chains=0, retries=0,
                         input_range=[min(in_tokens), max(in_tokens)], output_range=[min(out_tokens), max(out_tokens)],
                         input_tokens=sum(in_tokens), output_tokens=sum(out_tokens), last_response_seconds=last,
                         wall_seconds=journal["wall_seconds"], provider_fee_usd=summary["provider_fee_usd"],
                         hardware_energy_editor_cost=None, model_sha256=MODEL, temperature=0, seed=42)
    return dict(reviewer_session=scores["reviewer_session"], score_commit=SCORE_COMMIT, score_sha256=SCORE_HASH,
                experiment_checkout=PREREG, mapping_commitment=commitment, telemetry=telemetry, **result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    outcome = reconcile()
    target = DOC/"FINAL.json"
    if args.write:
        target.write_text(json.dumps(outcome, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    else:
        assert read(target) == outcome
        for item in read(DOC/"FINAL-MANIFEST.json")["files"]:
            data = git("show", "HEAD:" + item["path"])
            assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
    print(json.dumps({k:outcome[k] for k in ("arm_totals","criterion_totals","hard_failure_dossier_counts","B_vs_A","gates","telemetry")}, indent=2))
