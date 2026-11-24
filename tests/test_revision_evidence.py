from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from agency_fixtures import account, create
from identity_fixtures import invite_member
from app.database import engine
from app.models import utcnow


def test_manual_report_is_internal_and_metadata_cannot_supply_evidence(api, agency):
    owner, base, readers = agency
    campaign = next(iter(readers[0][1]["campaigns"]))
    doc = create(
        api,
        base + "/deliverables",
        owner,
        {
            "campaign_id": campaign,
            "title": "Offer",
            "content": {
                "client_preview": "The best.",
                "workforce_run_id": "foreign-run",
                "qa_claims": [],
                "source_ids": ["forged"],
                "qa_evidence": {"state": "current"},
                "qa_approved_digest": "f" * 64,
            },
        },
    )
    report = doc["qa_evidence"]
    assert report["state"] == "source_unavailable"
    assert report["findings"][0]["status"] == "needs_evidence"
    assert report["findings"][0]["cited_ids"] == []
    assert doc["qa_approved_digest"] is None
    assert set(doc["content"]) == {"client_preview"}
    outsider = account(api, "Outside")
    for actor in (readers[0][0], readers[1][0], outsider):
        assert api.get(base + "/deliverables/" + doc["id"], headers=actor["headers"]).status_code == 404
        if engine.dialect.name == "postgresql":
            with engine.connect() as conn:
                conn.execute(text("SELECT set_config('amc.user_id',:u,true),set_config('amc.tenant_id',:t,true)"), {"u": actor["id"], "t": owner["tenant"]})
                assert conn.execute(text("SELECT qa_evidence FROM deliverables WHERE id=:d"), {"d": doc["id"]}).first() is None
                assert conn.execute(text("SELECT knowledge FROM workforce_runs WHERE deliverable_id=:d"), {"d": doc["id"]}).first() is None


def test_title_only_revision_rejects_old_approval_and_rejection(api, agency):
    owner, base, readers = agency
    editor = account(api, "Editor")
    invite_member(api, base, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    preview = "Copy stays unchanged."
    doc = create(
        api,
        base + "/deliverables",
        editor,
        {"title": "Original", "content": {"client_preview": preview}, "campaign_id": next(iter(readers[0][1]["campaigns"]))},
    )
    path = base + "/deliverables/" + doc["id"]
    first = doc["qa_evidence"]
    api.post(path + "/submit", headers=editor["headers"]).raise_for_status()
    assert api.post(path + "/review", headers=owner["headers"], json={"decision": "approved"}).status_code == 422
    api.patch(path + "/draft", headers=editor["headers"], json={"title": "The best.", "client_preview": preview}).raise_for_status()
    revised = api.post(path + "/submit", headers=editor["headers"]).json()["qa_evidence"]
    assert revised["content_digest"] != first["content_digest"]
    assert [(f["field"], f["claim"]) for f in revised["findings"]] == [("title", "The best.")]
    for decision in ("approved", "rejected"):
        assert (
            api.post(
                path + "/review",
                headers=owner["headers"],
                json={"decision": decision, "expected_content_digest": first["content_digest"], "expected_qa_revision": first["qa_revision"]},
            ).status_code
            == 412
        )
    approved = api.post(
        path + "/review",
        headers=owner["headers"],
        json={"decision": "approved", "expected_qa_revision": revised["qa_revision"], "expected_content_digest": revised["content_digest"]},
    )
    assert approved.json()["qa_approved_digest"] == revised["content_digest"]
    trail = api.get(base + "/audit", params={"subject_id": doc["id"]}, headers=owner["headers"]).json()
    events = [e for e in trail if e["subject_id"] == doc["id"]]
    assert {e["details"]["content_digest"] for e in events if e["event"] == "deliverable.qa_evaluated"} == {first["content_digest"], revised["content_digest"]}
    decision = next(e for e in events if e["event"] == "deliverable.reviewed")
    assert decision["user_id"] == owner["id"] and decision["details"] == {
        "content_digest": revised["content_digest"],
        "qa_revision": revised["qa_revision"],
        "ruleset_version": revised["ruleset_version"],
        "decision": "approved",
    }


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_concurrent_staff_decisions_and_sharing(api, agency):
    owner, base, readers = agency
    editor = account(api, "RaceEditor")
    invite_member(api, base, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    doc = create(
        api, base + "/deliverables", editor, {"title": "Original", "content": {"client_preview": "A"}, "campaign_id": next(iter(readers[0][1]["campaigns"]))}
    )
    path = base + "/deliverables/" + doc["id"]
    api.post(path + "/submit", headers=editor["headers"]).raise_for_status()

    def approve(report):
        return api.post(
            path + "/review",
            headers=owner["headers"],
            json={"decision": "approved", "expected_content_digest": report["content_digest"], "expected_qa_revision": report["qa_revision"]},
        )

    with ThreadPoolExecutor(2) as pool:
        edit = pool.submit(api.patch, path + "/draft", headers=editor["headers"], json={"title": "Next", "client_preview": "B"})
        vote = pool.submit(approve, doc["qa_evidence"])
    assert edit.result().status_code == 200 and vote.result().status_code in (200, 412)
    current = api.get(path, headers=owner["headers"]).json()
    assert current["status"] == "draft" and current["qa_approved_digest"] is None
    digest = current["qa_evidence"]["content_digest"]
    api.post(path + "/submit", headers=editor["headers"]).raise_for_status()

    def share():
        return api.post(path + "/share", headers=owner["headers"], json={"expires_at": (utcnow() + timedelta(days=1)).isoformat()})

    with ThreadPoolExecutor(2) as pool:
        snapshot = pool.submit(share)
        vote = pool.submit(approve, current["qa_evidence"])
    assert vote.result().status_code == 200 and snapshot.result().status_code in (201, 409)
    shared = snapshot.result() if snapshot.result().status_code == 201 else share()
    assert shared.json()["digest"] == digest and shared.json()["preview"] == "B"
    with ThreadPoolExecutor(2) as pool:
        edits = [pool.submit(api.patch, path + "/draft", headers=editor["headers"], json={"title": "Next", "client_preview": copy}) for copy in ("C", "D")]
    assert all(result.result().is_success for result in edits)
    final = api.get(path, headers=owner["headers"]).json()
    assert final["qa_revision"] == current["qa_revision"] + 2 == final["qa_evidence"]["qa_revision"]


@pytest.mark.parametrize(
    "phrase,category",
    [
        ("Gia phai chang.", "price"),
        ("San pham tot nhat thi truong.", "superiority"),
        ("Giá phải chăng.", "price"),
        ("Affordable.", "price"),
        ("Bác sĩ khuyên dùng.", "endorsement"),
        ("Recommended by experts.", "endorsement"),
        ("Sản phẩm tốt nhất thị trường.", "superiority"),
        ("The best.", "superiority"),
        ("Cam kết hiệu quả.", "guarantee"),
        ("Guaranteed results.", "guarantee"),
    ],
)
def test_quote_identifies_text_even_in_an_unreliable_source(phrase, category):
    from app.workforce_evidence import assess

    output = {"sections": {"title": phrase}, "source_ids": ["S1"]}
    assert assess(output, {"S1": {"excerpt": "Not " + phrase}})["claims"][0]["status"] == "needs_evidence"
    found = assess(output, {"S1": {"excerpt": phrase, "label": "Unverified advertisement"}})["claims"][0]
    assert found["categories"] == [category] and found["status"] == "source_quote"


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_legacy_approval_requires_a_fresh_report_and_human_decision(api, agency):
    import os
    import psycopg

    owner, base, readers = agency
    editor = account(api, "LegacyEditor")
    invite_member(api, base, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    doc = create(
        api,
        base + "/deliverables",
        editor,
        {"title": "Legacy", "content": {"client_preview": "Affordable."}, "campaign_id": next(iter(readers[0][1]["campaigns"]))},
    )
    path = base + "/deliverables/" + doc["id"]
    # Represent a v6 approval after the additive migration, including arbitrary legacy JSON.
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
        assert db.info.dbname.startswith("amc_test")
        db.execute(
            """UPDATE deliverables SET status='approved', reviewed_by=%s, qa_evidence=NULL,
                      content='{"client_preview":"Affordable.","qa_evidence":{"state":"current"},"qa_claims":[]}'
                      WHERE id=%s""",
            (owner["id"], doc["id"]),
        )
    expiry = {"expires_at": (utcnow() + timedelta(days=1)).isoformat()}
    assert api.get(path, headers=owner["headers"]).json()["qa_evidence"] is None
    assert api.post(path + "/share", headers=owner["headers"], json=expiry).status_code == 409
    evaluated = api.post(path + "/assessment", headers=owner["headers"]).json()["qa_evidence"]
    assert evaluated["findings"][0]["status"] == "needs_evidence"
    assert api.post(path + "/share", headers=owner["headers"], json=expiry).status_code == 409
    api.post(
        path + "/review",
        headers=owner["headers"],
        json={"decision": "approved", "expected_qa_revision": evaluated["qa_revision"], "expected_content_digest": evaluated["content_digest"]},
    ).raise_for_status()
    # A matching digest alone cannot authorize sharing when the approval revision is absent.
    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as db:
        db.execute("UPDATE deliverables SET qa_approved_revision=NULL WHERE id=%s", (doc["id"],))
    assert api.post(path + "/share", headers=owner["headers"], json=expiry).status_code == 409
    api.post(
        path + "/review",
        headers=owner["headers"],
        json={"decision": "approved", "expected_qa_revision": evaluated["qa_revision"], "expected_content_digest": evaluated["content_digest"]},
    ).raise_for_status()
    shared = create(api, path + "/share", owner, expiry)
    assert shared["digest"] == evaluated["content_digest"]
    assert "qa_evidence" not in shared and "qa_claims" not in shared


def test_sqlite_upgrades_legacy_columns_without_trusting_content():
    from sqlalchemy import create_engine, inspect
    from app.database import Base, prepare_database

    bind = create_engine("sqlite://")
    Base.metadata.create_all(bind)
    with bind.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE deliverables DROP COLUMN qa_revision")
        conn.exec_driver_sql("ALTER TABLE deliverables DROP COLUMN qa_approved_revision")
        conn.exec_driver_sql("ALTER TABLE deliverables DROP COLUMN qa_evidence")
        conn.exec_driver_sql("ALTER TABLE deliverables DROP COLUMN qa_approved_digest")
        conn.exec_driver_sql("""INSERT INTO deliverables(id,tenant_id,campaign_id,title,content,status,created_by)
            VALUES('old','t','c','Old','{"qa_evidence":{"state":"current"}}','approved','u')""")
    prepare_database(bind)
    prepare_database(bind)
    with bind.connect() as conn:
        assert {"qa_evidence", "qa_approved_digest"} <= {c["name"] for c in inspect(conn).get_columns("deliverables")}
        assert conn.exec_driver_sql("SELECT qa_revision,qa_approved_revision FROM deliverables WHERE id='old'").one() == (1, None)
        assert conn.exec_driver_sql("SELECT qa_evidence,qa_approved_digest FROM deliverables WHERE id='old'").one() == (None, None)
    bind.dispose()


def test_restored_copy_requires_a_new_qa_decision(api, agency):
    owner, base, readers = agency
    editor = account(api, "RevisionEditor")
    invite_member(api, base, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    original = {"title": "Spring offer", "client_preview": "Original copy."}
    doc = create(
        api,
        base + "/deliverables",
        editor,
        {"campaign_id": next(iter(readers[0][1]["campaigns"])), "title": original["title"], "content": {"client_preview": original["client_preview"]}},
    )
    path = base + "/deliverables/" + doc["id"]
    first = api.post(path + "/submit", headers=editor["headers"]).json()
    vote = {"decision": "approved", "expected_content_digest": first["qa_evidence"]["content_digest"], "expected_qa_revision": first["qa_revision"]}
    for copy in ({**original, "client_preview": "Changed copy."}, original):
        api.patch(path + "/draft", headers=editor["headers"], json=copy).raise_for_status()
    restored = api.post(path + "/submit", headers=editor["headers"]).json()
    assert restored["qa_evidence"]["content_digest"] == vote["expected_content_digest"]
    for decision in ("approved", "rejected"):
        response = api.post(path + "/review", headers=owner["headers"], json={**vote, "decision": decision})
        assert response.status_code == 412
    assert restored["qa_revision"] == first["qa_revision"] + 2
    assert (
        api.post(
            path + "/review", headers=owner["headers"], json={"decision": "approved", "expected_content_digest": vote["expected_content_digest"]}
        ).status_code
        == 422
    )
    invalid_hash = {**vote, "expected_qa_revision": restored["qa_revision"], "expected_content_digest": "0" * 64}
    assert api.post(path + "/review", headers=owner["headers"], json=invalid_hash).status_code == 412
    vote["expected_qa_revision"] = restored["qa_revision"]
    approved = api.post(path + "/review", headers=owner["headers"], json=vote).raise_for_status().json()
    assert approved["qa_approved_revision"] == restored["qa_revision"]
    assert approved["qa_approved_digest"] == vote["expected_content_digest"]
    expiry = {"expires_at": (utcnow() + timedelta(days=1)).isoformat()}
    # Even saving the exact same copy starts the next review cycle.
    api.patch(path + "/draft", headers=editor["headers"], json=original).raise_for_status()
    assert api.post(path + "/share", headers=owner["headers"], json=expiry).status_code == 409
    next_copy = api.post(path + "/submit", headers=editor["headers"]).json()
    assert next_copy["qa_revision"] == restored["qa_revision"] + 1 and next_copy["qa_approved_revision"] is None
    assert api.post(path + "/review", headers=owner["headers"], json=vote).status_code == 412
    events = api.get(base + "/audit", headers=owner["headers"], params={"subject_id": doc["id"]}).json()
    assert [e["details"]["qa_revision"] for e in events if e["event"] == "deliverable.reviewed"] == [restored["qa_revision"]]
