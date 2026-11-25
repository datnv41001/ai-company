"""Frozen job inputs and an allowlisted broker for read-only synthetic evidence."""

import base64
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from pilot_fixture import digest, encoded
from review_plan import catalog
from union_cases import SEEDS, SEMANTICS

MODELS = {
    "q05": (
        "Qwen2.5-0.5B-Instruct-Q4_K_M",
        "9217f5db79a29953eb74d5343926648285ec7e67",
        "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db",
        "Qwen2.5",
    ),
    "q15": (
        "Qwen2.5-1.5B-Instruct-Q4_K_M",
        "91cad51170dc346986eccefdc2dd33a9da36ead9",
        "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e",
        "Qwen2.5",
    ),
    "smol": (
        "SmolLM2-1.7B-Instruct-Q4_K_M",
        "2d4a76a30b4af41ecd395c35725ac11688d4cfe4",
        "decd2598bc2c8ed08c19adc3c8fdd461ee19ed5708679d1c54ef54a5a30d4f33",
        "SmolLM2",
    ),
}
ROOT = Path(__file__).resolve().parent
RUNTIME = digest(encoded(json.loads((ROOT / "runtime-pins/windows-x64.json").read_bytes())))
PROFILES = {"common": "MK-022", "repeat": "MK-022", "specialist": "MK-052", "prompt": "MK-022", "split": "MK-022", "cross": "MK-053", "arb": "AR-002"}


def rotate(seq, offset):
    n = offset % len(seq)
    return seq[n:] + seq[:n]


def build(scope, group, seed, label):
    schema = {}
    packets = []
    for slot, c in enumerate(scope):
        ix = c["position"] + SEEDS.index(seed)
        sources = rotate(c["sources"], ix)
        choices = {
            "verdict": rotate(["defect", "clean", "unresolved"], ix),
            "citation": rotate([s["ref"] for s in sources] + ["none"], ix + 1),
            "reason": rotate(["agrees", "contradicts", "insufficient"], ix + 2),
            "operation": rotate(["keep", "request evidence", SEMANTICS[c["domain"]][4]], ix + 1),
        }
        schema[c["id"]] = {
            "type": "object",
            "properties": {k: {"enum": v} for k, v in choices.items()},
            "required": list(choices),
            "additionalProperties": False,
        }
        if ix % 2:
            packets.append(dict(unit=c["id"], subject=c["subject"], evidence=sources, copy=c["observation"], answers=choices))
        else:
            packets.append(dict(unit=c["id"], listing=[c["subject"], c["observation"]], approved_records=sources, answers=choices))
    spec = {"type": "object", "properties": schema, "required": list(schema), "additionalProperties": False}
    instructions = (
        "Check each synthetic listing against evidence for the identical product. Answer each unit independently. "
        "A conflict is a defect; evidence supporting the published claim is clean; missing relevant evidence is unresolved. "
        "Cite the matching record ID and choose an operation. Never use a sibling's record. "
    )
    if group == "prompt":
        instructions += "Identify the applicable source first, compare scope and meaning, then give the verdict."
    if group in ("cross", "arb"):
        instructions += "Inspect earlier signed opinions independently against the same underlying source. Correct, reject or abstain."
    profile = PROFILES[group]
    instructions += (
        " Your responsibility: "
        + {"MK-022": "marketing copy evidence.", "MK-052": "commercial offer accuracy.", "MK-053": "independent challenge.", "AR-002": "final arbitration."}[
            profile
        ]
    )
    # JSON preserves the alternative case presentations; sorting a user dictionary would erase ordering.
    return dict(
        model="airc-qwen-" + MODELS[label][2][:12],
        messages=[dict(role="system", content=instructions), dict(role="user", content=json.dumps(packets, ensure_ascii=False, separators=(",", ":")))],
        response_format={"type": "json_schema", "json_schema": {"name": "review", "strict": True, "schema": spec}},
        max_tokens=420 if len(scope) > 3 else 210,
        temperature=0.35,
        seed=seed + (31 if group in ("repeat", "specialist") else 0),
        stream=False,
        cache_prompt=False,
    )


def plan(rows, manifest, label, key):
    source = digest(encoded(manifest))
    jobs = []
    sem = [dict(r, position=i) for i, r in enumerate(r for r in rows if r["kind"] == "semantic")]
    for phasegroups in (("common", "repeat", "specialist", "prompt", "split"), ("cross",), ("arb",)):
        for seed in SEEDS:
            for group in phasegroups:
                if label != "q05" and group != "common":
                    continue
                size = 3 if group == "split" else 6
                for i in range(0, len(sem), size):
                    scope = sem[i : i + size]
                    reviewer = PROFILES[group]
                    chunk = i // size
                    peers = {"cross": ("common", "specialist"), "arb": ("common", "specialist", "cross")}.get(group, ())
                    units = [r["id"] for r in scope]
                    grant = {"read_units": units, "source_manifest": source, "tools": ["read_enrolled_fixture"]}
                    jobs.append(
                        dict(
                            assignment_id=f"{group}-{seed}-{chunk}",
                            reviewer_id=reviewer,
                            phase={"cross": "cross", "arb": "arbitration"}.get(group, "blind"),
                            artifact_kind=catalog()[1][reviewer]["artifact_kind"],
                            obligations=units,
                            principal="reviewer/" + reviewer,
                            source_manifest=source,
                            tool_grant_digest=digest(encoded(grant)),
                            model_key=key,
                            model_digest=MODELS[label][2],
                            runtime_digest=RUNTIME,
                            template=build(scope, group, seed, label),
                            peer_assignments=[f"{p}-{seed}-{chunk}" for p in peers],
                        )
                    )
    return dict(version=2, assignments=jobs, required_obligations=[r["id"] for r in sem])


def parse(raw, template):
    result = json.loads(raw)
    choice = result["choices"][0]
    if choice["finish_reason"] != "stop":
        raise ValueError("incomplete output")
    answer = json.loads(choice["message"]["content"])
    Draft202012Validator(template["response_format"]["json_schema"]["schema"]).validate(answer)
    return answer


def authorized_context(job, planned, attempts):
    payload = deepcopy(job["template"])
    prior = {}
    for aid in job["peer_assignments"]:
        a = next((a for a in attempts.values() if a["state"] == "accepted" and a["assignment"]["assignment_id"] == aid), None)
        if a is None:
            raise ValueError("missing required signed peer")
        source = next(j for j in planned["assignments"] if j["assignment_id"] == aid)
        answers = parse(base64.b64decode(a["output"], validate=True), source["template"])
        prior[aid] = {uid: answers[uid] for uid in job["obligations"] if uid in answers}
    if prior:
        payload["messages"].append({"role": "user", "content": encoded({"scoped_prior_opinions": prior}).decode()})
    return payload


def validate_enrolled_fixture(run, supplied, trust):
    """Only the enrolled safe fixture broker may authorize v2 template contents."""
    from union_cases import holdout, manifest

    if run["repository"] == "fixture/public-research-v4":
        from research_study import validate_fixture

        return validate_fixture(run, supplied, trust)
    if run["repository"] != "fixture/meridian-offers" or len(trust) != 1:
        raise ValueError("v2 admits only the fixed local fixture and one signer")
    rows, _ = holdout()
    source = manifest(rows)
    key, adapter = next(iter(trust.items()))
    label = next(
        (name for name, model in MODELS.items() if model == (adapter["model"], adapter["model_version"], adapter["model_digest"], adapter["family"])), None
    )
    if label is None or (run["base_sha"], run["head_sha"], run["source_manifest_digest"]) != (source["base"], source["head"], digest(encoded(source))):
        raise ValueError("source or model outside enrollment")
    if supplied != plan(rows, source, label, key):
        raise ValueError("approval differs from scoped source builder")
