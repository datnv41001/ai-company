"""Exercise the public wording through its actual source, exact binding and decision."""

from agency_fixtures import account
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, bundle, call, revision


def test_whole_projection_approval(api):
    owner, path, source, _, _ = bundle(api)
    sample = api.get(path + "/revisions/" + source["id"], headers=owner["headers"]).json()
    placement = sample["data"]["entries"][0]["assertion"]["placement"]
    expert = account(api, "ProjectionReview")
    invite_member(api, "/api/tenants/" + owner["tenant"], owner["headers"], expert["headers"], email=expert["email"], role="admin")

    def write(subject, kind, data, **options):
        return revision(api, owner, path, subject, kind, data, **options)

    mandate = write(
        "uncategorized-mandate",
        "qualification",
        dict(approver_id=expert["id"], category="unclassified", basis="Synthetic approval of unclassified wording", valid_until="2099-01-01T00:00:00Z"),
        visibility="restricted",
    )
    stock = write(
        "stock", "availability", dict(placement=placement, status="available", observed_at="2025-01-01T00:00:00Z", valid_until="2099-01-01T00:00:00Z")
    )
    promise = "Guaranteed performance under all operating conditions"
    policy = write("terms", "policy", dict(placement=placement, warranty=promise, payment="Every purchase generates a return"))
    price = dict(
        amount_minor=250000, currency="VND", unit="m²", basis_quantity="1", moq="5", tier_min="5", tier_max=None, tax="included", conditions=["Prepaid"]
    )
    offer = write("wholesale", "offer", dict(placement=placement, price=price, policy=policy["id"]))
    statement = dict(
        placement=placement, category="price", wording="VND 250000 / 1 m² (tax included)", qualifiers=["Prepaid"], offer=offer["id"], price=price, quantity="5"
    )

    def claim(name, assertion):
        evidence = write(
            name + "-source",
            "source",
            dict(
                publisher="Synthetic office",
                document="Trade bulletin",
                valid_until="2099-01-01T00:00:00Z",
                entries=[dict(locator="row", excerpt=assertion["wording"], assertion=assertion)],
            ),
        )
        link = write(name + "-binding", "binding", dict(source=evidence["id"], locator="row", assertion=assertion))
        return write(name, "claim", dict(binding=link["id"], assertion=assertion), approve=False)

    def approve(actor, row, **options):
        return call(
            api,
            actor,
            path,
            f"/revisions/{row['id']}/events",
            expected_digest=row["digest"],
            expected_sequence=0,
            state="approved",
            reason="Checked complete synthetic projection",
            **options,
        )

    routine = claim("solo-quote", statement)
    assert approve(owner, routine).status_code == 200
    dollar_terms = price | {"currency": "USD", "amount_minor": 1900, "conditions": [promise]}
    dollar_offer = write("usd-contract", "offer", dict(placement=placement, price=dollar_terms, policy=policy["id"]))
    approved_claims = []
    for name, assertion in (
        ("extra-quote", statement | {"qualifiers": ["Prepaid", promise]}),
        (
            "offer-condition",
            statement | {"wording": "USD 19.00 / 1 m² (tax included)", "qualifiers": [promise], "offer": dollar_offer["id"], "price": dollar_terms},
        ),
        ("stock-copy", dict(placement=placement, category="availability", wording="available", qualifiers=[promise], availability=stock["id"])),
        ("warranty-copy", dict(placement=placement, category="warranty", wording=promise, qualifiers=[], policy=policy["id"])),
        ("payment-copy", dict(placement=placement, category="payment", wording="Every purchase generates a return", qualifiers=[], policy=policy["id"])),
        ("mislabelled", dict(placement=placement, category="description", wording=promise, qualifiers=[])),
        ("untyped-channel", dict(placement=placement | {"channel": promise}, category="description", wording="Rounded", qualifiers=[])),
    ):
        draft = claim(name, assertion)
        own_status = approve(owner, draft).status_code
        assert own_status == 409, name
        qualified_status = approve(expert, draft, qualification_revision=mandate["id"]).status_code
        assert qualified_status == 200, name
        approved_claims.append(draft["id"])
    preview = accepted(call(api, expert, path, "/previews", claims=approved_claims))
    assert promise in preview["canonical"]
    accepted(
        call(
            api,
            owner,
            path,
            f"/revisions/{mandate['id']}/events",
            expected_digest=mandate["digest"],
            expected_sequence=1,
            state="withdrawn",
            reason="Appointment withdrawn",
        )
    )
    assert call(api, expert, path, "/authorize", operation="queue", snapshot_id=preview["id"], digest=preview["digest"]).status_code == 409
    assert call(api, owner, path, "/previews", claims=[routine["id"]]).status_code == 201
