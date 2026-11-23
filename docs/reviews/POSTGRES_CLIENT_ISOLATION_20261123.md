# Phân quyền xem theo khách hàng trong cùng agency

**Kết quả ngày 23/11/2026.** Hai tài khoản khách hàng thuộc cùng một agency đã đăng nhập bằng JWT, gửi yêu cầu HTTP đến FastAPI và nhận đúng tập ID được cấp. Kết quả truy vấn trực tiếp sáu bảng bằng tài khoản PostgreSQL của API trùng với kết quả qua HTTP. Kiểm thử dùng PostgreSQL 16.16 thật trên Windows, kết nối loopback và dữ liệu giả lập.

## Ai được xem gì?

| Thành viên | Quyền trong một agency |
|---|---|
| `client_viewer` | Xem một hồ sơ khách hàng được gán và các thương hiệu, chiến dịch, nhiệm vụ, tài liệu, đề xuất hành động thuộc hồ sơ đó. Bao gồm bản nháp của chính khách hàng. Mọi thương hiệu thuộc cùng hồ sơ đều nằm trong phạm vi. |
| `viewer` | Nhân sự nội bộ xem toàn agency. Chủ dự án cần phân loại các tài khoản cũ và chuyển từng người bên ngoài sang `client_viewer` đúng hồ sơ. |
| `editor`, `admin`, `owner` | Giữ quyền nội bộ của starter. API cấp, đổi và thu hồi quyền khách hàng yêu cầu admin hoặc owner. Nhật ký agency chỉ hiển thị cho admin/owner. |

Một người có thể thuộc nhiều workspace. Mỗi cặp người dùng và agency có một membership. Giao diện cho phép chọn workspace theo tên. Quyền ở agency này được xác định độc lập với vai trò trong một workspace khác.

## Cấp, đổi và thu hồi

Dùng bearer token của người quản trị và các đường dẫn dưới đây. `{tenant}` là agency, `{user}` là ID người dùng. Khách cần có tài khoản đã đăng ký theo cơ chế hiện tại của starter.

| Tác vụ | API | Dữ liệu và kết quả |
|---|---|---|
| Cấp lần đầu | `POST /api/tenants/{tenant}/members` | `{"email":"reader@example.com","role":"client_viewer","client_id":"<id-khách-hàng>"}` → 201 |
| Chuyển viewer cũ hoặc đổi khách hàng phụ trách | `PUT /api/tenants/{tenant}/members/{user}/client-scope` | `{"client_id":"<id-khách-hàng>"}` → 200. Có audit ID cũ và mới trong cùng giao dịch. |
| Thu hồi | `DELETE /api/tenants/{tenant}/members/{user}/client-scope` | 204. Membership khách hàng được gỡ. Yêu cầu đọc kế tiếp bằng token cũ trả 404. |

API từ chối role khách thiếu client ID, từ chối ghép role nội bộ với client ID và kiểm tra khách hàng thuộc đúng tenant. Kiểm tra quyền áp dụng trên từng yêu cầu. Việc thu hồi không thể thu lại nội dung mà người dùng đã tải xuống trước đó.

## Hai tầng kiểm soát

- **API** xác thực JWT, đọc membership và lọc truy vấn theo tenant/client. Chi tiết chiến dịch và danh sách nhiệm vụ ngoài phạm vi trả 404. SQLite dùng cùng quy tắc ở lớp API.
- **PostgreSQL** lưu `memberships.client_id`, kiểm tra role/phạm vi và dùng khóa ngoại ghép để buộc bản ghi con thuộc cùng tenant với cha. RLS lọc từ client đến brand, campaign, task, deliverable và action. Nhật ký có policy riêng. Bảng users, tenants và memberships cũng có policy.
- **Kết nối** dùng `amc_runtime` tách khỏi chủ sở hữu bảng. API kiểm tra role, RLS và phiên bản schema khi khởi động. Context người dùng/tenant do backend xác lập từ phiên đã xác thực, có hiệu lực trong giao dịch. PostgreSQL tự bỏ context khi commit hoặc rollback. Ba hàm trợ giúp có search path cố định, quyền thực thi chỉ cấp cho runtime và chủ sở hữu.
- **Ranh giới tin cậy.** Credential DB của runtime thuộc backend. Người dùng cuối chỉ nhận JWT. Người có credential DB dùng chung có thể tự đặt context. Thiết kế này bảo vệ đường API và những truy vấn thiếu điều kiện lọc trong backend tin cậy. Quản trị viên DB có đặc quyền vẫn có thể truy cập dữ liệu.

## Bằng chứng nghiệm thu

| Phép thử | Dữ liệu / kết quả |
|---|---|
| A và B cùng agency | Mỗi khách có 2 brand, 2 campaign, 14 task, 2 tài liệu và 2 đề xuất hành động. So sánh **tập ID chính xác** ở cả hai hướng cho danh sách và nhiệm vụ. Owner xem được cả 4 campaign. |
| Đọc theo ID và quyền ghi | Chiến dịch và nhiệm vụ của khách kia trả 404 kể cả khi biết ID. Client viewer không tạo được khách mới, không đọc được audit. Truy vấn SQL UPDATE tác động 0 hàng, INSERT bị từ chối với SQLSTATE 42501. |
| SQL trực tiếp và connection pool | Với đúng tài khoản của API, SELECT không có WHERE trên sáu bảng chỉ trả ID của khách đang đăng nhập. Cùng một kết nối vật lý đổi từ A sang B. Trước khi đặt context và sau commit/rollback, các bảng nghiệp vụ trả 0 hàng. |
| Đồng thời | 4 luồng thực hiện 32 lượt GET luân phiên trên hai token. Mỗi phản hồi khớp đúng tập dữ liệu của chủ token. |
| Quản trị quyền | Đổi A sang phạm vi B có hiệu lực ngay với token cũ. Thu hồi thì token cũ mất quyền ở agency, người còn lại tiếp tục truy cập. Có audit đổi/thu hồi. Phạm vi thuộc tenant khác bị từ chối. |
| Tương thích | Tài khoản in-house có client nội bộ, có thể đồng thời làm client viewer ở agency khác. Migration chạy trên DB starter đã có dữ liệu, chạy lại thành công, giữ viewer nội bộ và cô lập đúng sau khi chuyển viewer sang khách đã chọn. API từ chối kết nối bằng tài khoản migration có đặc quyền. |

Toàn bộ suite với PostgreSQL được bật có **21 test đạt**. Trong đó **6 test chạy qua Uvicorn/HTTP với PostgreSQL thật**, 3 bài nghiệm thu quyền qua API trên SQLite và 12 regression test ban đầu trên SQLite. Một phép kiểm tra nâng cấp DB có dữ liệu chạy riêng và đạt. Ruff và kiểm tra cú pháp JavaScript đều đạt. Cảnh báo Starlette liên quan đến TestClient ở bộ test SQLite. Bài test HTTP PostgreSQL dùng httpx qua socket thực.

## Dùng bản mã

**Compose để phát triển.** Đặt `POSTGRES_PASSWORD`, `AMC_RUNTIME_PASSWORD` và `JWT_SECRET` ngẫu nhiên, riêng biệt trong môi trường local. Với cấu hình DSN của Compose, dùng mật khẩu chỉ gồm chữ/số ngẫu nhiên để tránh vấn đề mã hóa URL. Chạy `docker compose up -d --build`. Dịch vụ `migrate` cập nhật schema trước khi `api` kết nối bằng `amc_runtime`. Role đã tồn tại sẽ giữ mật khẩu đã cấp. Khi nâng cấp volume cũ, dừng API cũ, sao lưu, dùng đúng mật khẩu của chủ DB và rà danh sách viewer cũ trước khi mở lại truy cập. Compose đã qua `docker compose config -q`. Máy kiểm thử chạy PostgreSQL trực tiếp do Docker Engine từ chối quyền truy cập.

**Chạy lại test trên PostgreSQL riêng.** Từ thư mục dự án, tạo môi trường Python 3.12, cài `requirements-dev.txt`. Dùng một DB cục bộ dành riêng cho test, tên bắt đầu bằng `amc_test`. Đặt `AMC_MIGRATION_DSN` cho chủ DB, `AMC_RUNTIME_PASSWORD` cho role ứng dụng, `DATABASE_URL` dạng `postgresql+psycopg://amc_runtime:…@127.0.0.1:…/amc_test…`, `JWT_SECRET` mạnh và `APP_ENV=local`. Lệnh PowerShell:

~~~powershell
$env:AMC_TEST_PG = '1'
$env:PYTHONPATH = '.'
python migrations/apply.py
python -m pytest -q
python -m ruff check app tests migrations
~~~

Để lặp phép thử nâng cấp, trỏ **cả hai DSN** đến một DB test trống thứ hai trên cùng cluster, sau đó chạy `python tests/check_postgres_upgrade.py`. Quy trình CI kèm theo chuẩn bị hai DB này tự động. Đợt nghiệm thu đã chạy trên máy cục bộ. Tệp CI chưa được đẩy lên GitHub.

**Tệp chính.** [SQL migration và RLS](../../migrations/002_client_isolation.sql) · [Transaction context và bộ lọc API](../../app/access.py) · [Test quyền truy cập](../../tests/test_client_isolation.py) · [Test nâng cấp](../../tests/check_postgres_upgrade.py).

Phạm vi nghiệm thu là các đường đọc và sáu nhóm dữ liệu nghiệp vụ hiện có. File đính kèm, vector search, export, cache hoặc worker bổ sung về sau cần phép thử cách ly tương ứng trước khi giao khách. Quyền duyệt hoặc ghi của người dùng khách nằm ngoài phạm vi vai trò chỉ đọc này.
