from uuid import uuid4

from agency_fixtures import account
from knowledge_fixtures import accepted, call, revision, scope
from test_business_workspace import post, read


def test_internal_brief_pins_selected_revisions_without_importing_source_data(api):
    owner = account(api, "BriefComposition")
    path = scope(api, owner, "Internal briefs")
    ui = path.removesuffix("/knowledge") + "/business-workspace"
    other = scope(api, owner, "Sibling client")
    product = revision(api, owner, path, "model-blue", "product", {"name": "Blue tile", "sku": "BL-37"})
    audience = revision(
        api, owner, path, "planners", "icp", {"name": "Project planners", "description": "Initial interviews pending", "basis": "hypothesis"}, approve=False
    )
    foreign = revision(api, owner, other, "other-blue", "product", {"name": "Other client tile"})
    restricted = revision(api, owner, path, "private-blue", "product", {"name": "Private item"}, visibility="restricted")
    found = read(api, ui + "/brief-options?slot=product&q=tile", owner)
    assert [r["id"] for r in found["items"]] == [product["id"]]
    base = dict(title="Planning study", expected_revision=0, expected_company_revision=0)
    for wrong in ({"product": foreign["id"]}, {"product": restricted["id"]}, {"audience": product["id"]}):
        post(api, ui + "/briefs", owner, status=422, **base, selections=wrong)
    key = uuid4().hex
    fields = dict(**base, key=key, selections={"product": product["id"], "audience": audience["id"]})
    first = post(api, ui + "/briefs", owner, **fields)
    assert first == post(api, ui + "/briefs", owner, **fields) == read(api, ui + "/commands/" + key, owner)
    assert first["selections"]["product"]["digest"] == product["digest"]
    icp = first["selections"]["audience"]
    assert (icp["label"], icp["basis"], icp["saved_state"]) == ("Project planners", "hypothesis", "draft")
    assert "description" not in icp and "source" not in icp
    assert first["state"] == "internal_draft"
    accepted(
        call(
            api,
            owner,
            path,
            "/revisions/" + product["id"] + "/events",
            expected_sequence=1,
            expected_digest=product["digest"],
            state="withdrawn",
            reason="Retired SKU",
        )
    )
    old = read(api, ui + "/briefs/" + first["id"], owner)["selections"]["product"]
    assert (old["label"], old["digest"], old["saved_state"], old["current_state"]) == ("Blue tile", product["digest"], "approved", "withdrawn")
    post(api, ui + "/briefs", owner, **base, selections={"product": product["id"]}, status=422)
    assert "selections" not in post(api, ui + "/briefs", owner, **base)
