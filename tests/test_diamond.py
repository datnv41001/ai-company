"""PostgreSQL acceptance for the opt-in frozen diamond."""
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pool_worker import report
from pool_lab import Lab
from test_workforce import call_model

pytestmark = pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires PostgreSQL")


@pytest.fixture
def diamond():
    with TestClient(app) as api:
        lab = Lab(api, os.environ["AMC_MIGRATION_DSN"], workflow="diamond-v1")
        try:
            lab.configure(lab.y, 10000, False)
            lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=%s",(lab.runs[1],))
            assert all(w.take() is None for w in lab.workers)
            yield lab
        finally:
            lab.close()


def graph(lab):
    base,admin,*_=lab.cases[0]
    return lab.api.get(base+"/workforce/runs/"+lab.runs[0],headers=admin["headers"]).json()["graph"]


def take_node(lab):
    for w in lab.workers:
        assert w.take() is None
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(lambda _:lab.dispatch(),range(2)))==[False,True]
    return next((w,j) for w in lab.workers if (j:=w.take()))


def complete(lab, expected, invalid=False):
    w,job=take_node(lab)
    body=job["body"]
    assert body["response_format"]["json_schema"]["name"]==expected
    context=json.loads(body["messages"][1]["content"])
    if expected in ("content","seo"):
        assert list(context["earlier_drafts"])==["strategy"]
    result=list(call_model(None,body))
    if invalid:
        result[0]["source_ids"]=["unknown-source"]
    assert report(w.conn,job,result)
    assert not report(w.conn,job,result)
    assert lab.consume()
    lab.owner.execute("update workforce_runs set ready_at=now() where id=%s",(lab.runs[0],))


@pytest.mark.parametrize("seo_first",[False,True])
def test_diamond_join_and_sibling_isolation(diamond,seo_first):
    lab=diamond
    def ready():
        return {n["node_id"] for n in graph(lab)["nodes"] if n["status"]=="ready"}
    assert ready()=={"director"}
    complete(lab,"director")
    assert ready()=={"research"}
    complete(lab,"research")
    assert ready()=={"strategy"}
    complete(lab,"strategy")
    assert ready()=={"content","seo"}
    complete(lab,"content",invalid=seo_first)
    assert lab.states()[0]=="queued"
    complete(lab,"seo")
    if seo_first:
        assert lab.states()[0]=="queued"
        complete(lab,"content")
    assert lab.states()[0]=="awaiting_qa"
    run=lab.owner.execute("select checkpoints,deliverable_id from workforce_runs where id=%s",(lab.runs[0],)).fetchone()
    assert [p["node_id"] for p in run[0]]==["director","research","strategy","content","seo"]
    assert all(n["status"]=="succeeded" for n in graph(lab)["nodes"])
    assert lab.owner.execute("select count(*) from deliverables where id=%s",(run[1],)).fetchone()==(1,)
