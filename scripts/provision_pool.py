"""Provision dedicated PostgreSQL LOGINs or bind an existing pool worker to one campaign."""

import argparse
import os
import re
from uuid import uuid4

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


def internal_route(conn, worker, tenant, client, brand, campaign):
    """Bind an infrastructure-only editor without a mailbox, user session, or sibling workspace."""
    scope = conn.execute("""select t.id from tenants t join clients c on c.tenant_id=t.id
        join brands b on (b.tenant_id,b.client_id)=(t.id,c.id)
        join campaigns k on (k.tenant_id,k.brand_id)=(t.id,b.id)
        where t.mode='inhouse' and (t.id,c.id,b.id,k.id)=(%s,%s,%s,%s) for update of t""",
        (tenant, client, brand, campaign)).fetchone()
    if not scope:
        raise ValueError("Expected an exact inhouse campaign scope")
    record = conn.execute("select user_id from amc_c3.worker_operators where tenant_id=%s", (tenant,)).fetchone()
    if record:
        operator = record[0]
    else:
        operator = str(uuid4())
        # No credential is ever generated. Web login explicitly rejects this reserved non-hash.
        conn.execute("""insert into users(id,email,password_hash,created_at) values (%s,%s,'!amc-worker',now())""",
                     (operator, f"{operator}@operator.invalid"))
        conn.execute("insert into memberships(tenant_id,user_id,role) values(%s,%s,'editor')", (tenant, operator))
        conn.execute("insert into amc_c3.worker_operators values(%s,%s)", (tenant, operator))
    route(conn, worker, tenant, client, brand, campaign, operator)
    return operator


def inventory(conn, names):
    if not names or len(set(names)) != len(names):
        raise ValueError("List one dedicated dispatcher login per replica")
    for name in names:
        if not conn.execute("""select r.rolcanlogin and exists(select from pg_auth_members m
            where m.member=r.oid and m.roleid='amc_dispatch'::regrole) from pg_roles r where r.rolname=%s""",(name,)).fetchone() == (True,):
            raise ValueError("Unknown dispatcher login")
    conn.execute("""insert into amc_ops.dispatcher_inventory(singleton,expected) values(true,%s::name[])
        on conflict(singleton) do update set expected=excluded.expected,recorded_at=clock_timestamp()""",(names,))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    logins = sub.add_parser("login")
    logins.add_argument("name")
    logins.add_argument("group", choices=["amc_pool_worker", "amc_dispatch"])
    roster = sub.add_parser("inventory", help="Declare the complete dispatcher roster for this database")
    roster.add_argument("names", nargs="+")
    routes = sub.add_parser("route")
    for key in ("worker", "tenant", "client", "brand", "campaign", "operator"):
        routes.add_argument(key)
    internal = sub.add_parser("internal-route", help="Bind an inhouse campaign to a non-interactive worker operator")
    for key in ("worker", "tenant", "client", "brand", "campaign"):
        internal.add_argument(key)
    args = vars(parser.parse_args())
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as conn:
        mode = args.pop("mode")
        if mode == "inventory":
            inventory(conn,args["names"])
        elif mode == "login":
            provision(conn, **args, password=os.environ["AMC_POOL_PASSWORD"])
        elif mode == "internal-route":
            internal_route(conn, **args)
        else:
            route(conn, **args)


if __name__ == "__main__":
    main()
