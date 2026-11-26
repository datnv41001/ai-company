"""Upgrade a populated #55 core-v26 desk in place and reopen its pre-upgrade dump using #55."""
import argparse
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from sqlalchemy.engine import make_url

from check_c3_cutover import PUBLISH, ROOT, unpack
from check_sandbox_journal import archive_tool, host

PREVIOUS = "c5c6329599a66fd2dc6011428e7ab8eed9208df4"


def run(container=None, physical_copy=False):
    admin_dsn = os.environ["AMC_MIGRATION_DSN"]
    runtime = make_url(os.environ["DATABASE_URL"])
    assert os.getenv("AMC_TEST_PG") == "1" and runtime.username == "amc_runtime"
    assert runtime.host in {"localhost", "127.0.0.1", "::1"} and runtime.database.startswith("amc_test")
    with psycopg.connect(admin_dsn, autocommit=True) as admin, TemporaryDirectory() as tmp:
        assert (admin.info.host, admin.info.dbname) == (runtime.host, runtime.database)
        base = Path(tmp)
        old = unpack(PREVIOUS, base)
        backup = base / "pre-consultation.dump"
        env = {**os.environ, "PGUSER": admin.info.user, "PGPASSWORD": admin.info.password or "",
               "PGHOST": admin.info.host, "PGPORT": str(admin.info.port), "AMC_DEV_MAILBOX_DIR": str(base / "mail")}
        env.pop("PYTHONPATH", None)
        def config(name):
            return {**env, "DATABASE_URL":runtime.set(database=name).render_as_string(hide_password=False),
                    "AMC_MIGRATION_DSN":make_conninfo(admin_dsn, dbname=name)}

        def history(settings):
            with psycopg.connect(settings["AMC_MIGRATION_DSN"]) as db:
                marker = db.execute("SELECT obj_description('amc_acl.campaign_desk(text,text)'::regprocedure,'pg_proc')").fetchone()[0]
                rows = db.execute("SELECT id, operation, result FROM knowledge_commands ORDER BY id").fetchall()
                return marker, rows

        inserted = []
        try:
            test, restored = ["amc_test_consult_" + uuid4().hex[:12] for _ in range(2)]
            for name in ((test,) if physical_copy else (test, restored)):
                admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
                inserted.append(name)
            active = config(test)
            subprocess.run(PUBLISH, cwd=old, env=active, check=True)
            with host(old, active) as (_, previous):
                seed = previous({"seed":True})
                query = {"method":"GET","url":seed["root"] + "/sandbox","headers":seed["headers"]}
                before = previous(query)
                assert before["status"] == 200 and before["data"]["receipts"]
            old_marker, rows = history(active)
            assert old_marker != "campaign-role-desk/2" and rows
            if physical_copy:
                admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(restored), sql.Identifier(test)))
                inserted.append(restored)
            else:
                archive_tool("pg_dump", test, backup, active, container)
            for _ in range(2):
                subprocess.run(PUBLISH, cwd=ROOT, env=active, check=True)
                assert history(active) == ("campaign-role-desk/2", rows)
            with host(ROOT, active) as (_, current):
                after = current(query)
                assert after["status"] == 200 and after["data"]["receipts"] == before["data"]["receipts"]
            if not physical_copy:
                archive_tool("pg_restore", restored, backup, config(restored), container)
            assert history(config(restored)) == (old_marker, rows)
            with host(old, config(restored)) as (_, previous):
                replay = previous(query)
                assert replay["status"] == 200 and replay["data"]["receipts"] == before["data"]["receipts"]
            method = "physical database copy" if physical_copy else "pg_dump/pg_restore"
            print(f"PASS consultation cutover: #55 v26, repeated desk/2 publisher, {len(rows)} journal rows, old API on {method}")
        finally:
            for name in reversed(inserted):
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container")
    parser.add_argument("--physical-copy", action="store_true", help="Use an offline native copy on a machine without archive client tools")
    args = parser.parse_args()
    run(args.container, args.physical_copy)
