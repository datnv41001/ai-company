from datetime import datetime, timedelta, timezone
import time

from knowledge_fixtures import accepted, bundle, call, revision
from test_knowledge_conflicting_authority import declaration, supported_claim


def fixture(api):
    owner, path, source, _, _ = bundle(api)
    data = api.get(path + "/revisions/" + source["id"], headers=owner["headers"]).json()["data"]
    return owner, path, data["entries"][0]["assertion"]["placement"]


def test_conditions_public_scope_and_audited_source_preference(api):
    owner, path, p = fixture(api)
    band = dict(option="retail", unit="box", minimum="2", maximum="10")

    def fact(name, value, placement=p, **kw):
        return declaration(api, owner, path, "availability", name, value, placement, **kw)

    yes = fact("stock-sheet", "available", applicability=band)
    claim = supported_claim(api, owner, path, "availability", "stock", "available", p, yes, band)

    def preview():
        return call(api, owner, path, "/previews", claims=[claim["id"]])

    # Compatible coexisting claims, different order bands, places, markets and channels.
    fact("same-fact", "available", applicability=band)
    fact("larger", "unavailable", applicability=band | {"minimum": "11", "maximum": None})
    fact("other-option", "unavailable", applicability=band | {"option": "wholesale"})
    fact("other-unit", "unavailable", applicability=band | {"unit": "piece"})
    fact("other-region", "unavailable", p | {"region": "HCM"}, applicability=band)
    fact("other-channel", "unavailable", p | {"channel": "retail"}, applicability=band)
    other = revision(api, owner, path, "other-market", "market", {"name": "Other sales area", "locales": ["vi-VN"]})
    fact("other-market-stock", "unavailable", p | {"market": other["id"]}, applicability=band)
    snap = accepted(preview())
    assert '"applicability":' in snap["canonical"] and '"minimum":"2"' in snap["canonical"]
    # An unrestricted declaration covers every selected band.
    wildcard = fact("wildcard", "unavailable")
    assert preview().status_code == 409
    accepted(
        call(
            api,
            owner,
            path,
            "/revisions/" + wildcard["id"] + "/events",
            state="withdrawn",
            reason="Broad observation withdrawn",
            expected_digest=wildcard["digest"],
            expected_sequence=1,
        )
    )
    boundary = fact("touching", "unavailable", applicability=band | {"minimum": "10", "maximum": "18"})
    assert preview().status_code == 409
    accepted(
        call(
            api,
            owner,
            path,
            "/revisions/" + boundary["id"] + "/events",
            state="withdrawn",
            reason="Correction",
            expected_digest=boundary["digest"],
            expected_sequence=1,
        )
    )
    conflicting = fact("local-sheet", "unavailable", applicability=band)
    conflict = preview()
    assert conflict.status_code == 409 and conflict.json()["detail"] == "Commercial authority disputed"
    accepted(
        call(
            api,
            owner,
            path,
            "/revisions/" + conflicting["id"] + "/events",
            state="disputed",
            reason="Conflicting sources under review",
            expected_digest=conflicting["digest"],
            expected_sequence=1,
        )
    )
    assert preview().status_code == 409
    prefer = dict(state="superseded", reason="Owner verified stock-sheet for this exact range", expected_digest=conflicting["digest"], expected_sequence=2)
    assert call(api, owner, path, "/revisions/" + conflicting["id"] + "/events", preferred_revision=wildcard["id"], **prefer).status_code == 409
    accepted(call(api, owner, path, "/revisions/" + conflicting["id"] + "/events", preferred_revision=yes["id"], **prefer))
    events = api.get(path + "/revisions/" + conflicting["id"] + "/events", headers=owner["headers"]).json()
    assert events[-1]["preferred_revision"] == yes["id"] and events[-1]["reason"] == prefer["reason"]
    assert preview().status_code == 201


def test_stale_observation_stops_competing_at_its_end_instant(api):
    owner, path, p = fixture(api)
    chosen = declaration(api, owner, path, "availability", "inventory", "available", p)
    claim = supported_claim(api, owner, path, "availability", "catalogue", "available", p, chosen)
    # A later observation has no automatic priority over another unexpired source.
    until = datetime.now(timezone.utc) + timedelta(seconds=4)
    declaration(
        api, owner, path, "availability", "temporary", "unavailable", p, observed_at=(until - timedelta(minutes=1)).isoformat(), valid_until=until.isoformat()
    )
    assert call(api, owner, path, "/previews", claims=[claim["id"]]).status_code == 409
    time.sleep(max(0, (until - datetime.now(timezone.utc)).total_seconds()) + 0.05)
    assert call(api, owner, path, "/previews", claims=[claim["id"]]).status_code == 201


def test_equivalent_warranty_and_qualified_alternative_terms(api):
    owner, path, p = fixture(api)
    standard = dict(option="standard")
    base = declaration(api, owner, path, "warranty", "default", "18 months", p, applicability=standard)
    claim = supported_claim(api, owner, path, "warranty", "default-warranty", "18 months", p, base, standard)
    declaration(api, owner, path, "warranty", "dieu-khoan", "18 tháng", p, applicability=standard)
    declaration(api, owner, path, "warranty", "extended", "36 months", p, applicability=dict(option="extended"))
    assert call(api, owner, path, "/previews", claims=[claim["id"]]).status_code == 201


def test_source_cannot_broaden_qualified_warranty_or_retire_it_in_favour_of_payment(api):
    owner, path, placement = fixture(api)
    warranty = declaration(api, owner, path, "warranty", "option-warranty", "12 months", placement, applicability={"option": "extended"})
    unqualified = dict(placement=placement, category="warranty", policy=warranty["id"], wording="12 months", qualifiers=[])
    source = revision(
        api,
        owner,
        path,
        "unqualified-source",
        "source",
        dict(
            publisher="Synthetic",
            document="Sheet",
            entries=[dict(locator="r1", excerpt="12 months", assertion=unqualified)],
            valid_until="2099-01-01T00:00:00Z",
        ),
    )
    binding = revision(api, owner, path, "unqualified-binding", "binding", dict(source=source["id"], locator="r1", assertion=unqualified), approve=False)
    approval = call(
        api,
        owner,
        path,
        f"/revisions/{binding['id']}/events",
        state="approved",
        reason="Check applicability",
        expected_digest=binding["digest"],
        expected_sequence=0,
    )
    assert approval.status_code == 409 and "exact commercial applicability" in approval.json()["detail"]
    payment = declaration(api, owner, path, "payment", "unrelated-policy", "Prepaid", placement, applicability={"option": "extended"})
    preference = call(
        api,
        owner,
        path,
        f"/revisions/{warranty['id']}/events",
        state="superseded",
        reason="Choose policy",
        expected_digest=warranty["digest"],
        expected_sequence=1,
        preferred_revision=payment["id"],
    )
    assert preference.status_code == 409 and "each term" in preference.json()["detail"]
