"""Fetch the optional local demo weights and verify their immutable upstream digest."""

import hashlib
import os
from pathlib import Path
import tempfile

import httpx

URL = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_k_m.gguf"
DIGEST = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"


def main():
    target = Path(__file__).resolve().parents[1] / "models" / "workforce.gguf"
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        with target.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() == DIGEST:
                print("Verified", target)
                return
        raise SystemExit("Existing model differs from the expected weights; choose a separate checkout")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
        stage = Path(temp.name)
    try:
        digest = hashlib.sha256()
        with httpx.stream("GET", URL, follow_redirects=True, timeout=120) as response, stage.open("wb") as output:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != DIGEST:
            raise SystemExit("Unexpected model digest")
        stage.chmod(0o644)  # Public model weights must also be readable by the container user.
        os.replace(stage, target)
        print("Verified", target)
    finally:
        stage.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
