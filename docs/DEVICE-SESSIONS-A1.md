# Phiên thiết bị AMC · A1

Nhánh này xếp trên Business Profile C1 v22, xét duyệt riêng. Migration 023 nâng ứng dụng lên v23. Đăng ký tiếp tục trả HTTP 202. Login thành công vẫn trả bearer, đồng thời tạo một phiên thiết bị. Access có hạn 5 phút. Family hết hạn sau 24 giờ không refresh hoặc tối đa 7 ngày. Mọi access của v22 thiếu `sid`, epoch phiên hoặc epoch credential bị từ chối; người dùng đăng nhập lại khi cutover. [Thiết kế được review](IDENTITY-SESSION-RECOVERY.md)

## Người dùng và API

- Sau khi đăng nhập, mở **Phiên đăng nhập trên thiết bị** để xem các phiên của tài khoản, thời điểm refresh gần nhất và thu hồi thiết bị khác. Thiết bị ghi nhãn trình duyệt chung. Muốn thu hồi phiên khác sau 5 phút, người dùng xác thực lại mật khẩu tại chỗ. Nút **Đổi tài khoản** kết thúc phiên hiện tại trước khi mở lại trang đăng nhập.
- `GET /api/me/sessions`, `DELETE /api/me/sessions/{sid}`, `POST /api/auth/reauthenticate` và `POST /api/auth/logout` xác thực bearer. `POST /api/auth/refresh` và `POST /api/auth/logout-cookie` kiểm Origin, cookie host-only `Secure`, `SameSite=Lax` và CSRF header. Refresh secret có `HttpOnly`. Xóa phiên qua cookie còn kiểm sid của tab để xử lý trường hợp người khác đã đăng nhập ở tab khác. Native client dùng HTTPS cookie jar với CSRF proof hoặc đăng nhập lại.
- Mỗi lần refresh khóa family theo account, thay digest và ghi dấu grant đã tiêu trong cùng transaction. Reuse đúng secret đã tiêu thu hồi cả phiên. Secret ngẫu nhiên sai bị từ chối. Hai tab Chrome dùng Web Locks khi refresh. Nếu server đã commit mà trình duyệt mất response thì lần dùng lại grant cũ dẫn đến đăng nhập lại. UI không tự phát lại lệnh thay đổi dữ liệu.
- API kiểm `sid`, hai epoch, thời hạn, chữ ký và khóa triển khai trên PostgreSQL primary. Lỗi đọc trạng thái phải đóng request. Tất cả thay đổi password hash trong database, kể cả từ cơ chế recovery sau này, tăng credential epoch trong trigger. Session và refresh trước đó mất hiệu lực. API recovery và email thật sẽ có phạm vi riêng.

## Ranh giới quyết định

Read đã được kiểm tra trước logout có thể hoàn tất. Request tiếp theo phải kiểm tra lại. Với thay đổi qua SQLAlchemy Session của request, `before_commit` kiểm lại access và trạng thái phiên trong từng transaction, kể cả khi route đã commit quota rồi bắt đầu transaction mới. Tại ranh giới quyết định trên primary, mutation giữ shared advisory lock của user đến hết commit. Logout/refresh/thay credential dùng exclusive lock cùng định danh. Logout commit trước thì mutation rollback. Mutation vượt ranh giới trước thì logout đợi đến lúc mutation commit. Giới hạn chờ lock 5 giây. SQLite chỉ phục vụ pilot local, PostgreSQL là chuẩn nghiệm thu cạnh tranh. [Session guard](../app/session_state.py) · [Ca hai HTTP listener và hai thứ tự commit](../tests/test_device_sessions.py)

## Nâng cấp, xoay khóa và restore

1. Dừng writer, sao lưu database, giữ keyring có kiểm soát ngoài bản dump. Máy sạch dùng `python scripts/init_env.py`. Cụm v21/v22 dùng `python scripts/init_env.py --upgrade-identity` khi ứng dụng đã dừng. Bước chuyển giữ nguyên từng byte khóa HMAC quota dẫn xuất cũ, tạo vật liệu độc lập cho proof và restore. Native launcher Windows giữ cấu hình cạnh cluster riêng. Dùng `docker compose up -d --build` trong lab riêng. Migration phải chạy bằng owner và API phải chạy qua `amc_runtime` bị giới hạn.
2. `JWT_SECRET` chỉ ký access mới. Đổi secret đồng bộ các API worker sẽ làm access cũ hết hiệu lực, refresh còn hợp lệ tiếp tục dùng được. `AMC_QUOTA_KEY` kiểm qua fingerprint ở database. Nếu cần đổi chính khóa quota, dừng toàn bộ admission, chờ mọi cửa sổ hoạt động kết thúc, chạy `python migrations/apply.py --identity-operation rotate-quota` với key mới rồi cấp cùng key cho mọi worker API. Command từ chối khi cửa sổ còn hiệu lực. Lịch ngừng admission phải được duyệt trước khi vận hành.
3. `AMC_DB_PROOF_KEY` bảo vệ actor, email challenge và signed append của C1. Khi xoay, dừng các API writer, thay secret trong kho bảo mật rồi chạy `python migrations/apply.py --identity-operation rotate-proof` bằng publisher, khởi động lại toàn bộ writer với key mới và kiểm readiness, xác minh email và một append C1 tổng hợp. Giá trị sai làm startup proof thất bại. [Các consumer ở schema 017](../migrations/017_verified_identity.sql) · [019](../migrations/019_onboarding.sql) · [022](../migrations/022_business_knowledge.sql)
4. Restore **vào database cách ly khỏi API**. Cấp `AMC_SESSION_GENERATION` mới ngoài bản dump rồi chạy `python migrations/apply.py --identity-operation restore-fence` với migration DSN của bản khôi phục. Transaction kiểm generation đã đổi, thu hồi toàn bộ thiết bị còn hoạt động và xóa dấu refresh cùng challenge tiền restore. API dùng generation cũ phải trả 503, API cấu hình mới từ chối access cũ. Chỉ chuyển kết nối sau khi đã thử cả hai. Rollback cần dừng writer và buộc đăng nhập lại; chạy lại binary v22 với secret JWT cũ có thể phục hồi đường chấp nhận token v22, nên luồng rollback cần khóa JWT mới trước khi mở cổng. [Diễn tập dump/restore](../tests/check_postgres_upgrade.py)

## Chạy lại và giới hạn

```sh
python -m pip install -r requirements-dev.txt
python -m ruff check app tests migrations scripts
python -m pytest -q tests/test_device_sessions.py tests/test_identity_quota.py
```

Dùng biến môi trường và PostgreSQL bỏ được trong job `api-tests` để chạy cả hai provider và đường nâng v1–v22 → v23. Các ca concurrency chạy thực qua hai Uvicorn listener dùng cùng primary và role hạn chế. Đọc mã lab độc lập trước khi chạy OIDC. Keycloak trong Docker đã cho thấy thiết bị còn refresh được sau administrative password reset. Lệnh logout tường minh sau đó ngăn refresh. AMC hiện xử lý đổi credential local qua trigger; liên kết IdP cần event và đối soát có bằng chứng riêng. [Keycloak lab](../engineering/identity-lab/README.md) · [CI của phép thử](https://github.com/datnv41001/ai-company/actions/runs/45518450304/job/138883891993)

Ràng buộc vận hành còn mở gồm định kỳ dọn session/grant hết hạn, chốt ngưỡng tải theo NAT, audit vận hành, HA, recovery đầy đủ và chính sách cutover cho client không có HTTPS. Commercial GA tiếp tục NO-GO.
