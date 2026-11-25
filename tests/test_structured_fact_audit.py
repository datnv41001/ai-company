"""Offline render-audit regression cases. All content here is synthetic and authored for these tests."""

from copy import deepcopy
import json

import pytest

from evaluation.c3 import structured_fact_audit as audit


LINE = "Giá tham khảo: 150.000 VND / 1 lượt, đã gồm thuế. Đơn tối thiểu: 2 lượt. Áp dụng từ 2 lượt đến 4 lượt. Số lượng đối chiếu: 3 lượt. Áp dụng tại Huế."
PRICE = {
    "amount_minor": 150000,
    "currency": "VND",
    "basis_quantity": "1",
    "unit": "visit",
    "moq": "2",
    "tier_min": "2",
    "tier_max": "4",
    "tax": "included",
    "conditions": ["Áp dụng tại Huế."],
}
CASE = {
    "id": "synthetic",
    "workflow": "WF-13",
    "locale": "vi-VN",
    "product": "Sửa ngăn kéo",
    "facts": [{"id": "price-card", "category": "price", "wording": "Giá 150.000 VND/lượt.", "qualifiers": "Áp dụng tại Huế.", "quantity": "3", "price": PRICE}],
}
REF = {"F1": LINE}
SHA = "a" * 40
PIN = "b" * 64


def surface(text, case=CASE, refs=REF):
    facts = audit.expected_facts(case, None)
    return audit.audit_surface(text, facts, refs, case["locale"])


def test_individual_assertions_and_distinct_qualifier():
    result = surface(LINE)
    actual = result["facts"]["F1"]
    assert actual["matches_recorded_reference"]
    assert len(actual["checks"]) == 10
    assert all(row["status"] == "matched" for row in actual["checks"].values())
    assert actual["checks"]["condition.1|qualifier.1"]["status"] == "matched"


@pytest.mark.parametrize(
    "old,new,field",
    [
        ("150.000", "15.000", "amount_minor"),
        ("VND /", "USD /", "currency"),
        (" / 1 lượt", " / 2 lượt", "basis_quantity"),
        (" / 1 lượt", " / 1 người", "price_unit"),
        ("gồm thuế", "chưa tính thuế", "tax"),
        ("tối thiểu: 2 lượt", "tối thiểu: 2 người", "moq_with_unit"),
        ("từ 2 lượt", "từ 1 lượt", "tier_min_with_unit"),
        ("đến 4 lượt", "đến 4 máy", "tier_max_with_unit"),
        ("chiếu: 3 lượt", "chiếu: 4 lượt", "quoted_quantity_with_unit"),
    ],
)
def test_correct_number_cannot_certify_other_fields(old, new, field):
    checks = surface(LINE.replace(old, new))["facts"]["F1"]["checks"]
    assert checks[field]["status"] == "mismatch"
    if field != "amount_minor":
        assert checks["amount_minor"]["status"] == "matched"


def test_other_card_and_negation_cannot_satisfy_qualifiers():
    text = LINE.replace("Áp dụng tại Huế.", "Không áp dụng tại Huế.") + "\nThẻ vận chuyển. Áp dụng tại Huế."
    assert surface(text)["facts"]["F1"]["checks"]["condition.1|qualifier.1"]["status"] == "unconfirmed"


def test_swapped_references_cannot_pool_facts_from_two_prices():
    case = deepcopy(CASE)
    second = deepcopy(case["facts"][0])
    second.update(id="other", price={**PRICE, "amount_minor": 220000})
    case["facts"].append(second)
    other = LINE.replace("150.000", "220.000")
    result = surface(other + "\n" + LINE, case, {"F1": other, "F2": LINE})
    assert all(all(v["status"] == "inconclusive" for v in f["checks"].values()) for f in result["facts"].values())
    result = surface(other + "\n" + LINE, case, {"F1": LINE, "F2": other})
    assert result["facts"]["F1"]["checks"]["amount_minor"]["status"] == "matched"


def test_open_tier_and_english_usd_minor_units():
    fact = {
        "id": "P",
        "price": {**PRICE, "currency": "USD", "amount_minor": 2515, "unit": "box", "tier_max": None, "conditions": []},
        "qualifiers": [],
        "quantity": "3",
    }
    text = "Indicative price: 25.15 USD / 1 box, tax included. Minimum order: 2 boxes. Applies from 2 boxes. Quoted quantity: 3 boxes."
    assert all(r["status"] == "matched" for r in audit.score_line(fact, text, "en-US").values())
    result = audit.score_line(fact, text.replace("from 2 boxes.", "from 2 boxes to 7 boxes."), "en-US")
    assert result["open_upper_tier"]["status"] == "mismatch"
    assert audit.score_line(fact, text.replace("25.15", "25,15"), "en-US")["amount_minor"]["status"] == "inconclusive"


def test_unsupported_public_prose_remains_visible():
    text = LINE + "\nVIP chỉ 22 USD.\nKhuyến mãi 12 EUR."
    report = surface(text)
    assert len(report["additional_commercial_text_for_review"]) == 2
    assert len(surface(LINE + " Chỉ 22 USD.")["additional_commercial_text_for_review"]) == 1


def test_unlabelled_applicability_cannot_fill_a_number_elsewhere():
    f = {
        "id": "A",
        "wording": "Giao hàng theo tuyến.",
        "qualifiers": [],
        "applicability": {"payment_type": "credit", "minimum": "2", "maximum": "10", "unit": "participant"},
    }
    text = "Giao hàng theo tuyến. Thanh toán: trả sau. Đơn tối thiểu: 2. Tối đa: 10. Đơn vị: người."
    assert all(v["status"] == "matched" for v in audit.score_line(f, text, "vi-VN").values())
    result = audit.score_line(f, text.replace("Tối đa: 10.", "Còn 10 chỗ."), "vi-VN")
    assert result["applicability.maximum"]["status"] == "inconclusive"


def artifact():
    cid = CASE["id"]
    view = {"title": "Giá thử", "body": LINE}
    content_sha = audit.digest({"title": view["title"], "preview": view["body"]})
    facts = audit.expected_facts(CASE, None)
    projected = [{**facts[0], "id": "F1"}]
    projected[0].pop("handle")
    projection = {"facts": projected, "product": CASE["product"], "locale": CASE["locale"]}
    state = {
        "groups": {"copy": {"commercial_terms": LINE}},
        "references": [{"handle": "F1", "text": LINE}],
        "preview": view,
        "quality_issues": [{"reason": "repetition"}],
        "findings": [{"outcome": "unresolved"}],
    }
    edit = {"before": {**state, "revision": 1}, "after": {**state, "revision": 2}, "qa_evidence": {"content_digest": content_sha}}
    row = {
        "case": cid,
        "checkout": SHA,
        "cases_sha256": PIN,
        "manifest": {"id": "manifest-01", "digest": PIN},
        "deliverable": {"title": view["title"], "body": view["body"], "qa_revision": 1, "digest": content_sha},
        "edited_example": edit,
        "workflow": audit.RELEASES[CASE["workflow"]],
        "arm": "improved",
        "origin": "internal",
        "run_id": "run-01",
        "projection_digest": audit.digest(projection, ascii_only=True),
    }
    return row, {"case": cid, "workflow": row["workflow"], "projection": projection}


def test_real_shape_projection_head_and_independent_product_qa():
    row, pair = artifact()
    report = audit.audit_case(CASE, row, pair, SHA, PIN, "study")
    assert set(report["surfaces"]) == set(audit.SURFACES)
    assert report["product_qa"]["before"]["statement_outcomes"] == {"unresolved": 1}
    assert report["product_qa"]["after"]["studio_issues"] == {"repetition": 1}
    with pytest.raises(ValueError, match="checkout"):
        audit.audit_case(CASE, row, pair, "f" * 40, PIN, "study")
    pair["projection"]["facts"][0]["price"]["unit"] = "machine"
    with pytest.raises(ValueError, match="Projection digest"):
        audit.audit_case(CASE, row, pair, SHA, PIN, "study")
    row["projection_digest"] = audit.digest(pair["projection"], ascii_only=True)
    with pytest.raises(ValueError, match="differ"):
        audit.audit_case(CASE, row, pair, SHA, PIN, "study")


def test_recovery_requires_exact_unit_evidence():
    case = deepcopy(CASE)
    case["facts"][0]["price"]["unit"] = "service"
    row, _ = artifact()
    row["correction"] = {
        "unit_before": "service",
        "unit_confirmed": "visit",
        "source_excerpt": case["facts"][0]["wording"],
        **{k: k for k in ("source", "offer", "binding", "claim", "original_offer", "original_claim")},
    }
    assert audit.audit_case(case, row, None, SHA, PIN, "recovery")["authority"].startswith("frozen fixture")
    row["correction"]["unit_confirmed"] = "participant"
    with pytest.raises(ValueError, match="Unit not attested"):
        audit.audit_case(case, row, None, SHA, PIN, "recovery")


def test_handle_assignment_follows_pinned_facts_instead_of_fixture_order():
    case = deepcopy(CASE)
    case["facts"].insert(0, {"id": "text", "wording": "Chai nhỏ.", "qualifiers": []})
    refs = [{"handle": "F1", "text": LINE}, {"handle": "F2", "text": "Chai nhỏ."}]
    for with_projection in (True, False):
        facts = audit.expected_facts(case, None)
        projection = {"facts": [facts[1] | {"id": "F1"}, facts[0] | {"id": "F2"}]} if with_projection else None
        audit.bind_handles(facts, "vi-VN", refs, projection)
        assert [(f["id"], f["handle"]) for f in facts] == [("text", "F2"), ("price-card", "F1")]


def test_missing_artifact_keeps_all_planned_fields_in_denominator(tmp_path, monkeypatch):
    fixture = tmp_path / "frozen.json"
    fixture.write_text(json.dumps({"cases": [CASE]}), encoding="utf8")
    pin = audit.sha(fixture.read_bytes())
    monkeypatch.setitem(audit.PINS, "study", (pin, 1))
    result = audit.audit_series(tmp_path, fixture, "study", SHA)
    assert result["expected_cases"] == 1 and result["cases_with_valid_inputs"] == 0
    assert all(r["expected_checks"] == 10 and r["outcomes"] == {"inconclusive": 10} for r in result["coverage"].values())
    assert result["product_qa"]["before"]["covered_cases"] == 0
    assert result["cases"]["synthetic"]["error"]
