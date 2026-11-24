"""Verify a real Qwen planner, specialists and approved registry snapshot."""

from dataclasses import replace
import json
import os
from pathlib import Path
import time
import subprocess

from fastapi.testclient import TestClient
from app.main import app
from app.workforce_gateway import GatewayError, infer
from app.pool_worker import report
from pool_lab import Lab
from pool_model_smoke import receipts
from test_registry import policy, registry_brief
from test_adapter_rollout import second_release
from dispatcher_build import turn
from test_role_qa_rollout import activate_qa, WORKFLOW as QA_WORKFLOW
from migrations.runtime_bundle import canonical_hash
from app.registry_adapters import V1_DIGEST, seo_v2_digest
from migrations.apply import publish_registry
from migrations.runtime_bundle import reviewed_runtime, runtime_fingerprint, runtime_identity


def drive(lab, rid, config, *, old_checkout=None, after_content=None, seo_v2=False):
    deadline = time.monotonic() + 360
    switch = None
    while time.monotonic() < deadline and lab.states()[0] in ("queued", "running"):
        for worker in lab.workers:
            job = worker.take()
            if job:
                assert job["run"] == rid
                if job["body"]["response_format"]["json_schema"]["name"] == "seo":
                    assert ("literal search query" in job["body"]["messages"][0]["content"]) == seo_v2
                try:
                    result = infer(config, job["body"])
                    assert report(worker.conn, job, list(result))
                except GatewayError as exc:
                    assert report(worker.conn, job, result=exc.usage, error=str(exc))
        if old_checkout and switch is None:
            probe = turn(old_checkout, lab, "consume")
            assert probe["digest"] == V1_DIGEST
            details = read_run(lab, rid)
            if any(cp["skill"] == "content" for cp in details["checkpoints"]):
                assert details["state"] == "queued" and not details["deliverable_id"]
                switch = {k: details["registry"][k] for k in ("workflow", "plan_digest", "manifest_digest")}
                after_content()
            else:
                turn(old_checkout, lab, "dispatch")
        elif not lab.consume() and not lab.dispatch():
            time.sleep(0.1)
    assert lab.states() == ["awaiting_qa"]
    if old_checkout:
        assert switch is not None
        assert all(read_run(lab, rid)["registry"][k] == v for k, v in switch.items())
    return switch


def read_run(lab, rid):
    return lab.api.get(lab.cases[0][0] + "/workforce/runs/" + rid, headers=lab.x["headers"]).json()


def verify():
    assert reviewed_runtime()
    with TestClient(app) as api:
        lab = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow="dynamic-v1")
        try:
            lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=any(%s)", (lab.runs,))
            policy(lab, "activate").raise_for_status()
            path, terms = registry_brief(lab)
            queued = api.post(path, json=terms, headers=lab.x["headers"])
            queued.raise_for_status()
            rid = queued.json()["id"]
            lab.runs = [rid]
            config = replace(lab.config, url=os.environ["AMC_LOCAL_MODEL_URL"])
            old = os.getenv("AMC_V1_SOURCE")
            if old:
                prior_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=old, text=True).strip()
                assert prior_sha == "bae0ddeb1df5a922c82f6d5c9a2b09e46eeee728"
            release2 = second_release(version=2)

            def deploy():
                with lab.owner.transaction():
                    publish_registry(lab.owner, release2)
                endpoint = lab.cases[0][0] + "/workforce/registry/" + lab.cases[0][-1]
                api.put(
                    endpoint, headers=lab.x["headers"], json={"workflow": release2["workflow_id"] + "@2", "skills": release2["required"], "action": "activate"}
                ).raise_for_status()

            switch = drive(lab, rid, config, old_checkout=old, after_content=deploy)
            results = receipts(lab, [(rid, lab.cases[0], "Registry")])
            Path("registry-measurements.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
            assert lab.states() == ["awaiting_qa"]
            details = api.get(lab.cases[0][0] + "/workforce/runs/" + rid, headers=lab.x["headers"]).json()
            assert details["approved_assets"] and details["registry"]["plan_digest"] == details["graph"]["digest"]
            assert {"director", "content", "seo"} == {n["skill_id"] for n in details["registry"]["nodes"]}
            assert all(n["attempt_ids"] for n in details["registry"]["nodes"])
            if old:
                path, terms = registry_brief(lab)
                queued = api.post(path, json={**terms, "registry_workflow": release2["workflow_id"] + "@2"}, headers=lab.x["headers"])
                queued.raise_for_status()
                new = queued.json()["id"]
                lab.runs = [new]
                drive(lab, new, config, seo_v2=True)
                new_receipt = receipts(lab, [(new, lab.cases[0], "Registry v2")])
                current = read_run(lab, new)
                assert current["approved_assets"] and current["deliverable_id"] != details["deliverable_id"]
                evidence = {
                    "source_before": prior_sha,
                    "source_after": os.environ["AMC_SOURCE_SHA"],
                    "runtime_fingerprint": runtime_fingerprint(),
                    "runtime_identity": runtime_identity(),
                    "cutover_after": "content",
                    "before": switch,
                    "v1_runtime": "seo@1",
                    "v2_runtime": "seo@2",
                    "v1_adapter_digest": V1_DIGEST,
                    "v2_adapter_digest": seo_v2_digest(),
                    "v1_completed": details["registry"],
                    "v1_snapshots": details["approved_assets"],
                    "v2_completed": current["registry"],
                    "v2_snapshots": current["approved_assets"],
                    "v2_receipt": new_receipt,
                }
                Path("registry-rollout.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
                activate_qa(lab)
                path, terms = registry_brief(lab)
                queued = api.post(path, headers=lab.x["headers"], json={**terms, "registry_workflow": QA_WORKFLOW})
                queued.raise_for_status()
                qa_run = queued.json()["id"]
                lab.runs = [qa_run]
                drive(lab, qa_run, config, seo_v2=True)
                usage = receipts(lab, [(qa_run, lab.cases[0], "Landing role QA")])[0]
                run = read_run(lab, qa_run)
                nodes = [p for p in run["checkpoints"] if p["skill"] in ("content", "seo")]
                assert {p["skill"] for p in nodes} == {"content","seo"} and len(run["approved_assets"]) == 1
                for p in nodes:
                    qa = p["quality"]["role_qa"]
                    assert qa["node_id"] == p["node_id"] and qa["policy"] == p["skill"] + "-qa@2"
                    assert qa["plan_digest"] == run["graph"]["digest"] and qa["output_digest"] == canonical_hash(p["output"])
                role_evidence = {"sha": evidence["source_after"], "runtime_fingerprint": runtime_fingerprint(),
                                 "manifest_digest": run["registry"]["manifest_digest"], "usage": usage,
                                 "reports": [p["quality"]["role_qa"] for p in nodes], "approved": run["approved_assets"]}
                Path("role-qa-measurements.json").write_text(json.dumps(role_evidence, indent=2), encoding="utf-8")
        finally:
            lab.close()


if __name__ == "__main__":
    verify()
