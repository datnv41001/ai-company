"""C3 readiness, immutable projection, guarded queue / QA / share, and independent scope."""

import json
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from app import c3_marketing
from c3_fixtures import capture, prepared, withdraw
from knowledge_fixtures import accepted, revision
from migrations.apply import publish_registry
from test_business_workspace import post
from test_company_objectives import decision
from test_registry import PG, policy, pool as registry_pool, registry_brief
from test_role_qa_rollout import post_output
from test_workforce import DATA, workforce as workforce_fixture

workforce = workforce_fixture
pool = registry_pool
ROOT = Path(__file__).resolve().parents[1]


def test_scope_and_historical_manifests(api, workforce):
    owner, reader, _, base, root, scope, _, brief = workforce
    bid = brief["id"]
    api.put(root + "/briefs/" + bid + "/submission", headers=reader["headers"], json=DATA).raise_for_status()
    prep = prepared(api, owner, base, scope.client, scope.brand, scope.campaign, bid)
    api_path, body = prep["marketing"], prep["params"]
    assert post(api, api_path + "/readiness", owner, status=200, **body)["status"] == "ready"
    frozen = capture(api, owner, prep)
    projection = frozen["projection"]
    assert projection["facts"] == [{"id": "F1", "wording": "Matte surface", "category": "description", "qualifiers": []}]
    from fastapi import HTTPException
    from app.c3_projection import check_delivery_capacity

    large = [{"id": f"F{i}", "wording": "A" * 1800, "qualifiers": [str(j).ljust(160, "B") for j in range(12)]} for i in range(12)]
    with pytest.raises(HTTPException, match="every qualifier"):
        check_delivery_capacity(c3_marketing.LANDING, projection | {"facts": large})
    assert "PRIVATE_SYNTHETIC" not in json.dumps(frozen) and prep["sources"][0]["id"] not in json.dumps(frozen)
    assert capture(api, owner, prep) == frozen
    private_path = api_path + "/manifests/" + frozen["id"] + "/provenance"
    trace = accepted(api.get(private_path, headers=owner["headers"]))
    assert trace["entries"][0]["source_revision"] == prep["sources"][0]["id"]
    assert (trace["entries"][0]["handle"], trace["entries"][0]["locator"]) == ("F1", "private locator")
    from test_claim_desk import reader as create_member
    from agency_fixtures import account

    for denied in (reader, create_member(api, owner, "editor"), account(api, "Other evidence agency")):
        assert api.get(private_path, headers=denied["headers"]).status_code == 404
    assert api.get(api_path + "/manifests/" + frozen["id"], headers=reader["headers"]).status_code == 404
    for updates in ({"region": "VN-DN"}, {"locale": "fr-FR"}, {"channel": "store"}):
        failed = post(api, api_path + "/readiness", owner, status=200, **(body | updates))
        assert failed["status"] == "needs_input" and failed["guidance"]
    variant = revision(api, owner, prep["path"], "different-sku", "variant", {"name": "Variant B", "sku": "B", "product": prep["selections"]["product"]})
    other = post(
        api,
        prep["ui"] + "/briefs",
        owner,
        title="Variant brief",
        expected_revision=1,
        expected_company_revision=1,
        selections=prep["selections"] | {"product": variant["id"]},
    )
    post(api, api_path + "/manifests", owner, status=409, **(body | {"key": uuid4().hex, "workspace_brief_id": other["id"]}))
    accepted(withdraw(api, owner, prep))
    assert accepted(api.get(private_path, headers=owner["headers"])) == trace
    assert post(api, api_path + "/readiness", owner, status=200, **body)["status"] == "needs_input"
    assert api.get(api_path + "/manifests/" + frozen["id"], headers=owner["headers"]).json() == frozen
    assert api.get(prep["path"] + "/snapshots/" + frozen["id"], headers=owner["headers"]).status_code == 404


def setup_pool(lab, workflow=c3_marketing.LANDING, *, case=None):
    lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=any(%s)", (lab.runs,))
    name = "research-strategy-v2" if workflow == c3_marketing.RESEARCH else "landing-seo-v5"
    manifest = json.loads((ROOT / "catalog" / (name + ".json")).read_text(encoding="utf-8"))
    publish_registry(lab.owner, manifest)
    policy(lab, "activate", skills=manifest["required"], workflow=workflow).raise_for_status()
    run_path, terms = registry_brief(lab)
    base, owner, reader, client, campaign = lab.cases[0]
    brand = lab.owner.execute("select brand_id from campaigns where id=%s", (campaign,)).fetchone()[0]
    data = prepared(lab.api, owner, base, client, brand, campaign, run_path.split("/")[-2], workflow, case=case)
    snap = capture(lab.api, owner, data)
    terms.update(knowledge_manifest={"id": snap["id"], "digest": snap["digest"]}, registry_workflow=workflow)
    return run_path, terms, data, snap


def run_workers(lab, rid, workflow):
    primary, secondary = c3_marketing.ROLES[workflow]
    post_output(
        lab,
        rid,
        "c3_director",
        {
            "primary_assignment": "Examine the approved scope of this exact product.",
            "secondary_assignment": "Prepare work for this product using the primary evidence.",
        },
    )
    for role in (primary, secondary):
        post_output(lab, rid, "c3_" + role, {k: "Draft a synthetic proposal for local shops" for k in c3_marketing.FIELDS[role]} | {"source_ids": ["F1"]})


def doc_and_decision(lab, base, owner, rid):
    trace = lab.api.get(base + "/workforce/runs/" + rid, headers=owner["headers"]).json()
    did = trace["deliverable_id"]
    doc = next(d for d in lab.api.get(base + "/deliverables", headers=owner["headers"]).json() if d["id"] == did)
    evidence = doc["qa_evidence"]
    return base + "/deliverables/" + did, {
        "expected_qa_revision": doc["qa_revision"],
        "expected_content_digest": evidence["content_digest"],
        "decision": "approved",
        "note": "Reviewed exact synthetic product declaration",
    }


@PG
@pytest.mark.parametrize("workflow,withdraw_stage", [(c3_marketing.RESEARCH, "qa"), (c3_marketing.LANDING, "share"), (c3_marketing.LANDING, None)])
def test_real_boundaries(pool, workflow, withdraw_stage):
    lab = pool
    long_name = "S" * 160 if withdraw_stage is None else None
    path, terms, data, snap = setup_pool(lab, workflow, case={"product": long_name} if long_name else None)
    base, owner, reader, _, _ = lab.cases[0]
    api = lab.api

    def queue(body):
        return api.post(path, headers=owner["headers"], json=body)

    assert queue({k: v for k, v in terms.items() if k != "knowledge_manifest"}).status_code == 422
    rid = accepted(queue(terms))["id"]
    knowledge = lab.owner.execute("select knowledge from workforce_runs where id=%s", (rid,)).fetchone()[0]
    for role in ("director", *c3_marketing.ROLES[workflow]):
        envelope = c3_marketing.request(SimpleNamespace(knowledge=knowledge), "synthetic", node=SimpleNamespace(skill=role))
        reference = json.loads(envelope["messages"][1]["content"])["reference"]
        assert reference["knowledge"] == c3_marketing.role_view(role, snap["projection"])
        raw = json.dumps(envelope)
        assert "PRIVATE_SYNTHETIC" not in raw and data["sources"][0]["id"] not in raw and snap["id"] not in raw
    assert accepted(queue(terms))["id"] == rid
    assert queue(terms | {"knowledge_manifest": terms["knowledge_manifest"] | {"digest": "1" * 64}}).status_code == 409
    run_workers(lab, rid, workflow)
    doc, qa = doc_and_decision(lab, base, owner, rid)
    if long_name:
        assert lab.owner.execute("select title from deliverables where id=%s", (doc.split("/")[-1],)).fetchone() == (long_name,)
    if withdraw_stage == "qa":
        decision(api, data["company"] + "/company-objectives", owner, data["root"], state="withdrawn")
    result = api.post(doc + "/review", headers=owner["headers"], json=qa)
    if withdraw_stage == "qa":
        assert result.status_code == 409
        return
    accepted(result)
    accepted(api.post(doc + "/review", headers=owner["headers"], json=qa))
    if withdraw_stage is None:
        # Rehearse a prior ruleset. Reassessment invalidates QA even if the text and save revision are unchanged.
        lab.owner.execute(
            "update deliverables set qa_evidence=(qa_evidence::jsonb || jsonb_build_object('ruleset_version','previous'))::json where id=%s",
            (doc.split("/")[-1],),
        )
        accepted(api.post(doc + "/assessment", headers=owner["headers"]))
        accepted(api.post(doc + "/review", headers=owner["headers"], json=qa))
        assert lab.owner.execute("select count(*) from knowledge_commands where snapshot_id=%s and operation='c3_qa'", (snap["id"],)).fetchone() == (2,)
    if withdraw_stage == "share":
        accepted(withdraw(api, owner, data))
    terms_share = {"expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
    assert api.post(doc + "/share", headers=owner["headers"], json=terms_share).status_code == 422
    terms_share.update(expected_qa_revision=qa["expected_qa_revision"], expected_content_digest=qa["expected_content_digest"])
    assert api.post(doc + "/share", headers=owner["headers"], json=terms_share | {"expected_qa_revision": qa["expected_qa_revision"] + 1}).status_code == 412
    result = api.post(doc + "/share", headers=owner["headers"], json=terms_share)
    if withdraw_stage == "share":
        assert result.status_code == 409
        return
    shared = accepted(result)
    assert accepted(api.post(doc + "/share", headers=owner["headers"], json=terms_share))["id"] == shared["id"]
    old = api.get(base + "/reviews/" + shared["id"], headers=reader["headers"]).json()
    # A lost share request must never deliver another approved revision just because the deadline is unchanged.
    from test_claim_desk import reader as new_member

    editor = new_member(api, owner, "editor")
    accepted(
        api.patch(doc + "/draft", headers=editor["headers"], json={"title": "Another edition", "client_preview": "Revised approved matte surface reference."})
    )
    accepted(api.post(doc + "/submit", headers=editor["headers"]))
    _, new_decision = doc_and_decision(lab, base, owner, rid)
    accepted(api.post(doc + "/review", headers=owner["headers"], json=new_decision))
    assert api.post(doc + "/share", headers=owner["headers"], json=terms_share).status_code == 412
    assert lab.owner.execute("select count(*) from client_reviews where deliverable_id=%s", (doc.split("/")[-1],)).fetchone() == (1,)
    accepted(withdraw(api, owner, data))
    assert api.get(base + "/reviews/" + shared["id"], headers=reader["headers"]).json()["preview"] == old["preview"]
    assert "Matte surface" in old["preview"] and "PRIVATE_SYNTHETIC" not in old["preview"]
