"""Build or verify the portable AIRC-500 catalog. Standard library, no network."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COUNTS = {"PM": 50, "MK": 100, "SE": 70, "AI": 50, "SP": 50, "UX": 40,
          "QT": 40, "BF": 30, "LC": 20, "IO": 25, "ID": 15, "AR": 10}
# Capabilities resolve only through the broker. A source name is not a filesystem path.
TOOLS = {
    "charter": "read_excerpt", "journey": "read_trace", "marketing": "read_excerpt",
    "source": "read_blob", "test": "read_test_attestation", "registry": "read_blob",
    "workflow": "read_trace", "policy": "read_excerpt", "render": "read_render",
    "finance": "read_trace", "approved_reference": "read_excerpt", "sealed_case": "read_case",
}


def build(groups):
    if {g["id"]: g["count"] for g in groups} != COUNTS or len(groups) != len(COUNTS):
        raise ValueError("discipline allocation differs from charter")
    rows = []
    for g in groups:
        code = g["id"]
        subjects, lenses = g["subjects"], g["lenses"]
        if len(lenses) != 5 or len(subjects) * len(lenses) != COUNTS[code]:
            raise ValueError(f"bad allocation for {code}")
        # The broker withholds sealed_case until the blind barrier has closed.
        sources = list(dict.fromkeys([*g["sources"], "sealed_case"]))
        tools = sorted({TOOLS[s] for s in sources})
        for i, (topic, invariant, probe) in enumerate(subjects):
            for j, (role, method, artifact) in enumerate(lenses):
                rid = f"{code}-{i * len(lenses) + j + 1:03d}"
                rows.append({
                    "reviewer_id": rid, "discipline": g["name"],
                    "expertise": f"{topic} / {role}", "mission": f"{probe}, then {method}.",
                    "scope": {"topic": topic, "invariant": invariant,
                              "boundary": "assigned pinned artifacts and authorized synthetic fixtures"},
                    "rubric": [
                        {"points": 4, "criterion": invariant},
                        {"points": 3, "criterion": probe},
                        {"points": 3, "criterion": f"Use the {artifact} to {method}."},
                    ],
                    "tools": tools, "sources": sources,
                    "output": {"contract": "arbitration.v1" if code == "AR" else "review.v1",
                               "artifact_kind": artifact, "proof_obligation": f"{invariant}. {probe}.",
                               "required_method": method},
                })
    for field in ("reviewer_id", "expertise", "mission"):
        if len({r[field] for r in rows}) != 500:
            raise ValueError(f"duplicate {field}")
    return rows


def encoded_catalog():
    groups = json.loads((ROOT / "disciplines.json").read_text(encoding="utf-8"))
    return "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                   for r in build(groups)).encode("utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rebuild reviewers.jsonl")
    args = parser.parse_args()
    data = encoded_catalog()
    target = ROOT / "reviewers.jsonl"
    if args.write:
        target.write_bytes(data)
    # Git on Windows may present text with CRLF on checkout. Hash canonical LF bytes.
    if target.read_text(encoding="utf-8").encode("utf-8") != data:
        raise SystemExit("Catalog drift. Inspect disciplines.json and rebuild with --write.")
    from hashlib import sha256
    print("500 catalog entries, 12 disciplines; canonical SHA-256", sha256(data).hexdigest())
