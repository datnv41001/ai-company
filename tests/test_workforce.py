from contextlib import closing
from dataclasses import replace
from datetime import timedelta
from threading import Thread
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from agency_fixtures import account, create
from app.database import engine, get_db
from app.main import app
from app.models import utcnow
from app.workforce_gateway import CORE, EXTRA, Gateway, GatewayError, validate_output
from app.workforce_models import WorkforceRun
from app.workforce_worker import Scope, authorized_queue, claim, finish, process_one

LOCAL = Gateway("local", "fixture", "http://localhost/v1", 0, 0, 5)
DATA = {
    "objective": "Promote the A5 notebook",
    "audience": "University students",
    "offer": "See the notebook in store",
    "sources": [{"label": "Product card", "excerpt": "A5 notebook with 80 lined pages"}],
}


@pytest.fixture
def workforce(api, agency):
    owner, base, ((alice, a), (bob, b)) = agency
    staff = account(api, "WorkforceEditor")
    create(api, base + "/members", owner, {"email": staff["email"], "role": "editor"})
    client_id = next(iter(a["clients"]))
    brand = create(api, base + "/brands", owner, {"client_id": client_id, "name": "Paper Street", "product_truth": "80 lined pages"})
    campaign = create(
        api, base + "/campaigns", owner, {"brand_id": brand["id"], "name": "Launch", "brief": "Back to school launch", "objective": "Reach students"}
    )
    scope = Scope(owner["tenant"], client_id, brand["id"], campaign["id"], staff["id"])
    bind = engine
    if get_db in app.dependency_overrides:
        with closing(app.dependency_overrides[get_db]()) as gen:
            bind = next(gen).get_bind()
    root = base + "/workforce"
    brief = create(api, root + "/briefs", owner, {"campaign_id": campaign["id"], "recipient_id": alice["id"], "title": "Launch kit"})
    return owner, alice, bob, base, root, scope, bind, brief


def call_model(config, body):
    spec = body["response_format"]["json_schema"]
    out = {"text": "Draft notebook copy with 80 lined pages. Estimate 99 leads as a hypothesis. Giá phải chăng.", "source_ids": ["S1"]}
    out.update({k: out["text"] for k in spec["schema"]["properties"] if k not in ("assignments", "source_ids")})
    if spec["name"] == "director":
        roles = spec["schema"]["properties"]["assignments"]["required"]
        out["assignments"] = {k: "Create a launch plan for the notebook." for k in roles}
    return out, 90, 36


def submit_and_start(api, w, extra=(), budget=0):
    owner, alice, _, _, root, _, _, brief = w
    assert api.put(root + "/briefs/" + brief["id"] + "/submission", headers=alice["headers"], json=DATA).status_code == 200
    ready = api.post(root + "/briefs/" + brief["id"] + "/run", headers=owner["headers"], json={"extra_skills": list(extra), "budget_microusd": budget})
    assert ready.status_code == 200, ready.text
    return ready.json()["id"]


def test_brief_worker_and_approved_asset(api, workforce):
    owner, alice, bob, base, root, scope, bind, b = workforce
    assert api.get(root + "/briefs", headers=bob["headers"]).json() == []
    url = root + "/briefs/" + b["id"]
    assert api.put(url + "/submission", headers=bob["headers"], json=DATA).status_code == 404
    assert api.post(url + "/run", headers=owner["headers"], json={}).status_code == 409
    assert api.put(url + "/submission", headers=alice["headers"], json={**DATA, "audience": " "}).status_code == 422
    rid = submit_and_start(api, workforce, EXTRA)
    assert submit_and_start(api, workforce, EXTRA) == rid
    assert api.put(url + "/submission", headers=alice["headers"], json={**DATA, "offer": "changed afterwards"}).status_code == 409
    assert api.post(url + "/run", headers=alice["headers"], json={}).status_code == 404
    assert api.get(root + "/runs/" + rid, headers=alice["headers"]).status_code == 404
    for field in ("client", "brand", "campaign"):
        assert not process_one(bind, replace(scope, **{field: "wrong"}), LOCAL, call_model)
    with pytest.raises(PermissionError):
        process_one(bind, replace(scope, tenant=bob["tenant"]), LOCAL, call_model)
    for _ in CORE + EXTRA:
        assert process_one(bind, scope, LOCAL, call_model)
    assert not process_one(bind, scope, LOCAL, call_model)
    detail = api.get(root + "/runs/" + rid, headers=owner["headers"]).json()
    assert detail["state"] == "awaiting_qa" and detail["approved_assets"] == []
    assert [p["skill"] for p in detail["checkpoints"]] == CORE + EXTRA
    assert detail["checkpoints"][-1]["quality"]["numbers_for_qa"] == ["99"]
    assert all(j["input_tokens"] == 90 and j["estimated_microusd"] == 0 for j in detail["journal"])
    assert api.get(base + "/reviews", headers=alice["headers"]).json() == []
    path = base + "/deliverables/" + detail["deliverable_id"]
    draft = api.get(path, headers=owner["headers"]).json()
    assert any(f["claim"] == "Giá phải chăng." and f["status"] == "needs_evidence" for f in draft["content"]["qa_claims"])
    expiry = {"expires_at": (utcnow() + timedelta(days=1)).isoformat()}
    assert api.post(path + "/share", headers=owner["headers"], json=expiry).status_code == 409
    assert api.post(path + "/review", headers=owner["headers"], json={"decision": "approved"}).status_code == 200
    v = create(api, path + "/share", owner, expiry)
    customer_view = api.get(base + "/reviews/" + v["id"], headers=alice["headers"]).json()
    assert customer_view["digest"] == v["digest"] and "qa_claims" not in str(customer_view)
    assert "assignments" not in v["preview"] and "CONTENT" in v["preview"]
    assert api.get(base + "/reviews/" + v["id"], headers=bob["headers"]).status_code == 404
    api.put(base + f"/members/{alice['id']}/review-rights", headers=owner["headers"], json={"can_comment": True, "can_decide": True}).raise_for_status()
    decision = api.post(
        base + "/reviews/" + v["id"] + "/events", headers=alice["headers"], json={"kind": "approved", "digest": v["digest"], "request_key": uuid4().hex}
    )
    assert decision.status_code == 200
    assert api.get(root + "/runs/" + rid, headers=owner["headers"]).json()["approved_assets"] == [{"id": v["id"], "digest": v["digest"], "version": 1}]
    # Other identities cannot read artifacts after revocation even with an existing token.
    api.delete(base + f"/members/{alice['id']}/client-scope", headers=owner["headers"]).raise_for_status()
    assert api.get(base + "/reviews/" + v["id"], headers=alice["headers"]).status_code == 404


def make_due(db, scope, rid):
    run = db.scalar(authorized_queue(db, scope).where(WorkforceRun.id == rid))
    run.ready_at = utcnow() - timedelta(seconds=1)
    db.commit()


def test_checkpoint_fencing_retries_and_failure(api, workforce):
    owner, _, _, _, root, scope, bind, _ = workforce
    rid = submit_and_start(api, workforce)
    with Session(bind) as db:
        stale = claim(db, scope, LOCAL)
        make_due(db, scope, rid)
        recovered = claim(db, scope, LOCAL)
        assert stale[1] != recovered[1]
        assert not finish(db, scope, LOCAL, stale, call_model(LOCAL, stale[2]), None)
        db.rollback()
        assert finish(db, scope, LOCAL, recovered, call_model(LOCAL, recovered[2]), None)

    def timeout(*args):
        raise GatewayError("timeout")

    for _ in range(3):
        assert process_one(bind, scope, LOCAL, timeout)
        with Session(bind) as db:
            make_due(db, scope, rid)
    report = api.get(root + "/runs/" + rid, headers=owner["headers"]).json()
    assert report["state"] == "failed" and report["deliverable_id"] is None
    assert [j["outcome"] for j in report["journal"]] == ["lease_expired", "ok", "timeout", "timeout", "timeout"]
    assert [p["skill"] for p in report["checkpoints"]] == ["director"]


def test_budget_prevents_provider_call(api, workforce):
    owner, _, _, _, root, scope, bind, _ = workforce
    rid = submit_and_start(api, workforce)
    assert not process_one(bind, scope, replace(LOCAL, input_rate=1_000_000), lambda *_: pytest.fail("budget overrun"))
    assert api.get(root + "/runs/" + rid, headers=owner["headers"]).json()["last_error"] == "budget_exhausted"
    with pytest.raises(GatewayError, match="invalid_source"):
        validate_output({"text": "Invalid reference in this copy", "source_ids": ["other-client"]}, "content", CORE, {"S1": {}})


@pytest.mark.parametrize("api", ["postgres"], indirect=True)
def test_worker_pg_rls_and_competing_claims(api, workforce):
    _, _, bob, _, _, scope, bind, brief = workforce
    rid = submit_and_start(api, workforce)
    with Session(bind) as db:
        authorized_queue(db, replace(scope, campaign="wrong"))
        assert db.scalar(select(WorkforceRun).where(WorkforceRun.id == rid)) is None
        db.rollback()
        assert db.scalar(text("SELECT count(*) FROM workforce_runs")) == 0
        from app.access import set_context

        set_context(db, actor=bob["id"], tenant=scope.tenant)
        assert db.scalar(text("SELECT count(*) FROM workforce_briefs WHERE id=:id"), {"id": brief["id"]}) == 0
    results = []

    def race():
        with Session(bind) as db:
            results.append(claim(db, scope, LOCAL))

    jobs = [Thread(target=race) for _ in range(2)]
    for j in jobs:
        j.start()
    for j in jobs:
        j.join()
    assert len(results) == 2 and sum(t is not None for t in results) == 1


@pytest.mark.parametrize("withdrawal", ["remove", "rescope"])
def test_withdraw_during_provider_call_fences_result_and_retries(api, workforce, withdrawal):
    owner, alice, _, base, root, scope, bind, brief = workforce
    rid = submit_and_start(api, workforce, budget=100000)
    paid = replace(LOCAL, input_rate=1000000)

    # An open generation may already have incurred a charge. The callback models
    # a grant mutation committing before the provider response arrives.
    def inflight(config, body):
        if withdrawal == "remove":
            api.delete(base + f"/members/{alice['id']}/client-scope", headers=owner["headers"]).raise_for_status()
            api.post(
                base + "/members", headers=owner["headers"], json={"email": alice["email"], "role": "client_viewer", "client_id": scope.client}
            ).raise_for_status()
        else:
            other = create(api, base + "/brands", owner, {"client_id": scope.client, "name": "Second scope"})
            rights = base + f"/members/{alice['id']}/review-rights"
            api.put(rights, headers=owner["headers"], json={"brand_id": other["id"], "can_decide": False, "can_comment": False}).raise_for_status()
            api.put(rights, headers=owner["headers"], json={"brand_id": scope.brand, "can_decide": True, "can_comment": True}).raise_for_status()
        return call_model(config, body)

    assert process_one(bind, scope, paid, inflight)
    run = api.get(root + "/runs/" + rid, headers=owner["headers"]).json()
    assert (run["state"], run["last_error"], run["deliverable_id"], run["checkpoints"]) == ("failed", "recipient_revoked", None, [])
    assert len(run["journal"]) == 1 and run["journal"][0]["outcome"] == "recipient_revoked"
    assert run["journal"][0]["usage_unconfirmed"] is True
    assert run["reserved_microusd"] == run["journal"][0]["reserved_microusd"] > 0
    assert not process_one(bind, scope, paid, lambda *_: pytest.fail("revoked run retried"))
    assert api.post(root + "/briefs/" + brief["id"] + "/run", headers=owner["headers"], json={"budget_microusd": 100000}).json()["state"] == "failed"
    audit = api.get(base + "/audit", headers=owner["headers"]).json()
    assert sum(e["event"] == "workforce.recipient_revoked" and e["subject_id"] == rid for e in audit) == 1


def test_queued_withdrawal_and_unrelated_grant_edit(api, workforce):
    owner, alice, bob, base, root, scope, bind, _ = workforce
    rid = submit_and_start(api, workforce)
    api.delete(base + f"/members/{bob['id']}/client-scope", headers=owner["headers"]).raise_for_status()
    api.put(
        base + f"/members/{alice['id']}/review-rights", headers=owner["headers"], json={"brand_id": scope.brand, "can_comment": False, "can_decide": False}
    ).raise_for_status()
    assert api.get(root + "/runs/" + rid, headers=owner["headers"]).json()["state"] == "queued"
    api.delete(base + f"/members/{alice['id']}/client-scope", headers=owner["headers"]).raise_for_status()
    assert not process_one(bind, scope, LOCAL, lambda *_: pytest.fail("revoked job reached provider"))
    run = api.get(root + "/runs/" + rid, headers=owner["headers"]).json()
    assert run["last_error"] == "recipient_revoked" and run["journal"] == [] and run["reserved_microusd"] == 0


def test_evidence_uses_only_cited_complete_sentences():
    from app.workforce_evidence import assess

    sources = {"S1": {"excerpt": "Bút màu xanh. Không phải giá rẻ."}, "S2": {"excerpt": "Bút rẻ nhất."}}
    result = assess({"source_ids": ["S1"], "sections": {"body": "Bút rẻ nhất. Được chuyên gia khuyên dùng. Chất lượng hàng đầu."}}, sources)
    assert [c["categories"] for c in result["claims"]] == [["price"], ["endorsement"], ["superiority"]]
    assert all(c["status"] == "needs_evidence" and not c["matching_ids"] for c in result["claims"])
    quote = assess({"source_ids": ["S2"], "sections": {"body": "Bút rẻ nhất."}}, sources)["claims"][0]
    assert quote["status"] == "source_quote" and quote["matching_ids"] == ["S2"]
    assert assess({"source_ids": ["S1"], "sections": {"body": "Bút màu xanh."}}, sources)["claims"] == []


def test_missing_budget_rejects_even_when_worker_secret_is_configured(api, workforce, monkeypatch, tmp_path):
    owner, _, _, _, root, scope, bind, _ = workforce
    key = tmp_path / "worker_key"
    key.write_text("synthetic-only")
    for k, v in {
        "AMC_WORKER_KEY_FILE": str(key),
        "AMC_WORKFORCE_PROVIDER": "openai",
        "AMC_WORKFORCE_MODEL": "test",
        "AMC_INPUT_RATE_MICROUSD": "1000000",
        "AMC_OUTPUT_RATE_MICROUSD": "1000000",
    }.items():
        monkeypatch.setenv(k, v)
    rid = submit_and_start(api, workforce, budget=0)
    assert not process_one(bind, scope, Gateway.configured(), lambda *_: pytest.fail("called paid gateway"))
    assert api.get(root + "/runs/" + rid, headers=owner["headers"]).json()["last_error"] == "budget_exhausted"
