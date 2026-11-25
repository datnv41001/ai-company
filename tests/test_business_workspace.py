"""A company's partial profile, the origin of each field and pinned personal working drafts."""

from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from agency_fixtures import account, create
from app.access import set_context, set_worker_scope
from app.database import engine
from app.security import sign_actor
from identity_fixtures import invite_member


def workspace(api, owner, label, brands=2):
    tenant = "/api/tenants/" + owner["tenant"]
    client = create(api, tenant + "/clients", owner, {"name": label})["id"]
    base = tenant + "/clients/" + client
    paths = []
    for i in range(brands):
        brand_id = create(api, tenant + "/brands", owner, {"client_id": client, "name": f"{label} {i}"})["id"]
        paths.append(base + "/brands/" + brand_id + "/business-workspace")
    return base + "/business-profile", paths


def post(api, path, actor, status=201, **kw):
    r = api.post(path, headers=actor["headers"], json={"key": uuid4().hex, **kw})
    assert r.status_code == status, (path, r.text)
    return r.json()


def read(api, path, actor):
    r = api.get(path, headers=actor["headers"])
    assert r.status_code == 200, (path, r.text)
    return r.json()


def test_partial_inheritance_pinned_brief_and_recovery(api):
    owner = account(api, "ProfileCompany")
    common, (a, b) = workspace(api, owner, "One company")
    assert read(api, a, owner)["completion"] == {"filled": 0, "total": 4, "missing": ["name", "sells", "audience", "goal"]}
    token = uuid4().hex
    command = dict(key=token, expected_revision=0, fields={"name": "Material House", "sells": "Tiles"})
    first = post(api, common, owner, **command)
    assert read(api, common + "/commands/" + token, owner) == post(api, common, owner, **command) == first
    post(api, common, owner, status=409, **(command | {"fields": {"name": "different"}}))
    assert read(api, a, owner)["completion"]["filled"] == read(api, b, owner)["completion"]["filled"] == 2
    post(
        api,
        a + "/overrides",
        owner,
        expected_company_revision=1,
        expected_revision=0,
        fields={"name": {"mode": "override", "value": "Retail Brand"}, "sells": {"mode": "empty"}},
    )
    after = read(api, a, owner)
    assert after["fields"]["sells"]["mode"] == "empty" and after["fields"]["sells"]["value"] is None
    assert after["fields"]["name"]["value"] == "Retail Brand" and after["fields"]["name"]["source"] == "brand"
    assert read(api, b, owner)["fields"]["name"]["value"] == "Material House"
    brief_key = uuid4().hex
    brief_body = dict(key=brief_key, expected_company_revision=1, expected_revision=1, title="Internal creative brief")
    brief = post(api, a + "/briefs", owner, **brief_body)
    assert brief["missing"] == ["sells", "audience", "goal"] and brief["state"] == "internal_draft"
    post(api, common, owner, expected_revision=1, fields={"name": "Company renamed", "goal": "More enquiries"})
    assert post(api, a + "/briefs", owner, **brief_body) == read(api, a + "/commands/" + brief_key, owner) == brief
    post(api, a + "/overrides", owner, status=409, expected_company_revision=1, expected_revision=1, fields={"name": {"mode": "inherit"}})
    post(api, a + "/overrides", owner, expected_company_revision=2, expected_revision=1, fields={"name": {"mode": "inherit"}})
    fresh = read(api, a, owner)
    assert fresh["fields"]["name"] == dict(
        mode="inherit", value="Company renamed", source="company", source_revision=2, override_revision=2, company_source_revision=2
    )
    assert fresh["fields"]["sells"]["mode"] == "empty" and fresh["fields"]["sells"]["company_source_revision"] == 1
    assert len(fresh["briefs"]) == 1
    assert read(api, a + "/briefs/" + brief["id"], owner) == brief and not read(api, b, owner)["briefs"]
    assert read(api, common + "/revisions/1", owner)["fields"]["name"] == {"value": "Material House", "revision": 1}
    assert read(api, a + "/overrides/revisions/1", owner)["fields"]["name"]["value"] == "Retail Brand"
    assert api.get(b + "/overrides/revisions/1", headers=owner["headers"]).status_code == 404
    post(api, a + "/briefs", owner, status=422, expected_revision=2, expected_company_revision=2, title="Invalid", recipient_id=owner["id"])


def test_staff_roles_tenant_client_and_private_draft(api):
    owner, outsider, editor, viewer = [account(api, name) for name in ("ProfileOwner", "Elsewhere", "WorkspaceEditor", "WorkspaceReader")]
    base = "/api/tenants/" + owner["tenant"]
    c, (a,) = workspace(api, owner, "Same name", 1)
    _, (other_client,) = workspace(api, owner, "Same name", 1)
    _, (other_tenant,) = workspace(api, outsider, "Same name", 1)
    for member, role in [(editor, "editor"), (viewer, "viewer")]:
        invite_member(api, base, owner["headers"], member["headers"], email=member["email"], role=role)
    assert read(api, a, viewer)["can_edit"] is False
    post(api, c, viewer, status=404, expected_revision=0, fields={"name": "Not allowed"})
    post(api, c, editor, expected_revision=0, fields={"sells": "Rain coats"})
    assert read(api, other_client, owner)["company"]["sells"] is None
    wrong = other_client.replace(other_client.split("/")[7], a.split("/")[7])
    for path, actor in [(wrong, owner), (a, outsider), (other_tenant, owner)]:
        assert api.get(path, headers=actor["headers"]).status_code == 404
    token = uuid4().hex
    brief = post(api, a + "/briefs", editor, key=token, expected_revision=0, expected_company_revision=1, title="Working note")
    assert not read(api, a, owner)["briefs"]
    for path, actor in [(a + "/briefs/" + brief["id"], owner), (a + "/commands/" + token, owner), (other_client + "/briefs/" + brief["id"], editor)]:
        assert api.get(path, headers=actor["headers"]).status_code == 404
    client_id = a.split("/")[5]
    assert api.put(base + "/members/" + viewer["id"] + "/client-scope", headers=owner["headers"], json={"client_id": client_id}).status_code == 200
    assert api.get(a, headers=viewer["headers"]).status_code == 404
    assert api.delete(base + "/members/" + viewer["id"] + "/client-scope", headers=owner["headers"]).status_code == 204
    assert api.get(a, headers=viewer["headers"]).status_code == 404


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_native_workspace_lock_rls_and_no_operational_side_effects(api):
    owner, editor = account(api, "ConcurrentOwner"), account(api, "SecondWriter")
    common, (a,) = workspace(api, owner, "Native", 1)
    invite_member(api, "/api/tenants/" + owner["tenant"], owner["headers"], editor["headers"], email=editor["email"], role="editor")

    def save(n):
        return api.post(common, headers=owner["headers"], json=dict(key=uuid4().hex, expected_revision=0, fields={"goal": "Goal " + str(n)})).status_code

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(save, [1, 2])) == [201, 409]

    def counts():
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as observer:
            public = tuple(
                observer.execute("SELECT count(*) FROM " + tbl + " WHERE tenant_id=%s", (owner["tenant"],)).fetchone()[0]
                for tbl in ("workforce_runs", "workforce_briefs", "work_tasks")
            )
            return (
                public
                + observer.execute(
                    "SELECT count(*),coalesce(sum(held),0),coalesce(sum(spent),0) FROM amc_ops.ledger WHERE tenant=%s", (owner["tenant"],)
                ).fetchone()
            )

    before = counts()
    token = uuid4().hex

    def draft(_):
        return post(api, a + "/briefs", owner, key=token, expected_revision=0, expected_company_revision=1, title="Pinned once")

    with ThreadPoolExecutor(2) as pool:
        one, two = pool.map(draft, [1, 2])
    assert one == two and len(read(api, a, owner)["briefs"]) == 1 and counts() == before
    for actor, visible in [(editor, 0), (owner, 1)]:
        with Session(engine) as db:
            set_context(db, actor=actor["id"], tenant=owner["tenant"])
            sign_actor(db, actor["id"])
            view = text("SELECT count(*) FROM business_workspace_records WHERE id=:id")
            assert db.scalar(view, {"id": one["id"]}) == visible
            assert not db.scalar(text("SELECT has_table_privilege(current_user,'business_workspace_records','INSERT,UPDATE,DELETE,TRUNCATE')"))
            set_worker_scope(db, a.split("/")[5], a.split("/")[7], str(uuid4()))
            assert db.scalar(view, {"id": one["id"]}) == 0
