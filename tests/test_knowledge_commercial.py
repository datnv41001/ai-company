from copy import deepcopy

from agency_fixtures import account, create
from knowledge_fixtures import accepted, bundle, call, revision, scope


def draft(api, user, path, subject, kind, data):
    return call(api, user, path, "/revisions", subject=subject, kind=kind, data=data, visibility="public", expected_revision=0)


def approve(api, user, path, r):
    return call(api, user, path, f"/revisions/{r['id']}/events", state="approved", expected_digest=r["digest"], expected_sequence=0, reason="Reviewed")


def test_prices_quantity_conditions_and_multiple_skus(api):
    user = account(api, "PriceEditor")
    path = scope(api, user, "Price fixtures")

    def write(name, kind, data):
        return revision(api, user, path, name, kind, data)

    product = write("product", "product", {"name": "Tile", "sku": "T"})
    market = write("market", "market", {"name": "VN retail", "locales": ["vi-VN", "en"]})
    a, b = [write(x, "variant", {"product": product["id"], "name": x, "sku": x}) for x in ("A", "B")]
    place = dict(product=product["id"], variant=a["id"], market=market["id"], locale="vi-VN", region="HN", channel="store")
    policy = write("standard", "policy", {"placement": place, "payment": "Prepaid", "warranty": "12 months"})
    base_price = dict(
        amount_minor=1800, currency="USD", unit="box", basis_quantity="1", moq="2", tier_min="2", tier_max="20", tax="included", conditions=["Prepaid"]
    )
    offer = write("offer", "offer", {"placement": place, "price": base_price, "policy": policy["id"]})
    statement = dict(
        placement=place, category="price", wording="USD 18.00 / 1 box (tax included)", qualifiers=["Prepaid"], offer=offer["id"], price=base_price, quantity="5"
    )
    bcase = dict(placement=place | {"variant": b["id"]}, category="description", wording="Rounded", qualifiers=[])

    def located(locator, rule):
        return dict(locator=locator, excerpt=rule["wording"], assertion=rule)

    def source(name, entries):
        return write(name, "source", dict(publisher="Synthetic supplier", document="Synthetic schedule", valid_until="2099-01-01T00:00:00Z", entries=entries))

    sheet = source("sheet", [located("A at 5 boxes", statement), located("B description", bcase)])
    exact = dict(source=sheet["id"], locator="A at 5 boxes", assertion=statement)
    bound = write("bound", "binding", exact)
    claim = write("price-copy", "claim", {"binding": bound["id"], "assertion": statement})
    other = write("b-binding", "binding", dict(source=sheet["id"], locator="B description", assertion=bcase))
    assert other["id"] != bound["id"]
    for key, val in (
        ("currency", "VND"),
        ("amount_minor", 18),
        ("unit", "m²"),
        ("basis_quantity", "2"),
        ("moq", "5"),
        ("tax", "excluded"),
        ("conditions", []),
        ("tier_max", "9"),
    ):
        changed = deepcopy(statement)
        changed["price"][key] = val
        assert draft(api, user, path, "wrong-" + key, "claim", {"binding": bound["id"], "assertion": changed}).status_code == 422
    for mutation in ({"locale": "en"}, {"channel": "web"}, {"region": "HCM"}, {"variant": b["id"]}):
        bad = statement | {"placement": place | mutation}
        assert draft(api, user, path, "bad-placement", "binding", exact | {"assertion": bad}).status_code == 422
    bad = statement | {"qualifiers": []}
    assert draft(api, user, path, "missing-qualifier", "claim", {"binding": bound["id"], "assertion": bad}).status_code == 422
    # Even matching source/claim commercial fields must be reconciled against the exact live offer.
    for name, bad in (
        ("below-moq", statement | {"quantity": "1"}),
        ("wrong-text", statement | {"wording": "USD 18 per piece"}),
        ("wrong-value", statement | {"price": base_price | {"amount_minor": 23456}}),
    ):
        src = source("sheet-" + name, [located(name, bad)])
        candidate = accepted(draft(api, user, path, name, "binding", dict(source=src["id"], locator=name, assertion=bad)))
        assert approve(api, user, path, candidate).status_code == 409
    preview = accepted(call(api, user, path, "/previews", claims=[claim["id"]]))
    assert "18.00" in preview["canonical"] and "Synthetic supplier" not in preview["canonical"]
    # Same SKU also offers VND per square metre and another quantity tier. They have separate selectors.
    vnd = base_price | dict(currency="VND", unit="m²", amount_minor=25000)
    sqm = write("square-meter", "offer", dict(placement=place, price=vnd, policy=policy["id"]))
    price_vn = statement | dict(offer=sqm["id"], price=vnd, wording="VND 25000 / 1 m² (tax included)")
    vsource = source("sheet-vn", [located("m²", price_vn)])
    vb = write("binding-vn", "binding", dict(source=vsource["id"], locator="m²", assertion=price_vn))
    write("price-vn", "claim", dict(binding=vb["id"], assertion=price_vn))
    write("large-order", "offer", dict(placement=place, price=base_price | {"tier_min": "21", "tier_max": None}, policy=policy["id"]))
    assert call(api, user, path, "/previews", claims=[claim["id"]]).status_code == 201
    write("overlap", "offer", dict(placement=place, price=base_price | {"amount_minor": 1200, "basis_quantity": "1.00"}, policy=policy["id"]))
    assert call(api, user, path, "/previews", claims=[claim["id"]]).status_code == 409
    assert call(api, user, path, "/authorize", operation="queue", snapshot_id=preview["id"], digest=preview["digest"]).status_code == 409


def test_cross_scope_binding_and_snapshot_history(api):
    owner, path, src, claim, preview = bundle(api)
    other_tenant = account(api, "SecondKnowledge")
    other_path = scope(api, other_tenant, "Other tenant")
    client_path = scope(api, owner, "Client B")
    client_id = path.split("/")[5]
    second_brand = create(api, f"/api/tenants/{owner['tenant']}/brands", owner, {"client_id": client_id, "name": "Other brand"})
    brand_path = path.replace(path.split("/")[7], second_brand["id"])
    raw = api.get(path + "/revisions/" + claim["id"], headers=owner["headers"]).json()["data"]
    for actor, outside in ((owner, client_path), (owner, brand_path), (other_tenant, other_path)):
        assert draft(api, actor, outside, "no-cross", "claim", raw).status_code == 404
        assert api.get(outside + "/revisions/" + src["id"], headers=actor["headers"]).status_code == 404
        assert api.get(outside + "/snapshots/" + preview["id"], headers=actor["headers"]).status_code == 404
    original = preview["canonical"]
    accepted(
        call(
            api,
            owner,
            path,
            f"/revisions/{src['id']}/events",
            state="disputed",
            expected_digest=src["digest"],
            expected_sequence=1,
            reason="Issuer disputes statement",
        )
    )
    read = api.get(path + "/snapshots/" + preview["id"], headers=owner["headers"]).json()
    assert read["canonical"] == original and read["digest"] == preview["digest"] and read["current_authority_issue"]
    assert call(api, owner, path, "/authorize", operation="queue", snapshot_id=preview["id"], digest=preview["digest"]).status_code == 409


def test_approval_supersession_and_solo_sensitive_source(api):
    user, path, src, claim, _ = bundle(api)
    src_data = api.get(path + "/revisions/" + src["id"], headers=user["headers"]).json()["data"]
    new_source = accepted(call(api, user, path, "/revisions", kind="source", subject=src["subject"], expected_revision=1, visibility="public", data=src_data))
    assert approve(api, user, path, new_source).status_code == 200
    prior = api.get(path + "/revisions/" + src["id"], headers=user["headers"]).json()
    assert prior["data"] == src_data and prior["state"] == "superseded"
    assert call(api, user, path, "/previews", claims=[claim["id"]]).status_code == 409
    stmt = src_data["entries"][0]["assertion"] | {"category": "performance", "wording": "Higher tested wear resistance"}
    src_data["entries"][0].update(assertion=stmt, excerpt=stmt["wording"])
    src2 = revision(api, user, path, "performance-tests", "source", src_data)
    binding = revision(api, user, path, "performance-entry", "binding", dict(source=src2["id"], locator="row 2", assertion=stmt))
    sensitive = accepted(draft(api, user, path, "sensitive", "claim", dict(binding=binding["id"], assertion=stmt)))
    assert approve(api, user, path, sensitive).status_code == 409
    assert api.get(path + "/revisions/" + sensitive["id"], headers=user["headers"]).json()["state"] == "draft"


def test_bounded_profile_intelligence_entities(api):
    owner, path, src, _, _ = bundle(api)

    def write(name, kind, data):
        return revision(api, owner, path, name, kind, data)

    write("quick", "profile", dict(name="Tile business", sells="Ceramics", audience="Installers", goal="Qualified enquiries"))
    write("installation", "service", dict(name="Tile installation"))
    write("icp", "icp", dict(name="Installers", description="Trade buyers", basis="hypothesis"))
    write("audience", "segment", dict(name="Trade teams", description="Synthetic observed segment", basis="fact", source=src["id"]))
    top = write("goal", "objective", dict(name="Growth", level="company", owner="Commercial team"))
    brand = write("brand-goal", "objective", dict(name="Enquiries", level="brand", owner="Brand operator", parent=top["id"]))
    write(
        "lead-kpi",
        "kpi",
        dict(
            objective=brand["id"],
            name="Qualified leads",
            unit="leads",
            method="Synthetic lead qualification count",
            window="30 days",
            source=src["id"],
            owner="Brand operator",
        ),
    )
    assert draft(api, owner, path, "wrong-goal", "objective", dict(name="Bad", level="brand", parent=brand["id"], owner="X")).status_code == 422
    write("tone", "guidelines", dict(guidance="Clarity and supportable factual statements"))
    assert draft(api, owner, path, "group", "segment", dict(name="Group", description="Audience", basis="fact")).status_code == 422
