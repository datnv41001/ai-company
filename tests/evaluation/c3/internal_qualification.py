"""C3 internal-task Qwen smoke and frozen, bounded component comparison on synthetic inputs."""

# ruff: noqa: E402 -- run_comparison sets the repository/test fixture import path.
import argparse
import hashlib
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
from time import monotonic
from uuid import uuid4

from run_comparison import CASES, ROOT, MarketingLab, app, dump, lab_client, run_one
from qualification import conditions
from agency_fixtures import postgres_api
from c3_task_fixtures import internal_workspace
from c3_fixtures import capture, prepared
from knowledge_fixtures import accepted, revision
from test_c3_internal_worker import InternalPool
from migrations.apply import publish_registry
from migrations.runtime_bundle import canonical_hash
from scripts.provision_pool import internal_route
from app import c3_assets, c3_skill_library, c3_studio
from app.workforce_gateway import GatewayError, infer

FROZEN = Path(__file__).with_name("qualification-v2.json")
FROZEN_HASH = "993f93551657734fbea73f6c8898633a18df9dd573fcd0ff78b5e01653bc3346"


def prepare_task(lab, case, owner, base, client, brand, campaign, workflow):
    headers = owner["headers"]
    research = workflow == c3_assets.RESEARCH
    intent = {k: case[k] for k in ("product", "audience", "region", "locale", "channel", "buyer_action", "editorial_style")}
    intent.update(
        purpose=case["objective"],
        deliverable_type="marketing_strategy" if research else "landing_page",
        requirements=[case["cta"]],
        exclusions=[case["unsupported_example"]],
        acceptance_criteria=["Giúp người mua thực hiện đúng bước tiếp theo trong phạm vi đã duyệt."],
    )
    task = accepted(lab.api.post(base + "/workforce/internal-tasks", headers=headers, json={"key": str(uuid4()), "campaign_id": campaign, "intent": intent}))
    assert task["origin"] == "internal"
    inputs = deepcopy(case)
    for fact in inputs["facts"]:
        fact["qualifiers"] = [fact["qualifiers"]]
    state = prepared(lab.api, owner, base, client, brand, campaign, task["id"], workflow, case=inputs)
    guide = revision(
        lab.api,
        owner,
        state["path"],
        "qualification-style",
        "guidelines",
        {"guidance": "Dùng câu cụ thể và có căn cứ.", "tone": "Điềm tĩnh", "prohibited_claims": [case["unsupported_example"]]},
    )
    state["params"]["guidelines"] = guide["id"]
    snap = capture(lab.api, owner, state)
    assert snap["projection"]["brand_guidelines"]["digest"] == guide["digest"]
    assert snap["projection"]["task_intent"]["buyer_action"] == case["buyer_action"]
    return task["id"], snap, None


def seed_internal(lab, case, recovery):
    owner, base, client, brand, campaign = internal_workspace(lab.api)
    lab.cases.append((base, owner, None, client, campaign))
    lab.configure(owner, 10000)
    lab.case = case
    research = case["workflow"] == "WF-03"
    workflow = c3_assets.RESEARCH if research else c3_assets.LANDING
    filename = "research-strategy-v3.json" if research else "landing-seo-v6.json"
    definition = json.loads((ROOT / "catalog" / filename).read_bytes())
    with lab.owner.transaction():
        internal_route(lab.owner, lab.worker_name, owner["tenant"], client, brand, campaign)
        publish_registry(lab.owner, definition)
    headers = owner["headers"]
    lab.api.put(
        base + "/workforce/registry/" + campaign, headers=headers, json={"workflow": workflow, "skills": definition["required"], "action": "activate"}
    ).raise_for_status()
    if recovery:
        from recovery_fixture import prepare_recovered

        recovered = prepare_recovered(lab.api, case, owner, base, client, brand, campaign)
        task_id, snap, correction = recovered["task_id"], recovered["manifest"], recovered["correction"]
        assert recovered["workflow"] == workflow
    else:
        task_id, snap, correction = prepare_task(lab, case, owner, base, client, brand, campaign, workflow)
    projection = snap["projection"]
    run = accepted(
        lab.api.post(
            base + "/workforce/briefs/" + task_id + "/run",
            headers=headers,
            json={
                "registry_workflow": workflow,
                "workflow": "dynamic-v1",
                "budget_microusd": 10000,
                "knowledge_manifest": {"id": snap["id"], "digest": snap["digest"]},
            },
        )
    )
    return run["id"], workflow, task_id, projection, definition, correction


def instruction_control(lab, request, treatment, projection, workflow, native):
    """Hold the exact role input, constrained schema, weights, and assembly constant."""
    control = deepcopy(request)
    control["messages"][0]["content"] = (
        "Use the selected locale. Complete the required fields from supplied facts. Never invent factual claims. Use only supplied evidence handles."
    )
    assert control["messages"][1:] == request["messages"][1:]
    actual_worker_digest = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert actual_worker_digest == treatment["request_sha256"]
    role = "strategy" if workflow == c3_assets.RESEARCH else "content"
    result = {
        "scope": role,
        "max_invocations": 1,
        "provider_fee_usd": 0,
        "model": request["model"],
        "same_user_input_digest": canonical_hash(request["messages"][1:]),
        "schema_digest": canonical_hash(request["response_format"]),
        "control_schema_digest": canonical_hash(control["response_format"]),
        "control_user_input_digest": canonical_hash(control["messages"][1:]),
        "treatment_attempt_request_sha256": actual_worker_digest,
        "control_request_digest": canonical_hash(control),
        "treatment_request_digest": canonical_hash(request),
        "paired_treatment_attempt_id": treatment["attempt_id"],
    }
    start = monotonic()
    try:
        output, n_in, n_out = infer(lab.config, control)
        result.update(raw_output=output, input_tokens=n_in, output_tokens=n_out)
        sources = {f["id"]: f for f in projection["facts"]}
        contract = c3_skill_library.validate(output, role, {}, sources)
        groups = c3_studio.compose(workflow, projection, native | {role: contract})
        result.update(groups=groups, field_findings=c3_studio.quality_issues(workflow, groups, projection))
    except GatewayError as exc:
        result["error"] = str(exc)
        if exc.usage:
            result.update(input_tokens=exc.usage[1], output_tokens=exc.usage[2])
    result["seconds"] = round(monotonic() - start, 3)
    return result


def edit_studio(api, uri, headers, workflow, case):
    before = accepted(api.get(uri + "/studio", headers=headers))
    groups = deepcopy(before["groups"])
    key = "strategy" if workflow == c3_assets.RESEARCH else "seo"
    field = "positioning" if key == "strategy" else "meta_description"
    assert field in groups[key]
    groups[key][field] = f"{case['product']} tại {case['region']}. {case['cta']}."
    saved = accepted(api.patch(uri + "/studio", headers=headers, json={"expected_revision": before["revision"], "groups": groups}))
    doc = accepted(api.get(uri, headers=headers))
    assert saved["groups"] == groups and saved["revision"] == before["revision"] + 1 == doc["qa_revision"]
    assert doc["qa_evidence"]["content_evidence"]["qa_revision"] == doc["qa_revision"]
    return {"kind": "scripted staff edit", "field": [key, field], "before": before, "after": saved, "qa_evidence": doc["qa_evidence"]}


def run_internal(api, case, url, folder, study, recovery):
    start = monotonic()
    lab = InternalPool(api, os.environ["AMC_MIGRATION_DSN"])
    try:
        lab.config = replace(lab.config, url=url, model=os.getenv("AMC_WORKFORCE_MODEL", "amc-local"))
        rid, workflow, task_id, projection, definition, correction = seed_internal(lab, case, recovery)
        baseline = c3_studio.compose(workflow, projection, {})
        requests = {}
        record = run_one(lab, case["workflow"], "improved", folder, queued=(rid, workflow), request_log=requests)
        record.update(
            task_id=task_id,
            origin="internal",
            task_intent=projection["task_intent"],
            guideline=projection["brand_guidelines"],
            correction=correction,
            projection_digest=canonical_hash(projection),
            skill_digests={k: c3_skill_library.method_digest(v) for k, v in definition["marketing_methods"].items()},
            deterministic={"model_calls": 0, "groups": baseline, "field_findings": c3_studio.quality_issues(workflow, baseline, projection)},
        )
        if record.get("deliverable"):
            base, admin, *_ = lab.cases[0]
            staff = accepted(api.get(base + "/workforce/runs/" + rid, headers=admin["headers"]))
            native = {entry["skill"]: entry["output"] for entry in staff["checkpoints"]}
            assert record["skill_digests"] == {k: v for step in native.values() for k, v in step.get("marketing_skills", {}).items()}
            composed = c3_studio.compose(workflow, projection, native)
            record["composed"] = {"groups": composed, "field_findings": c3_studio.quality_issues(workflow, composed, projection)}
            record["staff"] = staff["marketing_artifacts"]
            doc = record["deliverable"]
            record["edited_example"] = edit_studio(api, base + "/deliverables/" + doc["id"], admin["headers"], workflow, case)
            if not study and not recovery and os.getenv("AMC_LIVE_STUDIO_SCREENSHOTS"):
                from browser_marketing_studio import capture_live

                with postgres_api() as server:
                    capture_live(str(server.base_url).rstrip("/"), admin, rid, workflow, folder / "browser")
            if study:
                stage = "strategy" if workflow == c3_assets.RESEARCH else "content"
                success = next(a for a in reversed(record["attempts"]) if a["schema"] == "c3_skills_" + stage and "raw_output" in a)
                record["matched_instruction_control"] = instruction_control(lab, requests[success["attempt_id"]], success, projection, workflow, native)
        record["automated_journey_seconds"] = round(monotonic() - start, 3)
        return record
    finally:
        lab.release_connections()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--study", action="store_true")
    mode.add_argument("--recovery", action="store_true")
    args = parser.parse_args()
    source = FROZEN if args.study else CASES.with_name("holdout-v1.json") if args.recovery else CASES
    meta, url = conditions(source)
    cases = json.loads(source.read_bytes())["cases"]
    if args.study:
        if meta["cases_sha256"] != FROZEN_HASH or len(cases) != 10:
            raise ValueError("Frozen case set mismatch.")
    elif args.recovery:
        assert meta["cases_sha256"] == "c497ff707c986acaa3c48ba799ab1a378f194d3e7cd4262834d41a4aae0fe477"
        cases = [c for c in cases if c["persona"] in ("service", "inhouse")]
        assert len(cases) == 20
    else:
        smoke = {"materials": ("WF-03", "rfq"), "seller": ("WF-13", "purchase")}
        cases = [dict(c, workflow=smoke[c["id"]][0], buyer_action=smoke[c["id"]][1], editorial_style="plain") for c in cases if c["id"] in smoke]
    args.out.mkdir(parents=True, exist_ok=False)
    dump(args.out / "conditions.json", meta)
    pins = {}
    for case in cases:
        with lab_client(app) as api:
            folder = args.out / case["id"]
            folder.mkdir()
            record = run_internal(api, case, url, folder, args.study, args.recovery)
            dump(folder / "result.json", meta | record)
            pins.update(record["skill_digests"])
            print(case["id"], record["workflow"], record["state"], len(record["attempts"]), flush=True)
            if not args.study and not args.recovery:
                assert record["state"] == "awaiting_qa" and record["origin"] == "internal" and len(record["staff"]["sections"]) == 7
                assert record["runtime_fingerprint"] and record["deliverable"]["assessment"]["content_evidence"]
                assert record["input_tokens"] and record["output_tokens"] and record["unmetered_attempts"] == 0
        if args.study:
            with lab_client(app) as reference_api:
                legacy = MarketingLab(reference_api, os.environ["AMC_MIGRATION_DSN"], case)
                try:
                    legacy.config = replace(legacy.config, url=url, model=os.getenv("AMC_WORKFORCE_MODEL", "amc-local"))
                    other = folder / "previous"
                    other.mkdir()
                    dump(other / "result.json", meta | run_one(legacy, case["workflow"], "projected", other))
                finally:
                    legacy.close()
    assert len(pins) == 7
    dump(args.out / "skill-digests.json", pins)


if __name__ == "__main__":
    main()
