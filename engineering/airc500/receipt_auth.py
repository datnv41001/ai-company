"""AIRC receipt authentication. The verifier receives public trust material only."""

import base64
import binascii
import hashlib
import json
from datetime import datetime
from pathlib import Path

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = json.loads(Path(__file__).with_name("contracts.schema.json").read_text(encoding="utf-8"))
VALIDATORS = {
    name: Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": SCHEMA["$defs"]}, format_checker=FormatChecker())
    for name in ("run", "assignment", "receipt", "checkpoint")
}
BINDINGS = ("adapter_identity", "model", "model_version", "model_digest", "family")


def validate(kind, record):
    error = next(VALIDATORS[kind].iter_errors(record), None)
    if error:
        raise ValueError(f"invalid {kind} field at {list(error.path)}")


def instant(value):
    instant_ = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant_.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return instant_.timestamp()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def signed_message(receipt, headers):
    # Domain separation covers the protected header as well as the complete payload.
    payload = {k: v for k, v in receipt.items() if k != "signature"}
    return b"AMC-AIRC-RECEIPT\x00" + rfc8785.dumps({"header": headers, "payload": payload})


class Signer:
    def __init__(self, adapter_identity, private_key):
        self.adapter_identity = adapter_identity
        self._private_key = private_key
        public = private_key.public_key().public_bytes_raw()
        self.public_key = base64.b64encode(public).decode("ascii")
        self.key_id = digest(public)

    @classmethod
    def generate(cls, adapter_identity):
        return cls(adapter_identity, Ed25519PrivateKey.generate())

    def sign(self, receipt):
        if receipt.get("adapter_identity") != self.adapter_identity:
            raise ValueError("adapter identity differs")
        headers = {"key_id": self.key_id, "algorithm": "Ed25519", "signature_version": 1}
        value = self._private_key.sign(signed_message(receipt, headers))
        return {**receipt, "signature": {**headers, "value": base64.b64encode(value).decode("ascii")}}


def verify_signature(receipt, trust):
    validate("receipt", receipt)
    signature = receipt["signature"]
    key = trust.get(signature["key_id"])
    if not key or any(receipt[field] != key[field] for field in BINDINGS):
        raise ValueError("untrusted signing key or adapter/model binding")
    started, ended = instant(receipt["started_utc"]), instant(receipt["ended_utc"])
    if started > ended or ("not_before" in key and started < instant(key["not_before"])) or ("not_after" in key and ended > instant(key["not_after"])):
        raise ValueError("invalid receipt or key validity window")
    try:
        public = base64.b64decode(key["public_key"], validate=True)
        if digest(public) != signature["key_id"]:
            raise ValueError("key fingerprint differs")
        headers = {k: v for k, v in signature.items() if k != "value"}
        Ed25519PublicKey.from_public_bytes(public).verify(base64.b64decode(signature["value"], validate=True), signed_message(receipt, headers))
    except (InvalidSignature, binascii.Error, ValueError) as exc:
        raise ValueError("invalid receipt signature") from exc
