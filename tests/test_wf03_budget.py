"""Price the WF-03 Director from the actual release and compare a real pool offer to its ledger."""

from dataclasses import replace
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import dynamic_plan, research_strategy
from app.pool_dispatch import dispatch
from app.scheduler_telemetry import dispatcher_heartbeat, worker_heartbeat
from app.workforce_gateway import reserve_tokens
from scripts.provision_pool import inventory
from test_registry import PG, pool as registry_pool
from test_research_strategy import start_research

pool = registry_pool


@PG
@pytest.mark.parametrize("margin", [0, 1], ids=["exact", "one-above"])
def test_wf03_director_budget_boundary_matches_ledger(pool, margin):
    lab = pool
    rid = start_research(lab)
    base, admin, *_ = lab.cases[0]
    config = replace(lab.config, input_rate=100_000, output_rate=100_000)
    row = lab.owner.execute("select knowledge,plan,checkpoints,journal from workforce_runs where id=%s", (rid,)).fetchone()
    run = SimpleNamespace(knowledge=row[0], plan=row[1], checkpoints=row[2], journal=row[3])
    assert run.knowledge["registry"]["contracts"]["director"]["adapter"] == "director@2"
    # Independent oracle: compare both released envelopes before testing the public endpoint.
    body = research_strategy.request(run, config.model, node=SimpleNamespace(skill="director"))

    def price(request):
        return config.price(reserve_tokens(request), request["max_tokens"])

    hold = price(body)
    legacy_hold = price(dynamic_plan.planner_body(run, config.model))
    assert abs(hold - legacy_hold) > 1

    inventory(lab.owner, [lab.logins[0][0]])

    def observe():
        with lab.bind.begin() as db:
            dispatcher_heartbeat(db, config)
        for worker in lab.workers:
            worker_heartbeat(worker.conn, config)
            assert worker.take() is None
        response = lab.api.get(base + "/workforce/runs/" + rid + "/wait-diagnostics", headers=admin["headers"])
        response.raise_for_status()
        (node,) = response.json()["nodes"]
        assert node["node_id"] == "director" and node["candidate"] and "telemetry_unknown" not in node["wait_reasons"]
        return node["wait_reasons"]

    lab.limit_x(hold - 1)
    below = observe()
    assert not dispatch(lab.bind, config)
    assert lab.owner.execute("select count(*) from amc_ops.attempts where run=%s", (rid,)).fetchone() == (0,)
    assert lab.owner.execute("select reserved_microusd from workforce_runs where id=%s", (rid,)).fetchone() == (0,)
    lab.limit_x(hold + margin)
    allowed = observe()
    assert dispatch(lab.bind, config)
    rows = lab.owner.execute(
        """select a.node_id,a.status,a.body,a.reserved,l.event,l.held,l.spent,r.reserved_microusd
                 from amc_ops.attempts a join amc_ops.ledger l using(id) join workforce_runs r on r.id=a.run
                 where a.run=%s order by l.seq""",
        (rid,),
    ).fetchall()
    (record,) = rows
    node, status, envelope, reserved, event, ledger_held, spent, run_total = record
    assert envelope == body
    assert (node, status, reserved, event, ledger_held, spent, run_total) == ("director", "offered", hold, "hold", hold, 0, hold)
    evidence = {
        "checkout_sha": os.getenv("GITHUB_SHA"),
        "adapter": "director@2",
        "workflow": run.knowledge["registry"]["workflow"],
        "manifest_digest": run.knowledge["registry"]["manifest_digest"],
        "pinned_hold": hold,
        "legacy_hold": legacy_hold,
        "below": {"ceiling": hold - 1, "wait_reasons": below, "offered": False, "held": 0},
        "admitted": {
            "ceiling": hold + margin,
            "wait_reasons": allowed,
            "offered": True,
            "attempt_reserved": reserved,
            "ledger_event": event,
            "ledger_held": ledger_held,
            "ledger_spent": spent,
            "run_reserved": run_total,
        },
    }
    if directory := os.getenv("AMC_WF03_HOLD_EVIDENCE"):
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        (target / f"wf03-hold-plus-{margin}.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    assert ("budget_insufficient" in below, "budget_insufficient" in allowed) == (True, False), evidence
