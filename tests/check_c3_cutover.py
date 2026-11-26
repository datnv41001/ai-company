"""Qualify the C3 cutover against real pinned API and publisher binaries on an empty synthetic database."""
import argparse
from contextlib import contextmanager
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

import psycopg
import pytest
from sqlalchemy import create_engine

from app.database import prepare_database
from migrations.apply import migrate
from check_publisher_order import fingerprint

ROOT = Path(__file__).resolve().parents[1]
MAIN = "9bfbabcaddf9818eb4030cb0c5337e65e794ebfe"
REVIEWED = "58258de5c802f1af3ad19d3491d63cf9f7b49e8a"
TABLES = ("deliverables", "client_reviews", "review_entries", "workforce_runs", "knowledge_revisions",
          "knowledge_snapshots", "amc_ops.ledger", "amc_acl.session_keys")
PUBLISH = [sys.executable, "-m", "migrations.apply"]
STARTUP = [sys.executable, "-c", "from fastapi.testclient import TestClient; from app.main import app\n"
           "with TestClient(app) as c: assert c.get('/api/health').status_code==200"]
# Keep the same API process, pool connection and open transaction across cutover.
# Zero-row statements only probe protocol enforcement. No client object is mutated.
LIVE = """
import json
import sys
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from app.access import set_context
from app.main import app
from app.database import engine
with TestClient(app) as client, engine.connect() as connection, Session(connection) as db:
    assert client.get('/api/health').status_code==200
    set_context(db, actor='cutover-probe')
    def execute(sql):
        return db.connection().exec_driver_sql(sql)
    pid=execute('SELECT pg_backend_pid()').scalar_one()
    protocol=execute("SELECT current_setting('amc.delivery_protocol',true)").scalar_one()
    print('ready',flush=True)
    for request in sys.stdin:
        if request.strip()=='stop': break
        if request.startswith('{'):
            # Only the test controller can write this private pipe. Exercise the pinned
            # binary's ordinary FastAPI routes; return the refusal code, never credentials.
            args=json.loads(request)
            try:
                response=client.request(**args)
                result=str(response.status_code)
            except DBAPIError as error:
                result=str(error.orig.sqlstate)
            print(result,flush=True)
            continue
        if request.strip()=='protocol':
            print(protocol or 'undeclared',flush=True)
            continue
        assert execute('SELECT pg_backend_pid()').scalar_one()==pid
        outcomes=[]
        for table in ('deliverables','client_reviews','review_entries'):
            try:
                with db.begin_nested():
                    result=execute('INSERT INTO public.'+table+' (id) SELECT id FROM public.'+table+' WHERE false')
                    assert result.rowcount==0
            except DBAPIError as error:
                outcomes.append(error.orig.sqlstate)
            else:
                outcomes.append('allowed-zero')
        db.commit()
        print(','.join(outcomes),flush=True)
"""


def unpack(pin, root):
    folder = root / pin[:8]
    folder.mkdir()
    archive = subprocess.check_output(["git", "archive", pin, "app", "migrations", "catalog", "tests", "scripts",
                                       "requirements.txt", "requirements-registry.txt", "pyproject.toml"], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(folder, filter="data")
    return folder


@contextmanager
def running_api(old, env):
    with subprocess.Popen([sys.executable, "-u", "-c", LIVE], cwd=old, env=env, text=True,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        try:
            assert proc.stdout.readline().strip() == "ready"
            def probe(command="probe"):
                proc.stdin.write(command+"\n")
                proc.stdin.flush()
                return proc.stdout.readline().strip()
            yield probe
        finally:
            if proc.poll() is None:
                proc.stdin.write("stop\n")
                proc.stdin.flush()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def snapshot(db):
    return {table: db.execute(f"SELECT to_jsonb(t) FROM {table} t ORDER BY to_jsonb(t)").fetchall()
            for table in TABLES}


def refuse(cmd, old, env, reason):
    result = subprocess.run(cmd, cwd=old, env=env, capture_output=True)
    assert result.returncode and reason in result.stderr, (cmd[:3], result.returncode)


def run(phase):
    dsn = os.environ["AMC_MIGRATION_DSN"]
    runtime = create_engine(os.environ["DATABASE_URL"])
    with psycopg.connect(dsn) as db:
        assert os.getenv("AMC_TEST_PG") == "1" and runtime.url.username == "amc_runtime"
        assert db.info.host in {"localhost", "127.0.0.1", "::1"} and db.info.dbname.startswith("amc_test")
        assert db.info.dbname == runtime.url.database and runtime.url.host == db.info.host
        assert db.execute("SELECT to_regclass('amc_schema_versions')").fetchone() == (None,)
    with tempfile.TemporaryDirectory(prefix="c3-cutover-") as directory:
        tmp = Path(directory)
        old = unpack(MAIN, tmp)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AMC_DEV_MAILBOX_DIR=str(tmp / "mail"))
        env.pop("PYTHONPATH", None)
        subprocess.run(PUBLISH, cwd=old, env=env, check=True)
        with pytest.raises(RuntimeError, match="schema migrations"):
            prepare_database(runtime)
        if phase == "qualification":
            subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short", "--maxfail=1",
                            "tests/test_knowledge_commercial.py::test_cross_scope_binding_and_snapshot_history[postgres]",
                            "tests/test_research_strategy.py::test_research_scope_provenance_and_strategy_snapshot"],
                           cwd=old, env=env, check=True)
        with running_api(old, env) as probe:
            if phase == "observation":
                reviewed = unpack(REVIEWED, tmp)
                subprocess.run(PUBLISH, cwd=reviewed, env=env, check=True)
                subprocess.run(STARTUP, cwd=old, env=env, check=True)
                observed = probe()
                assert observed == "allowed-zero,allowed-zero,allowed-zero", observed
                with psycopg.connect(dsn) as db:
                    assert db.execute("SELECT version FROM amc_c3.versions").fetchall() == [(1,)]
                print(f"RED observed {MAIN} API starts after {REVIEWED} migration; live API has no writer fence on 3 zero-row statements")
                return
            with psycopg.connect(dsn) as db:
                before = snapshot(db)
                assert all(before.values()), {k:len(v) for k,v in before.items()}
                db.execute("ALTER TABLE amc_schema_versions ADD CONSTRAINT cutover_rollback_test CHECK(version<>25)")
            with pytest.raises(psycopg.errors.CheckViolation):
                migrate(dsn)
            with psycopg.connect(dsn) as db:
                assert db.execute("SELECT max(version),to_regnamespace('amc_c3') FROM amc_schema_versions").fetchone() == (24,None)
                assert snapshot(db) == before
                db.execute("ALTER TABLE amc_schema_versions DROP CONSTRAINT cutover_rollback_test")
            migrate(dsn)
            prepare_database(runtime)
            observed = probe()
            assert observed == "55000,55000,55000", observed
            refuse(STARTUP, old, env, b"schema migrations")
            with psycopg.connect(dsn) as db:
                assert snapshot(db) == before
                witness = fingerprint(db)
            refuse(PUBLISH, old, env, b"Unknown schema version")
            migrate(dsn)
            with psycopg.connect(dsn) as db:
                assert fingerprint(db) == witness and snapshot(db) == before
            subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short", "--maxfail=1",
                            "tests/test_c3_content_gate.py::test_published_content_gate"],
                           cwd=ROOT, env=env, check=True)
            print("GREEN v24 to v26, 3 live-writer denials, predecessor startup/replay denied, new runtime started,"
                  " rollback and historical rows preserved", {k:len(v) for k,v in before.items()})
    runtime.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["observation", "qualification"])
    run(parser.parse_args().phase)
