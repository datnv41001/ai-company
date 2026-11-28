# Từ Strategy Work Order đến Content · AMC-CONTENT-HANDOFF-01

**Kết luận ở main `7446bc8`.** Content lead đã đọc được một work order `web_use_guide` do reviewer độc lập ký cho brief nội bộ. Khi chính người nhận gửi loại tài sản đó qua API tạo task, validation trả HTTP 422 ở `deliverable_type`. Thử tạo manifest WF-13 từ bản brief gốc cũng trả 409 do sai loại bản giao. Cần một contract có phiên bản để sản xuất đúng hướng dẫn trên trang sản phẩm. Không có Content task, manifest, run, bản thảo, Content QA, practitioner acceptance, publication hoặc kết quả kinh doanh trong hành trình này. [Receipt và delta dữ liệu](admission.json)

## Phần nào đã chạy

| Bước | Dữ kiện quan sát được |
|---|---|
| Nguồn và Strategy | Commission in-house có brief, projection, manifest và Workforce run. Director, Research và Strategy đóng ba attempt qua dispatcher/worker PostgreSQL với câu trả lời do Codex cung cấp. |
| Sửa và duyệt | Editor sửa Research/Strategy trong Studio. Người duyệt độc lập ký ba nhóm và QA tài liệu tại revision 2. Có thể truy ngược document ID, digest, QA receipt, release và manifest trong lineage. |
| Giao việc | Recipient đọc đúng receipt và work order từ API. Có mục đích của brief và asset, audience, buyer action/CTA, style, requirements, exclusions, acceptance criteria, placement, wording đã duyệt, claim limits và trạng thái đo `planned_only`. |
| Admission | 4/4 loại asset bị từ chối. Cùng một request hợp lệ về actor/campaign nhưng sai loại asset, gửi đồng thời cùng key rồi đọc lại, không tạo task hoặc reservation. Số brief, manifest, run, action request và ledger entry trước/sau giữ nguyên. |
| Thực thi Content | Dừng trước queue. Chưa có phép thử retry worker, thu hồi giữa admission và dùng kết quả, signoff Content hoặc raw/assembled Content trên lineage này. |
| Quyền bên ngoài | Work order cho phép chuẩn bị nội bộ. Không cấp quyền tìm người phỏng vấn, gửi thông điệp, publish hoặc spend. KPI vẫn là kế hoạch. |

[Phép thử thực thi và các denial](../../../tests/test_content_handoff_admission.py) · [Baseline phân quyền, replay và withdrawal](../../../tests/test_strategy_runtime_handoff.py)

## Bốn loại tài sản và contract thực thi

| Tài sản, người sử dụng | Đầu vào và placement | Workflow gần nhất và phần tái sử dụng | Contract thiếu, đầu ra thực tế và quyền |
|---|---|---|---|
| **web_use_guide** · Content lead viết cho người sử dụng sản phẩm | Tình huống sử dụng đã release, bước/hướng dẫn có căn cứ, wording và qualifier, CTA của brief. Web hoặc owned product page. | WF-13 @6 có Content, giữ terms và action, trả headline, value proposition, benefit, CTA cùng SEO. Đây là ca gần nhất và đã thử nhận việc bằng API. | Thiếu loại hướng dẫn nhúng trong trang hiện hữu và liên kết receipt ở admission. WF-13 tạo landing copy/SEO. Work order chỉ cho phép soạn nội bộ. |
| **web_terms_panel** · Content lead viết cho người mua cần kiểm điều kiện | Điều kiện mua đã phát hành, giới hạn áp dụng, thông tin còn thiếu cần hỏi bên có quyền. Cùng hai placement web. | Phần commercial terms của Studio và kiểm qualifier có thể tái sử dụng. | Panel là một thành phần trên trang. Hiện TaskIntent chỉ có loại landing cho WF-13, chưa có asset panel, layout và signoff riêng. |
| **counter_use_card** · Nhân viên tại quầy giải thích thao tác | Tình huống trực tiếp, dữ kiện sản phẩm cho phép dùng, hướng trình diễn và giới hạn mẫu. Owned counter card. | Content hiện có kỹ năng viết câu cho người mua; WF-08 tạo storyboard cho video. | Cả page copy/SEO và video storyboard đều khác loại thẻ trình diễn tại quầy. Không có contract task, Studio artifact hoặc quyền in/phát hành thẻ. |
| **counter_terms_card** · Nhân viên tại quầy trao đổi thông số với người mua | Điều kiện, thông số được duyệt và hướng làm rõ trước khi đặt. Owned counter card. | Dùng lại kiểm terms và evidence ở cấp span khi thiết kế sau này. | Thiếu loại thẻ thông tin và projection/renderer theo placement. Site search snippet không thực hiện được công việc này. |

**Căn cứ trong mã.** Handoff /2 liệt kê loại tài sản, mục đích, placement và work order đã lọc cho recipient. TaskIntent và ActionIntent nhận `marketing_strategy` hoặc `landing_page`; StoryboardIntent có loại riêng `video_storyboard`. Manifest kiểm loại brief trước khi chọn release. Registry pin adapter theo release; Studio WF-13 tạo copy/SEO. Sự tồn tại của role Content hoặc workflow trong charter không tạo thêm hợp đồng thực thi. [Handoff /2](../../../app/c3_strategy_handoff.py) · [Task contract](../../../app/c3_tasks.py) · [Projection](../../../app/c3_projection.py) · [Registry](../../../app/registry_adapters.py) · [WF-13 @6](../../../catalog/landing-seo-v6.json) · [Studio](../../../app/c3_studio.py) · [Workflow catalog](../../../catalog/workflows.json)

**In-house và agency.** Handoff /2 hiện yêu cầu WF-03 trên internal commission. Internal task API kiểm mode in-house và campaign thuộc tenant, còn agency đi qua brief gửi cho đúng khách theo grant và chính khách submit. Một agency dùng intent hợp lệ để thử internal route nhận 404. Khách có grant submit `web_terms_panel` cho agency brief của mình nhận 422 ở loại bản giao. Riêng work order đã ký vẫn không thêm quyền cho người khác, tenant khác hoặc người nhận sau khi Strategy đổi revision/source bị thu hồi. Các ca hai khách cùng agency và thu hồi mandate nằm trong bộ hồi quy đi kèm. [Receipt agency](agency.json)

**Giới hạn tiết lộ nguồn.** Work order hợp lệ giữ nguyên cả câu “For indoor sorting only.” Khi excerpt được phép đối chiếu chỉ bao gồm phần mô tả khay, cùng quy trình ký trả `brief_disclosure_blocked`; người nhận không thấy work order. Ca này được giữ làm kiểm thử hồi quy. [Receipt hold](partial-excerpt.json)

**Replay và recovery.** Ở bước ký Strategy, hai request đồng thời rồi một lần gửi lại sau khi mất phản hồi trả cùng receipt. Khi revision thay đổi, quyết định cũ trả 412. Khi source hoặc mandate bị thu hồi, bộ kiểm tra Strategy đánh giá lại điều kiện ký. Ở bước tạo Content task, cả hai request bị từ chối trước khi ghi dữ liệu. Chưa thể kiểm recovery của Content worker, thu hồi sau khi nhận task hoặc QA đầu ra cho guide cho tới khi có contract tương thích.

**Lần chạy phát triển.** Hai lần dựng ca agency ban đầu thất bại ở bước chuẩn bị fixture. Ca cuối dùng đúng loại workspace, brief đủ điều kiện và tài khoản khách được cấp quyền trên đúng client. Ca thiếu qualifier trong excerpt được lưu riêng với trạng thái hold. Các số liệu nghiệm thu bên dưới lấy từ lần chạy sau cùng.

## Đề xuất hẹp, chưa triển khai

Đề xuất review phiên bản kế tiếp cho **một** asset `web_use_guide` in-house. Product Owner cần quyết định trước về nội dung đủ dùng của hướng dẫn trên trang sản phẩm, ai ký và phần được phép release. Giữ nguyên semantics của task, WF-03, WF-13 và các receipt hiện có.

1. Khi chính recipient bấm bắt đầu, server đọc lại quyết định còn hiệu lực và phạm vi tenant/client/brand/campaign; lấy nguyên allowlist của recipient projection và exact product wording/qualifiers. Ghim Strategy document, revision/digest, final QA và handoff receipt làm đầu vào cho task có phiên bản. Mọi ghi chú, locator và mandate nội bộ ở lại nguồn.
2. Chọn hoặc đề xuất phiên bản registry/adapter có thể trả về guide trên trang hiện hữu, gồm tình huống, bước sử dụng có bằng chứng, giới hạn và CTA. Nếu nguồn chỉ cho phép mô tả sản phẩm, giữ việc để bổ sung căn cứ cho bước thao tác. Không thêm SEO bắt buộc chỉ vì release landing hiện có dùng hai role.
3. Tái sử dụng queue, ledger, admission key, worker checkpoint và QA độc lập. Cần test lại quyền tại admission, khi nhận kết quả và khi ký. Khóa quan hệ một receipt + một phiên bản task + một recipient, kiểm duplicate, concurrent request, mất phản hồi, retry và nguồn/mandate bị thu hồi giữa các bước. Handoff không tự tạo reservation. Sau Content QA, publish vẫn là quyền riêng. Chưa triển khai schema, table, adapter, service hay release mới.

## Gói chấm D/A/C · development only

Gói gồm **Studio Working Draft đã lưu** và **research_notes.fields nguyên văn** của cùng một run có checkpoint. Lấy riêng từng phần từ API bằng phiên của editor đã lưu bản đó. Phiên reviewer độc lập cung cấp lineage QA còn hiệu lực. Kiểm document, revision, campaign, run, đường dẫn manifest đúng tenant/client/brand, digest manifest, digest preview, từng digest nhóm Studio và equality giữa raw notes với checkpoint ghim của reviewer; đọc lại QA receipt/revision sau khi lấy dữ liệu. Nếu thiếu quyền, dữ liệu không đồng nhất hoặc receipt hết hiệu lực, dừng thu gói. Đây là công cụ test trên fixture công khai, không có endpoint xuất dữ liệu khách. [Bằng chứng và các SHA-256](assembled.json) · [Mã kiểm](../../../tests/content_handoff_packet.py)

- **Studio-only** cho thấy nội dung editor thực sự sửa; câu hỏi và evidence biên tập vẫn xem được độc lập với notes. Raw notes giữ giá trị từ trước khi sửa, kể cả phần chưa được xác minh. Chúng không được dùng để chứng minh tuyên bố Marketing.
- **Hai phần ghép** có SHA-256 riêng và digest liên kết với lineage, dùng JSON UTF-8 canonical của repo. Ca phát triển kiểm raw evidence_needed chứa switch/hold, trong khi preview, Studio-only và recipient work order không có câu đó. Phạm vi đọc riêng của staff ở các API khác không thay đổi.
- **D** lấy deterministic composition của cùng projection, đối chiếu với suggestions trả về từ Studio và ghi `worker_notes=null`. Đây là control tái dựng, không có worker D. **A/C** dùng chung quy tắc ghép; một trace điều khiển kiểm apparatus cho cả hai, chưa có output thực nghiệm của model A hoặc C, điểm chấm hay số phút biên tập.
- **Cohort** 12 brief và tối đa 72 lượt vẫn PROPOSED. Giữ phân bổ, counterbalance, việc khóa rubric và vai trò custodian/hai evaluator của protocol. Với ca bị QA giữ, ghi outcome thiếu hoặc hold theo protocol, không chỉ chọn các ca pass để chấm. Bảy câu procedural /1 chỉ bao phủ danh mục đã review. Không mở cohort và không mở rộng waiver. [Protocol](../rs02/NEXT-PROTOCOL.md)

## Bàn giao và rollback

[Chứng nhận main và tài nguyên CI](MAIN-68.md) · [JUnit cục bộ](junit.xml) · [Manifest của candidate](MANIFEST.json). Tại PostgreSQL dev theo cấu hình trong workflow CI của repo, đặt `AMC_TEST_PG=1` rồi chạy `python -m pytest -q tests/test_content_handoff_admission.py tests/test_strategy_runtime_handoff.py tests/test_c3_internal_worker.py tests/test_research_instruction.py tests/test_rs02_contract_alignment.py --junitxml=focused.xml`. Nhóm này đạt **43/43** trên PostgreSQL. Để tái tạo bốn JSON bằng các ID mới, đặt `AMC_CONTENT_HANDOFF_EVIDENCE` tới thư mục output trước khi chạy. Chỉ dữ liệu tổng hợp. Rollback bằng revert thay đổi evaluation và tài liệu; receipt sản phẩm lịch sử giữ nguyên.

Full regression cục bộ chạy bằng `python -m pytest -q` trên database test riêng đã migrate lên v26. Baseline đạt 795, skip 2. Candidate có thêm 7 ca, đạt **802**, skip **2**, thời gian 24 phút 40 giây. Hai skip là biến thể SQLite của các phép kiểm dành cho PostgreSQL. Ruff đạt trên các tệp Python thay đổi. Theo quyết định của Product Owner, CI trên push/head/trial của draft này chưa chạy. [JUnit toàn bộ của candidate](junit-full.xml)

**AMC-R68-01 · P3 · OPEN, static.** Diagnostic cũ có thể còn trên span đã được phân loại editorial; Studio có thể ưu tiên diagnostic đó. Signoff lịch sử cũng cần phân biệt với QA eligibility sau khi thu hồi mandate. Khi có thay đổi presentation liên quan, tái hiện qua API và Chromium trước, rồi sửa cách hiển thị nếu xác nhận được. Không đổi canonical report/digest để sửa nhãn. Không thay UI trong vòng này.

**Điểm cần Independent Review quyết định:** có phê duyệt thiết kế một contract mới cho guide trên trang sản phẩm hay giữ giới hạn hiện tại. Commercial GA và production vẫn NO-GO.
