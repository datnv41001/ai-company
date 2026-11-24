"""Verify a real Qwen planner, specialists and approved registry snapshot."""

from dataclasses import replace
import json
import os
from pathlib import Path
import time

from fastapi.testclient import TestClient
from app.main import app
from app.workforce_gateway import GatewayError, infer
from app.pool_worker import report
from pool_lab import Lab
from pool_model_smoke import receipts
from test_registry import policy, registry_brief


def verify():
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
            deadline = time.monotonic() + 360
            while time.monotonic() < deadline and lab.states()[0] in ("queued", "running"):
                for w in lab.workers:
                    job = w.take()
                    if job:
                        assert job["run"] == rid
                        try:
                            raw, inputs, outputs = infer(config, job["body"])
                            assert report(w.conn, job, [raw, inputs, outputs])
                        except GatewayError as exc:
                            assert report(w.conn, job, result=exc.usage, error=str(exc))
                if not lab.consume() and not lab.dispatch():
                    time.sleep(0.1)
            results = receipts(lab, [(rid, lab.cases[0], "Registry")])
            Path("registry-measurements.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
            assert lab.states() == ["awaiting_qa"]
            details = api.get(lab.cases[0][0] + "/workforce/runs/" + rid, headers=lab.x["headers"]).json()
            assert details["approved_assets"] and details["registry"]["plan_digest"] == details["graph"]["digest"]
            assert {"director", "content", "seo"} == {n["skill_id"] for n in details["registry"]["nodes"]}
            assert all(n["attempt_ids"] for n in details["registry"]["nodes"])
        finally:
            lab.close()


if __name__ == "__main__":
    verify()
