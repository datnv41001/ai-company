"""Campaign and brief pins survive content ABA and separate lab authority from actual targets."""

from contextlib import closing
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from agency_fixtures import account, create
from app.access import set_context
from app.database import engine, get_db
from app.main import app
from app.security import sign_actor
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, bundle, call


def test_target_content_generation_and_foundation_scope(api):
    owner, path, _, claim, lab = bundle(api)
    tenant = owner["tenant"]
    base = "/api/tenants/" + tenant
    cid, bid = path.split("/")[5], path.split("/")[7]
    client = account(api, "TargetClient")
    invite_member(api, base, owner["headers"], client["headers"], email=client["email"], client_id=cid, role="client_viewer")
    campaign = create(api, base + "/campaigns", owner, dict(brand_id=bid, name="Campaign", brief="New tile description", objective="Product enquiries"))

    def brief(title):
        return create(api, base + "/workforce/briefs", owner, dict(campaign_id=campaign["id"], recipient_id=client["id"], title=title))

    first, second = brief("Check first brief"), brief("Second brief")
    target = {"campaign_id": campaign["id"], "brief_id": first["id"]}
    other = target | {"brief_id": second["id"]}

    def preview():
        return accepted(call(api, owner, path, "/previews", claims=[claim["id"]], target=target))

    def queue(snap, **kwargs):
        return call(api, owner, path, "/authorize", operation="queue", snapshot_id=snap["id"], digest=snap["digest"], **kwargs)

    draft = preview()
    assert draft["target"]["kind"] == "campaign_brief" and not draft["target"]["submitted"]
    assert queue(draft, target=target).status_code == 409
    assert queue(lab, target=target).status_code == 409
    assert queue(draft).status_code == 409
    payload = dict(
        objective="Report approved tile details",
        audience="Trade installers",
        offer="Current catalogue",
        sources=[dict(label="Product sheet", excerpt="Matte ceramic tile")],
    )
    assert api.put(base + "/workforce/briefs/" + first["id"] + "/submission", headers=client["headers"], json=payload).status_code == 200
    assert queue(draft, target=target).status_code == 409
    frozen = preview()
    assert frozen["target"]["brief_generation"] > draft["target"]["brief_generation"]
    assert payload["objective"] not in frozen["canonical"]
    assert queue(frozen, target=other).status_code == 409
    key = uuid4().hex
    receipt = accepted(queue(frozen, target=target, key=key))
    assert receipt["target"] == frozen["target"]
    assert queue(frozen, target=target, key=key).json() == receipt
    assert queue(frozen, target=other, key=key).status_code == 409
    # Two legitimate edits of the campaign through the scoped runtime leave its
    # original wording intact. Its persisted generation still invalidates a new action.
    bind = engine
    if get_db in app.dependency_overrides:
        with closing(app.dependency_overrides[get_db]()) as dbs:
            bind = next(dbs).get_bind()
    for objective in ("Temporary offer", campaign["objective"]):
        with Session(bind) as db:
            set_context(db, actor=owner["id"], tenant=tenant)
            sign_actor(db, owner["id"])
            assert (
                db.execute(
                    text("UPDATE campaigns SET objective=:value WHERE id=:id AND tenant_id=:t"), dict(value=objective, id=campaign["id"], t=tenant)
                ).rowcount
                == 1
            )
            db.commit()
    assert queue(frozen, target=target).status_code == 409
    assert queue(frozen, target=target, key=key).json() == receipt
    renewed = preview()
    assert renewed["target"]["campaign_digest"] == frozen["target"]["campaign_digest"]
    assert renewed["target"]["campaign_generation"] > frozen["target"]["campaign_generation"]
    assert api.delete(base + "/members/" + client["id"] + "/client-scope", headers=owner["headers"]).status_code == 204
    assert queue(renewed, target=target).status_code in (404, 409)
    retained = api.get(path + "/receipts/" + receipt["id"], headers=owner["headers"])
    assert retained.json() == receipt
