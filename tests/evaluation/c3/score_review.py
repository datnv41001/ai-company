"""Verify API digests and masked ratings, then join the two experimental arms."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import median


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def summarize(root):
    review = root / "review"
    key = load(review / "key.json")
    cases = load(Path(__file__).with_name("cases.json"))["cases"]
    expected = {(c["id"], workflow, arm) for c in cases for workflow in ("WF-03", "WF-13")
                for arm in ("legacy", "projected")}
    rows = []
    seen = set()
    for workflow in ("WF-03", "WF-13"):
        ratings = load(review / f"ratings-{workflow.lower().replace('-', '')}.json")
        for rating in ratings:
            pid = rating["id"]
            scores = rating["scores"]
            if pid in seen or len(scores) != 6 or any(type(v) is not int or v not in (0, 1) for v in scores):
                raise ValueError(f"Invalid or repeated rating {pid}")
            seen.add(pid)
            entry = key[pid]
            identity = entry["case"], workflow, entry["arm"]
            expected.remove(identity)
            packet = review / "packets" / (pid + ".md")
            if sha256(packet.read_bytes()).hexdigest() != entry["packet_sha256"]:
                raise ValueError(f"Packet changed after generation {pid}")
            record = load(root / entry["arm"] / entry["case"] / workflow / "result.json")
            if record["run_id"] != entry["run"] or not record["workflow"].startswith(workflow + "/"):
                raise ValueError(f"Mismatched run {pid}")
            draft = record.get("deliverable")
            if draft:
                canonical = json.dumps({"preview": draft["body"], "title": draft["title"]}, sort_keys=True,
                                       separators=(",", ":"), ensure_ascii=False)
                if sha256(canonical.encode()).hexdigest() != draft["digest"]:
                    raise ValueError(f"API digest mismatch {pid}")
            rows.append({"case": entry["case"], "workflow": workflow, "arm": entry["arm"], "packet": pid,
                         "run": entry["run"], "scores": scores, "observation": rating["observation"],
                         "digest": draft["digest"] if draft else None, **{k: record[k] for k in
                         ("state", "first_pass_runtime", "input_tokens", "output_tokens", "provider_fee_usd",
                          "runtime_s", "unmetered_attempts")}, "attempts": len(record["attempts"])})
    if expected or seen != set(key):
        raise ValueError("Incomplete comparison")
    result = {}
    for arm in ("legacy", "projected"):
        sample = [r for r in rows if r["arm"] == arm]
        result[arm] = {
            "criteria": [sum(r["scores"][i] for r in sample) for i in range(6)],
            "marketing_first_pass": sum(all(r["scores"]) for r in sample),
            "technical_first_pass": sum(r["first_pass_runtime"] for r in sample),
            "median_runtime_s": median(r["runtime_s"] for r in sample),
            **{k: sum(r[k] for r in sample) for k in ("input_tokens", "output_tokens", "provider_fee_usd",
                                                      "attempts", "unmetered_attempts")},
        }
    return {"arms": result, "rows": sorted(rows, key=lambda row: (row["case"], row["workflow"], row["arm"]))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    output = summarize(args.root)
    (args.root / "review" / "scores.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                                                       encoding="utf8")
    print(json.dumps(output["arms"], indent=2))
