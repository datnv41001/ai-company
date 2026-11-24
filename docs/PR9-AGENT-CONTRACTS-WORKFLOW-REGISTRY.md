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

Chỉ danh tính phát hành của nền tảng trong pipeline Git/CI được nhập manifest vào PostgreSQL. Pipeline dùng commit đã qua review, xác minh schema, adapter và digest trước khi nhập, rồi ghi SHA, digest và danh tính phát hành vào audit. Owner/admin của agency dùng API để kích hoạt phiên bản đã phát hành trong phạm vi tenant/client/brand/campaign được cấp. API và quyền DB của agency không cho phép tạo adapter, đổi schema hoặc xuất bản manifest. Ghi riêng người kích hoạt, scope và phiên bản. Giữ lịch sử định nghĩa và giữ adapter cũ cho đến khi mọi run ghim phiên bản đó kết thúc. Nếu thiếu adapter đúng phiên bản, dispatcher dừng trước khi giữ tiền và báo operator.

Ví dụ binding rút gọn dưới đây dùng dữ liệu thiết kế. Hai trường `role_id` và `skill_version` được server điền sau khi kiểm tra grant. Bộ bằng chứng nguồn và các tham số chi phí thực tế được lấy từ run và ledger. Ví dụ chỉ liệt kê các trường chọn adapter và quyền. Binding bền vững bổ sung khóa run và hai digest theo bước freeze bên dưới.

```json
{
  "workflow_id": "WF-13/landing-seo-draft", "workflow_version": 1,
  "node_id": "n02", "parents": ["n01"],
  "role_id": "ai-seo-geo-specialist", "contract_version": 1,
  "skill_id": "seo", "skill_version": 1,
  "input_schema": "seo-from-brief@1", "output_schema": "seo-fields@1",
  "qa_policy": "seo-cited-draft@1", "approval_policy": "revision-qa-and-client-snapshot@1",
  "allowed_tools": [], "model_profile": "local-text", "max_iterations": 3
}
```

## 3. Một brief đi qua registry như thế nào

**`WF-13/landing-seo-draft@1`** tạo bản nháp landing page và SEO metadata từ brief có nguồn và Brand Kit của cùng campaign. Workflow mẹ là **WF-13 Landing/CRO**. Phần metadata đóng góp cho **WF-11 SEO/GEO** và **MKT-11**. Giữ nguyên các ID gốc trong catalog và ma trận. Form, tracking, thử nghiệm và tối ưu của WF-13 cùng crawl, audit và cập nhật CMS của WF-11 cần nghiệm thu riêng.

Director đóng băng DAG. Content viết landing copy. SEO tạo title, meta description và search intent. Khi metadata phải bám sát câu chữ của trang, DAG phải có cạnh Content → SEO để SEO đọc đúng bản copy. Join kết hợp hai đầu ra, QA duyệt revision/digest rồi khách duyệt snapshot.

1. **Chọn workflow.** UI lấy danh mục hiệu lực trong campaign. Đề xuất API đọc `GET /api/tenants/{tenant}/campaigns/{campaign}/workflow-versions`. Enqueue qua endpoint brief hiện có với tham chiếu phiên bản tùy chọn. Request cũ tiếp tục chạy theo mode v13. Client viewer chỉ thấy brief và snapshot được chia sẻ theo grant hiện tại. Truy cập campaign ngoài scope trả 404.
2. **Tính quyền.** Server lấy giao của phiên bản đã phát hành, tập skill của workflow, grant campaign còn hiệu lực và adapter triển khai được. Với template, thiếu skill bắt buộc thì dừng trước khi giữ tiền. Với dynamic, từ chối enqueue nếu không thể tạo một đường hợp lệ tới đủ đầu ra bắt buộc. Register hoặc đăng nhập được vào pool chưa đủ để được chọn skill. Worker vẫn cần LOGIN, route và quyền của người vận hành.
3. **Ghim và freeze.** Tại enqueue, lưu scope, `manifest_digest`, `workflow_id/workflow_version`, hợp đồng Director và tập role/skill/QA được phép. Tại freeze, server tra phiên bản từ snapshot này và gán `node_id`. Băm topology, assignment, thứ tự Join và các binding đã phân giải để tạo `plan_digest`. Ghi digest cùng binding của từng node trong giao dịch đóng băng graph trước khi tạo task chuyên môn. Một lần phát hành mới không đổi phiên bản của run đang chạy. Ghi nhận usage của Director kể cả khi proposal bị từ chối.
4. **Cấp việc.** Worker nhận brief, nguồn và Brand Kit đã ghim, assignment và đầu ra của predecessor trực tiếp. Tool mặc định rỗng trong lát cắt này. Giá và route lấy từ cấu hình tin cậy. Kiểm tra quyền thực thi tại freeze, cấp offer và commit checkpoint theo quy tắc dưới đây.
5. **Bàn giao.** Join tạo đúng một bản giao. QA duyệt revision và content digest. Khách chỉ đọc và duyệt snapshot theo quyền hiện hành.

### Hiệu lực của thay đổi quyền

| Thao tác trong campaign | Run mới | Run đã ghim phiên bản |
|---|---|---|
| Ngừng kích hoạt (`disable for new runs`) | Từ thời điểm commit, enqueue loại phiên bản khỏi tập có thể chọn. | Run đã enqueue, kể cả đang chờ freeze, tiếp tục theo quyền thực thi đã cấp. |
| Thu hồi thực thi (`revoke active execution`) | Quyền bị loại khỏi tập có thể chọn. | Khi quyền thiết yếu mất hiệu lực, dừng toàn bộ run, fence tất cả lease và chặn offer, checkpoint, Join và bản giao mới. Cấp lại quyền chỉ áp dụng cho run mới. |

Trên PostgreSQL, các đường ghi v14 dùng chung khóa giao dịch scheduler v13 trước khi lấy khóa grant và run. Enqueue, freeze, offer, checkpoint, Join và thu hồi cùng khóa các dòng grant theo thứ tự ID ổn định rồi các dòng run theo thứ tự ID. Đọc lại quyền và kiểm tra fencing token sau khi lấy khóa. Giao dịch thu hồi cập nhật hiệu lực và tăng generation, ghi trạng thái dừng và fence các lease của run bị ảnh hưởng trong cùng giao dịch. Nếu checkpoint commit trước thì giữ lịch sử của checkpoint đó. Nếu thu hồi commit trước thì checkpoint đến muộn bị từ chối. Join kiểm tra lại quyền ngay trong giao dịch tạo bản giao, kể cả khi checkpoint cuối đã commit trước lúc thu hồi. Snapshot đã duyệt được bảo toàn và tiếp tục chịu grant đọc hiện hành. Thu hồi không hủy hold đã gửi hoặc cản việc đối soát receipt.

### Trần chi phí qua tất cả attempt của một node

Đơn vị là micro-USD nguyên. `E_node = chi phí ròng đã xác nhận + tổng hold chưa quyết toán` của tất cả attempt thuộc cùng node, kể cả retry. Khi cấp offer, chỉ ghi hold nếu `E_node + hold_mới ≤ trần_node` và đồng thời đủ trần run, ngân sách agency trong kỳ UTC. Kiểm tra và ghi hold trong cùng giao dịch có khóa ngân sách. Settlement chuyển hold thành chi phí đã xác nhận một lần cho đúng attempt và kỳ gốc. Refund tham chiếu khoản chi gốc bằng bút toán bù.

Ví dụ trần 1.000, attempt đầu đã gửi giữ 700 rồi timeout. Khi usage chưa rõ, exposure vẫn là 700 nên từ chối hold mới 400. Khi receipt quyết toán 350 và giải phóng phần dự phòng còn lại, có thể cấp 400 nếu cả ba cấp đủ ngân sách, đưa exposure lên 750. Trần này giới hạn số tiền được phép cấp. Nếu hóa đơn đến muộn xác nhận chi phí cao hơn dự phòng, ghi đủ chi phí thật, đánh dấu overage, chặn offer tiếp theo trong phạm vi bị ảnh hưởng và đưa chênh lệch vào đối soát. Giữ các bút toán gốc để truy vết.

**Đường truy vết bắt buộc.** Snapshot → deliverable/revision → run → node → attempt UUID → hold, usage, receipt và refund. Từ mỗi node và mỗi lần thử phải đọc lại được `workflow_id/workflow_version`, `role_id/contract_version`, `skill_id/skill_version`, `manifest_digest` và `plan_digest` qua binding bất biến của run/node. Hai node dùng cùng skill vẫn có node ID và tập attempt riêng. QA digest định danh nội dung của bản giao. Các run v13 thiếu binding hiển thị `legacy_v13`. Để trống metadata thiếu, tuyệt đối không suy phiên bản từ tên skill.

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
| Phát hành và quyền theo scope | Agency admin thử tạo adapter, đổi schema, nhập manifest và kích hoạt chéo scope. A/B cùng agency, C khác agency. Disable trước/sau enqueue. | CI nhập manifest hợp lệ. API và RLS từ chối mọi ghi vượt quyền. Run cũ tiếp tục sau disable, run mới thiếu grant bị chặn. |
| Thu hồi và checkpoint | Dùng hai kết nối PostgreSQL với barrier để buộc cả hai thứ tự commit. Thu hồi giữa hai lease, thử checkpoint/Join muộn rồi cấp lại. | Chỉ giữ checkpoint commit trước thu hồi. Chặn bản giao sau thu hồi, mọi lease bị fence, run dừng, hold đã gửi còn đối soát được, snapshot cũ vẫn chịu grant đọc. |
| Ngân sách và cạnh tranh | Hai node cùng xin 700 khi cấp run hoặc kỳ agency còn 1.000. Hai retry cùng xin phần còn lại của trần node. | Giao dịch chỉ cấp một offer khi đủ cho một. Số dư khớp ở cả ba cấp. |
| Usage chưa biết | Timeout sau khi gửi attempt, giữ 700 rồi xin thêm 400 trên trần 1.000. | Trước thu hồi, chặn retry vì vượt trần. Sau thu hồi, giữ hold để đối soát receipt và chặn mọi offer vì run đã dừng. |
| Receipt muộn | Receipt 350 về sau timeout và sau ranh giới kỳ UTC, gửi lại cùng receipt. | Quyết toán đúng một lần vào kỳ gốc. Với retry hợp lệ giữ 400, exposure là 750. |
| Refund | Gửi refund tham chiếu khoản chi của attempt cũ, sau đó phát lại sự kiện. | Một bút toán bù, giảm đúng chi phí ròng trong kỳ gốc và đọc lại được khoản chi ban đầu. |
| Overage | Sau một hold 700, provider xác nhận 1.050 trong khi trần node là 1.000. | Ghi đúng 1.050, nhận diện chênh 350 so với dự phòng và 50 vượt trần, chặn offer, mở đối soát. |
| QA và tích hợp | Mẫu đạt/lỗi của bốn vai trò, nguồn thiếu/sai scope, sửa A → B → A, v1 đang chạy khi v2 phát hành. | Findings theo phiên bản, snapshot QA/khách, quyết định và bộ dữ liệu tổng hợp tái lập được. |
| Nghiệm thu cuối | Giữ 124 bài hồi quy và thêm test mới. Chạy SQLite, PostgreSQL/RLS, migration lặp, Docker/Chromium 1280/390 và Qwen local. | SHA, job CI, graph do model tạo, số lượt gồm lượt lỗi, token và chi phí đã biết/chưa rõ. Báo riêng fixture song song và graph do Director thật chọn. |

**Bàn giao sau review.** Ba quyết định trên là đầu vào cho PR triển khai v14 riêng sau khi PR thiết kế được duyệt và merge. Bắt đầu bằng các test RED cho phiên bản, quyền, cạnh tranh PostgreSQL và ledger, sau đó thực hiện migration 014 và cung cấp bằng chứng GREEN. Bổ sung truy vấn từ mỗi attempt về đủ hai digest và ba cặp phiên bản, cùng fixture lịch sử hiển thị `legacy_v13`.

Theo dõi từng yêu cầu trong [ma trận 49 module, 37 vai trò và 24 workflow](PR9-TRACEABILITY.md). Tiêu chí phát hành thương mại về xác thực, tích hợp, thanh toán, quyền riêng tư và vận hành có quyết định nghiệm thu riêng. [Các điều kiện chặn GA](SECURITY_AND_GA_BLOCKERS.md).
