"""Run a durable worker for one explicitly configured campaign. See HANDOFF.md."""

import argparse
import multiprocessing as mp
import os
import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import set_context, set_worker_scope
from .database import engine, prepare_database
from .delivery import as_utc
from .revision_qa import evaluate
from .models import AuditEvent, Deliverable, Membership, utcnow
from .workforce_gateway import Gateway, GatewayError, PROMPT_VERSION, infer, quality, request_body, reserve_tokens, validate_output
from .workforce_models import WorkforceRun

MAX_TRIES = 3


@dataclass(frozen=True)
class Scope:
    tenant: str
    client: str
    brand: str
    campaign: str
    operator: str

    @classmethod
    def configured(cls):
        return cls(*(os.environ["AMC_WORKER_" + k] for k in ("TENANT", "CLIENT", "BRAND", "CAMPAIGN", "OPERATOR")))


def authorized_queue(db, scope):
    set_context(db, actor=scope.operator, tenant=scope.tenant)
    set_worker_scope(db, scope.client, scope.brand, scope.campaign)
    if db.get_bind().dialect.name == "sqlite":
        conn = db.connection()
        if not conn.connection.driver_connection.in_transaction:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
    member = db.get(Membership, (scope.tenant, scope.operator))
    if not member or member.role != "editor":
        raise PermissionError("A dedicated editor membership is required for this campaign worker")
    return select(WorkforceRun).where(
        WorkforceRun.tenant_id == scope.tenant,
        WorkforceRun.client_id == scope.client,
        WorkforceRun.brand_id == scope.brand,
        WorkforceRun.campaign_id == scope.campaign,
    )


def close_attempt(run, **updates):
    run.journal = [*run.journal[:-1], {**run.journal[-1], **updates, "finished_at": utcnow().isoformat()}]


def claim(db, scope, config, *, run_id=None, commit=True):
    now = utcnow()
    q = authorized_queue(db, scope)
    if run_id is not None:
        q = q.where(WorkforceRun.id == run_id)
    run = db.scalar(
        q.where(WorkforceRun.state.in_(["queued", "running"]), WorkforceRun.ready_at <= now)
        .order_by(WorkforceRun.ready_at, WorkforceRun.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if not run:
        return
    if run.state == "running":
        close_attempt(run, outcome="lease_expired")
    stage = run.plan[len(run.checkpoints)]
    body = request_body(run, config.model)
    reserved = config.price(reserve_tokens(body), body["max_tokens"])
    if run.attempts >= MAX_TRIES or run.reserved_microusd + reserved > run.budget_microusd or run.knowledge["prompt_version"] != PROMPT_VERSION:
        error = (
            "attempts_exhausted" if run.attempts >= MAX_TRIES else "prompt_version" if run.knowledge["prompt_version"] != PROMPT_VERSION else "budget_exhausted"
        )
        if run_id is not None and error == "budget_exhausted" and reserved <= run.budget_microusd:
            # A late receipt can make this pooled retry affordable. Preserve its repair context.
            return
        run.last_error = error
        run.state, run.lease = "failed", None
        if commit:
            db.commit()
        else:
            db.flush()
        return
    token = str(uuid4())
    run.lease, run.state, run.ready_at = token, "running", now + timedelta(seconds=config.timeout + 20)
    run.attempts += 1
    run.reserved_microusd += reserved
    run.journal = [
        *run.journal,
        {
            "skill": stage,
            "attempt": run.attempts,
            "provider": config.provider,
            "model": config.model,
            "prompt": PROMPT_VERSION,
            "started_at": now.isoformat(),
            "outcome": "running",
            "reserved_microusd": reserved,
        },
    ]
    ident = run.id
    if commit:
        db.commit()
    else:
        db.flush()
    return ident, token, body


def _child(pipe, config, body):
    try:
        pipe.send(("ok", infer(config, body)))
    except GatewayError as exc:
        pipe.send(("error", (str(exc), exc.usage)))
    finally:
        pipe.close()


def bounded_call(config, body):
    ctx = mp.get_context("spawn")
    reader, writer = ctx.Pipe(duplex=False)
    child = ctx.Process(target=_child, args=(writer, config, body), daemon=True)
    child.start()
    writer.close()
    try:
        if not reader.poll(config.timeout):
            raise GatewayError("timeout")
        try:
            kind, value = reader.recv()
        except EOFError:
            raise GatewayError("provider_process") from None
        if kind != "ok":
            raise GatewayError(*value)
        return value
    finally:
        reader.close()
        if child.is_alive():
            child.terminate()
        child.join(3)
        if child.is_alive():
            child.kill()
            child.join()


def finish(db, scope, config, task, result, error, *, commit=True):
    rid, token, body = task
    run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == rid).with_for_update())
    if not run or run.state != "running" or run.lease != token or as_utc(run.ready_at) <= utcnow():
        return False  # A stale worker must never append a second checkpoint or artifact.
    stage = run.plan[len(run.checkpoints)]
    metrics = {}
    if result is not None:
        raw, inputs, outputs = result
        try:
            if type(inputs) is not int or type(outputs) is not int or not (0 < inputs <= reserve_tokens(body) and 0 < outputs <= body["max_tokens"]):
                raise GatewayError("invalid_usage")
            cost = config.price(inputs, outputs)
            run.reserved_microusd += cost - run.journal[-1]["reserved_microusd"]
            metrics = {"input_tokens": inputs, "output_tokens": outputs, "estimated_microusd": cost}
            if not error:
                output = validate_output(raw, stage, run.plan, run.knowledge["sources"])
        except GatewayError as exc:
            error = str(exc)
    run.lease = None
    if error:
        close_attempt(run, outcome=error, **metrics)
        run.last_error = error
        run.state = "failed" if run.attempts >= MAX_TRIES else "queued"
        run.ready_at = utcnow() + timedelta(seconds=2**run.attempts)
    else:
        close_attempt(run, outcome="ok", **metrics)
        run.checkpoints = [*run.checkpoints, {"skill": stage, "output": output, "quality": quality(output, run.knowledge["sources"])}]
        run.last_error, run.attempts, run.ready_at = None, 0, utcnow()
        run.state = "queued"
        if len(run.checkpoints) == len(run.plan):
            # Only draft copy and specialist proposals enter QA. Director instructions, prompts and source excerpts stay private.
            preview = "\n\n".join(p["skill"].upper() + "\n" + p["output"]["text"] for p in run.checkpoints if p["skill"] != "director")
            doc = Deliverable(
                tenant_id=run.tenant_id,
                campaign_id=run.campaign_id,
                title=run.knowledge["title"],
                content={"client_preview": preview, "workforce_run_id": run.id},
                created_by=scope.operator,
                status="submitted",
            )
            db.add(doc)
            db.flush()
            run.deliverable_id, run.state = doc.id, "awaiting_qa"
            db.flush()  # The evidence lookup follows the persisted worker-to-draft link.
            evaluate(db, doc, scope.operator)
            db.add(
                AuditEvent(tenant_id=run.tenant_id, user_id=scope.operator, subject_id=doc.id, event="workforce.submitted_to_qa", details={"run_id": run.id})
            )
    if commit:
        db.commit()
    else:
        db.flush()
    return True


def process_one(bind, scope, config, call=bounded_call):
    with Session(bind) as db:
        task = claim(db, scope, config)
    if not task:
        return False
    with Session(bind) as db:
        active = db.scalar(
            authorized_queue(db, scope).where(
                WorkforceRun.id == task[0], WorkforceRun.state == "running", WorkforceRun.lease == task[1], WorkforceRun.ready_at > utcnow()
            )
        )
        if active is None:
            return False
    result, error = None, None
    try:
        result = call(config, task[2])
    except GatewayError as exc:
        error, result = str(exc), exc.usage
    with Session(bind) as db:
        finish(db, scope, config, task, result, error)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one specialist checkpoint")
    args = parser.parse_args()
    from dotenv import dotenv_values

    for name, value in dotenv_values().items():
        if value is not None and (
            name.startswith(("AMC_WORKER_", "AMC_WORKFORCE_"))
            or name in {"AMC_MODEL_TIMEOUT", "AMC_LOCAL_MODEL_URL", "AMC_INPUT_RATE_MICROUSD", "AMC_OUTPUT_RATE_MICROUSD"}
        ):
            os.environ.setdefault(name, value)
    scope, config = Scope.configured(), Gateway.configured()
    # Load the full model inventory before checking migration readiness.
    from .main import app  # noqa: F401

    prepare_database(engine)
    while True:
        worked = process_one(engine, scope, config)
        if args.once:
            break
        if not worked:
            time.sleep(2)


if __name__ == "__main__":
    main()
