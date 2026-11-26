# Giao thức journal chiến dịch và chuyển phiên bản

Bản hợp nhất dùng core v26, Business v3, C3 v5 và journal `ops/2`. Migration 026 chỉ thay đổi quyền ghi của luồng kế hoạch và journal qua trigger trên `knowledge_commands`; trigger không viết lại dòng lịch sử. Store mới đọc theo sequence từ hai namespace. Các sự kiện mới, kể cả khi tất toán công việc cũ, được ghi với operation `campaign_sandbox_v2`.

## Chuyển trên bản sao dữ liệu phát triển

1. Ghi SHA của binary và phiên bản cơ sở dữ liệu hiện tại. Dừng tiếp nhận thay đổi, dừng API và bộ điều phối, chờ giao dịch đang chạy kết thúc. PostgreSQL khóa bảng khi thiết lập fence để phân định thứ tự commit.
2. Tạo archive trước chuyển và khôi phục thử vào database mới với đúng binary cũ. Trên SQLite đóng các kết nối và tạo backup bằng SQLite Backup API; sao chép một file đang dùng WAL sẽ thiếu giao dịch.
3. Chạy `python migrations/apply.py` rồi khởi động API mới. Startup xác nhận role runtime, bộ marker liền mạch và trigger đã bật. Mỗi giao dịch API khai báo `ops/2`. Chạy lại publisher lần hai và đối chiếu UUID, nội dung cùng thứ tự receipt cũ.
4. Đọc lại bằng runtime mới. Với PostgreSQL, process tiền nhiệm còn sống chỉ nhận các receipt v1; parser cũ không thấy các entity hoặc action v2. Ngay cả process đã qua startup cũng bị database từ chối ghi v1. Binary và publisher core v25 mới khởi động từ chối core v26. Trên SQLite, hàm nhận dạng được gắn theo connection. Dừng toàn bộ process cũ khi chuyển file; kết nối cũ sẽ không ghi tiếp được sau khi trigger v2 được thiết lập.
5. Khi rollback, giữ nguyên database mới để bảo toàn receipt sau chuyển. Tạo database khác từ archive trước chuyển và mở bằng đúng binary tiền nhiệm. Kiểm tra số lượng, ID và giá trị trước khi cho vận hành lại. Người phụ trách cần đối soát riêng những công việc đã phát sinh sau backup. Đừng đổi riêng binary khi còn dùng database mới. Các bản thử trung gian có định dạng typed trong namespace v1 không phải nguồn cho chuyển trực tiếp từ production; dùng archive sạch cùng binary đã được nghiệm thu.

## Chạy lại kiểm chứng

`tests/check_sandbox_journal.py` lấy source từ commit tiền nhiệm được ghim, chạy publisher và API thực của commit đó trên dữ liệu tổng hợp, giữ một tiến trình qua thời điểm migrate, rồi kiểm tra API mới và replay sau restart. Mẫu action đã duyệt trong phép thử này chỉ là fixture định dạng lưu trữ. Phép thử tích hợp riêng thực thi tám hành động thực trên bốn nhóm đã được duyệt.

Trong môi trường kiểm thử PostgreSQL chỉ dùng loopback và tên DB bắt đầu bằng `amc_test`, chạy `python tests/check_sandbox_journal.py --container amc-test-pg` để dùng pg_dump/pg_restore trong container. Nếu PostgreSQL local thiếu hai công cụ này, `--physical-copy` tạo một bản backup database tĩnh ở cấp PostgreSQL rồi phục hồi sang một database độc lập nữa. Cả hai đường đều mở lại kết quả bằng API cũ và so sánh với dữ liệu trước chuyển.

Chạy `python -m pytest -q tests/test_sandbox_storage_contract.py tests/test_department_dispatch_integration.py` với `AMC_TEST_PG=1` cùng cấu hình test của repository. Ca tích hợp có cạnh tranh giữa hai bộ điều phối local, khởi động lại, thu hồi người duyệt và lưu một revision Studio mới trước khi chạy. Tất cả đầu ra ở trong sandbox.
