"""Vietnamese editorial playbooks for the offline Studio regression. Values are proposals."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Journey:
    decision: str
    prompt: str
    comparison: str
    event: str
    recipient: str
    reconciliation: str


PLAYBOOKS = {
    "purchase": Journey(
        "kiểm tra món hàng có vừa vị trí sử dụng", "Hãy đo vị trí đặt sản phẩm rồi đối chiếu với quy cách.",
        "hướng dẫn đo ngay đầu trang", "đơn mua đã xác nhận", "bộ phận bán hàng",
        "đối chiếu mã đơn, tách đơn hủy và khoản hoàn"),
    "colour_card_request": Journey(
        "đối chiếu màu trước khi chọn quà", "Hãy ghi màu cần so và yêu cầu bảng màu trước khi chọn.",
        "hướng dẫn đối chiếu màu tại vị trí đặt quà", "yêu cầu bảng màu hợp lệ", "nhân viên tư vấn",
        "khớp mã yêu cầu với bảng màu được gửi, ghi riêng bước đặt hàng"),
    "sample_request": Journey(
        "chọn mẫu vật liệu trước khi đưa vào bảng dự toán", "Hãy nêu vị trí sử dụng và đặc điểm bề mặt cần đối chiếu.",
        "bảng so mẫu theo vị trí lắp đặt", "yêu cầu mẫu có vị trí sử dụng", "phụ trách vật liệu",
        "khớp mã yêu cầu với mẫu được chọn, ghi tách yêu cầu báo giá sau đó"),
    "rfq": Journey(
        "so báo giá trên cùng số lượng và điều kiện", "Hãy gửi số lượng dự kiến cùng địa bàn cần báo giá.",
        "bảng điều kiện tính theo số lượng", "yêu cầu báo giá đủ số lượng và địa bàn", "Sales",
        "đối chiếu mã RFQ với báo giá đã lập, ghi riêng đơn xác nhận sau báo giá"),
    "appointment": Journey(
        "chọn lịch phù hợp với thời gian dừng thiết bị", "Hãy ghi số thiết bị và khung giờ có thể bàn giao.",
        "mẫu yêu cầu khung giờ kèm số thiết bị", "lịch hẹn đã được hai bên xác nhận", "điều phối kỹ thuật",
        "đối chiếu mã lịch, loại lịch trùng và ghi riêng lịch hủy hoặc chưa xác nhận"),
    "registration": Journey(
        "chọn buổi thực hành và chuẩn bị phần học phí chưa bao gồm", "Hãy ghi buổi muốn học và số người tham gia.",
        "hướng dẫn chọn buổi và kiểm tra phần cần chuẩn bị", "đăng ký có buổi và số người xác nhận", "điều phối lớp",
        "khớp mã đăng ký với danh sách đã xác nhận, tách người tham dự thực tế"),
    "catalogue_download": Journey(
        "lập danh sách quy cách trước khi hỏi giá nhà cung cấp", "Hãy dùng danh mục để ghi lại quy cách cần so sánh.",
        "mẫu ghi quy cách ngay cạnh liên kết danh mục", "lượt tải danh mục hoàn tất", "phụ trách danh mục",
        "khớp mã tải với phiên, tách yêu cầu báo giá và đơn mua về sau"),
}


def journey_for(action, selling_unit):
    reviewed_units = {
        "purchase": {"piece"}, "colour_card_request": {"piece"}, "sample_request": {"m²"},
        "rfq": {"piece", "box"}, "appointment": {"machine"}, "registration": {"participant"},
        "catalogue_download": {"box"},
    }
    journey = PLAYBOOKS.get(action)
    if not journey or selling_unit not in reviewed_units[action]:
        raise ValueError("Buyer action outside reviewed study playbooks")
    if action == "rfq" and selling_unit == "box":
        return Journey(journey.decision, "Hãy gửi số hộp cần báo giá và địa bàn nhận hàng.",
                       "bảng so theo số hộp đặt cho mỗi điểm bán", journey.event, journey.recipient, journey.reconciliation)
    return journey
