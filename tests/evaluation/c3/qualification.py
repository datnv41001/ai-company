"""Exercise the real local provider via the restricted pool for CI smoke or frozen cases."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

import httpx
from run_comparison import CASES, MarketingLab, ROOT, app, dump, lab_client, run_one
from candidate_fixture import MissingSellingUnit
from verify_receipts import WEIGHTS, verify


def edit_example(lab, record):
    """Save a labelled fixture edit through the staff API and read back both revisions."""
    from app.c3_releases import fact_text
    base, admin, *_ = lab.cases[0]
    original = record["deliverable"]
    uri = base + "/deliverables/" + original["id"]
    knowledge = lab.owner.execute("select knowledge from workforce_runs where id=%s", (record["run_id"],)).fetchone()[0]
    projection = knowledge["c3_projection"]
    blocks = [fact_text(record["workflow"], fact, projection) for fact in projection["facts"]]
    preview = "\n\n".join([projection["product"], *blocks, lab.case["cta"]])
    lab.api.patch(uri + "/draft", headers=admin["headers"], json={"title":projection["product"], "client_preview":preview}).raise_for_status()
    res = lab.api.get(uri, headers=admin["headers"])
    res.raise_for_status()
    edited = res.json()
    assert edited["id"] == original["id"] and edited["qa_revision"] == original["qa_revision"] + 1
    assert edited["qa_evidence"]["content_digest"] != original["digest"] and edited["status"] == "draft"
    return {"kind":"scripted fixture editor; no practitioner time measured", "id":edited["id"],
            "qa_revision":edited["qa_revision"], "title":edited["title"], "body":edited["content"]["client_preview"],
            "status":edited["status"], "qa_evidence":edited["qa_evidence"]}


def conditions(cases):
    from app.database import engine
    url = os.environ["AMC_LOCAL_MODEL_URL"].rstrip("/")
    local = {"127.0.0.1", "localhost", "::1"}
    if engine.url.host not in local or not engine.url.database.startswith("amc_test") or urlsplit(url).hostname not in local or not url.endswith("/v1"):
        raise ValueError("Use a disposable loopback amc_test database and a loopback model.")
    with httpx.Client(trust_env=False) as client:
        res = client.get(url[:-3] + "/props")
        res.raise_for_status()
        props = res.json()
    with Path(os.environ.get("AMC_EVAL_MODEL_FILE", props["model_path"])).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert digest == WEIGHTS
    return {"checkout": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "provider": "llama.cpp loopback", "model_sha256": digest, "build": props.get("build_info"),
            "cases_sha256": hashlib.sha256(cases.read_bytes()).hexdigest(), "worker_concurrency": 1}, url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--holdout", type=Path)
    parser.add_argument("--arms", nargs="+", choices=["projected", "improved"], default=["projected"])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    path = args.holdout or CASES
    meta, url = conditions(path)
    args.out.mkdir(parents=True, exist_ok=True)
    conditions_file = args.out / "conditions.json"
    if conditions_file.exists() and json.loads(conditions_file.read_text()) != meta:
        raise ValueError("Different experimental conditions in this directory")
    dump(conditions_file, meta)
    cases = json.loads(path.read_text(encoding="utf8"))["cases"]
    if args.holdout:
        assert meta["cases_sha256"] == "c497ff707c986acaa3c48ba799ab1a378f194d3e7cd4262834d41a4aae0fe477"
        # Round-robin through personas from the frozen set to keep partial runs balanced.
        cases.sort(key=lambda case: (int(case["id"][-2:]), case["persona"]))
    else:
        cases = [dict(c, workflow={"materials": "WF-03", "service": "WF-13"}[c["id"]]) for c in cases if c["id"] in ("materials", "service")]
    for case in cases[:args.limit]:
        for arm in args.arms:
            folder = args.out / arm / case["id"]
            folder.mkdir(parents=True, exist_ok=True)
            result = folder / "result.json"
            if result.exists():
                continue
            with lab_client(app) as api:
                lab = MarketingLab(api, os.environ["AMC_MIGRATION_DSN"], case)
                try:
                    lab.config = replace(lab.config, model=os.getenv("AMC_WORKFORCE_MODEL", "amc-local"), url=url)
                    try:
                        record = run_one(lab, case["workflow"], arm, folder)
                    except MissingSellingUnit as exc:
                        if not args.holdout:
                            raise
                        record = {"case":case["id"], "arm":arm, "workflow":case["workflow"], "state":"needs_clarification",
                                  "last_error":str(exc), "attempts":[], "input_tokens":0, "output_tokens":0,
                                  "runtime_s":0, "provider_fee_usd":0}
                    if not args.holdout and record.get("deliverable"):
                        record["edited_example"] = edit_example(lab, record)
                    dump(result, {**meta, **record})
                    print(case["id"], record["workflow"], record["state"], record["runtime_s"], record["input_tokens"], record["output_tokens"], flush=True)
                finally:
                    lab.close()
    if not args.holdout:
        print(verify(args.out, meta["checkout"]))


if __name__ == "__main__":
    main()
