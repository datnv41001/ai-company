"""Positive controls and denied entitlement on normal product API and signed runtime LOGIN."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from agency_fixtures import account
from app.access import set_context, set_worker_scope
from app.database import engine
from app.security import sign_actor
from identity_fixtures import invite_member
from knowledge_fixtures import accepted, call, revision, scope


def test_visibility_and_revoked_reader(api):
    owner, editor, client = [account(api, n) for n in ("PrivacyOwner", "PrivacyEditor", "ScopedReader")]
    tenant = owner["tenant"]
    base = "/api/tenants/" + tenant
    path = scope(api, owner, "Marketing catalogue")
    cid = path.split("/")[5]
    invite_member(api, base, owner["headers"], editor["headers"], email=editor["email"], role="editor")
    invite_member(api, base, owner["headers"], client["headers"], email=client["email"], role="viewer")
    public = revision(api, owner, path, "public", "product", {"name": "Public name"})
    private = revision(api, owner, path, "confidential", "guidelines", {"guidance": "Internal test supplier condition"}, visibility="restricted")
    internal = revision(api, editor, path, "crew", "guidelines", {"guidance": "Staff workflow"}, visibility="internal", approve=False)
    assert api.get(path + "/revisions/" + internal["id"], headers=client["headers"]).status_code == 200
    assert api.put(base + "/members/" + client["id"] + "/client-scope", headers=owner["headers"], json={"client_id": cid}).status_code == 200
    for row in (public, internal, private):
        view = path + "/revisions/" + row["id"]
        assert api.get(view, headers=owner["headers"]).status_code == 200
        assert api.get(view, headers=client["headers"]).status_code == 404
        assert api.get(view, headers=editor["headers"]).status_code == (404 if row is private else 200)
    hidden = call(
        api, editor, path, "/revisions", subject="confidential", kind="guidelines", visibility="internal", expected_revision=0, data={"guidance": "Candidate"}
    )
    visible = call(
        api, editor, path, "/revisions", subject="crew", kind="guidelines", visibility="internal", expected_revision=0, data={"guidance": "Candidate"}
    )
    assert hidden.status_code == visible.status_code == 409 and hidden.json() == visible.json()
    assert api.delete(base + "/members/" + client["id"] + "/client-scope", headers=owner["headers"]).status_code == 204
    assert api.get(path + "/snapshots/anything", headers=client["headers"]).status_code == 404
    assert (
        call(
            api, editor, path, f"/revisions/{internal['id']}/events", expected_sequence=0, expected_digest=internal["digest"], state="approved", reason="Review"
        ).status_code
        == 404
    )


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_signed_read_only_runtime_and_worker(api):
    owner, other, client = (account(api, x) for x in ("DbActor", "DbOuter", "DbClient"))
    path = scope(api, owner, "Signed synthetic")
    tenant = owner["tenant"]
    cid, bid = path.split("/")[5], path.split("/")[7]
    invite_member(api, "/api/tenants/" + tenant, owner["headers"], client["headers"], email=client["email"], role="client_viewer", client_id=cid)
    row = revision(api, owner, path, "owner-source", "guidelines", {"guidance": "Controlled confidential material"}, visibility="restricted")
    for user, visible in ((owner, True), (other, False), (client, False)):
        with Session(engine) as session:
            assert session.scalar(text("select current_user")) == "amc_runtime"
            set_context(session, actor=user["id"], tenant=tenant)
            sign_actor(session, user["id"])
            query = text("SELECT count(*) FROM public.knowledge_revisions WHERE id=:id")
            assert session.scalar(query, {"id": row["id"]}) == int(visible)
            with pytest.raises(DBAPIError) as denied, session.begin_nested():
                session.execute(text("UPDATE public.knowledge_revisions SET subject=subject WHERE id=:id"), {"id": row["id"]})
            assert denied.value.orig.sqlstate == "42501"
            assert not session.scalar(text("SELECT has_table_privilege(current_user,'public.knowledge_events','INSERT')"))
            assert not session.scalar(text("SELECT has_table_privilege(current_user,'public.knowledge_snapshots','DELETE')"))
            if visible:
                set_worker_scope(session, cid, bid, str(uuid4()))
                assert session.scalar(query, {"id": row["id"]}) == 0
    base = path.rsplit("/clients/", 1)[0]
    assert api.delete(base + "/members/" + client["id"] + "/client-scope", headers=owner["headers"]).status_code == 204
    assert api.get(path + "/revisions/" + row["id"], headers=client["headers"]).status_code == 404


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_concurrent_expected_revision_has_one_winner(api):
    owner = account(api, "CasOwner")
    path = scope(api, owner, "CAS")
    initial = revision(api, owner, path, "guide", "guidelines", {"guidance": "Initial"})

    def update(i):
        return call(
            api,
            owner,
            path,
            "/revisions",
            subject="guide",
            kind="guidelines",
            expected_revision=1,
            visibility="public",
            data={"guidance": "Candidate " + str(i)},
        )

    with ThreadPoolExecutor(2) as workers:
        outcomes = list(workers.map(update, range(2)))
    assert sorted(r.status_code for r in outcomes) == [201, 409]
    winner = next(r.json() for r in outcomes if r.status_code == 201)
    assert winner["revision"] == 2
    assert api.get(path + "/revisions/" + initial["id"], headers=owner["headers"]).json()["data"] == {"guidance": "Initial"}
    body = dict(key=uuid4().hex, subject="second", kind="guidelines", expected_revision=0, visibility="public", data={"guidance": "Replayed"})
    with ThreadPoolExecutor(2) as workers:
        both = list(workers.map(lambda _: call(api, owner, path, "/revisions", **body), range(2)))
    assert both[0].status_code == both[1].status_code == 201 and both[0].json() == both[1].json()


def test_second_qualified_approver(api):
    from knowledge_fixtures import bundle

    owner, path, source, _, _ = bundle(api)
    expert = account(api, "QualifiedAdmin")
    invite_member(api, "/api/tenants/" + owner["tenant"], owner["headers"], expert["headers"], email=expert["email"], role="admin")
    src_data = api.get(path + "/revisions/" + source["id"], headers=owner["headers"]).json()["data"]
    statement = src_data["entries"][0]["assertion"] | {"category": "comparison", "wording": "Comparison limited to the synthetic panel"}
    src_data["entries"][0].update(assertion=statement, excerpt=statement["wording"])
    evidence = revision(api, owner, path, "comparison", "source", src_data, visibility="restricted")
    bound = revision(api, owner, path, "scoped", "binding", {"source": evidence["id"], "locator": "row 2", "assertion": statement}, visibility="restricted")
    claim = revision(api, owner, path, "public-copy", "claim", {"binding": bound["id"], "assertion": statement}, approve=False)
    terms = dict(expected_digest=claim["digest"], expected_sequence=0, state="approved", reason="Comparison checked")
    transition = "/revisions/" + claim["id"] + "/events"
    assert call(api, expert, path, transition, **terms).status_code == 409
    mandate = revision(
        api,
        owner,
        path,
        "expert-comparison",
        "qualification",
        {
            "approver_id": expert["id"],
            "category": "comparison",
            "basis": "Internal appointment based on synthetic comparison review exercise",
            "valid_until": "2099-01-01T00:00:00Z",
        },
        visibility="restricted",
    )
    assert call(api, owner, path, transition, qualification_revision=mandate["id"], **terms).status_code == 409
    assert call(api, expert, path, transition, qualification_revision=mandate["id"], **terms).status_code == 200
    preview = accepted(call(api, expert, path, "/previews", claims=[claim["id"]]))
    assert "appointment" not in preview["canonical"] and evidence["id"] not in preview["canonical"] and "Synthetic lab" not in preview["canonical"]
    accepted(
        call(
            api, owner, path, f"/revisions/{mandate['id']}/events", state="withdrawn", expected_digest=mandate["digest"], expected_sequence=1, reason="Retired"
        )
    )
    assert call(api, expert, path, "/authorize", operation="queue", snapshot_id=preview["id"], digest=preview["digest"]).status_code == 409
