"""Identify the installed execution bundle independently of historical manifest digests."""

from functools import lru_cache
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPROVAL = ROOT / "migrations" / "registry-runtime.lock.json"
CONSTRAINTS = ROOT / "requirements-registry.txt"


def canonical_hash(value):
    return sha256(json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def source_fingerprint():
    # Hash directory membership as well as whole files: a new helper or data
    # file must invalidate the same approval as an edit to an existing one.
    paths = [ROOT / "requirements.txt", CONSTRAINTS]
    for name in ("app", "migrations", "catalog"):
        for path in (ROOT / name).rglob("*"):
            relative = path.relative_to(ROOT)
            if "__pycache__" in relative.parts or relative.parts[:2] == ("app", "static") or path == APPROVAL:
                continue
            if path.is_file():
                paths.append(path)
    entries = {}
    for path in paths:
        content = path.read_bytes()
        # Git autocrlf on Windows must produce the same identity as a Linux image.
        if path.suffix in {".py", ".sql", ".json", ".txt"}:
            content = content.replace(b"\r\n", b"\n")
        entries[path.relative_to(ROOT).as_posix()] = sha256(content).hexdigest()
    return canonical_hash(entries)


def runtime_identity():
    packages = {}
    for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, _ = line.split("==")
            packages[name] = version(name)
    return {
        "format": 1,
        "sources": source_fingerprint(),
        "python": sys.implementation.name + "-" + ".".join(map(str, sys.version_info[:3])),
        "packages": packages,
    }


@lru_cache(maxsize=1)
def runtime_fingerprint():
    return canonical_hash(runtime_identity())


@lru_cache(maxsize=1)
def approved_adapter_digests():
    """Map this installed bundle to the historical contracts explicitly released for it."""
    try:
        approved = json.loads(APPROVAL.read_text(encoding="utf-8"))
        if approved["format"] == 1:
            digests = approved["fingerprints"][runtime_fingerprint()]["adapters"]
            if isinstance(digests, list) and all(isinstance(digest, str) for digest in digests):
                return frozenset(digests)
    except (OSError, ValueError, KeyError, TypeError, PackageNotFoundError):
        pass
    return frozenset()


def reviewed_runtime():
    return bool(approved_adapter_digests())
