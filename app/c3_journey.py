"""Optional editorial guidance. Industry and product type are confirmed by the editor."""

VERSION = "amc.buyer-journey-editor/1"

# (industry, product type, action, selling units, suggested buyer preparation, Sales evidence)
PLAYBOOKS = (
    ("Nội thất", "Hàng gia dụng", "purchase", ("piece",), "Đo vị trí sử dụng rồi đối chiếu với quy cách.", "đơn mua xác nhận sau khi đối chiếu điều kiện"),
    ("Quà tặng", "Sản phẩm có lựa chọn màu", "colour_card_request", ("piece",), "Ghi màu cần so khi yêu cầu bảng màu.", "yêu cầu bảng màu được người phụ trách tiếp nhận"),
    ("Vật liệu", "Vật liệu hoàn thiện", "sample_request", ("m²",), "Nêu vị trí lắp đặt và bề mặt cần so trước khi chọn mẫu.", "yêu cầu mẫu có vị trí sử dụng"),
    ("Vật liệu", "Vật tư công trình", "rfq", ("piece", "m²"), "Ghi số lượng dự kiến, địa bàn giao và thời điểm cần hàng để nhận báo giá.", "yêu cầu đủ thông tin để Sales báo giá"),
    ("Phân phối", "Hàng đóng hộp", "rfq", ("box",), "Ghi số hộp, địa bàn nhận và thời hạn cần báo giá.", "yêu cầu báo giá đủ điều kiện giao"),
    ("Dịch vụ kỹ thuật", "Dịch vụ theo thiết bị", "appointment", ("machine",), "Ghi số thiết bị và khung giờ có thể bàn giao khi đặt lịch.", "lịch hẹn được hai bên xác nhận"),
    ("Đào tạo", "Lớp thực hành", "registration", ("participant",), "Chọn buổi học và ghi số người đăng ký.", "đăng ký được người phụ trách lớp xác nhận"),
    ("Phân phối", "Danh mục hàng đóng hộp", "catalogue_download", ("box",), "Đánh dấu các quy cách cần đối chiếu trong danh mục.", "lượt tải hoàn tất, ghi riêng yêu cầu báo giá sau đó"),
)


def candidates(projection):
    action = projection.get("task_intent", {}).get("buyer_action")
    facts = [f for f in projection.get("facts", []) if f.get("price")]
    units = {f["price"].get("unit") for f in facts}
    result = {"version": VERSION, "eligible": [], "action": action, "channel": projection.get("channel"),
              "source_handles": [f["id"] for f in facts]}
    if projection.get("locale") != "vi-VN" or projection.get("channel", "").strip().casefold() != "web" or len(units) != 1:
        return result
    unit = next(iter(units))
    for industry, product_type, supported_action, supported_units, prompt, measure in PLAYBOOKS:
        if action != supported_action or unit not in supported_units:
            continue
        result["eligible"].append({
            "industry": industry, "product_type": product_type, "unit": unit,
            "reason": f"Đề xuất bước tiếp theo cho {projection['audience']} khi xem {projection['product']}.",
            "fields": {
                "copy.value_proposition": {"kind": "editorial", "text": prompt},
                "client_strategy.activation": {"kind": "editorial", "text": "Đề xuất đặt hướng dẫn này cạnh biểu mẫu. " + prompt},
                "client_measurement.hypothesis": {"kind": "hypothesis", "text": f"Thử xem hướng dẫn rõ ở cạnh biểu mẫu có giúp tăng số {measure}."},
            },
        })
    return result
