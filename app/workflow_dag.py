"""DAG adapter for the trusted dispatcher. Node slots only bridge the v10 attempt ledger."""

from dataclasses import dataclass
import json

from sqlalchemy import text


@dataclass(frozen=True)
class Node:
    id: str
    revision: int
    attempts: int
    last_error: str | None
    skill: str
    template: str
    assignment: str | None
    parallel: bool


def node_for_slot(db, run, slot):
    row = db.execute(
        text("""
        select n.node_id,n.revision,h.tries,h.last_error,coalesce(n.skill_type,n.node_id),g.template,n.assignment,amc_ops.parallel_node(n.run,n.slot)
        from amc_ops.dag_nodes n join amc_ops.dag_plans g using(run) cross join lateral (
            select count(*) tries,(array_agg(a.outcome order by a.started desc))[1] last_error
            from amc_ops.attempts a where a.run=n.run and a.node_id=n.node_id and a.status='closed'
            and not exists(select from amc_ops.ledger l where l.id=a.id and l.event='unsent')
        ) h where n.run=:run and n.slot=:slot
    """),
        {"run": run, "slot": slot},
    ).first()
    return Node(*row) if row else None


def inputs(db, run, node):
    rows = db.execute(
        text("""
        select p.node_id,p.checkpoint from amc_ops.dag_edges e
        join amc_ops.dag_nodes p on (p.run,p.node_id)=(e.run,e.parent)
        where e.run=:run and e.child=:node order by p.position
    """),
        {"run": run, "node": node.id},
    )
    earlier = {skill: checkpoint["output"]["text"][:1400] for skill, checkpoint in rows if skill != "director"}
    if node.template == "dynamic-v1":
        return earlier, node.assignment or ""
    assignment = ""
    if node.id != "director":
        director = db.scalar(text("select checkpoint from amc_ops.dag_nodes where run=:r and node_id='director'"), {"r": run})
        assignment = director["output"]["assignments"][node.id]
    return earlier, assignment


def freeze(db, token, contract, digest):
    db.execute(text("select amc_ops.freeze_dynamic(:token,cast(:contract as jsonb),:digest)"),
               {"token": token, "contract": json.dumps(contract, ensure_ascii=False), "digest": digest})


def checkpoint(db, run, node, record):
    params = {"r": run.id, "v": node.revision, "n": node.id, "cp": json.dumps(record, ensure_ascii=False)}
    db.execute(
        text("""
        update amc_ops.dag_nodes set checkpoint=cast(:cp as jsonb) where run=:r and revision=:v
        and node_id=:n and checkpoint is null and amc_ops.dag_ready(:r,:n) returning node_id
    """),
        params,
    ).scalar_one()
    # This canonical projection is the source for revision QA and the client-visible preview.
    run.checkpoints = list(
        db.scalars(
            text("""select checkpoint from amc_ops.dag_nodes
        where run=:r and revision=:v and node_id<>'join' and checkpoint is not null order by position"""),
            params,
        )
    )
    return (
        db.execute(
            text("""update amc_ops.dag_nodes set checkpoint=jsonb_build_object('joined',true)
        where run=:r and revision=:v and node_id='join' and checkpoint is null and amc_ops.dag_ready(:r,'join')
        returning node_id"""),
            params,
        ).scalar()
        is not None
    )
