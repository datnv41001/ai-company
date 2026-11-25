# C1 · Hồ sơ nghiệp vụ Marketing và nguồn có thẩm quyền

C1 bổ sung API nội bộ ở schema v22 cho nhân sự ghi nhận dữ kiện theo khách hàng/thương hiệu, gắn từng claim với đúng dòng chứng cứ và đọc lại chính xác nội dung đã được phép sử dụng. Mốc tích hợp là `main@16fea3d45aff62dc4ba80243fcf0791627ffb90f`. [Lịch sử tích hợp và CI các PR tiền nhiệm](INTEGRATION-BASE.md)

## Chạy từ máy khác

Chạy từ gốc repo trên DB phát triển riêng. Dùng cấu hình, khoá ngẫu nhiên và chỉ dẫn cấp tài khoản trong [HANDOFF](../../HANDOFF.md). Compose chạy migration bằng tài khoản publisher, API dùng LOGIN giới hạn `amc_runtime`. Mở `/docs` trên API local, đăng nhập bearer rồi dùng một workspace đã xác minh email. Runner CI tạo DB mới từ dữ liệu tổng hợp cho mỗi đợt kiểm thử. PostgreSQL native được kiểm tại 16.16, Compose ghim image 16.6-alpine.

~~~sh
docker compose config --quiet
docker compose up --build -d
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_business_knowledge.py tests/test_business_knowledge_legacy.py tests/test_knowledge_commercial.py tests/test_knowledge_permissions.py tests/test_knowledge_authority_race.py tests/test_knowledge_validity.py tests/test_knowledge_target.py
~~~

Mặc định pytest kiểm SQLite và skip ca cần PostgreSQL. Để chạy cả hai, cấp DB mang tên `amc_test_*` trên loopback rồi dùng các biến và các bước của job `api-tests` trong [workflow](../../.github/workflows/ci.yml). Đặt `AMC_MIGRATION_DSN` cho publisher, `DATABASE_URL` cho LOGIN runtime, `AMC_RUNTIME_PASSWORD`, `JWT_SECRET`, `AMC_TEST_PG=1`, chạy `python migrations/apply.py` trước bộ pytest. Chạy lại migration có kiểm tra version. Lệnh `python tests/check_postgres_upgrade.py --from-v21` cần một DB thử mới khác và binary/fixture đúng phiên bản. Các môi trường local đã có dữ liệu phải sao lưu sang DB riêng trước khi thử nâng cấp.

## Hợp đồng lệnh

### Kiểm tra lại hai phản biện của PR 22

Main ở `5dc4ebc73c9423f360d63287d52350e2ef21a31a` dùng schema v21. PR #22 nâng database lên v22. Bản sửa quy tắc thương mại vẫn dùng số phiên bản v22. Trên DB từng chạy bản PR cũ, dừng API, chạy lại `python migrations/apply.py` bằng publisher rồi khởi động bản mới. Publisher bổ sung hàm quyết định và index, giữ bytes của snapshot, event và receipt cũ. API kiểm tra hàm này khi khởi động. Tình trạng có hiệu lực được tính lại khi lập preview hoặc xin receipt mới.

- **C1-P1-01.** Khi duyệt claim, đọc cả wording, qualifier, điều kiện giá, locale, vùng và kênh hiển thị. Điều khoản thương mại thông thường được nhận diện bằng danh mục cố định. Nội dung ngoài danh mục cần người thứ hai với qualification còn hiệu lực cho phạm vi tương ứng. Khi kiểm lại phê duyệt cũ, hệ thống đối chiếu mandate, người duyệt và revision của claim. [Kiểm thử các trường đưa ra công chúng](../../tests/test_projection_approval.py)
- **C1-P1-02.** Mỗi yêu cầu mới so sánh các khai báo tồn kho, bảo hành hoặc thanh toán đã duyệt, theo đúng product revision, variant, market, locale, channel và region. `applicability` có thể ghi `{"option":"retail","unit":"box","minimum":"2","maximum":"10"}`. Nguồn, binding, claim và bản công khai phải giữ cùng điều kiện. Bỏ trống điều kiện nghĩa là áp dụng cho mọi đơn trong placement. Hai khoảng số lượng có chung một đầu mút cũng chồng lấn. Khoảng hiệu lực gồm thời điểm bắt đầu và kết thúc ngay trước `valid_until`. Kho cần observation đã xảy ra. [Kiểm thử phạm vi, thời hạn và lựa chọn nguồn](../../tests/test_knowledge_commerce_conditions.py)
- Hai giá trị trái nhau trong phạm vi trùng lặp chặn preview/queue/QA/share mới bằng HTTP 409. Editor chỉ nhận `Commercial authority disputed` nếu nguồn cạnh tranh là restricted. Thời điểm quan sát mới hơn tự nó chưa đủ để chọn bên thắng. Người có quyền có thể thu hồi hoặc đánh dấu nguồn cũ `superseded`, ghi lý do và `preferred_revision` của nguồn đang được duyệt cho cùng placement, điều kiện và các loại điều khoản. Trạng thái `disputed` của nguồn từng được duyệt tiếp tục chặn sử dụng cho tới khi xử lý. Hai cách diễn đạt chưa được khai báo tương đương cần một quyết định nghiệp vụ. [Fixture tồn kho, bảo hành và thanh toán trên hai engine](../../tests/test_knowledge_conflicting_authority.py)

Chạy `python -m pytest -q tests/test_projection_approval.py tests/test_knowledge_conflicting_authority.py tests/test_knowledge_commerce_conditions.py` với cấu hình SQLite hoặc PostgreSQL mô tả phía trên. Trước khi sửa, ba fixture xung đột vẫn tạo preview 201 và claim có qualifier tự do vẫn tự duyệt thành công. Sau khi sửa, kiểm tra 409, bytes/digest của lịch sử, và 201 khi đã giải quyết xung đột. Ca `--from-v21` kiểm thêm tình trạng database v22 thiếu hàm, khởi động lại và migration lặp. Dữ liệu thử đều là dữ liệu tổng hợp. C1 đang chờ phản biện độc lập lần tới, Commercial GA **NO-GO**.

### So khớp phạm vi thương mại trên database v22 đã có dữ liệu

Kho, bảo hành, thanh toán, offer và quyết định chọn nguồn dùng chung ba nhóm địa danh gồm `HN / Hà Nội / VN-HN`, `HCM / TP.HCM / VN-SG`, `Đà Nẵng / VN-DN`. Giá trị gốc vẫn dùng trong nguồn, claim, SHA-256 và snapshot. Các địa danh khác dùng đúng nhãn được cung cấp. Các mã option thuộc ba nhóm gồm loại khách `retail / wholesale`, thanh toán `prepaid / credit`, gói `standard / extended`. Hai lựa chọn khác nhau trong cùng nhóm tách các đơn hàng. Các lựa chọn ở hai nhóm khác nhau có thể đồng thời áp dụng. Một chính sách bảo hành 12 tháng cho bán lẻ và chính sách 24 tháng cho trả trước chặn quyết định mới đến khi xử lý phần giao nhau.

Với DB từng chạy `b9edc99`, chạy lại publisher rồi khởi động API. Publisher so sánh SHA-256 SQL đã cài với quy tắc trong binary và cập nhật hàm ngay tại chỗ khi khác phiên bản. Chạy `python -m pytest -q tests/test_knowledge_scope_aliases.py tests/test_knowledge_commercial.py` trên cả hai engine. Trước bản sửa, bảy ca trên SQLite tái hiện xung đột tồn kho, điều khoản và giá đã lọt qua hoặc quyết định chọn offer cùng địa danh bị từ chối. Bộ `--from-v21` kiểm tra startup và chạy lặp publisher với hàm bị thiếu hoặc cũ rồi đối chiếu OID và dữ liệu cũ. [Nguồn danh mục](../../app/commercial_scope.py) · [Kiểm thử trên hai engine](../../tests/test_knowledge_scope_aliases.py)

### Endpoint

Tiền tố là `/api/tenants/{tenant}/clients/{client}/brands/{brand}/knowledge`. Mỗi POST cần `key` tối đa 96 ký tự. Server xác định actor từ bearer. Cùng scope, actor, key và payload trả kết quả đã lưu; tái sử dụng key với payload hoặc đối tượng khác trả 409. Client giữ key khi thử lại sau mất kết nối. Database serialize theo brand rồi khóa membership, kiểm lại role và lấy giờ server trong giao dịch. SQLite dùng single-writer, PostgreSQL dùng READ COMMITTED và khóa giao dịch. [Mẫu gọi API chạy được bằng dữ liệu tổng hợp](../../tests/knowledge_fixtures.py)

| Lệnh | Dữ liệu và kết quả |
| --- | --- |
| POST `/revisions` | `subject, kind, expected_revision, visibility, data, key`. Tạo mới dùng revision 0. Mỗi lần sửa thành công tạo một ID revision mới, checksum mới và trạng thái draft. Cùng stable subject giữ nguyên loại và phân lớp. |
| GET `/revisions/{id}`, GET `/revisions?kind=product` | Đọc revision cụ thể hoặc tối đa 100 revision gần đây. Scope và quyền xem áp dụng cả với revision lịch sử. |
| POST `/revisions/{id}/events` | `state, expected_sequence, expected_digest, reason, key`. Duyệt chính xác digest và event sequence, từ chối quyết định cũ. Thu hồi/dispute tạo event. Khi revision mới được duyệt, revision cũ được supersede. Revision đã thu hồi chỉ có thể thay bằng revision khác. |
| GET `/revisions/{id}/events`, GET `/revisions/{id}/impact` | Đọc lịch sử quyết định và các snapshot đang tham chiếu exact revision. Kết quả impact bị giới hạn, có cờ `more`. Thay đổi lịch bán/offer cũng được kiểm vào lúc xin quyền mới. |
| POST `/import-legacy` | Sao chép văn bản legacy khác rỗng thành draft nội bộ, bảo toàn bảng brands. Source legacy thiếu binding hợp lệ phải qua biên tập trước khi duyệt. Hai stable subject legacy được dành cho lệnh import. |
| POST `/previews` | `claims:[exact claim revision IDs], ttl_seconds, key`. Tối đa 24 claim. Truyền `target:{campaign_id,brief_id}` để ghim đúng campaign và brief, hoặc bỏ target để thử hợp đồng trong scope brand. Kết quả có handle `id`, UTF-8 canonical, SHA-256, snapshot_as_of, preview_created_at và expires_at. |
| POST `/authorize` | `snapshot_id,digest,operation,previous_receipt?,key`. Queue dùng preview còn hạn; QA tham chiếu queue receipt; share tham chiếu QA receipt cùng snapshot. Cả ba kiểm lại thời hạn và tất cả dependency. Với snapshot campaign, truyền lại đúng target. Queue yêu cầu brief đã submit và grant của recipient còn hiệu lực. Đây là durable authority receipt nội bộ; C3 mới gọi runtime Workforce. |
| GET `/snapshots/{id}`, GET `/receipts/{id}` | Snapshot cũ giữ bytes/digest và báo vấn đề authority hiện tại. Receipt giữ actor-side quyết định tại thời điểm đó. Quyền đọc luôn kiểm lại. |

## Schema và nghiệp vụ

Sáu bảng additive gồm `knowledge_revisions`, `knowledge_links`, `knowledge_events`, `knowledge_snapshots`, `knowledge_dependencies`, `knowledge_commands`. ID toàn cục kết hợp FK tenant/client/brand trên mọi cạnh revision hoặc snapshot. Dữ liệu riêng của từng loại được kiểm qua Pydantic trước khi ký toàn bộ row + actor + transaction + bảng. Bảng phụ riêng `amc_acl.knowledge_target_epochs` ghi generation khi campaign/brief thay đổi, gồm A → B → A. Digest ghim nội dung dự án và generation nhưng không chứa dữ kiện riêng của brief. Các row cũ giữ nguyên cấu trúc. PostgreSQL buộc RLS, chỉ cho LOGIN API đọc các hàng thuộc quyền và gọi hàm append có proof; UPDATE/DELETE bị chặn. [Schema PostgreSQL](../../migrations/022_business_knowledge.sql) · [Hợp đồng dữ liệu](../../app/knowledge_contracts.py)

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
| Target campaign/brief, A → B → A và quyền recipient | [Hai engine, drift sau submit, không dùng được receipt brand cho campaign](../../tests/test_knowledge_target.py) |
| 6–8 · CAS, idempotency và append-only | [Replay lệnh](../../tests/test_business_knowledge.py), [hai giao dịch và quyền DB thật](../../tests/test_knowledge_permissions.py) |
| 9–10, 15 · ổn định digest, hết hạn sau preview, giữ lịch sử | [Test thật theo đồng hồ](../../tests/test_knowledge_validity.py) |
| 11–12 · withdrawal trước/sau QA và share | [Bốn thứ tự có quan sát khóa trực tiếp qua pg_blocking_pids](../../tests/test_knowledge_authority_race.py) |
| 14, 16 · import legacy, runtime trước đó và restore | [Import legacy](../../tests/test_business_knowledge_legacy.py), [nâng cấp có dữ liệu và backup/restore](../../tests/check_postgres_upgrade.py), bộ API/worker/registry hồi quy của CI |

RED trên code v21 khi POST revision đầu tiên trả 404 ở ca create/replay. GREEN trên code v22 dùng đúng route API và DB thử đã migrate. Scope test này dùng nguồn tổng hợp. Smoke browser và Qwen của CI vẫn kiểm các workflow hiện hữu. C2 còn UI cho Solo/Business/Agency và nghiên cứu usability; C3 còn adapter WF-03/WF-13 mới với contract ghim, cầu nối tới QA/share thực của deliverable, test local model và kiểm soát quyền ở worker. C4 còn đánh giá chất lượng nghiệp vụ độc lập. Commercial GA giữ **NO-GO**.

Rollback bằng ngừng gọi endpoint C1 và giữ bản API tương thích schema v22. Nếu phải quay về binary v21, phục hồi backup trước nâng sang DB riêng, đối chiếu checksum các bảng và kiểm tác vụ đang chạy trước cutover. Các record C1 sau mốc backup cần xuất đối soát trước khi quyết định đổi DB. Nhánh phát triển này dùng dữ liệu tổng hợp.

**Câu hỏi cho reviewer.** Với cùng SKU, hai mức giá chồng lấn, nguồn bị thu hồi sau QA và một reviewer mất qualification, hãy đối chiếu receipt lịch sử, trạng thái khi xin quyền mới và danh sách snapshot bị tác động. Mỗi khoản pricing phải truy được về đúng ô tài liệu, điều kiện bán và tiền tệ.
