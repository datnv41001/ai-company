from uuid import uuid4

from agency_fixtures import account
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, call, revision
from test_business_workspace import workspace
from test_knowledge_commerce_conditions import fixture
from test_knowledge_conflicting_authority import declaration, supported_claim


def paths(api, owner):
    _, (path,) = workspace(api, owner, "Catalog", 1)
    prefix = path.rsplit("/", 1)[0]
    return prefix + "/catalog", prefix + "/knowledge"


def save(api, owner, root, kind, data, **opts):
    body = {"key": uuid4().hex, "expected_revision": 0, "visibility": "internal", "data": data, "kind": kind, **opts}
    return api.post(root + "/items", headers=owner["headers"], json=body)


def approve(api, user, path, row):
    return call(
        api,
        user,
        path,
        "/revisions/" + row["id"] + "/events",
        state="approved",
        expected_digest=row["digest"],
        expected_sequence=0,
        reason="Checked synthetic documents",
    )


def test_registered_master_search_and_forbidden_duplicate(api):
    owner = account(api, "CatalogOwner")
    root, knowledge = paths(api, owner)
    editor = account(api, "CatalogEditor")
    invite_member(api, "/api/tenants/" + owner["tenant"], owner["headers"], editor["headers"], email=editor["email"], role="editor")
    plant = accepted(save(api, owner, root, "product", {"name": "Tile series"}, code="TILE.1", visibility="public"))
    accepted(approve(api, owner, knowledge, plant))
    secret = accepted(save(api, owner, root, "service", {"name": "Private service"}, code="PRIVATE", visibility="restricted"))
    duplicate = save(api, editor, root, "product", {"name": "Duplicate"}, code="PRIVATE")
    assert duplicate.status_code == 409 and secret["id"] not in duplicate.text
    source = revision(
        api,
        owner,
        knowledge,
        "private-sheet",
        "source",
        dict(publisher="Hidden publisher", document="Hidden source name", entries=[], valid_until="2099-01-01T00:00:00Z"),
        visibility="restricted",
        approve=False,
    )
    seg = accepted(
        save(api, owner, root, "segment", {"name": "Installers", "description": "Working hypothesis", "basis": "hypothesis", "source": source["id"]})
    )
    detail = api.get(root + "/items/" + seg["id"], headers=editor["headers"])
    assert detail.status_code == 200 and detail.json()["references"]["source"] == {"status": "restricted"}
    assert source["id"] not in detail.text and "Hidden source" not in detail.text
    duplicate = call(
        api,
        editor,
        knowledge,
        "/revisions",
        subject="external-key",
        kind="variant",
        expected_revision=0,
        visibility="public",
        data={"name": "Alias", "product": plant["id"], "sku": "private"},
    )
    assert duplicate.status_code == 409
    revision(api, owner, knowledge, "legacy-market", "market", {"name": "Hanoi retail", "locales": ["vi-VN"]}, visibility="restricted")
    assert save(api, editor, root, "market", {"name": "Hanoi retail", "locales": ["vi-VN"]}, code="VN-RETAIL").status_code == 409
    assert accepted(save(api, owner, root, "product", {"name": "Tile B"}, code="TILE.2"))
    page = api.get(root + "/items", headers=editor["headers"], params={"kind": "product", "q": "tile", "limit": 1}).json()
    following = api.get(root + "/items", headers=editor["headers"], params={"kind": "product", "q": "tile", "limit": 1, "after": page["next"]}).json()
    assert [page["items"][0]["code"], following["items"][0]["code"]] == ["TILE.1", "TILE.2"] and following["next"] is None
    updated = accepted(save(api, owner, root, "product", {"name": "Porcelain"}, code="TILE.1", visibility="public", expected_revision=1))
    assert updated["revision"] == 2
    assert not api.get(root + "/items", headers=editor["headers"], params={"kind": "product", "q": "series"}).json()["items"]
    assert not api.get(root + "/items", headers=editor["headers"], params={"kind": "service"}).json()["items"]
    _, other_brand = paths(api, owner)
    assert api.get(other_brand.replace("/knowledge", "/catalog") + "/items/" + plant["id"], headers=owner["headers"]).status_code == 404


def test_exact_money_territory_audience_and_kpi_workflow(api):
    owner = account(api, "CatalogWorkflow")
    cat, k = paths(api, owner)

    def add(kind, data, **kw):
        row = accepted(save(api, owner, cat, kind, data, **kw))
        accepted(approve(api, owner, k, row))
        return row

    p = add("product", {"name": "Tile"}, code="TILE")
    m = add("market", {"name": "First region", "locales": ["vi-VN"]}, code="VN-RETAIL")
    v = add("variant", {"name": "White", "product": p["id"]}, code="WHITE")
    placement = dict(product=p["id"], variant=v["id"], market=m["id"], region="VN-HN", channel="web", locale="vi-VN")
    pol = add("policy", dict(placement=placement, payment="Prepaid", warranty="12 months", shipping="Warehouse pickup"))
    price = dict(amount="12.34", currency="USD", unit="m²", basis_quantity="1", moq="2", tier_min="2", tier_max="20", tax="included", condition_ids=["prepaid"])
    data = {"placement": placement, "price": price, "policy": pol["id"]}
    offer = add("offer", data)
    full = api.get(cat + "/items/" + offer["id"], headers=owner["headers"]).json()
    assert full["data"]["price"]["amount"] == "12.34" and full["references"]["variant"]["label"] == "White"
    raw = api.get(k + "/revisions/" + offer["id"], headers=owner["headers"]).json()["data"]["price"]
    assert raw["amount_minor"] == 1234 and raw["conditions"] == ["Prepaid"]
    for curr, amount in [("JPY", "1.5"), ("VND", "2.01"), ("USD", "9.999")]:
        assert save(api, owner, cat, "offer", data | {"price": price | {"amount": amount, "currency": curr}}).status_code == 422
    hero = add("guidelines", {"guidance": "Use measured evidence", "tone": "Plain and calm"})
    assert api.get(cat + "/items/" + hero["id"], headers=owner["headers"]).json()["data"]["tone"] == "Plain and calm"
    icp = add("icp", {"name": "Installers", "description": "Local professionals", "basis": "hypothesis", "needs": "Fast supply", "market": m["id"]})
    assert api.get(cat + "/items/" + icp["id"], headers=owner["headers"]).json()["evidence_state"] == "missing"
    assert save(api, owner, cat, "icp", {"name": "Buyers", "description": "Asserted", "basis": "fact"}).status_code == 422
    goal = add("objective", {"name": "Monthly inquiries", "owner": "Marketing lead", "level": "company"})
    kpi = accepted(
        save(
            api,
            owner,
            cat,
            "kpi",
            {
                "name": "Inquiries",
                "unit": "count",
                "objective": goal["id"],
                "owner": "Analyst",
                "window": "30 days",
                "method": "CRM entries",
                "baseline": "0",
                "target": "15",
            },
        )
    )
    assert approve(api, owner, k, kpi).status_code == 409
    detail = api.get(cat + "/items/" + kpi["id"], headers=owner["headers"]).json()
    assert detail["missing_fields"] == ["source", "actual"] and detail["data"]["baseline"] == "0"


def test_multi_axis_overlap_preserves_legacy_sources(api):
    owner, k, p = fixture(api)
    primary = declaration(api, owner, k, "warranty", "base", "12 months", p, applicability={"option": "retail", "payment_type": "prepaid"})
    claim = supported_claim(api, owner, k, "warranty", "claim", "12 months", p, primary, {"buyer": "retail", "payment_type": "prepaid"})
    declaration(api, owner, k, "warranty", "credit", "24 months", p, applicability={"buyer": "retail", "payment_type": "credit"})
    assert call(api, owner, k, "/previews", claims=[claim["id"]]).status_code == 201
    declaration(api, owner, k, "warranty", "extended", "24 months", p, applicability={"service_level": "extended", "payment_type": "prepaid"})
    assert call(api, owner, k, "/previews", claims=[claim["id"]]).status_code == 409
