"""A channel package uses the existing independent Studio and portal lifecycle."""

from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app import c3_assets, c3_boundaries, c3_studio, campaign_channels, registry
from app.knowledge_models import KnowledgeSnapshot
from app.knowledge_store import Store
from app.models import Deliverable, User, utcnow
from app.workforce_models import WorkforceRun
from campaign_planner_fixtures import CASES, prepare_inputs
from knowledge_fixtures import accepted
from test_c3_content_gate import approve
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_studio_postgres import agency_draft
from test_workforce import workforce as workforce_fixture

pool = registry_pool
workforce = workforce_fixture


def commission(api, base, owner, campaign, snapshot, revision=0):
    url = base + "/campaigns/" + campaign + "/engine"
    plan = accepted(api.post(url + "/plans", headers=owner["headers"], json={
        "manifest_ids": [snapshot["id"]], "budget_vnd": 500000, "duration_days": 14, "expected_revision": revision, "key": uuid4().hex}))
    accepted(api.post(url + "/plans/" + plan["id"] + "/approve", headers=owner["headers"],
                      json={"expected_digest": plan["digest"], "key": uuid4().hex}))
    return plan


def sqlite_channel(api, workforce, monkeypatch, case, wf=c3_assets.LANDING):
    owner, buyer, other, base, _, scope, engine, _ = workforce
    other_workflow = c3_assets.RESEARCH if wf == c3_assets.LANDING else c3_assets.LANDING
    (snap, next_snap), _ = prepare_inputs(api, owner, buyer, scope.client, scope.brand, scope.campaign, case, workflows=(wf, other_workflow))
    plan = commission(api, base, owner, scope.campaign, snap)
    editor = reader(api, owner, "editor")
    binding = {"workflow": wf, "manifest_digest": "e" * 64}
    monkeypatch.setattr(registry, "pin", lambda *args: binding)
    # SQLite has no publisher/worker logins. Seed only the completed run and its
    # queue association. PostgreSQL below drives the actual worker and publisher.
    with Session(engine) as db:
        doc = Deliverable(tenant_id=scope.tenant, campaign_id=scope.campaign, title=case["product"],
                          content={"client_preview": case["product"]}, created_by=editor["id"])
        db.add(doc)
        db.flush()
        source = db.get(KnowledgeSnapshot, snap["id"])
        run = WorkforceRun(tenant_id=scope.tenant, client_id=scope.client, brand_id=scope.brand, campaign_id=scope.campaign,
                           brief_id=source.brief_id, deliverable_id=doc.id, plan=[], budget_microusd=0, state="awaiting_qa",
                           knowledge={"title": case["product"], "registry": binding, "c3_projection": snap["projection"],
                                      "sources": {}, "c3_manifest": {"id": source.id, "digest": source.digest}})
        db.add(run)
        db.flush()
        store = Store(db, db.get(User, owner["id"]), scope.tenant, scope.client, scope.brand, write=True)
        c3_boundaries.record(store, source, "queue", "queue:" + run.id, {"run_id": run.id, "manifest_digest": source.digest})
        did = doc.id
        db.commit()
    return base + "/deliverables/" + did, snap, plan, editor, other, next_snap


def lifecycle(api, base, owner, buyer, other, doc, snap, plan, editor, observe=None, next_snap=None):
    url = doc + "/studio"
    proposed = accepted(api.get(url, headers=owner["headers"]))
    edition = proposed["channel_edition"]
    assert edition and edition["plan"]["plan_digest"] == plan["digest"]
    assert accepted(api.get(url, headers=editor["headers"]))["channel_edition"] is None
    groups = c3_studio.compose(snap["workflow"], snap["projection"]) | edition["groups"]
    def write(actor, current, values, **extra):
        return api.patch(url, headers=actor["headers"], json={"expected_revision": current["revision"], "groups":values,
                         "delivery_version": campaign_channels.VERSION, "expected_plan_digest":plan["digest"]} | extra)
    assert write(editor, proposed, groups).status_code == 409
    assert write(owner, proposed, groups, expected_plan_digest="0"*64).status_code == 409
    saved = accepted(write(owner, proposed, groups))
    reviewer = reader(api, owner, "admin")
    changed = deepcopy(groups)
    changed["ad"]["description"] = "Giảm giá 90%."
    price = next((f for f in snap["projection"]["facts"] if f.get("price")), None)
    wrong = f"Receive {int(price['price']['amount_minor']):,} VND when you book." if price else "Giảm giá 90%."
    changed["social"]["opening"] = groups["social"]["opening"] + " " + wrong
    changed["creative_brief"]["provenance"] = "Video đã sản xuất."
    bad = accepted(write(editor, saved, changed))
    if price:
        offer, = [s for s in bad["segment_suggestions"] if s["field"] == "studio.social.opening" and s["reason"] == "payment_direction"]
        assert offer["original"] == wrong and offer["handles"] == [price["id"]]
        assert changed["social"]["opening"][:offer["start"]] == groups["social"]["opening"] + " "
        assert offer["end"] == len(changed["social"]["opening"])
    assert any(r["field"] == "provenance" for r in bad["quality_issues"])
    assert any(r["field"] == "studio.ad.description" and r["outcome"] == "needs_correction" for r in bad["findings"])
    assert write(owner, saved, groups).status_code == 412
    accepted(api.post(doc + "/submit", headers=editor["headers"]))
    def sign(current, group):
        return api.post(url + "/approvals", headers=reviewer["headers"], json={"group":group, "expected_revision":current["revision"],
                        "expected_asset_digest":current["asset_digests"][group], "note":"Đối chiếu trường với phạm vi và nguồn được duyệt."})
    assert sign(bad, "ad").status_code == sign(bad, "creative_brief").status_code == sign(bad, "social").status_code == 409
    final = accepted(write(editor, bad, groups))
    assert not final["approvals"] and sign(bad, "social").status_code == 412
    submitted = accepted(api.post(doc + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision":final["revision"], "expected_content_digest":submitted["qa_evidence"]["content_digest"]}
    assert approve(api, doc, reviewer, terms).status_code == 409
    pending = [(r["field"],r["text"],r["outcome"]) for r in final["findings"] if r["outcome"] not in ("verified","editorial")]
    assert not pending, pending
    for group in groups:
        signed = accepted(sign(final, group))
    accepted(approve(api, doc, reviewer, terms))
    shared = accepted(api.post(doc + "/share", headers=owner["headers"], json={**terms, "expires_at":(utcnow()+timedelta(days=1)).isoformat()}))
    assert api.get(base + "/reviews/" + shared["id"], headers=other["headers"]).status_code == 404
    accepted(api.put(base + "/members/" + buyer["id"] + "/review-rights", headers=owner["headers"], json={"can_comment":True, "can_decide":True}))
    accepted(api.post(base + "/reviews/" + shared["id"] + "/events", headers=buyer["headers"],
                      json={"kind":"approved","digest":shared["digest"],"request_key":uuid4().hex}))
    root = base + "/campaigns/" + plan["campaign_id"]
    observed = accepted(api.get(root + "/engine/plans/" + plan["id"] + "/production", headers=owner["headers"]))
    accepted_units = {}
    for group in campaign_channels.FIELDS:
        item, = [r for r in observed["assets"] if r["kind"] == group]
        assert item["fields"] == groups[group] and item["digest"] == final["asset_digests"][group]
        assert item["approval_receipt"] == signed["approvals"][group]["receipt"]
        assert item["plan_digest"] == plan["digest"] and all(text in shared["preview"] for text in groups[group].values())
        reception = {"kind":"unit_receipt","request_id":uuid4().hex,"plan_id":plan["id"],"package_id":group,
                     "review_id":shared["id"]}
        receipt = accepted(api.post(root+"/sandbox/commands", headers=owner["headers"], json=reception))
        assert receipt["value"]["status"] == "fixture_accepted"
        assert api.post(root+"/sandbox/commands", headers=owner["headers"], json=reception | {"request_id":uuid4().hex}).status_code == 409
        accepted_units[group] = receipt
    if observe:
        observe(owner, buyer, doc.rsplit("/",1)[1], shared, plan)
    if directory := os.getenv("AMC_CHANNEL_EVIDENCE"):
        path = Path(directory)
        path.mkdir(exist_ok=True, parents=True)
        action = snap["projection"]["task_intent"]["buyer_action"]
        (path/f"{action}.json").write_text(json.dumps({"source":"synthetic API lifecycle","plan":edition["plan"],"revision":final["revision"],
            "snapshot_digest":shared["digest"], "customer_preview":shared["preview"], "assets":{k:groups[k] for k in campaign_channels.FIELDS},
            "field_evidence":[{"field":r["field"], "outcome":r["outcome"], "handles":r.get("handles",[])} for r in final["findings"]
                              if r["field"].split(".")[1:2] in [[key] for key in campaign_channels.FIELDS]],
            "group_approvals":signed["approvals"], "work_receipts":accepted_units}, indent=2, ensure_ascii=False)+"\n",encoding="utf8")
    latest = accepted(write(editor, final, groups))
    if next_snap:
        commission(api, base, owner, plan["campaign_id"], next_snap, revision=1)
        accepted(api.post(doc + "/submit", headers=editor["headers"]))
        assert sign(latest, "ad").status_code == 409
    assert accepted(api.get(base+"/reviews/"+shared["id"],headers=buyer["headers"]))["preview"] == shared["preview"]


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
@pytest.mark.parametrize("case", CASES, ids=lambda c:c["id"])
def test_channel_edition_sqlite(api, workforce, monkeypatch, case):
    doc, snap, plan, editor, other, next_snap = sqlite_channel(api, workforce, monkeypatch, case)
    owner, buyer, _, base, *_ = workforce
    lifecycle(api, base, owner, buyer, other, doc, snap, plan, editor, next_snap=next_snap)


@PG
def test_channel_edition_restricted_postgres(pool):
    base, owner, buyer, _, cid = pool.cases[0]
    plan = {}
    def before(snap, *_):
        plan.update(commission(pool.api, base, owner, cid, snap))
    doc, _, snap = agency_draft(pool, c3_assets.LANDING, rfq=True, before_queue=before)
    editor = reader(pool.api, owner, "editor")
    lifecycle(pool.api, base, owner, buyer, pool.cases[1][2], doc, snap, plan, editor)
