"""Read-only inventory for a local development cluster, with identifiers omitted from output."""
from collections import Counter
from datetime import datetime, timezone
import json
import os

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo


def inventory(dsn):
    args = conninfo_to_dict(dsn)
    if args.get("host") not in {"127.0.0.1", "::1", "localhost"} or args.get("service") or args.get("hostaddr") not in {None, "127.0.0.1", "::1"}:
        raise ValueError("Supply an explicit loopback development connection.")
    dsn = make_conninfo(dsn, options="-c default_transaction_read_only=on", connect_timeout=3)
    with psycopg.connect(dsn) as conn:
        roles = {r[0] for r in conn.execute("select rolname from pg_roles where rolcanlogin and rolname ~ '^amc_ops_[0-9a-f]{10}$'")}
        cfg = {name:int(value) for name,value in conn.execute("select name,setting from pg_settings where name in ('max_connections','reserved_connections','superuser_reserved_connections')")}
        sessions = conn.execute("select usename,datname,coalesce(state,'unknown') from pg_stat_activity where backend_type='client backend'").fetchall()
        databases = [r[0] for r in conn.execute("select datname from pg_database where datallowconn and not datistemplate")]
    routed, routes, unreadable = set(), 0, 0
    for database in databases:
        try:
            with psycopg.connect(make_conninfo(dsn, dbname=database)) as conn:
                if conn.execute("select to_regclass('amc_ops.routes')").fetchone()[0]:
                    for name, count in conn.execute("select worker,count(*) from amc_ops.routes group by worker"):
                        routed.add(name)
                        routes += count
        except psycopg.Error:
            unreadable += 1
    connected = {row[0] for row in sessions}
    return {"time_utc":datetime.now(timezone.utc).isoformat(), "settings":cfg, "ordinary_slots_available":
            cfg["max_connections"]-cfg["superuser_reserved_connections"]-cfg.get("reserved_connections",0)-len(sessions),
            "sessions_by_scope_and_state":dict(Counter(("test" if (n or "").startswith("amc_test") else "shared") + ":" + s for _,n,s in sessions)),
            "readable_databases":len(databases)-unreadable, "unreadable_databases":unreadable, "total_route_rows":routes,
            "matching_logins":len(roles), "matching_connected":len(roles & connected), "matching_routed":len(roles & routed),
            "matching_idle_and_unrouted":len(roles-routed-connected)}


if __name__ == "__main__":
    print(json.dumps(inventory(os.environ["AMC_MIGRATION_DSN"]), indent=2))
