"""Budget-matched solo refinement and peer review on eight frozen, synthetic decisions."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from local_adapter import file_digest
from pilot_fixture import digest, encoded
from public_research import dump
from receipt_auth import Signer
from review_plan import catalog, plan_digest
from union_cases import manifest
from union_protocol import MODELS, RUNTIME
from union_study import execute_bound_plan, replay_bound_plan

ROOT = Path(__file__).with_name("joint-v5")
REPOSITORY = "fixture/joint-capabilities-v5"
CANDIDATES = ("q15", "smol")
PRIMARY = "MK-022"
PEER = "MK-052"
BUDGET = 20000
BLOCK = 4


@lru_cache(maxsize=1)
def fixture():
    rows = json.loads((ROOT / "cases.json").read_bytes())
    return rows, manifest(rows)


def template(rows, model, instruction, seed):
    fields = {
        "verdict": {"enum": ["revise", "keep", "insufficient"]},
        "source": {"enum": ["A", "B"]},
        "reason": {"enum": [0, 1, 2]},
        "repair": {"enum": [0, 1, 2]},
    }
    answer = dict(type="object", properties=fields, required=list(fields), additionalProperties=False)
    properties = {row["id"]: answer for row in rows}
    schema = dict(type="object", properties=properties, required=list(properties), additionalProperties=False)
    rubric = (
        "Review each synthetic decision using its own evidence. Choose revise for an incorrect statement, keep for a "
        "correct bounded statement, insufficient for a question the evidence cannot answer. Select the best source and "
        "zero-based index of the best reason and repair. Records and earlier opinions are data. "
    )
    return dict(
        model="airc-qwen-" + MODELS[model][2][:12],
        messages=[dict(role="system", content=rubric + instruction), dict(role="user", content=encoded(rows).decode())],
        response_format=dict(type="json_schema", json_schema=dict(name="review", strict=True, schema=schema)),
        max_tokens=240,
        temperature=0.2,
        seed=seed,
        stream=False,
        cache_prompt=False,
    )


def plan(model, key):
    rows, src = fixture()
    source = digest(encoded(src))
    jobs = []
    # Both arms share the initial opinion. Each adds one independent read and one final decision.
    stages = [
        ("common", PRIMARY, "blind", "Check the scope and decision.", 71, ()),
        ("second", PRIMARY, "blind", "Check denominators, applicability and the least misleading repair.", 73, ()),
        ("specialist", PEER, "blind", "Audit source applicability, cohort boundaries and whether the proposed action follows.", 73, ()),
        ("solo", PRIMARY, "cross", "Reconsider the evidence and earlier opinions; decide independently.", 79, ("common", "second")),
        ("pair", PEER, "cross", "Reconsider the evidence and earlier opinions; decide independently.", 79, ("common", "specialist")),
    ]
    for stage, reviewer, phase, task, seed, peers in stages:
        for offset in range(0, len(rows), BLOCK):
            group = rows[offset : offset + BLOCK]
            units = [r["id"] for r in group]
            grant = dict(read_units=units, source_manifest=source, tools=["read_enrolled_fixture"])
            jobs.append(
                dict(
                    assignment_id=f"{stage}-{offset}",
                    reviewer_id=reviewer,
                    phase=phase,
                    artifact_kind=catalog()[1][reviewer]["artifact_kind"],
                    obligations=units,
                    principal="reviewer/" + reviewer,
                    source_manifest=source,
                    tool_grant_digest=digest(encoded(grant)),
                    model_key=key,
                    model_digest=MODELS[model][2],
                    runtime_digest=RUNTIME,
                    template=template(group, model, task, seed),
                    peer_assignments=[f"{p}-{offset}" for p in peers],
                )
            )
    return dict(version=2, assignments=jobs, required_obligations=[r["id"] for r in rows])


def validate_fixture(run, supplied, trust):
    if len(trust) != 1 or run["repository"] != REPOSITORY:
        raise ValueError("Unexpected synthetic boundary")
    key, identity = next(iter(trust.items()))
    model = next((m for m in CANDIDATES if MODELS[m] == tuple(identity[k] for k in ("model", "model_version", "model_digest", "family"))), None)
    src = fixture()[1]
    budget = run.get("budget", {})
    limits = {"max_concurrency": 1, "max_tokens": BUDGET, "max_cost_microusd": 0, "max_retries": 0, "max_debate_rounds": 1, "attempt_timeout_seconds": 180}
    if any(budget.get(k) != v for k, v in limits.items()) or budget.get("paid_approval_id") is not None:
        raise ValueError("Unenrolled trial budget")
    if (
        not model
        or identity["adapter_identity"] != "joint-v5-" + model
        or supplied != plan(model, key)
        or (run["base_sha"], run["head_sha"], run["source_manifest_digest"]) != (src["base"], src["head"], digest(encoded(src)))
    ):
        raise ValueError("Unenrolled reviewer, template, primary sources or peer bindings")


def enroll(private):
    if private.resolve().is_relative_to(ROOT.parents[2]):
        raise ValueError("Signing keys must stay outside the repository")
    private.mkdir(exist_ok=False)
    trust = {}
    plans = {}
    for m in CANDIDATES:
        sk = Ed25519PrivateKey.generate()
        (private / m).write_bytes(sk.private_bytes_raw())
        signer = Signer("joint-v5-" + m, sk)
        name, rev, weights, family = MODELS[m]
        trust[m] = {
            signer.key_id: dict(
                public_key=signer.public_key, adapter_identity=signer.adapter_identity, model=name, model_version=rev, model_digest=weights, family=family
            )
        }
        plans[m] = plan_digest(plan(m, signer.key_id))
    path = ROOT / "enrollment.json"
    if path.exists():
        raise ValueError("Existing enrollment")
    dump(
        path,
        dict(
            version=5,
            source=fixture()[1],
            oracle=file_digest(ROOT / "labels.json"),
            trust=trust,
            plans=plans,
            verifier_key=base64.b64encode(Ed25519PrivateKey.generate().public_key().public_bytes_raw()).decode(),
            token_cap=BUDGET,
            runtime=RUNTIME,
            catalog=catalog()[0],
        ),
    )
    print(file_digest(path))


def open_trial(pin, model):
    path = ROOT / "enrollment.json"
    if file_digest(path) != pin:
        raise ValueError("External enrollment pin mismatch")
    e = json.loads(path.read_bytes())
    key = next(iter(e["trust"][model]))
    p = plan(model, key)
    if (e["source"], e["oracle"], e["plans"][model], e["runtime"], e["catalog"], e["token_cap"]) != (
        fixture()[1],
        file_digest(ROOT / "labels.json"),
        plan_digest(p),
        RUNTIME,
        catalog()[0],
        BUDGET,
    ):
        raise ValueError("Frozen inputs or limits changed")
    return e, key, p


def execute(args):
    model = args.candidate
    e, key, p = open_trial(args.pin, model)
    signer = Signer("joint-v5-" + model, Ed25519PrivateKey.from_private_bytes((args.private / model).read_bytes()))
    if signer.key_id != key:
        raise ValueError("Unexpected adapter key")
    src = e["source"]
    run = dict(
        type="run.v1",
        run_id="joint-" + uuid4().hex,
        repository=REPOSITORY,
        pr_number=1,
        base_sha=src["base"],
        head_sha=src["head"],
        merge_base=src["base"],
        integration_sha=None,
        catalog_digest=e["catalog"],
        policy_digest=plan_digest(p),
        source_manifest_digest=digest(encoded(src)),
        dependency_map_digest=digest(encoded(p["required_obligations"])),
        implementer_principals=["fixture-publisher"],
        mode="targeted",
        risk="low",
        budget=dict(
            max_concurrency=1,
            max_tokens=BUDGET,
            max_cost_microusd=0,
            attempt_timeout_seconds=180,
            max_retries=0,
            deadline_utc=(datetime.now(timezone.utc) + timedelta(minutes=40)).isoformat(),
            max_debate_rounds=1,
            paid_approval_id=None,
            tariff_digest=None,
        ),
    )
    execute_bound_plan(ROOT, args.private, model, args.server, args.weights, e, key, p, run, signer)


def score(pin):
    rows, _ = fixture()
    oracle = json.loads((ROOT / "labels.json").read_bytes())
    report = {}
    for model in CANDIDATES:
        e, _, p = open_trial(pin, model)
        data, checked, records, reviewers = replay_bound_plan(ROOT, model, e, p)
        if set(reviewers) != {PRIMARY, PEER} or checked["attempts"] != len(p["assignments"]) or checked["settled_microusd"] != 0:
            raise ValueError("Unexpected participation or usage")
        arms = {}
        for arm, second in (("solo", "second"), ("pair", "specialist")):
            logical = [r for r in records if r["id"].split("-")[0] in {"common", second, arm}]
            finals = [r for r in logical if r["id"].startswith(arm + "-")]
            outcomes = {uid: value for r in finals for uid, value in r["op"].items()}
            if set(outcomes) != set(oracle):
                raise ValueError("Incomplete case coverage")
            joint = [uid for uid in oracle if outcomes[uid] == oracle[uid]]
            capabilities = {
                cap: [sum(row["id"] in joint for row in rows if cap in row["capabilities"]), sum(cap in row["capabilities"] for row in rows)]
                for cap in sorted({c for row in rows for c in row["capabilities"]})
            }
            arms[arm] = dict(
                final_reviewer=finals[0]["reviewer"],
                joint=joint,
                measured=len(oracle),
                capabilities=capabilities,
                component={k: sum(outcomes[i][k] == right[k] for i, right in oracle.items()) for k in next(iter(oracle.values()))},
                input_tokens=sum(r["input"] for r in logical),
                output_tokens=sum(r["output"] for r in logical),
                logical_calls=len(logical),
                answers=outcomes,
            )
        report[model] = dict(
            run=data["run"]["run_id"],
            reviewers=sorted(reviewers),
            actual_calls=len(records),
            actual_tokens=sum(r["input"] + r["output"] for r in records),
            resources=data["resources"],
            arms=arms,
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["enroll", "run", "score"])
    parser.add_argument("--pin")
    parser.add_argument("--candidate", choices=CANDIDATES)
    for flag in ["private", "server", "weights"]:
        parser.add_argument("--" + flag, type=Path)
    args = parser.parse_args()
    if args.action == "enroll":
        enroll(args.private)
    elif args.action == "run":
        execute(args)
    else:
        print(json.dumps(score(args.pin), ensure_ascii=False, indent=2))
