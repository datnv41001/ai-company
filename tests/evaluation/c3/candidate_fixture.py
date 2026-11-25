"""Build the candidate via signed business APIs and the same restricted queue as staff."""
from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

from agency_fixtures import create
from c3_fixtures import capture, prepared
from migrations.apply import publish_registry


def queue_projected(lab, kind):
    case = lab.case
    root = Path(__file__).resolve().parents[3]
    filename = {"WF-03": "research-strategy-v2.json", "WF-13": "landing-seo-v5.json"}[kind]
    manifest = json.loads((root / "catalog" / filename).read_text(encoding="utf8"))
    workflow = f"{manifest['workflow_id']}@{manifest['workflow_version']}"
    with lab.owner.transaction():
        publish_registry(lab.owner, manifest)
    base, admin, reader, client, campaign = lab.cases[0]
    lab.api.put(base + "/workforce/registry/" + campaign, headers=admin["headers"], json={
        "action": "activate", "workflow": workflow, "skills": manifest["required"],
    }).raise_for_status()
    bid = create(lab.api, base + "/workforce/briefs", admin, {
        "title": case["objective"], "recipient_id": reader["id"], "campaign_id": campaign,
    })["id"]
    uri = base + "/workforce/briefs/" + bid
    refs = [{"label": f["id"], "excerpt": f["wording"] + " " + f["qualifiers"]} for f in case["facts"]]
    refs.append({"label": "Giả thuyết và khoảng trống", "excerpt": case["hypotheses"][0] + " " + case["gaps"][0]})
    lab.api.put(uri + "/submission", headers=reader["headers"], json={
        "objective": case["objective"] + ". KPI: " + case["kpi"] + ". Kênh: " + case["channel"],
        "audience": case["audience"], "offer": case["product"] + ". CTA: " + case["cta"], "sources": refs,
    }).raise_for_status()
    if hasattr(lab, "business_case"):
        data = deepcopy(lab.business_case)
        data["params"].update(key=uuid4().hex, target={"campaign_id":campaign,"brief_id":bid}, workflow=workflow)
    else:
        inputs=deepcopy(case)
        for fact in inputs["facts"]:
            fact["qualifiers"]=[fact["qualifiers"]]
        data=prepared(lab.api,admin,base,client,lab.brand,campaign,bid,workflow,case=inputs)
        lab.business_case=data
    snap = capture(lab.api, admin, data)
    queued = lab.api.post(uri + "/run", headers=admin["headers"], json={
        "registry_workflow": workflow, "workflow": "dynamic-v1", "budget_microusd": 10000, "max_parallel_nodes": 1,
        "knowledge_manifest": {"id":snap["id"],"digest":snap["digest"]},
    })
    queued.raise_for_status()
    return queued.json()["id"], workflow

