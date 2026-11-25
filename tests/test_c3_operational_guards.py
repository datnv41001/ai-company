"""C3 negative cases through normal staff/recipient API and durable pool leases."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from app import c3_marketing
from app.knowledge_contracts import price_wording
from app.knowledge_store import Store
from knowledge_fixtures import accepted, call, revision
from test_c3_authority import doc_and_decision, run_workers, setup_pool
from test_registry import PG, pool as registry_pool
from test_diamond import take_node
from test_workforce import DATA
from test_business_workspace import post

pool = registry_pool


@PG
def test_foreign_brand_campaign_and_membership(pool):
    lab = pool
    path, terms, data, _ = setup_pool(lab)
    api = lab.api
    base, admin, viewer, client, campaign = lab.cases[0]
    foreign = lab.cases[1]
    unrelated = data["marketing"].replace("/clients/" + client, "/clients/" + foreign[3])
    response = api.post(unrelated + "/manifests", headers=admin["headers"], json=data["params"])
    assert response.status_code == 404
    assert api.post(path, headers=viewer["headers"], json=terms).status_code == 404
    new_product = revision(api, admin, data["path"], "wrong-product", "product", {"name": "Another SKU", "sku": "WRONG"})
    wrong_brief = post(
        api,
        data["ui"] + "/briefs",
        admin,
        title="Different product",
        expected_revision=1,
        expected_company_revision=1,
        selections=data["selections"] | {"product": new_product["id"]},
    )
    assert (
        api.post(
            data["marketing"] + "/manifests", headers=admin["headers"], json=data["params"] | {"key": uuid4().hex, "workspace_brief_id": wrong_brief["id"]}
        ).status_code
        == 409
    )
    brand = data["path"].split("/")[-2]
    created = accepted(
        api.post(
            base + "/campaigns",
            headers=admin["headers"],
            json={"brand_id": brand, "name": "Different season", "brief": "Another internal campaign", "objective": "Engage other buyers"},
        )
    )
    new = accepted(
        api.post(
            base + "/workforce/briefs", headers=admin["headers"], json={"campaign_id": created["id"], "recipient_id": viewer["id"], "title": "Separate season"}
        )
    )
    api.put(base + "/workforce/briefs/" + new["id"] + "/submission", headers=viewer["headers"], json=DATA).raise_for_status()
    assert (
        api.post(
            data["marketing"] + "/manifests",
            headers=admin["headers"],
            json=data["params"] | {"key": uuid4().hex, "target": {"brief_id": new["id"], "campaign_id": created["id"]}},
        ).status_code
        == 409
    )
    api.delete(base + "/members/" + viewer["id"] + "/client-scope", headers=admin["headers"]).raise_for_status()
    assert api.post(path, headers=admin["headers"], json=terms).status_code in (404, 409)
    assert lab.owner.execute("select count(*) from workforce_runs where brief_id=%s", (path.split("/")[-2],)).fetchone() == (0,)


@PG
@pytest.mark.parametrize("reason", ["price_expiry", "disputed_stock", "revoked_qualification"])
def test_live_commercial_authority_after_queue(pool, monkeypatch, reason):
    lab = pool
    base, admin, *_ = lab.cases[0]
    today = datetime.now(timezone.utc)
    price = {
        "amount_minor": 25000,
        "currency": "VND",
        "unit": "piece",
        "basis_quantity": "1",
        "moq": "1",
        "tier_min": "1",
        "tier_max": None,
        "tax": "included",
        "conditions": [],
    }
    if reason == "price_expiry":
        fact = {
            "category": "price",
            "wording": price_wording(price),
            "price": price,
            "quantity": "1",
            "qualifiers": [],
            "offer_valid_until": (today + timedelta(days=2)).isoformat(),
        }
    elif reason == "disputed_stock":
        fact = {"category": "availability", "wording": "available", "qualifiers": []}
    else:
        fact = {"category": "description", "wording": "Prototype finish verified on the signed sample only", "qualifiers": []}
    path, terms, data, _ = setup_pool(lab, case={"facts": [fact]})
    rid = accepted(lab.api.post(path, headers=admin["headers"], json=terms))["id"]
    run_workers(lab, rid, c3_marketing.LANDING)
    doc, qa = doc_and_decision(lab, base, admin, rid)
    if reason == "price_expiry":
        # Advance the eligibility instant past only the offer; the 2099 source/mandate is still current.
        original = Store.now
        monkeypatch.setattr(Store, "now", lambda s: original(s) + timedelta(days=4))
    else:
        subject = "stock-0" if reason == "disputed_stock" else "mandate-0"
        rows = lab.owner.execute(
            "select id,digest from knowledge_revisions where brand_id=%s and subject=%s", (data["path"].split("/")[-2], subject)
        ).fetchall()
        assert len(rows) == 1
        key, signature = rows[0]
        accepted(
            call(
                lab.api,
                admin,
                data["path"],
                "/revisions/" + key + "/events",
                expected_sequence=1,
                expected_digest=signature,
                state="disputed" if reason == "disputed_stock" else "withdrawn",
                reason="Synthetic verification suspended",
            )
        )
    assert lab.api.post(doc + "/review", headers=admin["headers"], json=qa).status_code == 409


@PG
def test_lost_worker_offer_and_duplicate_queue(pool):
    from app.pool_worker import report

    lab = pool
    path, terms, data, snap = setup_pool(lab)
    base, owner, *_ = lab.cases[0]

    def submit(_):
        return accepted(lab.api.post(path, headers=owner["headers"], json=terms))["id"]

    with ThreadPoolExecutor(2) as executor:
        first, again = executor.map(submit, range(2))
    assert first == again
    old, job = take_node(lab)
    assert job["run"] == first
    lab.owner.execute("update workforce_runs set ready_at=now()-interval '1 second' where id=%s", (first,))
    assert not report(
        old.conn,
        job,
        [{"primary_assignment": "Expired lease cannot complete this stage.", "secondary_assignment": "Expired lease cannot create another plan."}, 100, 30],
    )
    assert lab.consume()
    lab.owner.execute("update workforce_runs set ready_at=now() where id=%s", (first,))
    run_workers(lab, first, c3_marketing.LANDING)
    assert lab.owner.execute("select count(*) from workforce_runs where brief_id=%s", (data["params"]["target"]["brief_id"],)).fetchone() == (1,)
    assert lab.owner.execute("select count(*) from deliverables where content->>'workforce_run_id'=%s", (first,)).fetchone() == (1,)
    assert lab.owner.execute("select count(*) from knowledge_commands where snapshot_id=%s and operation='c3_queue'", (snap["id"],)).fetchone() == (1,)
    finance = lab.owner.execute(
        "select count(*),count(distinct (l.id,l.event)),sum(l.held+l.spent) from amc_ops.ledger l join amc_ops.attempts a on a.id=l.id where a.run=%s", (first,)
    ).fetchone()
    assert finance[0] == finance[1] and finance[2] == 0


@PG
@pytest.mark.parametrize("stage", ["queue", "qa", "share"])
def test_revoked_device_cannot_act_when_session_api_installed(pool, stage):
    from test_claim_desk import reader

    lab = pool
    path, terms, data, snap = setup_pool(lab)
    base, admin, *_ = lab.cases[0]
    url, body = path, terms
    if stage in ("qa", "share"):
        rid = accepted(lab.api.post(path, headers=admin["headers"], json=terms))["id"]
        run_workers(lab, rid, c3_marketing.LANDING)
        doc, qa = doc_and_decision(lab, base, admin, rid)
        url, body = doc + "/review", qa
        if stage == "share":
            accepted(lab.api.post(url, headers=admin["headers"], json=body))
            url, body = (
                doc + "/share",
                {
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    "expected_qa_revision": qa["expected_qa_revision"],
                    "expected_content_digest": qa["expected_content_digest"],
                },
            )
    operator = reader(lab.api, admin, "admin")
    lab.api.post("/api/auth/logout", headers=operator["headers"]).raise_for_status()
    assert lab.api.post(url, headers=operator["headers"], json=body).status_code == 401
    assert lab.owner.execute("select count(*) from knowledge_commands where snapshot_id=%s and operation=%s", (snap["id"], "c3_" + stage)).fetchone() == (0,)
