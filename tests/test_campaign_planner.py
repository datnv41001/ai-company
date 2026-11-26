from uuid import uuid4

from campaign_planner_fixtures import CASES, prepare_inputs
from c3_fixtures import withdraw
from knowledge_fixtures import accepted


def test_plan_is_revision_scoped_and_commissions_only_current_approved_inputs(api, agency):
    owner, base, ((customer, scoped), (other, unrelated)) = agency
    cid, other_cid = next(iter(scoped["campaigns"])), next(iter(unrelated["campaigns"]))
    campaigns = accepted(api.get(base + "/campaigns", headers=owner["headers"]))
    brand = next(c["brand_id"] for c in campaigns if c["id"] == cid)
    snaps, setup = prepare_inputs(api, owner, customer, next(iter(scoped["clients"])), brand, cid, CASES[0])
    path = base + "/campaigns/" + cid + "/engine"
    foreign = base + "/campaigns/" + other_cid + "/engine"
    draft = {"key": uuid4().hex, "expected_revision": 0, "manifest_ids": [s["id"] for s in snaps], "duration_days": 21, "budget_vnd": 700000}
    assert api.post(foreign + "/plans", headers=owner["headers"], json=draft).status_code == 404
    sibling = next(c for c in scoped["campaigns"] if c != cid)
    assert api.post(base + "/campaigns/" + sibling + "/engine/plans", headers=owner["headers"], json=draft).status_code == 404
    assert api.get("/api/tenants/" + other["tenant"] + "/campaigns/" + cid + "/engine/planner", headers=other["headers"]).status_code == 404
    for actor in (customer, other):
        assert api.get(path + "/planner", headers=actor["headers"]).status_code in (403, 404)

    def stage():
        return accepted(api.get(path + "/planner", headers=owner["headers"]))

    assert {s["id"] for s in stage()["choices"]} == set(draft["manifest_ids"])

    def create(body):
        return api.post(path + "/plans", headers=owner["headers"], json=body)

    first = accepted(create(draft))
    assert accepted(create(draft)) == first
    assert "composed_assets" not in first and stage()["proposed"]["composed_assets"] == []
    assert stage()["active"] is None
    assert api.get(path + "/plans/" + first["id"] + "/production", headers=owner["headers"]).json()["assets"] == []
    assert create(draft | {"key": uuid4().hex}).status_code == 409
    second = accepted(create(draft | {"key": uuid4().hex, "expected_revision": 1, "duration_days": 28, "budget_vnd": 900000}))

    def sign(p, d):
        return api.post(path + "/plans/" + p["id"] + "/approve", headers=owner["headers"], json={"key": uuid4().hex, "expected_digest": d})

    assert sign(first, first["digest"]).status_code == 409
    assert sign(second, first["digest"]).status_code == 409
    assert accepted(sign(second, second["digest"]))["status"] == "approved"
    active = stage()["active"]
    assert (active["id"], active["revision"], active["duration_days"], active["selling_unit"]) == (second["id"], 2, 28, "box")
    assert set(active["manifests"]) == {"strategy", "landing"}
    material = "/plans/" + second["id"] + "/content-pack"
    for actor in (customer, other):
        assert api.get(path + material, headers=actor["headers"]).status_code in (403, 404)
    assert api.get(foreign + material, headers=owner["headers"]).status_code in (404, 409)
    content = accepted(api.get(path + material, headers=owner["headers"]))
    assert content["plan_digest"] == active["digest"] and content["status"] == "internal_draft"
    assert sum(item["budget_vnd"] for item in content["advertising"]["ad_groups"]) == active["budget_vnd"]
    assert content["website"]["commercial_terms"] and content["organic_search"]["answer"]
    assert all(post["copy"] != content["advertising"]["descriptions"][0] for post in content["social"])
    assert len({p["id"] for p in active["work_packages"]}) == 8
    assert stage()["revisions"][1]["status"] == "superseded"
    pack = accepted(api.get(path + "/plans/" + second["id"] + "/production", headers=owner["headers"]))
    assert set(a["kind"] for a in pack["assets"]) == {"ad", "creative_brief", "social", "calendar"}
    assert all(a["manifest"] in active["manifests"].values() and a["plan_id"] == active["id"] for a in pack["assets"])
    third = accepted(create(draft | {"key": uuid4().hex, "expected_revision": 2, "budget_vnd": 100000}))
    assert sign(third, third["digest"]).status_code == 200
    assert api.get(path + material, headers=owner["headers"]).status_code == 409
    accepted(withdraw(api, owner, setup))
    assert api.post(path + "/plans/" + third["id"] + "/runs/landing", headers=owner["headers"]).status_code == 409


def test_numeric_product_variant_keeps_evidence_gate_closed(api, agency):
    owner, base, ((customer, scoped), _) = agency
    cid = next(iter(scoped["campaigns"]))
    campaigns = accepted(api.get(base + "/campaigns", headers=owner["headers"]))
    brand = next(c["brand_id"] for c in campaigns if c["id"] == cid)
    from types import SimpleNamespace
    from app import c3_assets, c3_content_evidence, c3_customer_assets, c3_studio

    original = dict(CASES[0], product=CASES[0]["product"] + " 12")
    (snap,), _ = prepare_inputs(api, owner, customer, next(iter(scoped["clients"])), brand, cid, original, workflows=(c3_assets.RESEARCH,))
    src = snap["projection"]
    groups = c3_studio.compose(snap["workflow"], src) | c3_customer_assets.strategy(src)
    preview = c3_customer_assets.preview(snap["workflow"], groups, src)
    doc = SimpleNamespace(
        id="unpublished",
        qa_revision=2,
        title=preview["title"],
        content={"client_preview": preview["body"], "studio": {"version": c3_studio.VERSION, "delivery_version": c3_customer_assets.VERSION, "groups": groups}},
    )
    run = SimpleNamespace(knowledge={"registry": {"workflow": snap["workflow"]}, "c3_projection": src, "c3_manifest": {"digest": snap["digest"]}})
    result = c3_content_evidence.assess_document(doc, run, "0" * 64)
    pending = [e for e in result["statements"] if e["outcome"] not in ("verified", "editorial", "reviewed")]
    assert any(e["field"].startswith("studio.") and "12" in e["text"] for e in pending)
