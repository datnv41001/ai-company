"""Marketing Studio retains each edited bundle and scopes it to an actual completed run."""

import pytest
from sqlalchemy.orm import Session

from app import c3_assets
from app.models import Deliverable
from app.workforce_models import WorkforceRun
from knowledge_fixtures import accepted
from test_c3_skill_library import projection
from test_workforce import workforce as workforce_fixture

workforce = workforce_fixture


@pytest.fixture
def studio_fixture(api, workforce):
    owner, assigned, other, base, _, scope, engine, brief = workforce
    with Session(engine) as db:
        doc = Deliverable(tenant_id=scope.tenant, campaign_id=scope.campaign, title="GB-6060", content={"client_preview": "GB-6060"}, created_by=owner["id"])
        db.add(doc)
        db.flush()
        p = projection("materials")
        for fact in p["facts"]:
            fact.setdefault("category", "description")
        p["task_intent"]["buyer_action"] = "rfq"
        run = WorkforceRun(
            tenant_id=scope.tenant,
            client_id=scope.client,
            brand_id=scope.brand,
            campaign_id=scope.campaign,
            brief_id=brief["id"],
            deliverable_id=doc.id,
            plan=[],
            budget_microusd=0,
            state="awaiting_qa",
            knowledge={"registry": {"workflow": c3_assets.LANDING}, "c3_projection": p, "sources": {}, "c3_manifest": {"id": "fixture", "digest": "f" * 64}},
        )
        db.add(run)
        db.commit()
        return owner, assigned, other, base + "/deliverables/" + doc.id, engine, run.id


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_studio_get_save_history_scope(api, studio_fixture):
    owner, assigned, other, doc, engine, rid = studio_fixture
    for client in (assigned, other):
        assert api.get(doc + "/studio", headers=client["headers"]).status_code == 404
        assert api.patch(doc + "/studio", headers=client["headers"], json={"expected_revision": 1, "groups": {}}).status_code == 404
    view = accepted(api.get(doc + "/studio", headers=owner["headers"]))
    assert view["version"] == "amc.marketing-studio/1" and view["mode"] == "proposal"
    assert set(view["groups"]) == {"copy", "seo"}
    assert "báo giá" in view["groups"]["copy"]["call_to_action"]
    changed = view["groups"]
    changed["copy"]["headline"] = "GB-6060 cho công trình"
    edit = {"expected_revision": view["revision"], "groups": changed}
    saved = accepted(api.patch(doc + "/studio", headers=owner["headers"], json=edit))
    assert saved["revision"] == view["revision"] + 1
    assert saved["history"][0]["groups"] == changed
    assert saved["preview"]["title"] == changed["copy"]["headline"]
    assert "meta_description" not in saved["preview"]["body"]
    assert api.patch(doc + "/studio", headers=owner["headers"], json=edit).status_code == 412
    risk = accepted(api.get(doc, headers=owner["headers"]))["qa_evidence"]["content_evidence"]
    assert any(s["field"] == "studio.copy.headline" for s in risk["statements"])
    with Session(engine) as db:
        doc_row = db.get(Deliverable, doc.rsplit("/", 1)[1])
        assert doc_row.content["studio"]["groups"] == changed


def test_strategy_requires_a_problem_position_and_distinct_measurement_steps():
    from app.c3_studio import compose, quality_issues

    p = projection("materials")
    p["task_intent"].update(audience="Chủ xưởng đồ gỗ", region="Bình Dương")
    groups = compose(c3_assets.RESEARCH, p)
    groups["research"]["buyer_problem"] = p["task_intent"]["audience"]
    groups["strategy"]["positioning"] = p["task_intent"]["region"] + "."
    clause = "Đếm số yêu cầu hợp lệ theo từng biểu mẫu"
    groups["measurement"]["measurement_method"] = f"{clause}, {clause}."
    issues = {row["field"]: row["reason"] for row in quality_issues(c3_assets.RESEARCH, groups, p)}
    assert issues["buyer_problem"] == issues["positioning"] == "entity_only"
    assert issues["measurement_method"] == "repetition"
    groups["measurement"]["measurement_method"] = clause + ", sau đó kiểm tra các yêu cầu trùng."
    assert "measurement_method" not in {row["field"] for row in quality_issues(c3_assets.RESEARCH, groups, p)}


def test_composer_explicit_control_and_distinct_strategy():
    from app.c3_studio import compose, quality_issues

    p = projection("materials")
    p["task_intent"]["buyer_action"] = "sample_request"
    strategy = compose(c3_assets.RESEARCH, p)
    assert set(strategy) == {"research", "strategy", "measurement"}
    assert strategy["strategy"]["execution"] and p["product"] in strategy["research"]["buyer_problem"]
    landing = compose(c3_assets.LANDING, p)
    assert "mẫu" in landing["copy"]["call_to_action"] and "PRIVATE" not in str(landing)
    assert "VND" in landing["copy"]["commercial_terms"]
    repeated = {"content": {"sections": {"headline": "Lặp đi lặp lại", "benefit": "Lặp đi lặp lại"}}}
    fields = compose(c3_assets.LANDING, p, repeated)
    assert any(row["reason"] == "repetition" for row in quality_issues(c3_assets.LANDING, fields, p))
    no_action = compose(c3_assets.LANDING, {**p, "task_intent": {}})
    assert no_action["copy"]["call_to_action"] == ""


@pytest.mark.parametrize("api", ["sqlite"], indirect=True)
def test_independent_asset_decisions_bind_to_one_submitted_revision(api, workforce, monkeypatch):
    from app import registry
    from c3_fixtures import prepared, capture
    from c3_task_fixtures import INTENT
    from knowledge_fixtures import revision
    from test_claim_desk import reader
    from test_c3_content_gate import approve
    from test_workforce import DATA

    owner, viewer, _, base, root, scope, engine, brief = workforce
    workflow = c3_assets.RESEARCH
    intent = INTENT | {"product": "Fabric sample", "audience": "Independent interior shops", "deliverable_type": "marketing_strategy"}
    accepted(api.put(root + "/briefs/" + brief["id"] + "/submission", headers=viewer["headers"], json=DATA | {"task_intent": intent}))
    state = prepared(api, owner, base, scope.client, scope.brand, scope.campaign, brief["id"], workflow)
    guide = revision(api, owner, state["path"], "voice", "guidelines", {"guidance": "Use plain words."})
    state["params"]["guidelines"] = guide["id"]
    snap = capture(api, owner, state)
    editor = reader(api, owner, "editor")
    binding = {"workflow": workflow, "manifest_digest": "e" * 64}
    # SQLite has no registry publisher. Only the worker association is seeded.
    monkeypatch.setattr(registry, "pin", lambda *args: binding)
    with Session(engine) as db:
        doc = Deliverable(
            tenant_id=scope.tenant, campaign_id=scope.campaign, title="Fabric sample", content={"client_preview": "Fabric sample"}, created_by=editor["id"]
        )
        db.add(doc)
        db.flush()
        path = base + "/deliverables/" + doc.id
        db.add(
            WorkforceRun(
                tenant_id=scope.tenant,
                client_id=scope.client,
                brand_id=scope.brand,
                campaign_id=scope.campaign,
                brief_id=brief["id"],
                deliverable_id=doc.id,
                plan=[],
                budget_microusd=0,
                state="awaiting_qa",
                knowledge={
                    "registry": binding,
                    "c3_projection": snap["projection"],
                    "sources": {},
                    "c3_manifest": {"id": snap["id"], "digest": snap["digest"]},
                },
            )
        )
        db.commit()
    studio = path + "/studio"
    proposal = accepted(api.get(studio, headers=editor["headers"]))
    groups = proposal["groups"]
    groups["research"]["hypothesis"] = "Test whether buyers prefer the matte finish."
    groups["measurement"]["measurable_action"] = snap["projection"]["product"]
    view = accepted(api.patch(studio, headers=editor["headers"], json={"groups": groups, "expected_revision": 1}))

    def sign(group, who=owner):
        return api.post(
            studio + "/approvals",
            headers=who["headers"],
            json={
                "group": group,
                "expected_revision": view["revision"],
                "expected_asset_digest": view["asset_digests"][group],
                "note": "Examined source, relevance and objective.",
            },
        )

    assert sign("research").status_code == 409
    submitted = accepted(api.post(path + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision": view["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    assert approve(api, path, owner, terms).status_code == 409
    assert sign("research", editor).status_code in (403, 404)
    assert sign("research").status_code == 409
    specialist = reader(api, owner, "admin")
    mandate = revision(
        api,
        owner,
        state["path"],
        "studio-content-qualification",
        "qualification",
        {"approver_id": specialist["id"], "category": "unclassified", "basis": "Synthetic materials specialist", "valid_until": "2099-01-01T00:00:00Z"},
        visibility="restricted",
    )
    report = accepted(api.get(studio, headers=specialist["headers"]))
    hypothesis = next(s for s in report["findings"] if s["field"] == "studio.research.hypothesis")
    assert hypothesis["outcome"] == "unresolved"
    handle = snap["projection"]["facts"][0]["id"]
    accepted(
        api.post(
            path + "/content-evidence/resolutions",
            headers=specialist["headers"],
            json=terms
            | {
                "statement_id": hypothesis["id"],
                "handle": handle,
                "qualification_revision": mandate["id"],
                "reason": "Matched the matte finish to the approved source. The wording proposes a test of preference.",
            },
        )
    )
    reopened = accepted(api.get(studio, headers=owner["headers"]))
    assert next(s for s in reopened["findings"] if s["id"] == hypothesis["id"])["outcome"] == "reviewed"
    for group in groups:
        signed = accepted(sign(group))
        assert signed["approvals"][group]["actor"] == owner["id"]
    assert accepted(sign("strategy"))["approvals"] == signed["approvals"]
    accepted(approve(api, path, owner, terms))
    changed = accepted(api.patch(studio, headers=editor["headers"], json={"groups": groups, "expected_revision": view["revision"]}))
    assert changed["revision"] > view["revision"] and not changed["approvals"]
    assert sign("strategy").status_code == 412


def test_material_format_uncertainty_requires_correction():
    from app.c3_content_evidence import classify

    p = projection("materials")

    def diagnose(text):
        return classify(text, p["facts"], [], set(), p, precise=True)[1:3]

    assert diagnose("Giảm giá 25%") == ("needs_correction", "unsupported_assertion")
    assert diagnose("Con số 42") == ("needs_correction", "unsupported_format")
    assert diagnose("SKU: XX-304") == ("contradiction", "product_identity")
    assert diagnose("Để xem " + p["sku"])[0] == "unresolved"


def test_explicit_photo_request_and_search_relevance():
    from app.c3_studio import compose, quality_issues

    p = projection("materials")
    p["task_intent"].update(buyer_action="rfq", buyer_input="photo")
    groups = compose(c3_assets.LANDING, p)
    assert groups["copy"]["call_to_action"] == "Yêu cầu báo giá. Gửi kèm ảnh."
    groups["seo"]["page_title"] = "Trải nghiệm nhà hàng Ý"
    assert {"group": "seo", "field": "page_title", "reason": "relevance"} in quality_issues(c3_assets.LANDING, groups, p)
