# Nghiệm thu kỹ thuật B/C, 26/11/2026

Các file trong thư mục này được sản xuất bằng API AMC từ hai bộ đầu vào tổng hợp. Mỗi package có digest, danh mục SHA-256 từng file và receipt do tài khoản QA fixture khác người dựng quyết định. Mỗi landing đi qua một lượt xem và một submission; hồ sơ appointment lưu trạng thái yêu cầu, chưa phải lịch được xác nhận.

| Đầu ra local | RFQ | Appointment |
| --- | --- | --- |
| Số byte của gói Creative | 367.710 | 363.370 |
| Thời gian dựng và tính digest Creative | 774,37 ms | 255,96 ms |
| Số byte HTML landing | 4.155 | 4.237 |
| Thời gian dựng và tính digest trang | 7,56 ms | 0,48 ms |

Đây là từng lần dựng thực tế trên Windows của fixture, gồm thời gian thực thi native trong môi trường có tác vụ song song. Chưa có phân vị độ trễ, thời gian của nhân sự, chi phí toàn phần hoặc kết luận tiết kiệm. Chi phí provider chưa phát sinh; renderer và bridge ghi số lần gọi bên ngoài bằng 0 trong receipt. [Receipt Creative RFQ](rfq/creative/receipt.json) · [Receipt Creative appointment](appointment/creative/receipt.json) · [Receipt trang RFQ](rfq/landing/receipt.json) · [Receipt trang hẹn](appointment/landing/receipt.json).

Chromium 157.0.8103.52 mở hai ca ở viewport 1280/820/390. Kích thước nội dung thực của trang trong hộp xem lớn lần lượt là 1234/784/362 px. Hai cỡ lớn hiển thị hai cột, điện thoại một cột. Browser kiểm metadata, tải ảnh, giải mã media thành các khung hình khác nhau ở giây 0 và 3,5, đọc duration sáu giây, chạy biểu mẫu hợp lệ và hiển thị biên nhận. Mỗi ca có 14 ảnh sáng/tối ở ba kích thước, gồm hai ảnh trạng thái form. [Phiên RFQ](screens/rfq/sessions.json) · [Phiên appointment](screens/appointment/sessions.json).

Trong checkout và môi trường Python nghiệm thu không có checkpoint diffusion đã đăng ký cho AMC, các module `diffusers`, `comfy`, `torch` hoặc CLI `sd-cli` / `comfy-cli` để thử kèm giấy phép model. Baseline đã được kiểm chứng với Pillow, font OFL và nguồn hình học AMC. Chưa có bằng chứng thực thi hay quyền sử dụng model ảnh sinh trong sản phẩm. Video là file VP8 local từ ba cảnh tĩnh, phù hợp cho thử bố cục và CTA. Chất lượng sáng tạo thực địa vẫn cần người làm nghề nghiệm thu.

Chạy `python -m pytest -q tests/test_production_evidence_bundle.py tests/test_creative_master_export.py` để kiểm tra bộ bàn giao, đối chiếu các digest giữa browser và API, rồi dựng lại master. Để kiểm tra PostgreSQL, bật cấu hình runtime test có quyền giới hạn như CI và chạy `tests/test_production_studios.py`. Hai ca bao gồm cả kế hoạch cũ thiếu đơn vị bán; hệ thống yêu cầu bổ sung nguồn trước khi dựng form. [Quy trình đầy đủ](README.md).

Ở lần chạy đầu, PostgreSQL từ chối đọc lại bản ghi ORM đã hết hiệu lực sau commit do chính sách RLS. API nay trả digest đã đối chiếu trong giao dịch. Kế hoạch cũ thiếu đơn vị bán từng đi tới bước dựng RFQ mới lỗi; nay API báo cần duyệt đơn vị trước khi sinh trang. Với Chromium, SQLite bộ nhớ dùng chung làm các phiên đăng nhập cạnh tranh. Fixture cuối dùng file WAL và kết nối riêng. Iframe ban đầu chặn cả event submit; giờ cho dùng form trong sandbox, giữ CSP chặn submit ra mạng và kiểm receipt qua bridge. Bộ test lưu riêng các ca này để người tiếp quản có thể chạy lại.
