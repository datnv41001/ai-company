"""Opt-in parallel specialists. The attempt row owns the lease and reservation."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from . import workflow_dag
from .registry_adapters import node_request, validate_output
from .models import utcnow
from .workforce_gateway import GatewayError, PROMPT_VERSION, measured_cost, reserve_tokens
from .workforce_models import WorkforceRun
from .workforce_worker import MAX_TRIES, authorized_queue, save_checkpoint


@dataclass(frozen=True)
class Offer:
    run: str
    token: str
    body: dict
    hold: int
    deadline: datetime
    ordinal: int


def claim(db, scope, config, rid, node):
    run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == rid, WorkforceRun.state == "queued").with_for_update())
    if not run:
        return
    earlier, assignment = workflow_dag.inputs(db, rid, node)
    body = node_request(run, config.model, node=node, predecessors=earlier, assignment=assignment)
    hold = config.price(reserve_tokens(body), body["max_tokens"])
    if node.attempts >= MAX_TRIES or run.knowledge["prompt_version"] != PROMPT_VERSION or hold > run.budget_microusd:
        run.state = "failed"
        run.last_error = (
            "attempts_exhausted"
            if node.attempts >= MAX_TRIES
            else "prompt_version"
            if run.knowledge["prompt_version"] != PROMPT_VERSION
            else "budget_exhausted"
        )
        return
    if run.reserved_microusd + hold > run.budget_microusd:
        return
    now = utcnow()
    offer = Offer(rid, str(uuid4()), body, hold, now + timedelta(seconds=config.timeout + 20), node.attempts + 1)
    run.reserved_microusd += hold
    run.journal = [
        *run.journal,
        {
            "attempt_id": offer.token,
            "node_id": node.id,
            "plan_revision": node.revision,
            "skill": node.skill,
            "attempt": offer.ordinal,
            "provider": config.provider,
            "model": config.model,
            "prompt": PROMPT_VERSION,
            "started_at": now.isoformat(),
            "reserved_microusd": hold,
            "outcome": "running",
        },
    ]
    db.flush()
    return offer


def finish(db, scope, config, row, node, result, error):
    run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == row["run"]).with_for_update())
    metrics = {}
    if result is not None:
        raw, inputs, outputs = result
        try:
            cost = measured_cost(config, row["body"], inputs, outputs)
            run.reserved_microusd += cost - row["reserved"]
            metrics = {"estimated_microusd": cost, "input_tokens": inputs, "output_tokens": outputs}
            if not error:
                output = validate_output(raw, node.skill, run.plan, run.knowledge["sources"], run.knowledge.get('registry'))
        except GatewayError as exc:
            error = str(exc)
    entry = {"outcome": error or "ok", "finished_at": utcnow().isoformat(), **metrics}
    # Journal is an audit projection. Decisions above use the locked attempt and graph.
    run.journal = [{**j, **entry} if j.get("attempt_id") == str(row["id"]) else j for j in run.journal]
    if error:
        if row["ordinal"] >= MAX_TRIES:
            run.state, run.last_error = "failed", error
        db.execute(
            text("update amc_ops.dag_nodes set ready_at=:when where run=:run and revision=:rev and node_id=:node"),
            {"when": utcnow() + timedelta(seconds=2 ** row["ordinal"]), "run": run.id, "rev": node.revision, "node": node.id},
        )
    else:
        save_checkpoint(db, scope, run, node.skill, output, node)
    db.flush()
    return entry
