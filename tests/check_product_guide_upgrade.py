"""Exercise a populated pre-guide v26 cutover with the normal publishers and native PostgreSQL tools."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

BASE_TREE = "edda35771fcee71ded819d85878e947f93ef9127"
TABLES = (
    "workforce_briefs",
    "deliverables",
    "workforce_runs",
    "knowledge_commands",
    "knowledge_snapshots",
    "knowledge_revisions",
    "knowledge_dependencies",
    "amc_ops.attempts",
    "amc_ops.ledger",
    "amc_ops.registry_releases",
)
ROOT = Path(__file__).resolve().parents[1]


def run(checkout, *args):
    env = os.environ | {"PYTHONPATH": str(checkout)}
    subprocess.run([sys.executable, *args], cwd=checkout, env=env, check=True)


def proof(db):
    result = {}
    for table in TABLES:
        name = sql.Identifier(*table.split("."))
        rows = db.execute(sql.SQL("SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text").format(name)).fetchall()
        result[table] = {"rows": len(rows), "sha256": hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()}
    return result


def native_restore(db, dsn, params, pg_bin, expected, fence):
    target = "amc_test_guide_restore_" + uuid4().hex
    with TemporaryDirectory() as directory:
        path = Path(directory) / "guide.dump"
        env = os.environ | {"PGHOST": params["host"], "PGPORT": str(params["port"]), "PGUSER": params["user"], "PGPASSWORD": params["password"]}
        subprocess.run([str(pg_bin / "pg_dump"), "-Fc", "-f", str(path), params["dbname"]], env=env, check=True)
        db.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target)))
        try:
            subprocess.run([str(pg_bin / "pg_restore"), "--exit-on-error", "--single-transaction", "-d", target, str(path)], env=env, check=True)
            with psycopg.connect(make_conninfo(dsn, dbname=target)) as restored:
                assert restored.execute(fence).fetchone() == (True,)
                assert proof(restored) == expected
        finally:
            db.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(target)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-checkout", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, help="Directory containing matching pg_dump and pg_restore to also run native archive rehearsal")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    old = args.previous_checkout.resolve()
    git = ["git", "-c", "safe.directory=" + old.as_posix()]
    tree = subprocess.check_output([*git, "rev-parse", "HEAD^{tree}"], cwd=old, text=True).strip()
    assert tree == BASE_TREE
    subprocess.run([*git, "diff", "--exit-code", "HEAD", "--", "app", "migrations", "catalog", "tests"], cwd=old, check=True)
    dsn = os.environ["AMC_MIGRATION_DSN"]
    params = conninfo_to_dict(dsn)
    assert params["host"] in ("localhost", "127.0.0.1", "::1") and params["dbname"].startswith("amc_test")
    assert os.environ.get("AMC_TEST_PG") == "1"
    sys.path.insert(0, str(ROOT))
    from migrations.product_guide_contract import GUIDE_FENCE

    with psycopg.connect(dsn, autocommit=True) as db:
        assert db.execute("SELECT max(version) FROM amc_schema_versions").fetchone() == (26,)
        assert db.execute("SELECT to_regprocedure('amc_c3.guide_authorized(public.workforce_runs,boolean)')").fetchone() == (None,)
        run(old, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_content_handoff_admission.py", "-k", "released-terms")
        baseline = proof(db)
        assert all(r["rows"] > 0 for r in baseline.values())
        run(ROOT, "migrations/apply.py")
        assert db.execute(GUIDE_FENCE).fetchone() == (True,) and proof(db) == baseline
        identities = db.execute("SELECT oid,prosrc FROM pg_proc WHERE pronamespace='amc_c3'::regnamespace ORDER BY oid").fetchall()
        run(ROOT, "migrations/apply.py")
        assert db.execute("SELECT oid,prosrc FROM pg_proc WHERE pronamespace='amc_c3'::regnamespace ORDER BY oid").fetchall() == identities
        assert proof(db) == baseline
        run(
            ROOT,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_product_guide_rollback.py::test_previous_reader_sees_strategy_but_cannot_load_guide",
        )
        before_dump = proof(db)
        guide_docs = db.execute("SELECT count(*) FROM deliverables WHERE content::jsonb ? 'product_guide'").fetchone()[0]
        assert guide_docs > 0
        record = {
            "predecessor_tree": tree,
            "core": 26,
            "postgresql_server_version": db.info.server_version,
            "populated_before_upgrade": baseline,
            "repeat_publisher_preserved_rows_and_function_oids": True,
            "after_guide": before_dump,
            "guide_documents": guide_docs,
            "native_archive": "not_run",
        }
        if args.pg_bin:
            native_restore(db, dsn, params, args.pg_bin, before_dump, GUIDE_FENCE)
            record["native_archive"] = "passed"
    args.report.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"PASS populated pre-guide v26, repeat publisher and reader rollback; native archive {record['native_archive']}")


if __name__ == "__main__":
    main()
