# Bàn giao vận hành chiến dịch trong sandbox

Mở chiến dịch trong Campaign Command Center bằng tài khoản quản trị agency. Duyệt kế hoạch từ mục tiêu và hồ sơ đã xác nhận. Màn hình lấy công việc, RFQ và số liệu từ cùng các biên nhận mà API trả về. Báo cáo trong công cụ này sử dụng dữ liệu tổng hợp. Đối soát nguồn cho biết đường đi của một bản ghi, chưa đo hiệu quả nhân quả của Marketing. [Nhiệm vụ sản phẩm](../PRODUCT_MISSION.md)

## Thực thi có kiểm soát

1. Người lập lịch chọn bản giao C3 có QA hợp lệ, gửi ID, revision, SHA-256, giờ thực hiện có múi giờ và dự toán VND.
2. Một admin hoặc owner khác phê duyệt lịch. Tổng chi đã mô phỏng của chiến dịch cộng với các khoản đã duyệt còn giữ chỗ trong bản kế hoạch hiện tại phải nằm trong hạn mức.
3. Khi đến hạn, lệnh thực thi đọc lại quyền của người duyệt, kế hoạch, nguồn và bản giao. Thành công tạo một biên nhận cùng số tiền mô phỏng. Lỗi tạm thời giữ chỗ cho lần thử sau, tối đa ba lần. Hủy lịch đang chờ hoặc lỗi sẽ giải phóng phần giữ chỗ.
4. Khi mất phản hồi, gửi lại nguyên payload với cùng tài khoản và `request_id`. Server trả lại biên nhận cũ. Một payload khác dùng cùng khóa sẽ nhận HTTP 409.

Tất cả thao tác ở `/api/tenants/{tenant_id}/campaigns/{campaign_id}/sandbox`. Đọc bằng GET. Ghi bằng POST tới `/commands` với `kind`, `plan_id`, `request_id` và các trường quy định trong OpenAPI. Ở phiên bản này, kế hoạch có thể chứa tài liệu hạn chế nên operations dành cho admin và owner trong phạm vi chiến dịch. Khách hàng tiếp tục phản hồi qua cổng duyệt bản giao của họ.

## RFQ, Sales và doanh thu

RFQ mới cần mã yêu cầu, sản phẩm, đơn vị đã duyệt và mục đích liên hệ. Yêu cầu thiếu số lượng, địa bàn, ngày cần giao hoặc quyền trả lời được giữ ở trạng thái chờ. Dùng `complete_rfq` để bổ sung. Đơn vị đếm như máy và hộp dùng số nguyên. Khối lượng và diện tích nhận số thập phân. Có thể gửi thêm một hợp đồng `details` phù hợp với đơn vị.

| Hợp đồng | Trường nghiệp vụ |
| --- | --- |
| `materials_v1` | Ứng dụng vật liệu và điều kiện tiếp cận nơi giao |
| `service_v1` | Phạm vi dịch vụ và loại thiết bị |
| `seats_v1` | Chương trình và hình thức tổ chức tại chỗ, trực tuyến hoặc kết hợp |

Ví dụ sau dùng sản phẩm bán theo máy. Thay ID bằng dữ liệu của chiến dịch thử, thay ngày và thời điểm bằng giá trị phù hợp. Công cụ xác nhận dữ liệu bổ sung theo hợp đồng. Tên, số điện thoại và email khách thật không cần thiết cho các ca thử.

```json
{
  "kind": "rfq",
  "request_id": "intake-001",
  "plan_id": "APPROVED_PLAN_ID",
  "rfq_id": "SYNTH-PUMP-001",
  "product_id": "APPROVED_PRODUCT_ID",
  "unit": "machine",
  "quantity": "2",
  "location": "Xưởng thử A",
  "required_date": "2026-12-21",
  "contact_purpose": "quote_request",
  "occurred_at": "2026-11-25T09:00:00+07:00",
  "details": {"schema_id": "service_v1", "service_scope": "Kiểm tra định kỳ", "equipment_type": "Bơm"}
}
```

Sales nhận phân công, ghi lý do tiếp nhận hoặc từ chối, rồi lần lượt báo giá, lập đơn và xác nhận số tiền. Mỗi chuyển trạng thái mang `expected_revision` của RFQ để ngăn ghi đè. Việc điều chỉnh, hoàn tiền hoặc hủy cần lý do. Khi kế hoạch đổi phiên bản, Sales vẫn có thể đối soát yêu cầu cũ. Biên nhận giữ thời điểm nghiệp vụ và thời điểm ghi sổ.

Báo cáo tổng hợp từ từng yêu cầu và hành động thực thi đã thành công. Doanh thu xác nhận trừ hoàn tiền và loại đơn đã hủy. Một phiên đến muộn có thể bổ sung attribution nếu khớp kế hoạch, hành động và thời điểm xảy ra. Doanh thu thiếu nguồn nằm ở một cột riêng. Chi phí quảng cáo mô phỏng dùng VND, độc lập với sổ nguồn lực Workforce tính theo micro-USD. Người thứ hai có quyền duyệt một đề xuất tối ưu hóa thành gói việc tiếp theo sau khi kiểm tra số liệu gốc. Thay đổi số liệu làm đề xuất cũ hết hiệu lực.

## Đơn vị công việc và xác nhận thực tế

Đề xuất kế hoạch chỉ mô tả công việc sẽ giao. Trong giao dịch duyệt, hệ thống ghi đủ biên nhận `commission` ở trạng thái `requested`, sau đó mới soạn nội dung mạng xã hội, quảng cáo, brief hình ảnh và lịch. Mỗi bản nháp thành công có thêm biên nhận `generated`, cùng ID đầu việc và đúng manifest nguồn. Nếu bước soạn lỗi, toàn bộ giao dịch được hoàn tác. Gửi lại lệnh duyệt đã thành công sẽ trả về đúng kết quả cũ.

Khi duyệt kế hoạch, server tạo đầu việc trong cùng giao dịch, trước khi xếp Workforce. Danh tính đầu việc gắn với tenant, khách hàng, brand, campaign, sản phẩm, đối tượng, mục tiêu, bộ manifest, loại đầu ra và tiêu chí nghiệm thu. Đổi ngân sách cho cùng một nhiệm vụ chưa chạy giữ nguyên đầu việc. Giao một mục tiêu hay brief mới tạo danh tính mới. Nhật ký giữ các lần giao, thao tác người dùng và biên nhận quyết định. Trạng thái worker, số lần thử và revision bản giao được đọc từ đúng run.

Khi hai bản kế hoạch sử dụng cùng brief, tra `queue_receipt` để biết phiên bản nào sở hữu đầu ra. Hệ thống đối chiếu thời điểm xếp hàng do cơ sở dữ liệu ghi, lần phê duyệt kế hoạch có hiệu lực lúc đó, run, brief và digest manifest. Đầu việc cũ còn chờ khi mục tiêu đổi được ghi `incomplete` và giữ thời gian, chi phí đã phát sinh. Bản bàn giao đã sản xuất vẫn nhận được quyết định khách hàng sau khi chiến dịch chuyển sang kế hoạch mới. Mỗi cặp biên nhận chia sẻ và nhóm nội dung chỉ ghi nhận một lần.

Mỗi khai báo `labor` ghi người quan sát, giai đoạn làm rõ, sửa, QA hoặc sản xuất, thời lượng và chi phí được phân bổ nếu đã biết. Sau khi ghi đủ lần thử, `close_unit_cost` ghi chi phí ngoài nhân công và căn cứ đối soát. Một khai báo nhân công mới mở lại kết toán. Mẫu số là số đầu việc đã được người hành nghề chấp thuận. Giá thành tính cả đơn vị đã giao nhưng bị từ chối hoặc còn dang dở. Chỉ khi toàn bộ đầu việc đã ghi đủ chi phí và mẫu số dương mới hiện giá thành. Thời lượng, cơ sở so sánh thủ công và kết quả kinh doanh cần bằng chứng quan sát thực tế.

`unit_receipt` yêu cầu ID quyết định từ cổng khách hàng cùng nhóm bản giao C3 tương ứng. Bản thử mặc định được gắn `fixture_accepted`. Khi tổ chức đã xác minh và được phép mời người hành nghề, quản trị môi trường có thể khai báo `AMC_PRACTITIONER_ACCEPTORS` gồm các bộ `tenant_id/campaign_id/client_reviewer_user_id`, ngăn cách bằng dấu phẩy. Để trống khi chạy ví dụ hoặc CI. Chỉ sau quyết định trên snapshot khớp của đúng người đã ghi danh thì đầu việc mới nhận `business_accepted`. Khoản này chỉ xác nhận đầu ra cụ thể. Các bước vận hành và báo cáo tài chính ở sandbox luôn mang nhãn mô phỏng.

## Chạy lại trên máy khác

Dùng môi trường Python và PostgreSQL thử đã mô tả trong README của repository. SQLite chạy `python -m pytest -q tests/test_campaign_operations.py`. Với PostgreSQL cục bộ đã migrate, đặt các biến môi trường test của dự án và `AMC_TEST_PG=1`, sau đó chạy lại cùng lệnh. Fixture chỉ mở kết nối runtime đến DB thử trên loopback có tên bắt đầu bằng `amc_test`. Ca khởi động lại tạo hai tiến trình API liên tiếp và tái gửi cùng một lệnh sau khi tiến trình đầu đã dừng.

Kiểm thử API dùng nghiệp vụ bảo trì theo số máy. Hành trình B2B trong `tests/campaign_planner_journey.py` gọi `tests/campaign_operations_journey.py` sau khi đã có bản giao landing, bản sửa, QA và quyết định từ cổng khách hàng. Chạy với cấu hình model local theo hướng dẫn của Campaign Engine để lấy biên nhận thực tế. Đọc `operating_result` trong JSON hành trình để kiểm tra mã sự kiện, phiên bản, lần thử, RFQ, đơn hàng và mẫu số chi phí của chính lần chạy. Dữ liệu được lưu trong journal kiến thức có RLS và quyền ghi qua cơ chế hiện hữu ở schema v25.
