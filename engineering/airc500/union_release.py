"""Reviewed trust anchors live outside the evidence directory. All results are recomputed."""

import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
from pathlib import Path

from pilot_fixture import digest, encoded
from union_protocol import MODELS
from union_study import results

ENROLLMENT = "030e8730c357b8b7ab659b9bd54c04241d53098d00eaa5cab1264efc34997537"
INDEX = "ed3b34db683d7c710bba58799cfab8367f767552ab488bc770500536bfbdd1b3"
RELEASE_KEY = "B0nFeodXdV8XpmWUKWDOLVb594tcG316eH0PFjaGtGg="
NAMES = {"enrollment.json", "metrics.json", "verification.json", "no-capacity-preflight.json", *(label + ".json.gz" for label in MODELS)}


def index(path):
    return {name: digest((path / name).read_bytes()) for name in sorted(NAMES)}


def certificate(path, metrics):
    return dict(
        purpose="AMC verified fixture union v3",
        preflight_digest=digest((path / "no-capacity-preflight.json").read_bytes()),
        enrollment=ENROLLMENT,
        scores_sha256=digest(encoded(metrics)),
        output_journals={label: digest((path / (label + ".json.gz")).read_bytes()) for label in MODELS},
        scope="synthetic fixture only",
        authority="local engineering verification",
    )


def attest(path, private_key, enrollment_pin=ENROLLMENT):
    """Separate local verification invocation. It reads the model output archives without adapter signing keys."""
    if private_key.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("private key must be outside checkout")
    if digest((path / "enrollment.json").read_bytes()) != enrollment_pin:
        raise ValueError("unexpected enrollment")
    from quality_run import save

    key = Ed25519PrivateKey.from_private_bytes(private_key.read_bytes())
    if base64.b64encode(key.public_key().public_bytes_raw()).decode() != RELEASE_KEY:
        raise ValueError("unregistered verification key")
    metrics = results(path, enrollment_pin)
    body = certificate(path, metrics)
    save(path / "metrics.json", metrics)
    save(path / "verification.json", dict(body=body, signature=base64.b64encode(key.sign(encoded(body))).decode()))
    save(path / "index.json", index(path))
    return digest((path / "index.json").read_bytes())


def verify_release(path, index_pin=INDEX, enrollment_pin=ENROLLMENT):
    path = Path(path)
    raw = (path / "index.json").read_bytes()
    if index_pin != INDEX or enrollment_pin != ENROLLMENT or digest(raw) != INDEX or json.loads(raw) != index(path):
        raise ValueError("wrong released evidence package")
    metrics = results(path, enrollment_pin)
    if json.loads((path / "metrics.json").read_bytes()) != metrics:
        raise ValueError("reported scores differ from signed outputs")
    cert = json.loads((path / "verification.json").read_bytes())
    if cert["body"] != certificate(path, metrics):
        raise ValueError("certificate does not bind these outputs")
    Ed25519PublicKey.from_public_bytes(base64.b64decode(RELEASE_KEY)).verify(base64.b64decode(cert["signature"], validate=True), encoded(cert["body"]))
    return metrics


if __name__ == "__main__":
    import sys

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "evidence/union-v3"
    print(encoded({k: {"calls": r["calls"], "input": r["input_tokens"], "output": r["output_tokens"]} for k, r in verify_release(path).items()}).decode())
