"""Synthetic A/B/C acceptance data shared by the database and real-model tests."""

import json
from dataclasses import dataclass
from secrets import token_hex

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from sqlalchemy import create_engine

from agency_fixtures import account, create
from identity_fixtures import invite_member
from app.pool_dispatch import consume, dispatch
from app.pool_worker import report, take
from app.workforce_gateway import Gateway
from scripts.provision_pool import provision, route
from test_workforce import DATA, call_model


@dataclass(frozen=True)
class FixedHold(Gateway):
    amount: int = 700

    def price(self, inputs, outputs):
        return self.amount


class Worker:
    def __init__(self, conn):
        self.conn = conn

    def take(self):
        return take(self.conn)

    def complete(self, job):
        return report(self.conn, job, call_model(None, job["body"]))

    def error(self, job, error):
        return report(self.conn, job, error=error)


class Lab:
    def __init__(self, api, dsn, workflow="linear", parallelism=1):
        self.parallelism = parallelism
        self.workflow = workflow
        self.api, self.dsn = api, dsn
        self.owner = psycopg.connect(dsn, autocommit=True)
        assert self.owner.info.dbname.startswith("amc_test")
        self.logins = []
        self.workers = []
        self.runs, self.cases = [], []
        self.config = Gateway("local", "amc-local", "http://localhost/v1", 0, 0, 180)
        dispatch_name, dispatch_dsn = self.login("amc_dispatch")
        self.bind = create_engine("postgresql+psycopg://", creator=lambda: psycopg.connect(dispatch_dsn))
        for _ in range(2):
            name, worker_dsn = self.login("amc_pool_worker")
            self.workers.append(Worker(psycopg.connect(worker_dsn, autocommit=True)))
        self.x, self.y = account(api, "AgencyX"), account(api, "AgencyY")
        for admin in (self.x, self.y):
            self.configure(admin, 10000)
        for label, admin in zip("ABC", (self.x, self.x, self.y), strict=True):
            self.seed(label, admin)

    def login(self, group):
        name, password = "amc_ops_" + token_hex(5), token_hex(32)
        provision(self.owner, name, group, password)
        dsn = make_conninfo(self.dsn, user=name, password=password)
        self.logins.append((name, dsn))
        return name, dsn

    def configure(self, admin, ceiling, enabled=True):
        self.api.put(
            "/api/tenants/" + admin["tenant"] + "/operations/budget", headers=admin["headers"], json={"capacity": 2, "ceiling": ceiling, "enabled": enabled}
        ).raise_for_status()

    def seed(self, label, admin):
        tenant = admin["tenant"]
        base = "/api/tenants/" + tenant
        reader, editor = account(self.api, "Reader" + label), account(self.api, "Operator" + label)
        client = create(self.api, base + "/clients", admin, {"name": "Client " + label})["id"]
        brand = create(self.api, base + "/brands", admin, {"name": "Brand " + label, "client_id": client, "product_truth": "A5 notebook for " + label})["id"]
        campaign = create(
            self.api,
            base + "/campaigns",
            admin,
            {"brand_id": brand, "name": "Campaign " + label, "brief": "Synthetic campaign acceptance", "objective": "Reach students"},
        )["id"]
        invite_member(self.api, base, admin["headers"], reader["headers"], email=reader["email"], role="client_viewer", client_id=client)
        invite_member(self.api, base, admin["headers"], editor["headers"], email=editor["email"], role="editor")
        for worker, _ in self.logins[1:]:
            route(self.owner, worker, tenant, client, brand, campaign, editor["id"])
        brief = create(self.api, base + "/workforce/briefs", admin, {"campaign_id": campaign, "recipient_id": reader["id"], "title": "Notebook " + label})
        path = base + "/workforce/briefs/" + brief["id"]
        brief_data = dict(DATA)
        terms = {}
        if self.workflow == "dynamic-v1":
            brief_data["objective"] = "Write one short notebook email for students." if label != "C" else "Write a notebook landing page and SEO metadata based on the page."
            terms["max_parallel_nodes"] = self.parallelism
            terms["extra_skills"] = ["seo"] if label == "C" else []
        self.api.put(
            path + "/submission",
            headers=reader["headers"],
            json={**brief_data, "sources": [{"label": "Product card", "excerpt": "Notebook reference for client " + label}]},
        ).raise_for_status()
        response = self.api.post(path + "/run", headers=admin["headers"], json={"budget_microusd": 10000, **terms, **({"workflow": self.workflow} if self.workflow != "linear" else {})})
        response.raise_for_status()
        self.runs.append(response.json()["id"])
        self.cases.append((base, admin, reader, client, campaign))

    def dispatch(self, reserve=0):
        config = FixedHold(**vars(self.config), amount=reserve) if reserve else self.config
        return dispatch(self.bind, config)

    def consume(self):
        return consume(self.bind, self.config)

    def drain(self):
        for _ in range(40):
            while self.consume():
                pass
            if not self.dispatch():
                return
            for w in self.workers:
                job = w.take()
                if job:
                    assert w.complete(job)

    def states(self):
        return [self.owner.execute("select state from workforce_runs where id=%s", (rid,)).fetchone()[0] for rid in self.runs]

    def check_isolation(self, first, second):
        import pytest

        assert first["id"] != second["id"]
        for w, own, foreign in zip(self.workers, (first, second), (second, first), strict=True):
            scope = self.cases[self.runs.index(foreign["run"])]
            w.conn.execute("select set_config('amc.tenant_id',%s,false),set_config('amc.user_id',%s,false)", (scope[1]["tenant"], scope[1]["id"]))
            assert not w.complete(foreign)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                w.conn.execute("select knowledge from workforce_runs")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                w.conn.execute("select * from amc_ops.ledger")
            data = json.loads(own["body"]["messages"][1]["content"])
            assert data["knowledge"]["sources"]["S1"]["excerpt"].endswith("ABC"[self.runs.index(own["run"])])
        base, admin, reader, *_ = self.cases[0]
        for actor in (reader, self.y):
            assert self.api.get(base + "/operations", headers=actor["headers"]).status_code == 404
        rid = self.runs[0]
        # The v8 worker role sees zero rows in its own editor context for a pooled run.
        from app.workforce_worker import Scope, process_one
        from app.database import engine

        row = self.owner.execute(
            "select tenant,client,brand,campaign,operator from amc_ops.routes where tenant=%s and campaign=%s limit 1", (admin["tenant"], self.cases[0][-1])
        ).fetchone()
        assert not process_one(engine, Scope(*row), self.config, lambda *_: pytest.fail("legacy worker reached inference"))
        assert self.api.post(base + "/workforce/briefs/" + rid + "/run", headers=reader["headers"], json={"tenant": self.y["tenant"]}).status_code == 422

    def revoke_and_restore_a(self):
        base, admin, reader, client, _ = self.cases[0]
        path = base + "/members/" + reader["id"] + "/client-scope"
        self.api.delete(path, headers=admin["headers"]).raise_for_status()
        invite_member(self.api, base, admin["headers"], reader["headers"], email=reader["email"], role="client_viewer", client_id=client)

    def verify_assets_and_dependencies(self, *runs):
        for rid in runs:
            row = self.owner.execute("select checkpoints,deliverable_id,tenant_id,campaign_id from workforce_runs where id=%s", (rid,)).fetchone()
            skills = ["director","research","strategy","content"]
            if self.workflow == "diamond-v1":
                skills.append("seo")
                assert self.owner.execute("select deliverable from amc_ops.dag_plans where run=%s",(rid,)).fetchone() == (row[1],)
            if self.workflow == "dynamic-v1":
                contract, linked = self.owner.execute("select contract,deliverable from amc_ops.dag_plans where run=%s",(rid,)).fetchone()
                assert linked == row[1]
                skills = ["director", *(n["skill_type"] for n in contract["nodes"])]
            assert [c["skill"] for c in row[0]] == skills
            assert self.owner.execute("select tenant_id,campaign_id from deliverables where id=%s", (row[1],)).fetchone() == row[2:]
            assert self.owner.execute("select count(*) from amc_ops.tasks where run=%s and done", (rid,)).fetchone() == (len(skills),)
        assert self.owner.execute("select deliverable_id from workforce_runs where id=%s", (self.runs[0],)).fetchone() == (None,)

    def limit_x(self, amount):
        self.configure(self.x, amount)
        self.configure(self.y, 10000, False)

    def balance_x(self):
        return self.owner.execute("select sum(held),sum(spent) from amc_ops.ledger where tenant=%s", (self.x["tenant"],)).fetchone()

    def receipt(self, job, amount, ref):
        base, admin, *_ = self.cases[0]
        return self.api.post(base + "/operations/attempts/" + job["id"] + "/receipts", headers=admin["headers"], json={"amount": amount, "receipt": ref})

    def bill(self, job, amount, ref):
        self.receipt(job, amount, ref).raise_for_status()

    def reject_conflicting_receipt(self, job):
        import pytest

        assert self.receipt(job, 400, "receipt-1").status_code == 409
        with pytest.raises(psycopg.Error, match="append-only"):
            self.owner.execute("update amc_ops.ledger set spent=0 where id=%s", (job["id"],))

    def close(self):
        for admin in (self.x, self.y):
            self.configure(admin, 0, False)
        self.owner.execute("delete from amc_ops.routes where worker=any(%s)", ([n for n, _ in self.logins[1:]],))
        while self.consume():
            pass
        for w in self.workers:
            w.conn.close()
        self.bind.dispose()
        for name, _ in self.logins:
            self.owner.execute(sql.SQL("drop role {}").format(sql.Identifier(name)))
        self.owner.close()
