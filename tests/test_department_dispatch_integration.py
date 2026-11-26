"""Exercise the optional Content Factory writer on the combined development build."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from app import c3_assets
from app.models import utcnow
from knowledge_fixtures import accepted
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_studio_postgres import agency_draft
from test_campaign_operations import fresh_process

pool = registry_pool


@PG
def test_dispatch_reviewed_channel_editions(pool,monkeypatch):
    pytest.importorskip("app.campaign_channels", reason="The optional C3 v5 Content Factory writer is required")
    from test_channel_editions import commission, lifecycle

    base, owner, buyer, _, cid = pool.cases[0]
    api = pool.api
    plan = {}

    def before(snap, *_):
        plan.update(commission(api, base, owner, cid, snap))

    doc, _, snap = agency_draft(pool, c3_assets.LANDING, rfq=True, before_queue=before)
    editor, approver = reader(api, owner, "editor"), reader(api, owner, "admin")
    root = base + "/campaigns/" + cid
    evidence = []
    stale = {}
    service_key=uuid4().hex+uuid4().hex
    monkeypatch.setenv("AMC_SANDBOX_DISPATCH_KEY",service_key)
    monkeypatch.setenv("AMC_SANDBOX_DISPATCH_TOKEN",approver["headers"]["Authorization"].split(" ",1)[1])

    def command(kind, actor, **payload):
        return api.post(root + "/sandbox/commands", headers=actor["headers"],
                        json={"kind": kind, "request_id": uuid4().hex, "plan_id": plan["id"], **payload})

    def inspect(_owner, _buyer, did, _shared, approved):
        rows = accepted(api.get(root + "/engine/plans/" + approved["id"] + "/production", headers=owner["headers"]))
        for group, channel, destination, action_type in (
            ("ad", "paid_media", "sandbox_ad_slot", "rehearse_placement"),
            ("social", "organic_social", "sandbox_social", "render_preview"),
            ("creative_brief", "internal", "sandbox_review", "render_preview"),
            ("calendar", "internal", "sandbox_review", "render_preview"),
        ):
            asset, = [a for a in rows["assets"] if a["kind"] == group]
            target = {"contract": "sandbox-capability/1", "mode": "manual", "group": group,
                      "channel": channel, "destination": destination, "group_digest": asset["digest"], "action_type": action_type}
            args = {"action_id": "channel-" + group, "deliverable_id": did, "expected_revision": asset["revision"],
                    "expected_digest": asset["document_digest"], "due_at": (utcnow() - timedelta(seconds=1)).isoformat(), "cost_vnd": 0}
            assert command("schedule", owner, **args, target=target | {"group_digest": "0"*64}).status_code == 409
            scheduled = accepted(command("schedule", owner, **args, target=target))
            auth = accepted(command("authorize", approver, action_id=args["action_id"]))
            done = accepted(command("execute", owner, action_id=args["action_id"]))
            output = done["value"]["sandbox_output"]
            assert output["fields"] == asset["fields"] and output["external_writes"] == 0
            assert done["value"]["target"]["approval_receipt"] == asset["approval_receipt"]
            evidence.append({"group": group, "destination": destination, "asset_digest": asset["digest"],
                             "scheduled": scheduled["id"], "authorized": auth["id"], "executed": done["id"],
                             "plan_digest": approved["digest"], "external_writes": output["external_writes"]})
            queued_args = args | {"action_id":"auto-"+group,"target":target|{"mode":"scheduled"}}
            issued=accepted(command("schedule",owner,**queued_args))
            permission=accepted(command("authorize",approver,action_id=queued_args["action_id"]))
            assert command("execute",owner,action_id=queued_args["action_id"]).status_code==409
            evidence.append({"group":group,"path":"scheduled","scheduled":issued["id"],"authorized":permission["id"],"action":queued_args["action_id"]})
            stale.update(queued_args)
        def tick(origin):
            result=subprocess.run([sys.executable,"scripts/dispatch_campaign_sandbox.py","--origin",origin,"--tenant",owner["tenant"],
                                  "--campaign",cid,"--ticks","1","--batch","4"],text=True,capture_output=True,check=True,timeout=60,
                                  creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            return [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        with fresh_process() as first, fresh_process() as second:
            with ThreadPoolExecutor(max_workers=2) as threads:
                calls=list(threads.map(tick,[str(first.base_url).rstrip("/"),str(second.base_url).rstrip("/")]))
            assert all(call["http"]==200 for batch in calls for call in batch)
        with fresh_process() as restart:
            assert not tick(str(restart.base_url).rstrip("/"))
        operations=accepted(api.get(root+"/sandbox",headers=owner["headers"]))
        for row in (e for e in evidence if e.get("path")=="scheduled"):
            action=next(a for a in operations["actions"] if a["id"]==row["action"])
            receipts=[r for r in operations["receipts"] if r["kind"]=="execute" and r["entity_id"]==action["id"]]
            assert len(receipts)==1 and action["attempts"]==1 and action["executed_via"]=="local_dispatcher"
            assert action["sandbox_output"]["fields"]==next(a["fields"] for a in rows["assets"] if a["kind"]==row["group"])
            row.update(executed=receipts[0]["id"],asset_digest=action["target"]["group_digest"],
                       document_digest=action["asset_digest"],external_writes=action["sandbox_output"]["external_writes"])
        removed=reader(api,owner,"admin")
        stale["action_id"]="withdrawn-dispatch"
        accepted(command("schedule",owner,**stale))
        accepted(command("authorize",removed,action_id=stale["action_id"]))
        from test_studio_postgres import demote
        demote(pool.owner,owner,removed)
        reject_scheduled(stale["action_id"])
        stale["action_id"]="superseded-dispatch"
        accepted(command("schedule",owner,**stale))
        accepted(command("authorize",approver,action_id=stale["action_id"]))

    def reject_scheduled(action_id):
        with fresh_process() as service:
            res=service.post(root+"/sandbox/dispatch",headers=owner["headers"]|{"X-AMC-Sandbox-Dispatch":service_key},
                             json={"kind":"execute","plan_id":plan["id"],"action_id":action_id,"request_id":uuid4().hex})
            assert res.status_code==409,res.text
        assert not any(r["kind"]=="execute" and r["entity_id"]==action_id for r in accepted(api.get(root+"/sandbox",headers=owner["headers"]))["receipts"])

    lifecycle(api, base, owner, buyer, pool.cases[1][2], doc, snap, plan, editor, observe=inspect)
    reject_scheduled(stale["action_id"])  # lifecycle saves a newer Studio revision after the observer returns.
    assert len(evidence) == 8
    if directory := os.getenv("AMC_DEPT_OPS_EVIDENCE"):
        path = Path(directory)
        path.mkdir(exist_ok=True, parents=True)
        (path / "channel-dispatch.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
