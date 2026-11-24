"""Measure same-run inference overlap at llama.cpp, on isolated synthetic data."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
from threading import Barrier
import time

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.pool_worker import report
from app.workforce_gateway import infer
from pool_lab import Lab
from pool_model_smoke import receipts
from test_diamond import take_node
from test_dynamic_plan import node


def verify():
    endpoint = os.environ["AMC_LOCAL_MODEL_URL"]
    with TestClient(app) as api, httpx.Client(base_url=endpoint.removesuffix("/v1"), trust_env=False, timeout=3) as model:
        assert len(model.get("/slots").raise_for_status().json()) == 2
        lab = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow="dynamic-v1", parallelism=2)
        try:
            lab.configure(lab.y, 10000, False)
            lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=%s", (lab.runs[1],))
            worker, planner = take_node(lab)
            # Choose two ready leaves deterministically. The separate planner smoke lets Qwen choose topology.
            proposal = {"nodes": [node("email", "content"), node("page", "content")]}
            assert report(worker.conn, planner, [proposal, 100, 25]) and lab.consume()
            assert all(w.take() is None for w in lab.workers)
            assert lab.dispatch() and lab.dispatch()
            jobs = [w.take() for w in lab.workers]
            assert all(j["run"] == lab.runs[0] for j in jobs)
            config = replace(lab.config, url=endpoint)
            gate = Barrier(2)

            def real_call(pair):
                w, j = pair
                gate.wait(10)
                start = time.perf_counter_ns()
                raw, inputs, outputs = infer(config, j["body"])
                end = time.perf_counter_ns()
                assert report(w.conn, j, [raw, inputs, outputs])
                return start, end, inputs, outputs

            observations = []
            with ThreadPoolExecutor(max_workers=2) as executor:
                pending = [executor.submit(real_call, pair) for pair in zip(lab.workers, jobs, strict=True)]
                while not all(f.done() for f in pending):
                    slots = model.get("/slots").raise_for_status().json()
                    if len([s for s in slots if s["is_processing"]]) == 2:
                        observations.append(time.perf_counter_ns())
                    time.sleep(0.025)
                spans = [f.result() for f in pending]
            assert lab.consume() and lab.consume() and not lab.consume()
            assert lab.states()[0] == "awaiting_qa"
            receipts(lab)
            rid = lab.runs[0]
            lease_ms = lab.owner.execute(
                """select extract(epoch from min(reported)-max(collected))*1000
                from amc_ops.attempts where run=%s and parallel and status='closed'""",
                (rid,),
            ).fetchone()[0]
            snapshot_count = lab.owner.execute(
                """select count(*) from review_entries e join client_reviews c on e.review_id=c.id
                join workforce_runs w on c.deliverable_id=w.deliverable_id where w.id=%s and e.kind='approved'""",
                (rid,),
            ).fetchone()[0]
            assert snapshot_count == 1
            info = {
                "observed_two_slots": len(observations),
                "two_slot_span_ms": (observations[-1] - observations[0]) / 1e6 if observations else 0,
                "lease_overlap_ms": float(lease_ms),
                "request_overlap_ms": (min(s[1] for s in spans) - max(s[0] for s in spans)) / 1e6,
                "real_specialist_calls": 2,
                "input_tokens": sum(s[2] for s in spans),
                "output_tokens": sum(s[3] for s in spans),
                "estimated_microusd": int(sum(lab.balance_x())),
                "approved_snapshots": snapshot_count,
            }
            print("Concurrent Qwen measurements", json.dumps(info), flush=True)
            if os.getenv("AMC_PARALLEL_REPORT"):
                Path(os.environ["AMC_PARALLEL_REPORT"]).write_text(json.dumps(info, indent=2))
            assert info["two_slot_span_ms"] > 0 and info["lease_overlap_ms"] > 0 and info["request_overlap_ms"] > 0
        finally:
            lab.close()


if __name__ == "__main__":
    verify()
