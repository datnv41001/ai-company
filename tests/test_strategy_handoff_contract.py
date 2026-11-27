"""Decision contract and minimal Content readback. Runtime authority is exercised with real sessions separately."""
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.c3_strategy_handoff import Decision, _recipient_decision, evaluate


def dossier():
    return {
        "F1": {"category": "description", "source_revision": "interview-v2", "locator": "interview-1/line-4",
               "research_spans": ["qa-span-1"], "positioning_spans": [],
               "excerpt": "One shift supervisor asked to see the belt change at handoff."},
        "F2": {"category": "description", "source_revision": "manual-v3", "locator": "sec-2",
               "research_spans": [], "positioning_spans": ["qa-span-2"],
               "complete_wording": "The belt is replaceable. Model A only.", "excerpt": "Replaceable belt for model A."},
        "F3": {"category": "description", "source_revision": "interview-v2", "locator": "interview-2/line-3",
               "research_spans": [], "positioning_spans": [], "excerpt": "One purchasing supervisor requested written ordering terms."},
    }


def request(**changes):
    values = dict(expected_revision=4, expected_content_digest="a"*64, qualification_revision="q"*36, recipient_id="r"*36,
                  option="explain_use", asset_type="web_use_guide", evidence_state="supported",
                  observation_kind="buyer_statement", observation_excerpt="asked to see the belt change",
                  support_handle="F1", product_handle="F2", interpretation="A demonstration may answer this question.",
                  buyer_persona="Shift supervisor", buying_situation="During the handoff", sample_limit="One interview at one shift.")
    return Decision.model_validate({**values, **changes})


def assess(body, references=None, *, placement="owned product page", strategy_placement=None, audience="Shift supervisor"):
    projection = dict(channel=placement, audience=audience, objective="Explain the approved model A procedure")
    return evaluate(body, references or dossier(), projection, {"channel_choice": strategy_placement or placement})


def test_new_observation_and_explicit_editorial_selection_preserve_original_product_declaration():
    reasons, original = assess(request())
    assert reasons == []
    new_revision = dossier()
    new_revision["F1"]["research_spans"] = []
    new_revision["F3"]["research_spans"] = ["qa-span-new"]
    reasons, revised = assess(request(option="explain_terms", support_handle="F3", asset_type="web_terms_panel",
                              observation_excerpt="requested written ordering terms", buyer_persona="Purchasing supervisor",
                              buying_situation="Preparing an order", interpretation="The written terms may help this buyer."),
                              new_revision, audience="Purchasing supervisor")
    assert reasons == []
    assert original["asset_type"] == "web_use_guide"
    assert revised["asset_type"] == "web_terms_panel"
    assert original["sources"]["observation"]["locator"] != revised["sources"]["observation"]["locator"]
    assert original["message"] == revised["message"] == dossier()["F2"]["complete_wording"]
    assert request().interpretation not in original["message"]
    assert original["claim_limits"][0] == request().sample_limit


@pytest.mark.parametrize(("changes", "reason"), [
    ({"contrary_handle": "F3"}, "conflicting_source"),
    ({"contrary_handle": "F3", "evidence_state": "conflicting"}, "contradictory_evidence"),
    ({"support_handle": None, "evidence_state": "insufficient"}, "missing_evidence"),
    ({"support_handle": None}, "missing_observation"),
    ({"product_handle": None}, "missing_product_fact"),
    ({"product_handle": "F1"}, "source_purpose_mismatch"),
    ({"buyer_persona": "Budget owner"}, "buyer_scope_mismatch"),
    ({"observation_excerpt": "All supervisors prefer this model"}, "observation_unverified"),
    ({"observation_kind": "hypothesis"}, "observation_unverified"),
    ({"evidence_state": "needs_clarification"}, "clarify_commission"),
    ({"option": "explain_terms"}, "asset_option_mismatch"),
    ({"asset_type": None}, "asset_required"),
    ({"recipient_id": None}, "recipient_required"),
])
def test_unanswered_authority_and_evidence_conditions_are_actionable_holds(changes, reason):
    reasons, order = assess(request(**changes))
    assert reason in reasons
    assert order is None


def test_reconfirming_counter_placement_does_not_transfer_a_product_page_asset():
    reasons, order = assess(request(), placement="owned counter card")
    assert reasons == ["asset_placement_mismatch"] and order is None
    reasons, order = assess(request(asset_type="counter_use_card"), placement="owned counter card")
    assert reasons == [] and order["asset_type"] == "counter_use_card"
    reasons, order = assess(request(asset_type="counter_use_card"), placement="owned counter card", strategy_placement="web")
    assert reasons == ["strategy_placement_mismatch"] and order is None


def test_price_record_and_duplicated_source_cannot_double_as_pinned_buyer_observation():
    refs = dossier()
    refs["F1"]["category"] = "price"
    assert assess(request(), refs) == (["observation_unverified"], None)
    refs["F1"].update(category="description", locator=refs["F2"]["locator"], source_revision=refs["F2"]["source_revision"])
    assert assess(request(), refs) == (["source_purpose_mismatch"], None)


def test_in_scope_but_unadopted_or_swapped_description_cannot_be_commissioned():
    refs = dossier()
    wrong_research = request(support_handle="F3", observation_excerpt=refs["F3"]["excerpt"])
    assert assess(wrong_research, refs) == (["observation_unverified"], None)
    assert assess(request(product_handle="F3"), refs) == (["source_purpose_mismatch"], None)
    swapped = request(support_handle="F2", product_handle="F1", observation_excerpt=refs["F2"]["excerpt"])
    assert assess(swapped, refs) == (["observation_unverified", "source_purpose_mismatch"], None)


def test_recipient_receives_approved_wording_without_upstream_editorial_material():
    body = request()
    reasons, order = assess(body)
    refs = dossier()
    receipt = SimpleNamespace(id="decision-7", actor="reviewer", effective_at=datetime.now(timezone.utc),
                              result=dict(request=body.model_dump(), work_order=order, reasons=reasons, selected_references=refs))
    view = _recipient_decision({"provenance": {"worker_proposals": "upstream only"}, "research": {"private": "notes"}}, receipt)
    assert view["decision"]["receipt_id"] == "decision-7"
    assert view["work_order"]["message"] == refs["F2"]["complete_wording"]
    assert "sources" not in view["work_order"] and view["research"] == {} and view["provenance"] == {}
    assert body.observation_excerpt not in str(view)
    assert "manual-v3" not in str(view) and body.qualification_revision not in str(view)
    assert view["measurement"]["execution_authorized"] is False


def test_injected_work_order_approval_or_scope_cannot_be_accepted_from_client():
    with pytest.raises(ValidationError):
        request(status="approved", sources={"F99": "private"}, work_order={"message": "unreviewed"})
