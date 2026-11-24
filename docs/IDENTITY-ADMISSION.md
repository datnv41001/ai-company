# Giới hạn thao tác tài khoản và lời mời

## Hợp đồng API

Khi địa chỉ và mật khẩu đúng định dạng, `POST /api/auth/register` trả HTTP 202 với `{"status":"accepted"}` cho cả đăng ký mới và địa chỉ đã đăng ký. Chỉ bản ghi mới tạo thư xác minh. Màn hình giữ lại email và chuyển tiêu điểm sang mật khẩu đăng nhập. Client đang dùng token từ kết quả đăng ký phải chuyển sang `POST /api/auth/login`. Chỉ khi đăng nhập thành công API mới trả token, user ID và thông tin workspace đang chờ xác minh. Đăng nhập sai dùng cùng mã 401 và thông báo cho địa chỉ có hoặc chưa có tài khoản. Các thao tác cần xác minh email vẫn kiểm tra bằng chứng hiện hành. Nếu hộp thư nội bộ không ghi được, hệ thống rollback việc tạo tài khoản mới, ghi sự kiện identity_delivery_unavailable và giữ cùng phản hồi 202. Sau khi sửa hộp thư, người dùng có thể gửi lại yêu cầu tạo tài khoản.

## Quyết định thiết kế

Chính sách khởi đầu cho pilot được đóng phiên bản ở [021_quota_policy.json](../migrations/021_quota_policy.json). Mỗi giá trị bên dưới là số lượt trên số giây trong cửa sổ tính từ lượt đầu.

| Thao tác | Theo nguồn kết nối | Phạm vi bổ sung |
| --- | --- | --- |
| Đăng ký | 120/60 | email chuẩn hóa 4/600 |
| Đăng nhập | 300/60 | email 60/60, cặp IP và email 12/60 |
| Xin mã xác minh | 240/60 | tài khoản 4/300 |
| Dùng mã xác minh | 240/60 | tài khoản 10/300 |
| Tạo và gửi lại lời mời, dùng chung | 300/60 | người gửi 40/60, tenant 100/60, cặp tenant và email người nhận 6/600 |

API đăng ký thu cả hạn mức nguồn và email trước khi phát thư ban đầu. Các dòng xin và dùng mã yêu cầu phiên đã xác thực. Khi gửi lại, API kiểm tra tư cách quản trị và xác định người nhận trong tenant trước khi tính hạn mức. API kiểm tra lại quyền, trạng thái và phạm vi của lời mời trong transaction nghiệp vụ. Lỗi xác thực bearer, dữ liệu sai định dạng, tra cứu lời mời không tồn tại không gửi thư. Kiểm soát lưu lượng ở hạ tầng vẫn cần được nghiệm thu riêng.

PostgreSQL v21 khóa theo thứ tự các khoá HMAC, dùng giờ database, cập nhật các cửa sổ trong cùng transaction READ COMMITTED. API commit khoản sử dụng trước thao tác nghiệp vụ nên lỗi mật khẩu, token hay kênh giao thư vẫn tiêu lượt đã nhận. Nhiều process dùng chung database và JWT secret dùng chung hạn mức. HMAC có miền riêng và bao gồm loại thao tác, chiều, giá trị đã chuẩn hoá. SQLite local dùng BEGIN IMMEDIATE và cùng chính sách. Các bảng chính sách và bộ đếm PostgreSQL thuộc schema riêng, login API chỉ được thực thi hàm admission.

HTTP 429 trả thời gian chờ bằng giây trong `Retry-After`, không gia hạn vì tiếp tục bấm gửi. UI hiển thị số giây cần chờ. Lỗi kho giới hạn trả 503 trước khi tiến hành nghiệp vụ. Người dùng có thể thử lại sau cửa sổ. Pilot dùng cửa sổ cố định nên có thể nhận hai cụm sát biên cửa sổ. Người dùng chung NAT có thể cùng tiêu hạn mức của nguồn. Các ngưỡng cần đo thêm trước khi vận hành thật.

## Reverse proxy và ghi nhận vận hành

Docker và launcher native chạy Uvicorn với `--no-proxy-headers` để giữ địa chỉ peer thật. Mặc định lấy địa chỉ socket; IPv6 dùng prefix /64. Với reverse proxy riêng, cấu hình `AMC_IDENTITY_TRUSTED_PROXIES` bằng danh sách CIDR của **peer trực tiếp** đã quản lý. Proxy phải xóa đầu vào X-Real-IP của client rồi đặt đúng một giá trị IP đã xác thực. X-Forwarded-For không tham gia cách tính. Cấu hình CIDR sai sẽ làm startup thất bại. Giữ allowlist rỗng khi chạy trực tiếp.

Logger `amc.identity_limits` phát sự kiện giới hạn và lỗi admission, kèm thao tác và thời gian chờ nếu có. Thiết lập thu mức INFO nếu cần theo dõi sự kiện 429. Toàn bộ dữ liệu diễn tập là dữ liệu tổng hợp. Chủ database có thể tổng hợp áp lực theo từng chiều bằng câu lệnh dưới. Một yêu cầu có thể chạm nhiều chiều; các số này không cộng thành lượt yêu cầu duy nhất. Bộ đếm active được đặt lại khi sang cửa sổ mới. Mỗi thao tác dọn tối đa 64 cửa sổ đã quá hạn hơn 24 giờ. Khi không có lưu lượng, bộ dọn chạy tiếp ở lượt sau.

```sql
SELECT action, dimension, count(*) AS windows, sum(denied) AS window_denials
FROM amc_acl.identity_windows
GROUP BY action, dimension
ORDER BY action, dimension;
```

## Chạy lại trên máy khác và khôi phục

1. Dùng checkout của PR, chạy `python scripts/init_env.py` và `docker compose -p amc-identity-admission up -d --build` với volume mới, thông tin local riêng và cổng trống. Migration owner chạy trước API. PostgreSQL engine của Compose là 16.6. Dùng mail capture nội bộ.
2. Chạy `python -m ruff check .` và `python -m pytest -q tests/test_identity_quota.py` với dependencies trong requirements của dự án. Để chạy cả PostgreSQL, dùng database bỏ được có tên bắt đầu bằng `amc_test`, biến môi trường và lệnh của job API trong [.github/workflows/ci.yml](../.github/workflows/ci.yml). Bộ tuần tự lịch sử kiểm tra v1–v20 lên v21, migration lần hai và backup/restore. Job Chromium chạy luồng đăng ký rồi đăng nhập ở hai kích thước.
3. Trước nâng bản có dữ liệu, sao lưu database và cấu hình secret ở đúng nơi lưu nội bộ, diễn tập restore sang database riêng. Để rollback, ngừng writer, ghim lại phiên bản main v20, trỏ đến backup v20 đã khôi phục và xác minh marker, tenant, invitation, QA/snapshot. Nếu đã có ghi mới, đối soát các thay đổi sau backup trước khi chuyển lưu lượng. Không hạ marker thủ công. Bản v20 sẽ từ chối schema v21.
4. Các release gate còn mở gồm phục hồi tài khoản, MFA hoặc SSO, email giao thực, ingress/telemetry vận hành, thẩm định quota và giám sát lưu lượng phân tán. Commercial GA tiếp tục NO-GO.
