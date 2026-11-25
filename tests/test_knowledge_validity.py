"""Wall-clock expiry tests on an isolated PostgreSQL database with an authenticated real API."""

from datetime import datetime, timedelta, timezone
import time

import pytest

from knowledge_fixtures import accepted, bundle, call, revision


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_expiry_during_preview_uses_current_db_clock_and_preserves_bytes(api):
    user, path, src, _, _ = bundle(api)
    source = api.get(path + "/revisions/" + src["id"], headers=user["headers"]).json()["data"]
    until = datetime.now(timezone.utc) + timedelta(seconds=10)
    source["valid_until"] = until.isoformat()
    source = revision(api, user, path, "short-source", "source", source)
    source_data = api.get(path + "/revisions/" + source["id"], headers=user["headers"]).json()["data"]
    statement = source_data["entries"][0]["assertion"]
    bound = revision(api, user, path, "short-bound", "binding", dict(source=source["id"], locator="row 2", assertion=statement))
    claim = revision(api, user, path, "short-copy", "claim", dict(binding=bound["id"], assertion=statement))
    fresh = accepted(call(api, user, path, "/previews", claims=[claim["id"]], ttl_seconds=120))
    terms = dict(operation="queue", snapshot_id=fresh["id"], digest=fresh["digest"])
    receipt = accepted(call(api, user, path, "/authorize", **terms))
    assert datetime.fromisoformat(receipt["effective_at"]) <= datetime.fromisoformat(receipt["queued_at"]) < until
    time.sleep(max(0, (until - datetime.now(timezone.utc)).total_seconds()) + 0.05)
    assert call(api, user, path, "/authorize", **terms).status_code == 409
    assert api.get(path + "/revisions/" + source["id"], headers=user["headers"]).json()["state"] == "expired"
    historical = api.get(path + "/snapshots/" + fresh["id"], headers=user["headers"]).json()
    assert historical["digest"] == fresh["digest"] and historical["canonical"] == fresh["canonical"] and historical["current_authority_issue"]
    assert api.get(path + "/receipts/" + receipt["id"], headers=user["headers"]).json() == receipt
    hits = api.get(path + "/revisions/" + source["id"] + "/impact", headers=user["headers"]).json()["snapshots"]
    assert {"id": fresh["id"], "digest": fresh["digest"]} in hits


def test_exact_product_and_availability(api):
    user, path, src, _, _ = bundle(api)
    statement = api.get(path + "/revisions/" + src["id"], headers=user["headers"]).json()["data"]["entries"][0]["assertion"]
    p = statement["placement"]
    other = revision(api, user, path, "different-product", "product", dict(name="Other tile", sku="T-2"))
    v = revision(api, user, path, "variant-a", "variant", dict(product=p["product"], name="Matte", sku="T-A"))
    wrong = p | dict(variant=v["id"], product=other["id"])
    assert (
        call(
            api,
            user,
            path,
            "/revisions",
            subject="bad-stock",
            kind="availability",
            expected_revision=0,
            visibility="public",
            data=dict(placement=wrong, status="available", observed_at="2025-01-01T00:00:00Z", valid_until="2099-01-01T00:00:00Z"),
        ).status_code
        == 422
    )
    observation = revision(
        api,
        user,
        path,
        "unknown-stock",
        "availability",
        dict(placement=p, status="unknown", observed_at="2025-01-01T00:00:00Z", valid_until="2099-01-01T00:00:00Z"),
    )
    rule = statement | dict(category="availability", wording="available", availability=observation["id"])
    source = revision(
        api,
        user,
        path,
        "stock-source",
        "source",
        dict(
            publisher="Synthetic",
            document="Stock check",
            valid_until="2099-01-01T00:00:00Z",
            entries=[dict(locator="row 5", excerpt="Unknown", assertion=rule)],
        ),
    )
    bound = revision(api, user, path, "stock-bind", "binding", dict(source=source["id"], locator="row 5", assertion=rule), approve=False)
    assert (
        call(
            api,
            user,
            path,
            f"/revisions/{bound['id']}/events",
            expected_sequence=0,
            expected_digest=bound["digest"],
            state="approved",
            reason="Check availability",
        ).status_code
        == 409
    )
