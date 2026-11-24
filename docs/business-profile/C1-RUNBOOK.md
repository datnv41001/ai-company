# C1 · Hồ sơ nghiệp vụ Marketing và nguồn có thẩm quyền

C1 bổ sung API nội bộ ở schema v22 cho nhân sự ghi nhận dữ kiện theo khách hàng/thương hiệu, gắn từng claim với đúng dòng chứng cứ và đọc lại chính xác nội dung đã được phép sử dụng. Mốc tích hợp là `main@16fea3d45aff62dc4ba80243fcf0791627ffb90f`. [Lịch sử tích hợp và CI các PR tiền nhiệm](INTEGRATION-BASE.md)

## Chạy từ máy khác

Chạy từ gốc repo trên DB phát triển riêng. Dùng cấu hình, khoá ngẫu nhiên và chỉ dẫn cấp tài khoản trong [HANDOFF](../../HANDOFF.md). Compose chạy migration bằng tài khoản publisher, API dùng LOGIN giới hạn `amc_runtime`. Mở `/docs` trên API local, đăng nhập bearer rồi dùng một workspace đã xác minh email. Runner CI tạo DB mới từ dữ liệu tổng hợp cho mỗi đợt kiểm thử. PostgreSQL native được kiểm tại 16.16, Compose ghim image 16.6-alpine.

~~~sh
docker compose config --quiet
docker compose up --build -d
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_business_knowledge.py tests/test_business_knowledge_legacy.py tests/test_knowledge_commercial.py tests/test_knowledge_permissions.py tests/test_knowledge_authority_race.py tests/test_knowledge_validity.py
~~~

Mặc định pytest kiểm SQLite và skip ca cần PostgreSQL. Để chạy cả hai, cấp DB mang tên `amc_test_*` trên loopback rồi dùng các biến và các bước của job `api-tests` trong [workflow](../../.github/workflows/ci.yml). Đặt `AMC_MIGRATION_DSN` cho publisher, `DATABASE_URL` cho LOGIN runtime, `AMC_RUNTIME_PASSWORD`, `JWT_SECRET`, `AMC_TEST_PG=1`, chạy `python migrations/apply.py` trước bộ pytest. Chạy lại migration có kiểm tra version. Lệnh `python tests/check_postgres_upgrade.py --from-v21` cần một DB thử mới khác và binary/fixture đúng phiên bản. Các môi trường local đã có dữ liệu phải sao lưu sang DB riêng trước khi thử nâng cấp.

## Hợp đồng lệnh

Tiền tố là `/api/tenants/{tenant}/clients/{client}/brands/{brand}/knowledge`. Mỗi POST cần `key` tối đa 96 ký tự. Server xác định actor từ bearer. Cùng scope, actor, key và payload trả kết quả đã lưu; tái sử dụng key với payload hoặc đối tượng khác trả 409. Client giữ key khi thử lại sau mất kết nối. Database serialize theo brand rồi khóa membership, kiểm lại role và lấy giờ server trong giao dịch. SQLite dùng single-writer, PostgreSQL dùng READ COMMITTED và khóa giao dịch. [Mẫu gọi API chạy được bằng dữ liệu tổng hợp](../../tests/knowledge_fixtures.py)

| Lệnh | Dữ liệu và kết quả |
| --- | --- |
| POST `/revisions` | `subject, kind, expected_revision, visibility, data, key`. Tạo mới dùng revision 0. Mỗi lần sửa thành công tạo một ID revision mới, checksum mới và trạng thái draft. Cùng stable subject giữ nguyên loại và phân lớp. |
| GET `/revisions/{id}`, GET `/revisions?kind=product` | Đọc revision cụ thể hoặc tối đa 100 revision gần đây. Scope và quyền xem áp dụng cả với revision lịch sử. |
| POST `/revisions/{id}/events` | `state, expected_sequence, expected_digest, reason, key`. Duyệt chính xác digest và event sequence, từ chối quyết định cũ. Thu hồi/dispute tạo event. Khi revision mới được duyệt, revision cũ được supersede. Revision đã thu hồi chỉ có thể thay bằng revision khác. |
| GET `/revisions/{id}/events`, GET `/revisions/{id}/impact` | Đọc lịch sử quyết định và các snapshot đang tham chiếu exact revision. Kết quả impact bị giới hạn, có cờ `more`. Thay đổi lịch bán/offer cũng được kiểm vào lúc xin quyền mới. |
| POST `/import-legacy` | Sao chép văn bản legacy khác rỗng thành draft nội bộ, bảo toàn bảng brands. Source legacy thiếu binding hợp lệ phải qua biên tập trước khi duyệt. Hai stable subject legacy được dành cho lệnh import. |
| POST `/previews` | `claims:[exact claim revision IDs], ttl_seconds, key`. Tối đa 24 claim. Kết quả có handle `id`, UTF-8 canonical, SHA-256, snapshot_as_of, preview_created_at và expires_at. |
| POST `/authorize` | `snapshot_id,digest,operation,previous_receipt?,key`. Queue dùng preview còn hạn; QA tham chiếu queue receipt; share tham chiếu QA receipt cùng snapshot. Cả ba kiểm lại thời hạn và tất cả dependency. Đây là durable authority receipt nội bộ; C3 mới gọi runtime Workforce. |
| GET `/snapshots/{id}`, GET `/receipts/{id}` | Snapshot cũ giữ bytes/digest và báo vấn đề authority hiện tại. Receipt giữ actor-side quyết định tại thời điểm đó. Quyền đọc luôn kiểm lại. |

## Schema và nghiệp vụ

Sáu bảng additive gồm `knowledge_revisions`, `knowledge_links`, `knowledge_events`, `knowledge_snapshots`, `knowledge_dependencies`, `knowledge_commands`. ID toàn cục kết hợp FK tenant/client/brand trên mọi cạnh revision hoặc snapshot. Dữ liệu riêng của từng loại được kiểm qua Pydantic trước khi ký toàn bộ row + actor + transaction + bảng. PostgreSQL buộc RLS, chỉ cho LOGIN API đọc các hàng thuộc quyền và gọi hàm append có proof; UPDATE/DELETE bị chặn. [Schema PostgreSQL](../../migrations/022_business_knowledge.sql) · [Hợp đồng dữ liệu](../../app/knowledge_contracts.py)

- Profile chứa tên, bán gì, bán cho ai và mục tiêu. C1 quản lý từng bộ hồ sơ trong scope brand của client. Product/service, variant, market, policy, availability và offer dùng các revision riêng. Alias SKU không thay thế identity. ICP/segment ghi rõ giả thuyết hoặc căn cứ. Objective có cấp company/brand/campaign, parent và scope. KPI chứa unit, method, window, source và owner.
- Giá dùng số nguyên theo minor units trong tập tiền tệ khai báo. Decimal quantity tối đa ba chữ số thập phân được chuẩn hóa. Quote có selling unit, basis quantity, MOQ, tier min/max, thuế, điều kiện, thị trường, locale, khu vực và kênh. Hàng tồn có observed_at và valid_until. Chỉ công bố giá có đúng một offer công khai đủ điều kiện. Quote trả 409 khi nhiều offer khớp; trên 256 candidate revision cho cùng product cần đối soát. Wording giá được đối chiếu với số tiền và đơn vị do server render.
- Một source có tối đa 12 dòng, mỗi locator duy nhất và một assertion có scope đầy đủ. Binding đối chiếu exact source, locator và assertion. Claim phải trùng binding, gồm điều kiện và các qualifier. Hai dòng trong một file có thể áp dụng cho hai SKU độc lập. Việc so khớp chứng minh truy vết; nhân sự vẫn phải kiểm uy tín, nội dung và quyền dùng nguồn.
- Public, internal và restricted mô tả phạm vi dữ liệu. Portal và tài khoản worker chưa được cấp quyền vào API authoring. Viewer/editor thấy dữ liệu public/internal; quyền restricted dành cho admin/owner. Chỉ wording claim public cùng qualifier, placement và giá đã duyệt vào canonical projection. Excerpt, tài liệu nhà cung cấp, người duyệt và dữ liệu qualification nằm trong kho nội bộ.
- Editor ghi draft. Admin/owner duyệt dữ kiện thông thường. Solo có thể tự khai và duyệt các giá/điều kiện có căn cứ, cũng như các thuộc tính trung tính mà hợp đồng hỗ trợ. Mô tả tự do ngoài thuộc tính này phải qua người duyệt độc lập có qualification `unclassified`. Claim comparison, performance, regulated cần người thứ hai có mandate đúng category và còn hạn. Một owner khác với người nhận duyệt mandate restricted ghi rõ cơ sở chuyên môn. Đây là quyết định nhân sự nội bộ; việc kiểm chứng chứng chỉ nghề nghiệp ngoài hệ thống thuộc quy trình của doanh nghiệp. Thiếu người đủ quyền giữ claim ở draft. Thu hồi qualification chặn cấp quyền tiếp.
- Source/offer có cửa sổ UTC nửa mở. Deadline preview chỉ dùng cho queue lần đầu. Source expiry trước queue hoặc sau QA vẫn chặn quyết định mới. Hai receipt lịch sử trước/sau một thay đổi có thể được phân biệt bằng key và effective_at. Không gửi nội dung ra ngoài, không tạo WorkforceRun và không ghi vào ngân sách.

## Ma trận nghiệm thu C1

| Nhóm trong handoff | Bằng chứng trên code thực thi |
| --- | --- |
| 1–3, 13 · tenant/client/brand/SKU, staff, portal, worker, revocation | [Kiểm thử quyền và signed LOGIN](../../tests/test_knowledge_permissions.py), [scope, nhiều SKU và multi-offer](../../tests/test_knowledge_commercial.py), [product/availability](../../tests/test_knowledge_validity.py) |
| 4–5 · ambiguity, VND/USD, đơn vị, thuế, điều kiện và số lượng | [So sánh source → claim → offer](../../tests/test_knowledge_commercial.py) |
| 6–8 · CAS, idempotency và append-only | [Replay lệnh](../../tests/test_business_knowledge.py), [hai giao dịch và quyền DB thật](../../tests/test_knowledge_permissions.py) |
| 9–10, 15 · ổn định digest, hết hạn sau preview, giữ lịch sử | [Test thật theo đồng hồ](../../tests/test_knowledge_validity.py) |
| 11–12 · withdrawal trước/sau QA và share | [Bốn thứ tự có quan sát khóa trực tiếp qua pg_blocking_pids](../../tests/test_knowledge_authority_race.py) |
| 14, 16 · import legacy, runtime trước đó và restore | [Import legacy](../../tests/test_business_knowledge_legacy.py), [nâng cấp có dữ liệu và backup/restore](../../tests/check_postgres_upgrade.py), bộ API/worker/registry hồi quy của CI |

RED trên code v21 khi POST revision đầu tiên trả 404 ở ca create/replay. GREEN trên code v22 dùng đúng route API và DB thử đã migrate. Scope test này dùng nguồn tổng hợp. Smoke browser và Qwen của CI vẫn kiểm các workflow hiện hữu. C2 còn UI cho Solo/Business/Agency và nghiên cứu usability; C3 còn adapter WF-03/WF-13 mới với contract ghim, cầu nối tới QA/share thực của deliverable, test local model và kiểm soát quyền ở worker. C4 còn đánh giá chất lượng nghiệp vụ độc lập. Commercial GA giữ **NO-GO**.

Rollback bằng ngừng gọi endpoint C1 và giữ bản API tương thích schema v22. Nếu phải quay về binary v21, phục hồi backup trước nâng sang DB riêng, đối chiếu checksum các bảng và kiểm tác vụ đang chạy trước cutover. Các record C1 sau mốc backup cần xuất đối soát trước khi quyết định đổi DB. Nhánh phát triển này dùng dữ liệu tổng hợp.

**Câu hỏi cho reviewer.** Với cùng SKU, hai mức giá chồng lấn, nguồn bị thu hồi sau QA và một reviewer mất qualification, hãy đối chiếu receipt lịch sử, trạng thái khi xin quyền mới và danh sách snapshot bị tác động. Mỗi khoản pricing phải truy được về đúng ô tài liệu, điều kiện bán và tiền tệ.
