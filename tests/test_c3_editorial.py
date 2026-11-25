from app import c3_marketing as marketing


def test_quotation_keeps_interval_tax_currency_and_minor_units():
    fact = {
        "id": "F2", "wording": "canonical source price", "qualifiers": ["Pickup only."], "quantity": "4",
        "price": {"currency": "USD", "amount_minor": 1005, "basis_quantity": "1", "unit": "box",
                  "tax": "excluded", "moq": "2", "tier_min": "3", "tier_max": "8", "conditions": ["Pickup only."]},
    }
    line = marketing.fact_line(fact)
    assert all(value in line for value in ("[F2]", "10,05 USD", "1 hộp", "chưa gồm thuế", "từ 3 hộp đến 8 hộp",
                                           "tối thiểu 2 hộp", "4 hộp", "tham khảo"))
    assert line.count("Pickup only.") == 1
    assert "amount_minor" not in line


def test_repeated_staff_goal_is_removed_from_buyer_sections():
    goal = "Increase appointment requests"
    checkpoint = {"sections": dict.fromkeys(marketing.FIELDS["content"], goal + ".")}
    checkpoint["sections"]["headline"] = "Select the right sample size"
    assert marketing.editorial_sections("content", checkpoint, {"objective": goal}) == [
        "Tiêu đề trang: Select the right sample size"
    ]
    assert "khung giờ" in marketing.buyer_action("Trang đặt lịch", "Service A")
