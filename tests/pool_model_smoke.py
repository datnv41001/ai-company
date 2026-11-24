"""Run two independent worker processes against pinned local Qwen in a disposable test DB."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import URL

from app.main import app
from pool_lab import Lab


def url(dsn, docker):
    info = conninfo_to_dict(dsn)
    return URL.create(
        "postgresql+psycopg", info["user"], info["password"], "db" if docker else info["host"], 5432 if docker else int(info["port"]), info["dbname"]
    ).render_as_string(hide_password=False)


def receipts(lab):
    reports = []
    for rid, case, label in zip(lab.runs, lab.cases, "ABC", strict=True):
        base, admin, reader, _, _ = case
        report = lab.api.get(base + "/workforce/runs/" + rid, headers=admin["headers"]).json()
        journal = report["journal"]
        first = [j for j in journal if j["attempt"] == 1]
        reports.append(
            {
                "campaign": label,
                "state": report["state"],
                "first_pass": sum(j["outcome"] == "ok" for j in first),
                "first_attempts": len(first),
                "attempts": len(journal),
                "outcomes": dict(Counter(j["outcome"] for j in journal)),
                "input_tokens": sum(j.get("input_tokens", 0) for j in journal),
                "output_tokens": sum(j.get("output_tokens", 0) for j in journal),
                "director_attempts": [j["outcome"] for j in journal if j["skill"] == "director"],
                "stage_attempts": [
                    {
                        "skill": j["skill"],
                        "outcome": j["outcome"],
                        "attempt": j["attempt"],
                        "input_tokens": j.get("input_tokens"),
                        "output_tokens": j.get("output_tokens"),
                    }
                    for j in journal
                ],
                "unconfirmed_usage": sum("input_tokens" not in j for j in journal),
            }
        )
        if lab.workflow == "dynamic-v1":
            reports[-1]["graph"] = report["graph"]
            reports[-1]["estimated_or_held_microusd"] = report["reserved_microusd"]
        if report["state"] == "awaiting_qa":
            doc = base + "/deliverables/" + report["deliverable_id"]
            draft = lab.api.get(doc, headers=admin["headers"]).json()
            evidence = draft["qa_evidence"]
            lab.api.post(
                doc + "/review",
                headers=admin["headers"],
                json={"decision": "approved", "expected_qa_revision": draft["qa_revision"], "expected_content_digest": evidence["content_digest"]},
            ).raise_for_status()
            shared = lab.api.post(
                doc + "/share", headers=admin["headers"], json={"expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
            ).json()
            assert shared["digest"] == evidence["content_digest"]
            lab.api.put(
                base + "/members/" + reader["id"] + "/review-rights", headers=admin["headers"], json={"can_comment": True, "can_decide": True}
            ).raise_for_status()
            lab.api.post(
                base + "/reviews/" + shared["id"] + "/events",
                headers=reader["headers"],
                json={"kind": "approved", "digest": shared["digest"], "request_key": uuid4().hex},
            ).raise_for_status()
    print("Qwen pool measurements", json.dumps(reports), flush=True)
    return reports


def exercise(docker, workflow):
    with TestClient(app) as api:
        lab = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow=workflow)
        settings = {
            "AMC_MODEL_TIMEOUT": "180",
            "AMC_WORKFORCE_PROVIDER": "local",
            "AMC_LOCAL_MODEL_URL": os.getenv("AMC_LOCAL_MODEL_URL", "http://127.0.0.1:18084/v1"),
        }
        dispatcher, one, two = [url(dsn, docker) for _, dsn in lab.logins]
        compose = ["docker", "compose", "-p", "amc-workforce-test", "-f", "compose.yaml", "-f", "tests/compose_pool_database.yaml", "-f", "compose.pool.yaml"]
        env = {**os.environ, "AMC_DISPATCH_URL": dispatcher, "AMC_POOL_ONE_DSN": one.replace("+psycopg", ""), "AMC_POOL_TWO_DSN": two.replace("+psycopg", "")}
        children = []
        try:
            if docker:
                subprocess.run([*compose, "up", "-d", "--build", "--no-deps", "dispatcher", "worker-one", "worker-two"], env=env, check=True)
            else:
                # Pass only the one LOGIN needed by each process; never copy the migration DSN.
                native = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "PYTHONUTF8", "LOCALAPPDATA"}}
                for module, secret in [
                    ("pool_dispatch", {"AMC_DISPATCH_URL": dispatcher}),
                    ("pool_worker", {"AMC_POOL_DSN": one.replace("+psycopg", "")}),
                    ("pool_worker", {"AMC_POOL_DSN": two.replace("+psycopg", "")}),
                ]:
                    children.append(subprocess.Popen([sys.executable, "-m", "app." + module], env={**native, **settings, **secret}))
            revoked = False
            deadline = time.monotonic() + 1000
            while time.monotonic() < deadline:
                if not revoked and lab.owner.execute("select 1 from amc_ops.attempts where run=%s and status='sent'", (lab.runs[0],)).fetchone():
                    lab.revoke_and_restore_a()
                    revoked = True
                if all(s in ("failed", "awaiting_qa") for s in lab.states()):
                    break
                assert all(p.poll() is None for p in children), "Worker process exited"
                time.sleep(0.15)
            stats = receipts(lab)
            assignments = lab.owner.execute(
                """select worker, count(distinct run), count(*) from amc_ops.attempts
                where run=any(%s) group by worker order by worker""",
                (lab.runs,),
            ).fetchall()
            print("Distinct campaigns / attempts per login", [(r[1], r[2]) for r in assignments], flush=True)
            if os.getenv("AMC_POOL_REPORT"):
                Path(os.environ["AMC_POOL_REPORT"]).write_text(
                    json.dumps({"campaigns": stats, "worker_campaign_counts": [r[1] for r in assignments]}, indent=2)
                )
            assert revoked and lab.states() == ["failed", "awaiting_qa", "awaiting_qa"]
            assert len(assignments) == 2 and max(r[1] for r in assignments) >= 2
            if workflow == "dynamic-v1":
                structures = [[(n["skill_type"], n["parents"]) for n in case["graph"]["contract"]["nodes"]] for case in stats[1:]]
                assert structures[0] != structures[1], "Different briefs must produce different graphs"
                # Synthetic briefs ask for an email for B and a landing page for C.
                for campaign, word in zip(stats[1:], ("email", "page"), strict=True):
                    assert any(word in n["assignment"].lower() for n in campaign["graph"]["contract"]["nodes"] if n["skill_type"] == "content")
            lab.verify_assets_and_dependencies(*lab.runs[1:])
        finally:
            if docker:
                subprocess.run([*compose, "stop", "dispatcher", "worker-one", "worker-two"], env=env, check=True)
            for child in children:
                child.terminate()
                child.wait(15)
            lab.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true")
    parser.add_argument("--workflow",choices=("linear","diamond-v1","dynamic-v1"),default="linear")
    args=parser.parse_args()
    exercise(args.docker,args.workflow)
