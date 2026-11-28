"""Trusted scheduler. Each turn commits before an inference worker can take its envelope."""

import json
import os
import time
from dataclasses import replace

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .registry_adapters import resolve

from . import node_attempts, scheduler_telemetry
from .workforce_gateway import Gateway, GatewayError, measured_cost
from .workforce_models import WorkforceRun
from .workflow_dag import node_for_slot
from .workforce_worker import Scope, authorized_queue, claim, finish


def query(db, sql, **params):
    return db.execute(text(sql), params)


def lock_scheduler(db):
    query(db, "select pg_advisory_xact_lock(4197832742)")


def dispatch(bind, config):
    with Session(bind) as db, db.begin():
        lock_scheduler(db)
        candidates = query(db, "select * from amc_ops.candidates()").mappings().all()
        for route in candidates:
            scope = Scope(*(route[k] for k in ("tenant", "client", "brand", "campaign", "operator")))
            with db.begin_nested() as change:
                try:
                    node = node_for_slot(db, route["run"], route["step"])
                    contract = None
                    if node:
                        run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == route["run"]).with_for_update())
                        if run is None:
                            continue
                        if binding := run.knowledge.get("registry"):
                            contract = binding["contracts"][node.skill]
                            if not resolve(contract) or config.provider != contract["model"] or config.timeout > contract["timeout_seconds"]:
                                # A compatible dispatcher may still claim this node during rollout.
                                continue
                    if node and node.parallel:
                        offer = node_attempts.claim(db, scope, config, route["run"], node)
                    else:
                        task = claim(db, scope, config, run_id=route["run"], node=node, commit=False)
                        offer = None
                        if task:
                            rid, token, body = task
                            run = db.get(WorkforceRun, rid)
                            offer = node_attempts.Offer(rid, token, body, run.journal[-1]["reserved_microusd"], run.ready_at, run.attempts)
                except PermissionError:
                    continue
                if not offer:
                    continue
                token, body, hold = offer.token, offer.body, offer.hold
                if contract:
                    # Receipt, revoke and checkpoint take this same scheduler lock.
                    exposure = query(db, """select coalesce(sum(l.held+l.spent),0)
                        from amc_ops.attempts a join amc_ops.ledger l on l.id=a.id
                        where a.run=:r and a.node_id=:n""", r=run.id,n=node.id).scalar_one()
                    if exposure + hold > contract["node_cap"]:
                        change.rollback()
                        continue
                period = query(
                    db,
                    """
                    select p.month from amc_ops.periods p where tenant=:tenant
                    and month=date_trunc('month',now() at time zone 'UTC')::date and
                    amc_ops.available_budget(:tenant) >= :hold for update of p
                """,
                    tenant=scope.tenant,
                    hold=hold,
                ).scalar()
                if period is None:
                    change.rollback()
                    continue
                query(
                    db,
                    """
                    insert into amc_ops.attempts(id,run,step,worker,operator,tenant,month,deadline,body,reserved,input_rate,output_rate,ordinal,node_id,plan_revision)
                    values(:id,:run,:step,:worker,:operator,:tenant,:month,:deadline,cast(:body as jsonb),:hold,:ir,:orr,:ordinal,:node,:rev)
                """,
                    **route,
                    id=token,
                    month=period,
                    deadline=offer.deadline,
                    body=json.dumps(body),
                    hold=hold,
                    ir=config.input_rate,
                    orr=config.output_rate,
                    ordinal=offer.ordinal,
                    node=node.id if node else None,
                    rev=node.revision if node else None,
                )
                query(
                    db,
                    """insert into amc_ops.ledger(id,tenant,month,event,actor,held,spent)
                      values(:id,:t,:m,'hold',session_user,:h,0)""",
                    id=token,
                    t=scope.tenant,
                    m=period,
                    h=hold,
                )
                query(db, "update amc_ops.agencies set served=nextval('amc_ops.turn') where tenant=:t", t=scope.tenant)
                return True
    return False


def pending_reports(db, worker_names=None):
    # Usually the oldest report is compatible. Fetch another only when a peer
    # owns its adapter; avoid locking or reading every queued model response.
    after = None
    workers = "and a.worker = any(cast(:workers as name[]))" if worker_names is not None else ""
    params = {"workers": worker_names} if worker_names is not None else {}
    while True:
        cursor = "and (a.started,a.id) > (:started,cast(:id as uuid))" if after else ""
        row = query(db, f"""
            select a.*,t.client,t.brand,t.campaign,t.skill from amc_ops.attempts a join amc_ops.tasks t using(run,step)
            where a.status<>'closed' and (a.status='reported' or not amc_ops.live(a.id)) {workers} {cursor}
            order by a.started,a.id limit 1 for update of a
        """, **params, **(after or {})).mappings().first()
        if row is None:
            return
        yield row
        after = {"started":row["started"], "id":str(row["id"])}


def consume(bind, config, *, worker_names=None):
    with Session(bind) as db, db.begin():
        lock_scheduler(db)
        for row in pending_reports(db, worker_names):
            token = str(row["id"])
            scope = Scope(*(row[k] for k in ("tenant", "client", "brand", "campaign", "operator")))
            live_report = False
            if row["status"] == "reported":
                # A simultaneous human change can hold Knowledge's scope lock before the
                # scheduler lock. Defer consumption instead of reversing that lock order.
                try:
                    with db.begin_nested():
                        live_report = query(db, "select amc_ops.fence(:id)", id=token).scalar()
                except OperationalError as exc:
                    if getattr(exc.orig, "sqlstate", None) != "55P03":
                        raise
                    continue
            if live_report and row["node_id"]:
                run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == row["run"]))
                binding = run.knowledge.get("registry")
                if binding and not resolve(binding["contracts"][row["skill"]]):
                    # Preserve the reported output for a peer that owns this version's validator and QA.
                    continue
            break
        else:
            return False
        outcome, event, cost = "lease_expired", None, 0
        inputs = outputs = None
        if row["status"] == "offered":
            event = "unsent"
        if live_report:
            result, error = row["result"], row["error"]
            if result is not None and (not isinstance(result, list) or len(result) != 3):
                result, error = None, "invalid_usage"
            # Price at the rates captured at reservation, even after a restart or a rate change.
            priced = replace(config, input_rate=row["input_rate"], output_rate=row["output_rate"])
            task = (row["run"], token, row["body"])
            node = node_for_slot(db, row["run"], row["step"]) if row["node_id"] else None
            entry = None
            if row['parallel']:
                entry = node_attempts.finish(db, scope, priced, row, node, result, error)
            elif finish(db, scope, priced, task, result, error, node=node, commit=False):
                run = db.get(WorkforceRun, row["run"])
                entry = run.journal[-1]
            if entry:
                outcome = entry["outcome"]
                if "estimated_microusd" in entry:
                    event, cost = "usage", entry["estimated_microusd"]
                    inputs, outputs = entry["input_tokens"], entry["output_tokens"]
                if outcome == "ok":
                    query(db, "update amc_ops.tasks set done=true where run=:run and step=:step", run=row["run"], step=row["step"])
        if outcome == "lease_expired":
            outcome = query(db, "select amc_ops.retire(:id)", id=token).scalar()
            if outcome == "guide_authority_changed" and row["status"] == "reported":
                result = row["result"]
                if isinstance(result, list) and len(result) == 3:
                    priced = replace(config, input_rate=row["input_rate"], output_rate=row["output_rate"])
                    try:
                        from .product_guide_runtime import DIRECTOR
                        if row["body"].get("local_adapter") == DIRECTOR:
                            if any(type(value) is not int or value != 0 for value in result[1:]):
                                raise GatewayError("invalid_usage")
                            cost = 0
                        else:
                            cost = measured_cost(priced, row["body"], result[1], result[2])
                    except GatewayError:
                        pass  # A sent attempt with unconfirmed usage retains its original hold.
                    else:
                        event, inputs, outputs = "usage", result[1], result[2]
        if event:
            query(
                db,
                """insert into amc_ops.ledger(id,tenant,month,event,actor,held,spent)
                values(:id,:tenant,:month,:event,session_user,:delta,:cost)""",
                id=token,
                tenant=row["tenant"],
                month=row["month"],
                event=event,
                delta=-row["reserved"],
                cost=cost,
            )
        query(
            db,
            "update amc_ops.attempts set status='closed',outcome=:o,input_tokens=:inputs,output_tokens=:outputs,body='{}',result=null where id=:id",
            o=outcome,
            inputs=inputs,
            outputs=outputs,
            id=token,
        )
        return True


def main():
    from . import delivery_models, knowledge_models, session_state  # noqa: F401 - load ORM relationships without user signing keys

    bind = create_engine(os.environ["AMC_DISPATCH_URL"], pool_pre_ping=True)
    config = Gateway.configured()
    if config.provider != "local":
        raise ValueError("Pool supports local inference only")
    next_heartbeat = 0.0
    while True:
        if time.monotonic() >= next_heartbeat:
            with bind.begin() as conn:
                scheduler_telemetry.dispatcher_heartbeat(conn,config)
            next_heartbeat = time.monotonic()+3
        if not consume(bind, config) and not dispatch(bind, config):
            time.sleep(0.5)


if __name__ == "__main__":
    main()
