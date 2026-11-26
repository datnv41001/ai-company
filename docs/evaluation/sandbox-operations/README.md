# Lịch dịch vụ, tác vụ cục bộ và chứng từ chi phí

Nền thử nghiệm là merge #44 `837ec9fc6c67868f5a88e263f06febc7d0ddf6bc`. Schema core v25, Business v3, C3 v4. Không có migration hoặc thay đổi quyền PostgreSQL. Bản này chưa nâng cấp bất kỳ pool đang vận hành.

## Hành trình lịch dịch vụ

Trong **Chiến dịch → Điều hành chiến dịch**, chọn kế hoạch đã duyệt có hành động người mua đặt lịch và đơn vị dịch vụ đã xác nhận. Ghi mã yêu cầu, số lượng theo đơn vị, phạm vi dịch vụ, nơi làm, giờ mong muốn và quyền liên hệ. Người điều hành xác nhận giờ, giao cho một nhân viên có quyền trong tổ chức rồi ghi nhận hoàn thành, hủy hoặc vắng mặt cùng phản hồi. Mỗi thay đổi cần revision hiện tại. Lịch cùng chiến dịch được đối soát riêng với RFQ và đơn hàng. Hoàn thành dịch vụ không tự tạo doanh thu. Việc nhập sự kiện hỗ trợ thời điểm nghiệp vụ trong quá khứ, gồm cả múi giờ. [Biên nhận PostgreSQL của ba lịch](appointments.json)

## Tác vụ có quyền và bộ điều phối

Ở **Thực thi trong sandbox**, chọn nhóm bản giao đã được QA qua C3, đích nội bộ, chế độ thủ công hoặc điều phối, dự toán và thời điểm. Một admin hoặc owner khác xác nhận trước khi chạy. Các capability là render bản xem trước website/tìm kiếm/duyệt nội bộ và diễn tập vị trí quảng cáo trên dữ liệu đã duyệt. Kết quả lưu trường nội dung, SHA-256 và biên nhận vào journal trong cùng giao dịch với khoản mô phỏng. Ở hợp đồng C3 /1 hiện hỗ trợ copy, SEO, chiến lược và đo lường. Mẫu quảng cáo từ copy là diễn tập bố trí. Kênh social/ad chuyên biệt của nhánh mở rộng Studio /2 cần nối và kiểm thử sau khi tích hợp. [Biên nhận điều phối](dispatch.json)

Để chạy trên máy khác, dùng API và database local theo HANDOFF. Cấu hình một bí mật ngẫu nhiên ít nhất 32 byte ở biến `AMC_SANDBOX_DISPATCH_KEY` cho cả tiến trình API và runner. Chỉ cấp cho runner một access token hiện hành của admin được phép đọc đúng chiến dịch qua `AMC_SANDBOX_DISPATCH_TOKEN`. Truyền các bí mật qua môi trường local, lưu ngoài Git. API chỉ chấp nhận đầu nối loopback cho đường điều phối và đọc lại quyền nhóm, revision, kế hoạch và ngân sách. Mỗi vòng lấy tối đa 25 tác vụ. Giữ nguyên database khi restart. Lệnh sau chạy một số vòng hữu hạn và in ID biên nhận, không in token.

```sh
python scripts/dispatch_campaign_sandbox.py --origin http://127.0.0.1:8000 --tenant TENANT_UUID --campaign CAMPAIGN_UUID --ticks 8 --batch 5 --interval 2
```

## Đối soát chi phí

Bảng đầu việc lấy mọi lần thử từ journal thực của run, gồm lượt thất bại, token chưa đo, thời điểm và outcome. Số liệu cấp chiến dịch đếm mỗi run một lần ngay cả khi hai nhóm nội dung dùng chung run. Người thực hiện ghi riêng thời gian làm rõ, biên tập, QA, sản xuất và baseline thủ công. Lệnh `close_unit_cost` lưu khai báo của người vận hành; nó không chứng nhận hóa đơn.

Tích hợp kế toán nội bộ có thể gửi lệnh `verify_unit_cost` kèm bốn dòng phân bổ VND cho model, compute, công cụ và người làm. Mỗi dòng có mã phân bổ riêng. Bên đo độc lập giữ khóa HMAC `AMC_SANDBOX_COST_METER_KEY` tối thiểu 32 byte; trình duyệt và người nhập liệu không cần khóa. Payload chữ ký trong `app/campaign_operations_cost.py` gắn phạm vi, ID đầu việc, plan và digest của toàn bộ kiểm kê hiện tại. Ghi thêm công hoặc thay đổi dữ liệu sẽ làm chứng từ cũ hết hiệu lực. Chỉ dùng mã phân bổ duy nhất từ nguồn kế toán và kiểm tra phân bổ nhiều nhóm trên cùng một hóa đơn tại nguồn. Chưa có kết nối kế toán hay đồng hồ tài nguyên sản xuất. Bộ ca dùng chứng từ tổng hợp để kiểm thử giao thức. Giá thành đầu ra thực vẫn chưa đo. Thiếu bất kỳ nhóm chi phí nào, còn lượt chưa đo, hoặc chưa có đầu việc được doanh nghiệp chấp nhận thì giá thành tổng hợp hiển thị chưa xác định.

## Nghiệm thu và chạy lại

Trên PostgreSQL 16.6 local, bộ test sandbox, lịch dịch vụ, quyền và workflow liên quan đạt 11/11. Chromium local đạt 3/3, gồm thao tác bàn phím, tách scope và đối chiếu trạng thái thật sau khi lưu. Các ca hoạt động trên SQLite và PostgreSQL hạn chế theo cấu hình test hiện có. Bộ điều phối được chạy ở process riêng rồi khởi động lại cùng database. Phép thử dùng worker có phản hồi xác định; token trong biên nhận dispatcher là số kiểm thử, không phải phép so sánh năng lực model hoặc hóa đơn thực tế.

```sh
python -m pytest -q tests/test_campaign_appointments.py tests/test_campaign_operations.py tests/test_campaign_unit_ownership.py tests/test_research_strategy.py
python -m pytest -q tests/browser_campaign_engine.py
```

Đặt `AMC_TEST_PG=1` cùng môi trường test PostgreSQL cục bộ của repository để chạy cả hai backend. Đặt `AMC_DEPT_OPS_EVIDENCE` thành thư mục tuyệt đối để xuất lại biên nhận JSON và ảnh. [Desktop sáng](ui/appointment-1280.png) · [Desktop tối](ui/appointment-1280-dark.png) · [Tablet sáng](ui/appointment-820.png) · [Tablet tối](ui/appointment-820-dark.png) · [Mobile sáng](ui/appointment-390.png) · [Mobile tối](ui/appointment-390-dark.png)

Khi rollback nội bộ, dừng dispatcher trước, lưu bản backup database và giữ nguyên journal. Chạy lại image cùng bản mã tương thích trước khi tiếp tục sử dụng các lịch mới. Bản #44 chưa hiểu loại sự kiện appointment, vì vậy chỉ dùng với bản phục hồi dữ liệu trước khi có sự kiện mới hoặc giữ ứng dụng mới ở trạng thái dừng để chờ bản sửa. Commercial GA vẫn NO-GO.
