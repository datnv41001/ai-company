"""Rehearse the Studio field-review protocol upgrade in a disposable PostgreSQL database."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import psycopg
import pytest
from sqlalchemy import create_engine

from app.database import prepare_database
from check_c3_cutover import PUBLISH, ROOT, STARTUP, refuse, running_api, snapshot, unpack
from check_publisher_order import fingerprint
from migrations.apply import migrate

PREDECESSOR = "64964aab4f954e3a25bb7b7849fe77a11bfdf5c5"


def run(from_studio_v2=False):
    previous = "eb64af438f0a418ed5c951b20387e1d5bf7d982f" if from_studio_v2 else PREDECESSOR
    old_version = 2 if from_studio_v2 else 1
    next_version = old_version + 1
    dsn = os.environ["AMC_MIGRATION_DSN"]
    runtime = create_engine(os.environ["DATABASE_URL"])
    with psycopg.connect(dsn) as db:
        assert os.getenv("AMC_TEST_PG") == "1" and runtime.url.username == "amc_runtime"
        assert db.info.host in {"localhost", "127.0.0.1", "::1"} and db.info.dbname.startswith("amc_test")
        assert db.info.dbname == runtime.url.database and runtime.url.host == db.info.host
        assert db.execute("SELECT to_regclass('amc_schema_versions')").fetchone() == (None,)
    with tempfile.TemporaryDirectory(prefix="studio-cutover-") as directory:
        tmp = Path(directory)
        old = unpack(previous, tmp)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AMC_DEV_MAILBOX_DIR=str(tmp / "mail"))
        env.pop("PYTHONPATH", None)
        subprocess.run(PUBLISH, cwd=old, env=env, check=True)
        with pytest.raises(RuntimeError, match="delivery writer fence"):
            prepare_database(runtime)
        subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short", "--maxfail=1",
                        "tests/test_c3_content_gate.py::test_published_content_gate",
                        "tests/test_research_strategy.py::test_research_scope_provenance_and_strategy_snapshot"],
                       cwd=old, env=env, check=True)
        with running_api(old, env) as probe, psycopg.connect(dsn, autocommit=True) as db:
            assert probe("protocol") == f"c3/{old_version}"
            assert probe() == "allowed-zero,allowed-zero,allowed-zero"
            before = snapshot(db)
            assert all(before.values()), {t:len(v) for t,v in before.items()}
            db.execute(f"ALTER TABLE amc_c3.versions ADD CONSTRAINT studio_rollback_test CHECK(version<>{next_version})")
            with pytest.raises(psycopg.errors.CheckViolation):
                migrate(dsn)
            assert db.execute("SELECT to_regprocedure('amc_acl.lock_c3_reviewer(text,text)')").fetchone() == (None,)
            assert db.execute("SELECT max(version) FROM amc_c3.versions").fetchone() == (old_version,)
            assert snapshot(db) == before
            assert probe() == "allowed-zero,allowed-zero,allowed-zero"
            db.execute("ALTER TABLE amc_c3.versions DROP CONSTRAINT studio_rollback_test")
            migrate(dsn)
            prepare_database(runtime)
            assert probe() == "55000,55000,55000"
            assert db.execute("SELECT version FROM amc_c3.versions ORDER BY version").fetchall() == [(1,), (2,), (3,)]
            refuse(STARTUP, old, env, b"delivery writer fence")
            refuse(PUBLISH, old, env, b"Unsupported C3 task schema version")
            witness = fingerprint(db)
            migrate(dsn)
            assert snapshot(db) == before and fingerprint(db) == witness
            with running_api(ROOT, env) as current:
                assert current("protocol") == "c3/3"
                assert current() == "allowed-zero,allowed-zero,allowed-zero"
    runtime.dispose()
    print(f"PASS Studio core v25 C3 v{old_version} to v3: three c3/{old_version} writer denials, c3/3 accepted,"
          " startup and publisher refused, atomic rollback and replay, rows preserved",
          {t:len(v) for t,v in before.items()})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-studio-v2", action="store_true")
    run(parser.parse_args().from_studio_v2)
