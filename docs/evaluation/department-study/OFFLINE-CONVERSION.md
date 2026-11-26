# Đối soát nội bộ trước khi cân nhắc Google Data Manager

**Quyết định thiết kế ngày 26/11/2026.** AMC chưa có connector cho chuyển đổi ngoại tuyến. Giao dịch trong Sales/Service và quyền gửi dữ liệu quảng cáo là hai quyết định nghiệp vụ riêng. Đối với một triển khai mới, đích thiết kế là Google Data Manager API. Các ngoại lệ legacy dành cho hoạt động trước đây chỉ có thể được xác minh ở cấp tài khoản/dự án được phép. [Tài liệu migration và phạm vi thời gian](../../research/KNOWLEDGE_CARDS.md) · [Hợp đồng Google](https://developers.google.com/data-manager/api/devguides/events/google-ads/offline/send-events)

| Dữ kiện | Nguồn tin cậy và quyết định cho AMC |
| --- | --- |
| Mục tiêu đo | Chủ doanh nghiệp chọn một mốc và mẫu số. Nhận RFQ, Sales tiếp nhận và xác nhận doanh thu là ba mốc khác nhau. Mỗi mốc cần hành động chuyển đổi và người phê duyệt riêng. |
| Tenant, destination và mục đích | Khóa tenant/campaign với destination và action đã được ủy quyền. Sự đồng ý nhận tư vấn thuộc luồng liên hệ; cần bằng chứng riêng cho mục đích measurement, quyền dữ liệu và consent tương ứng nếu có. |
| Xác định sự kiện | Truy event hoặc receipt của giao dịch nguồn, timestamp có múi giờ và eventSource thực tế. Không dùng thời gian chạy báo cáo, session tổng hợp hoặc ngày duyệt thay cho thời điểm phát sinh. |
| Giá trị và sửa đổi | Với doanh thu, đối soát số tiền/currency xác nhận. Phân biệt đơn hàng, hoàn/hủy và điều chỉnh. Cố định định danh giao dịch trong scope và phối hợp receipt, idempotency, phiên bản và số đã điều chỉnh. |
| Đối sánh và xác nhận nhà cung cấp | Adapter tương lai cần thẩm quyền với dữ liệu đối sánh, bộ kiểm riêng, quyền hợp lệ và receipt/kết quả kiểm tra từ nền tảng. Hash có thể được dùng để đối sánh người dùng. Gửi validateOnly tới Google cũng truyền dữ liệu. |

## Phép kiểm có thể chạy offline

Hai receipt thương mại đã công bố từ SQLite và PostgreSQL cùng ghi một đơn. Trước hủy, số doanh thu xác nhận là 5.000 VND tổng hợp. Sau hủy vẫn có một đơn đã từng phát sinh nhưng doanh thu xác nhận bằng 0. Các receipt mô tả việc nội bộ, thiếu bằng chứng consent quảng cáo, destination và timestamp của conversion. Vì thế đầu ra dành cho người phân tích là **giữ giao dịch trong bảng đối soát**, chưa đủ điều kiện xuất.

```sh
python -m pytest -q tests/test_offline_conversion_boundary.py tests/test_api.py::test_approval_requires_separate_human_and_is_tenant_scoped
```

Kiểm thử gọi API AMC trong bộ nhớ. Đề xuất loại hành động upload không được hỗ trợ trả 422 kể cả khi thêm validateOnly. Đường thực thi ngoài sandbox đã có kiểm thử 501 sau khi phê duyệt độc lập. Không có tài khoản Google, request tới Google hoặc chi phí quảng cáo trong phép thử. [Receipt SQLite](../business-intake/consultation/sqlite.json) · [Receipt PostgreSQL](../business-intake/consultation/postgres.json) · [Phép kiểm](../../../tests/test_offline_conversion_boundary.py)
