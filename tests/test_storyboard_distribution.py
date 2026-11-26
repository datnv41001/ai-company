"""Run a scoped WF-08 edition into an actual Studio intake and restricted CRM on PostgreSQL."""

from base64 import b64decode
from copy import copy
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app import c3_assets, c3_skill_library, c3_studio, campaign_channels
from c3_fixtures import capture, withdraw
from knowledge_fixtures import accepted
from migrations.apply import publish_registry
from test_c3_authority import doc_and_decision
from test_channel_editions import commission
from test_claim_desk import reader
from test_registry import PG, policy, pool as registry_pool
from test_role_qa_rollout import post_output
from test_video_storyboard import CASES, ROOT, start, work
from test_workforce import DATA

pool = registry_pool


def approved_destination(lab, base, owner, buyer, prep, board_snapshot, qa):
    api = lab.api
    scope = prep["params"]["target"]
    brief = base + "/workforce/briefs"
    page = accepted(api.post(brief, headers=owner["headers"], json={
        "title": "Trang tiếp nhận yêu cầu báo giá", "campaign_id": scope["campaign_id"], "recipient_id": buyer["id"]}))
    intent = board_snapshot["projection"]["task_intent"].copy()
    for key in ("duration_seconds", "rights", "aspect_ratio"):
        intent.pop(key)
    intent.update(deliverable_type="landing_page", requirements=["Trình bày sản phẩm và biểu mẫu báo giá."])
    accepted(api.put(brief + "/" + page["id"] + "/submission", headers=buyer["headers"], json=DATA | {"task_intent": intent}))
    workflow = c3_assets.LANDING
    registry = json.loads((ROOT / "catalog/landing-seo-v6.json").read_text(encoding="utf8"))
    publish_registry(lab.owner, registry)
    accepted(policy(lab, "activate", skills=registry["required"], workflow=workflow))
    selection = prep["params"] | {"key": uuid4().hex, "workflow": workflow, "target": scope | {"brief_id": page["id"]}}
    snap = capture(api, owner, prep | {"params": selection})
    plan = commission(api, base, owner, scope["campaign_id"], snap)
    url = base + "/campaigns/" + scope["campaign_id"] + "/engine/plans/" + plan["id"]
    run = accepted(api.post(url + "/runs/landing", headers=owner["headers"]))
    for stage in ("director", *c3_assets.ROLES[workflow]):
        if stage == "director":
            output = {"primary_assignment": "Explain the source-bound buyer action and product.",
                      "secondary_assignment": "Prepare the controlled intake edition and measurement plan."}
        else:
            output = {k: v for ref in c3_skill_library.PACKS[stage] for k, v in c3_skill_library.method(ref)["examples"]["good"].items()}
            output["source_ids"] = ["F1"]
        post_output(lab, run["id"], "c3_skills_" + stage, output)
    doc, _ = doc_and_decision(lab, base, owner, run["id"])
    studio = doc + "/studio"
    proposal = accepted(api.get(studio, headers=owner["headers"]))
    groups = c3_studio.compose(workflow, snap["projection"]) | proposal["channel_edition"]["groups"]
    saved = accepted(api.patch(studio, headers=owner["headers"], json={
        "groups": groups, "expected_revision": proposal["revision"], "delivery_version": campaign_channels.VERSION,
        "expected_plan_digest": plan["digest"]}))
    approved = accepted(api.post(doc + "/submit", headers=owner["headers"]))
    unresolved = [(r["field"], r["text"], r["outcome"]) for r in saved["findings"] if r["outcome"] not in ("verified", "editorial")]
    assert not unresolved, unresolved
    for group in groups:
        accepted(api.post(studio + "/approvals", headers=qa["headers"], json={
            "group": group, "expected_revision": saved["revision"], "expected_asset_digest": saved["asset_digests"][group],
            "note": "Đối chiếu dữ kiện công khai và mục tiêu của bản giao."}))
    accepted(api.post(doc + "/review", headers=qa["headers"], json={
        "decision": "approved", "expected_qa_revision": saved["revision"], "expected_content_digest": approved["qa_evidence"]["content_digest"],
        "note": "Đã đối chiếu phiên bản theo yêu cầu báo giá."}))
    root = studio + "/production"
    landing = accepted(api.post(root, headers=owner["headers"], json={
        "kind": "landing", "expected_revision": saved["revision"], "expected_plan_digest": plan["digest"], "expected_version": 0,
        "expected_groups": {k: saved["asset_digests"][k] for k in ("copy", "seo")}}))
    url = root + "/" + landing["id"]
    accepted(api.post(url + "/approve", headers=qa["headers"], json={
        "expected_digest": landing["digest"], "note": "Đã rà soát bản trang đích và biểu mẫu thử nghiệm."}))
    return url, landing, plan


@PG
@pytest.mark.parametrize("release", [1, 2], ids=["legacy", "content-handoff"])
def test_connected_distribution(pool, release):
    lab, api = pool, pool.api
    case = next(c for c in CASES if c["id"] == "index-tray")
    case = case | {"objective": "Nhận yêu cầu báo giá " + case["product"]}
    args = {}
    if release == 2:
        from test_storyboard_brief import case_input
        case, overrides = case_input(case)
        args = {"release": "WF-08/video-storyboard@2", "intent_overrides": overrides}
    base, owner, buyer, prep, snap, queued = start(lab, case, **args)
    rid = queued["id"]
    trace_url = base + "/workforce/runs/" + rid
    states = [queued]
    for stage in ("director", *(["content"] if release == 2 else []), "storyboard"):
        work(lab, rid, stage, states)
    trace = accepted(api.get(trace_url, headers=owner["headers"]))
    raw = json.loads(trace["checkpoints"][-1]["output"]["text"])
    board_doc, original = doc_and_decision(lab, base, owner, rid)
    qa = reader(api, owner, "admin")
    terms = {k: v for k, v in original.items() if k.startswith("expected_")}
    edition = accepted(api.post(trace_url + "/storyboard-edition", headers=owner["headers"], json=terms | {"hook_variant": "audience"}))
    current = dict(expected_qa_revision=edition["revision"], expected_content_digest=edition["content_digest"])
    accepted(api.post(board_doc + "/submit", headers=owner["headers"]))
    accepted(api.post(board_doc + "/review", headers=qa["headers"], json=original | current))
    landing_path, landing, plan = approved_destination(lab, base, owner, buyer, prep, snap, qa)
    root = landing_path + "/storyboard-distributions"
    evidence = {"request_scope": "authenticated synthetic", "release": release, "states": states, "worker_journal": trace["journal"],
                "raw_checkpoint": trace["checkpoints"][-1], "rejected": {}}

    def put(url, data, actor=owner):
        return api.post(url, headers=actor["headers"], json=data)

    def reject(name, response, code):
        assert response.status_code == code, response.text
        evidence["rejected"][name] = code

    body = dict(request_id=uuid4().hex, storyboard_document_id=trace["deliverable_id"], expected_run_id=rid,
                expected_revision=edition["revision"], expected_content_digest=edition["content_digest"],
                expected_landing_digest=landing["digest"], style="parts")
    reject("other_customer", put(root, body, lab.cases[1][2]), 404)
    reject("foreign_tenant", put(root, body, lab.y), 404)
    if release == 2:
        # One agency owner can read both customers. Even identical synthetic
        # briefs and product names must never join across the two client IDs.
        other = copy(lab)
        other.cases = [lab.cases[1], lab.cases[0], *lab.cases[2:]]
        _, _, _, _, _, foreign = start(other, case, **args)
        for stage in ("director", "content", "storyboard"):
            work(other, foreign["id"], stage, [])
        foreign_doc, foreign_qa = doc_and_decision(other, base, owner, foreign["id"])
        reject("agency_owner_cross_client_source", put(root, body | {
            "expected_run_id": foreign["id"], "storyboard_document_id": foreign_doc.rsplit("/", 1)[-1],
            "expected_revision": foreign_qa["expected_qa_revision"], "expected_content_digest": foreign_qa["expected_content_digest"]}), 404)
    reject("stale_revision", put(root, body | {"expected_revision": original["expected_qa_revision"]}), 412)
    binding = accepted(put(root, body))
    assert accepted(put(root, body)) == binding
    reject("reused_request_changed_style", put(root, body | {"style": "route"}), 409)
    dist = root + "/" + binding["id"]
    visit_req = {"request_id": uuid4().hex}
    reject("unsigned_preview", put(dist + "/visits", visit_req), 409)
    files = {}
    for name, checksum in binding["preview"]["renderer"]["files"].items():
        artifact = accepted(api.get(dist + "/files/" + name, headers=qa["headers"]))
        files[name] = b64decode(artifact["base64"])
        assert sha256(files[name]).hexdigest() == checksum
    decision = {"expected_digest": binding["distribution_digest"], "note": "Đã đối chiếu khung hình, phụ đề và bản trang đích."}
    reject("self_approval", put(dist + "/approve", decision), 409)
    assert accepted(put(dist + "/approve", decision, qa)) == accepted(put(dist + "/approve", decision, qa))
    current_view = accepted(api.get(dist, headers=owner["headers"]))
    assert current_view["storyboard"]["run_id"] == rid and current_view["landing"]["plan_id"] == plan["id"]
    files["landing.html"] = b64decode(accepted(api.get(landing_path + "/files/landing.html", headers=owner["headers"]))["base64"])
    assert sha256(files["landing.html"]).hexdigest() == current_view["landing"]["file_digest"]
    visit = accepted(put(dist + "/visits", visit_req))
    assert visit == accepted(put(dist + "/visits", visit_req))
    contract = landing["master"]["intake_contract"]
    answers = {f["id"]: f["minimum"] if f["type"] == "integer" else f["options"][0]["value"] for f in contract["fields"]}
    form = {"request_id": uuid4().hex, "visit_id": visit["entity_id"], "contract_digest": contract["digest"], "consent": True, "answers": answers}
    reject("unbound_submission_for_connected_visit", put(landing_path + "/submissions", form), 409)
    submission = accepted(put(dist + "/submissions", form))
    assert submission == accepted(put(dist + "/submissions", form))
    reject("replay_as_unbound_submission", put(landing_path + "/submissions", form), 409)
    source = submission["value"]["landing_source"]
    assert source == visit["value"]["landing_source"] and source["storyboard_distribution"]["id"] == binding["id"]
    campaign = base + "/campaigns/" + plan["campaign_id"]
    desk = campaign + "/business-desk"
    operator = reader(api, owner, "editor")
    accepted(put(desk + "/grants", {"key": uuid4().hex, "subject": operator["id"], "role": "marketing_operator",
                                    "enabled": True, "expected_revision": 0}))
    inbox = accepted(api.get(desk + "/marketing_operator/inbox", headers=operator["headers"]))
    crm = next(i for i in inbox["items"] if i["value"]["id"] == submission["entity_id"])
    assert crm["value"]["intake"]["answers"] == answers and crm["value"]["landing_source"] == source
    metric = accepted(api.get(campaign + "/sandbox", headers=owner["headers"]))["intake_measurement"]
    assert metric["window"] == "approved_plan_lifetime" and metric["landing_visits"] == metric["valid_submissions"] == 1
    assert metric["manual_requests"] == metric["orders"] == 0
    if release == 2:
        changed = accepted(put(trace_url + "/storyboard-edition", current | {
            "mode": "controlled_hook", "hook_variant": "style_alternate",
            "distribution": {"landing_did": current_view["landing"]["document_id"], "landing_pid": landing["id"],
                             "distribution_id": binding["id"]}}))
        evidence["offline_comparison"] = changed["receipt"]["comparison"]
        reject("stale_distribution_after_edit", put(dist + "/visits", visit_req), 409)
    else:
        withdraw(api, owner, prep)
        reject("withdrawn_source", put(dist + "/visits", visit_req), 409)
    evidence.update(distribution=current_view, visit=visit, submission=submission, crm=crm, measurement=metric,
                    creative_effectiveness=None, primary_kpi=None, paid_media_spend=0)
    if folder := os.environ.get("AMC_CONNECTED_EVIDENCE"):
        dest = Path(folder) / f"wf08-v{release}"
        dest.mkdir(parents=True, exist_ok=False)
        for name, data in files.items():
            (dest / name).write_bytes(data)
        for name, item in (("receipt", evidence), ("worker-board", raw), ("approved-edition", edition["storyboard"])):
            (dest / (name + ".json")).write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")

