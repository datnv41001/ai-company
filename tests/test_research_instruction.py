"""Internal planning classification and the signed delivery boundary on synthetic commissions."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agency_fixtures import postgres_api
from app.c3_research_instruction import eligible_span
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from strategy_runtime_fixtures import INTENT, OBSERVATION, PRODUCT, commission_lab, studio_save

EN = "What did you do immediately before your last purchase?"
EN_STEP = "Show the step or document you used."
VI = "Ngay trước lần mua gần nhất, bạn đã làm gì?"
VI_STEP = "Hãy chỉ ra bước hoặc tài liệu bạn đã sử dụng."


def record(name, data):
    if path := os.environ.get("AMC_RES_QA_EVIDENCE"):
        folder = Path(path)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (name + ".json")).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


@pytest.mark.parametrize("locale,sentence", [
    ("en-US", "How did we reduce your time by 30%?"), ("vi-VN", "Bạn đã tiết kiệm 30% thời gian như thế nào?"),
    ("en-US", "Why did your customers request automatic tracking?"), ("vi-VN", "Vì sao khách hàng đã yêu cầu theo dõi tự động?"),
    ("en-US", "How did next-day delivery help?"), ("vi-VN", "Giao ngày mai có giúp bạn không?"),
    ("en-US", "Would the $20 price or MOQ of one work?"), ("vi-VN", "Giá 20 USD và MOQ một hộp có phù hợp?"),
    ("en-US", "When did the carrier confirm the slot?"), ("vi-VN", "Hãng vận tải đã xác nhận khung giờ khi nào?"),
    ("en-US", "Show the step or document you used at private locator."), ("vi-VN", "Gửi dữ liệu riêng sang bộ phận ngoài phạm vi."),
])
def test_free_text_cannot_be_classified(locale, sentence):
    row = dict(field="studio.research.research_question", outcome="unresolved", claim_type="unclassified", reason="unsupported", handles=[], text=sentence)
    assert not eligible_span(row, {"locale":locale})
    for field in ("client_preview", "studio.strategy.positioning", "studio.client_strategy.message"):
        assert not eligible_span({**row, "text": EN if locale == "en-US" else VI, "field": field}, {"locale":locale})


def submit(api, ctx, question, *, positioning=PRODUCT, problem=OBSERVATION, use_controls=False):
    owner = ctx["author"]["headers"]
    view = accepted(api.get(ctx["studio"], headers=owner))
    groups = {k:view["suggestions"][k] for k in view["groups"]} if use_controls else view["groups"]
    groups["research"].update(research_question=question, buyer_problem=problem)
    groups["strategy"].update(positioning=positioning, channel_choice="web")
    saved = studio_save(api, ctx, groups)
    accepted(api.post(ctx["doc"] + "/submit", headers=owner))
    report = accepted(api.get(ctx["doc"] + "/content-evidence", headers=ctx["reviewer"]["headers"]))
    return saved, report


def request_body(ctx, report, row):
    return dict(statement_id=row["id"], qualification_revision=ctx["mandate"]["id"], expected_qa_revision=report["qa_revision"],
                expected_content_digest=report["content_digest"], reason="Neutral interview procedure for internal planning only.")


def sign(api, ctx, saved, group):
    return api.post(ctx["studio"] + "/approvals", headers=ctx["reviewer"]["headers"], json={
        "group": group, "expected_revision": saved["revision"], "expected_asset_digest": saved["asset_digests"][group],
        "note": "Check research procedure and evidence independently."})


pg = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Requires authorized synthetic PostgreSQL roles")


@pg
@pytest.mark.parametrize("locale,question,step,revoke", [
    ("en-US","At the last handover, what did you try to find immediately before using or putting aside the tray?", EN_STEP,"source"),
    ("vi-VN", VI, VI_STEP, "mandate"),
])
def test_scoped_classification(api_for_research, locale, question, step, revoke):
    api = api_for_research
    with commission_lab(api, intent={**INTENT, "locale":locale}) as ctx:
        saved, view = submit(api, ctx, question + " " + step)
        path = ctx["doc"] + "/content-evidence"
        endpoint = path + "/research-instructions"
        qa = ctx["reviewer"]["headers"]
        rows = [s for s in view["statements"] if s.get("instruction_review_available")]
        assert [s["text"] for s in rows] == [question, step]
        body = request_body(ctx, view, rows[0])
        assert sign(api, ctx, saved, "research").status_code == 409
        assert api.post(endpoint, headers=ctx["owner"]["headers"], json=body).status_code == 403
        for field in ("tenant_id", "client_id", "brand_id", "campaign_id", "manifest_id", "text", "purpose"):
            assert api.post(endpoint, headers=qa, json=body | {field:"different"}).status_code == 422
        assert api.post(endpoint, headers=qa, json=body | {"qualification_revision":ctx["state"]["sources"][0]["id"]}).status_code == 409
        assert api.post(path + "/resolutions", headers=qa, json=body | {"handle":"F1"}).status_code == 409
        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = [pool.submit(api.post, endpoint, headers=qa, json=body) for _ in range(2)]
            receipts = [accepted(f.result(timeout=20)) for f in replies]
        assert receipts[0] == receipts[1] and receipts[0]["reviewer"] == ctx["reviewer"]["id"]
        assert api.post(endpoint, headers=qa, json=body | {"reason":"A different justification for the same span."}).status_code == 409
        assert sign(api, ctx, saved, "research").status_code == 409
        second = accepted(api.post(endpoint, headers=qa, json=request_body(ctx, view, rows[1])))
        report = accepted(api.get(path, headers=qa))
        classified = [s for s in report["statements"] if s["reason"] == "signed_research_instruction"]
        assert len(classified) == 2 and all(s["outcome"] == "editorial" and s["sources"] == s["handles"] == [] for s in classified)
        assert len([d for d in report["decisions"] if d.get("contract") == second["contract"]]) == 2
        assert sign(api, ctx, saved, "research").status_code == 200
        held = accepted(api.get(ctx["studio"] + "/content-handoff", headers=ctx["recipient"]["headers"]))
        assert held["work_order"] is None and not held["references"]
        assert question not in json.dumps(held, ensure_ascii=False)
        before = [s["resolution_id"] for s in classified]
        record(locale, {"scope":ctx["scope"], "receipts":[receipts[0], second], "resolution_ids":before, "recipient":held["status"]})
        if revoke == "mandate":
            accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
        else:
            accepted(withdraw(api, ctx["owner"], ctx["state"]))
        after = accepted(api.get(path, headers=qa))
        assert not any(s["reason"] == "signed_research_instruction" for s in after["statements"])
        assert api.post(endpoint, headers=qa, json=body).status_code == 409


@pytest.fixture
def api_for_research():
    with postgres_api() as api:
        yield api


@pg
def test_final_qa_keeps_plan_decisions_separate_from_evidence(api_for_research):
    api = api_for_research
    with commission_lab(api) as ctx:
        saved, report = submit(api, ctx, EN, use_controls=True)
        qa = ctx["reviewer"]["headers"]
        path = ctx["doc"] + "/content-evidence"
        row = next(s for s in report["statements"] if s.get("instruction_review_available"))
        accepted(api.post(path + "/research-instructions", headers=qa, json=request_body(ctx, report, row)))
        for group in ("research","strategy","measurement"):
            accepted(sign(api, ctx, saved, group))
        accepted(api.post(ctx["doc"] + "/review", headers=qa, json={"decision":"approved","note":"Approved these scoped internal groups.",
            "expected_qa_revision":saved["revision"],"expected_content_digest":report["content_digest"]}))
        history = accepted(api.get(path, headers=qa))
        proof = next(d for d in history["decisions"] if d["operation"]=="c3_qa")
        receipt_id = next(s["resolution_id"] for s in history["statements"] if s["id"]==row["id"])
        assert proof["internal_research_instructions"]["receipts"] == {row["id"]:receipt_id}
        assert row["id"] not in proof["reviewed_statements"]
        downstream = accepted(api.get(ctx["studio"]+"/content-handoff",headers=ctx["recipient"]["headers"]))
        assert downstream["work_order"] is None and not downstream["references"]


@pg
@pytest.mark.parametrize("locale,sentences", [
    ("en-US", [EN, "Why did customers request automatic tracking?", "How did we save 30%?", "Will the MOQ be one?",
               "Can we guarantee next-day delivery?", "Send private locator to the other brand."]),
    ("vi-VN", [VI, "Vì sao khách đã yêu cầu thêm tính năng?", "Bạn đã tiết kiệm 30% ra sao?", "Giá 20 USD có phù hợp?",
               "Chúng tôi chắc chắn giao hàng ngày mai?", "Gửi private locator sang nhãn hiệu khác."]),
])
def test_mixed_field_does_not_waive_neighboring_claims(api_for_research, locale, sentences):
    api = api_for_research
    with commission_lab(api, intent=INTENT | {"locale":locale}) as ctx:
        saved, view = submit(api, ctx, " ".join(sentences))
        qa = ctx["reviewer"]["headers"]
        endpoint = ctx["doc"] + "/content-evidence/research-instructions"
        spans = [s for s in view["statements"] if s["field"] == "studio.research.research_question"]
        assert [s["text"] for s in spans] == sentences
        accepted(api.post(endpoint, headers=qa, json=request_body(ctx, view, spans[0])))
        for span in spans[1:]:
            assert not span.get("instruction_review_available")
            assert api.post(endpoint, headers=qa, json=request_body(ctx, view, span)).status_code == 409
        assert sign(api, ctx, saved, "research").status_code == 409


@pg
def test_mixed_revision_and_foreign_document(api_for_research):
    api = api_for_research
    with commission_lab(api) as ctx, commission_lab(api) as other:
        saved, report = submit(api, ctx, EN + " Customers demanded automatic tracking.")
        path = ctx["doc"] + "/content-evidence/research-instructions"
        qa = ctx["reviewer"]["headers"]
        neutral, claim = [s for s in report["statements"] if s["field"] == "studio.research.research_question"]
        body = request_body(ctx, report, neutral)
        accepted(api.post(path, headers=qa, json=body))
        assert api.post(path, headers=qa, json=request_body(ctx, report, claim)).status_code == 409
        assert sign(api, ctx, saved, "research").status_code == 409
        _, other_report = submit(api, other, EN)
        other_path = other["doc"] + "/content-evidence/research-instructions"
        other_row = next(s for s in other_report["statements"] if s.get("instruction_review_available"))
        other_body = request_body(other, other_report, other_row)
        assert api.post(other_path, headers=qa, json=other_body).status_code in (403,404)
        assert api.post(other_path, headers=other["reviewer"]["headers"], json=other_body | {"statement_id":neutral["id"]}).status_code == 409
        assert api.post(other_path, headers=other["reviewer"]["headers"], json=other_body | {"qualification_revision":ctx["mandate"]["id"]}).status_code in (404,409)
        _, fresh = submit(api, ctx, EN + " Customers demanded automatic tracking.")
        assert fresh["qa_revision"] > report["qa_revision"]
        assert api.post(path, headers=qa, json=body).status_code == 412
        assert not any(s.get("resolution_id") for s in fresh["statements"])
        accepted(api.patch(ctx["doc"] + "/draft", headers=ctx["author"]["headers"], json={"title":"Internal plan", "client_preview":EN}))
        accepted(api.post(ctx["doc"] + "/submit", headers=ctx["author"]["headers"]))
        public = accepted(api.get(ctx["doc"] + "/content-evidence", headers=qa))
        preview = next(s for s in public["statements"] if s["field"] == "client_preview" and s["text"] == EN)
        assert api.post(path, headers=qa, json=request_body(ctx, public, preview)).status_code == 409


@pg
@pytest.mark.parametrize("variant,promise", [
    ("delivery", "The modular rack ensures quick delivery to the requested site window."),
    ("delivery-speed", "The modular rack guarantees rapid arrival."),
])
def test_delivery_worker_promise_stops_before_signature(api_for_research, variant, promise):
    api = api_for_research
    product = "The rack is delivered flat packed."
    form = "The quote form accepts a site window and access note."
    qualifier = "Carrier availability requires written confirmation; unloading is excluded."
    facts = [dict(wording=t, qualifiers=[qualifier], excerpt=t+" "+qualifier) for t in (product, form)]
    intent = {**INTENT, "product":"Modular rack R7", "buyer_action":"rfq", "audience":"Warehouse buyers",
              "purpose":"Request a delivery-window quote.", "requirements":["Keep carrier and unloading conditions."],
              "exclusions":["Customer contact"], "acceptance_criteria":["Maintain all delivery conditions in the proposal."]}
    with commission_lab(api, intent=intent, observation=form, product_statement=product, source_facts=facts,
                        controlled={"strategy":{"positioning":promise, "rationale":"Compare the information required for a quote."}}) as ctx:
        if variant == "delivery":
            projection = ctx["snap"]["projection"]
            key = next(f["id"] for f in projection["facts"] if f["wording"] == form)
            record("development", {"projection":projection,"reply":{
                "segment":"Warehouse buyer arranging inbound delivery.",
                "buyer_problem":"H1: missing access details delay an RFQ. H2: uncertainty about carrier confirmation delays it.",
                "research_question":"At the last quote request, which detail did you seek first, and where did you look?",
                "evidence_needed":"With permission inspect two synthetic walkthroughs. Access first in both: test an access checklist. Timing first in both: clarify written confirmation. Mixed or missing: hold for owner.",
                "source_ids":[key]}})
        qa = ctx["reviewer"]["headers"]
        original = accepted(api.get(ctx["studio"], headers=ctx["author"]["headers"]))
        assert original["groups"]["strategy"]["positioning"] == ctx["raw"]["strategy"]["positioning"] == promise
        saved, report = submit(api, ctx, EN + " " + product, positioning=promise, problem=form+" "+qualifier)
        assert not any(i["group"] == "strategy" for i in saved["quality_issues"])
        row = next(s for s in report["statements"] if s["field"]=="studio.strategy.positioning" and s["text"]==promise)
        assert row["outcome"] in ("unresolved","contradiction","needs_correction") and not row.get("instruction_review_available")
        body = request_body(ctx, report, row)
        incomplete = next(s for s in report["statements"] if s["field"]=="studio.research.research_question" and s["text"]==product)
        assert incomplete["reason"] == "missing_qualifier"
        assert api.post(ctx["doc"]+"/content-evidence/research-instructions", headers=qa, json=request_body(ctx, report, incomplete)).status_code == 409
        assert api.post(ctx["doc"]+"/content-evidence/research-instructions", headers=qa, json=body).status_code == 409
        for handle in (f["id"] for f in ctx["snap"]["projection"]["facts"]):
            assert api.post(ctx["doc"]+"/content-evidence/resolutions", headers=qa, json=body | {"handle":handle}).status_code == 409
        assert sign(api, ctx, saved, "strategy").status_code == 409
        decision = api.post(ctx["doc"] + "/review", headers=qa, json={"decision":"approved","note":"Verify synthetic delivery claim.",
            "expected_qa_revision":saved["revision"],"expected_content_digest":report["content_digest"]})
        assert decision.status_code == 409
        handoff = accepted(api.get(ctx["studio"] + "/content-handoff", headers=ctx["recipient"]["headers"]))
        assert handoff["work_order"] is None and not handoff["references"]
        assert promise not in saved["preview"]["body"]
        record(variant,{"scope":ctx["scope"],"brief":ctx["task"]["id"],"action":ctx["snap"]["projection"]["task_intent"]["buyer_action"],
               "manifest":ctx["snap"]["id"],"manifest_digest":ctx["snap"]["digest"],"run":ctx["run"]["id"],"source_facts":ctx["snap"]["projection"]["facts"],
               "attempt":ctx["requests"]["strategy"]["completed_attempt_id"],"worker_positioning":promise,"studio_positioning":saved["groups"]["strategy"]["positioning"],
               "structural":saved["quality_issues"],"statement":row,"revision":saved["revision"],"digest":report["content_digest"],
               "strategy_signature":409,"document_approval":decision.status_code,"preview":saved["preview"]["body"],"work_order":None})
