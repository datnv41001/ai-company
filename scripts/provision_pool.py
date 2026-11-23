"""Provision dedicated PostgreSQL LOGINs or bind an existing pool worker to one campaign."""

import argparse
import os
import re

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


def provision(conn, name, group, password):
    if group not in ("amc_pool_worker", "amc_dispatch") or not re.fullmatch(r"amc_ops_[a-z0-9_]{1,50}", name):
        raise ValueError("Use dedicated amc_ops_ login names")
    existing = conn.execute(
        """select rolcanlogin and not (rolsuper or rolbypassrls or rolcreaterole or rolcreatedb or rolreplication),
        array(select g.rolname from pg_auth_members m join pg_roles g on g.oid=m.roleid where m.member=r.oid)
        from pg_roles r where rolname=%s""",
        (name,),
    ).fetchone()
    if existing:
        if not existing[0] or existing[1] != [group]:
            raise ValueError("Existing login does not match requested dedicated role")
        # Detect a lost or mismatched .env.pool without rotating an existing login.
        with psycopg.connect(make_conninfo(conn.info.dsn, user=name, password=password)):
            pass
        return
    if len(password) < 24:
        raise ValueError("Pool login requires at least 24 characters")
    conn.execute(
        sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD {}").format(sql.Identifier(name), sql.Literal(password))
    )
    conn.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(group), sql.Identifier(name)))


def route(conn, worker, tenant, client, brand, campaign, operator):
    if not conn.execute("select pg_has_role(%s,'amc_pool_worker','member')", (worker,)).fetchone()[0]:
        raise ValueError("Expected registered worker")
    member = conn.execute("select role from memberships where tenant_id=%s and user_id=%s", (tenant, operator)).fetchone()
    if member != ("editor",):
        raise ValueError("Expected a dedicated editor")
    conn.execute(
        """insert into amc_ops.routes values(%s,%s,%s,%s,%s,%s)
        on conflict(worker,tenant,client,brand,campaign) do update set operator=excluded.operator""",
        (worker, tenant, client, brand, campaign, operator),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    logins = sub.add_parser("login")
    logins.add_argument("name")
    logins.add_argument("group", choices=["amc_pool_worker", "amc_dispatch"])
    routes = sub.add_parser("route")
    for key in ("worker", "tenant", "client", "brand", "campaign", "operator"):
        routes.add_argument(key)
    args = vars(parser.parse_args())
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as conn:
        if args.pop("mode") == "login":
            provision(conn, **args, password=os.environ["AMC_POOL_PASSWORD"])
        else:
            route(conn, **args)


if __name__ == "__main__":
    main()
