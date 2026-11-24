"""Execute the installed sources in independent interpreters, with the historical manifest unchanged."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from dispatcher_build import turn
from test_adapter_rollout import specialist
from test_registry import frozen_run, pool as registry_pool_fixture

pool = registry_pool_fixture
ROOT = Path(__file__).resolve().parents[1]
PROBE = """
import json
from types import SimpleNamespace
from pathlib import Path
from app.registry_adapters import resolve
from app.workforce_gateway import request_body
from migrations.registry_release import adapter_digest
node=SimpleNamespace(skill='seo',last_error=None,attempts=0)
run=SimpleNamespace(knowledge={'sources':{'brand':{'excerpt':'fact'}}},checkpoints=[],plan=[])
contract=json.loads(Path("catalog/landing-seo-v1.json").read_text(encoding="utf-8"))["contracts"]["seo"]
body=request_body(run,'local',node=node,predecessors={},assignment='')
print(json.dumps(dict(max_tokens=body['max_tokens'],legacy_digest=adapter_digest(),pinned=contract['adapter_digest'],
                      compatible=resolve(contract) is not None)))
"""


def checkout(target):
    for name in ("app", "migrations", "catalog"):
        shutil.copytree(ROOT / name, target / name, ignore=shutil.ignore_patterns("__pycache__"))
    for path in ROOT.glob("requirements*.txt"):
        shutil.copyfile(path, target / path.name)


def change(target, filename, old, new):
    path = target / filename
    source = path.read_text(encoding="utf-8")
    assert source.count(old) == 1
    path.write_text(source.replace(old, new), encoding="utf-8")


def inspect_build(path):
    result = subprocess.run([sys.executable, "-B", "-c", PROBE], cwd=path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    "filename,old,new",
    [
        ("app/workforce_gateway.py", "MAX_OUTPUT = 640", "MAX_OUTPUT = 800"),
        ("app/dynamic_plan.py", "{0,23}", "{0,15}"),
        ("app/workforce_gateway.py", "encode()) + 512", "encode()) + 1024"),
        ("app/workforce_evidence.py", "re.compile(pattern, re.IGNORECASE)", "re.compile(pattern)"),
    ],
)
def test_changed_runtime_with_same_legacy_digest_yields(tmp_path, filename, old, new):
    checkout(tmp_path)
    before = inspect_build(tmp_path)
    assert before["compatible"] and before["max_tokens"] == 640
    change(tmp_path, filename, old, new)
    after = inspect_build(tmp_path)
    assert after["pinned"] == before["pinned"] == before["legacy_digest"] == after["legacy_digest"]
    if old == "MAX_OUTPUT = 640":
        assert after["max_tokens"] == 800
    assert not after["compatible"], (before, after)


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires PostgreSQL")
def test_token_limit_change_cannot_claim_partly_completed_run(pool, tmp_path):
    lab = pool
    rid = frozen_run(lab)
    specialist(lab, rid, "content")
    checkout(tmp_path)
    change(tmp_path, "app/workforce_gateway.py", "MAX_OUTPUT = 640", "MAX_OUTPUT = 800")
    for w in lab.workers:
        w.take()

    def state():
        return lab.owner.execute(
            """select r.state,r.knowledge::text,p.digest,r.checkpoints::text,
           r.reserved_microusd,(select count(*) from amc_ops.attempts a where a.run=r.id)
           from workforce_runs r join amc_ops.dag_plans p on p.run=r.id where r.id=%s""",
            (rid,),
        ).fetchone()

    before = state()
    probe = turn(tmp_path, lab, "dispatch")
    if probe["worked"]:
        tokens = lab.owner.execute(
            """select (body->>'max_tokens')::int from amc_ops.attempts
                                    where run=%s and status='offered'""",
            (rid,),
        ).fetchone()[0]
        pytest.fail(f"Incompatible dispatcher issued SEO offer with max_tokens={tokens}, digest={probe['digest']}")
    assert before == state() and before[0] == "queued"
    specialist(lab, rid, "seo")
    after = state()
    assert after[0] == "awaiting_qa" and after[1:3] == before[1:3]
