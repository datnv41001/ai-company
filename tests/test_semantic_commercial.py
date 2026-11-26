"""Commercial meaning regressions from the synthetic Khe Gọn and Luồng Rõ briefs."""
import pytest

from app.c3_content_evidence import classify


FEATURE = {"id": "F1", "category": "feature", "wording": "Vách ngăn có thể tháo rời",
           "qualifiers": ["Áp dụng cho mẫu tiêu chuẩn."]}
FEE = {"id": "F2", "category": "price", "wording": "Phí khảo sát", "price": {
    "currency": "VND", "amount_minor": 760000, "unit": "visit", "moq": 1,
    "tax": "included", "basis_quantity": 1, "tier_min": 1, "conditions": []}}
SCOPE = {"region": "HN", "product": "Khay chia linh kiện Khe Gọn", "locale": "vi-VN",
         "hypotheses": ["Cần quan sát ca nhận hàng để kiểm chứng."]}


@pytest.mark.parametrize(("copy", "reason", "handles"), [
    ("Nhận 760.000 VND khi đặt lịch.", "payment_direction", ["F2"]),
    ("Receive 760,000 VND when you book.", "payment_direction", ["F2"]),
    ("Phí khảo sát chuyển thành khoản hoàn tiền 760.000 VND.", "payment_kind", ["F2"]),
    ("Vách ngăn có thể tháo rời, và cả khay cũng có thể tháo rời.", "component_scope", ["F1"]),
    ("Có thể tháo rời toàn bộ khay.", "component_scope", ["F1"]),
    ("Chúng tôi đã khảo sát khách hàng và xác nhận nhu cầu.", "observation_status", []),
    ("Vách ngăn có thể tháo rời.", "missing_qualifier", ["F1"]),
])
def test_edited_asset_meaning(copy, reason, handles):
    result = classify(copy, [FEATURE, FEE], [], set(), SCOPE, precise=True)
    assert result[1:] == ("contradiction", reason, handles)


def test_questions_and_ambiguity_require_review():
    for copy in ["Khách hàng có thể nhận thông tin về phí khảo sát?",
                 "Có nên phỏng vấn người mua trong ca nhận hàng?"]:
        assert classify(copy, [FEATURE, FEE], [], set(), SCOPE, precise=True)[1] == "unresolved"


def test_commercial_assertion_and_segment_provenance():
    from app.commercial_meaning import assertion, suggestions

    fact = assertion(FEE, SCOPE)
    assert (fact["payer"], fact["payee"], fact["price"], fact["scope"]["region"]) == ("buyer", "seller", FEE["price"], "HN")
    before = "Giữ câu đầu. Nhận 760.000 VND. Giữ câu cuối."
    bad = "Nhận 760.000 VND."
    left = before.index(bad)
    row = {"id": "one", "field": "studio.copy.benefit", "text": bad, "start": left, "end": left + len(bad),
           "handles": ["F2"], "reason": "payment_direction", "outcome": "contradiction"}
    item, = suggestions([row], SCOPE, [{"handle": "F2", "text": "Giá theo lượt và điều kiện đã duyệt."}])
    assert before[:item["start"]] + item["proposed"] + before[item["end"]:] == (
        "Giữ câu đầu. Giá theo lượt và điều kiện đã duyệt. Giữ câu cuối.")


@pytest.mark.parametrize("text", ["The product has a removable divider, not a removable tray.",
                                 "Không phải toàn bộ khay có thể tháo rời; chỉ vách ngăn tháo rời."])
def test_negated_product_scope_is_reviewable(text):
    assert classify(text, [FEATURE], [], set(), SCOPE, precise=True)[1:3] == ("unresolved", "scope_paraphrase")


def test_clause_suggestion_preserves_useful_lead():
    from app.commercial_meaning import suggestions

    text = "Đối chiếu mã yêu cầu, và nhận 760.000 VND khi đặt lịch."
    result = classify(text, [FEE], [], set(), SCOPE, precise=True)
    assert result[2] == "payment_direction"
    item, = suggestions([{"id":"a","field":"studio.copy.benefit","start":0,"end":len(text),"text":text,
                          "outcome":result[1],"reason":result[2],"handles":result[3]}],
                        SCOPE | {"facts":[FEE]}, [{"handle":"F2","text":"Giá đã duyệt."}])
    assert text[:item["start"]] == "Đối chiếu mã yêu cầu, và "
    assert text[item["start"]:item["end"]] == item["original"] == "nhận 760.000 VND khi đặt lịch."
