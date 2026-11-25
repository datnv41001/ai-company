"""Exercise the explicit legacy import through a normal tenant-scoped API session."""
from uuid import uuid4

from agency_fixtures import account, create


def test_legacy_brand_text_imports_as_draft_and_preserves_original(api):
    owner = account(api, "LegacyBrandOwner")
    outsider = account(api, "UnrelatedOwner")
    base = f"/api/tenants/{owner['tenant']}"
    client = create(api, base + "/clients", owner, {"name": "Legacy client"})
    legacy = {"client_id": client["id"], "name": "Legacy catalogue",
              "brand_guidelines": "Synthetic editorial rule, pending evidence.",
              "product_truth": "Synthetic unreviewed product description."}
    brand = create(api, base + "/brands", owner, legacy)
    command = base + f"/clients/{client['id']}/brands/{brand['id']}/knowledge/import-legacy"
    request = {"key": uuid4().hex}
    assert api.post(command, headers=outsider["headers"], json=request).status_code == 404
    response = api.post(command, headers=owner["headers"], json=request)
    assert response.is_success, response.text
    revisions = response.json()["revisions"]
    assert len(revisions) == 2
    assert len({r["id"] for r in revisions}) == 2
    assert all(r["state"] == "draft" and r["revision"] == 1 and len(r["digest"]) == 64 for r in revisions)
    replay = api.post(command, headers=owner["headers"], json=request)
    assert replay.is_success and replay.json() == response.json()
    retained = next(b for b in api.get(base + "/brands", headers=owner["headers"]).json() if b["id"] == brand["id"])
    assert {key: retained[key] for key in legacy} == legacy


def test_empty_legacy_brand_produces_no_fact(api):
    owner = account(api, "EmptyLegacyOwner")
    base = f"/api/tenants/{owner['tenant']}"
    client = create(api, base + "/clients", owner, {"name": "Empty client"})
    brand = create(api, base + "/brands", owner, {"client_id":client["id"],"name":"Empty brand"})
    path = base + f"/clients/{client['id']}/brands/{brand['id']}/knowledge/import-legacy"
    response = api.post(path, headers=owner["headers"], json={"key": uuid4().hex})
    assert response.is_success and response.json()["revisions"] == []
