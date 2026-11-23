# Bắt đầu ở đây khi tiếp quản AI Marketing Company

## 1. Lấy đúng mã trên máy mới

Repo chính là [datnv41001/ai-company](https://github.com/datnv41001/ai-company). Nhánh đang đánh giá cho cổng duyệt là `feature/client-delivery-handoff`, bắt đầu từ `55dada3`. Sau khi PR được merge, dùng `main`. Để hai máy chạy chính xác cùng mã, sao chép SHA đầy đủ từ máy bàn giao và đối chiếu sau khi checkout.

~~~sh
git clone https://github.com/datnv41001/ai-company.git
cd ai-company
git fetch origin --prune
git switch feature/client-delivery-handoff
git pull --ff-only
git rev-parse HEAD
git status --short --branch
~~~

Nếu tiếp tục viết code từ một SHA cụ thể, dùng `git switch -c ten-nhanh-moi SHA_DA_XAC_NHAN`. Với nhánh đang sửa dở, commit và push phần cần bàn giao trước khi sang máy khác. Một bản ZIP chỉ thể hiện thời điểm xuất. Git đồng bộ mã, migration và các quyết định nghiệp vụ; database, tài khoản, file cấu hình riêng và Docker volume nằm tại từng máy.

## 2. Chạy bằng Docker từ một checkout sạch

Cần Git, Docker Engine đang hoạt động và Compose v2. Từ thư mục gốc, chạy trong PowerShell hoặc Bash:

~~~sh
docker info
docker run --rm -v "${PWD}:/src" -w /src python:3.12-slim python scripts/init_env.py
docker compose -p amc-dev config -q
docker compose -p amc-dev up -d --build
docker compose -p amc-dev ps -a
~~~

Lệnh đầu tiên tạo file cấu hình là lệnh chạy `scripts/init_env.py`; nếu máy đã có Python có thể chạy `python scripts/init_env.py` trực tiếp. Script giữ file .env đã tồn tại. Với cấu hình cũ, kiểm tra ba biến `POSTGRES_PASSWORD`, `AMC_RUNTIME_PASSWORD`, `JWT_SECRET` đã có giá trị riêng, ngẫu nhiên. Giữ đúng mật khẩu cũ nếu tiếp tục dùng volume cũ.

Mở [giao diện](http://127.0.0.1:8000), [health](http://127.0.0.1:8000/api/health) và [hợp đồng API](http://127.0.0.1:8000/docs). Trạng thái mong đợi: service db healthy, migrate thoát với mã 0, api healthy. Đăng ký một tổ chức Agency bằng dữ liệu thử. Nếu cổng 8000 đã được dùng, đặt `AMC_HTTP_PORT=8001` trong .env trước khi chạy Compose và dùng cổng đó trên trình duyệt.

- Chẩn đoán bằng `docker compose -p amc-dev logs --tail=80 migrate api`. Docker Desktop trên Windows cần chạy và tài khoản phải có quyền truy cập Docker Engine. Đường chạy PostgreSQL native trên Windows nằm trong [README](README.md).
- Dừng bằng `docker compose -p amc-dev stop`. Khởi động lại cùng dữ liệu bằng `docker compose -p amc-dev up -d`. Giữ nguyên project name và volume. Khi đổi commit, dùng lại `up -d --build` để chạy migration tương ứng. Không dùng tùy chọn xóa volume cho DB cần giữ.
- Khi chuyển cả dữ liệu, sao lưu bằng công cụ PostgreSQL, truyền bản sao và bí mật qua kênh riêng được phép, phục hồi trên DB riêng và kiểm tra quyền bằng tài khoản runtime. Không push dữ liệu hay khóa vào Git. Cùng commit giúp đồng bộ logic; phiên bản dependency nằm trong khoảng cho phép có thể đổi khi build lại. CI ghi lại các phiên bản và image thực dùng.

## 3. Hợp đồng nghiệp vụ hiện tại · schema 3

| Quy tắc | Nơi sửa khi thay đổi | Bằng chứng phải chạy |
|---|---|---|
| Người nội bộ có thể xem bản làm việc. Khách chỉ thấy hồ sơ client của mình và phiên bản đã được chia sẻ. | [Bộ lọc API](app/access.py), [policy PostgreSQL](migrations/003_delivery_policies.sql) | [Test cách ly](tests/test_client_isolation.py), [draft riêng tư](tests/test_delivery.py) |
| Sửa bản làm việc hủy QA cũ. Người tạo và người sửa cuối không tự QA. Admin/owner chỉ chia sẻ bản đã qua QA, có preview và hạn trong tương lai. | [API nội bộ](app/main.py), [luồng bàn giao](app/delivery.py) | [Test vòng đời](tests/test_review_lifecycle.py) |
| Một request là một snapshot. SHA-256 bao gồm đúng tiêu đề và preview UTF-8. Mỗi quyết định lưu ID snapshot, digest, người, giờ, ý kiến. Yêu cầu mới đóng phiên bản đang chờ. | [Model](app/delivery_models.py), [DDL](migrations/003_delivery_tables.sql), [ADR-003](docs/ADR-003-CLIENT-DELIVERY.md) | Test hai quyết định đồng thời, retry, sửa v1→v2, hết hạn, thu hồi |
| Quyền xem, bình luận và quyết định tách biệt. Grant có thể giới hạn đến brand/campaign trong một client. Hội đồng duyệt là những người còn quyền trong đúng nhóm đó. | PUT `/api/tenants/{tenant}/members/{user}/review-rights` | Test viewer, reviewer, rescope và token cũ |
| Duyệt nội dung chỉ ghi nhận quyết định. Thực thi hành động ra ngoài vẫn bị khóa. | [Đường execute](app/main.py) | [Test hồi quy](tests/test_api.py) |
| Giao diện hiển thị phiên bản, hạn theo giờ máy người xem, nội dung, lịch sử và hành động theo quyền. | [Cổng duyệt](app/static/reviews.js) | [Test trình duyệt desktop/mobile](tests/browser_delivery.py) |

**Thử một vòng bằng dữ liệu giả.** Dùng ba tài khoản khác nhau cho editor, QA/admin và khách. Các tài khoản cần đăng ký trước. Admin thêm thành viên nội bộ hoặc `client_viewer` qua POST `/api/tenants/{tenant}/members`. Với khách, gán đúng client_id và dùng PUT `review-rights` nếu người đó cần bình luận hoặc duyệt. Ví dụ body `{"can_comment":true,"can_decide":true,"brand_id":null,"campaign_id":null}` áp dụng cho hồ sơ client đã gán. Việc gửi lại body với cờ false thu hồi khả năng tương ứng. Tạo client → brand → campaign. Trong giao diện, editor mở **Soạn và bàn giao cho khách**, tạo bản nháp rồi gửi QA. QA đăng nhập đúng workspace, duyệt và chia sẻ kèm hạn. Khách đăng nhập ở trình duyệt riêng, chọn workspace của agency, mở phiên bản và phản hồi. Agency xem lại kết quả trong cùng danh sách bàn giao. Quyền quản trị thành viên hiện thao tác qua API docs.

## 4. Kiểm thử và dữ liệu nâng cấp

[Workflow CI](.github/workflows/ci.yml) là lệnh tham chiếu chi tiết cho một máy Linux sạch. Job `api-tests` chạy Ruff, SQLite, HTTP với PostgreSQL thật, nâng cấp từ v1 và từ v2 có dữ liệu. Job `compose-browser` build đúng repo bằng Compose và thao tác qua Chromium với hai kích thước. Kiểm tra job trên **đúng commit** của PR.

Khi chạy pytest nhanh với SQLite, đặt DATABASE_URL tới SQLite thử riêng, cài `requirements-dev.txt`, chạy `python -m pytest -q`. Các bài PostgreSQL bị skip trong chế độ này. Khi chạy suite đầy đủ, dùng DB trống cục bộ tên bắt đầu bằng `amc_test`, runtime role `amc_runtime`, có `AMC_TEST_PG=1` và chạy migration trước pytest. Tách hai DB thử trống cho `tests/check_postgres_upgrade.py` và cùng script kèm `--from-v2`. Với test trình duyệt, cài `requirements-browser.txt`, chạy `python -m playwright install chromium` rồi trỏ `AMC_BROWSER_TEST_URL` đến một instance loopback chỉ có dữ liệu thử. Test tạo tài khoản mẫu. Không chạy các kịch bản này trong DB đang phục vụ người dùng.

Schema v3 giữ bản nháp và quyền cũ trong DB; khách ngoài được backfill grant chỉ xem và có danh sách review rỗng tới lần chia sẻ đầu tiên. Không tự chuyển viewer nội bộ thành khách. [Trình chạy migration](migrations/apply.py) ghi version trong cùng giao dịch. Xem quy trình phục hồi trong [ADR-003](docs/ADR-003-CLIENT-DELIVERY.md).

## 5. Bàn giao sau mỗi thay đổi

Người hoặc AI sửa mã cập nhật **cùng PR** phần hợp đồng tương ứng trong file này. Chú thích cạnh mã cho lý do khó suy ra, chẳng hạn thứ tự khóa, ranh giới dữ liệu giữa agency/khách hoặc quy đổi thời gian. Nếu đổi schema, quyền, state machine hoặc tích hợp, ghi tradeoff và rollback trong ADR; giữ lại migration đã phát hành và thêm migration mới. Đặc tả, kế hoạch và kết quả đã được kiểm thử cần được ghi rõ trạng thái riêng.

Ghi vào PR: hành vi cũ → mới, đường vào API/UI, files chính, phiên bản schema, lệnh kiểm thử, kết quả đạt/skip, link CI, dữ liệu cần chuyển và điểm còn mở. Người nhận chạy lại thay đổi từ SHA của PR và lấy dữ liệu mẫu qua fixture. Chưa merge thì nêu tên nhánh. Khi hoàn tất một work package, cập nhật mục tiếp theo và mốc xác minh. Mẫu có ở [pull request template](.github/pull_request_template.md).

**Trạng thái kế tiếp.** Cổng duyệt cần chủ sản phẩm nghiệm thu cách chia sẻ theo nhóm client/brand. Sau đó là brief và Brand Kit có phiên bản. Xác minh danh tính thật, xác minh email, rate limiting và connector ghi ra ngoài là các hạng mục còn mở trước khi phục vụ khách thật.
