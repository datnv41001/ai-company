"""Check first requests by role so weights and generated predecessor context stay separately identifiable."""

from hashlib import sha256
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def hash_json(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compare(root):
    arms = ("qwen05", "qwen7", "qwen15")
    rows = []
    for case in ("index-tray", "receipt-map"):
        for workflow in ("strategy", "landing", "channel"):
            bodies = {}
            releases = {}
            for arm in arms:
                folder = root / case / arm
                if workflow == "channel":
                    bodies[arm] = {"channel": read(folder / "channel-attempt.json")["request"]}
                    continue
                worker = read(folder / workflow / "worker.json")
                releases[arm] = {
                    "workflow": worker["workflow"],
                    "runtime": worker.get("runtime_fingerprint"),
                    "registry": hash_json(worker["binding"]) if worker.get("binding") else None,
                }
                events = worker["attempts"]
                requests = read(folder / workflow / "requests.json")
                initial = {}
                for event in events:
                    initial.setdefault(event["schema"], requests[event["attempt_id"]])
                bodies[arm] = initial
            for role in sorted(set().union(*(set(v) for v in bodies.values()))):
                row = {"case": case, "workflow": workflow, "role": role, "arms": {}}
                for arm in arms:
                    body = bodies[arm].get(role)
                    if body:
                        row["arms"][arm] = {
                            "initial_request": hash_json(body),
                            "system": hash_json(body["messages"][0]),
                            "user_context": hash_json(body["messages"][1]),
                            "schema": hash_json(body["response_format"]),
                            "settings": {k: body[k] for k in ("model", "temperature", "max_tokens")},
                        }
                for field in ("initial_request", "system", "user_context", "schema", "settings"):
                    row["identical_" + field] = len(row["arms"]) == len(arms) and len({hash_json(v[field]) for v in row["arms"].values()}) == 1
                if releases:
                    row["releases"] = releases
                    row["identical_release"] = len(releases) == len(arms) and len({hash_json(val) for val in releases.values()}) == 1
                rows.append(row)
    return rows


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    rows = compare(args.directory)
    (args.directory / "matching.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {f: sum(r["identical_" + f] for r in rows) for f in ("initial_request", "system", "user_context", "schema", "settings")}
            | {"comparisons": len(rows)}
        )
    )
