"""Regression for incompatible commercial declarations, with real normal-API positive controls."""

import pytest

from agency_fixtures import account
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, bundle, call, revision


def declaration(api, owner, path, field, name, value, placement, *, visibility="public", **details):
    kind = "availability" if field == "availability" else "policy"
    facts = {"status": value, "observed_at": "2025-01-01T00:00:00Z", "valid_until": "2099-01-01T00:00:00Z"} if kind == "availability" else {field: value}
    return revision(api, owner, path, name, kind, {"placement": placement, **facts, **details}, visibility=visibility)


def supported_claim(api, owner, path, field, suffix, value, placement, authority, band=None):
    key = "availability" if field == "availability" else "policy"
    assertion = dict(category=field, wording=value, qualifiers=[], placement=placement, **{key: authority["id"]})
    if band:
        assertion["applicability"] = band
    src = revision(
        api,
        owner,
        path,
        "sheet-" + suffix,
        "source",
        dict(
            publisher="Synthetic catalogue",
            document="Controlled fixture",
            valid_until="2099-01-01T00:00:00Z",
            entries=[dict(locator="r1", excerpt=value, assertion=assertion)],
        ),
    )
    binding = revision(api, owner, path, "bind-" + suffix, "binding", dict(source=src["id"], locator="r1", assertion=assertion))
    return revision(api, owner, path, "claim-" + suffix, "claim", dict(binding=binding["id"], assertion=assertion))


@pytest.mark.parametrize(
    ("field", "positive", "contrary"),
    [("availability", "available", "unavailable"), ("warranty", "12 months", "24 months"), ("payment", "Prepaid", "Cash on delivery")],
)
def test_colliding_authority_requires_audited_resolution(api, field, positive, contrary):
    owner, path, source, _, _ = bundle(api)
    placement = api.get(path + "/revisions/" + source["id"], headers=owner["headers"]).json()["data"]["entries"][0]["assertion"]["placement"]
    primary = declaration(api, owner, path, field, "a", positive, placement)
    claim = supported_claim(api, owner, path, field, "first", positive, placement, primary)

    def preview(user):
        return call(api, user, path, "/previews", claims=[claim["id"]])

    before = accepted(preview(owner))
    original = accepted(call(api, owner, path, "/authorize", operation="queue", snapshot_id=before["id"], digest=before["digest"]))
    editor = account(api, "CommerceEditor")
    invite_member(api, "/api/tenants/" + owner["tenant"], owner["headers"], editor["headers"], email=editor["email"], role="editor")
    # Another current approved declaration may contain restricted source data.
    private = declaration(api, owner, path, field, "b", contrary, placement, visibility="restricted")
    for actor in (owner, editor):
        stopped = preview(actor)
        assert stopped.status_code == 409, stopped.text
        assert stopped.json()["detail"] == "Commercial authority disputed"
        assert contrary not in stopped.text and private["id"] not in stopped.text
    fresh = call(api, owner, path, "/authorize", operation="qa", previous_receipt=original["id"], snapshot_id=before["id"], digest=before["digest"])
    assert fresh.status_code == 409
    history = api.get(path + "/snapshots/" + before["id"], headers=owner["headers"]).json()
    assert (history["canonical"], history["digest"], history["current_authority_issue"]) == (
        before["canonical"],
        before["digest"],
        "Commercial authority disputed",
    )
    assert api.get(path + "/receipts/" + original["id"], headers=owner["headers"]).json() == original
    accepted(
        call(
            api,
            owner,
            path,
            f"/revisions/{private['id']}/events",
            state="withdrawn",
            reason="Supplier withdrew alternative",
            expected_digest=private["digest"],
            expected_sequence=1,
        )
    )
    assert preview(editor).status_code == 201
