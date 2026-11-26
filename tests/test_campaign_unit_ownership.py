"""Commit a real worker dispatch, Studio share and portal decision after an unstarted brief changes owner."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from app import c3_assets, c3_studio
from app.models import utcnow
from c3_fixtures import capture
from knowledge_fixtures import accepted
from test_c3_content_gate import approve
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_studio_postgres import agency_draft
from test_workforce import DATA

pool = registry_pool
pytestmark = PG


def test_queue_owner_and_unique_share_group_survive_later_commissions(pool):
    api = pool.api
    base, owner, customer, _, cid = pool.cases[0]
    root = base + "/campaigns/" + cid
    headers = owner["headers"]
    plans = {}

    def commission(revision, manifest, target):
        plan = accepted(api.post(root + "/engine/plans", headers=headers, json={"expected_revision":revision - 1,
            "target_outcome":target, "manifest_ids":[manifest["id"]], "key":uuid4().hex, "duration_days":10,"budget_vnd":10000}))
        accepted(api.post(root + "/engine/plans/" + plan["id"] + "/approve", headers=headers,
                          json={"key":uuid4().hex,"expected_digest":plan["digest"]}))
        plans[revision] = plan
        return plan

    def command(revision, kind, *, status=200, key=None, **args):
        result = api.post(root + "/sandbox/commands", headers=headers, json={"kind":kind,"request_id":key or uuid4().hex,
                          "plan_id":plans[revision]["id"],**args})
        assert result.status_code == status, (kind,result.text[:600])
        return result.json()

    def state():
        return accepted(api.get(root + "/sandbox", headers=headers))

    def unit(revision, slot):
        return next(u for u in state()["work_units"] if u["plan_id"] == plans[revision]["id"] and u["package_id"] == slot)

    def before_queue(manifest, prep, intent):
        commission(1,manifest,manifest["projection"]["objective"])
        command(1,"labor",package_id="landing",phase="clarification",seconds=15,allocated_cost_vnd=3,observation="Synthetic review of first brief")
        command(1,"close_unit_cost",package_id="landing",nonlabor_vnd=4,basis="Synthetic measured allocation")
        commission(2,manifest,manifest["projection"]["kpi"])
        terms = {"workflow": "dynamic-v1", "max_parallel_nodes": 2, "budget_microusd": 1,
                 "registry_workflow": manifest["workflow"], "knowledge_manifest": {"id": manifest["id"], "digest": manifest["digest"]}}
        direct = base + "/workforce/briefs/" + prep["params"]["target"]["brief_id"] + "/run"
        assert api.post(direct, headers=headers, json=terms).status_code == 409
        assert api.post(direct, headers=headers, json={}).status_code == 409
        abandoned = unit(1,"landing")
        assert abandoned["status"] == "incomplete" and abandoned["cost_statement"]["total_vnd"] == 7
        assert abandoned["labor"][0]["seconds"] == 15 and not abandoned.get("run_id")
        bid = accepted(api.post(base + "/workforce/briefs",headers=headers,json={"campaign_id":cid,
            "recipient_id":customer["id"],"title":"Independent next campaign commission"}))["id"]
        accepted(api.put(base + "/workforce/briefs/" + bid + "/submission",headers=customer["headers"],json=DATA | {"task_intent":intent}))
        other = deepcopy(prep)
        other["params"].update(key=uuid4().hex,target={"campaign_id":cid,"brief_id":bid})
        plans["separate_manifest"] = capture(api,owner,other)

    doc, _, snap = agency_draft(pool,c3_assets.LANDING,rfq=True,before_queue=before_queue)
    run = unit(2,"landing")
    assert run["status"] == "generated" and run.get("run_id") and run.get("queue_receipt")
    assert unit(1,"landing")["status"] == "incomplete" and not unit(1,"landing").get("run_id")
    editor, qa = reader(api,owner,"editor"), reader(api,owner,"admin")
    route = doc + "/studio"
    proposal = accepted(api.get(route,headers=editor["headers"]))
    edition = proposal["customer_edition"]
    groups = c3_studio.compose(c3_assets.LANDING,snap["projection"]) | edition["groups"]
    saved = accepted(api.patch(route,headers=editor["headers"],json={"expected_revision":proposal["revision"],"delivery_version":edition["version"],"groups":groups}))
    submit = accepted(api.post(doc + "/submit",headers=editor["headers"]))
    terms = {"expected_qa_revision":saved["revision"],"expected_content_digest":submit["qa_evidence"]["content_digest"]}
    for group in groups:
        accepted(api.post(route + "/approvals",headers=qa["headers"],json={"expected_revision":saved["revision"],
            "expected_asset_digest":saved["asset_digests"][group],"group":group,"note":"Reviewed the exact scoped synthetic edition."}))
    accepted(approve(api,doc,owner,terms))
    share = accepted(api.post(doc + "/share",headers=headers,json=terms | {"expires_at":(utcnow()+timedelta(days=2)).isoformat()}))
    accepted(api.put(base + "/members/" + customer["id"] + "/review-rights",headers=headers,json={"can_comment":True,"can_decide":True}))
    accepted(api.post(base + "/reviews/" + share["id"] + "/events",headers=customer["headers"],
                      json={"kind":"approved","digest":share["digest"],"request_key":uuid4().hex}))

    commission(3,plans["separate_manifest"],plans["separate_manifest"]["projection"]["objective"])
    assert unit(3,"landing")["status"] == "requested" and not unit(3,"landing").get("run_id")
    receipt = {"package_id":"landing","review_id":share["id"]}
    command(1,"unit_receipt",status=409,**receipt)
    command(3,"unit_receipt",status=409,**receipt)
    accepted_copy = command(2,"unit_receipt",key="settle-approved-copy",**receipt)
    assert accepted_copy == command(2,"unit_receipt",key="settle-approved-copy",**receipt)
    command(2,"unit_receipt",status=409,**receipt)
    command(2,"unit_receipt",package_id="seo",review_id=share["id"])
    copy = unit(2,"landing")["acceptance"]
    seo = unit(2,"seo")["acceptance"]
    assert copy["queue_receipt"] == run["queue_receipt"] and copy["run_id"] == run["run_id"]
    assert copy["share_receipt"] == seo["share_receipt"] and {copy["group"],seo["group"]} == {"copy","seo"}
    assert unit(1,"landing")["acceptance"] is None and state()["business_accepted_units"] == 0
