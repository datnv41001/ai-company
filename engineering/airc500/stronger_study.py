"""Paired, synthetic checkpoint comparison. Run enroll before inference; retain its hash."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema.exceptions import ValidationError

from local_adapter import LocalAdapter, file_digest, launch
from pilot_fixture import FAMILY, MODEL, MODEL_DIGEST, MODEL_VERSION, digest, encoded
from quality_corpus import corpus, git_fixture
from quality_eval import score
from quality_run import parse, prompt, read, save, shape
from receipt_auth import Signer, verify_signature
from review_journal import Journal
from review_plan import catalog, plan_digest

ROOT = Path(__file__).resolve().parent
DOMAINS = ("price", "variant", "qualifier", "negation")
SEEDS = (17, 43)
REVIEWER = "MK-022"
MODELS = {
    "small": (MODEL, MODEL_VERSION, MODEL_DIGEST),
    "larger": ("Qwen2.5-1.5B-Instruct-Q4_K_M", "91cad51170dc346986eccefdc2dd33a9da36ead9", "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"),
}


def selected():
    rows, labels = corpus("marketing")
    chosen = []
    # Immutable stratification before either model runs; no post-selection by predictions.
    for domain in DOMAINS:
        for defect in (True, False):
            chosen.append(min((r for r in rows if r["domain"] == domain and labels[r["unit"]]["defect"] == defect), key=lambda r: r["unit"]))
    cases = sorted(chosen, key=lambda r: r["unit"])
    return cases, {r["unit"]: labels[r["unit"]] for r in cases}


def plan(cases):
    units = [r["unit"] for r in cases]
    entry = catalog()[1][REVIEWER]
    jobs = [dict(assignment_id=f"paired-{s}", reviewer_id=REVIEWER, phase="blind", artifact_kind=entry["artifact_kind"], obligations=units) for s in SEEDS]
    return dict(version=1, assignments=jobs, required_obligations=units)


def packet(label, seed, cases):
    alias = "airc-qwen-" + MODELS[label][2][:12]
    builder = LocalAdapter("", alias, "", None)
    payload = builder.payload(prompt(cases, REVIEWER, "common", {}), shape(cases), seed)
    payload["max_tokens"] = 220
    return payload


def protocol():
    cases, labels = selected()
    manifest = git_fixture(cases)
    pins = ROOT / "runtime-pins/windows-x64.json"
    return dict(
        version=1,
        case_ids=[c["unit"] for c in cases],
        domains=DOMAINS,
        seeds=SEEDS,
        models=MODELS,
        oracle_digest=digest(encoded(labels)),
        manifest=manifest,
        catalog=catalog()[0],
        runtime_pins=digest(encoded(read(pins))),
        plan=plan(cases),
        scoring="Per seed TP FP FN TN; six-field exact fix and five-field explanation among true flags; unsure reported separately",
        requests={m: {str(s): digest(encoded(packet(m, s, cases))) for s in SEEDS} for m in MODELS},
    )


def enroll(out, private):
    if private.resolve().is_relative_to(ROOT.parents[1]) or private.resolve().is_relative_to(out.resolve()):
        raise ValueError("Keep study private keys outside the checkout and public evidence")
    data = protocol()
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    keys = {}
    for label, (model, revision, weight) in MODELS.items():
        key = Ed25519PrivateKey.generate()
        (private / label).write_bytes(key.private_bytes_raw())
        (private / label).chmod(0o600)
        signer = Signer("stronger-local-" + label, key)
        keys[label] = {
            signer.key_id: dict(
                public_key=signer.public_key, adapter_identity=signer.adapter_identity, model=model, model_version=revision, model_digest=weight, family=FAMILY
            )
        }
    # The statistical calibration below uses synthetic label comparisons. No human verification is claimed.
    verifier = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    save(out / "enrollment.json", dict(protocol=data, trust=keys, verifier_key=base64.b64encode(verifier).decode()))
    print("ENROLLMENT", file_digest(out / "enrollment.json"), flush=True)


def pinned(out, expected):
    path = out / "enrollment.json"
    if len(expected) != 64 or file_digest(path) != expected:
        raise ValueError("Operator enrollment differs")
    data = read(path)
    if encoded(data["protocol"]) != encoded(protocol()):
        raise ValueError("Frozen data, source, runtime or input changed")
    return data


def execute(out, private, expected, binary, model, label):
    enrollment = pinned(out, expected)
    cases, _ = selected()
    recipe, manifest = enrollment["protocol"]["plan"], enrollment["protocol"]["manifest"]
    trust = enrollment["trust"][label]
    signer = Signer("stronger-local-" + label, Ed25519PrivateKey.from_private_bytes((private / label).read_bytes()))
    if signer.key_id not in trust:
        raise ValueError("Signing identity differs")
    folder = out / label
    if folder.exists():
        raise ValueError("Refuse to overwrite an earlier arm")
    with launch(binary, model, expected_model_digest=MODELS[label][2]) as (adapter, env):
        folder.mkdir()
        journal = Journal(private / (label + ".sqlite"))
        run_id = "paired-" + uuid4().hex
        run = dict(
            type="run.v1",
            run_id=run_id,
            repository="fixture/marketing-paired",
            pr_number=1,
            base_sha=manifest["base_sha"],
            head_sha=manifest["head_sha"],
            merge_base=manifest["base_sha"],
            integration_sha=None,
            catalog_digest=catalog()[0],
            policy_digest=plan_digest(recipe),
            source_manifest_digest=digest(encoded(manifest)),
            dependency_map_digest=digest(encoded(DOMAINS)),
            implementer_principals=["fixture-publisher"],
            mode="targeted",
            risk="low",
            budget=dict(
                max_concurrency=1,
                max_tokens=8000,
                max_cost_microusd=0,
                deadline_utc=(datetime.now(timezone.utc) + timedelta(minutes=8)).isoformat(),
                attempt_timeout_seconds=90,
                max_retries=0,
                max_debate_rounds=0,
                paid_approval_id=None,
                tariff_digest=None,
            ),
        )
        journal.start_planned(run, trust, recipe, enrollment["verifier_key"])
        try:
            for seed, job in zip(SEEDS, recipe["assignments"], strict=True):
                body = packet(label, seed, cases)
                n = adapter.admit(body)
                ass = dict(
                    type="assignment.v1",
                    run_id=run_id,
                    base_sha=run["base_sha"],
                    head_sha=run["head_sha"],
                    reviewer_id=REVIEWER,
                    assignment_id=job["assignment_id"],
                    phase="blind",
                    round=0,
                    principal="reviewer/" + REVIEWER,
                    topic="Synthetic marketing claims",
                    reason="Matched prompts and checkpoint comparison",
                    context_digest=digest(encoded(body)),
                    tool_grant_digest=digest(encoded(job["obligations"])),
                    output_contract=catalog()[1][REVIEWER]["contract"],
                    artifact_kind=job["artifact_kind"],
                    token_reservation=4000,
                    cost_reservation_microusd=0,
                )
                attempt = journal.reserve(ass, signer.key_id)["attempt_id"]
                journal.dispatch(attempt)
                save(folder / f"request-{seed}.json", body)
                try:
                    raw = adapter.complete(body, 90)
                    (folder / f"response-{seed}.json").write_bytes(raw)
                    response = json.loads(raw)
                except Exception:
                    journal.timeout(attempt)
                    raise
                receipt = journal.receipt_template(attempt)
                try:
                    parse(raw, cases)
                    outcome = "completed"
                except (ValueError, KeyError, IndexError, TypeError, ValidationError):
                    outcome = "failed"
                receipt.update(
                    ended_utc=datetime.now(timezone.utc).isoformat(),
                    outcome=outcome,
                    output_digest=digest(raw),
                    usage_known=True,
                    input_tokens=response["usage"]["prompt_tokens"],
                    output_tokens=response["usage"]["completion_tokens"],
                    cost_microusd=0,
                    provider_request_or_local_execution_id=response["id"],
                )
                signed = signer.sign(receipt)
                state = journal.ingest(signed, raw)
                save(folder / f"receipt-{seed}.json", signed)
                print(label, seed, state, n, receipt["output_tokens"], flush=True)
                if state != "accepted":
                    raise ValueError("No accepted output")
            journal.seal(run_id)
            save(folder / "journal.json", dict(run=run, events=journal.export_events(run_id), checkpoint=journal.checkpoint(run_id), runtime=env))
        except Exception:
            journal.cancel(run_id)
            save(
                folder / "partial.json",
                dict(decision="inconclusive", run=run, events=journal.export_events(run_id), checkpoint=journal.checkpoint(run_id), runtime=env),
            )
            raise
        finally:
            journal.close()


def replay(out, expected):
    e = pinned(out, expected)
    cases, labels = selected()
    result = {}
    for name in MODELS:
        arm = out / name
        state = read(arm / "journal.json")
        manifest = e["protocol"]["manifest"]
        if (state["run"]["base_sha"], state["run"]["head_sha"]) != (manifest["base_sha"], manifest["head_sha"]):
            raise ValueError("Wrong fixture revision")
        if state["runtime"]["model_sha256"] != MODELS[name][2]:
            raise ValueError("Wrong GGUF in environment")
        runtime = read(ROOT / "runtime-pins/windows-x64.json")
        if state["runtime"]["binary_sha256"] != runtime["files"][runtime["executable"]]:
            raise ValueError("Wrong runtime executable")
        checked = Journal.verify_events(
            state["run"]["run_id"],
            state["events"],
            state["checkpoint"],
            e["trust"][name],
            expected_plan_digest=plan_digest(e["protocol"]["plan"]),
            verifier_key=e["verifier_key"],
        )
        if checked["run"] != state["run"] or checked["run"]["source_manifest_digest"] != digest(encoded(manifest)):
            raise ValueError("Run manifest differs from verified journal")
        by_job = {v["assignment"]["assignment_id"]: (k, v) for k, v in checked["accepted_attempts"].items()}
        if set(by_job) != {f"paired-{s}" for s in SEEDS}:
            raise ValueError("Incomplete study")
        result[name] = {}
        for seed in SEEDS:
            body, raw, receipt = read(arm / f"request-{seed}.json"), (arm / f"response-{seed}.json").read_bytes(), read(arm / f"receipt-{seed}.json")
            verify_signature(receipt, e["trust"][name])
            attempt_id, accepted = by_job[f"paired-{seed}"]
            if (
                receipt != accepted["receipt"]
                or receipt["attempt_id"] != attempt_id
                or body != packet(name, seed, cases)
                or receipt["context_digest"] != digest(encoded(body))
                or receipt["output_digest"] != digest(raw)
            ):
                raise ValueError("Unmatched signed response")
            parsed = json.loads(raw)
            if parsed["model"] != body["model"]:
                raise ValueError("Unexpected response model")
            if (receipt["input_tokens"], receipt["output_tokens"], receipt["provider_request_or_local_execution_id"]) != (
                parsed["usage"]["prompt_tokens"],
                parsed["usage"]["completion_tokens"],
                parsed["id"],
            ):
                raise ValueError("Actual usage differs")
            predictions = parse(raw, cases)
            flags = [unit for unit, p in predictions.items() if p["status"] == "flag"]
            metrics = score(flags, labels, {u: [p] for u, p in predictions.items()})
            result[name][str(seed)] = dict(
                metrics=metrics,
                input_tokens=receipt["input_tokens"],
                output_tokens=receipt["output_tokens"],
                elapsed_seconds=(datetime.fromisoformat(receipt["ended_utc"]) - datetime.fromisoformat(receipt["started_utc"])).total_seconds(),
                inconclusive_units=[u for u, p in predictions.items() if p["status"] == "unsure"],
            )
    differences = {}
    for seed in map(str, SEEDS):
        small = result["small"][seed]["metrics"]
        larger = result["larger"][seed]["metrics"]
        small_errors = set(small["false"] + small["missed"])
        larger_errors = set(larger["false"] + larger["missed"])
        differences[seed] = dict(
            correct_only_larger=sorted(small_errors - larger_errors),
            correct_only_small=sorted(larger_errors - small_errors),
            both_wrong=sorted(small_errors & larger_errors),
            both_correct=sorted(labels.keys() - (small_errors | larger_errors)),
        )
    return {"arms": result, "matched_binary_decisions": differences}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="mode", required=True)
    for mode in ("enroll", "run", "replay"):
        cmd = commands.add_parser(mode)
        cmd.add_argument("--out", type=Path, required=True)
        if mode in ("enroll", "run"):
            cmd.add_argument("--private", type=Path, required=True)
        if mode in ("run", "replay"):
            cmd.add_argument("--expected-enrollment", required=True)
        if mode == "run":
            cmd.add_argument("--server", type=Path, required=True)
            cmd.add_argument("--model", type=Path, required=True)
            cmd.add_argument("--arm", choices=MODELS, required=True)
    args = cli.parse_args()
    if args.mode == "enroll":
        enroll(args.out, args.private)
    elif args.mode == "run":
        execute(args.out, args.private, args.expected_enrollment, args.server, args.model, args.arm)
    else:
        print(json.dumps(replay(args.out, args.expected_enrollment), ensure_ascii=False, indent=2))
