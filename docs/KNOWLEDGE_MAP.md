# Tiếp quản AMC từ một checkout

Muốn biết **bản nào hiện ở main, bản nào còn đang review và việc kế tiếp thuộc ai**, bắt đầu tại [đầu HANDOFF](../HANDOFF.md). Khi thấy mục có ngày cũ trong bất kỳ report nào, chỉ áp dụng số liệu cho SHA của mục đó. [Kiểm toán continuity ngày 27/11](evaluation/knowledge-handoff/KC-AUDIT-01.md)

| Loại tri thức | Nơi cập nhật khi thay đổi |
|---|---|
| Mandate, quyền và giao việc | [AGENTS](../AGENTS.md); kết luận review theo [PR template](../.github/pull_request_template.md). |
| Quyết định sản phẩm và roadmap | [Đặc tả, mục 14 và 17](PRODUCT_SPEC_V1.md); lý do thay kiến trúc ở ADR chịu trách nhiệm. |
| Mức trưởng thành và thử nghiệm theo phòng ban | [Từ điển trạng thái](IMPLEMENTATION_STATUS.md) và [sổ bằng chứng theo năng lực](evaluation/DEPARTMENT-CAPABILITY-REGISTER.md). |
| Ranh giới phát hành và giấy phép | [Gate an toàn](SECURITY_AND_GA_BLOCKERS.md) và [sổ giấy phép](../LICENSE-STATUS.md). |

Ở mỗi vòng phát triển, người phụ trách chọn một việc người dùng cần làm, ghi nhận khó khăn từ nguồn công khai có thể đọc và lần tới workflow hiện hữu. Ghi URL, ngày, phần đã đọc, quyền dùng lại, giới hạn và giả thuyết có thể bác bỏ trong [sổ nguồn](research/SOURCE_REGISTRY.md) và [ma trận áp dụng](research/APPLICABILITY_MATRIX.md). Video chỉ có mô tả thì ghi mức mô tả. Kết thúc vòng bằng đầu ra người nhận có thể dùng, kết quả thử và phép đo kinh tế còn thiếu. [Đầu việc theo checkout](../HANDOFF.md) · [Biên nhận main #56](evaluation/department-review/MAIN-56.json) · [Cold handoff lịch sử #53](evaluation/knowledge-handoff/FINAL-53.md)

Đọc theo thứ tự dưới đây. Trước khi báo cáo trạng thái, ghi kết quả của `git rev-parse HEAD`, `git status --short --branch` và nhánh đích. Khi làm việc ngoại tuyến, ghi mốc đồng bộ gần nhất. Mỗi kết quả nghiệm thu chỉ áp dụng cho phiên bản và hành trình đã thử.

1. Đọc [README](../README.md) để chọn cách chạy và [AGENTS](../AGENTS.md) để biết quyền quyết định. [HANDOFF](../HANDOFF.md) mở đầu bằng mốc đang bàn giao. Các mục có ngày, schema hoặc PR cũ là lịch sử.
2. Đọc [sứ mệnh](PRODUCT_MISSION.md) để xác định ai dùng đầu ra và đo công việc được doanh nghiệp chấp nhận như thế nào. [Đặc tả V1](PRODUCT_SPEC_V1.md) giữ phạm vi, mô hình Agency/In-house, các gói dịch vụ, ba sổ tài chính và tiêu chí phát hành. Product Owner quyết định thay đổi phạm vi.
3. Tra [trạng thái module, vai trò và workflow](IMPLEMENTATION_STATUS.md). Dùng bảng dưới để lần từ một tuyên bố đến mã thực thi và bằng chứng trên đúng cây. [Các điều kiện GA](SECURITY_AND_GA_BLOCKERS.md) là căn cứ cho quyết định phát hành.
4. Chọn đầu việc theo mục hiện hành của HANDOFF. So với cơ hội trong [backlog nghiên cứu](research/PRODUCT_OPPORTUNITIES.md), dependency và kết quả đã bị bác bỏ. Ghi người nhận, đầu ra, tiêu chí nghiệm thu và phép đo còn thiếu trước khi sửa.

| Cần biết | Nguồn chính thức và điểm kiểm tra |
|---|---|
| Kiến trúc và lý do lựa chọn | [ADR nền tảng](ADR-001-OWN-SaaS-CORE.md), [quyết định về snapshot](ADR-003-CLIENT-DELIVERY.md), [QA theo revision](ADR-007-QA-EVIDENCE-REVISION.md), [Director/DAG](ADR-009-DIRECTOR-DAG.md) và [node attempts](ADR-011-NODE-ATTEMPTS.md). Đối chiếu trạng thái đề xuất/đã áp dụng của từng quyết định với mã tại HEAD. |
| Luồng công việc và cấu trúc mã | [FastAPI và các router](../app/main.py) nối workspace, tri thức, chiến dịch và bàn giao. [Worker](../app/pool_worker.py) nhận việc theo quyền và ngân sách. [UI](../app/static/) gọi các API này. Theo một ca từ brief đã duyệt tới [commission và receipt](evaluation/campaign-engine/commission/README.md), [biên tập theo kênh](evaluation/content-factory/README.md) và [thao tác sandbox](evaluation/sandbox-operations/README.md). |
| Database, quyền và khôi phục | [ORM và kết nối](../app/database.py), [các model lõi](../app/models.py), [bảng tri thức](../app/knowledge_models.py), [SQL và runner migration](../migrations/), [Compose](../compose.yaml). Xem [cô lập hai khách cùng agency](reviews/POSTGRES_CLIENT_ISOLATION_20261123.md) và [chuyển journal, backup và rollback](evaluation/sandbox-operations/CUTOVER.md). Dùng binary và backup tương thích khi quay lui. |
| AI, kỹ năng và phát triển năng lực | [Catalog vai trò](../catalog/agent_roles.json), [quy trình](../catalog/workflows.json), [kỹ năng Marketing có phiên bản](C3-MARKETING-SKILLS.md), [manifest và runtime](PR9-AGENT-CONTRACTS-WORKFLOW-REGISTRY.md). Chu trình cải tiến gồm mục tiêu theo tác vụ, bộ ca đã đóng băng, thử model/prompt/skill, so với baseline và quyết định theo bằng chứng. [So sánh model và pilot](evaluation/department-study/RESULTS.md). Mọi tuyên bố về huấn luyện trọng số cần có dataset được phép, phiên bản model và nghiệm thu riêng. |
| Nguồn và quyền dùng lại | [Sổ nguồn](research/SOURCE_REGISTRY.md) → [thẻ kiến thức](research/KNOWLEDGE_CARDS.md) → [đối chiếu sản phẩm](research/APPLICABILITY_MATRIX.md) → [cơ hội](research/PRODUCT_OPPORTUNITIES.md) hoặc [giả thuyết bị bác bỏ](research/REJECTED_HYPOTHESES.md). Với mã hay tài sản, ghi rõ quyền và attribution theo [reuse review](GITHUB_RESEARCH_AND_REUSE.md) và [tình trạng giấy phép](../LICENSE-STATUS.md). |
| Phản biện và chất lượng | [Các đánh giá](evaluation/), [thiết kế pilot nghiệp vụ](evaluation/department-study/PILOT.md), [AIRC-500](../engineering/airc500/README.md) và [giao thức kiểm định](../engineering/airc500/CONTRACTS.md). Phân biệt người triển khai, reviewer độc lập, model có receipt và người hành nghề thực sự. Lưu bất đồng còn mở tại báo cáo có liên quan. |
| Vận hành và giới hạn triển khai | [Chạy trên máy mới](../HANDOFF.md#2-chạy-bằng-docker-từ-một-checkout-sạch), [worker pool](POOL-RUNBOOK.md), [khôi phục phiên](IDENTITY-SESSION-RECOVERY.md) và [workflow CI](../.github/workflows/ci.yml). Thiết lập dev dùng loopback và fixture. Cần quyết định theo từng gate trước khi triển khai production hoặc bật adapter ghi ra ngoài. |

## Đọc mức nghiệm thu

Tra tám mức từ ý tưởng tới giá trị thương mại trong [từ điển trạng thái V1](IMPLEMENTATION_STATUS.md#cách-đọc-trạng-thái). Áp dụng mức cho từng năng lực trong phạm vi đã đo. Khi hai nguồn mâu thuẫn, ghim checkout, tái hiện hành vi, ghi cách phân xử và cập nhật đúng tài liệu chịu trách nhiệm.

<a id="cold-start"></a>
## Bài tiếp quản bằng một AI mới

Cuối mỗi vòng review sản phẩm, hoặc sau thay đổi cách chạy, phân quyền hay chuyển schema, người bàn giao cho một phiên AI mới SHA và quyền đọc đúng cây. Bắt đầu phiên không có lịch sử chat, không đưa đáp án, không cho ghi repository, key của maintainer, dữ liệu khách hay quyền production. Cấp sandbox tạm riêng để chạy dịch vụ loopback và test với dữ liệu tổng hợp. Nếu dùng người vận hành làm trung gian, chỉ trả nội dung đường dẫn và kết quả lệnh mà AI yêu cầu. Ghi rõ ai chạy lệnh và phạm vi môi trường.

Yêu cầu AI giải thích sứ mệnh và người dùng, lần theo một hành trình qua kiến trúc và dữ liệu, xác định trạng thái hiện tại, nêu việc chưa xong, giải thích một quyết định, khởi chạy và kiểm thử trong dev, rồi chọn việc tiếp theo và bằng chứng cần thu. AI dẫn đường dẫn cụ thể cho mỗi câu trả lời. Người chấm đối chiếu câu trả lời với nguồn, đầu ra thật và SHA. Ghi kết quả từng mục, lệnh, lỗi và điều chưa thử vào hồ sơ evaluation. Nếu một mục sai vì thiếu thông tin, sửa tài liệu chính thức và thử lại bằng phiên sạch. Dùng mẫu [bàn giao PR](../.github/pull_request_template.md) để chuyển các điểm cần phản biện.
