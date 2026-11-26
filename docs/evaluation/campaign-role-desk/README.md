# Bàn giao Sales và dịch vụ theo chiến dịch

Nhân viên có tài khoản nội bộ cấp viewer có thể nhận một yêu cầu đã được giao, ghi lại kết quả và để điều phối viên đối chiếu trên báo cáo chiến dịch. Quyết định đi vào cùng journal nghiệp vụ đang tính số cuộc hẹn và cơ hội Sales. Hành trình này đã có dữ liệu tổng hợp. Mức độ hữu ích với nhân viên thật, thời gian tiết kiệm và giá trị doanh thu chưa được đo.

## Dùng trên máy khác

Chạy publisher và API từ cùng revision theo HANDOFF, sau đó đăng nhập vào workspace. Trong **Chiến dịch → Bàn giao nghiệp vụ**, chọn chiến dịch. Admin hoặc chủ tổ chức mở **Phân quyền theo chiến dịch**, chọn tài khoản nhân viên nội bộ hiện hữu bằng mã thành viên, chọn vai trò rồi lưu. Người nhận chọn lại chiến dịch và vai trò tại cùng màn hình. Mỗi tác vụ dùng mã hồ sơ, plan và lần cập nhật được trả về từ inbox. Sau khi đổi vai trò tổ chức hoặc tái gia nhập, người quản lý cấp lại quyền chiến dịch.

| Vai trò | Hồ sơ hiển thị | Thao tác trong phạm vi chiến dịch |
| --- | --- | --- |
| Điều phối Marketing | Hẹn và RFQ của chiến dịch | Xác nhận và đổi lịch, phân công hoặc chuyển người xử lý, hủy theo trạng thái |
| Nhân viên Sales | RFQ đang giao cho chính mình | Tiếp nhận, phản hồi từ chối, ghi báo giá hoặc đơn nhận được |
| Người thực hiện dịch vụ | Lịch hiện giao cho chính mình | Ghi hoàn thành, khách vắng hoặc hủy cùng phản hồi |
| Người phản biện | Mã ca, phiên bản, trạng thái, plan | Ghi nhận xét cho đúng phiên bản mà mình đã đọc |
| Người phụ trách kinh doanh | Hẹn, RFQ và phản hồi trong chiến dịch | Điều phối hoặc nhận xét, đọc kết quả bàn giao |

Muốn cho khách yêu cầu cả lịch hẹn và báo giá, khi lập đề xuất với các hồ sơ **lịch hẹn**, chọn **Tiếp nhận báo giá trong chiến dịch lịch hẹn → Nhận thêm yêu cầu báo giá**. Quyết định duyệt plan ghim lựa chọn này vào digest. Mặc định chỉ có luồng lịch hẹn. RFQ là chính đối với kế hoạch RFQ; các mục đích liên hệ và mẫu số đo lường được theo dõi riêng. Các RFQ cũ vẫn có thể được chốt theo plan ban đầu.

## Giao thức API

Mọi đường dẫn bên dưới nằm trong `/api/tenants/{tenant_id}/campaigns/{campaign_id}/business-desk`. Thiết lập session bằng tài khoản thực của người tác nghiệp.

- `GET /access` trả vai trò còn hiệu lực và quyền quản lý của chính người gọi. `GET /grants` hiển thị lịch cấp gần nhất, revision và hiệu lực hiện hành cho quản trị viên.
- `POST /grants` nhận `key, subject, role, enabled, expected_revision`. Chỉ admin/chủ tổ chức quản lý quyền. Khách trên cổng giao bản và worker không đạt điều kiện nhận vai trò.
- `GET /{role}/inbox` trả hồ sơ đang được phép, gồm ID, revision và phản hồi đã gắn phiên bản. Hai chiến dịch cùng agency có các danh sách riêng. Chuyển người phụ trách sẽ rút quyền thấy ca đó của nhân viên cũ.
- `POST /{role}/decisions` nhận hợp đồng `sales`, `appointment_decision` hoặc `review_feedback`, cùng request ID, plan và revision đã xem. RFQ có thể chuyển người nhận khi còn ở trạng thái được giao. Có thể đổi lịch ở trạng thái xác nhận hoặc đã phân công. Chuyển người, đổi lịch, hủy và ghi kết quả đều lưu người thao tác và lý do theo hợp đồng. Nhận xét phản biện yêu cầu entity, mã hồ sơ, revision và ghi chú, không mang thẩm quyền QA bản giao.
- Gửi lại cùng payload và request ID trả đúng receipt sau khi kiểm tra lại quyền và quyền xem hồ sơ. Sửa payload với cùng khóa hoặc gửi revision cũ trả 409. Sai quyền hoặc phạm vi trả 404. Nhân viên không được dùng vai trò này để kích hoạt kênh bên ngoài, xác nhận doanh thu, điều chỉnh hoàn tiền hay cấp quyền tổ chức.

## Lưu trữ và chuyển đổi

Core v26, Business v3 và C3 v5. Chạy `python migrations/apply.py` để cài bổ sung các capability của desk, rồi khởi động API. PostgreSQL dùng quyền đọc/ghi chuyên biệt với proof gắn actor thật, transaction và nội dung đã kiểm tra. Thành viên, grant, plan và ca đều được đối chiếu trong campaign scope. Khóa theo brand dùng cùng thứ tự với bút toán CRM. Các grant lưu riêng trong operation `campaign_role_grant`; feedback lưu trong `campaign_desk_feedback`; kết quả nghiệp vụ dùng journal `campaign_sandbox_v2`. Database bảo vệ intake RFQ ngay cả khi một API cũ còn hoạt động. Bảo toàn archive trước thay đổi để quay lại theo [quy trình journal](../sandbox-operations/CUTOVER.md).

## Kiểm chứng và giới hạn

KPI theo nhóm lịch xác nhận sử dụng lần xác nhận hợp lệ đầu tiên. Đổi giờ trên một lịch đã xác nhận giữ nguyên ngày tiếp nhận vào nhóm. Bảng báo giá phụ hiển thị từ khi duyệt đúng phiên bản cho phép nhận RFQ, bao gồm số hồ sơ, kết quả Sales, tiền xác nhận và hoàn tiền mô phỏng. Báo cáo KPI chính dịch vụ tiếp tục tính theo kỳ và mẫu số đã ký. Các ảnh `ui/secondary-rfq-*.png` ghi một RFQ hợp lệ và chưa có lịch hẹn, trên Chrome tại ba kích thước trong hai theme.

Hai phép thử `test_rescheduling_cannot_reenter_a_prior_confirmation_cohort` và `test_secondary_quotes_count_only_the_explicit_plan_and_settlements` trong `tests/test_measurement_integrity.py` thất bại trên cây `044a914`. Trường hợp đầu đưa ngày xác nhận cũ vào kỳ do đổi lịch, trường hợp sau thiếu báo cáo riêng. Browser trên cùng cây không tìm thấy thẻ số yêu cầu đặt lịch của kế hoạch. Sau thay đổi, hai regression và hành trình `tests/browser_campaign_engine.py::test_campaign_commands_and_scope_switch` đạt trên dữ liệu tổng hợp.

Dùng cấu hình kiểm thử local của repository. Chạy `python -m pytest -q tests/test_campaign_role_desk.py tests/test_campaign_appointments.py tests/test_campaign_operations.py` với `AMC_TEST_PG=1`. Chạy `python -m pytest -q tests/browser_role_desk.py tests/browser_campaign_engine.py` với Chromium; có thể đặt `AMC_BROWSER_EXECUTABLE` tới trình duyệt cục bộ. `AMC_DESK_SCREENSHOTS` là thư mục ảnh, `AMC_DEPT_OPS_EVIDENCE` là thư mục receipt không chứa token. Các tệp trong thư mục này ghi lại một ca giả lập và giao diện tại 1280, 820, 390 px trong hai theme. Người phản biện có thể kiểm lại nghiệm thu bằng cách thu hồi quyền giữa hai lần gửi cùng receipt, đổi người phụ trách, đổi tư cách thành viên rồi cấp lại và so sánh dữ liệu của hai khách cùng agency.

Phạm vi gồm phối hợp nghiệp vụ nội bộ. Chưa có đồng bộ lịch ngoài, CRM/ERP ngoài, hóa đơn, ghi nhận chi tiêu thật hoặc dữ liệu khách thật. Không có kết luận về hiệu quả nghề nghiệp hoặc tiết kiệm chi phí. Commercial GA vẫn NO-GO.
