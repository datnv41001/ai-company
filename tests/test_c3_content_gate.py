"""The editor, independent QA and client exercise the actual content decision APIs."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app import c3_marketing, registry
from app.knowledge_contracts import price_wording
from app.models import Deliverable
from app.workforce_models import WorkforceRun
from c3_fixtures import capture, prepared
from knowledge_fixtures import accepted, revision
from test_c3_authority import doc_and_decision, run_workers, setup_pool
from test_registry import PG, pool as registry_pool
from test_workforce import DATA, workforce as workforce_fixture


workforce = workforce_fixture
pool = registry_pool
PRICE = dict(amount_minor=210000, currency="VND", unit="m²", basis_quantity="1", moq="50", tier_min="50", tier_max=None, tax="included", conditions=[])
FACTS = [
    {"wording": "Matte surface", "qualifiers": ["Indoor use only"]},
    {"wording": price_wording(PRICE), "category": "price", "price": PRICE, "quantity": "50", "qualifiers": []},
]
EXAMPLES = [
    ("Giảm giá 25% với mã ưu đãi. [F1]", "commercial_terms"),
    ("Giá 120.000 VND/m². [F1]", "commercial_terms"),
    ("Giao hàng trên toàn quốc. [F1]", "geography"),
    ("Matte surface", "missing_qualifier"),
    ("[F1] Lasts longer than every competing product.", "unsupported"),
]


@pytest.fixture
def content_lab(api, workforce, monkeypatch):
    """SQLite has no registry publisher; install the genuine worker association only in this in-memory fixture.

    The pinned source declarations, edit, qualification, gate, review and share all use ordinary APIs.
    The PostgreSQL acceptance below also executes the real registry worker.
    """
    owner, viewer, _, base, root, scope, engine, brief = workforce
    assert engine.dialect.name == "sqlite"
    approved = {"workflow": c3_marketing.LANDING, "manifest_digest": "e" * 64}
    monkeypatch.setattr(registry, "pin", lambda *args: approved)
    accepted(api.put(root + "/briefs/" + brief["id"] + "/submission", headers=viewer["headers"], json=DATA))
    data = prepared(api, owner, base, scope.client, scope.brand, scope.campaign, brief["id"], case={"facts": FACTS})
    snap = capture(api, owner, data)
    from test_claim_desk import reader

    editor = reader(api, owner, "editor")
    with Session(engine) as db:
        doc = Deliverable(tenant_id=owner["tenant"], campaign_id=scope.campaign, title="Fabric sample", content={}, created_by=editor["id"])
        db.add(doc)
        db.flush()
        path = base + "/deliverables/" + doc.id
        run = WorkforceRun(
            tenant_id=owner["tenant"],
            client_id=scope.client,
            brand_id=scope.brand,
            campaign_id=scope.campaign,
            brief_id=brief["id"],
            deliverable_id=doc.id,
            plan=[],
            budget_microusd=0,
            knowledge={"registry": approved, "c3_projection": snap["projection"], "sources": {}, "c3_manifest": {"id": snap["id"], "digest": snap["digest"]}},
        )
        db.add(run)
        db.commit()
    return owner, viewer, editor, path, data, snap


def submit_copy(api, path, editor, body):
    accepted(api.patch(path + "/draft", headers=editor["headers"], json={"title": "Fabric sample", "client_preview": body}))
    doc = accepted(api.post(path + "/submit", headers=editor["headers"]))
    return {"expected_qa_revision": doc["qa_revision"], "expected_content_digest": doc["qa_evidence"]["content_digest"]}


def approve(api, path, actor, terms):
    return api.post(path + "/review", headers=actor["headers"], json=dict(terms, decision="approved", note="Examined selected revision"))


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_content_contradictions_through_api(api, content_lab):
    owner, _, editor, path, _, snap = content_lab
    # Collect all RED responses before checking the new field, so the pre-amend failure identifies every accepted example.
    responses = []
    for statement, _ in EXAMPLES:
        terms = submit_copy(api, path, editor, statement)
        responses.append(approve(api, path, owner, terms).status_code)
    assert responses == [409] * len(EXAMPLES)
    for statement, reason in EXAMPLES:
        terms = submit_copy(api, path, editor, statement)
        gate = accepted(api.get(path + "/content-evidence", headers=owner["headers"]))
        row = next(r for r in gate["statements"] if r["field"] == "client_preview")
        assert row["reason"] == reason and row["text"] == statement[row["start"] : row["end"]]
        assert row["outcome"] in ("contradiction", "unresolved") and not gate["ready"]
        assert approve(api, path, owner, terms).status_code == 409
    body = "\n".join(c3_marketing.fact_line(fact) for fact in snap["projection"]["facts"])
    terms = submit_copy(api, path, editor, body)
    accepted(approve(api, path, owner, terms))
    expiry = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    shared = accepted(api.post(path + "/share", headers=owner["headers"], json=terms | {"expires_at": expiry}))
    assert shared["preview"] == body


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_qualified_resolution_is_scoped_to_a_save_and_rechecked_at_share(api, content_lab):
    from test_claim_desk import reader
    from knowledge_fixtures import call
    from agency_fixtures import account

    owner, viewer, editor, path, data, snap = content_lab
    qa = reader(api, owner, "admin")
    mandate = revision(
        api,
        owner,
        data["path"],
        "content-mandate",
        "qualification",
        {"approver_id": qa["id"], "category": "unclassified", "basis": "Synthetic product materials reviewer", "valid_until": "2099-01-01T00:00:00Z"},
        visibility="restricted",
    )
    handle = next(f["id"] for f in snap["projection"]["facts"] if f["wording"] == "Matte surface")
    # The qualification belongs to one exact assertion including its conditions. A second
    # unrelated sentence requires its own decision. Keep this paraphrase in one sentence.
    copy = f"[{handle}] A matte finish for this sample — Indoor use only"
    terms = submit_copy(api, path, editor, copy)
    report = accepted(api.get(path + "/content-evidence", headers=qa["headers"]))
    assert not report["ready"] and report["qualifications"]
    assert len(report["references"][handle]["source_digest"]) == 64
    row = next(r for r in report["statements"] if r["outcome"] == "unresolved")
    values = terms | {
        "handle": handle,
        "statement_id": row["id"],
        "qualification_revision": mandate["id"],
        "reason": "Compared the paraphrase with the signed matte finish declaration; the indoor limit remains.",
    }
    endpoint = path + "/content-evidence/resolutions"
    assert api.post(endpoint, headers=editor["headers"], json=values).status_code in (403, 404)
    assert api.post(endpoint, headers=owner["headers"], json=values).status_code == 409
    accepted(api.post(endpoint, headers=qa["headers"], json=values))
    accepted(api.post(endpoint, headers=qa["headers"], json=values))
    updated = accepted(api.get(path + "/content-evidence", headers=qa["headers"]))
    assert updated["ready"] and len(updated["decisions"]) == 1
    archived = updated["revisions"][0]["id"]
    for outsider in (viewer, account(api, "OtherCompany")):
        assert api.get(path + "/content-evidence", headers=outsider["headers"]).status_code in (403, 404)
    public = accepted(api.get(path + "/content-evidence", headers=editor["headers"]))
    assert "PRIVATE_SYNTHETIC" not in str(public) and "source_revision" not in str(public)
    assert api.get(path + "/content-evidence/history/" + archived, headers=editor["headers"]).status_code in (403, 404)
    accepted(approve(api, path, owner, terms))
    accepted(
        call(
            api,
            owner,
            data["path"],
            "/revisions/" + mandate["id"] + "/events",
            expected_digest=mandate["digest"],
            expected_sequence=1,
            state="withdrawn",
            reason="Synthetic qualification withdrawn",
        )
    )
    assert (
        api.post(
            path + "/share", headers=owner["headers"], json=terms | {"expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
        ).status_code
        == 409
    )
    submit_copy(api, path, editor, "Matte surface")
    again = submit_copy(api, path, editor, copy)
    assert again["expected_content_digest"] == terms["expected_content_digest"] and again["expected_qa_revision"] > terms["expected_qa_revision"]
    assert api.post(endpoint, headers=qa["headers"], json=values).status_code == 412
    assert approve(api, path, owner, again).status_code == 409
    old = accepted(api.get(path + "/content-evidence/history/" + archived, headers=owner["headers"]))
    assert any(s["text"] == copy and s["outcome"] == "unresolved" for s in old["assessment"]["statements"])
    assert old["references"][handle]["source_revision"] == updated["references"][handle]["source_revision"]


def test_new_assertions_are_not_layout_or_editorial_advice():
    from app.c3_content_evidence import classify

    projection = {"region": "HN", "brand_guidelines": {"prohibited_claims": ["khỏi bệnh"]}, "task_intent": {"exclusions": ["suất cuối"]}}
    for text, reason in (
        ("Hàng có tại Đà Nẵng", "geography"),
        ("Đặt qua mọi kênh", "channel"),
        ("SKU XYZ", "product_identity"),
        ("Cam kết khỏi bệnh", "prohibited"),
        ("Chỉ còn suất cuối", "prohibited"),
        ("Áp dụng từ 2 hộp", "commercial_terms"),
    ):
        assert classify(text, [], [], set(), projection)[1:3] == ("contradiction", reason)


@PG
def test_published_content_gate(pool):
    lab = pool
    path, terms, _, snap = setup_pool(lab, case={"facts": FACTS})
    base, owner, _, _, _ = lab.cases[0]
    rid = accepted(lab.api.post(path, headers=owner["headers"], json=terms))["id"]
    run_workers(lab, rid, c3_marketing.LANDING)
    doc, _ = doc_and_decision(lab, base, owner, rid)
    from test_claim_desk import reader

    editor = reader(lab.api, owner, "editor")
    for statement, _ in EXAMPLES:
        revision_terms = submit_copy(lab.api, doc, editor, statement)
        assert approve(lab.api, doc, owner, revision_terms).status_code == 409
    body = "\n".join(c3_marketing.fact_line(fact) for fact in snap["projection"]["facts"])
    revision_terms = submit_copy(lab.api, doc, editor, body)
    accepted(approve(lab.api, doc, owner, revision_terms))
