"""Execute pinned local inference or independently replay the complete v3 fixture study."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import gzip
import json
from pathlib import Path
import time
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from local_adapter import launch
from pilot_fixture import encoded, digest
from quality_run import save
from receipt_auth import Signer
from review_journal import Journal
from review_plan import catalog, plan_digest
from union_cases import SEEDS, holdout, manifest
from union_eval import decide, raw_scores, summarize
from union_protocol import MODELS, RUNTIME, authorized_context, parse, plan
from union_resources import Resources

ROOT = Path(__file__).resolve().parent


def register(out, private):
    if private.resolve().is_relative_to(ROOT.parents[1]) or private.resolve().is_relative_to(out.resolve()):
        raise ValueError("private keys must be outside checkout")
    out.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    rows, labels = holdout()
    source = manifest(rows)
    trust = {}
    pins = {}
    for label, (model, revision, weights, family) in MODELS.items():
        key = Ed25519PrivateKey.generate()
        path = private / label
        path.write_bytes(key.private_bytes_raw())
        path.chmod(0o600)
        signer = Signer("union-" + label, key)
        trust[label] = {
            signer.key_id: dict(
                public_key=signer.public_key, adapter_identity=signer.adapter_identity, model=model, model_version=revision, model_digest=weights, family=family
            )
        }
        pins[label] = plan_digest(plan(rows, source, label, signer.key_id))
    verifier = base64.b64encode(Ed25519PrivateKey.generate().public_key().public_bytes_raw()).decode()
    save(
        out / "enrollment.json",
        dict(
            source=source,
            oracle=digest(encoded(labels)),
            trust=trust,
            plan_pins=pins,
            verifier_key=verifier,
            runtime_digest=RUNTIME,
            catalog=catalog()[0],
            version=3,
        ),
    )
    print(digest((out / "enrollment.json").read_bytes()), flush=True)


def open_enrollment(out, pin, label):
    raw = (out / "enrollment.json").read_bytes()
    if digest(raw) != pin:
        raise ValueError("external enrollment differs")
    e = json.loads(raw)
    rows, labels = holdout()
    source = manifest(rows)
    trust = e["trust"][label]
    kid = next(iter(trust))
    mdl = MODELS[label]
    profile = trust[kid]
    if (
        e["source"] != source
        or e["oracle"] != digest(encoded(labels))
        or e["runtime_digest"] != RUNTIME
        or e["catalog"] != catalog()[0]
        or (profile["model"], profile["model_version"], profile["model_digest"], profile["family"]) != mdl
    ):
        raise ValueError("source, model, label or runtime differs")
    p = plan(rows, source, label, kid)
    if plan_digest(p) != e["plan_pins"][label]:
        raise ValueError("frozen plan differs")
    return e, rows, labels, kid, p


def execute(out, private, pin, label, binary, weight):
    e, rows, labels, kid, p = open_enrollment(out, pin, label)
    target = out / (label + ".json.gz")
    partial = out / (label + "-partial.json")
    if target.exists() or partial.exists():
        raise ValueError("study arm already started")
    signer = Signer("union-" + label, Ed25519PrivateKey.from_private_bytes((private / label).read_bytes()))
    if kid != signer.key_id:
        raise ValueError("signing principal differs")
    rid = "union-study-" + uuid4().hex
    src = e["source"]
    run = dict(
        type="run.v1",
        run_id=rid,
        repository="fixture/meridian-offers",
        pr_number=1,
        base_sha=src["base"],
        head_sha=src["head"],
        merge_base=src["base"],
        integration_sha=None,
        catalog_digest=e["catalog"],
        policy_digest=plan_digest(p),
        source_manifest_digest=digest(encoded(src)),
        dependency_map_digest=digest(encoded([r["id"] for r in rows])),
        implementer_principals=["fixture-publisher"],
        mode="targeted",
        risk="low",
        budget=dict(
            max_concurrency=1,
            max_tokens=90000 if label == "q05" else 12000,
            max_cost_microusd=0,
            attempt_timeout_seconds=180,
            max_retries=0,
            deadline_utc=(datetime.now(timezone.utc) + timedelta(minutes=55)).isoformat(),
            max_debate_rounds=1,
            paid_approval_id=None,
            tariff_digest=None,
        ),
    )
    j = Journal(private / (label + ".sqlite"))
    previous = {}
    times = {}
    sealed = False
    try:
        j.start_planned(run, e["trust"][label], p, e["verifier_key"])
        with launch(binary, weight, expected_model_digest=MODELS[label][2]) as (adapter, env):
            with Resources(adapter.process.pid) as meter:
                for job in p["assignments"]:
                    if job["phase"] != "blind" and not sealed:
                        j.seal(rid)
                        sealed = True
                    body = authorized_context(job, p, previous)
                    adapter.admit(body)
                    ass = {k: job[k] for k in ("assignment_id", "reviewer_id", "phase", "artifact_kind", "principal", "tool_grant_digest")}
                    ass.update(
                        type="assignment.v1",
                        run_id=rid,
                        base_sha=src["base"],
                        head_sha=src["head"],
                        round=int(job["phase"] != "blind"),
                        topic="synthetic product copy",
                        reason="frozen semantic scope",
                        output_contract=catalog()[1][job["reviewer_id"]]["contract"],
                        context_digest=digest(encoded(body)),
                        token_reservation=3500,
                        cost_reservation_microusd=0,
                    )
                    attempt = j.reserve(ass, kid)["attempt_id"]
                    j.dispatch(attempt)
                    start = time.perf_counter()
                    try:
                        raw = adapter.complete(body, 175)
                        resp = json.loads(raw)
                    except Exception:
                        j.timeout(attempt)
                        raise
                    errors = None
                    try:
                        parse(raw, body)
                    except Exception as exc:
                        errors = exc
                    receipt = j.receipt_template(attempt)
                    receipt.update(
                        ended_utc=datetime.now(timezone.utc).isoformat(),
                        outcome="failed" if errors else "completed",
                        output_digest=digest(raw),
                        usage_known=True,
                        input_tokens=resp["usage"]["prompt_tokens"],
                        output_tokens=resp["usage"]["completion_tokens"],
                        cost_microusd=0,
                        provider_request_or_local_execution_id=resp["id"],
                    )
                    signed = signer.sign(receipt)
                    status = j.ingest(signed, raw)
                    if errors:
                        raise ValueError("invalid response with known usage") from errors
                    if status != "accepted":
                        raise ValueError("receipt fenced")
                    previous[attempt] = dict(state="accepted", assignment=ass, output=base64.b64encode(raw).decode())
                    times[job["assignment_id"]] = round(time.perf_counter() - start, 3)
                    print(label, job["assignment_id"], receipt["input_tokens"], receipt["output_tokens"], flush=True)
                if not sealed:
                    j.seal(rid)
        record = dict(run=run, events=j.export_events(rid), checkpoint=j.checkpoint(rid), runtime=env, resources=meter.report(), latencies=times)
        target.write_bytes(gzip.compress(encoded(record), mtime=0))
    except Exception:
        j.cancel(rid)
        save(partial, dict(summary=j.summary(rid), checkpoint=j.checkpoint(rid)))
        raise
    finally:
        j.close()


def replay(out, pin, label):
    e, rows, labels, kid, p = open_enrollment(out, pin, label)
    data = json.loads(gzip.decompress((out / (label + ".json.gz")).read_bytes()))
    run = data["run"]
    src = e["source"]
    if (run["base_sha"], run["head_sha"], run["source_manifest_digest"], run["policy_digest"]) != (
        src["base"],
        src["head"],
        digest(encoded(src)),
        plan_digest(p),
    ):
        raise ValueError("wrong source or policy")
    checked = Journal.verify_events(
        run["run_id"], data["events"], data["checkpoint"], e["trust"][label], expected_plan_digest=plan_digest(p), verifier_key=e["verifier_key"]
    )
    runtime = json.loads((ROOT / "runtime-pins/windows-x64.json").read_bytes())
    if (
        checked["run"] != run
        or data["runtime"]["model_sha256"] != MODELS[label][2]
        or data["runtime"]["binary_sha256"] != runtime["files"][runtime["executable"]]
    ):
        raise ValueError("wrong run or executable")
    raw = {r["data"]["attempt_id"]: base64.b64decode(r["data"]["output"]) for r in data["events"] if r["kind"] == "receipt"}
    accepted = checked["accepted_attempts"]
    previous = {}
    records = []
    ids = set()
    for job in p["assignments"]:
        aid = job["assignment_id"]
        attempt, v = next((k, v) for k, v in accepted.items() if v["assignment"]["assignment_id"] == aid)
        body = authorized_context(job, p, previous)
        receipt = v["receipt"]
        blob = raw[attempt]
        response = json.loads(blob)
        if (digest(encoded(body)), response["id"], response["usage"]["prompt_tokens"], response["usage"]["completion_tokens"], body["model"]) != (
            receipt["context_digest"],
            receipt["provider_request_or_local_execution_id"],
            receipt["input_tokens"],
            receipt["output_tokens"],
            response["model"],
        ):
            raise ValueError("raw output/request/usage mismatch")
        previous[attempt] = dict(state="accepted", assignment=v["assignment"], output=base64.b64encode(blob).decode())
        ids.add(job["reviewer_id"])
        wall = (datetime.fromisoformat(receipt["ended_utc"]) - datetime.fromisoformat(receipt["started_utc"])).total_seconds()
        records.append(
            dict(
                id=aid,
                reviewer=job["reviewer_id"],
                op=parse(blob, body),
                seconds=round(wall, 3),
                input=receipt["input_tokens"],
                output=receipt["output_tokens"],
                context_limit=4096,
                output_ceiling=body["max_tokens"],
                timings=response.get("timings", {}),
            )
        )
    if set(data["latencies"]) != {r["id"] for r in records} or len(accepted) != len(records):
        raise ValueError("incomplete study")
    sem = [r for r in rows if r["kind"] == "semantic"]
    arms = {"blind": ("common",)}
    if label == "q05":
        arms.update(
            one_repeated=("common", "repeat"),
            two_independent=("common", "specialist"),
            source_first=("prompt",),
            decomposed=("split",),
            post_cross=("common", "specialist", "cross"),
            full_union=("common", "specialist", "cross", "arb"),
        )
    results = {}
    for seed in SEEDS:
        base = decide(rows, [])
        by_arm = {}
        for name, groups in arms.items():
            chosen = [r for r in records if r["id"].split("-")[0] in groups and r["id"].split("-")[1] == str(seed)]
            opinions = [r["op"] for r in chosen]
            decisions = decide(rows, opinions)
            tokens = sum(r["input"] + r["output"] for r in chosen)
            seconds = sum(r["seconds"] for r in chosen)
            by_arm[name] = dict(
                calls=len(chosen),
                tokens=tokens,
                seconds=round(seconds, 3),
                output_ceiling=sum(r["output_ceiling"] for r in chosen),
                generated_tokens_per_wall_second=round(sum(r["output"] for r in chosen) / seconds, 2),
                raw=raw_scores(sem, labels, opinions),
                union=summarize(rows, decisions),
                decisions=decisions,
            )
        results[str(seed)] = {"deterministic": summarize(rows, base), "arms": by_arm}
    return dict(
        model=MODELS[label][0],
        reviewers=sorted(ids),
        calls=len(records),
        failed=checked["attempts"] - len(records),
        input_tokens=checked["input_tokens"],
        output_tokens=checked["output_tokens"],
        cost_microusd=checked["settled_microusd"],
        resources=data["resources"],
        seeds=results,
    )


def results(out, pin):
    return {label: replay(out, pin, label) for label in MODELS}


if __name__ == "__main__":
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("action", choices=("enroll", "run", "replay"))
    cmd.add_argument("--out", required=True, type=Path)
    cmd.add_argument("--private", type=Path)
    cmd.add_argument("--pin")
    cmd.add_argument("--label", choices=MODELS)
    cmd.add_argument("--binary")
    cmd.add_argument("--weight")
    args = cmd.parse_args()
    if args.action == "enroll":
        register(args.out, args.private)
    elif args.action == "run":
        execute(args.out, args.private, args.pin, args.label, args.binary, args.weight)
    else:
        print(json.dumps(results(args.out, args.pin), sort_keys=True))
