"""Trusted scheduler. Each turn commits before an inference worker can take its envelope."""

import json
import os
import time
from dataclasses import replace

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from .workforce_gateway import Gateway
from .workforce_models import WorkforceRun
from .workflow_dag import node_for_slot
from .workforce_worker import Scope, claim, finish


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
                    task = claim(db, scope, config, run_id=route["run"], node=node, commit=False)
                except PermissionError:
                    continue
                if not task:
                    continue
                rid, token, body = task
                run = db.get(WorkforceRun, rid)
                hold = run.journal[-1]["reserved_microusd"]
                period = query(
                    db,
                    """
                    select p.month from amc_ops.periods p where tenant=:tenant
                    and month=date_trunc('month',now() at time zone 'UTC')::date and
                    p.ceiling >= :hold + coalesce((select sum(held+spent) from amc_ops.ledger l
                    where l.tenant=p.tenant and l.month=p.month),0) for update of p
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
                    deadline=run.ready_at,
                    body=json.dumps(body),
                    hold=hold,
                    ir=config.input_rate,
                    orr=config.output_rate,
                    ordinal=run.attempts,
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


def consume(bind, config):
    with Session(bind) as db, db.begin():
        lock_scheduler(db)
        row = (
            query(
                db,
                """
            select a.*,t.client,t.brand,t.campaign from amc_ops.attempts a join amc_ops.tasks t using(run,step)
            where a.status<>'closed' and (a.status='reported' or not amc_ops.live(a.id))
            order by a.started limit 1 for update of a
        """,
            )
            .mappings()
            .first()
        )
        if not row:
            return False
        token = str(row["id"])
        scope = Scope(*(row[k] for k in ("tenant", "client", "brand", "campaign", "operator")))
        outcome, event, cost = "lease_expired", None, 0
        inputs = outputs = None
        if row["status"] == "offered":
            event = "unsent"
        if row["status"] == "reported" and query(db, "select amc_ops.fence(:id)", id=token).scalar():
            result, error = row["result"], row["error"]
            if result is not None and (not isinstance(result, list) or len(result) != 3):
                result, error = None, "invalid_usage"
            # Price at the rates captured at reservation, even after a restart or a rate change.
            priced = replace(config, input_rate=row["input_rate"], output_rate=row["output_rate"])
            task = (row["run"], token, row["body"])
            node = node_for_slot(db, row["run"], row["step"]) if row["node_id"] else None
            if finish(db, scope, priced, task, result, error, node=node, commit=False):
                run = db.get(WorkforceRun, row["run"])
                entry = run.journal[-1]
                outcome = entry["outcome"]
                if "estimated_microusd" in entry:
                    event, cost = "usage", entry["estimated_microusd"]
                    inputs, outputs = entry["input_tokens"], entry["output_tokens"]
                if outcome == "ok":
                    query(db, "update amc_ops.tasks set done=true where run=:run and step=:step", run=row["run"], step=row["step"])
        if outcome == "lease_expired":
            outcome = query(db, "select amc_ops.retire(:id)", id=token).scalar()
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
    from .main import app  # noqa: F401 - load ORM relationships

    bind = create_engine(os.environ["AMC_DISPATCH_URL"], pool_pre_ping=True)
    config = Gateway.configured()
    if config.provider != "local":
        raise ValueError("Pool supports local inference only")
    while True:
        if not consume(bind, config) and not dispatch(bind, config):
            time.sleep(0.5)


if __name__ == "__main__":
    main()
