"""Verify release-specific, SHA-bound technical smoke receipts in a CI artifact."""
import argparse
import json
from pathlib import Path
import re

REQUIRED = {"WF-03/research-strategy-draft@2", "WF-13/landing-seo-draft@5"}
WEIGHTS = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"


def verify(folder, checkout):
    matched = {}
    for path in folder.rglob("*.json"):
        obj = json.loads(path.read_text(encoding="utf8"))
        if not isinstance(obj, dict) or obj.get("workflow") not in REQUIRED or obj.get("checkout") != checkout:
            continue
        release = obj["workflow"]
        doc = obj["deliverable"]
        assert obj["model_sha256"] == WEIGHTS and obj["binding"]["workflow"] == release
        for digest in (obj["runtime_fingerprint"], obj["manifest"]["digest"], obj["binding"]["manifest_digest"], doc["digest"]):
            assert re.fullmatch(r"[0-9a-f]{64}", digest)
        stages = {"director", "research", "strategy"} if release.startswith("WF-03/") else {"director", "content", "seo"}
        assert {entry["schema"].removeprefix("c3_") for entry in obj["attempts"] if "raw_output" in entry} == stages, obj["attempts"]
        assert len({entry["attempt_id"] for entry in obj["attempts"]}) == len(obj["attempts"])
        assert all(entry["input_tokens"] > 0 and entry["output_tokens"] > 0 for entry in obj["attempts"] if "raw_output" in entry)
        assert doc["id"] and doc["qa_revision"] >= 1 and obj["run_id"] and obj["journal"]
        assert doc["status"] in {"draft", "submitted"}
        assessment = doc["assessment"]["content_evidence"]
        assert assessment["qa_revision"] == doc["qa_revision"] and assessment["content_digest"] == doc["digest"] and assessment["statements"]
        edit = obj["edited_example"]
        assert edit["id"] == doc["id"] and edit["status"] == "draft"
        assert edit["qa_revision"] == doc["qa_revision"] + 1
        evidence = edit["qa_evidence"]["content_evidence"]
        assert evidence["qa_revision"] == edit["qa_revision"] and evidence["content_digest"] != doc["digest"]
        assert evidence["content_digest"] == edit["qa_evidence"]["content_digest"]
        assert release not in matched
        matched[release] = doc["id"]
    if matched.keys() != REQUIRED:
        raise ValueError(f"Missing exact release receipts on {checkout}: {sorted(REQUIRED - matched.keys())}")
    return matched


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("checkout")
    args = parser.parse_args()
    print(verify(args.folder, args.checkout))
