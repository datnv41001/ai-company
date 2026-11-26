"""Exercise the optional Content Factory writer on the combined development build."""
from datetime import timedelta
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app import c3_assets
from app.models import utcnow
from knowledge_fixtures import accepted
from test_claim_desk import reader
from test_registry import PG, pool as registry_pool
from test_studio_postgres import agency_draft

pool = registry_pool


@PG
def test_dispatch_reviewed_channel_editions(pool):
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

    lifecycle(api, base, owner, buyer, pool.cases[1][2], doc, snap, plan, editor, observe=inspect)
    assert len(evidence) == 4
    if directory := os.getenv("AMC_DEPT_OPS_EVIDENCE"):
        path = Path(directory)
        path.mkdir(exist_ok=True, parents=True)
        (path / "channel-dispatch.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
