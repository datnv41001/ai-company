# Business Profile & Brand Intelligence · Gói triển khai tiếp theo

**Quyết định đề xuất.** Cho phép agency ghi dữ kiện Marketing một lần theo khách hàng/thương hiệu, duyệt claim kèm nguồn, rồi xem chính xác phiên bản WF-03 và WF-13 sẽ dùng. Người phụ trách chiến dịch có thể trả lời “ai duyệt, câu nào được phép viết, và thông tin còn hiệu lực tới khi nào”. Đây là thiết kế và fixture nghiệm thu cho increment sản phẩm tiếp theo. Đề xuất ban đầu đối chiếu schema v18 tại `ece8ecc8`. Bản C0 đã đồng bộ onboarding từ `49cbc070` (schema v20). Commercial GA vẫn **NO-GO** theo [release gates](../SECURITY_AND_GA_BLOCKERS.md).

## Quyết định C0 sau review thiết kế

| Phản biện | Quy tắc hiện hành | Bằng chứng trong PR |
|---|---|---|
| BP-P1-01 | Product/Service và Variant mô tả đối tượng. Offer xác định giá + currency, quantity, hạn, kênh và thị trường; Availability xác định tồn/công suất và địa bàn; Commercial Policy xác định MOQ, giao hàng, bảo hành, thanh toán. Approved Claim sử dụng đúng phạm vi và nguồn đã duyệt. | [Snapshot tổng hợp](synthetic-snapshot.json) và [bộ ca thương mại](acceptance-cases.json) |
| BP-P1-02 | Giữ nguyên snapshot_as_of và bytes của preview. Kiểm lại thời hạn và quyền tại effective_at khi queue, QA và share. | Ca preview giữ digest khi đồng hồ chạy; hết hạn đúng biên bị từ chối. |
| BP-P1-03 | Withdrawn vì thông tin sai hoặc bị cấm chặn mọi share mới, kể cả khi QA đã duyệt. Chỉ claim/revision mới với chứng cứ đủ và QA mới tạo lại thẩm quyền. | [Giao dịch thu hồi, QA và share](C1-PLAN.md#thu-hồi-qa-và-share) |
| BP-P1-04 | Claim và nguồn phải khớp tenant, client, brand, product, variant, offer, market, channel, locale, revision, locator và qualifier. | Ca khác sản phẩm cùng brand, khác variant, điều kiện bán hoặc revision. |
| BP-P2-01 | Quick setup gồm tên, một sản phẩm/dịch vụ, nhóm khách dự kiến, mục tiêu. Có thể tạo draft brief/ràng buộc còn thiếu; chứng cứ cần cho claim được bổ sung trước khi công bố. | [Hành trình theo quy mô và test](C2-C4-ACCEPTANCE.md) |
| BP-P2-02 | Business objective → Marketing objective → campaign KPI; operational/efficiency KPI liên kết cùng campaign. Tách target, baseline, observed và hypothesis. | Năm tầng trong fixture; từng chỉ số ghi owner, window, unit, method và source. |

**Tái lập kiểm định C0** từ gốc checkout bằng Python 3.12:

```sh
python -m unittest discover -s docs/business-profile -p test_c0.py -v
```

Đây là kiểm tra hợp đồng thiết kế trên dữ liệu tổng hợp. [Kế hoạch C1 với ranh giới giao dịch và RLS](C1-PLAN.md) là đầu vào cho review, chưa phải migration hoặc API đã chạy. Trạng thái của từng release gate Marketing được ghi trong [ma trận nghiệm thu C2/C4](C2-C4-ACCEPTANCE.md).

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
| Company / product / service | Tên doanh nghiệp, lĩnh vực, ID đối tác tùy chọn, dịch vụ hoặc SKU và revision. Variant mang thuộc tính kỹ thuật; Offer/Availability/Commercial Policy có revision và nguồn riêng theo điều kiện ở bảng C0. |
| ICP / segment | Khu vực, nhu cầu, tiêu chí phân khúc, kênh, căn cứ fact/hypothesis và nguồn; dùng mô tả nhóm tổng hợp. Thiếu số liệu vẫn có thể tạo giả thuyết có nhãn. |
| Business objective | Tên KPI, đơn vị, baseline hoặc unknown, mục tiêu, cửa sổ đo, owner, phương pháp và nguồn cho số lịch sử. Target có nhãn riêng để giữ ý nghĩa dự báo. |
| Brand guidelines | Voice/tone, ngôn ngữ, từ bắt buộc/cấm, CTA được phép, ngoại lệ theo kênh, guideline revision và nguồn. |
| Approved claim | ID ổn định, revision, nguyên văn, qualifier, channel/locale/market, approved_by/at, from/until, nguồn và locator. Mọi claim đã duyệt có ít nhất một source revision đủ hiệu lực cho mục đích đó. |
| Evidence source | Publisher, loại, URI hoặc internal artifact ref, đoạn trích, thời điểm quan sát/hiệu lực, lịch review, digest nội dung, owner, license/visibility và trạng thái. `observed_at` không mặc nhiên là ngày xuất bản. |
| Snapshot | Contract version, tenant/client/brand/campaign, brief revision, các revision profile/claim/source, snapshot_as_of UTC, nội dung được chiếu, ordered citations và digest. Event về việc thu hồi tham chiếu đến snapshot cũ mà không thay bytes. |

Nguồn gốc được đóng băng trong kho dữ liệu Marketing của AMC. Không truyền profile, campaign hoặc dữ liệu khách tới Research Broker engineering. Cho phép đọc snapshot chỉ khi subject có quyền hiện hành với scope nguồn. Chủ thể worker có grant giới hạn theo từng run. Customer portal tiếp tục dùng brief được giao và snapshot đã chia sẻ; quyền xem khách hàng không mở quyền xem kho nội bộ, nguồn giá hay profile của khách khác.

Đề xuất editor tạo draft trong scope, admin/owner duyệt và thu hồi, viewer nội bộ đọc trong scope hiện hành. Author của claim thương mại nhạy cảm gửi người thứ hai có quyền duyệt. Tại API và PostgreSQL, ràng buộc composite tenant/client/brand/campaign cho mọi quan hệ, kể cả bảng liên kết evidence. Một source thuộc khách A không thể được gắn vào claim khách B. Dùng RLS mới với default deny và kiểm bằng signed runtime LOGIN trên dữ liệu tổng hợp. Audit ghi actor/revision/digest cho tạo, duyệt, từ chối, thu hồi, snapshot và activation.

## Hợp đồng immutable source snapshot

- Tên hợp đồng đề xuất `brand_knowledge.snapshot.v2`. Snapshot lưu server-side theo scope, digest và revision. `scope` được resolve từ campaign/brief và quyền actor ở server. Dữ liệu JSON từ trình duyệt chỉ chọn các revision hợp lệ; server tự dựng projection và digest, không tin client tự khai nguồn hay quyền.
- Định nghĩa digest cho fixture C0 v2 là SHA-256 trên JSON UTF-8, khóa object sắp xếp tăng theo Unicode code point, mảng giữ thứ tự đã khai báo, số nguyên, boolean, null, chuỗi, không BOM/spaces. Giá trị số thập phân dùng chuỗi giá trị kèm đơn vị theo field contract; materializer áp dụng thứ tự section khai báo trong contract, giữ thứ tự hiển thị có ý nghĩa và chuẩn hóa những bộ ID không có thứ tự trước khi pin. Verifier băm trực tiếp bytes canonical từ chính payload đã lưu. Reject duplicate property và giá trị ngoài contract. Fixture mẫu có digest `13eb3847655ba865841fce37abe1542092e36186732a486c99c14760e9c54b42`. Thời điểm pin, source bytes và approval provenance phải có khả năng tái dựng.
- Preview trả handle bất biến, expected revisions, `snapshot_as_of`, `preview_created_at` và `snapshot_digest`. SHA băm bytes chứa snapshot_as_of cố định. Ba mốc preview_created_at, queued_at và effective_at thuộc metadata bên ngoài digest. Queue lần đầu khóa brief/authority, đối chiếu lại bytes của chính preview, kiểm expected revisions và quyền/hiệu lực tại effective_at do server lấy sau khi khóa. queued_at ghi lúc run được tạo. Nếu preview cũ hoặc nguồn đã hết hạn, trả 409/412 kèm lý do cần tải lại. Lưu snapshot và run cùng transaction. Mất kết nối sau commit, retry đúng terms trả run và digest đầu tiên kể cả profile sau đó đổi. Yêu cầu terms khác cho brief đã có run trả 409. Journal giữ lịch sử retry.
- Chế độ Agency dùng owner/client cụ thể ở mọi selector. In-house dùng brand thuộc client nội bộ đã cấu hình; khóa tenant/brand vẫn bắt buộc. Với bản ghi legacy, release cũ tiếp tục đọc `brand` và `S1..S4` như trước. Khi tạo profile ban đầu từ legacy text, nguồn mang trạng thái imported/unreviewed và yêu cầu người có quyền xác nhận trước khi dùng như approved claim.
- **WF-03** ghi `knowledge_snapshot_digest` và danh mục source handles vào run. Research xuất fact/assumption/gap kèm source ref. Strategy chọn KPI, đơn vị, cửa sổ đo và baseline hiển thị “unknown” khi thiếu chứng cứ. Thuộc tính ICP có nhãn hypothesis không thể là baseline đã kiểm. Thất bại: ghi gap cho research; khi prerequisite bắt buộc thiếu thì dừng trước sản xuất deliverable.
- **WF-13** nhận cùng digest khi chọn chính phiên bản đó trên cùng scope. Bổ sung typed qualifier và claim/source refs vào contract adapter mới. Content/SEO đọc projection theo channel/locale và thời hạn. Verifier QA giải `claim_id@revision → source_id@revision → excerpt` từ bản pin, kiểm qualifier trong copy và metadata. Với claim mâu thuẫn hoặc bị rút, nghĩa vụ QA/share còn mở. Không thay hợp đồng snapshot delivery hay quy tắc digest/revision đã nghiệm thu.
- **Thay đổi hiệu lực sau khi queue.** Worker replay dùng bytes từ snapshot đã pin. Hệ thống ghi event invalidation cho run/draft phụ thuộc, thể hiện cho QA và kiểm lại tại share. Withdrawal nghiêm trọng khóa share mới. Bắt buộc thay revision/chứng cứ, tạo snapshot mới và QA lại theo thứ tự giao dịch trong kế hoạch C1. Khách đã duyệt một bản giao giữ đúng proof và nội dung trước đó.

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

**Điều kiện bàn giao.** Chốt review độc lập C0 trước C1. PR C1 chọn migration trống trên main tại thời điểm triển khai/tích hợp và công bố kiểm thử trên head/integration; khi một nhánh Identity cũng thêm migration cần cập nhật số, checksum, đường nâng và rehearsal trước merge. Docs này có thể review độc lập ngay. Rollback riêng tài liệu bằng revert commit thiết kế; rollback triển khai tương lai trước tiên ngừng activation mới, để run cũ hoàn tất với pinned release, sau đó phục hồi từ bản sao đã diễn tập nếu cần. Giữ full charter V1 với 37 vai trò. Increment này dùng hai workflow hiện có. [Phạm vi V1.0](../PRODUCT_SPEC_V1.md)

**Phản biện cho reviewer.** Một claim hết hạn giữa preview và queue, một nguồn bị thu hồi giữa QA và share, và một retry đến sau khi brand đã sửa phải dẫn tới ba kết quả phân biệt được bằng run ID, revision và audit. Đối chiếu điều đó trên cả hai khách hàng cùng agency.
