"""A populated v13 frozen graph with two live leases across the v14 upgrade."""

from uuid import uuid4

from psycopg.types.json import Jsonb
from app.dynamic_plan import compile_plan


def seed(db):
    rid = "dynamic-run"
    db.execute(
        """update workforce_runs set knowledge=(knowledge::jsonb || '{"max_parallel_nodes":2}'::jsonb)::json,
                 reserved_microusd=700 where id=%s""",
        (rid,),
    )
    contract, digest = compile_plan(
        {
            "nodes": [
                {"key": key, "skill_type": "content", "assignment": "Draft a sourced notebook page for " + key, "parents": []} for key in ("copy", "email")
            ]
        },
        ["content"],
    )
    db.execute("update amc_ops.dag_plans set contract=%s,digest=%s where run=%s", (Jsonb(contract), digest, rid))
    db.execute(
        """update amc_ops.dag_nodes set checkpoint='{"output":{"plan_digest":"v13-fixture"}}'
                  where run=%s and node_id='director'""",
        (rid,),
    )
    for slot in (1, 2):
        node, token = f"n0{slot}", uuid4()
        db.execute(
            """insert into amc_ops.tasks(tenant,client,brand,campaign,run,step,skill)
            values('agency','a','br','ca',%s,%s,'content')""",
            (rid, slot),
        )
        db.execute(
            """insert into amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id,position,slot,skill_type)
            values('agency','a','br','ca',%s,1,%s,%s,%s,'content')""",
            (rid, node, slot, slot),
        )
        db.execute("insert into amc_ops.dag_edges values('agency','a','br','ca',%s,1,%s,'director')", (rid, node))
        db.execute(
            """insert into amc_ops.attempts(id,run,step,worker,operator,tenant,month,deadline,body,
            status,reserved,ordinal,input_rate,output_rate,node_id,plan_revision)
            values(%s,%s,%s,%s,'alice','agency','2026-11-01',now()+interval '1 hour','{}','sent',350,1,0,0,%s,1)""",
            (token, rid, slot, f"registry-upgrade-{slot}", node),
        )
        db.execute(
            """insert into amc_ops.ledger(id,tenant,month,event,actor,held,spent)
            values(%s,'agency','2026-11-01','hold','dispatcher',350,0)""",
            (token,),
        )

    db.execute(
        """insert into amc_ops.dag_nodes(tenant,client,brand,campaign,run,revision,node_id,position,skill_type)
                  values('agency','a','br','ca',%s,1,'join',3,'join')""",
        (rid,),
    )
    for parent in contract["join"]:
        db.execute("insert into amc_ops.dag_edges values('agency','a','br','ca',%s,1,'join',%s)", (rid, parent))


def snapshot(db):
    return [
        db.execute(query).fetchall()
        for query in (
            "select * from amc_ops.attempts order by id",
            "select to_jsonb(n) from amc_ops.dag_nodes n order by run,position",
            "select * from amc_ops.dag_plans order by run",
            "select * from amc_ops.ledger order by seq",
            "select knowledge::text,journal::text,checkpoints::text,state,lease,ready_at,reserved_microusd from workforce_runs order by id",
        )
    ]
