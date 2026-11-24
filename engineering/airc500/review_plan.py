"""Versioned admission plan and independently signed evidence observations."""

import base64
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
import rfc8785

CATALOG = Path(__file__).with_name("reviewers.jsonl")
PURPOSE = b"AMC-AIRC-OBLIGATION-v1\x00"
HEX = re.compile("[0-9a-f]{64}")


def plan_digest(plan):
    return sha256(rfc8785.dumps(plan)).hexdigest()


@lru_cache(maxsize=1)
def catalog():
    raw = CATALOG.read_text(encoding="utf-8").encode()
    return sha256(raw).hexdigest(), {r["reviewer_id"]: r["output"] for r in map(json.loads, raw.splitlines())}


def nonempty_ids(items):
    return isinstance(items, list) and bool(items) and all(isinstance(i, str) and 0 < len(i) <= 200 for i in items) and len(set(items)) == len(items)


def validate_plan(run, plan, verifier_key, trust):
    catalog_digest, profiles = catalog()
    if (
        catalog_digest != run["catalog_digest"]
        or set(plan) != {"version", "assignments", "required_obligations"}
        or plan["version"] != 1
        or not nonempty_ids(plan["required_obligations"])
    ):
        raise ValueError("invalid plan or catalog pin")
    verifier_bytes = base64.b64decode(verifier_key, validate=True)
    Ed25519PublicKey.from_public_bytes(verifier_bytes)
    if sha256(verifier_bytes).hexdigest() in trust:
        raise ValueError("adapter may not verify its own outputs")
    jobs = plan["assignments"]
    if not isinstance(jobs, list) or not nonempty_ids([j["assignment_id"] for j in jobs]):
        raise ValueError("invalid or duplicate planned assignment")
    scoped = set()
    for j in jobs:
        if set(j) != {"assignment_id", "reviewer_id", "phase", "artifact_kind", "obligations"}:
            raise ValueError("missing or unexpected plan field")
        profile = profiles.get(j["reviewer_id"])
        if (
            not profile
            or profile["artifact_kind"] != j["artifact_kind"]
            or not nonempty_ids(j["obligations"])
            or j["phase"] not in ("blind", "cross", "arbitration")
            or (j["phase"] == "arbitration") != j["reviewer_id"].startswith("AR-")
        ):
            raise ValueError("invalid planned reviewer, phase, scope or deliverable")
        scoped.update(j["obligations"])
    if scoped != set(plan["required_obligations"]):
        raise ValueError("obligations and assignment scopes differ")


def planned_job(plan, ass):
    found = next((j for j in plan["assignments"] if j["assignment_id"] == ass["assignment_id"]), None)
    if (
        not found
        or any(found[k] != ass[k] for k in ("reviewer_id", "phase", "artifact_kind"))
        or ass["output_contract"] != catalog()[1][ass["reviewer_id"]]["contract"]
    ):
        raise ValueError("assignment differs from admitted plan")
    return found


class EvidenceSigner:
    def __init__(self, key):
        self._key = key
        self.public_key = base64.b64encode(key.public_key().public_bytes_raw()).decode()

    @classmethod
    def generate(cls):
        return cls(Ed25519PrivateKey.generate())

    def attest(self, run_id, plan_digest, assignment_id, obligation_id, output_digest, evidence_digest, disposition):
        body = dict(
            run_id=run_id,
            plan_digest=plan_digest,
            assignment_id=assignment_id,
            obligation_id=obligation_id,
            output_digest=output_digest,
            evidence_digest=evidence_digest,
            disposition=disposition,
        )
        return {**body, "signature": base64.b64encode(self._key.sign(PURPOSE + rfc8785.dumps(body))).decode()}


def verify_evidence(state, signed):
    body = {k: v for k, v in signed.items() if k != "signature"}
    if (
        set(body) != {"run_id", "plan_digest", "assignment_id", "obligation_id", "output_digest", "evidence_digest", "disposition"}
        or body["run_id"] != state.manifest["run_id"]
        or body["plan_digest"] != plan_digest(state.plan)
        or body["disposition"] not in ("verified", "insufficient", "rejected")
        or not HEX.fullmatch(body["evidence_digest"])
    ):
        raise ValueError("invalid evidence identity, disposition or source digest")
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(state.verifier_key, validate=True))
        key.verify(base64.b64decode(signed["signature"], validate=True), PURPOSE + rfc8785.dumps(body))
    except (InvalidSignature, KeyError, ValueError) as exc:
        raise ValueError("untrusted evidence observation") from exc
    a = next((a for a in state.attempts.values() if a["state"] == "accepted" and a["assignment"]["assignment_id"] == body["assignment_id"]), None)
    if not a or a["receipt"]["output_digest"] != body["output_digest"] or body["obligation_id"] not in planned_job(state.plan, a["assignment"])["obligations"]:
        raise ValueError("observation outside accepted scoped artifact")
    pair = (body["assignment_id"], body["obligation_id"])
    if state.cancelled or pair in state.observations:
        raise ValueError("fenced or duplicate evidence observation")


def coverage_report(state):
    if not state.plan:
        raise ValueError("historical run has no admitted plan")
    required = {j["assignment_id"] for j in state.plan["assignments"]}
    accepted = {a["assignment"]["assignment_id"] for a in state.attempts.values() if a["state"] == "accepted"}
    obligations = set(state.plan["required_obligations"])
    verified = {r["obligation_id"] for r in state.observations.values() if r["disposition"] == "verified"}
    complete = bool(state.seal) and required == accepted and obligations == verified and not state.cancelled and not state.overspent
    return {
        "execution": {"required": len(required), "accepted": len(accepted), "missing": sorted(required - accepted)},
        "evidence": {"required": len(obligations), "verified": len(verified), "missing": sorted(obligations - verified)},
        "quality": "separately_measured",
        "decision": "covered" if complete else "inconclusive",
    }
