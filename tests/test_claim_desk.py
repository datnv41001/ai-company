"""Product acceptance on the real scoped API, including private evidence and invalidation."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from agency_fixtures import account
from app.access import set_context, set_worker_scope
from app.database import engine
from app.security import sign_actor
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, bundle, call, revision, scope


def reader(api, owner, role, project=None):
    actor = account(api, "Desk" + role, project)
    invite_member(api, "/api/tenants/" + owner["tenant"], owner["headers"], actor["headers"], email=actor["email"], role=role)
    return actor


def private_copy(api):
    owner, path, public_source, _, _ = bundle(api)
    editor = reader(api, owner, "editor")
    admin = reader(api, owner, "admin")
    original = api.get(path + "/revisions/" + public_source["id"], headers=owner["headers"]).json()["data"]
    assertion = original["entries"][0]["assertion"] | {"category": "performance", "wording": "Résultat du panel", "qualifiers": ["Conditions synthétiques"]}
    src = revision(
        api,
        owner,
        path,
        "private-study",
        "source",
        original
        | {
            "document": "CONFIDENTIEL-DOCUMENT",
            "publisher": "PRIVATE-PUBLISHER",
            "entries": [{"locator": "PRIVATE-LOCATOR", "excerpt": "PRIVATE-EXCERPT", "assertion": assertion}],
        },
        "restricted",
    )
    bound = revision(api, owner, path, "private-link", "binding", {"source": src["id"], "locator": "PRIVATE-LOCATOR", "assertion": assertion}, "restricted")
    claim = revision(api, owner, path, "public-statement", "claim", {"binding": bound["id"], "assertion": assertion}, approve=False)
    mandate = revision(
        api,
        owner,
        path,
        "restricted-mandate",
        "qualification",
        {"approver_id": admin["id"], "category": "performance", "basis": "PRIVATE-QUALIFICATION", "valid_until": "2099-01-01T00:00:00Z"},
        "restricted",
    )
    decision = dict(expected_digest=claim["digest"], expected_sequence=0, state="approved", reason="PRIVATE-REVIEW-NOTE", qualification_revision=mandate["id"])
    assert call(api, admin, path, "/revisions/" + claim["id"] + "/events", **decision).is_success
    return owner, editor, admin, path, src, bound, claim, mandate


def test_read_only_projection_checks_current_source_and_qualification(api):
    owner, editor, admin, path, src, bound, claim, mandate = private_copy(api)
    url = path + "/claim-desk/" + claim["id"]
    protected = [src["id"], bound["id"], mandate["id"], "PRIVATE-", "CONFIDENTIEL-DOCUMENT"]
    private_snapshot = accepted(call(api, admin, path, "/previews", claims=[claim["id"]]))
    for dest in (
        url,
        path + "/claim-desk",
        path + "/revisions/" + claim["id"] + "/events",
        path + "/revisions/" + claim["id"] + "/impact",
        path + "/revisions?kind=source",
        path + "/revisions?kind=binding",
        path + "/revisions?kind=claim",
    ):
        result = api.get(dest, headers=editor["headers"])
        assert result.is_success
        assert not any(x in result.text for x in [*protected, private_snapshot["id"]])
    for row in (src, bound, mandate):
        for suffix in ("", "/events", "/impact"):
            assert api.get(path + "/revisions/" + row["id"] + suffix, headers=editor["headers"]).status_code == 404
    assert api.get(path + "/snapshots/" + private_snapshot["id"], headers=editor["headers"]).status_code == 404
    assertion = api.get(path + "/revisions/" + claim["id"], headers=owner["headers"]).json()["data"]["assertion"]
    public_binding = revision(api, owner, path, "readable-binding", "binding", {"source": src["id"], "locator": "PRIVATE-LOCATOR", "assertion": assertion})
    assert api.get(path + "/revisions/" + public_binding["id"], headers=editor["headers"]).status_code == 404
    trail = api.get(path + "/revisions/" + public_binding["id"] + "/events", headers=editor["headers"])
    assert trail.is_success and "reason" not in trail.json()[0] and "actor" not in trail.json()[0]
    detail = api.get(url, headers=editor["headers"]).json()
    assert detail["public_wording"]["qualifiers"] == ["Conditions synthétiques"]
    assert detail["public_wording"]["placement"] == dict(product="Tile", market="Vietnam", locale="vi-VN", channel="web", region="HN")
    assert detail["evidence"] is None and detail["assertion"] is None
    assert api.get(path + "/revisions/" + claim["id"], headers=editor["headers"]).status_code == 404
    assert api.get(url, headers=admin["headers"]).json()["evidence"]["excerpt"] == "PRIVATE-EXCERPT"
    assert api.get(path + "/claim-desk/sources/" + src["id"], headers=editor["headers"]).status_code == 404
    unrelated = scope(api, owner, "Second client's brand")
    assert api.get(unrelated + "/claim-desk/" + claim["id"], headers=editor["headers"]).status_code == 404
    assert api.get(url, headers=account(api, "OtherAgency")["headers"]).status_code in (403, 404)
    approved = dict(state="withdrawn", expected_digest=mandate["digest"], expected_sequence=1, reason="Retired")
    assert call(api, owner, path, "/revisions/" + mandate["id"] + "/events", **approved).is_success
    stale = api.get(url, headers=editor["headers"])
    assert stale.is_success and stale.json()["public_wording"] is None and not any(x in stale.text for x in protected)


def test_exact_source_draft_retry_comparison_transition_and_impact(api):
    owner, path, src, first, preview = bundle(api)
    entry = api.get(path + "/claim-desk/sources/" + src["id"], headers=owner["headers"]).json()["entries"][0]
    key = uuid4().hex
    payload = dict(key=key, subject=first["subject"], expected_revision=1, source_revision=src["id"], locator=entry["locator"], assertion=entry["assertion"])
    bad = payload | {"assertion": entry["assertion"] | {"qualifiers": ["New words"]}}
    assert api.post(path + "/claim-desk/drafts", headers=owner["headers"], json=bad).status_code == 409
    current = accepted(api.post(path + "/claim-desk/drafts", headers=owner["headers"], json=payload))
    assert api.get(path + "/claim-desk/commands/" + key, headers=owner["headers"]).json() == {"kind": "claim", "id": current["id"]}
    colleague = reader(api, owner, "editor")
    assert api.get(path + "/claim-desk/commands/" + key, headers=colleague["headers"]).status_code == 404
    assert accepted(api.post(path + "/claim-desk/drafts", headers=owner["headers"], json=payload)) == current
    assert api.post(path + "/claim-desk/drafts", headers=owner["headers"], json=payload | {"key": uuid4().hex}).status_code == 409
    url = path + "/claim-desk/" + current["id"]
    detail = api.get(url, headers=owner["headers"]).json()
    assert detail["claim"]["revision"] == 2 and len(detail["revisions"]) == 2
    assert detail["evidence"]["source"]["id"] == src["id"]
    assert preview["id"] in str(api.get(path + "/claim-desk/" + first["id"], headers=owner["headers"]).json()["impact"])
    for row in [detail["evidence"]["binding"], detail["claim"]]:
        assert call(
            api,
            owner,
            path,
            "/revisions/" + row["id"] + "/events",
            state="approved",
            expected_digest=row["digest"],
            expected_sequence=0,
            reason="Source compared",
        ).is_success
    assert api.get(url, headers=owner["headers"]).json()["public_wording"]["wording"] == "Matte surface"
    assert call(
        api, owner, path, "/revisions/" + src["id"] + "/events", state="disputed", expected_digest=src["digest"], expected_sequence=1, reason="Review data"
    ).is_success
    assert api.get(url, headers=owner["headers"]).json()["public_wording"] is None


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_signed_pg_display_cannot_cross_scope_or_run_as_worker(api):
    owner, path, _, claim, _ = bundle(api)
    other = account(api, "Unrelated")
    tenant, client, brand = owner["tenant"], path.split("/")[5], path.split("/")[7]
    sql = text("SELECT amc_business.claim_display_current(:t,:c,:b,:r,NULL)")
    args = dict(t=tenant, c=client, b=brand, r=claim["id"])
    with Session(engine) as db:
        set_context(db, actor=owner["id"], tenant=tenant)
        sign_actor(db, owner["id"])
        assert db.scalar(sql, args)
        assert not db.scalar(sql, args | {"c": str(uuid4())})
        set_worker_scope(db, client, brand, str(uuid4()))
        assert not db.scalar(sql, args)
    with Session(engine) as db:
        set_context(db, actor=other["id"], tenant=tenant)
        sign_actor(db, other["id"])
        assert not db.scalar(sql, args)
