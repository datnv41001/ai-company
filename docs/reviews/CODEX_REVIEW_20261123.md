# Đánh giá kỹ thuật độc lập · AI Marketing Company V1.0

**23/11/2026 · Quyết định CHALLENGE đối với ADR-001 · BLOCK đối với việc mở cho khách hàng thật.**

## Quyết định cho chủ dự án

Nên tiếp tục xây lõi SaaS và nghiệp vụ marketing riêng. Starter đã chạy được luồng đăng ký → tạo khách hàng/thương hiệu/chiến dịch → lập bảy đầu việc → lưu bản nháp và duyệt nội bộ. Một agency hiện có thể cấp quyền cho cả workspace, nhưng chưa thể giới hạn người của từng khách hàng trong các thương hiệu mà họ phụ trách. Đây là lý do ưu tiên đầu tư vào phân quyền trước khi mời khách hàng dùng thử.

Bản đã sửa vượt qua 12 test trên SQLite. Cả 49 phân hệ còn thiếu bằng chứng nghiệm thu thương mại, 37 vai trò nằm trong danh mục và 24 quy trình mới là đặc tả. Gọi mô hình thật, đăng bài, chi tiền quảng cáo và thanh toán chưa có biên nhận thực tế. Kiến nghị đầu tiên cho nhóm kỹ thuật là chứng minh quyền ở hai cấp tổ chức và thương hiệu trên PostgreSQL, sau đó cho một brief có phiên bản đi trọn vòng soạn → duyệt → bàn giao.

## Bằng chứng chạy tại máy

Windows, Python 3.12.14, môi trường ảo riêng, dữ liệu tổng hợp. ZIP đầu vào có SHA-256 `1e83eef117823e3b6fa6fc9fa78aa2fab33798340f6dfe34a2015e1a92964fbc`. Đã đối chiếu 34/34 mục trong manifest gốc trước khi sửa. Manifest chỉ mô tả đầu vào. Các số dòng ở phần phát hiện bên dưới dùng bản gốc, trừ khi ghi rõ bản vá.

| Phép kiểm tra | Kết quả quan sát |
|---|---|
| `pip install -r requirements-dev.txt` bằng wheel từ PyPI, rồi `python -m pip check` | Cài thành công. Không có dependency xung đột theo pip. Có bản chụp phiên bản Windows trong thư mục checks. |
| Pytest gốc, UTF-8 bật | 10 passed, 1 warning. |
| Pytest gốc, Windows CP1252 với PYTHONUTF8=0 | 9 passed, 1 failed. Đọc JSON tiếng Việt bằng encoding mặc định gây UnicodeDecodeError. |
| Hai test bổ sung, chạy trước các sửa tương ứng | Test catalog phát hiện mã vai trò thừa `ai-copywriter`. Test validation phát hiện giá trị password tổng hợp xuất hiện trong phản hồi 422. Cả hai đều đỏ trước khi sửa. |
| Toàn bộ pytest sau vá | UTF-8 bật và tắt đều 12 passed, 1 warning. Starlette cảnh báo việc dùng httpx trong TestClient đã deprecated. |
| `python -m ruff check app tests docs/reviews/checks` | All checks passed. |
| HTTP qua Uvicorn, SQLite tạm trên loopback | `/`, `/docs`, `/openapi.json`, `/api/health` đều 200. Đăng ký in-house 201, GET danh sách client 200 và trả đúng một “Internal Marketing”. Đã tắt máy chủ sau phép thử. |
| SQL chỉnh mã vai trò cũ | Fixture SQLite chứa 3 dòng. Lần đầu sửa đúng 1, lần hai sửa 0. Hai dòng ngoài điều kiện giữ nguyên. |
| Kiểm tra hợp đồng schema qua SQLAlchemy metadata | Exit 1 đúng mục đích kiểm tra trước GA. Năm quan hệ thiếu FK ghép tenant/parent. Membership thiếu phạm vi client/brand. |
| Docker Compose 2.34.0 | `config -q` đạt với secret tạm. `up -d --build` dừng trước khi lấy image Postgres vì Docker Engine từ chối quyền truy cập named pipe. Chưa nghiệm thu Postgres, RLS, startup log hay restore bằng Compose. |
| Mô hình và nền tảng bên ngoài | Test dùng provider giả để kiểm tra lưu draft. Thiếu key trả 503, execute action trả 501. Chưa đo chất lượng/chi phí của mô hình hoặc xác minh quyền API tài khoản thật. |

Để lặp lại trên bản mã kèm theo, chạy PowerShell từ thư mục dự án. File freeze là ảnh chụp môi trường đã thử riêng cho Windows/Python 3.12. Test schema là phép đo khoảng trống kiến trúc độc lập với pytest.

~~~powershell
py -3.12 -m venv .venv
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install -r docs/reviews/checks/requirements-windows-py312.txt
$env:APP_ENV = 'local'
$env:JWT_SECRET = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:OPENAI_API_KEY = ''
$env:PYTHONPATH = '.'
$env:PYTHONUTF8 = '0'
& $python -m pytest -q
$env:PYTHONUTF8 = '1'
& $python -m pytest -q
& $python -m ruff check app tests docs/reviews/checks
& $python docs/reviews/checks/http_smoke.py
& $python docs/reviews/checks/schema_contract.py
~~~

## Phát hiện và điều kiện đóng

P0 chặn việc đưa dữ liệu thật vào hệ thống hoặc mở tính năng liên quan. P1 cần xử lý trước khi tăng tải hay sử dụng thương mại. P2 ảnh hưởng độ chính xác nghiệp vụ, trải nghiệm hoặc độ tin cậy của phép kiểm tra. “Đọc mã” và “thiết kế” chỉ ra rủi ro hoặc khoảng trống yêu cầu, không phải sự cố thực tế đã quan sát.

| Mức | Phát hiện và chứng cứ | Điều kiện nghiệm thu |
|---|---|---|
| P0 · quyền agency | `app/models.py:33` chỉ lưu tenant/user/role. `app/main.py:123,139,156,205,259` truy vấn danh sách theo tenant. Chưa có bảng grant từng client/brand. Kiểm tra metadata xác nhận. Người được cấp viewer toàn workspace có phạm vi rộng hơn một client reviewer trong đặc tả. | Tách vai trò nội bộ và reviewer theo client/brand. Kiểm tra cả danh sách, chi tiết, duyệt, tìm kiếm và export với hai client cùng agency và một tenant độc lập. |
| P0 · cách ly dữ liệu | `app/models.py:48,58,69,82,95` giữ tenant và parent bằng FK độc lập. API kiểm tra parent trên đường tạo, nhưng DB chưa ràng buộc cặp đó cho writer khác. `app/main.py:29` dùng create_all. Compose dùng cùng tài khoản khởi tạo và kết nối ứng dụng. | Backfill/kiểm tra quan hệ trước migration. Thêm unique/FK ghép, RLS và app role riêng không sở hữu bảng, không BYPASSRLS. Chứng minh mặc định từ chối khi thiếu context, pool không giữ tenant cũ, restore thành công. [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) |
| P0 · xác thực và cấu hình | `app/security.py:12,14,34,41`, `app/database.py:10`, `app/main.py:26,76,109`. Có Argon2, HS256, issuer/audience, exp khi phát hành và kiểm tra thành viên mỗi request. Dev chấp nhận khóa mặc định/mẫu. Chỉ chuỗi môi trường production kích hoạt chốt. Chưa có xác minh email, lời mời có chấp nhận, thu hồi phiên, rate limit. Admin có thể cấp admin, thao tác từ hai user ID chưa bảo đảm hai người độc lập. | Từ chối mode/secret sai lúc khởi động. Yêu cầu claims bắt buộc, session ID và revoke. Kiểm thử hết hạn, thu hồi, giới hạn thử đăng nhập/cấp thành viên, phân quyền người duyệt theo chủ ngân sách. |
| P0 · trước khi bật ghi ra ngoài | `app/main.py:276,289`, `app/models.py:95`. Hiện execute bị khóa 501 kể cả sau duyệt. Approval lưu quyết định và user, thiếu phiên bản payload, đích, hạn duyệt, ngân sách, biên nhận và đối soát khi timeout. | A3/A4 phải gắn approval với nội dung, tài khoản đích, hạn và cap. Thu hồi OAuth sau khi duyệt phải chặn ghi. Sự cố sau ghi trước lưu receipt phải tạo trạng thái cần đối soát. |
| P1 · mật khẩu trong phản hồi 422 · đã vá | `app/schemas.py:5`, validation mặc định của đường auth trong bản gốc. Kiểm tra chỉ ghi boolean xác nhận password thử bị phản chiếu cho bên gọi. Rủi ro tăng nếu hệ thống trung gian thu response body. Chưa quan sát rò sang người dùng khác hay log. | Bản vá lọc chi tiết lỗi đăng nhập/đăng ký, giữ 422 và vị trí trường. Test mới bao phủ password sai độ dài, sai kiểu và sai cấu trúc cả body. |
| P1 · tranh chấp ghi | `app/main.py:79,183,191,237,241,280,284` đọc rồi mới ghi. Unique tại `app/models.py:71` ngăn hai task trùng khóa, nhưng chưa chuyển xung đột đồng thời thành kết quả ổn định. Hai reviewer có thể đọc cùng trạng thái trước khi ghi. Đây là phân tích mã. | PostgreSQL hai transaction đồng thời. Plan có đúng 7 task và phản hồi xác định cho cả hai yêu cầu. Review dùng cập nhật có điều kiện hoặc version, chỉ một quyết định và một audit được commit. |
| P1 · chi phí AI, dữ liệu gửi đi, prompt injection | `app/main.py:246`, `app/services/llm.py:10,19,24,30`. Một API call đồng bộ với giới hạn output, timeout và kiểm tra hình dạng JSON. Brief, facts và hướng dẫn thương hiệu cùng đi vào prompt. Chưa kiểm định claim/nguồn, thiếu reservation, chống lặp và ràng buộc processor theo tenant. Không có tool execution trong đường này. | Xác minh nguồn claim, bộ brief gắn nhãn, tenant opt-in, allowed provider, lọc dữ liệu, giữ chỗ chi phí và idempotency. Trên dữ liệu thử, nội dung không đáng tin vẫn chỉ tạo draft và không đổi quyền. |
| P1 · vòng đời phiên và dữ liệu | `app/static/app.js:2,7`, `app/security.py:18`. Bearer ở bộ nhớ và gắn tường minh vào header, nên CSRF kiểu tự gửi cookie chưa phải đường chính. Thiếu thiết kế refresh/logout phía server. `app/main.py:37` serialize mọi cột ORM được trả. Approval payload/brief và JSON thiếu hạn mức tổng. | Response model theo đối tượng, giới hạn byte/pagination và chính sách retention. Nếu chuyển cookie, kiểm tra Origin, CSRF token, SameSite và revoke. Kiểm thử trace không chứa mật khẩu, prompt riêng hay credential. |
| P1 · vận hành và bằng chứng | `tests/conftest.py:12`, `.github/workflows/ci.yml:15`, `requirements.txt:1`, `app/main.py:71`. Bộ test dùng SQLite bộ nhớ, lifespan vẫn gọi create_all trên engine cấu hình toàn cục. Health trả OK không thăm DB. CI không chạy Postgres. Các phiên bản thư viện dùng khoảng rộng. | Cô lập cả engine lifespan của test. CI với Postgres và app role thực, readiness kiểm DB, phân trang/load hai tenant, lock phiên bản + quét SBOM, backup/restore. Chưa đo SLO. |
| P2 · mã vai trò và Windows · đã vá | `app/services/marketing.py:7` lệch `catalog/agent_roles.json:139`. `tests/test_api.py:147` bản gốc đọc catalog bằng encoding hệ điều hành. Đã tái hiện cả hai sai lệch. | Test đối chiếu task và role qua API. SQL một lần cho dữ liệu cũ ở `migrations/001_correct_content_role.sql`. Chạy pytest qua cả CP1252 và UTF-8. |
| P2 · UX nhiều workspace | `app/static/app.js:28` chọn membership đầu tiên và gán mode agency khi đăng nhập lại. UI chỉ liệt kê bản nháp và quyết định. Chưa có luồng khách hàng đọc bản cụ thể và duyệt trên giao diện. | Cho chọn workspace, hiển thị rõ client/brand/người chịu trách nhiệm và phiên bản đang duyệt. Thử cùng một người thuộc hai tổ chức ở hai mode. |

**Phạm vi đọc API.** Bản gốc có 26 route khai báo bằng decorator. Trang chủ và health công khai, đăng ký/login cấp danh tính, me/catalog yêu cầu bearer. Nhóm nghiệp vụ cần membership, API tạo brand/campaign kiểm cha cùng tenant, submit/review kiểm trạng thái và cấm tự duyệt theo ID. Audit cần admin, trả tối đa 100 sự kiện. Mười model ORM bao phủ User, Tenant, Membership, Client, Brand, Campaign, WorkTask, Deliverable, ActionRequest, AuditEvent. Các test gốc ở `tests/test_api.py:33,61,84,119` chứng minh một số từ chối đúng qua API. Tệp nguồn, hàng đợi, vector index và cache đa khách hàng chưa có đối tượng chạy để kiểm tra.

## ADR-002 đề xuất cho vòng phản biện

**Giữ phương án B của ADR-001.** FastAPI và Postgres giữ dữ liệu nghiệp vụ. AMC quyết định ai có quyền, ai đã duyệt phiên bản nào và chi phí thuộc về ai. Bắt đầu một luồng nội bộ bằng transaction Postgres ghi đồng thời phiên bản brief, trạng thái và outbox. Worker nhận ID cùng tenant/brand, nạp lại quyền và thực hiện một bước có khóa chống lặp. Nhật ký run lưu liên kết đầu vào, đầu ra, lần thử, chi phí và trạng thái bàn giao.

| Phương án | Lợi ích | Chi phí/rủi ro và ngưỡng quyết định |
|---|---|---|
| Tự sở hữu lõi, Postgres + worker, provider adapter nhỏ | Dễ truy vết một quyết định và rollback. Tận dụng Python và hợp đồng API sẵn có. | Nhóm chịu trách nhiệm khóa, lease, retry giới hạn, hàng lỗi và công cụ vận hành. Dừng mở rộng scheduler tự viết khi timer/khôi phục liên quy trình trở thành phần đáng kể của công việc. |
| Temporal quản lý vòng đời nghiệp vụ, LangGraph chạy một bước AI nếu cần | Tách timer, chờ duyệt và retry khỏi quá trình sinh nội dung. Có thể tạm dừng workflow dài ngày. | Thêm hạ tầng và hai mô hình checkpoint. Mỗi run chỉ có một chủ sở hữu lịch retry. Activity vẫn cần idempotency. So sánh trên cùng WF-07, ép khởi động lại khi chờ duyệt và sau gọi provider. [Temporal Activities](https://docs.temporal.io/activity-definition) · [LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) |
| Fork Paperclip hoặc cấu hình Opensoul/Outclaw | Có sơ đồ đội ngũ, công việc, giao diện và mẫu tổ chức để tham khảo. | AMC vẫn cần cách ly agency/client, kế toán, portal và chính sách kênh. Mỗi nâng cấp upstream phải chạy lại các hợp đồng quyền quan trọng. Outclaw có phần enterprise riêng. [Đối chiếu 11 kho](UPSTREAM_20261123.md) |

**Chọn runtime có điều kiện.** Dùng LangGraph làm ứng viên ưu tiên cho bước cần rẽ nhánh/checkpoint. Dùng một lệnh gọi có schema cho bước soạn đơn giản. Chỉ chốt Temporal sau khi so sánh số lần thực thi trùng, khả năng resume, chi phí trực vận hành và độ trễ P95 trong cùng tình huống lỗi. Đưa workflow mới qua adapter, lưu ID run ổn định, rút hết run còn chờ ở engine cũ trước khi chuyển. Có thể chuyển các run mới về worker trước mà vẫn giữ lịch sử đã duyệt. Trì hoãn tách microservice cho tới khi có số đo tải hoặc nhu cầu cô lập credential cụ thể.

**Ngân sách bảo trì 3–5 năm.** Mô hình minh họa để chủ dự án thay giả định: lõi riêng mất 12 người-tháng xây phần nền và 8 người-tháng/năm bảo trì. Fork mất 6 người-tháng chỉnh ban đầu, 6 người-tháng/năm bảo trì cộng M người-tháng/năm hợp nhất và kiểm thử thay đổi upstream. Sau 3 năm: 36 so với 24 + 3M. Sau 5 năm: 52 so với 36 + 5M. Với M = 4, hai phương án bằng nhau ở năm 3, năm 5 là 52 và 56. Điểm hòa vốn năm 5 là M = 3,2. Đây là giả định phân tích độ nhạy, chưa phải báo giá. Cần đo M trên hai chu kỳ cập nhật và cộng riêng cloud, trực ca, phí EE, storage, inference và thời gian chuyên gia duyệt. Theo dõi chi phí mỗi deliverable được khách chấp nhận.

**Hiệu suất và UX.** Request chiến lược hiện giữ luồng xử lý tới khi provider trả lời. Đổi sang trả run ID, có trạng thái chờ và nút thử lại an toàn. Đo ở tải và kích thước brief xác định, theo từng tenant; kiểm tra hàng đợi công bằng và tốc độ màn hình phê duyệt. Đặc tả đặt P95 đọc phổ biến dưới 2 giây, RPO 24 giờ, RTO 4 giờ. Chưa có tải chuẩn, phép đo hay biên bản diễn tập.

**Quyền của nền tảng.** Google Ads chuyển cấp truy cập sang Cloud project từ 09/09/2026. Quy trình App Conversion Tracking có ngoại lệ riêng. Meta phân biệt Marketing API Access Tier với permission ads_management. Đặc tả cần chốt ma trận nhà cung cấp × tài khoản × thao tác bắt buộc ở V1, cùng cách nghiệm thu khi vendor chỉ cho đọc hoặc chưa phê duyệt. Nếu thiếu quyền, UI hiển thị trạng thái chờ và người chịu trách nhiệm. [Google Ads access](https://developers.google.com/google-ads/api/docs/api-policy/developer-token) · [Meta Marketing API Access Tier](https://developers.meta.com/blog/updates-to-ads-management-standard-access-feature/)

## Kiểm kê và quyết định tái sử dụng

[Ma trận 49 phân hệ, 37 vai trò và 24 workflow](INVENTORY_20261123.md) chỉ ra những chỗ bảng status gốc bỏ sót dấu vết triển khai. Chẳng hạn Workspace/Team có API cấp membership, Human-in-the-loop có review, Artifact có bản ghi JSON, Security/Audit có audit event. Chúng vẫn thiếu điều kiện nghiệm thu tương ứng.

[Đối chiếu 11 kho tại commit cụ thể](UPSTREAM_20261123.md) ghi giấy phép, ngoại lệ, CI và mẫu lịch sử advisory. [Sàng lọc 240 tệp kỹ năng](SKILLS_20261123.md) ghi các tệp của Digital Marketing Pro và Marketing Skills OS, ánh xạ sơ bộ sang vai trò/quy trình và những chỗ còn trống. Phép sàng lọc từ khóa chưa đánh giá chất lượng chuyên môn hoặc nội dung tất cả script phụ thuộc. Chưa chọn tệp nào để nhập vào lõi sản phẩm.

## Thứ tự công việc cho một V1.0 duy nhất

| Thứ tự và phụ thuộc | Phạm vi giao cho nhóm | Bằng chứng ra khỏi bước |
|---|---|---|
| A · bắt đầu | Product + kiến trúc chốt RACI, mode, danh tính người dùng/agent, quan hệ client/brand, scope connector và ma trận 49/37/24. | Chủ sản phẩm ký mẫu dữ liệu hai agency và một in-house, xác định ai có quyền duyệt, kênh nào thuộc cam kết. |
| B · cần A | Platform xây migration, quyền DB, RLS, invite/accept, MFA/phiên, tenant lifecycle, vault, audit. Áp cho file/vector/queue khi hình thành. | App role tối thiểu, ma trận quyền đạt ở API/DB, migration–restore và context pool được kiểm chứng. |
| C · cần B | Domain + UX xây Brand Kit, claim có nguồn, brief cấu trúc, phiên bản artifact và duyệt. Dùng WF-02/WF-07 làm lát cắt đầu-cuối nội bộ. | Người không kỹ thuật chuyển đúng workspace, kiểm tra bản soạn, trả sửa và duyệt một phiên bản xác định. |
| D · cần B,C | AI/runtime xây worker, outbox, quota reservation, policy gateway, eval và registry. So sánh LangGraph/Temporal theo ADR-002. | Kill/restart, retry giới hạn, ledger theo tenant và biên bản quyết định runtime. Từng role có hợp đồng input/output/tool. |
| E · cần B và hợp đồng chi phí ở D | Commerce + agency hoàn tất SAA-01..09 và AGY-01..08, portal, hợp đồng, entitlement, invoice/refund và ba sổ riêng cho doanh thu, AI cost, ad spend. | WF-01, WF-20/21/24 có đối soát, quyền khách và khôi phục khi gia hạn/thanh toán lại. |
| F · cần B,C,D | Nhóm tích hợp triển khai adapter theo capability đã duyệt. Kết nối đọc trước, sau đó ghi có đích, ngân sách, approval, receipt và reconciliation. | Mỗi provider/action có bằng chứng sandbox, revoke, timeout và giới hạn quota. Mỗi capability giao khách có chủ sở hữu. |
| G · cần C,D,F, dùng dữ liệu/quyền từ E | Nhóm marketing hoàn thiện MKT-01..20, AIO-01..12, chất lượng số liệu, attribution, báo cáo và toàn bộ WF-01..24. | Từng workflow có brief, artifact, nguồn dữ liệu, kết quả được người phụ trách chấp thuận, case lỗi và chi phí thực đo. |
| H · cần A..G | Security, QA, vận hành hoàn tất hiệu năng/SLO, DR, quyền riêng tư, chính sách quảng cáo, hỗ trợ, khả năng tiếp cận, diễn tập incidents và ký duyệt. | Một lần quyết định GA cho đủ V1.0. Bằng chứng theo từng mục gồm fixture, phiên bản mã, kết quả và người nghiệm thu. |

## Năm câu hỏi phản biện cho người duyệt kiến trúc

1. Nếu cùng một người thuộc hai agency và được phép duyệt đúng một brand, mô hình nào ràng buộc quyền xuyên suốt từ API, DB đến file, vector, hàng đợi và báo cáo?
2. Nếu provider đã đăng bài nhưng kết nối đứt trước khi có receipt và provider không hỗ trợ idempotency, ai quyết định đối soát hay cho phép thử lại? Khách hàng sẽ nhìn thấy trạng thái gì?
3. Khi chủ sở hữu đổi Brand Kit, hạ ngân sách hoặc thu hồi OAuth sau lúc duyệt nhưng trước lúc worker chạy, dữ liệu nào được giữ theo phiên bản và quyền nào phải kiểm tra lại?
4. Mức tải, số ngày chờ duyệt, tỷ lệ lỗi và chi phí trực nào khiến Temporal + LangGraph có lợi hơn worker hiện tại? Ai đo trên cùng fixture trước khi chốt?
5. V1.0 cam kết thao tác nào theo kênh và thị trường? Ai chịu chi phí model, công duyệt và xử lý lỗi khi một deliverable phải làm lại nhiều lần hoặc khi nền tảng từ chối cấp quyền?

**Bản bàn giao.** Gói ZIP đã rà chứa mã, test, SQL chỉnh dữ liệu cũ, các phụ lục và diff. Bản vá chỉ sửa validation auth, tham chiếu role và encoding của test. SQL là migration thủ công cho DB cục bộ đã tồn tại. Việc chạy SQL trên dữ liệu thực, thay đổi ADR chính thức và triển khai các bước B–H thuộc vòng phát triển sau.
