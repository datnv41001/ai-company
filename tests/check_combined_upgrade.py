"""Upgrade one populated, pinned predecessor on a disposable loopback database."""
import argparse
import hmac
import io
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tarfile
import tempfile
from unittest.mock import patch

from fastapi import HTTPException
import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.access import set_context
from app.database import prepare_database
from app.security import sign_actor
from app.session_state import active
from migrations.apply import migrate
from migrations.combined_contract import COMMERCIAL_CURRENT, DESK_CURRENT
from check_publisher_order import fingerprint

ROOT = Path(__file__).resolve().parents[1]
PINS = {"c2": "068b85170cf47106c8d08a8c573548e3f530647c", "a1": "322752384813b959515eb9bbb677199326a4fb74"}
COMMON = ["tests/test_knowledge_commercial.py::test_cross_scope_binding_and_snapshot_history[postgres]",
          "tests/test_research_strategy.py::test_research_scope_provenance_and_strategy_snapshot"]
CASES = {
    "c2": ["tests/test_business_workspace.py::test_partial_inheritance_pinned_brief_and_recovery[postgres]",
           "tests/test_company_objectives.py::test_shared_company_brand_campaign_and_cross_scope[postgres]"],
    "a1": ["tests/test_device_sessions.py::test_device_owner_logout_and_legacy_cutover[postgres]",
           "tests/test_device_sessions.py::test_refresh_response_loss_reuse_and_csrf[postgres]"],
}
TABLES = ("deliverables", "client_reviews", "workforce_runs", "amc_ops.ledger", "amc_ops.attempts",
          "amc_acl.identity_windows", "knowledge_revisions", "knowledge_links", "knowledge_events", "knowledge_snapshots")
EXTRA = {"c2": ("business_workspace_records", "business_company_objectives", "business_company_objective_edges"),
         "a1": ("device_sessions", "used_refresh_grants", "amc_acl.session_keys")}


def unpack(line, dest):
    archive = subprocess.check_output(["git", "archive", PINS[line], "app", "migrations", "catalog", "tests", "scripts",
                                      "requirements.txt", "requirements-registry.txt", "pyproject.toml"], cwd=ROOT)
    dest.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(dest, filter="data")
    return dest


def snapshot(db, line):
    return {name: db.execute(f"SELECT to_jsonb(t) FROM {name} t ORDER BY to_jsonb(t)").fetchall()
            for name in TABLES + EXTRA[line]}


def check_devices(db, runtime):
    rows = db.execute("""SELECT DISTINCT ON (revoked) user_id,id,epoch,credential_epoch,revoked
        FROM device_sessions ORDER BY revoked,created DESC""").fetchall()
    assert {row[-1] for row in rows} == {True, False}
    for actor, sid, epoch, credential_epoch, revoked in rows:
        with Session(runtime) as session:
            set_context(session, actor=actor)
            sign_actor(session, actor)
            if revoked:
                with pytest.raises(HTTPException) as error:
                    active(session, actor, sid, epoch, credential_epoch)
                assert error.value.status_code == 401
            else:
                active(session, actor, sid, epoch, credential_epoch)


def run(line):
    dsn = os.environ["AMC_MIGRATION_DSN"]
    runtime = create_engine(os.environ["DATABASE_URL"])
    assert runtime.url.username == "amc_runtime" and os.environ.get("AMC_TEST_PG") == "1"
    with psycopg.connect(dsn) as db:
        assert db.info.host in ("localhost", "127.0.0.1", "::1") and db.info.dbname.startswith("amc_test")
        assert runtime.url.database == db.info.dbname and runtime.url.host == db.info.host
        assert not db.execute("SELECT to_regclass('amc_schema_versions')").fetchone()[0]
    with tempfile.TemporaryDirectory(prefix="amc-") as folder:
        tmp = Path(folder)
        old = {name: unpack(name, tmp / name) for name in PINS}
        env = dict(os.environ, AMC_DEV_MAILBOX_DIR=str(tmp / "m"), PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTHONPATH", None)
        cmd = [sys.executable, "-m", "migrations.apply"]
        subprocess.run(cmd, cwd=old[line], env=env, check=True)
        subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short", "--maxfail=1", *COMMON, *CASES[line]],
                       cwd=old[line], env=env, check=True)
        with psycopg.connect(dsn) as db:
            before = snapshot(db, line)
            assert all(before.values()), {t: len(rows) for t, rows in before.items()}
            if line == "c2":
                assert {"company", "brand", "brief"} <= {r[0]["kind"] for r in before["business_workspace_records"]}
            else:
                check_devices(db, runtime)
            witness = fingerprint(db)
        if line == "a1":
            with patch.dict(os.environ, AMC_DB_PROOF_KEY=secrets.token_hex(32)), pytest.raises(ValueError, match="identity keys"):
                migrate(dsn)
        else:
            unknown_issuer = secrets.token_hex(48)
            unrelated_quota = hmac.digest(unknown_issuer.encode(), b"amc/identity-quota/v1", "sha256").hex()
            with (patch.dict(os.environ, JWT_SECRET=unknown_issuer, AMC_QUOTA_KEY=unrelated_quota),
                  pytest.raises(ValueError, match="Legacy issuer")):
                migrate(dsn)
            with psycopg.connect(dsn) as db:
                db.execute("ALTER TABLE amc_schema_versions ADD CONSTRAINT test_incomplete CHECK(version<>24)")
            with pytest.raises(psycopg.errors.CheckViolation):
                migrate(dsn)
            with psycopg.connect(dsn) as db:
                assert not db.execute("SELECT to_regclass('public.device_sessions')").fetchone()[0]
                db.execute("ALTER TABLE amc_schema_versions DROP CONSTRAINT test_incomplete")
        with psycopg.connect(dsn) as db:
            assert fingerprint(db) == witness
        migrate(dsn)
        prepare_database(runtime)
        with psycopg.connect(dsn) as db:
            assert snapshot(db, line) == before
            assert db.execute("SELECT version FROM amc_business.versions ORDER BY version").fetchall() == [(1,), (2,), (3,)]
            assert db.execute("SELECT max(version) FROM amc_schema_versions").fetchone() == (25,)
            assert db.execute("SELECT version FROM amc_c3.versions ORDER BY version").fetchall() == [(1,)]
            assert db.execute(COMMERCIAL_CURRENT).fetchone()[0] and db.execute(DESK_CURRENT).fetchone()[0]
            if line == "a1":
                check_devices(db, runtime)
            joined = fingerprint(db)
        migrate(dsn)
        for project in old.values():
            result = subprocess.run(cmd, cwd=project, env=env, check=False, capture_output=True)
            assert result.returncode and b"Unknown schema version" in result.stderr
        with psycopg.connect(dsn) as db:
            assert fingerprint(db) == joined
    runtime.dispose()
    print(f"PASS {line} {PINS[line]} to C3 v25, populated table rows",
          {t: len(rows) for t, rows in before.items()}, "atomic failure, replay and both predecessor refusals")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predecessor", choices=PINS)
    run(parser.parse_args().predecessor)
