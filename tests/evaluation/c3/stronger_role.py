"""Replay one bounded Studio role from each original synthetic integration receipt."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from time import monotonic, sleep
from types import SimpleNamespace

from product_qualification_summary import FROZEN, ROOT, WEIGHTS, WF, composition, plan, read, require

REVISION = "bb5d59e06d9551d752d08b292a50eb208b07ab1f"
SHARDS = {
    "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf": "dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db",
    "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf": "539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a",
}
IMAGE = "ghcr.io/ggml-org/llama.cpp:server@sha256:20db01dc9a92bff54a5b9fe4078caa52be6a0c1fa73859c6449e25b9cb67f998"
ORIGIN = "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/" + REVISION + "/"
URL = "http://127.0.0.1:18082"
GIB = 2**30
CONTEXT = 8192
# FP16 keys and values, layers, KV heads, head dimension, bytes, context.
KV = 2 * 28 * 4 * 128 * 2 * CONTEXT
MODEL_BOUND = 4_700_000_000
sys.path.insert(0, str(ROOT))


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    temp.replace(path)


def resource_gate(available, disk):
    need = MODEL_BOUND + KV + 3 * GIB
    return {
        "available_ram_bytes": available,
        "disk_free_bytes": disk,
        "weight_bytes_upper_bound": MODEL_BOUND,
        "fp16_kv_bytes": KV,
        "ram_required_bytes": need,
        "disk_required_bytes": MODEL_BOUND + 3 * GIB,
        "error": "insufficient available RAM including KV and working reserve"
        if available < need
        else "insufficient free disk for shards and image"
        if disk < MODEL_BOUND + 3 * GIB
        else None,
    }


def host_gate(folder):
    values = Path("/proc/meminfo").read_text().splitlines()
    avail = int(next(row.split()[1] for row in values if row.startswith("MemAvailable:"))) * 1024
    limit = Path("/sys/fs/cgroup/memory.max")
    if limit.is_file() and limit.read_text().strip() != "max":
        avail = min(avail, int(limit.read_text()) - int(limit.with_name("memory.current").read_text()))
    return resource_gate(avail, shutil.disk_usage(folder).free)


def source_pair(case, kind, record, pair, checkout):
    from migrations.runtime_bundle import canonical_hash

    role = "strategy" if kind == "WF-03" else "content"
    body = pair["request"]
    worker_hash = sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    require(
        record["origin"] == "internal"
        and record["arm"] == "improved"
        and record["cases_sha256"] == FROZEN
        and record["model_sha256"] == WEIGHTS
        and record["checkout"] == checkout
        and record["worker_concurrency"] == 1
        and record["provider"] == "llama.cpp loopback",
        "Baseline conditions mismatch",
    )
    require(
        case == record["case"] == pair["case"] and record["workflow"] == pair["workflow"] == WF[kind] and pair["role"] == role, "Source case/workflow mismatch"
    )
    matched = record["matched_instruction_control"]
    require(
        matched["paired_treatment_attempt_id"] == pair["attempt_id"]
        and matched["treatment_request_digest"] == canonical_hash(body)
        and pair["request_sha256"] == worker_hash == matched["treatment_attempt_request_sha256"],
        "Unbound role request",
    )
    require(
        set(body) == {"model", "temperature", "max_tokens", "messages", "response_format"}
        and body["model"] == "amc-local"
        and body["temperature"] == 0
        and body["max_tokens"] == 640
        and [m["role"] for m in body["messages"]] == ["system", "user"]
        and body["response_format"]["json_schema"]["name"] == "c3_skills_" + role,
        "Unexpected role request contract",
    )
    require(
        record["projection_digest"] == canonical_hash(pair["projection"]) and pair["treatment_groups"] == record["composed"]["groups"],
        "Projection or composed fields mismatch",
    )
    sources = [a for a in record["attempts"] if a["attempt_id"] == pair["attempt_id"]]
    require(
        len(sources) == 1
        and sources[0]["request_sha256"] == worker_hash
        and sources[0]["schema"] == "c3_skills_" + role
        and sources[0]["raw_output"] == pair["checkpoints"][role]["raw_reply"],
        "Missing observed baseline role output",
    )
    return sources[0]


def setup_model(weights, report):
    import hashlib
    import httpx

    weights.mkdir(parents=True, exist_ok=True)
    verified = {}
    for name, expected in SHARDS.items():
        path = weights / name
        subprocess.run(
            [
                "curl",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "-fLsS",
                "--max-time",
                "300",
                "--max-filesize",
                str(MODEL_BOUND),
                "-o",
                str(path),
                ORIGIN + name,
            ],
            check=True,
            timeout=315,
        )
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        require(actual == expected, "GGUF SHA mismatch: " + name)
        verified[name] = {"sha256": actual, "bytes": path.stat().st_size}
    report["verified_shards"] = verified
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "c3-stronger",
            "--memory=9g",
            "--memory-swap=9g",
            "--cpus=4",
            "-p",
            "127.0.0.1:18082:8080",
            "--mount",
            f"type=bind,src={weights.resolve()},dst=/models,readonly",
            IMAGE,
            "-m",
            "/models/" + next(iter(SHARDS)),
            "--alias",
            "amc-local",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "-c",
            str(CONTEXT),
            "-np",
            "1",
            "-t",
            "4",
        ],
        check=True,
        timeout=180,
    )
    with httpx.Client(trust_env=False, timeout=5) as client:
        for _ in range(60):
            try:
                r = client.get(URL + "/health")
                if r.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            sleep(2)
        else:
            raise ValueError("llama.cpp readiness timeout")
        props = client.get(URL + "/props")
        props.raise_for_status()
        props = props.json()
        require(props.get("model_path", "").endswith(next(iter(SHARDS))), "Unexpected loaded GGUF")
        report["build"] = props.get("build_info")
        report["backend_model_path"] = props["model_path"]
    return int(subprocess.check_output(["docker", "inspect", "--format", "{{.State.Pid}}", "c3-stronger"], text=True, timeout=8))


def peak_rss(pid):
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1]) * 1024
    raise ValueError("kernel did not expose model process peak RSS")


def measure(record, pair, attempt):
    from app import c3_studio, c3_skill_library
    from app.workforce_gateway import GatewayError, infer

    role, workflow, projection = pair["role"], pair["workflow"], pair["projection"]
    native = pair["checkpoints"]
    before = c3_studio.compose(workflow, projection, native)
    require(before == pair["treatment_groups"], "Original composer replay mismatch")
    started = monotonic()
    evidence = {
        "role": role,
        "baseline_attempt": attempt["attempt_id"],
        "request_sha256": attempt["request_sha256"],
        "baseline_input_tokens": attempt["input_tokens"],
        "baseline_output_tokens": attempt["output_tokens"],
        "projection_digest": record["projection_digest"],
        "input_tokens": None,
        "output_tokens": None,
        "baseline_role_output": attempt["raw_output"],
        "provider_fee_usd": 0,
    }
    try:
        raw, n_in, n_out = infer(SimpleNamespace(provider="local", url=URL + "/v1", timeout=110), pair["request"])
        evidence.update(raw_output=raw, input_tokens=n_in, output_tokens=n_out)
        validated = c3_skill_library.validate(raw, role, {}, {f["id"]: f for f in projection["facts"]})
        groups = c3_studio.compose(workflow, projection, native | {role: validated})
        treatment = {"groups": groups, "field_findings": c3_studio.quality_issues(workflow, groups, projection)}
        evidence.update(composed=treatment, paired=composition(record["composed"], treatment), state="paired")
    except GatewayError as exc:
        evidence.update(state="attempt_failed", reason=str(exc))
        if exc.usage:
            evidence.update(input_tokens=exc.usage[1], output_tokens=exc.usage[2])
    evidence["seconds"] = round(monotonic() - started, 3)
    return evidence


def main():
    import httpx

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("out", type=Path)
    args = cli.parse_args()
    checkout = os.environ["GITHUB_SHA"]
    require(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_REPOSITORY") == "datnv41001/ai-company"
        and os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
        and os.environ.get("RUNNER_OS") == "Linux"
        and subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == checkout,
        "Expected same-run GitHub Linux integration",
    )
    result = {
        "source_run": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "checkout": checkout,
        "source_artifact": "pool-model-measurements-integration",
        "frozen_sha256": FROZEN,
        "assigned": 10,
        "candidate": "Qwen2.5-7B-Instruct Q4_K_M",
        "revision": REVISION,
        "expected_shards": SHARDS,
        "license": "Apache-2.0",
        "image": IMAGE,
        "baseline_model_sha256": WEIGHTS,
        "role_concurrency": 1,
        "max_attempts": 10,
        "retries": 0,
        "provider_fee_usd": 0,
        "cases": {},
        "semantic_advantage": None,
        "human_accepted": None,
    }

    def checkpoint():
        rows = result["cases"].values()
        result["paired"] = sum(r["state"] == "paired" for r in rows)
        result["invoked"] = sum(r["state"] in {"paired", "attempt_failed"} for r in rows)
        result["observed_tokens"] = {k: sum(r.get(k) or 0 for r in rows) for k in ("input_tokens", "output_tokens")}
        result["unmetered_attempts"] = sum(r["state"] == "attempt_failed" and r.get("input_tokens") is None for r in rows)
        write(args.out / "summary.json", result)

    result["status"] = "preflight"
    assigned, _ = plan(ROOT, "study")
    for cid in assigned:
        result["cases"][cid] = {"state": "pending"}
    checkpoint()
    pid = None
    try:
        require(not (ROOT / "docs/evaluation/c3-product-v2/RESULTS.md").exists(), "Existing qualification dossier")
        gate = host_gate(args.out)
        result["hardware"] = gate
        require(not gate["error"], gate["error"])
        meta = read(args.source / "conditions.json")
        require(meta["checkout"] == checkout and meta["cases_sha256"] == FROZEN and meta["model_sha256"] == WEIGHTS, "Wrong source artifact")
        inputs = {}
        for cid, kind in assigned.items():
            try:
                pair = read(args.source / cid / "paired-role.json")
                record = read(args.source / cid / "result.json")
                attempt = source_pair(cid, kind, record, pair, checkout)
                inputs[cid] = (record, pair, attempt)
            except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
                result["cases"][cid] = {"state": "unpaired_source", "reason": str(exc)}
        require(inputs, "No matched baseline role requests")
        pid = setup_model(Path(os.environ["RUNNER_TEMP"]) / "c3-stronger-model", result)
        result["status"] = "running"
        result["peak_model_rss_bytes"] = peak_rss(pid)
        checkpoint()
        for cid, values in inputs.items():
            obs = measure(*values)
            write(args.out / cid / "result.json", obs)
            result["cases"][cid] = {k: v for k, v in obs.items() if k not in ("raw_output", "composed", "baseline_role_output")}
            checkpoint()
            result["peak_model_rss_bytes"] = max(result["peak_model_rss_bytes"], peak_rss(pid))
        result["status"] = "paired_all" if result["paired"] == len(assigned) else "partial"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, httpx.HTTPError) as exc:
        result.update(status="partial" if result.get("invoked") else "skipped", reason=str(exc))
    finally:
        for row in result["cases"].values():
            if row["state"] == "pending":
                row.update(state="unobserved", reason=result.get("reason", "measurement interrupted"))
        checkpoint()
    print(result["status"], result["paired"], "/", len(assigned), result.get("reason", ""))


if __name__ == "__main__":
    main()
