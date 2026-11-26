"""Commission matched presentations of the same approved business evidence through ordinary scoped APIs."""

from copy import deepcopy
import json
from uuid import uuid4

from agency_fixtures import create
from app import c3_assets
from campaign_planner_fixtures import facts
from c3_fixtures import capture, prepared
from c3_task_fixtures import INTENT
from knowledge_fixtures import accepted, revision
from migrations.apply import publish_registry

WORKFLOWS = {"strategy": c3_assets.RESEARCH, "landing": c3_assets.LANDING}


def commission(lab, case, root, sequence, existing):
    api = lab.api
    base, owner, customer, client, campaign = lab.cases[0]
    engine = base + "/campaigns/" + campaign + "/engine"
    snapshots = {}
    for kind, workflow in WORKFLOWS.items():
        if not sequence:
            file = "research-strategy-v3.json" if kind == "strategy" else "landing-seo-v6.json"
            release = json.loads((root / "catalog" / file).read_text())
            publish_registry(lab.owner, release)
            accepted(
                api.put(
                    base + "/workforce/registry/" + campaign,
                    headers=owner["headers"],
                    json={"action": "activate", "workflow": workflow, "skills": release["required"]},
                )
            )
        bid = create(api, base + "/workforce/briefs", owner, {"campaign_id": campaign, "recipient_id": customer["id"], "title": case["objective"]})["id"]
        intent = INTENT | {k: case[k] for k in ("product", "audience", "buyer_action", "exclusions")}
        intent.update(
            purpose=case["objective"],
            deliverable_type="marketing_strategy" if kind == "strategy" else "landing_page",
            requirements=[case["cta"]],
            editorial_style="plain",
            acceptance_criteria=[case["kpi"]],
        )
        payload = {
            "objective": case["objective"],
            "audience": case["audience"],
            "offer": case["product"],
            "sources": [{"label": "Mô tả tổng hợp", "excerpt": case["wording"] + ". " + case["qualifier"]}],
            "task_intent": intent,
        }
        accepted(api.put(base + "/workforce/briefs/" + bid + "/submission", headers=customer["headers"], json=payload))
        if existing is None:
            existing = prepared(api, owner, base, client, lab.brand, campaign, bid, workflow, case=case | {"facts": facts(case)})
            guide = revision(
                api,
                owner,
                existing["path"],
                "brand-study-voice",
                "guidelines",
                {"guidance": "Nêu đúng điều kiện, không suy diễn chứng nhận hoặc mức tiết kiệm.", "tone": "Cụ thể"},
            )
            existing["params"]["guidelines"] = guide["id"]
        current = deepcopy(existing)
        current["params"].update(workflow=workflow, target={"campaign_id": campaign, "brief_id": bid}, key=uuid4().hex, ttl_seconds=900)
        snapshots[kind] = capture(api, owner, current)
    proposed = accepted(
        api.post(
            engine + "/plans",
            headers=owner["headers"],
            json={
                "key": uuid4().hex,
                "expected_revision": sequence,
                "duration_days": 21,
                "budget_vnd": 2_000_000,
                "manifest_ids": [snap["id"] for snap in snapshots.values()],
            },
        )
    )
    accepted(
        api.post(engine + "/plans/" + proposed["id"] + "/approve", headers=owner["headers"], json={"key": uuid4().hex, "expected_digest": proposed["digest"]})
    )
    plan = accepted(api.get(engine + "/planner", headers=owner["headers"]))["active"]
    return existing, engine, plan, snapshots
