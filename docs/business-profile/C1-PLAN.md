# Kế hoạch C1 · nền dữ liệu và quyền Business Profile

**Gate bắt đầu.** Review độc lập phải chấp thuận C0 trên head đã đồng bộ. Chủ migration kiểm `main`, nhánh Identity và phiên bản registry ngay trước khi mở PR C1; chọn phiên bản trống lúc đó. Xây một PR backend có migration additive, repository/command nội bộ, RLS, audit và phép materialize snapshot. UI đầy đủ, ERP/PIM/CRM, connector, release adapter, external publication và thanh toán nằm trong các increment riêng. Nền kế toán tiếp tục tách AI usage cost, doanh thu SaaS và chi tiêu quảng cáo.

## Dữ liệu và điều kiện bán hàng

| Nhóm record được version hóa | Khóa và ý nghĩa | Điều kiện khi ghi |
|---|---|---|
| Company profile, segment, objective | Khóa tenant/client. Profile chứa trường quick setup và owner. Segment có provenance và nhãn hypothesis/fact. KPI có parent, level, unit, method, window, source và owner. | Staff trong scope ghi draft. Tránh lưu hồ sơ cá nhân trong mô tả nhóm. Chặn cycle KPI và campaign ngoài client. |
| Brand kit, product/service, variant, market | Khóa tenant/client/brand cùng stable subject ID và revision. Variant có composite FK về đúng product. Market chứa thị trường và tập locale; channel có bộ giá trị khai báo. | SKU bên ngoài chỉ là alias theo hệ thống mã. Claim đối với sản phẩm chung cần subject kind được duyệt rõ. Trường variant rỗng không phải wildcard. |
| Offer | Tham chiếu exact product revision, variant revision, market/locale/channel, currency ISO, integer minor units, lịch hiệu lực, quantity tier, availability và policy revision. | Cùng SKU có thể có nhiều offer. Selector đòi đúng một offer thích hợp tại quantity/time/place; bỏ price claim nếu không có hoặc có nhiều kết quả chưa phân giải. USD 18.00 khác 18 VND. |
| Availability, commercial policy | Inventory hoặc năng lực phục vụ theo variant, địa bàn và as-of/valid-until; policy có MOQ, đơn vị, giao hàng, bảo hành và thanh toán. | Draft có thể để unknown. Tuyên bố “còn hàng”, “miễn phí giao hàng” hoặc “bảo hành X tháng” cần authority còn hạn đối với chính thuộc tính. |
| Source revision / applicability | PK scope + source_id + revision. Source bảo toàn publisher, nội dung/locator chính xác, excerpt digest và thời hạn sử dụng. Binding có subject, variant, offer, location/market, locale, channel, qualifiers và source revision. | Tài liệu có thể chứa nhiều SKU. Từng binding phải trỏ đúng đoạn có căn cứ cho SKU/thuộc tính đó. Quyền đọc tài liệu và đủ căn cứ thương mại là hai điều kiện độc lập. |
| Approved claim revision | PK scope + claim_id + revision. Wording, subject, effective interval, qualifiers, approver và nguồn có revision. Link claim-source dùng hai composite FK có cùng tenant/client/brand và binding ID. | Resolver so use context và qualifiers sau khi kiểm FK/RLS; không tự lấy source mới nhất cùng ID. Số lượng bắt buộc và locator được lưu. |
| Snapshot / dependency / authority event | Payload bất biến, digest, run/brief, các source bindings. Bảng dependencies có index ngược từ source/claim revision tới run/draft và receipt QA/share. | Insert trong giao dịch có scope. Invalidation append-only, giữ actor, lý do, effective since, causation và đối tượng. |

C1 cần lưu present/unknown/draft rõ ràng. Chứng cứ dữ liệu có thể là public document, internal artifact hoặc synthetic fixture; các projection phải giữ quyền xem. Dùng `[valid_from, valid_until)` trên UTC cho offer, authority và source revision. Hiệu lực không có ngày kết thúc chỉ được phép nếu policy nguồn cho phép; vẫn cần lịch revalidation.

## Cập nhật, phê duyệt và snapshot

Editor gửi expected revision và idempotency key. Giao dịch khóa aggregate theo scope và lưu revision mới bằng compare-and-set, cùng audit và sự kiện. Cùng key và payload trả kết quả trước đó; payload khác trả xung đột. Duyệt là command target đúng revision/digest, kiểm lại actor và chứng cứ trong cùng giao dịch. Draft extraction từ nguồn chỉ tạo candidate; approver chịu trách nhiệm chọn wording và qualifier cụ thể.

1. Materializer đọc revision đã duyệt và tạo immutable payload với `snapshot_as_of` một lần; lưu preview handle có TTL và `preview_created_at` bên ngoài payload. Một thời điểm as-of mới chỉ xuất hiện khi người dùng tạo **preview mới**.
2. Queue lấy quyền cho brief hiện tại. Nếu đã có receipt cho cùng scope/command, kiểm terms và quyền xem kết quả hiện tại, trả lại run cũ. Không enqueue hay trừ ngân sách lần hai.
3. Queue mới khóa brief và authority guards theo một thứ tự, lấy `effective_at` từ giờ server sau khi đã lấy khóa. Xác thực TTL, scope, current revisions, offer, qualifiers, trạng thái, thời hạn, quyền và digest bằng bytes cũ. Dữ liệu bất biến nhưng thời hạn kinh doanh đã hết là lý do eligibility riêng. Ghi run, `queued_at`, snapshot ref và decision trong cùng commit. UI phân biệt “nguồn đã hết hạn” và “bản ghi đã thay”.
4. Mốc release C3 sẽ pin manifest mới cho WF-03/WF-13 và handle typed đã cấp; source_ids do model trả chỉ cho phép thuộc snapshot đó. Replays cũ vẫn dùng đúng pinned adapter và bytes đã duyệt.

## Thu hồi, QA và share

| Trạng thái hiện hành | Chia sẻ mới | Lịch sử và đường xử lý |
|---|---|---|
| Approved, chưa hết hạn | Chấp nhận khi quyền và QA revision/digest đều khớp | Ghi event, source/claim revisions, authority epoch và effective_at. |
| Superseded | Tạm chặn reuse revision cũ cho share mới của draft | Bản thay thế phải bind lại đúng subject và QA lại. Bản đã giao hiện trạng thái superseded. |
| Expired | Chặn từ đúng thời điểm kết thúc, cả khi QA trước hạn | Refresh nguồn/offer, pin revision đủ hiệu lực và QA lại. |
| Disputed | Chặn tới khi người có thẩm quyền giải quyết bằng evidence | Dissent và quyết định được gắn actor, lý do và nguồn. |
| Withdrawn do sai sự thật/vi phạm | Hard stop cho queue/QA/share thương mại phụ thuộc. Quản trị viên thông thường cũng bị chặn. | Append sự kiện. Cần claim/source revision khác đủ căn cứ cùng QA mới; receipt QA cũ không khôi phục thẩm quyền. |

Đề xuất dùng authority guard ở scope tenant/client/brand cho C1. Mọi mutation làm thay đổi quyền dùng nguồn/claim, tác vụ QA và tác vụ share đi qua cùng giao dịch guard. Lấy các guard theo thứ tự khóa scope ổn định trước khóa brief/deliverable. Đọc lại grant và authority sau khi lấy khóa; lưu quyết định và tăng epoch khi cần trong cùng commit. Đường thu hồi quyền và membership phải tham gia serialization của kiểm quyền hoặc được kiểm lại bằng DB gate tương đương; C1 phải chứng minh bằng hai kết nối.

Nếu withdrawal commit trước, QA/share sau thấy trạng thái mới và trả conflict. Nếu share commit trước, snapshot/receipt đó được giữ làm lịch sử; withdrawal tiếp theo ghi cảnh báo cho bản cũ và chặn mọi share/re-share tiếp theo. Kiểm quyền trước khi trả artifact lịch sử. Người xem được phép thấy cảnh báo “nguồn đã thu hồi”; entitlement cũ không cho tải thêm dữ liệu ngoài scope. Mạng/outbox chỉ xử lý sau decision commit và theo gate external actions. C0 không kích hoạt external action.

## Phân kỳ và nghiệm thu

| Thứ tự | Thay đổi trong PR nền | Chứng cứ go/no-go |
|---|---|---|
| 1 | Author/approver policy, tenant/client/brand composite keys, tables và migration additive | Ca dữ liệu thật sự được tạo bởi binary trước trên DB tổng hợp, rerun migration và so backup/restore; default deny khi thiếu context. |
| 2 | Commands draft, append revision, approve, invalidate, source resolve | Signed restricted runtime LOGIN không sửa history. Hai writer cùng revision chỉ một kết quả. Scope A/B cùng agency và khác tenant, hai SKU trong cùng brand có negative + positive controls. |
| 3 | Projection quick setup, compiler/preview, CAS queue foundation | Preview qua nhiều giây dùng đúng digest, source hết hạn giữa preview và queue bị chặn. Recovery sau commit trả cùng snapshot. |
| 4 | Guard và lịch sử authority; chọn transaction protocol đối với share | Hai transaction thật, lock observation có timeout, hai thứ tự withdrawal/share và QA/share; lịch sử giữ checksum, re-share bị chặn. |
| 5 | Bàn giao và review | Kiểm exact head và prospective integration, migration matrix, screenshot/UI khi đến C2, local model 2 workflow khi đến C3. Mỗi milestone phân biệt measured, synthetic và pending. |

Rollback ứng dụng C1 bằng vô hiệu hóa activation mới và dùng binary tương thích schema đã migrate, lưu lại history/authority. Nếu cần rollback schema, phục hồi bản backup trước migration sang DB riêng và so checksum trước cutover. Không hạ version marker trực tiếp. C0 chỉ thay tài liệu, fixture, kiểm định và CI theo path; có thể revert commit C0.
