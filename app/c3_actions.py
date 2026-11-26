"""Enumerated, deliberately disclosable buyer actions and requested materials."""

ACTIONS = {
    "rfq": {"vi": "Yêu cầu báo giá", "en": "Request a quote"},
    "appointment": {"vi": "Gửi đề nghị hẹn", "en": "Request an appointment"},
    "sample_request": {"vi": "Yêu cầu mẫu thử", "en": "Request a sample"},
    "colour_card_request": {"vi": "Yêu cầu bảng màu", "en": "Request a colour card"},
    "catalogue_download": {"vi": "Tải danh mục", "en": "Download the catalogue"},
    "registration": {"vi": "Đăng ký", "en": "Register"},
    "purchase": {"vi": "Mua hàng", "en": "Purchase"},
    "request_assessment": {"vi": "Yêu cầu khảo sát", "en": "Request an assessment"},
    "submit_reference": {"vi": "Gửi mẫu tham chiếu", "en": "Send a reference sample"},
    "select_sample": {"vi": "Gửi lựa chọn mẫu", "en": "Send your sample choice"},
    "choose_session": {"vi": "Chọn buổi", "en": "Choose a session"},
}


def action_label(action, locale, product):
    """Use a survey label only when the approved offering itself names a survey."""
    lang = "vi" if locale == "vi-VN" else "en"
    offering = " ".join(product.casefold().split())
    surveys = ("buổi khảo sát", "dịch vụ khảo sát", "khảo sát", "site survey", "survey visit")
    if action == "appointment" and any(offering == term or offering.startswith(term + " ") for term in surveys):
        return "Gửi đề nghị khảo sát" if lang == "vi" else "Request a survey"
    return ACTIONS.get(action, {}).get(lang, "")


BUYER_INPUTS = {
    "photo": {"vi": "Ảnh", "en": "Photo"},
    "sample": {"vi": "Mẫu tham chiếu", "en": "Reference sample"},
    "sample_choice": {"vi": "Lựa chọn mẫu", "en": "Sample choice"},
    "session_choice": {"vi": "Lựa chọn buổi", "en": "Session choice"},
}
