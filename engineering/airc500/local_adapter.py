"""Dedicated loopback-only llama.cpp adapter for one checksum-pinned GGUF."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import tempfile
import urllib.error
import urllib.request

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


@contextmanager
def launch(binary, model):
    binary, model = Path(binary).resolve(strict=True), Path(model).resolve(strict=True)
    if file_digest(model) != MODEL_DIGEST:
        raise ValueError("Unexpected model weights")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    # Do not inherit integration credentials or proxies. Use an ephemeral key so
    # another listener cannot silently impersonate the process on this port.
    env = {k: os.environ[k] for k in ("PATH", "SystemRoot", "WINDIR", "TMP", "TEMP", "TMPDIR", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH") if k in os.environ}
    with tempfile.TemporaryDirectory(prefix="airc-adapter-") as tmp:
        key = secrets.token_hex(32)
        keyfile = Path(tmp) / "access"
        keyfile.write_text(key, encoding="ascii")
        keyfile.chmod(0o600)
        alias = "airc-qwen-" + MODEL_DIGEST[:12]
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
        proc = subprocess.Popen(
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
            yield adapter, {"binary_sha256": file_digest(binary), "model_sha256": MODEL_DIGEST, "transport": "private loopback process", "max_concurrency": 1}
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
