"""Score locked decisions against the independent labels and verify archived raw invocations."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from advisory_study import DATA, MODEL, TASKS, output, read

LABELS = ("supported", "contradicted", "unknown")


def rate(num, den):
    return {"numerator": num, "denominator": den, "rate": round(num / den, 4) if den else None}


def metrics(pairs):
    counts = Counter(pairs)
    total = sum(counts.values())
    bad = sum(counts["contradicted", v] for v in LABELS)
    good = sum(counts["supported", v] for v in LABELS)
    tp = counts["contradicted", "contradicted"]
    fp = counts["supported", "contradicted"] + counts["unknown", "contradicted"]
    return {
        "matrix_gold_then_prediction": {g: {p: counts[g, p] for p in LABELS} for g in LABELS},
        "recall": rate(tp, bad), "false_negative_rate_including_abstentions": rate(bad - tp, bad),
        "false_positive_rate": rate(fp, total - bad), "false_contradiction_on_supported": rate(counts["supported", "contradicted"], good),
        "precision": rate(tp, tp + fp), "abstention": rate(sum(counts[g, "unknown"] for g in LABELS), total),
        "contradictions_called_supported": counts["contradicted", "supported"],
        "unknowns_called_supported": counts["unknown", "supported"],
    }


def evaluate(archives):
    by_group = {}
    usage = {}
    with ZipFile(archives) as z:
        host = json.loads(z.read("host.json"))
        assert host["weights"] == MODEL
        def receipt(key, group):
            obj = json.loads(z.read("receipts/" + key + ".json"))
            assert obj["weights"] == MODEL and obj["response"]["choices"] and obj["request"]["model"] == "amc-local"
            assert obj["request"]["seed"] == 42 and obj["request"]["temperature"] == 0
            totals = usage.setdefault(group, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "wall_seconds": 0, "length_stops": 0})
            totals["calls"] += 1
            for k in ("prompt_tokens", "completion_tokens"):
                totals[k] += obj["response"]["usage"][k]
            totals["wall_seconds"] = round(totals["wall_seconds"] + obj["wall_seconds"], 4)
            totals["length_stops"] += obj["response"]["choices"][0]["finish_reason"] == "length"
            return obj
        for split in ("inputs", "stress-inputs"):
            sources = {r["id"]: r for r in read(DATA / (split + ".json"))}
            labels_file = "labels.json" if split == "inputs" else "stress-labels.json"
            truth = {r["id"]: r["label"] for r in read(DATA / labels_file)}
            preds = json.loads(z.read(split + "-predictions.json"))
            assert set(sources) == set(truth) == {r["id"] for r in preds} and len(preds) == len(truth)
            slices = {}
            for row in preds:
                i = sources[row["id"]]
                call = receipt(i["id"], split)
                assert json.loads(call["request"]["messages"][1]["content"]) == {k: i[k] for k in ("source", "claim")}
                try:
                    raw = json.loads(call["response"]["choices"][0]["message"]["content"])
                except ValueError:
                    raw = {}
                quote = raw.get("quote") or ""
                assert row["advice"] == (raw.get("verdict") if quote.strip() and quote in i["source"] else "unknown")
                base = row["control"]["label"]
                assert row["combined"] == (row["advice"] if base == "unknown" else base)
                for name in ("all", "language/" + i["lang"], "category/" + i["category"]):
                    group = slices.setdefault(name, {"baseline": [], "combined_advisory": [], "model_alone": []})
                    for arm, value in (("baseline", base), ("combined_advisory", row["combined"]), ("model_alone", row["advice"])):
                        group[arm].append((truth[i["id"]], value))
            by_group[split] = {name: {arm: metrics(pairs) for arm, pairs in arms.items()} for name, arms in slices.items()}
        for brief in read(DATA / "briefs.json"):
            work = json.loads(z.read(brief["id"] + "-work.json"))
            assert set(work) == set(TASKS)
            for role, values in work.items():
                obj = receipt(brief["id"] + "-" + role, "specialists")
                prompt = json.loads(obj["request"]["messages"][1]["content"])
                assert prompt["brief"] == brief and prompt["draft"] == values["baseline"]
                assert values["proposed_revision"] == obj["response"]["choices"][0]["message"]["content"]
        assert sum(r["calls"] for r in usage.values()) == len([n for n in z.namelist() if n.startswith("receipts/")])
    return {"archive_sha256": hashlib.sha256(archives.read_bytes()).hexdigest(), "usage": usage,
            "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob("*.json"))},
            "measured_host": host, "slices": by_group}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    output(args.out, evaluate(args.archive))
