"""Provision one pinned quantization and isolated loopback server at a time on the same free runner."""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import shutil
import subprocess
from time import monotonic, sleep

import httpx
from stronger_role import CONTEXT, IMAGE, ORIGIN, SHARDS
from scripts.fetch_workforce_model import DIGEST, URL

MEDIUM_REV = "91cad51170dc346986eccefdc2dd33a9da36ead9"
MEDIUM_NAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MEDIUM_URL = f"https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/{MEDIUM_REV}/{MEDIUM_NAME}"
MODELS = {
    "qwen05": {URL.rsplit("/", 1)[1]: (URL, DIGEST)},
    "qwen7": {k: (ORIGIN + k, v) for k, v in SHARDS.items()},
    "qwen15": {MEDIUM_NAME: (MEDIUM_URL, "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e")},
}
SERVER = "http://127.0.0.1:18084"
CONTAINER = "amc-department-study"


def install(arm, cache):
    cache.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, (url, expected) in MODELS[arm].items():
        file = cache / name
        if not file.is_file():
            subprocess.run(
                [
                    "curl",
                    "--proto",
                    "=https",
                    "--proto-redir",
                    "=https",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--retry",
                    "2",
                    "--retry-all-errors",
                    "--max-time",
                    "600",
                    "--max-filesize",
                    "4800000000",
                    "--output",
                    str(file) + ".part",
                    url,
                ],
                check=True,
                timeout=650,
            )
            Path(str(file) + ".part").replace(file)
        with file.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"Unverified weights: {name}")
        files[name] = {"sha256": actual, "bytes": file.stat().st_size, "origin": url}
    return files


@contextmanager
def serve(arm, cache, receipt):
    before = monotonic()
    receipt.update(
        arm=arm,
        free_disk_bytes=shutil.disk_usage(cache.parent).free,
        image=IMAGE,
        context=CONTEXT,
        compute="4 CPU threads, 9 GiB container memory, no GPU",
        seed=42,
        temperature=0,
        currencies={"provider_fee_usd": 0, "compute_cost_usd": None},
    )
    receipt["weights"] = install(arm, cache)
    filename = next(iter(receipt["weights"]))
    args = [
        "docker",
        "run",
        "--detach",
        "--name",
        CONTAINER,
        "--memory=9g",
        "--memory-swap=9g",
        "--cpus=4",
        "-p",
        "127.0.0.1:18084:8080",
        "--mount",
        f"type=bind,src={cache.resolve()},dst=/models,readonly",
        IMAGE,
        "-m",
        "/models/" + filename,
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
    ]
    subprocess.run(args, check=True, timeout=240)
    try:
        with httpx.Client(timeout=4, trust_env=False) as client:
            for _ in range(120):
                try:
                    props = client.get(SERVER + "/props")
                    if props.is_success and props.json().get("model_path", "").endswith(filename):
                        break
                except httpx.HTTPError:
                    pass
                sleep(2)
            else:
                raise RuntimeError("Loopback model did not report its pinned file")
            receipt["server_build"] = props.json().get("build_info")
        receipt["setup_wall_seconds"] = round(monotonic() - before, 3)
        yield SERVER + "/v1"
    finally:
        # cgroup v2 includes the model and packet/cache charges; it is a process-container measure.
        peak = subprocess.run(["docker", "exec", CONTAINER, "cat", "/sys/fs/cgroup/memory.peak"], capture_output=True, text=True)
        receipt["peak_container_memory_bytes"] = int(peak.stdout) if peak.stdout.strip().isdigit() else None
        stats = subprocess.run(["docker", "exec", CONTAINER, "cat", "/sys/fs/cgroup/cpu.stat"], capture_output=True, text=True)
        receipt["container_cpu_microseconds"] = next((int(line.split()[1]) for line in stats.stdout.splitlines() if line.startswith("usage_usec ")), None)
        subprocess.run(["docker", "rm", "--force", CONTAINER], check=True, timeout=30)
