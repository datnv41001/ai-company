"""Commercial placements are compared semantically while evidence keeps its original spelling."""

import pytest

from knowledge_fixtures import accepted, call
from test_knowledge_commerce_conditions import fixture
from test_knowledge_conflicting_authority import declaration, supported_claim


@pytest.mark.parametrize("aliases", [("HN", "Hà Nội", "VN-HN"), ("HCM", "TP.HCM", "VN-SG"), ("Đà Nẵng", "VN-DN")])
def test_territory_aliases_conflict_and_audited_preference_preserves_original(api, aliases):
    owner, path, placement = fixture(api)
    primary_place = placement | {"region": aliases[0]}
    primary = declaration(api, owner, path, "availability", "chosen", "available", primary_place)
    claim = supported_claim(api, owner, path, "availability", "chosen-stock", "available", primary_place, primary)
    snapshot = accepted(call(api, owner, path, "/previews", claims=[claim["id"]]))
    for index, alias in enumerate(aliases[1:]):
        rival = declaration(api, owner, path, "availability", f"other-{index}", "unavailable", placement | {"region": alias}, visibility="restricted")
        blocked = call(api, owner, path, "/authorize", operation="queue", snapshot_id=snapshot["id"], digest=snapshot["digest"])
        assert blocked.status_code == 409 and blocked.json()["detail"] == "Commercial authority disputed"
        accepted(
            call(
                api,
                owner,
                path,
                f"/revisions/{rival['id']}/events",
                state="superseded",
                preferred_revision=primary["id"],
                expected_digest=rival["digest"],
                expected_sequence=1,
                reason="Checked stock for this territory",
            )
        )
        historical = api.get(path + "/revisions/" + rival["id"], headers=owner["headers"]).json()
        assert historical["digest"] == rival["digest"] and historical["data"]["placement"]["region"] == alias
        assert call(api, owner, path, "/previews", claims=[claim["id"]]).status_code == 201
    archived = api.get(path + "/snapshots/" + snapshot["id"], headers=owner["headers"]).json()
    assert archived["canonical"] == snapshot["canonical"] and archived["digest"] == snapshot["digest"]


@pytest.mark.parametrize(
    "primary_option,exclusive,intersecting", [("retail", "wholesale", "prepaid"), ("prepaid", "credit", "extended"), ("standard", "extended", "wholesale")]
)
def test_distinct_option_dimensions_overlap_but_same_dimension_alternatives_coexist(api, primary_option, exclusive, intersecting):
    owner, path, placement = fixture(api)
    option = {"option": primary_option}
    primary = declaration(api, owner, path, "warranty", "chosen-policy", "12 months", placement, applicability=option)
    claim = supported_claim(api, owner, path, "warranty", "warranty", "12 months", placement, primary, option)
    declaration(api, owner, path, "warranty", "other-tier", "24 months", placement, applicability={"option": exclusive})
    assert call(api, owner, path, "/previews", claims=[claim["id"]]).status_code == 201
    declaration(api, owner, path, "warranty", "other-dimension", "24 months", placement, applicability={"option": intersecting})
    blocked = call(api, owner, path, "/previews", claims=[claim["id"]])
    assert blocked.status_code == 409 and blocked.json()["detail"] == "Commercial authority disputed"
