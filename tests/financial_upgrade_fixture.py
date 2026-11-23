"""Populated v9 history for the v10 migration. All IDs refer to the synthetic upgrade agency."""

from uuid import uuid4


def seed(conn):
    billed, active = uuid4(), uuid4()
    conn.execute("insert into amc_ops.agencies(tenant,capacity) values ('agency',2)")
    conn.execute("insert into amc_ops.periods values ('agency','2026-10-01',2000), ('agency','2026-11-01',2000)")
    conn.execute("""insert into workforce_briefs(id,tenant_id,client_id,brand_id,campaign_id,recipient_id,title,created_at)
        values('pool-brief','agency','a','br','ca','current','Synthetic v9 brief',now())""")
    conn.execute(
        """insert into workforce_runs(id,tenant_id,client_id,brand_id,campaign_id,brief_id,knowledge,plan,
        checkpoints,journal,state,lease,ready_at,attempts,budget_microusd,reserved_microusd,created_at)
        values ('pool-run','agency','a','br','ca','pool-brief','{}','["director"]','[]','[]','running',%s,
        now()+interval '1 hour',2,2000,1100,now())""",
        (str(active),),
    )
    for attempt, month, status, ordinal, hold in [(billed, "2026-10-01", "closed", 1, 700), (active, "2026-11-01", "offered", 2, 400)]:
        conn.execute(
            """insert into amc_ops.attempts(id,run,step,worker,operator,tenant,month,deadline,body,
            status,reserved,ordinal,input_rate,output_rate)
            values (%s,'pool-run',0,'fixture-worker','alice','agency',%s,now()+interval '1 hour','{}',%s,%s,%s,0,0)""",
            (attempt, month, status, hold, ordinal),
        )
        conn.execute(
            """insert into amc_ops.ledger(id,tenant,month,event,actor,held,spent)
            values(%s,'agency',%s,'hold','dispatcher',%s,0)""",
            (attempt, month, hold),
        )
    conn.execute(
        """insert into amc_ops.ledger(id,tenant,month,event,actor,held,spent,absolute_cost,receipt)
        values(%s,'agency','2026-10-01','receipt','alice',-700,350,350,'v9-invoice')""",
        (billed,),
    )
    return active, conn.execute("select * from amc_ops.ledger order by seq").fetchall()


def verify(conn, before):
    active, ledger = before
    assert conn.execute("select * from amc_ops.ledger order by seq").fetchall() == ledger
    assert conn.execute("select reserved_microusd,lease,state from workforce_runs where id='pool-run'").fetchone() == (750, str(active), "running")
    assert conn.execute("select status from amc_ops.attempts where id=%s", (active,)).fetchone() == ("offered",)
