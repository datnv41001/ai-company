"""Immutable plan versions must agree with each approved production brief."""
from uuid import uuid4

from app import c3_assets
from campaign_planner_fixtures import CASES, prepare_inputs
from knowledge_fixtures import accepted


def test_conflicting_commissions_require_new_approved_inputs(api, agency):
    owner, base, ((customer, scope), (other, _)) = agency
    headers = owner["headers"]
    cid = next(iter(scope["campaigns"]))
    campaigns = accepted(api.get(base + "/campaigns", headers=headers))
    brand = next(c["brand_id"] for c in campaigns if c["id"] == cid)
    snaps, _ = prepare_inputs(api, owner, customer, next(iter(scope["clients"])), brand, cid,
                              CASES[0], workflows=(c3_assets.LANDING,))
    snap = snaps[0]
    path = base + "/campaigns/" + cid + "/engine"
    for rev, changes in enumerate(({"target_outcome": "A new objective never commissioned"},
                                   {"channels": [snap["projection"]["channel"], "unapproved channel"]}, {})):
        proposal = accepted(api.post(path + "/plans", headers=headers, json={
            "key": uuid4().hex, "expected_revision": rev, "manifest_ids": [snap["id"]],
            "budget_vnd": 987654, "ai_budget_microusd_per_run": 7632, "duration_days": 19, **changes}))
        args = {"key": uuid4().hex, "expected_digest": proposal["digest"]}
        approve = path + "/plans/" + proposal["id"] + "/approve"
        assert api.post(approve, headers=other["headers"], json=args).status_code in (403, 404)
        result = api.post(approve, headers=headers, json=args)
        if changes:
            assert result.status_code == 409 and "manifest" in result.text
        else:
            accepted(result)
    planner = accepted(api.get(path + "/planner", headers=headers))
    assert len(planner["revisions"]) == 3 and planner["active"]["id"] == proposal["id"]
    assert planner["active"]["budget_vnd"] == 987654 and planner["active"]["ai_budget_microusd_per_run"] == 7632
