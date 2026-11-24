"""Translate immutable Qwen observations into schema records. Only the verifier sets final status."""

from pilot_fixture import COPY, FACTS, read_catalog
import json
from jsonschema import Draft202012Validator
from pilot_fixture import ROOT

WIRE = Draft202012Validator(json.loads((ROOT / "contracts.schema.json").read_bytes()))


def wire_records(rows, calls, manifest, assessment):
    catalog = read_catalog()
    units = {u["id"]: u for u in rows}
    result = []
    candidates = assessment["candidates"]

    def evidence(uid):
        row = units[uid]
        return [
            {
                "id": kind + "-" + uid,
                "kind": "pinned_blob",
                "locator": f"{path}#L{row['line']}",
                "digest": manifest["blobs"][manifest["head_sha"] + ":" + path]["sha256"],
                "excerpt_or_observation": row[key],
                "provenance": "Git blob at submitted head",
            }
            for kind, path, key in (("source", FACTS, "source"), ("copy", COPY, "observed"))
        ]

    def append(kind, body):
        body = {"type": kind + ".v1", **body}
        WIRE.validate(body)
        result.append(body)

    for call in calls:
        rid = call["reviewer_id"]
        shared = {k: manifest[k] for k in ("base_sha", "head_sha")}
        shared.update(run_id=call["run_id"], reviewer_id=rid, attempt_id=call["attempt_id"])
        answer = call["answer"]
        scope = list(answer)
        cite = [e for uid in scope for e in evidence(uid)]
        checks = [c for c in candidates if c["unit"] in scope]
        if call["phase"] == "blind":
            own = [c for c in checks if c["attempt_id"] == call["attempt_id"]]
            for c in own:
                fields = (
                    "model",
                    "model_version",
                    "family",
                    "finding_id",
                    "severity",
                    "location",
                    "location_note",
                    "expected",
                    "actual",
                    "business_impact",
                    "reproduction",
                    "evidence",
                    "proposed_fix",
                    "acceptance_criteria",
                )
                append(
                    "finding",
                    {
                        **shared,
                        **{k: c[k] for k in fields},
                        "evidence": c["submitted_evidence"],
                        "verification_status": "candidate",
                        "counterarguments": [],
                        "unresolved_disagreements": [],
                    },
                )
            append(
                "review",
                {
                    **shared,
                    "assignment_id": call["assignment_id"],
                    "phase": "blind",
                    "artifact_kind": catalog[rid]["output"]["artifact_kind"],
                    "proof_observation": " | ".join(answer[k]["reason"] for k in scope),
                    "scope_reviewed": scope,
                    "gaps": [k for k in scope if answer[k]["status"] == "insufficient"],
                    "finding_ids": [c["finding_id"] for c in own],
                    "evidence": cite,
                },
            )
        elif call["phase"] == "cross":
            # A clean control without a candidate remains an observation in the signed raw packet.
            for i, c in enumerate(checks):
                observation = answer[c["unit"]]
                append(
                    "exchange",
                    {
                        **shared,
                        "message_id": call["assignment_id"] + "-" + str(i),
                        "target_finding_id": c["finding_id"],
                        "round": 1,
                        "kind": {"conflict": "corroborate", "matches": "object", "insufficient": "request_evidence"}[observation["status"]],
                        "reason": observation["reason"],
                        "evidence": evidence(c["unit"]),
                        "supersedes": None,
                    },
                )
        else:
            for uid in scope:
                opinion = answer[uid]
                positions = [x["status"] + ": " + x["note"] for x in assessment["judgments"][uid]]
                checks_for_unit = [c for c in checks if c["unit"] == uid]
                refs = [c["finding_id"] for c in checks_for_unit]
                expected = "conflict" if units[uid]["source"] != units[uid]["observed"] else "matches"
                dissent = [s for s in positions if not s.startswith(expected + ":")]
                # The inference recommends a disposition; final verification is recorded by the separate oracle.
                append(
                    "arbitration",
                    {
                        **shared,
                        "finding_ids": refs,
                        "competing_positions": positions,
                        "artifact_kind": catalog[rid]["output"]["artifact_kind"],
                        "proof_observation": opinion["reason"],
                        "evidence": evidence(uid),
                        "disposition": {"matches": "rejected", "conflict": "candidate", "insufficient": "unresolved"}[opinion["status"]],
                        "reason": opinion["reason"],
                        "remaining_dissent": dissent,
                        "owner": "campaign copy owner",
                        "next_observation": "Re-read the pinned copy and approved field." if dissent else None,
                    },
                )
    return result
