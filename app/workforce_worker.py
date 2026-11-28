"""Run a durable worker for one explicitly configured campaign. See HANDOFF.md."""

import argparse
import multiprocessing as mp
import os
import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .access import set_context, set_worker_scope
from .database import engine, prepare_database
from .delivery import as_utc
from .revision_qa import evaluate
from .registry_adapters import node_request, validate_output
from .models import AuditEvent, Deliverable, Membership, utcnow
from .workforce_gateway import Gateway, GatewayError, PROMPT_VERSION, infer, measured_cost, quality, request_body, reserve_tokens
from .workforce_models import WorkforceRun
from . import dynamic_plan, landing_qa, product_guide_runtime as guide, workflow_dag, storyboard_runtime

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


def claim(db, scope, config, *, run_id=None, node=None, commit=True):
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
    if run.knowledge.get("workflow") in ("diamond-v1", "dynamic-v1") and node is None:
        raise RuntimeError("Missing frozen node for pool dispatch")
    if node is not None:
        stage = node.skill
        earlier, assignment = workflow_dag.inputs(db, run.id, node)
        body = node_request(run, config.model, node=node, predecessors=earlier, assignment=assignment)
    else:
        stage = run.plan[len(run.checkpoints)]
        body = request_body(run, config.model)
    is_board = storyboard_runtime.is_run(run)
    local_adapter = body.get("local_adapter") if is_board or guide.is_run(run) else None
    reserved = 0 if local_adapter else config.price(reserve_tokens(body), body["max_tokens"])
    prior_attempts = node.attempts if node else run.attempts
    if prior_attempts >= MAX_TRIES or run.reserved_microusd + reserved > run.budget_microusd or run.knowledge["prompt_version"] != PROMPT_VERSION:
        error = (
            "attempts_exhausted"
            if prior_attempts >= MAX_TRIES
            else "prompt_version"
            if run.knowledge["prompt_version"] != PROMPT_VERSION
            else "budget_exhausted"
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
    run.attempts = prior_attempts + 1
    run.reserved_microusd += reserved
    run.journal = [
        *run.journal,
        {
            **({"node_id": node.id, "plan_revision": node.revision} if node else {}),
            "skill": stage,
            "attempt": run.attempts,
            "provider": "deterministic" if local_adapter else config.provider,
            "model": local_adapter or config.model,
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


def save_checkpoint(db, scope, run, stage, output, node):
    from . import research_strategy
    record = {"skill": stage, "output": output, "quality": quality(output, run.knowledge["sources"])}
    if binding := run.knowledge.get("registry"):
        from .registry_qa import assess_role
        contract = binding["contracts"][stage]
        from . import c3_releases
        if guide.is_run(run):
            record["quality"]["role_qa"] = {"policy": contract["qa_policy"], "source_ids": output["source_ids"],
                                           "manifest_digest": run.knowledge["c3_manifest"]["digest"]}
        elif storyboard_runtime.is_run(run):
            record["quality"]["role_qa"] = {"policy": contract["qa_policy"], "manifest_digest": run.knowledge["c3_manifest"]["digest"],
                                           "source_ids":output["source_ids"], "adapter":storyboard_runtime.adapter_for(run)}
        elif binding.get("workflow") in c3_releases.WORKFLOWS:
            record["quality"]["role_qa"] = {"policy": contract["qa_policy"], "findings": record["quality"]["claims"],
                                          "manifest_digest":run.knowledge["c3_manifest"]["digest"], "source_ids":output["source_ids"]}
        elif stage in ("research","strategy") and contract["adapter"] == stage+"@2":
            record["quality"]["role_qa"] = research_strategy.evidence(db,run,node,output)
        elif contract["adapter"] in landing_qa.ROLE_POLICY:
            record["quality"]["role_qa"] = landing_qa.evaluate_node(db, run, node, output)
        else:
            record["quality"]["role_qa"] = assess_role(stage, output, run.knowledge["sources"], contract)
    if node:
        record.update(node_id=node.id, plan_revision=node.revision)
        joined = workflow_dag.checkpoint(db, run, node, record)
    else:
        run.checkpoints = [*run.checkpoints, record]
        joined = len(run.checkpoints) == len(run.plan)
    if joined:
        # Only draft copy and specialist proposals enter QA. Director instructions, prompts and source excerpts stay private.
        preview = "\n\n".join(p["skill"].upper() + "\n" + p["output"]["text"] for p in run.checkpoints if p["skill"] != "director")
        if binding and binding["contracts"]["director"]["adapter"] == "director@2":
            preview = research_strategy.proposal(run.checkpoints)
        title = run.knowledge["title"]
        if storyboard_runtime.is_run(run):
            preview = next(p["output"]["text"] for p in run.checkpoints if p["skill"]=="storyboard")
        studio = None
        edition = None
        if guide.is_run(run):
            copy = next(p["output"]["raw_reply"] for p in run.checkpoints if p["skill"] == "content")
            edition = guide.compose(run.knowledge["c3_projection"], copy)
            initial = guide.preview(edition)
            title, preview = initial["title"], initial["body"]
        if binding and binding.get("workflow") in c3_releases.WORKFLOWS:
            from . import c3_marketing, c3_order_units
            renderer = c3_order_units.render if c3_releases.is_current(binding["workflow"]) else c3_marketing.render
            draft = renderer(binding["workflow"], run.knowledge["c3_projection"], {p["skill"]:p["output"] for p in run.checkpoints})
            projection = run.knowledge["c3_projection"]
            if c3_releases.is_current(binding["workflow"]) and projection.get("task_intent", {}).get("buyer_action"):
                from . import c3_studio
                groups = c3_studio.compose(binding["workflow"],projection,{p["skill"]:p["output"] for p in run.checkpoints})
                draft = c3_studio.preview(binding["workflow"],groups,draft)
                studio = {"version":c3_studio.VERSION,"origin":"worker","groups":groups}
            title, preview = draft["title"], draft["body"]
            if len(title) > 160:
                title = run.knowledge["c3_projection"]["product"]
        doc = Deliverable(
            tenant_id=run.tenant_id,
            campaign_id=run.campaign_id,
            title=title,
            content={"client_preview": preview, "workforce_run_id": run.id, **({"studio":studio} if studio else {}),
                     **({"product_guide": edition} if edition else {})},
            created_by=scope.operator,
            status="draft" if edition else "submitted",
        )
        db.add(doc)
        db.flush()
        if node:
            db.execute(
                text("""update amc_ops.dag_plans set deliverable=:d where run=:r and revision=:v
                and deliverable is null returning run"""),
                {"d": doc.id, "r": run.id, "v": node.revision},
            ).scalar_one()
        run.deliverable_id, run.state = doc.id, "awaiting_qa"
        db.flush()  # The evidence lookup follows the persisted worker-to-draft link.
        evaluate(db, doc, scope.operator)
        if studio:
            db.add(AuditEvent(tenant_id=run.tenant_id,user_id=scope.operator,subject_id=doc.id,event="studio.saved",
                              details={"revision":doc.qa_revision,"groups":studio["groups"],"version":studio["version"]}))
        db.add(
            AuditEvent(tenant_id=run.tenant_id, user_id=scope.operator, subject_id=doc.id,
                       event="workforce.product_guide_drafted" if edition else "workforce.submitted_to_qa", details={"run_id": run.id})
        )


def finish(db, scope, config, task, result, error, *, node=None, commit=True):
    rid, token, body = task
    run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == rid).with_for_update())
    if not run or run.state != "running" or run.lease != token or as_utc(run.ready_at) <= utcnow():
        return False  # A stale worker must never append a second checkpoint or artifact.
    stage = node.skill if node else run.plan[len(run.checkpoints)]
    metrics = {}
    verified_refusal = None
    if result is not None:
        raw, inputs, outputs = result
        try:
            if storyboard_runtime.is_run(run) or (guide.is_run(run) and stage == "director"):
                if type(inputs) is not int or type(outputs) is not int or (inputs, outputs) != (0, 0):
                    raise GatewayError("invalid_usage")
                cost = 0
            else:
                cost = measured_cost(config, body, inputs, outputs)
            run.reserved_microusd += cost - run.journal[-1]["reserved_microusd"]
            metrics = {"input_tokens": inputs, "output_tokens": outputs, "estimated_microusd": cost}
            if not error:
                if node and node.template == "dynamic-v1" and stage == "director":
                    binding = run.knowledge.get("registry",{})
                    from . import c3_marketing, c3_assets, c3_skill_library
                    director_raw = None
                    if binding.get("workflow") in c3_assets.ROLES:
                        director_raw = raw
                        raw = c3_skill_library.director_proposal(binding["workflow"], raw)
                    elif binding.get("workflow") in c3_marketing.ROLES:
                        raw = c3_marketing.director_proposal(binding["workflow"], raw)
                    elif binding.get("contracts",{}).get("director",{}).get("adapter")=="director@2":
                        from .research_strategy import director_proposal
                        raw = director_proposal(raw)
                    if guide.is_run(run):
                        director_raw = raw
                        contract, digest = guide.plan(raw, run.knowledge["required_outputs"], binding)
                    elif storyboard_runtime.is_run(run):
                        from .storyboard_contract import plan
                        contract, digest = plan(raw,run.knowledge["required_outputs"],binding)
                    else:
                        contract, digest = dynamic_plan.compile_plan(raw, run.knowledge["required_outputs"], run.knowledge.get('registry'))
                    workflow_dag.freeze(db, token, contract, digest)
                    output = {"text": digest, "sections": {}, "source_ids": [], "plan_digest": digest}
                    if director_raw is not None:
                        output["raw_reply"] = director_raw
                else:
                    if storyboard_runtime.is_run(run):
                        output = storyboard_runtime.validated(raw, body)
                    else:
                        output = validate_output(raw, stage, run.plan, run.knowledge["sources"], run.knowledge.get('registry'))
        except GatewayError as exc:
            error = str(exc)
            # Only the dispatcher's own adapter validation can attest that the
            # pinned input fails deterministically. A mailbox error cannot.
            if storyboard_runtime.is_run(run) and error in {"storyboard_needs_revision", "storyboard_invalid_checkpoint"}:
                verified_refusal = error
            if isinstance(exc, dynamic_plan.InvalidPlan):
                metrics["plan_error"] = exc.reason
    run.lease = None
    if error:
        if verified_refusal:
            metrics["retry_disposition"] = "terminal_for_pinned_input"
            metrics["recovery"] = (
                "revise_source_or_policy_and_queue_new_manifest"
                if verified_refusal == "storyboard_needs_revision"
                else "inspect_checkpoint_integrity_before_new_run"
            )
        elif error in ("timeout", "provider_process"):
            metrics["retry_disposition"] = "bounded_transport_retry"
        elif error == "provider_or_format":
            metrics["retry_disposition"] = "bounded_output_retry" if metrics else "bounded_provider_retry"
        elif error in ("invalid_output", "incomplete_output", "invalid_contract_output", "invalid_source", "invalid_plan", "invalid_storyboard_reply"):
            metrics["retry_disposition"] = "bounded_output_retry"
        close_attempt(run, outcome=error, **metrics)
        run.last_error = error
        run.state = "failed" if verified_refusal or run.attempts >= MAX_TRIES else "queued"
        run.ready_at = utcnow() + timedelta(seconds=2**run.attempts)
    else:
        close_attempt(run, outcome="ok", **metrics)
        run.last_error, run.attempts, run.ready_at = None, 0, utcnow()
        run.state = "queued"
        save_checkpoint(db, scope, run, stage, output, node)
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
    from . import delivery_models, knowledge_models, session_state  # noqa: F401

    prepare_database(engine, verify_identity=False)
    while True:
        worked = process_one(engine, scope, config)
        if args.once:
            break
        if not worked:
            time.sleep(2)


if __name__ == "__main__":
    main()
