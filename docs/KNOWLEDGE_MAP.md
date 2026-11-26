# Tiếp quản AMC từ một checkout

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

## Dùng bằng chứng để đặt trạng thái

| Mức | Bằng chứng tối thiểu |
|---|---|
| Ý tưởng | Nhu cầu, giả thuyết giá trị, đối tượng và phép thử dự kiến. |
| Đặc tả | Yêu cầu có ID, phạm vi, đầu vào, đầu ra và điều kiện nghiệm thu. |
| Đã hiện thực | Commit và đường chạy thực tế từ API, UI hoặc worker. |
| Đã kiểm thử kỹ thuật | Lệnh, fixture, phiên bản, kết quả đạt/trượt/bỏ qua và artifact tái kiểm được. |
| Đã kiểm chứng tích hợp | Base/head hoặc merge SHA, tree và bằng chứng các thành phần dùng cùng hợp đồng trong một hành trình. Ghi riêng bản ghép thử và bản có trên main. |
| Đã nghiệm thu nghiệp vụ | Người có thẩm quyền đã dùng hoặc xem đúng đầu ra, ghi quyết định, công sửa và revision chấp nhận. |
| Đủ điều kiện production | Owner chịu trách nhiệm ký các gate vận hành, bảo mật, pháp lý và phục hồi trong đặc tả. |
| Đã chứng minh giá trị thương mại | Số liệu trên công việc được chấp nhận, có mẫu số, baseline, kỳ đo, chi phí toàn hành trình và giới hạn suy luận. |

Áp dụng mức cho **từng năng lực trong phạm vi đã đo**. Một case tích hợp có thể đạt trong sandbox trong khi cả module còn thiếu nhiều hành trình. Giữ giá trị chưa đo là chưa đo. Khi hai nguồn mâu thuẫn, nêu rõ mốc của từng nguồn, tái hiện bằng checkout được chỉ định, sau đó cập nhật nguồn đang có trách nhiệm mô tả hành vi.

<a id="cold-start"></a>
## Bài tiếp quản bằng một AI mới

Cuối mỗi vòng review sản phẩm, hoặc sau thay đổi cách chạy, phân quyền hay chuyển schema, người bàn giao cho một phiên AI mới SHA và quyền đọc đúng cây. Bắt đầu phiên không có lịch sử chat, không đưa đáp án, không cho ghi repository, key của maintainer, dữ liệu khách hay quyền production. Cấp sandbox tạm riêng để chạy dịch vụ loopback và test với dữ liệu tổng hợp. Nếu dùng người vận hành làm trung gian, chỉ trả nội dung đường dẫn và kết quả lệnh mà AI yêu cầu. Ghi rõ ai chạy lệnh và phạm vi môi trường.

Yêu cầu AI giải thích sứ mệnh và người dùng, lần theo một hành trình qua kiến trúc và dữ liệu, xác định trạng thái hiện tại, nêu việc chưa xong, giải thích một quyết định, khởi chạy và kiểm thử trong dev, rồi chọn việc tiếp theo và bằng chứng cần thu. AI dẫn đường dẫn cụ thể cho mỗi câu trả lời. Người chấm đối chiếu câu trả lời với nguồn, đầu ra thật và SHA. Ghi kết quả từng mục, lệnh, lỗi và điều chưa thử vào hồ sơ evaluation. Nếu một mục sai vì thiếu thông tin, sửa tài liệu chính thức và thử lại bằng phiên sạch. Dùng mẫu [bàn giao PR](../.github/pull_request_template.md) để chuyển các điểm cần phản biện.
