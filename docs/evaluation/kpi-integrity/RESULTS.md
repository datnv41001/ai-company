# Kết quả kiểm KPI trước khi giao campaign

**Luồng Rõ cần đo 2 lịch được nhân sự xác nhận trên 3 yêu cầu, tức 66,7%.** Cả ba yêu cầu thiếu nguồn attribution, có một ca hủy sau khi đã xác nhận. Số phiên web của kế hoạch trong kỳ là 0. Dùng số phiên làm mẫu số sẽ khiến người đọc mất một kết quả có thể đối soát.

| Kiểm định | Kết quả |
|---|---|
| Renderer cũ trên `f1064d29` | Tái tạo được nguyên hai câu sai của #45. Một câu theo dõi “số yêu cầu hoàn tất trên lượt vào trang”, câu kia dùng “tỷ lệ hoàn tất trên lượt vào”. [Biên bản trước sửa](evidence/predecessor-red.json) |
| Luồng Rõ qua API quản trị và CRM | Hai manifest có cùng định nghĩa. Brief và kế hoạch ghim đúng KPI. Báo cáo sau ba yêu cầu là 2/3 trong 21 ngày. [Định nghĩa, biên nhận sự kiện và số đếm](evidence/luong-ro.json) |
| Sau khi editor sửa nội dung | Dùng lại câu sai ở phương pháp nội bộ, phương pháp gửi khách và ad. API từ chối ký cả ba. Bản sửa đúng được ký từng nhóm, kiểm QA và gửi tới tài khoản khách tổng hợp. Bản giao giữ riêng câu đếm phiên web như chỉ số phụ. [Snapshot, revision, digest và nguyên văn nội dung khách nhận](evidence/luong-ro-signed.json) |
| Holdout Mực Chuẩn | Brief mới đo buổi thực hiện trên lịch xác nhận. Một trong ba lịch hoàn tất, cho tỷ lệ 33,3% trong 14 ngày. Có một hủy. Cùng hệ thống vẫn phân biệt thứ tự hai biến cố của hai doanh nghiệp. [Receipt hành trình](evidence/holdout.json) |
| Giao diện thật | Chromium tạo và lưu KPI có cấu trúc bằng bộ chọn và bàn phím, kiểm dữ liệu đã lưu; tạo brief với đúng ID được phê duyệt và đọc 66,7% từ Analytics. Không tràn ngang ở 1280, 820 và 390 px, cả light/dark. [18 ảnh gốc](evidence/chromium.zip) · [Kết quả trình duyệt](evidence/browser-checks.json) |

Ở ca cửa sổ lịch sử của holdout, có hai lịch thiếu nguồn và một lịch có phiên đã xác định. Ở hành trình API riêng, cả ba lượt đều thiếu nguồn. Hai trường hợp cùng cho 1/3; khác biệt attribution được giữ trong từng biên bản. Mẫu số bằng 0 trả null. Phép đo gắn đúng plan và chủ thể được phép xem.

Bộ xác minh kiểm chính xác các trường định nghĩa, phương pháp giao khách, phép đo ở ad, một số diễn giải KPI trong lời quảng cáo và chiến lược. Người biên tập có thể giữ phần giả thuyết hoặc một câu chỉ số phụ đã được xác minh khi sửa mẫu số. Các cách diễn đạt tự nhiên khác vẫn cần reviewer đọc trên phiên bản cuối. Tách riêng phiên bản có lỗi, bản sau sửa và tài liệu người nhận được.

Bước ký/duyệt mẫu trong SQLite dùng một worker completion tổng hợp. Các endpoint tri thức, luồng quyết định, snapshot và portal chạy thật. Hành trình KPI/CRM và trình duyệt dùng PostgreSQL có RLS với dữ liệu tổng hợp. Không phát sinh lần gọi model mới hoặc phí provider. Chưa có người làm Marketing, reviewer nghiệp vụ hoặc Sales thật tham gia. Chi phí máy, giờ lao động, tiết kiệm và chi phí trên đơn vị được khách thực chấp nhận vẫn chưa đo được. [Runbook và giới hạn](HANDOFF.md) · [Pilot cho người làm nghề](PILOT.md)

## Lần xác minh trên mã đã bàn giao

Commit mã nguồn `08e35075d22f5dab8e8a46f48399f6b2ac441c0a` đạt 19/19 ca hồi quy cục bộ trong 289,49 giây với SQLite, PostgreSQL có RLS và Chromium. Lệnh chọn năm tệp test cùng ca channel edition SQLite. SHA-256 của gói 18 ảnh là `1444177bda9b43038c89dbf8ad681b97207d31982c919f8cd98a6061251c8a8a`.

```powershell
python -m pytest -q tests/test_measurement_integrity.py tests/test_measurement_edition.py tests/test_brief_knowledge.py tests/test_campaign_appointments.py tests/test_campaign_planner.py tests/test_channel_editions.py::test_channel_edition_sqlite
```
