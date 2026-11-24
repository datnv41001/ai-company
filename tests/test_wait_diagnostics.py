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
        return tuple(lab.owner.execute("select * from amc_ops." + table + " order by 1").fetchall()
                     for table in ("attempts","ledger","readiness","dag_nodes"))
    before = snapshot()
    def get():
        result = lab.api.get(path, headers=admin["headers"])
        result.raise_for_status()
        return {row["node_id"]:row for row in result.json()["nodes"]}
    rows = get()
    assert "telemetry_unknown" in rows["n01"]["wait_reasons"]
    assert "adapter_unavailable" not in rows["n01"]["wait_reasons"]
    assert "dependency_pending" in rows["n02"]["wait_reasons"]
    assert snapshot() == before
    with psycopg.connect(lab.logins[0][1]) as dispatcher:
        assert dispatcher.execute("select count(*) from amc_ops.candidates() where run=%s and step=1",(rid,)).fetchone()[0] > 0
    assert rows["n01"]["candidate"]
    with lab.bind.begin() as db:
        from app.scheduler_telemetry import dispatcher_heartbeat
        dispatcher_heartbeat(db,lab.config)
        assert db.scalar(text("select count(*) from amc_ops.pool_heartbeats")) >= 1
