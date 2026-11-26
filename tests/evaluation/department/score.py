"""Verify model receipts and summarize complete packages; practitioner scores are collected separately."""

import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def score(root):
    study = read(root / "study.json")
    totals = {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and (p / "control").exists()):
        controls = read(folder / "control" / "approved-inputs.json")
        projection = {k: v["projection"] for k, v in controls.items()}
        pin = hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        fixed = read(folder / "control" / "first-package.json")
        for arm in ["control", *study["models"]]:
            path = folder / arm
            first, final = [read(path / (stage + "-package.json")) for stage in ("first", "reviewed")]
            record = {
                "first_complete": all(k in first for k in ("strategy", "landing"))
                and all(first["assets"].get(k) for k in ("social", "ad", "creative_brief", "calendar")),
                "final_complete": all(k in final for k in ("strategy", "landing"))
                and all(final["assets"].get(k) for k in ("social", "ad", "creative_brief", "calendar")),
                "attempts": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "unmetered_attempts": 0,
                "signed_editions": 0,
                "failed_attempts": 0,
                "fields": {},
                "provider_fee_usd": 0,
                "hardware_cost_usd": None,
                "human_cost": None,
                "cost_per_business_accepted_unit": None,
            }
            totals[folder.name + "/" + arm] = record
            if arm == "control":
                assert first == final == fixed
                continue
            assert read(path / "commission.json")["manifest_projection_sha256"] == pin
            for kind in ("strategy", "landing"):
                worker = read(path / kind / "worker.json")
                requests = read(path / kind / "requests.json")
                for event in worker["attempts"]:
                    assert signature(requests[event["attempt_id"]]) == event["request_sha256"]
                    record["failed_attempts"] += int("error" in event)
                assert (
                    worker["manifest"] == {k: read(path / "commission.json")["manifests"][kind][k] for k in ("id", "digest")}
                    if worker.get("deliverable")
                    else True
                )
                record["attempts"] += len(worker["attempts"])
                for key in ("input_tokens", "output_tokens", "unmetered_attempts"):
                    record[key] += worker[key]
                decision = path / kind / "signed-synthetic-edition.json"
                if decision.exists():
                    approved = read(decision)
                    assert approved["groups"] == final[kind] and approved["snapshot"]["status"] == "approved"
                    record["signed_editions"] += 1
                if (path / kind / "editor-review.json").exists():
                    for field, trace in read(path / kind / "editor-review.json")["field_history"].items():
                        d = trace["decision"]
                        record["fields"][d] = record["fields"].get(d, 0) + 1
                        if d == "retained_model_verbatim":
                            source = next(e for e in worker["attempts"] if e["attempt_id"] == trace["attempt"])
                            group, key = field.split(".")
                            assert final[kind][group][key] == source["raw_output"][trace["worker_field"]] == trace["after"] != trace["control"]
            channel = read(path / "channel-attempt.json")
            assert signature(channel["request"]) == channel["request_sha256"]
            for key in ("input_tokens", "output_tokens"):
                record[key] += channel[key] or 0
            record["unmetered_attempts"] += int(channel["input_tokens"] is None)
            record["failed_attempts"] += int(channel["state"] != "returned")
            record["attempts"] += 1
            record["first_workflow_passes"] = sum(read(path / kind / "worker.json")["first_pass_runtime"] for kind in ("strategy", "landing"))
            record["channel_release_status"] = final["channel_status"]
            if channel["state"] == "returned":
                assert all(final["assets"][k] == channel["output"][k] for k in ("social", "ad"))
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    result = score(args.out)
    (args.out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
