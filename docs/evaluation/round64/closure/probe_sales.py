"""Run the historical PostgreSQL case unchanged with synthetic, read-only clock observations.

From the selected checkout, run this file using the disposable PostgreSQL test environment
from the API CI job. AMC_SALES_PROBE is a new output JSON path. Never use customer records.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest


def instant():
    return datetime.now(timezone.utc)


def sample(connection):
    start = instant()
    db = connection.execute("SELECT clock_timestamp()").fetchone()[0]
    end = instant()
    return {"process_before": start.isoformat(), "db": db.isoformat(), "process_after": end.isoformat(),
            "db_minus_process_interval_ms": [(db - end).total_seconds() * 1000, (db - start).total_seconds() * 1000]}


class Probe:
    @pytest.fixture(autouse=True)
    def instrument(self, monkeypatch):
        import consultation_fixtures
        from app.campaign_operations_crm import FROM

        output = Path(os.environ["AMC_SALES_PROBE"])
        if output.exists() or os.environ.get("AMC_TEST_PG") != "1":
            raise RuntimeError("A fresh output path and disposable PostgreSQL are required")
        original = consultation_fixtures.settle_inquiry
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as connection:
            def trace(api, owner, buyer, other, operator, desk, sandbox, first, additional_inquiry, *, pg):
                assert pg
                evidence = {}
                def save():
                    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

                def create(**values):
                    if "intake" in evidence:
                        return additional_inquiry(**values)
                    evidence["before_create"] = sample(connection)
                    receipt = additional_inquiry(**values)
                    row = receipt["value"]
                    evidence["intake"] = {k: row[k] for k in ("id","plan_id","revision","state","missing","quantity",
                                                              "unit","minimum_order_quantities","contact_purpose","last_event_at")}
                    evidence["created"] = {k: receipt[k] for k in ("id","entity_id","sequence","plan_id")}
                    # Do not query the database or write a file here: the next fixture event uses process time.
                    evidence["after_create_process"] = instant().isoformat()
                    return receipt

                post = api.post
                def inspect(path, *args, **kwargs):
                    cmd = kwargs.get("json") or {}
                    if not (evidence.get("intake", {}).get("id") == cmd.get("rfq_id") and cmd.get("step") == "refer" and "actual" not in evidence):
                        return post(path, *args, **kwargs)
                    row = evidence["intake"]
                    last = datetime.fromisoformat(row["last_event_at"])
                    when = datetime.fromisoformat(cmd["occurred_at"])
                    evidence["before_refer"] = sample(connection)
                    def facts(step, at):
                        return {"step": step, "occurred_at": at.isoformat(), "invalid_state": row["state"] not in FROM[step],
                                "backdated": at < last, "occurred_minus_last_ms": (at-last).total_seconds()*1000}
                    # Native signed payload is already frozen. Counterfactuals must fail without advancing revision.
                    for name, step, at in (("clock_control","refer",last-timedelta(microseconds=1)), ("state_control","assign",last)):
                        changed = {**cmd,"request_id":uuid4().hex,"step":step,"occurred_at":at.isoformat()}
                        r = post(path,*args,**{**kwargs,"json":changed})
                        evidence[name] = {**facts(step,at),"status":r.status_code,"detail":r.json().get("detail")}
                        save()
                        assert (r.status_code,r.json()["detail"]) == (409,"Invalid or out-of-order Sales transition")
                    actual = post(path,*args,**kwargs)
                    result = actual.json()
                    evidence["actual"] = {**facts("refer",when),"status":actual.status_code,"detail":result.get("detail"),
                                          "receipt":result.get("id"),"sequence":result.get("sequence"),
                                          "revision":result.get("value",{}).get("revision"),"expected_revision":cmd["expected_revision"]}
                    save()
                    return actual
                with monkeypatch.context() as context:
                    context.setattr(api, "post", inspect)
                    return original(api,owner,buyer,other,operator,desk,sandbox,first,create,pg=pg)
            monkeypatch.setattr(consultation_fixtures,"settle_inquiry",trace)
            yield


if __name__ == "__main__":
    sys.path.insert(0,str(Path.cwd()))
    sys.exit(pytest.main(["-q","-p","no:cacheprovider","--tb=short","--show-capture=no",
                          "tests/test_production_studios.py::test_restricted_production[False]", *sys.argv[1:]], plugins=[Probe()]))
