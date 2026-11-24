"""Dedicated loopback-only llama.cpp adapter for one checksum-pinned GGUF."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time
import tempfile
import urllib.error
import urllib.request

from host_capacity import machine_slot, spawn_with_slot
from pilot_fixture import MODEL_DIGEST, encoded


def file_digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


class LocalAdapter:
    def __init__(self, origin, alias, key, process):
        self.origin, self.alias, self.key, self.process = origin, alias, key, process
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def post(self, path, payload, timeout):
        if self.process.poll() is not None:
            raise RuntimeError("Owned llama process exited")
        request = urllib.request.Request(
            self.origin + path, data=encoded(payload), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key}
        )
        with self.opener.open(request, timeout=timeout) as response:
            raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise ValueError("Oversized local adapter response")
        return raw

    def payload(self, messages, schema, seed):
        return {
            "model": self.alias,
            "messages": messages,
            "response_format": {"type": "json_schema", "json_schema": {"name": "review", "strict": True, "schema": schema}},
            "max_tokens": 720,
            "temperature": 0.45,
            "seed": seed,
            "stream": False,
            "cache_prompt": False,
        }

    def admit(self, payload):
        # Count the actual rendered template (the grammar is applied at sampling).
        prompt = json.loads(self.post("/apply-template", {"messages": payload["messages"]}, 10))["prompt"]
        ids = json.loads(self.post("/tokenize", {"content": prompt, "add_special": True, "parse_special": True}, 10))["tokens"]
        if len(ids) > 2998:
            raise ValueError("Input exceeds 3,000-token cap")
        return len(ids)

    def complete(self, payload, timeout=90):
        return self.post("/v1/chat/completions", payload, timeout)


def stage_runtime(binary, model, directory, pins_path, binary_digest, model_digest):
    """Copy the operator-approved runtime into a private, empty loader directory."""
    pins = json.loads(Path(pins_path).read_bytes())
    files = pins["files"]
    if pins["format"] != 1 or pins["executable"] != binary.name or files.get(binary.name) != binary_digest:
        raise ValueError("Runtime does not match enrolled executable")
    for name, expected in files.items():
        if not name or name != Path(name).name or name in (".", "..") or "/" in name or "\\" in name:
            raise ValueError("Invalid runtime bundle member")
        target = directory / name
        shutil.copyfile(binary.parent / name, target)
        if file_digest(target) != expected:
            raise ValueError("Runtime component digest mismatch: " + name)
        target.chmod(0o500)
    weight = directory / "weights.gguf"
    shutil.copyfile(model, weight)
    if file_digest(weight) != model_digest:
        raise ValueError("Unexpected model weights")
    weight.chmod(0o400)
    return directory / binary.name, weight


@contextmanager
def launch(binary, model, *, expected_binary_digest=None, expected_model_digest=MODEL_DIGEST, runtime_pins=None):
    binary, model = Path(binary).resolve(strict=True), Path(model).resolve(strict=True)
    runtime_pins = runtime_pins or Path(__file__).parent / "runtime-pins" / "windows-x64.json"
    if expected_binary_digest is None:
        pins = json.loads(Path(runtime_pins).read_bytes())
        expected_binary_digest = pins["files"][pins["executable"]]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    # Do not inherit integration credentials or proxies. Use an ephemeral key so
    # another listener cannot silently impersonate the process on this port.
    env = {k: os.environ[k] for k in ("SystemRoot", "WINDIR", "TMP", "TEMP", "TMPDIR") if k in os.environ}
    with machine_slot() as slot, tempfile.TemporaryDirectory(prefix="airc-adapter-") as tmp:
        binary, model = stage_runtime(binary, model, Path(tmp), runtime_pins, expected_binary_digest, expected_model_digest)
        env["PATH"] = str(Path(env["SystemRoot"]) / "System32") if os.name == "nt" else os.defpath
        if os.name != "nt":
            env["LD_LIBRARY_PATH"] = str(Path(tmp))
        key = secrets.token_hex(32)
        keyfile = Path(tmp) / "access"
        keyfile.write_text(key, encoding="ascii")
        keyfile.chmod(0o600)
        alias = "airc-qwen-" + expected_model_digest[:12]
        cmd = [
            str(binary),
            "--model",
            str(model),
            "--alias",
            alias,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--api-key-file",
            str(keyfile),
            "--ctx-size",
            "4096",
            "--parallel",
            "1",
            "--threads",
            "4",
            "--no-ui",
            "--no-warmup",
            "--no-context-shift",
            "--log-disable",
        ]
        proc = spawn_with_slot(
            slot,
            cmd,
            env=env,
            cwd=tmp,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            adapter = LocalAdapter("http://127.0.0.1:" + str(port), alias, key, proc)
            deadline = time.monotonic() + 60
            for _ in range(300):
                try:
                    adapter.post("/tokenize", {"content": "ready"}, 1)
                    break
                except (TimeoutError, urllib.error.URLError):
                    if proc.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Dedicated adapter did not become ready") from None
                    time.sleep(0.2)
            else:
                raise RuntimeError("Dedicated adapter startup timed out")
            yield (
                adapter,
                {"binary_sha256": file_digest(binary), "model_sha256": expected_model_digest, "transport": "private loopback process", "max_concurrency": 1},
            )
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
