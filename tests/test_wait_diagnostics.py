"""Diagnostics use the scoped API and the same database state as pool admission."""

import psycopg
from sqlalchemy import text
from test_registry import PG, pool as registry_pool, frozen_run

pool = registry_pool


@PG
def test_waits_are_scoped_read_only_and_coverage_is_explicit(pool):
    lab = pool
    rid = frozen_run(lab)
    base, admin, reader, *_ = lab.cases[0]
    path = base + "/workforce/runs/" + rid + "/wait-diagnostics"
    for actor in (reader, lab.cases[1][2], lab.y):
        assert lab.api.get(path, headers=actor["headers"]).status_code == 404

    def snapshot():
        return tuple(
            lab.owner.execute("select to_jsonb(t)::text from amc_ops." + table + " t order by 1").fetchall()
            for table in ("attempts", "ledger", "readiness", "dag_nodes")
        )

    before = snapshot()

    def get():
        result = lab.api.get(path, headers=admin["headers"])
        result.raise_for_status()
        return {row["node_id"]: row for row in result.json()["nodes"]}

    rows = get()
    assert "telemetry_unknown" in rows["n01"]["wait_reasons"]
    assert "adapter_unavailable" not in rows["n01"]["wait_reasons"]
    assert "dependency_pending" in rows["n02"]["wait_reasons"]
    assert snapshot() == before
    with psycopg.connect(lab.logins[0][1]) as dispatcher:
        assert dispatcher.execute("select count(*) from amc_ops.candidates() where run=%s and step=1", (rid,)).fetchone()[0] > 0
    assert rows["n01"]["candidate"]
    with lab.bind.begin() as db:
        from app.scheduler_telemetry import dispatcher_heartbeat

        dispatcher_heartbeat(db, lab.config)
        assert db.scalar(text("select count(*) from amc_ops.pool_heartbeats")) >= 1


@PG
def test_budget_busy_capacity_and_report_match_admission(pool):
    from dataclasses import replace
    from app.pool_dispatch import dispatch
    from app.pool_worker import report
    from app.scheduler_telemetry import capabilities, dispatcher_heartbeat, worker_heartbeat
    from scripts.provision_pool import inventory
    from test_role_qa import PAGE
    import json

    lab = pool
    rid = frozen_run(lab)
    # Retire the two competing scheduler sessions used by frozen_run.
    lab.bind.dispose()
    base, admin, *_ = lab.cases[0]
    path = base + "/workforce/runs/" + rid + "/wait-diagnostics"

    def waits():
        response = lab.api.get(path, headers=admin["headers"])
        response.raise_for_status()
        return {n["node_id"]: n for n in response.json()["nodes"]}

    def beat(config):
        with lab.bind.begin() as db:
            dispatcher_heartbeat(db, config)
        for w in lab.workers:
            worker_heartbeat(w.conn, config)

    inventory(lab.owner, [lab.logins[0][0]])
    # Synthetic positive rates exercise a real Gateway.price calculation without model calls.
    priced = replace(lab.config, input_rate=1000, output_rate=1000)
    beat(priced)
    lab.limit_x(0)
    first = waits()["n01"]
    assert first["candidate"] and "budget_insufficient" in first["wait_reasons"]
    assert not dispatch(lab.bind, priced)
    lab.limit_x(10000)
    assert "budget_insufficient" not in waits()["n01"]["wait_reasons"]
    assert dispatch(lab.bind, priced)
    worker, job = next((w, j) for w in lab.workers if (j := w.take()))
    assert report(worker.conn, job, [{**PAGE, "source_ids": ["brand"]}, 60, 20])
    # Same login/connection, different reviewed executable capabilities during rollout.
    caps = capabilities(priced)
    caps["adapters"].pop("content@1")
    with lab.bind.begin() as db:
        db.execute(text("select amc_ops.heartbeat('dispatcher',cast(:c as jsonb))"), {"c": json.dumps(caps)})
    held = lab.balance_x()
    assert waits()["n01"]["wait_reasons"] == ["report_waiting_adapter"]
    lab.owner.execute("update amc_ops.pool_heartbeats set observed_at=now()-interval '1 minute' where kind='dispatcher'")
    assert "telemetry_unknown" in waits()["n01"]["wait_reasons"] and "report_waiting_adapter" not in waits()["n01"]["wait_reasons"]
    assert lab.balance_x() == held
    beat(priced)
    assert lab.consume()
    # Multiple independently true constraints on the next node.
    lab.owner.execute("update amc_ops.periods set ceiling=0 where tenant=%s", (admin["tenant"],))
    lab.owner.execute("update amc_ops.dag_nodes set ready_at=now()+interval '1 minute' where run=%s and node_id='n02'", (rid,))
    row = waits()["n02"]
    assert {"budget_insufficient", "retry_backoff"} <= set(row["wait_reasons"]) and not row["candidate"]
    assert not dispatch(lab.bind, priced)


@PG
def test_readonly_sql_and_partial_roster(pool):
    from app.scheduler_telemetry import capabilities
    from scripts.provision_pool import inventory
    import os
    import json

    lab = pool
    rid = frozen_run(lab)
    # Retire the two competing scheduler sessions used by frozen_run.
    lab.bind.dispose()
    base, admin, reader, *_ = lab.cases[0]
    other, _ = lab.login("amc_dispatch")
    names = [lab.logins[0][0], other]
    caps = capabilities(lab.config)
    caps["adapters"] = {}
    with lab.bind.begin() as db:
        db.execute(text("select amc_ops.heartbeat('dispatcher',cast(:c as jsonb))"), {"c": json.dumps(caps)})
    path = base + "/workforce/runs/" + rid + "/wait-diagnostics"

    def reasons():
        rows = lab.api.get(path, headers=admin["headers"]).json()["nodes"]
        return next(n["wait_reasons"] for n in rows if n["node_id"] == "n01")

    inventory(lab.owner, names)
    assert "telemetry_unknown" in reasons() and "adapter_unavailable" not in reasons()
    inventory(lab.owner, names[:1])
    assert "adapter_unavailable" in reasons()
    with psycopg.connect(os.environ["DATABASE_URL"].replace("+psycopg", "")) as conn:
        conn.execute("set transaction read only")
        for actor, expected in ((reader, False), (lab.cases[1][2], False), (lab.y, False), (admin, True)):
            conn.execute("select set_config('amc.user_id',%s,true),set_config('amc.tenant_id',%s,true)", (actor["id"], admin["tenant"]))
            snapshot = conn.execute("select amc_ops.wait_snapshot(%s,%s)", (admin["tenant"], rid)).fetchone()[0]
            assert (snapshot is not None) == expected
