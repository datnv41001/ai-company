from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.database import engine
from app.models import utcnow
from agency_fixtures import account, create


@pytest.fixture
def delivery(api, agency):
    owner, base, readers = agency
    a, a_data = readers[0]
    editor = account(api, "Editor")
    reviewer = account(api, "Reviewer")
    viewer = account(api, "ReadOnly")
    create(api, base + "/members", owner, {"email": editor["email"], "role": "editor"})
    for who in (reviewer, viewer):
        create(api, base + "/members", owner, {"email": who["email"], "role": "client_viewer", "client_id": next(iter(a_data["clients"]))})
    campaign = sorted(a_data["campaigns"])[0]
    draft = create(
        api,
        base + "/deliverables",
        editor,
        {"campaign_id": campaign, "title": "Handout", "content": {"client_preview": "Public copy", "internal_prompt": "private-canary"}},
    )
    path = base + "/deliverables/" + draft["id"]

    def approve_and_share(hours=3):
        assert api.post(path + "/submit", headers=editor["headers"]).status_code == 200
        assert api.post(path + "/review", headers=owner["headers"], json={"decision": "approved", "note": "private-qa"}).status_code == 200
        return create(api, path + "/share", owner, {"expires_at": (utcnow() + timedelta(hours=hours)).isoformat()})

    def grant(who, **changes):
        payload = {"can_comment": True, "can_decide": True, **changes}
        return api.put(base + f"/members/{who['id']}/review-rights", headers=owner["headers"], json=payload)

    assert grant(a).status_code == grant(reviewer).status_code == 200
    return owner, base, readers, editor, reviewer, viewer, path, approve_and_share, grant


def event(api, base, who, review, kind, **changes):
    payload = dict(digest=review["digest"], kind=kind, note="", request_key=uuid4().hex)
    return api.post(base + f"/reviews/{review['id']}/events", headers=who["headers"], json={**payload, **changes})


def test_exact_version_and_independent_rights(api, delivery):
    owner, base, ((alice, _), (bob, _)), editor, reviewer, viewer, path, share, grant = delivery
    assert api.get(base + "/reviews", headers=alice["headers"]).json() == []
    assert api.post(path + "/share", headers=owner["headers"], json={"expires_at": (utcnow() + timedelta(days=2)).isoformat()}).status_code == 409
    v1 = share()
    url = base + "/reviews/" + v1["id"]
    assert api.get(url, headers=bob["headers"]).status_code == 404
    assert api.get(base + "/reviews", headers=bob["headers"]).json() == []
    r = api.get(url, headers=viewer["headers"])
    assert r.json()["preview"] == "Public copy" and "private-" not in r.text and r.json()["version"] == 1
    canonical = json.dumps({"title": "Handout", "preview": "Public copy"}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert sha256(canonical).hexdigest() == v1["digest"]
    for who in (owner, viewer, bob):
        assert event(api, base, who, v1, "approved").status_code == 404
    assert event(api, base, reviewer, v1, "approved", digest="0" * 64).status_code == 409
    assert grant(viewer, can_decide=False).status_code == 200
    assert event(api, base, viewer, v1, "comment", note="Please confirm").status_code == 200
    key = uuid4().hex
    for _ in range(2):
        result = event(api, base, alice, v1, "approved", request_key=key)
        assert result.status_code == 200
        assert [e["kind"] for e in result.json()["history"]] == ["comment", "approved"]
    assert event(api, base, alice, v1, "rejected", request_key=key).status_code == 409
    assert api.patch(path + "/draft", headers=editor["headers"], json={"title": "Revised", "client_preview": "Public copy 2"}).status_code == 200
    v2 = share()
    assert v2["version"] == 2 and v2["status"] == "pending" and v2["digest"] != v1["digest"]
    assert api.get(url, headers=alice["headers"]).json()["status"] == "approved"
    assert api.get(url, headers=alice["headers"]).json()["preview"] == "Public copy"
    assert event(api, base, alice, v2, "changes_requested", note="Please shorten").json()["status"] == "changes_requested"


def test_rescope_cancel_and_supersede(api, delivery):
    owner, base, ((alice, a), (_, b)), editor, reviewer, _, path, share, grant = delivery
    v1 = share()
    assert grant(alice, brand_id=next(iter(b["brands"]))).status_code == 404
    assert grant(alice, brand_id=next(iter(a["brands"] - {v1["brand_id"]}))).status_code == 200
    assert api.get(base + "/reviews/" + v1["id"], headers=alice["headers"]).status_code == 404
    assert grant(alice, brand_id=v1["brand_id"], campaign_id=v1["campaign_id"], can_decide=False).status_code == 200
    assert event(api, base, alice, v1, "approved").status_code == 404
    assert api.patch(path + "/draft", headers=editor["headers"], json={"title": "Updated", "client_preview": "Second version"}).status_code == 200
    v2 = share()
    assert event(api, base, reviewer, v1, "approved").status_code == 409
    assert api.get(base + "/reviews/" + v1["id"], headers=reviewer["headers"]).json()["status"] == "superseded"
    assert event(api, base, owner, v2, "cancelled").json()["status"] == "cancelled"
    assert event(api, base, reviewer, v2, "approved").status_code == 409
    assert api.delete(base + f"/members/{reviewer['id']}/client-scope", headers=owner["headers"]).status_code == 204
    assert api.get(base + "/reviews/" + v2["id"], headers=reviewer["headers"]).status_code == 404


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_competing_decisions_and_direct_sql(api, delivery):
    owner, base, ((alice, _), (bob, b)), _, peer, _, _, share, _ = delivery
    v = share()
    with ThreadPoolExecutor(2) as pool:
        jobs = [pool.submit(event, api, base, who, v, kind) for who, kind in [(alice, "approved"), (peer, "rejected")]]
    assert sorted(j.result().status_code for j in jobs) == [200, 409]
    with engine.connect() as conn:
        for who, expected in ((alice, 1), (bob, 0)):
            for table in ("client_reviews", "review_entries", "portal_grants"):
                assert conn.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            conn.execute(text("SELECT set_config('amc.user_id',:u,true),set_config('amc.tenant_id',:t,true)"), {"u": who["id"], "t": owner["tenant"]})
            assert conn.scalar(text("SELECT count(*) FROM client_reviews")) == expected
            assert conn.scalar(text("SELECT count(*) FROM review_entries")) == expected
            with pytest.raises(DBAPIError), conn.begin_nested():
                conn.execute(text("UPDATE client_reviews SET title='changed' WHERE id=:i"), {"i": v["id"]})
            conn.rollback()
        conn.execute(text("SELECT set_config('amc.user_id',:u,true),set_config('amc.tenant_id',:t,true)"), {"u": owner["id"], "t": owner["tenant"]})
        with pytest.raises(DBAPIError) as denied, conn.begin_nested():
            conn.execute(text("UPDATE portal_grants SET brand_id=:b WHERE user_id=:a"), {"b": next(iter(b["brands"])), "a": alice["id"]})
        assert denied.value.orig.sqlstate == "23503"


def test_expiry_and_reject_forged_scope(api, delivery):
    import time

    _, base, ((reader, _), (other, _)), _, _, _, _, share, _ = delivery
    review = share(hours=0.00025)
    assert event(api, base, reader, review, "approved", tenant_id=other["tenant"]).status_code == 422
    time.sleep(1)
    assert api.get(base + "/reviews/" + review["id"], headers=reader["headers"]).json()["status"] == "expired"
    assert event(api, base, reader, review, "approved").status_code == 409


def test_edit_requires_new_independent_qa_and_rejection_is_final(api, delivery):
    owner, base, ((alice, _), _), editor, _, _, path, share, _ = delivery
    old = share()
    title = 'Bài "mới"'
    content = "Câu thứ nhất.\nDòng thứ hai."
    assert api.patch(path + "/draft", headers=owner["headers"], json={"title": title, "client_preview": content}).status_code == 200
    assert api.post(path + "/submit", headers=owner["headers"]).status_code == 200
    assert api.post(path + "/review", headers=owner["headers"], json={"decision": "approved"}).status_code == 403
    qa = account(api, "SecondQA")
    create(api, base + "/members", owner, {"email": qa["email"], "role": "admin"})
    assert api.post(path + "/review", headers=qa["headers"], json={"decision": "approved"}).status_code == 200
    revised = create(api, path + "/share", owner, {"expires_at": (utcnow() + timedelta(days=1)).isoformat()})
    assert revised["title"] == title and revised["preview"] == content
    assert event(api, base, alice, revised, "rejected").json()["status"] == "rejected"
    assert event(api, base, alice, revised, "approved").status_code == 409
    assert api.get(base + "/reviews/" + old["id"], headers=alice["headers"]).json()["status"] == "superseded"
