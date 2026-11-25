"""C1 integration, on both developer SQLite and the actual restricted Postgres API."""

from uuid import uuid4

from agency_fixtures import account
from knowledge_fixtures import call, scope


def test_scope_and_idempotent_revision(api):
    owner = account(api, "KnowledgeEditor")
    outsider = account(api, "OtherTenant")
    path = scope(api, owner, "C1 synthetic")
    data = dict(key=uuid4().hex, subject="widget", kind="product", expected_revision=0, visibility="public", data={"name": "Test tile", "sku": "T-8"})
    assert call(api, outsider, path, "/revisions", **data).status_code == 404
    created = call(api, owner, path, "/revisions", **data)
    assert created.status_code == 201, created.text
    assert call(api, owner, path, "/revisions", **data).json() == created.json()
    assert call(api, owner, path, "/revisions", **(data | {"data": {"name": "Other", "sku": "S"}})).status_code == 409
    assert call(api, owner, path, "/revisions", **(data | {"key": uuid4().hex})).status_code == 409
    other_brand = scope(api, owner, "C1 other client")
    assert api.get(other_brand + "/revisions/" + created.json()["id"], headers=owner["headers"]).status_code == 404
