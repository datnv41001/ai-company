"""Entry point for the paired fixture study. A new run writes a new evidence folder."""

import argparse
import base64
import gzip
import json
from pathlib import Path

from local_adapter import LocalAdapter, launch
from pilot_fixture import FAMILY, MODEL, MODEL_DIGEST, MODEL_VERSION, digest, encoded
from quality_corpus import SEEDS, corpus, deterministic, git_fixture
from quality_eval import compare
from quality_run import frozen, measurement, packet, parse, read, save, seed_run
from receipt_auth import Signer
from review_journal import Journal
from review_plan import EvidenceSigner, plan_digest


def main_run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    cases, keys = corpus(args.cohort)
    manifest = git_fixture(cases)
    signer = Signer.generate("local-fixture-quality")
    assessor = EvidenceSigner.generate()
    trust = {
        signer.key_id: {
            "public_key": signer.public_key,
            "adapter_identity": "local-fixture-quality",
            "model": MODEL,
            "model_version": MODEL_VERSION,
            "model_digest": MODEL_DIGEST,
            "family": FAMILY,
        }
    }
    ext = {
        "cohort": args.cohort,
        "output_protocol": "named-choices" if args.cohort == "identity" else "eight-digit-menu",
        "adapter_trust": trust,
        "verifier_key": assessor.public_key,
        "corpus_pin": manifest["bundle_sha256"],
        "keybook_pin": digest(encoded(keys)),
        "plan_pins": {str(s): plan_digest(frozen(cases, s)) for s in SEEDS},
    }
    save(out / "enrollment.json", ext)
    print("Enrollment SHA-256", digest((out / "enrollment.json").read_bytes()), flush=True)
    with launch(args.server, args.model, runtime_pins=args.runtime_pins) as (adapter, meta):
        save(out / "environment.json", meta)
        for seed in SEEDS:
            seed_run(out, seed, cases, manifest, adapter, signer, assessor, trust)
    summarize(out, True)


def replay(out, seed, registry, cases, keys, manifest):
    package = json.loads(gzip.decompress((out / f"seed-{seed}.json.gz").read_bytes()))
    run = package["run"]
    p = frozen(cases, seed)
    if (
        registry["corpus_pin"] != manifest["bundle_sha256"]
        or run["policy_digest"] != plan_digest(p)
        or p != package["plan"]
        or plan_digest(p) != registry["plan_pins"][str(seed)]
        or run["source_manifest_digest"] != digest(encoded(manifest))
        or run["base_sha"] != manifest["base_sha"]
        or run["head_sha"] != manifest["head_sha"]
        or registry["keybook_pin"] != digest(encoded(keys))
    ):
        raise ValueError("Wrong experiment or scoring oracle")
    trusted = Journal.verify_events(
        run["run_id"],
        package["events"],
        package["checkpoint"],
        registry["adapter_trust"],
        expected_plan_digest=plan_digest(p),
        verifier_key=registry["verifier_key"],
    )
    if trusted["run"] != run or trusted.get("coverage_report") != package["coverage"]:
        raise ValueError("Run or immutable coverage mismatch")
    accepted = trusted["accepted_attempts"]
    by_assignment = {v["assignment"]["assignment_id"]: (k, v) for k, v in accepted.items()}
    if set(by_assignment) != {j["assignment_id"] for j in p["assignments"]}:
        raise ValueError("Missing planned inference")
    raw = {e["data"]["attempt_id"]: base64.b64decode(e["data"]["output"]) for e in package["events"] if e["kind"] == "receipt"}
    rows = {c["unit"]: c for c in cases}
    records = []
    adapter = LocalAdapter(None, "airc-qwen-" + MODEL_DIGEST[:12], None, None)
    for job in p["assignments"]:
        body, scope, group = packet(job, rows, seed, records, adapter)
        attempt, verified = by_assignment[job["assignment_id"]]
        receipt = verified["receipt"]
        response = json.loads(raw[attempt])
        if (
            receipt["context_digest"] != digest(encoded(body))
            or response["id"] != receipt["provider_request_or_local_execution_id"]
            or response["model"] != body["model"]
            or response["usage"]["prompt_tokens"] != receipt["input_tokens"]
            or response["usage"]["completion_tokens"] != receipt["output_tokens"]
        ):
            raise ValueError("Request, response or usage mismatch")
        records.append(measurement(verified["assignment"], receipt, group, parse(raw[attempt], scope)))
    observations = {(e["data"]["assignment_id"], e["data"]["obligation_id"]): e["data"] for e in package["events"] if e["kind"] == "evidence"}
    for r in records:
        if r["phase"] != "arbitration":
            continue
        for uid, op in r["opinions"].items():
            case = rows[uid]
            grounded = op["evidence"] == case["authoritative_source"] and op["affected_subject"] == case["subject"]
            expected = deterministic(case)
            status = "verified" if grounded and expected is not None and op["status"] == ("flag" if expected else "clear") else "insufficient"
            observed = observations.get((r["assignment_id"], uid), {})
            if (
                observed.get("evidence_digest") != digest(encoded(case))
                or observed.get("disposition") != status
                or observed.get("output_digest") != accepted[r["attempt_id"]]["receipt"]["output_digest"]
            ):
                raise ValueError("Evidence observation not reproducible")
    facts = {
        "run_id": run["run_id"],
        "base_sha": run["base_sha"],
        "head_sha": run["head_sha"],
        "model": MODEL,
        "model_version": MODEL_VERSION,
        "model_digest": MODEL_DIGEST,
        "family": FAMILY,
        "distinct_reviewers": sorted({r["reviewer_id"] for r in records}),
        "phase_calls": {p: sum(r["phase"] == p for r in records) for p in ("blind", "cross", "arbitration")},
        "dispatches": trusted["dispatches"],
        "attempts": trusted["attempts"],
        "accepted_receipts": trusted["accepted_receipts"],
        "rejected_receipts": trusted["rejected_receipts"],
        "input_tokens": trusted["input_tokens"],
        "output_tokens": trusted["output_tokens"],
        "settled_microusd": trusted["settled_microusd"],
        "uncertain_attempts": trusted["uncertain_attempts"],
        "configured_budget": run["budget"],
    }
    return compare(cases, records, keys), package["coverage"], facts


def public_index(out):
    names = ["enrollment.json", "environment.json", "metrics.json", "trace.json.gz"]
    names.extend(f"seed-{s}.json.gz" for s in SEEDS)
    return {name: digest((out / name).read_bytes()) for name in names}


def verify_index(out, trusted_pin):
    if digest((out / "index.json").read_bytes()) != trusted_pin or read(out / "index.json") != public_index(out):
        raise ValueError("Published evidence differs from reviewed package")


def summarize(out, write=False):
    out = Path(out)
    registry = read(out / "enrollment.json")
    if read(out / "environment.json")["model_sha256"] != MODEL_DIGEST or any(t["model_digest"] != MODEL_DIGEST for t in registry["adapter_trust"].values()):
        raise ValueError("Unexpected model artifact")
    cases, keys = corpus(registry.get("cohort", "marketing"))
    manifest = git_fixture(cases)
    result = {
        "fixture": manifest,
        "oracle_provenance": {
            "synthetic": len(keys),
            "synthetic_by_provenance": {k: sum(row["provenance"] == k for row in keys.values()) for k in sorted({row["provenance"] for row in keys.values()})},
            "real_historical_labels": 0,
            "human_domain_labels": 0,
            "ai_adjudicated_labels": 0,
        },
        "seeds": {},
    }
    traces = {}
    for seed in SEEDS:
        scores, coverage, facts = replay(out, seed, registry, cases, keys, manifest)
        result["seeds"][str(seed)] = {
            "participation": facts,
            "five_arms": scores["five_arms"],
            "resources": scores["resources"],
            "coverage": coverage,
            "deterministic_abstentions": scores["deterministic_abstentions"],
            "phase_metrics": {k: {n: v for n, v in phase.items() if n != "by_domain"} for k, phase in scores["council"]["phases"].items()},
        }
        traces[str(seed)] = scores
    if write:
        save(out / "metrics.json", result)
        (out / "trace.json.gz").write_bytes(gzip.compress(encoded(traces), mtime=0))
        save(out / "index.json", public_index(out))
        print("Archive SHA-256", digest((out / "index.json").read_bytes()), flush=True)
    elif read(out / "metrics.json") != result or json.loads(gzip.decompress((out / "trace.json.gz").read_bytes())) != traces:
        raise ValueError("Metrics or lifecycle differs from immutable outputs")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_subparsers(dest="cmd", required=True)
    run = cmd.add_parser("run")
    run.add_argument("--cohort", choices=["marketing", "identity"], default="marketing")
    run.add_argument("--server", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--runtime-pins", help="Operator-reviewed runtime manifest for the executing platform")
    run.add_argument("--out", required=True)
    verify = cmd.add_parser("verify")
    verify.add_argument("--out", required=True)
    verify.add_argument("--enrollment-pin", required=True)
    verify.add_argument("--archive-pin", required=True)
    args = parser.parse_args()
    if args.cmd == "run":
        main_run(args)
    else:
        if digest((Path(args.out) / "enrollment.json").read_bytes()) != args.enrollment_pin:
            raise ValueError("Operator trust anchor differs")
        verify_index(Path(args.out), args.archive_pin)
        summarize(args.out)
        print("Verified frozen holdout, plan, signed model responses and phase-level scores.")
