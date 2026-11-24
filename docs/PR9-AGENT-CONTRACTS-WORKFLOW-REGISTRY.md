# PR #9 · Agent Contracts & Marketing Workflow Registry

**Đề xuất để kiểm toán thiết kế.** Mốc đối chiếu là `main@2846c174e393acfcc47526a8da5a62fa77bc87d5`, PostgreSQL v13. Người tiếp quản có thể đánh giá thiết kế bằng một câu hỏi cụ thể. Khi hai node Content viết email và landing page, hệ thống có chỉ ra được hợp đồng, nguồn, quyền, người duyệt và chi phí của từng bản không?

## 1. Điểm tích hợp trên v13

| Điểm trong mã | Trách nhiệm hiện có | Thay đổi đề xuất khi triển khai |
|---|---|---|
| [Danh mục vai trò](../catalog/agent_roles.json), [workflow](../catalog/workflows.json), [API danh mục](../app/main.py) | 37 vai trò và 24 đặc tả nghiệp vụ. `GET /api/catalog/roles` đọc danh sách mô tả. | Giữ định danh và phản hồi cũ. Bổ sung truy vấn các phiên bản thực thi mà người vận hành được phép chọn trong campaign. |
| [Enqueue](../app/workforce.py), [planner/compiler](../app/dynamic_plan.py) | Lưu brief và nguồn, chuẩn hóa đồ thị, cấp ID theo run và kiểm tra kiểu predecessor. | Chốt phiên bản workflow và tập hợp đồng tại enqueue. Dùng cùng tập đó khi tạo schema cho Director và kiểm tra proposal trên server. |
| [Gateway](../app/workforce_gateway.py), [checkpoint](../app/workflow_dag.py) | Prompt, schema và kiểm tra đầu ra theo skill. Catalogue của DAG động hẹp hơn danh sách prompt của luồng tuyến tính. | Tra adapter và QA bằng khóa phiên bản đã ghim. Bảo tồn đường đọc lịch sử và các mode v13. |
| [Node attempt](../app/node_attempts.py), [dispatcher](../app/pool_dispatch.py), [QA bản giao](../app/revision_qa.py) | Cấp lease/hold, ghi usage, xử lý fencing và Join, duyệt revision/digest. | Dùng các điểm giao dịch hiện có để kiểm tra quyền, gắn bằng chứng và hạch toán. [Quy tắc một và hai lease](ADR-011-NODE-ATTEMPTS.md). |

## 2. Ba bản ghi cần có phiên bản

| Khóa bất biến | Dữ liệu bắt buộc |
|---|---|
| `(role_id, contract_version)` | Tên, cấp quản lý, mục tiêu, chỉ số thành công, owner, nguồn kiến thức bắt buộc, schema vào/ra, profile model, công cụ cho phép, hành động cấm, giới hạn tính toán, số lượt, timeout, chính sách QA/duyệt, fallback và nơi chuyển việc cho người xử lý. Dùng đủ trường của [Agent Contract §2.1](PRODUCT_SPEC_V1.md). |
| `(skill_id, skill_version)` | Tham chiếu đúng một phiên bản role, adapter do backend đăng ký, schema vào/ra, kiểu đầu ra của các predecessor hợp lệ, bộ quy tắc QA và digest của prompt, schema, quy tắc. Director là một hợp đồng lập kế hoạch riêng. |
| `(workflow_id, workflow_version)` | ID nghiệp vụ chuẩn, trigger, phạm vi đã triển khai, đầu ra bắt buộc, tập phiên bản skill, mode `diamond-v1` hoặc `dynamic-v1`, chính sách Join và phê duyệt. Với template, đối chiếu toàn bộ node/cạnh. Với dynamic, compiler kiểm tra proposal trong giới hạn của workflow. |

Đề xuất lưu định nghĩa trong manifest có version được review qua Git và nhập bản phát hành chỉ đọc vào PostgreSQL. Mỗi bản phát hành có digest nội dung chuẩn hóa. Cùng khóa và cùng digest cho phép nhập lại. Cùng khóa với digest khác làm giao dịch thất bại. Sửa prompt, schema, công cụ, QA hay giới hạn tạo phiên bản mới. Adapter được tìm bằng bảng ánh xạ biên dịch cùng mã. Manifest chỉ chứa ID và dữ liệu, không chứa tên module để import tùy ý, mã chạy hay credential.

Tách **phiên bản định nghĩa**, **quyền kích hoạt theo campaign** và **mức nghiệm thu nghiệp vụ**. Chủ sở hữu nền tảng xuất bản phiên bản qua review. Owner/admin của agency chỉ kích hoạt phiên bản đã được phát hành cho đúng tenant/client/brand/campaign. Hai thao tác này có audit riêng. Mỗi định nghĩa đã dùng phải đọc lại được sau khi ngừng nhận run mới. Backend cần giữ adapter cũ đến khi mọi run ghim phiên bản đó đã kết thúc. Nếu worker thiếu adapter đúng version, dispatcher báo lỗi khả năng thực thi trước khi giữ tiền và chuyển cho operator xử lý.

Ví dụ binding rút gọn dưới đây dùng dữ liệu thiết kế. Hai trường `role_id` và `skill_version` được server điền sau khi kiểm tra grant. Bộ bằng chứng nguồn và các tham số chi phí thực tế được lấy từ run và ledger.

```json
{
  "workflow_id": "WF-11/brief-to-seo-draft", "workflow_version": 1,
  "node_id": "n02", "parents": ["n01"],
  "role_id": "ai-seo-geo-specialist", "contract_version": 1,
  "skill_id": "seo", "skill_version": 1,
  "input_schema": "seo-from-brief@1", "output_schema": "seo-fields@1",
  "qa_policy": "seo-cited-draft@1", "approval_policy": "revision-qa-and-client-snapshot@1",
  "allowed_tools": [], "model_profile": "local-text", "max_iterations": 3
}
```

## 3. Một brief đi qua registry như thế nào

Lát cắt nội bộ đầu tiên là soạn landing page và metadata từ nguồn do khách mẫu cung cấp. Đề xuất mã workflow thực thi `WF-11/brief-to-seo-draft@1`, gắn với đặc tả mẹ `WF-11 SEO/GEO`. Danh mục hiện dùng chuỗi chứa cả ID và tên. Khi nhập, tách mã ổn định `WF-11`, giữ nguyên chuỗi cũ cho client hiện hữu. Phạm vi lát cắt kết thúc ở bản nháp được duyệt. Crawl, technical audit và cập nhật CMS vẫn là tiêu chí riêng của WF-11.

1. **Chọn workflow.** UI lấy danh mục hiệu lực trong campaign. Đề xuất API đọc `GET /api/tenants/{tenant}/campaigns/{campaign}/workflow-versions`. Enqueue qua endpoint brief hiện có với tham chiếu phiên bản tùy chọn. Request cũ tiếp tục chạy theo mode v13. Client viewer chỉ thấy brief và snapshot được chia sẻ theo grant hiện tại. Truy cập campaign ngoài scope trả 404.
2. **Tính quyền.** Server lấy giao của phiên bản đã phát hành, tập skill của workflow, grant campaign còn hiệu lực và adapter triển khai được. Với template, thiếu skill bắt buộc thì dừng trước khi giữ tiền. Với dynamic, từ chối enqueue nếu không thể tạo một đường hợp lệ tới đủ đầu ra bắt buộc. Register hoặc đăng nhập được vào pool chưa đủ để được chọn skill. Worker vẫn cần LOGIN, route và quyền của người vận hành.
3. **Ghim và freeze.** Trong giao dịch enqueue, lưu snapshot tham chiếu gồm phiên bản workflow, hợp đồng Director, tập skill/role/QA có digest và phạm vi. Planner được đề xuất khóa node cục bộ, skill, assignment và predecessor. Server gán `node_id` và tra phiên bản. Chuẩn hóa rồi băm cả topology, assignment, thứ tự Join và phiên bản/digest đã giải quyết. Publish v2 trong khi Director đang chạy vẫn giữ các phiên bản của run. Proposal không hợp lệ được tính usage Director đã phát sinh. Chỉ sau freeze thành công mới tạo task chuyên môn.
4. **Cấp việc và nhận kết quả.** Tại freeze, trước offer và trước commit checkpoint, kiểm tra lại grant hiện hành cùng scope. Khóa hoặc kiểm tra generation của grant trong giao dịch để lệnh thu hồi có thứ tự rõ ràng với lệnh nhận kết quả. Thu hồi quyền bắt buộc làm run dừng, fence mọi lease và ghi lý do. Cấp lại quyền chỉ áp dụng cho run mới. Worker nhận brief, nguồn đã đóng băng, assignment và đầu ra của predecessor trực tiếp. Tool mặc định rỗng trong lát cắt này. Giá và route chỉ lấy từ cấu hình tin cậy.
5. **Tính phí và bàn giao.** Đơn vị là micro-USD nguyên. Dùng giới hạn thấp nhất về số lượt, timeout và trần tính toán giữa contract với runtime. Đề xuất trần chi phí **mỗi node cho toàn bộ retry**. Tính chi ròng cộng hold còn mở của tất cả attempt của node từ ledger, rồi kiểm tra cả trần node, run, agency trong giao dịch cấp offer hiện có. Receipt muộn, refund và usage chưa rõ đi cùng attempt/kỳ gốc. Join tiếp tục tạo đúng một bản giao. QA con người duyệt đúng revision và content digest, khách duyệt snapshot theo grant.

**Ví dụ truy vết cần trả được trên màn hình vận hành.** Với `n01` viết landing page, đường truy vấn bắt đầu từ snapshot → deliverable/revision → run và plan digest → `n01` → `ai-copywriter-content-strategist@1 / content@1` → attempt UUID → hold, usage và receipt. Với `n02` SEO, cùng run nhưng có `ai-seo-geo-specialist@1 / seo@1`, attempt và chi phí riêng. Nếu có thêm node Content viết email, nó có node ID mới dù dùng lại `content@1`. Digest QA tiếp tục định danh tiêu đề và nội dung; digest kế hoạch định danh hợp đồng thực thi. Artifact lịch sử thiếu liên kết registry hiển thị `legacy_v13`. Không suy đoán phiên bản từ tên skill.

## 4. QA theo vai trò

Mọi output dùng schema đóng, nguồn thuộc đúng registry đã đóng băng và phiên bản rule đã ghim. Sai schema, ID nguồn hoặc thiếu output bắt buộc chặn checkpoint, ghi lý do cùng usage và áp dụng retry hữu hạn. Nhận định cần đối chiếu được lưu làm finding có vị trí, trích dẫn và trạng thái để người QA quyết định. Khách chỉ nhận snapshot đã qua quy trình duyệt.

| Skill và vai trò đề xuất | Hợp đồng đầu ra v13 làm điểm xuất phát | Ca nghiệm thu nghiệp vụ |
|---|---|---|
| Research · `ai-market-researcher` | `observed_fact`, `audience_hypothesis`, `knowledge_gap` | Fact về sản phẩm phải trỏ đúng nguồn mẫu. Khi thiếu dữ kiện, ghi khoảng trống. Gắn nhãn giả thuyết cho suy luận về khách hàng. |
| Strategy · `ai-marketing-strategist` | `positioning`, `proposed_channel`, `success_metric` | Phải nhận Research đầu vào hợp lệ. KPI đề xuất có đơn vị và cách đo. Phát hiện việc dùng dự báo như kết quả đã đạt. |
| Content · `ai-copywriter-content-strategist` | `headline`, `body_copy`, `call_to_action` | Bộ mẫu có email và landing page để kiểm tra đúng định dạng, đối tượng, CTA. Thêm/bỏ claim trong bản sửa phải tạo kết quả QA mới, giữ lịch sử. |
| SEO · `ai-seo-geo-specialist` | `page_title`, `meta_description`, `search_intent` | Đối chiếu metadata với trang khi có cạnh Content → SEO. Số liệu search volume thiếu nguồn phải được đánh dấu, nguồn của khách B không hợp lệ cho A. |

Muốn thêm chuyên môn mới, review đồng thời adapter, schema, QA, một mẫu đạt và một mẫu phải chặn, phép thử quyền và E2E Qwen thật. Có sẵn prompt `ads`, `creative` hoặc `analytics` trong gateway chưa đáp ứng các điều kiện đó.

## 5. Migration, triển khai và rollback đề xuất

Đề xuất migration **014** ở PR triển khai kế tiếp. Các bảng định nghĩa dùng khóa phiên bản, policy kích hoạt dùng khóa ghép tenant/client/brand/campaign. Bản ghi binding của run mang scope, revision, workflow và digest; binding node tham chiếu khóa ghép của node v13 và phiên bản skill/role. Liên kết tài chính dùng attempt hiện hữu. Grant riêng cho đọc định nghĩa, kích hoạt, freeze và ghi audit; worker chỉ dùng mailbox. UI quản trị cho thấy phiên bản, phạm vi, lý do chưa khả dụng và run đang dùng. API trả 409 cho xung đột phiên bản, 422 cho hợp đồng sai, và không tạo hold khi từ chối trước inference.

Trên DB thử, nâng từ v1–v13 có dữ liệu và chạy lại migration. Fixture v13 phải giữ nguyên run đang có hai lease, deadline, checkpoint, hold chưa xác nhận, receipt, draft QA và snapshot khách đã duyệt. So sánh trước/sau từng khóa và số dư. Các run v13 đang chạy tiếp tục dùng adapter và digest v13. Thử lỗi giữa bước ghi binding và freeze, khởi động lại, xác nhận chỉ có một graph và một tập task. Khi rollback nội bộ, tắt intake registry mới, drain hoặc thu hồi run đã ghim, đối soát ledger rồi dùng lại điểm vào v13 cho brief mới. Giữ các định nghĩa và binding phục vụ kiểm toán lịch sử.

## 6. Thứ tự triển khai và bằng chứng để nghiệm thu

| Mốc | Phép thử phải qua | Bằng chứng cần đính vào PR triển khai |
|---|---|---|
| Contract và phiên bản | Hai Content cùng skill có ID khác nhau. Đảo thứ tự JSON cho cùng digest. Đổi QA/skill version cho digest mới. Trùng khóa khác nội dung bị từ chối. | Fixture chuẩn hóa, digest đối chiếu và test compiler. |
| Quyền theo scope | A/B cùng agency, C khác agency. Grant A không cấp việc cho B. Thu hồi trước freeze, giữa hai lease, rồi cấp lại. | Kết quả API/PostgreSQL cho từng actor, số offer/checkpoint, lý do dừng và số dư. |
| Ngân sách và cạnh tranh | Hai node tranh 700 khi run hoặc agency còn 1.000. Retry tranh trần node khi có hold chưa rõ. Receipt trùng, refund, chuyển kỳ UTC. | Sổ cái khớp cả ba cấp, một offer khi chỉ đủ một, một bản giao khi Join chạy lại. |
| QA và tích hợp | Mẫu đạt/lỗi của bốn vai trò, nguồn thiếu/sai scope, sửa A → B → A, v1 đang chạy khi v2 phát hành. | Findings theo phiên bản, snapshot QA/khách, quyết định và bộ dữ liệu tổng hợp tái lập được. |
| Nghiệm thu cuối | Giữ 124 bài hồi quy và thêm test mới. Chạy SQLite, PostgreSQL/RLS, migration lặp, Docker/Chromium 1280/390 và Qwen local. | SHA, job CI, graph do model tạo, số lượt gồm lượt lỗi, token và chi phí đã biết/chưa rõ. Báo riêng fixture song song và graph do Director thật chọn. |

**Điểm cần reviewer quyết định.** Có chấp nhận `WF-11/brief-to-seo-draft` là lát cắt đầu tiên không? Trần node qua mọi retry và quyết định dừng cả run khi mất grant bắt buộc có phù hợp vận hành agency không? Sau khi chốt các điểm này, bắt đầu bằng test phiên bản và thu hồi quyền trên PostgreSQL rồi mới viết migration.

Theo dõi từng yêu cầu trong [ma trận 49 module, 37 vai trò và 24 workflow](PR9-TRACEABILITY.md). Tiêu chí phát hành thương mại về xác thực, tích hợp, thanh toán, quyền riêng tư và vận hành có quyết định nghiệm thu riêng. [Các điều kiện chặn GA](SECURITY_AND_GA_BLOCKERS.md).
