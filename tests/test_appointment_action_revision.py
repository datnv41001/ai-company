"""Migrate approved service copy through the Studio and preserve its signed files."""
from base64 import b64decode
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app import c3_actions, c3_studio, campaign_channels
from app.models import utcnow
from knowledge_fixtures import accepted
from test_c3_content_gate import approve
from test_channel_editions import sqlite_channel, workforce  # noqa: F401
from test_claim_desk import reader


def test_action_wording_follows_the_approved_action_and_offer():
    assert c3_actions.action_label("appointment", "vi-VN", "Dịch vụ khảo sát hiện trường") == "Gửi đề nghị khảo sát"
    assert c3_actions.action_label("appointment", "en-US", "Site survey") == "Request a survey"
    assert c3_actions.action_label("appointment", "en-US", "Portrait consultation") == "Request an appointment"
    assert c3_actions.action_label("rfq", "en-US", "Site survey kit") == "Request a quote"


@pytest.mark.parametrize("case", ["receipt-map", "index-tray"])
def test_archived_aligned_artifacts_match_source_and_exact_file_qa(case):
    base = Path(__file__).resolve().parents[1] / "docs/evaluation"
    folder = base / "aligned-intake" / case
    proof = json.loads((folder / "evidence.json").read_text(encoding="utf8"))
    channels = json.loads((folder / "channel.json").read_text(encoding="utf8"))
    for kind, filename in (("creative", "portrait.png"), ("landing", "landing.html")):
        item = proof[kind]
        assert item["plan_digest"] == channels["plan"]["plan_digest"] and item["studio_revision"] == channels["revision"]
        assert item["group_receipts"]["copy"] == channels["group_approvals"]["copy"]["receipt"]
        assert item["production_qa"]["digest"] == item["digest"] and item["production_qa"]["reviewer"] != item["created_by"]
        assert sha256((folder / filename).read_bytes()).hexdigest() == item["files"][filename]["sha256"]
    form = proof["events"][1]["value"]
    assert form["landing_digest"] == proof["landing"]["digest"] and form["assignee_id"] is None
    if case == "receipt-map":
        label = proof["creative"]["master"]["cta"]
        storyboard = json.loads((base/"campaign-production-review"/case/"edit.json").read_text(encoding="utf8"))
        assert label == storyboard["shots"][-1]["caption"].rstrip(".") == "Gửi đề nghị khảo sát"
        assert all(channels["assets"][name]["buyer_action"] == label for name in ("social", "ad"))
        assert label in proof["landing"]["master"]["seo"]["meta_description"]
        assert form["state"] == "requested" and form["confirmed_for"] is None
    else:
        assert "commercial_moq" in form["missing"] and proof["intake"]["landing_funnel"]["qualified_rfqs"] == 0


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_signed_survey_cta_replaces_old_package_on_same_document(api, workforce, monkeypatch):  # noqa: F811
    briefs = json.loads((Path(__file__).parent / "evaluation/department/briefs-v1.json").read_text(encoding="utf8"))
    case = next(c for c in briefs["cases"] if c["id"] == "receipt-map")
    doc, snap, plan, editor, _, _ = sqlite_channel(api, workforce, monkeypatch, case)
    owner, buyer, _, base, *_ = workforce
    reviewer = reader(api, owner, "admin")
    studio = doc + "/studio"
    production = studio + "/production"
    def post(actor, url, payload):
        return api.post(url, headers=actor["headers"], json=payload)

    def edit():
        view = accepted(api.get(studio, headers=owner["headers"]))
        groups = c3_studio.compose(snap["workflow"], snap["projection"]) | view["channel_edition"]["groups"]
        return accepted(api.patch(studio, headers=owner["headers"], json={"expected_revision":view["revision"], "groups":groups,
                        "delivery_version":campaign_channels.VERSION, "expected_plan_digest":plan["digest"]}))

    def read_file(item, name):
        value = accepted(api.get(f"{production}/{item['id']}/files/{name}", headers=owner["headers"]))
        data = b64decode(value["base64"])
        assert sha256(data).hexdigest() == item["files"][name]["sha256"]
        return data

    def commission(view, prior):
        submission = accepted(api.post(doc + "/submit", headers=editor["headers"]))
        terms = {"expected_qa_revision":view["revision"], "expected_content_digest":submission["qa_evidence"]["content_digest"]}
        for group, asset_digest in view["asset_digests"].items():
            accepted(post(reviewer, studio + "/approvals", {"group":group, "expected_revision":view["revision"],
                          "expected_asset_digest":asset_digest, "note":"Đối chiếu CTA và trạng thái yêu cầu với brief."}))
        accepted(approve(api, doc, reviewer, terms))
        review = accepted(post(owner, doc + "/share", terms | {"expires_at":(utcnow()+timedelta(days=1)).isoformat()}))
        items = {}
        for kind, groups in (("creative", ("copy", "creative_brief")), ("landing", ("copy", "seo"))):
            item = accepted(post(owner, production, {"kind":kind, "expected_revision":view["revision"],
                "expected_plan_digest":plan["digest"], "expected_version":prior,
                "expected_groups":{name:view["asset_digests"][name] for name in groups}}))
            item["production_qa"] = accepted(post(reviewer, f"{production}/{item['id']}/approve",
                {"expected_digest":item["digest"], "note":"Đối chiếu master, CTA và trang với bản đang duyệt."}))
            items[kind] = item
        return review, items

    # Replay only the predecessor's CTA wording. Both editions use real revision, file, and signing APIs.
    with monkeypatch.context() as historic:
        historic.setattr(c3_studio, "action_label", lambda action, locale, product: "Đặt lịch")
        before = edit()
        original_review, old = commission(before, 0)
    original_files = {kind:read_file(old[kind], name) for kind, name in (("landing","landing.html"),("creative","portrait.png"))}
    assert "Đặt lịch".encode() in original_files["landing"] and old["creative"]["master"]["cta"] == "Đặt lịch"
    after = edit()
    assert after["revision"] == before["revision"] + 1 and not after["approvals"]
    groups = after["groups"]
    stale = {**groups, "seo":{**groups["seo"], "meta_description":before["groups"]["seo"]["meta_description"]}}
    assert {"group":"seo","field":"meta_description","reason":"buyer_action"} in c3_studio.quality_issues(snap["workflow"], stale, snap["projection"])
    rejected = post(reviewer, studio + "/approvals", {"group":"copy", "expected_revision":before["revision"],
                    "expected_asset_digest":before["asset_digests"]["copy"], "note":"Stale edition"})
    assert rejected.status_code == 412
    new_review, new = commission(after, 1)
    label = "Gửi đề nghị khảo sát"
    for kind, name in (("landing","landing.html"),("creative","portrait.png")):
        assert new[kind]["version"] == 2 and old[kind]["group_receipts"] != new[kind]["group_receipts"]
        assert new[kind]["production_qa"]["digest"] == new[kind]["digest"] != old[kind]["digest"]
        assert read_file(old[kind], name) == original_files[kind] != read_file(new[kind], name)
    assert label.encode() in read_file(new["landing"], "landing.html") and label == new["creative"]["master"]["cta"]
    assert new_review["digest"] != original_review["digest"]
    old_review = accepted(api.get(base+"/reviews/"+original_review["id"], headers=buyer["headers"]))
    assert (old_review["digest"],old_review["preview"]) == (original_review["digest"],original_review["preview"])
    assert post(owner, f"{production}/{old['landing']['id']}/visits", {"request_id":uuid4().hex}).status_code == 409
    landing = f"{production}/{new['landing']['id']}"
    visit = accepted(post(owner, landing + "/visits", {"request_id":uuid4().hex}))
    receipt = accepted(post(owner, landing + "/submissions", {"request_id":uuid4().hex, "visit_id":visit["entity_id"],
        "contract_digest":plan["intake_contract"]["digest"], "consent":True, "answers":{"site":"north","receiving_shift":"evening"}}))
    assert receipt["value"]["state"] == "requested" and receipt["value"]["assignee_id"] is None
    if directory := os.getenv("AMC_CTA_REVISION_EVIDENCE"):
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        def summary(items):
            keys = ("id","did","kind","version","studio_revision","plan_digest","manifest","digest","group_receipts","production_qa","files")
            return {kind:{k:item[k] for k in keys} for kind,item in items.items()}
        (folder/"revision.json").write_text(json.dumps({"source":"synthetic same-document API replay of the previous CTA",
             "previous":summary(old),"revised":summary(new),"original_snapshot":original_review["digest"],
             "revised_snapshot":new_review["digest"],"old_decision_http":rejected.status_code,
             "visit":visit["id"],"submission":receipt},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
