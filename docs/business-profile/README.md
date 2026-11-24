# Business Profile & Brand Intelligence · Gói triển khai tiếp theo

**Quyết định đề xuất.** Cho phép agency ghi dữ kiện Marketing một lần theo khách hàng/thương hiệu, duyệt claim kèm nguồn, rồi xem chính xác phiên bản WF-03 và WF-13 sẽ dùng. Người phụ trách chiến dịch có thể trả lời “ai duyệt, câu nào được phép viết, và thông tin còn hiệu lực tới khi nào”. Đây là thiết kế và fixture nghiệm thu cho increment sản phẩm tiếp theo. Base đối chiếu là `ece8ecc84b4938900821ff85403bb5b8243534c6` (schema v18). Commercial GA vẫn **NO-GO** theo [release gates](../SECURITY_AND_GA_BLOCKERS.md).

## Điểm bắt đầu từ mã đang có

| Hành vi ở base | Điểm nối đề xuất |
|---|---|
| `Brand` thuộc tenant/client và đang lưu `brand_guidelines`, `product_truth`. `Campaign` thuộc brand. [Mô hình hiện tại](../../app/models.py) | Tạo Business Profile cấp client và Brand Intelligence cấp brand. Dùng quan hệ hiện hữu để xác định scope từ campaign. |
| Khách có grant gửi brief gồm objective, audience, offer và 1–4 nguồn. `start()` khóa brief, đối chiếu run trước, xây `run.knowledge` từ brief, brand và pin registry. [Luồng brief và run](../../app/workforce.py) | Chèn bước materialize snapshot ngay trong giao dịch tạo run của release mới. Khi retry, so với snapshot đã pin của run đầu. |
| WF-03 tạo research/strategy, yêu cầu KPI và kiểm sự phù hợp của nguồn baseline. WF-13 kiểm brief/brand alignment, claim, SEO và vùng landing copy. [WF-03](../../app/research_strategy.py) · [QA landing](../../app/landing_qa.py) | Hai adapter mới đọc cùng snapshot và xuất locator có thể giải về đúng claim, revision, nguồn và đoạn trích. |
| Registry chọn release trong phạm vi tenant/campaign; manifest và contract được pin. [Binding hiện tại](../../app/registry.py) · [WF-03 v1](../../catalog/research-strategy-v1.json) · [WF-13 v4](../../catalog/landing-seo-v4.json) | Xuất bản manifest mới cho mỗi workflow sau test tương thích, giữ khả năng chạy các manifest đã phê duyệt. |

## Luồng sử dụng nội bộ đầu tiên

1. Nhân viên mở **Hồ sơ doanh nghiệp** trong đúng client, nhập công ty, sản phẩm/dịch vụ, khu vực phục vụ, khách hàng mục tiêu và mục tiêu kinh doanh. Mỗi mục hiện người chịu trách nhiệm, nguồn và lần rà soát gần nhất.
2. Tại **Thương hiệu**, biên tập viên thêm tone, thuật ngữ, điều cấm, CTA, claim và điều kiện áp dụng theo thời gian/thị trường/kênh. Tài liệu nội bộ chỉ cung cấp trích đoạn tối thiểu cần cho workflow.
3. Chủ workspace hoặc admin được phân công kiểm câu chữ cạnh nguồn, chọn duyệt/từ chối và thời hạn. Trạng thái quan sát được gồm draft, approved, superseded, withdrawn, expired. Sửa một claim đã duyệt tạo draft revision mới; claim cũ chỉ đổi hiệu lực qua event có người chịu trách nhiệm.
4. Từ brief chiến dịch, staff xem preview dữ liệu WF-03 hoặc WF-13 nhận được. Preview liệt kê dữ kiện sẽ pin, giả thuyết, nguồn hết hạn và khoảng trống theo từng loại đầu ra. Xác nhận preview và queue run trong cùng một phiên bản.
5. Khi xem draft Marketing, QA chọn một claim để mở đúng revision và đoạn chứng cứ. Nếu nguồn bị rút sau khi tạo draft, hồ sơ hiển thị bản lịch sử cùng quyết định cần làm trước lần chia sẻ mới.

**Ví dụ nghiệm thu.** Danh mục ghi khách được chạm bản sao và hiện vật gốc nằm sau kính. WF-03 ghi nhận dịch vụ này như một fact, còn “giáo viên sẽ mua nhiều nhất” chỉ là giả thuyết. WF-13 có thể viết CTA “Đăng ký lịch tham quan bản sao”. Câu “chạm hiện vật gốc” phải tạo finding trước khi chia sẻ. Tập dữ liệu dùng tên và số liệu tổng hợp. [Snapshot mẫu đã đóng băng](synthetic-snapshot.json)

## Dữ liệu và quyền đề xuất

| Dữ liệu | Trường bắt buộc và quy tắc cho bản đầu |
|---|---|
| Company / product / service | Tên doanh nghiệp, lĩnh vực, dịch vụ hoặc SKU, tên hiển thị, thị trường, availability, đơn vị giá nếu có, source revision và owner. Lưu phiếu giá kèm thời hạn nếu dùng claim về giá. |
| ICP / segment | Khu vực, nhu cầu, tiêu chí phân khúc, kênh, căn cứ fact/hypothesis và nguồn; dùng mô tả nhóm tổng hợp. Thiếu số liệu vẫn có thể tạo giả thuyết có nhãn. |
| Business objective | Tên KPI, đơn vị, baseline hoặc unknown, mục tiêu, cửa sổ đo, owner, phương pháp và nguồn cho số lịch sử. Target có nhãn riêng để giữ ý nghĩa dự báo. |
| Brand guidelines | Voice/tone, ngôn ngữ, từ bắt buộc/cấm, CTA được phép, ngoại lệ theo kênh, guideline revision và nguồn. |
| Approved claim | ID ổn định, revision, nguyên văn, qualifier, channel/locale/market, approved_by/at, from/until, nguồn và locator. Mọi claim đã duyệt có ít nhất một source revision đủ hiệu lực cho mục đích đó. |
| Evidence source | Publisher, loại, URI hoặc internal artifact ref, đoạn trích, thời điểm quan sát/hiệu lực, lịch review, digest nội dung, owner, license/visibility và trạng thái. `observed_at` không mặc nhiên là ngày xuất bản. |
| Snapshot | Contract version, tenant/client/brand/campaign, brief revision, các revision profile/claim/source, as_of UTC, nội dung được chiếu, ordered citations và digest. Event về việc thu hồi tham chiếu đến snapshot cũ mà không thay bytes. |

Nguồn gốc được đóng băng trong kho dữ liệu Marketing của AMC. Không truyền profile, campaign hoặc dữ liệu khách tới Research Broker engineering. Cho phép đọc snapshot chỉ khi subject có quyền hiện hành với scope nguồn. Chủ thể worker có grant giới hạn theo từng run. Customer portal tiếp tục dùng brief được giao và snapshot đã chia sẻ; quyền xem khách hàng không mở quyền xem kho nội bộ, nguồn giá hay profile của khách khác.

Đề xuất editor tạo draft trong scope, admin/owner duyệt và thu hồi, viewer nội bộ đọc trong scope hiện hành. Author của claim thương mại nhạy cảm gửi người thứ hai có quyền duyệt. Tại API và PostgreSQL, ràng buộc composite tenant/client/brand/campaign cho mọi quan hệ, kể cả bảng liên kết evidence. Một source thuộc khách A không thể được gắn vào claim khách B. Dùng RLS mới với default deny và kiểm bằng signed runtime LOGIN trên dữ liệu tổng hợp. Audit ghi actor/revision/digest cho tạo, duyệt, từ chối, thu hồi, snapshot và activation.

## Hợp đồng immutable source snapshot

- Tên hợp đồng đề xuất `brand_knowledge.snapshot.v1`. Snapshot lưu server-side theo scope, digest và revision. `scope` được resolve từ campaign/brief và quyền actor ở server. Dữ liệu JSON từ trình duyệt chỉ chọn các revision hợp lệ; server tự dựng projection và digest, không tin client tự khai nguồn hay quyền.
- Định nghĩa digest cho fixture v1 là SHA-256 trên JSON UTF-8, khóa object sắp xếp tăng theo Unicode code point, mảng giữ thứ tự đã khai báo, số nguyên, boolean, null, chuỗi, không BOM/spaces. Giá trị số thập phân dùng chuỗi giá trị kèm đơn vị theo field contract; normalize chuỗi và sort array theo ID tại bước materialize. Reject duplicate property và giá trị ngoài contract. Fixture mẫu có digest `fe1dd0fe2b9907634c688f13fed44889b5410541243dffdef6573e57b8702fda`. Thời điểm pin, source bytes và approval provenance phải có khả năng tái dựng.
- Đề xuất preview trả `expected_profile_revision`, `expected_claims_revision`, `as_of` và `snapshot_digest`. Queue lần đầu kiểm scope, quyền và ngày hiệu lực theo giờ server, khóa brief và kiểm lại expected revisions cùng preview digest trong giao dịch. Nếu preview cũ hoặc nguồn đã hết hạn, trả 409/412 kèm lý do cần tải lại. Lưu snapshot và run cùng transaction. Mất kết nối sau commit, retry đúng terms trả run và digest đầu tiên kể cả profile sau đó đổi. Yêu cầu terms khác cho brief đã có run trả 409. Journal giữ lịch sử retry.
- Chế độ Agency dùng owner/client cụ thể ở mọi selector. In-house dùng brand thuộc client nội bộ đã cấu hình; khóa tenant/brand vẫn bắt buộc. Với bản ghi legacy, release cũ tiếp tục đọc `brand` và `S1..S4` như trước. Khi tạo profile ban đầu từ legacy text, nguồn mang trạng thái imported/unreviewed và yêu cầu người có quyền xác nhận trước khi dùng như approved claim.
- **WF-03** ghi `knowledge_snapshot_digest` và danh mục source handles vào run. Research xuất fact/assumption/gap kèm source ref. Strategy chọn KPI, đơn vị, cửa sổ đo và baseline hiển thị “unknown” khi thiếu chứng cứ. Thuộc tính ICP có nhãn hypothesis không thể là baseline đã kiểm. Thất bại: ghi gap cho research; khi prerequisite bắt buộc thiếu thì dừng trước sản xuất deliverable.
- **WF-13** nhận cùng digest khi chọn chính phiên bản đó trên cùng scope. Bổ sung typed qualifier và claim/source refs vào contract adapter mới. Content/SEO đọc projection theo channel/locale và thời hạn. Verifier QA giải `claim_id@revision → source_id@revision → excerpt` từ bản pin, kiểm qualifier trong copy và metadata. Với claim mâu thuẫn hoặc bị rút, nghĩa vụ QA/share còn mở. Không thay hợp đồng snapshot delivery hay quy tắc digest/revision đã nghiệm thu.
- **Thay đổi hiệu lực sau khi queue.** Worker replay dùng bytes từ snapshot đã pin. Hệ thống ghi event invalidation cho run/draft phụ thuộc, thể hiện cho QA và kiểm lại tại share. Cần lấy snapshot mới cho công việc mới hoặc quyết định human review có căn cứ. Khách đã duyệt một bản giao giữ đúng proof và nội dung trước đó.

## Gói implementation, thứ tự và bằng chứng

| Lát cắt | Chủ thể và đầu việc | Chứng cứ kết thúc |
|---|---|---|
| C1 · dữ liệu và quyền | Backend + DB owner chọn số migration tiếp theo sau khi cập nhật main; tạo revisioned profile/claim/source và RLS. Thiết kế additive với restore từ backup đã đối chiếu. | Exact migrations của main mới, upgrade có dữ liệu, chạy lại, khôi phục snapshot/hồ sơ lịch sử, assertion bằng runtime LOGIN và kiểm thử đối chứng SQLite. |
| C2 · sử dụng trên UI | Product + UX cùng Marketing editor dựng form, empty states, trạng thái cần dữ liệu, preview, duyệt/thu hồi và lỗi stale save. | Chromium 1280px/390px, quyền editor/approver/viewer/client, mất response/refresh không tạo claim hay revision trùng. |
| C3 · chuyển giao vào Workforce | Registry maintainer + Marketing QA tạo versioned release thử nghiệm cho hai workflow, binder và QA source resolver. Feature opt-in trên campaign tổng hợp. | Hai run Qwen local thật trên đúng SHA, source handles và digest tái dựng, kiểm replay sau thay đổi profile, receipt/usage và screenshot kết quả QA. |
| C4 · nghiệm thu Marketing | Product owner + QA domain kiểm hiệu quả trên brief mới, ghi người gán nhãn, ý kiến bất đồng và giới hạn mẫu. | Tỷ lệ claim có nguồn hợp lệ, số claim thiếu qualifier lọt qua QA, số giả thuyết bị biến thành fact, thời gian lập brief và số lần nhập lại; có mẫu số và baseline. |

| Ca hồi quy cần chạy | Kết quả mong đợi |
|---|---|
| Hai tenant; hai khách trong một agency; hai brand cùng client | Không thể xem, gắn hoặc tạo snapshot từ source ngoài scope. Tác vụ nội bộ và API đều đối chiếu quyền. |
| Hai editor sửa cùng revision hoặc claim lặp A → B → A | Chỉ bản giữ expected revision hợp lệ được ghi, history còn nguyên; retry không sinh revision ngoài dự kiến. |
| Hai request queue cùng brief, một request mất ACK | Một run, một snapshot, một debit/reservation theo logic hiện tại; response sau resolve đúng run trước. |
| Profile thay đổi, source hết hạn hoặc rút khi QA đã mở | Run trước vẫn đọc bytes cũ, lần chia sẻ mới yêu cầu xử lý sự kiện; bản khách đã nhận còn nguyên. |
| Ba nguồn khác nhau cho cùng claim; hai nguồn trái nhau | Hiển thị evidence cạnh nhau, đánh dấu disputed; không nâng thành approved fact trước khi có quyết định và căn cứ. |
| Một CTA hợp lệ, một CTA sai đối tượng chạm; segment chưa chứng minh | WF-03 giữ nhãn hypothesis. WF-13 bắt đúng lỗi đối tượng, không buộc CTA hợp lệ thành finding. |
| Chạy lại release cũ, dữ liệu trước migration, agency và in-house | Giữ output contract và snapshot đã chốt; compiler từ chối activation thiếu adapter/fingerprint đã review. |

**Điều kiện bàn giao.** Bước đầu giao C1 trên main đã đồng bộ phần onboarding; PR schema đó mới chọn version và công bố kiểm thử trên head/integration. Docs này có thể review độc lập ngay. Rollback riêng tài liệu bằng revert commit thiết kế; rollback triển khai tương lai trước tiên ngừng activation mới, để run cũ hoàn tất với pinned release, sau đó phục hồi từ bản sao đã diễn tập nếu cần. Giữ full charter V1 với 37 vai trò. Increment này dùng hai workflow hiện có. [Phạm vi V1.0](../PRODUCT_SPEC_V1.md)

**Phản biện cho reviewer.** Một claim hết hạn giữa preview và queue, một nguồn bị thu hồi giữa QA và share, và một retry đến sau khi brand đã sửa phải dẫn tới ba kết quả phân biệt được bằng run ID, revision và audit. Đối chiếu điều đó trên cả hai khách hàng cùng agency.
