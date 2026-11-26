"""Exercise real scoped QA, local destinations, auth, dispatch, restart and cost inventory."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from test_campaign_operations import fresh_process
from knowledge_fixtures import accepted


def write_evidence(name, value):
    root = os.getenv("AMC_DEPT_OPS_EVIDENCE")
    if root:
        path = Path(root)
        path.mkdir(parents=True,exist_ok=True)
        (path / name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def exercise_dispatch(pool,base,root,owner,qa,plan,monkeypatch):
    api=pool.api
    data=accepted(api.get(root+"/engine/plans/"+plan["id"]+"/production",headers=owner["headers"]))
    asset=next(a for a in data["assets"] if a["kind"]=="landing")
    target={"contract":"sandbox-capability/1","action_type":"render_preview","channel":"website","destination":"sandbox_page",
            "group":"copy","group_digest":asset["digest"],"mode":"scheduled"}
    schedule={"action_id":"service-preview", "deliverable_id":asset["deliverable_id"],"expected_digest":asset["document_digest"],
              "expected_revision":asset["revision"],"cost_vnd":100,"due_at":(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),"target":target}
    def cmd(kind, actor, *, status=200, path=root, **args):
        r=api.post(path+"/sandbox/commands",headers=actor["headers"],json={"kind":kind,"request_id":uuid4().hex,"plan_id":plan["id"],**args})
        assert r.status_code==status,(kind,r.text[:450])
        return r.json()
    wrong_base, wrong_owner, _, _, wrong_campaign = pool.cases[1]
    assert api.post(wrong_base+"/campaigns/"+wrong_campaign+"/sandbox/commands",headers=wrong_owner["headers"],
                    json={"kind":"schedule","request_id":uuid4().hex,"plan_id":plan["id"],**schedule}).status_code in (404,409)
    cmd("schedule",owner,status=409,**{**schedule,"target":target|{"group_digest":"a"*64}})
    cmd("schedule",owner,status=409,**{**schedule,"target":target|{"destination":"sandbox_ad_slot"}})
    cmd("schedule",owner,status=422,**{**schedule,"target":target|{"destination":"https://invalid.example"}})
    issued=cmd("schedule",owner,**schedule)
    cmd("authorize",owner,status=409,action_id=schedule["action_id"])
    authorized=cmd("authorize",qa,action_id=schedule["action_id"])
    cmd("execute",owner,status=409,action_id=schedule["action_id"])
    secret=uuid4().hex+uuid4().hex
    monkeypatch.setenv("AMC_SANDBOX_DISPATCH_KEY",secret)
    monkeypatch.setenv("AMC_SANDBOX_DISPATCH_TOKEN",qa["headers"]["Authorization"].split(" ",1)[1])
    def tick():
        with fresh_process() as native:
            origin=str(native.base_url).rstrip("/")
            assert native.get(root+"/sandbox/dispatch-ready",headers=owner["headers"]).status_code==404
            result=subprocess.run([sys.executable,"scripts/dispatch_campaign_sandbox.py","--origin",origin,"--tenant",owner["tenant"],
                                   "--campaign",plan["campaign_id"],"--ticks","1","--batch","1"],capture_output=True,timeout=40,
                                  text=True,check=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            return [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    first=tick()
    assert len(first)==1 and first[0]["http"]==200
    assert tick()==[]
    state=accepted(api.get(root+"/sandbox",headers=owner["headers"]))
    action=next(a for a in state["actions"] if a["id"]==schedule["action_id"])
    assert action["executed_via"]=="local_dispatcher" and action["sandbox_output"]["fields"]==asset["fields"]
    assert state["report"]["simulated_spend_vnd"]==100
    write_evidence("dispatch.json",{"conditions":"Synthetic agency, independent QA, restricted PostgreSQL and separate loopback dispatcher process.",
        "schedule":issued["id"],"authorization":authorized["id"],"execution":first[0],"restart_dispatches":0,
        "action":action,"observed_attempts":state["observed_attempts"],"observed_input_tokens":state["observed_input_tokens"],
        "observed_output_tokens":state["observed_output_tokens"],"cost_status":state["cost_status"],"cost_per_business_accepted_vnd":state["cost_per_business_accepted_vnd"]})
