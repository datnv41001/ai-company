"""Compare two measured runs for cases 01 and 02 of each frozen persona."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from statistics import median

from summarize_qualification import HOLDOUT, WEIGHTS, audit, require


def measured_outputs(row):
    # Keep the last successful output per specialist; compare retries separately.
    return {a["schema"]: a for a in row["attempts"] if "raw_output" in a}


def values(stages):
    return {(role, field): value for role, attempt in stages.items()
            for field, value in attempt["raw_output"].items() if field != "source_ids"}


def compare_repeats(first, second):
    for key in ("case", "workflow", "arm", "checkout", "build", "cases_sha256", "model_sha256", "provider"):
        require(first[key] == second[key], f"Different {key} for {first['case']}")
    a_ids = {a["attempt_id"] for a in first["attempts"]}
    b_ids = {a["attempt_id"] for a in second["attempts"]}
    require(a_ids.isdisjoint(b_ids), f"Repeated invocation IDs for {first['case']}")
    result = {"case":first["case"], "state":[first["state"], second["state"]],
              "attempt_counts":[len(first["attempts"]), len(second["attempts"])]}
    if a_ids and b_ids:
        require(first["run_id"] != second["run_id"], f"Same run ID in purported repeat {first['case']}")
        result["measurements"] = {}
        for key in ("runtime_s", "input_tokens", "output_tokens"):
            pair = [first[key], second[key]]
            result["measurements"][key] = {"pair":pair, "absolute_delta":round(abs(pair[1]-pair[0]), 3)}
    if not (first.get("deliverable") and second.get("deliverable")):
        return result
    require(first["deliverable"]["id"] != second["deliverable"]["id"], f"Same deliverable ID for {first['case']}")
    require(first["runtime_fingerprint"] == second["runtime_fingerprint"], "Different runtime fingerprints")
    stages_a, stages_b = measured_outputs(first), measured_outputs(second)
    fields_a, fields_b = values(stages_a), values(stages_b)
    paths = sorted(fields_a.keys() | fields_b.keys())
    different = [".".join(k) for k in paths if fields_a.get(k) != fields_b.get(k)]
    same_requests = set(stages_a) == set(stages_b) and all(stages_a[k]["request_sha256"] == stages_b[k]["request_sha256"] for k in stages_a)
    result.update(rendered_title_body_identical=first["deliverable"]["digest"] == second["deliverable"]["digest"],
                  successful_stage_requests_identical=same_requests, specialist_and_director_fields=len(paths),
                  changed_raw_fields_excluding_handles=different)
    return result


def arm_repeat(first, second, name, cases, checkout):
    first_folder, second_folder = first / name, second / name
    # Both bundles must be authentic, internally consistent and contain single-SHA data.
    for folder in (first_folder, second_folder):
        audited = audit(folder, cases, name)
        require(audited["checkout_and_arm"] == [(checkout, name)], f"Receipt checkout differs from conditions in {folder}")
    keys = sorted(key for key in cases if key.endswith(("-01", "-02")))
    require(len(keys) == 10, "Expected ten preregistered cases")
    require({p.parent.name for p in second_folder.glob("*/result.json")} == set(keys), "Repeat must include exactly the ten preregistered cases")
    pairs = [compare_repeats(*[json.loads((folder / key / "result.json").read_text(encoding="utf8"))
                               for folder in (first_folder, second_folder)]) for key in keys]
    measured = [p for p in pairs if "measurements" in p]
    drafts = [p for p in pairs if "rendered_title_body_identical" in p]
    absolute_deltas = {}
    for metric in ("runtime_s", "input_tokens", "output_tokens"):
        deltas = [p["measurements"][metric]["absolute_delta"] for p in measured]
        absolute_deltas[metric] = {"n":len(deltas), "median":median(deltas), "max":max(deltas)} if deltas else None
    return {"assigned":len(keys), "paired_drafts":len(drafts),
            "state_pairs":dict(Counter(" -> ".join(p["state"]) for p in pairs)),
            "rendered_title_body_identical":sum(p["rendered_title_body_identical"] for p in drafts),
            "all_text_fields_identical":sum(not p["changed_raw_fields_excluding_handles"] for p in drafts),
            "identical_stage_requests":sum(p["successful_stage_requests_identical"] for p in drafts),
            "raw_fields_changed":sum(len(p["changed_raw_fields_excluding_handles"]) for p in drafts),
            "raw_fields_compared":sum(p["specialist_and_director_fields"] for p in drafts),
            "within_brief_absolute_delta":absolute_deltas, "pairs":pairs}


def memory_observation(samples, process):
    rows = [json.loads(line) for line in samples.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    meta = json.loads(process.read_text(encoding="utf-8-sig"))
    require(meta["ProcessName"] == "llama-server" and isinstance(meta["Id"], int), "Unexpected model process")
    require(bool(rows), "Empty memory sample file")
    moments = [datetime.fromisoformat(r["measured_utc"]) for r in rows]
    require(moments == sorted(moments) and all(m.utcoffset() is not None for m in moments), "Unexpected sample order or timezone")
    for row in rows:
        require(0 < row["resident_bytes"] <= row["process_lifetime_peak_bytes"], "Invalid working-set sample")
    gaps = [(b-a).total_seconds() for a,b in zip(moments, moments[1:])]
    return {"sampler_process_id":meta["Id"], "samples":len(rows), "first_utc":rows[0]["measured_utc"], "last_utc":rows[-1]["measured_utc"],
            "median_sample_gap_s":round(median(gaps),3) if gaps else None, "longest_sample_gap_s":round(max(gaps),3) if gaps else None,
            "highest_sampled_resident_bytes":max(r["resident_bytes"] for r in rows),
            "highest_reported_process_lifetime_peak_bytes":max(r["process_lifetime_peak_bytes"] for r in rows),
            "scope":"whole sampled process across tasks; lifetime peak can predate sampling"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first",type=Path)
    parser.add_argument("repeat",type=Path)
    parser.add_argument("--cases",type=Path,default=Path(__file__).with_name("holdout-v1.json"))
    parser.add_argument("--memory",type=Path)
    parser.add_argument("--process",type=Path)
    parser.add_argument("--out",type=Path)
    args = parser.parse_args()
    require(hashlib.sha256(args.cases.read_bytes()).hexdigest() == HOLDOUT, "Holdout changed")
    cases = {c["id"]:c for c in json.loads(args.cases.read_text(encoding="utf8"))["cases"]}
    first_meta, repeated_meta = [json.loads((p/"conditions.json").read_text(encoding="utf8")) for p in (args.first, args.repeat)]
    require(first_meta == repeated_meta and first_meta["cases_sha256"] == HOLDOUT and first_meta["model_sha256"] == WEIGHTS,
            "Runtime, model or data changed")
    result = {"schema":"c3-holdout-repeat/v1", "conditions":first_meta,
              "arms":{name:arm_repeat(args.first,args.repeat,name,cases,first_meta["checkout"]) for name in ("projected","improved")}}
    require(bool(args.memory) == bool(args.process), "Provide both the NDJSON samples and the process metadata")
    if args.memory:
        result["model_memory"] = memory_observation(args.memory,args.process)
    encoded = json.dumps(result,ensure_ascii=False,indent=2)
    if args.out:
        args.out.write_text(encoded+"\n",encoding="utf8")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
