"""Shared company objectives, brand/campaign applicability, pinned decisions and client isolation."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from agency_fixtures import account, create
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, bundle
from app.access import set_context, set_worker_scope
from app.database import engine
from app.security import sign_actor
from test_business_workspace import workspace, post, read
from test_marketing_catalog import save, approve


def area(api, owner, name):
    path, brands = workspace(api, owner, name)
    return path.rsplit("/", 1)[0] + "/company-objectives", [b.rsplit("/", 1)[0] for b in brands]


def decision(api, base, owner, row, state="approved", status=200, **overrides):
    return post(
        api,
        base + "/" + row["id"] + "/events",
        owner,
        status=status,
        **({"expected_sequence": row["sequence"], "expected_digest": row["digest"], "state": state, "reason": "Synthetic decision"} | overrides),
    )


def objective(api, owner, brand, level, **opts):
    return save(api, owner, brand + "/catalog", "objective", {"level": level, "name": level + " target", "owner": "Planner", **opts})


def test_shared_company_brand_campaign_and_cross_scope(api):
    owner, outsider = account(api, "CompanyPlanner"), account(api, "UnrelatedPlanner")
    shared, (a, b) = area(api, owner, "Ceramics")
    other, (c, _) = area(api, owner, "Other client")
    foreign, _ = area(api, outsider, "Other tenant")
    key = uuid4().hex
    body = dict(key=key, name="Shared inquiries", owner="Sales", expected_revision=0)
    root = post(api, shared, owner, **body)
    assert read(api, shared + "/commands/" + key, owner) == post(api, shared, owner, **body) == root
    post(api, shared, owner, status=409, **(body | {"owner": "Changed"}))
    assert not read(api, shared + "?approved_only=true", owner)["items"]
    child = accepted(objective(api, owner, a, "brand", company_parent=root["id"]))
    assert approve(api, owner, a + "/knowledge", child).status_code == 409
    decision(api, shared, owner, root)
    accepted(approve(api, owner, a + "/knowledge", child))
    sibling = accepted(objective(api, owner, b, "brand", company_parent=root["id"]))
    accepted(approve(api, owner, b + "/knowledge", sibling))
    assert read(api, a + "/catalog/items/" + child["id"], owner)["references"]["company_parent"]["label"] == "Shared inquiries"
    assert [r["id"] for r in read(api, shared + "?approved_only=true&q=inquiries", owner)["items"]] == [root["id"]]
    for area_path, actor in [(other, owner), (foreign, outsider), (shared, outsider)]:
        assert api.get(area_path + "/" + root["id"], headers=actor["headers"]).status_code == 404
    assert objective(api, owner, c, "brand", company_parent=root["id"]).status_code == 404
    campaign = create(
        api,
        "/api/tenants/" + owner["tenant"] + "/campaigns",
        owner,
        dict(brand_id=a.split("/")[-1], name="Spring tiles", brief="Installers", objective="Reach builders"),
    )
    campaign_obj = accepted(objective(api, owner, a, "campaign", parent=child["id"], campaign_id=campaign["id"]))
    accepted(approve(api, owner, a + "/knowledge", campaign_obj))
    assert read(api, a + "/catalog/items/" + campaign_obj["id"], owner)["references"]["campaign_id"]["label"] == "Spring tiles"
    assert objective(api, owner, b, "campaign", parent=sibling["id"], campaign_id=campaign["id"]).status_code == 422
    assert objective(api, owner, a, "campaign", parent=sibling["id"], campaign_id=campaign["id"]).status_code == 404
    assert objective(api, owner, a, "campaign", company_parent=root["id"], campaign_id=campaign["id"]).status_code == 422
    assert objective(api, owner, a, "brand", company_parent=root["id"], parent=sibling["id"]).status_code == 422
    legacy = accepted(objective(api, owner, a, "company"))
    assert objective(api, owner, b, "brand", parent=legacy["id"]).status_code == 404
    _, _, source, _, _ = bundle(api, owner, b + "/knowledge")
    kpi = accepted(
        save(
            api,
            owner,
            b + "/catalog",
            "kpi",
            dict(
                name="Requests",
                company_objective=root["id"],
                unit="requests",
                method="Count verified messages",
                window="Month",
                owner="Sales",
                target="15",
                source=source["id"],
            ),
        )
    )
    accepted(approve(api, owner, b + "/knowledge", kpi))
    assert read(api, b + "/catalog/items/" + kpi["id"], owner)["references"]["company_objective"]["id"] == root["id"]


def test_authority_on_replacement_and_historical_receipts(api):
    owner = account(api, "ObjectiveAuthority")
    base, (a, _) = area(api, owner, "Objective changes")
    root = post(api, base, owner, name="Revenue 10", owner="Sales", expected_revision=0)
    approved = decision(api, base, owner, root)
    child = accepted(objective(api, owner, a, "brand", company_parent=root["id"]))
    next_root = post(api, base, owner, name="Revenue 20", owner="Sales", subject=root["subject"], expected_revision=1)
    assert [r["id"] for r in read(api, base + "?approved_only=true", owner)["items"]] == [root["id"]]
    accepted(approve(api, owner, a + "/knowledge", child))
    next_approval = decision(api, base, owner, next_root)
    pending = accepted(objective(api, owner, a, "brand", company_parent=root["id"]))
    assert approve(api, owner, a + "/knowledge", pending).status_code == 409
    assert read(api, base + "/" + root["id"], owner)["state"] == "superseded"
    assert read(api, base + "/" + root["id"] + "/events", owner) == [root, approved]
    decision(api, base, owner, next_approval, "withdrawn")
    assert not read(api, base + "?approved_only=true", owner)["items"]
    assert approve(api, owner, a + "/knowledge", pending).status_code == 409
    assert read(api, base + "/" + root["id"], owner)["data"]["name"] == "Revenue 10"


def test_roles_commands_and_revision_cas(api):
    owner, editor, viewer = [account(api, n) for n in ("ObjectiveOwner", "ObjectiveEditor", "ObjectiveViewer")]
    shared, _ = area(api, owner, "Roles")
    tenant = "/api/tenants/" + owner["tenant"]
    for actor, role in [(editor, "editor"), (viewer, "viewer")]:
        invite_member(api, tenant, owner["headers"], actor["headers"], email=actor["email"], role=role)
    key = uuid4().hex
    root = post(api, shared, editor, key=key, name="Retention", owner="Lead", expected_revision=0)
    decision(api, shared, editor, root, status=404)
    assert api.get(shared + "/commands/" + key, headers=owner["headers"]).status_code == 404
    post(api, shared, viewer, status=404, name="Writer", owner="Lead", expected_revision=0)
    assert read(api, shared + "/" + root["id"], viewer)["id"] == root["id"]
    assert api.put(tenant + "/members/" + viewer["id"] + "/client-scope", headers=owner["headers"], json={"client_id": shared.split("/")[5]}).status_code == 200
    assert api.get(shared, headers=viewer["headers"]).status_code == 404

    def revise(n):
        return api.post(
            shared,
            headers=editor["headers"],
            json=dict(key=uuid4().hex, expected_revision=1, subject=root["subject"], name="Retention " + str(n), owner="Lead"),
        ).status_code

    assert [revise(1), revise(2)] == [201, 409]


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_native_company_objective_rls_and_serialized_update(api):
    company, outsider = account(api, "ObjectiveNative"), account(api, "NativeOtherTenant")
    base, (a, _) = area(api, company, "Native planning")
    root = post(api, base, company, name="Shared KPI", owner="Sales", expected_revision=0)
    decision(api, base, company, root)
    child = accepted(objective(api, company, a, "brand", company_parent=root["id"]))

    def save_once(n):
        return api.post(
            base, headers=company["headers"], json=dict(key=uuid4().hex, expected_revision=1, subject=root["subject"], name="Shared " + str(n), owner="Sales")
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save_once, (1, 2))) == [201, 409]
    for actor, visible in ((company, 1), (outsider, 0)):
        with Session(engine) as db:
            set_context(db, actor=actor["id"], tenant=actor["tenant"])
            sign_actor(db, actor["id"])
            for table, col, key in (("business_company_objectives", "id", root["id"]), ("business_company_objective_edges", "revision_id", child["id"])):
                assert not db.scalar(text("SELECT has_table_privilege(current_user,:t,'INSERT,UPDATE,DELETE,TRUNCATE')"), {"t": table})
                assert db.scalar(text(f"SELECT count(*) FROM {table} WHERE {col}=:key"), {"key": key}) == visible
            set_worker_scope(db, a.split("/")[5], a.split("/")[7], str(uuid4()))
            assert db.scalar(text("SELECT count(*) FROM business_company_objectives WHERE id=:id"), {"id": root["id"]}) == 0
