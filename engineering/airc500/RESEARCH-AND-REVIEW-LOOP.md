# Research Broker và điều phối review theo sự kiện

**Quyết định thiết kế B5/B6.** Pilot engineering dùng fixture cục bộ. Hai bộ tích hợp bên dưới là backlog cho giai đoạn sau pilot. Chủ dự án duyệt danh mục nguồn, ngân sách và quyền handoff một lần theo phạm vi đã định. Coordinator chịu trách nhiệm phân công và thu hồi assignment khi PR đổi phiên bản.

## B5 · Nghiên cứu có thể kiểm chứng

Reviewer gửi `ResearchRequest` chứa ID run, assignment, câu hỏi, loại nguồn, thị trường, ngôn ngữ, mốc thời gian và tiêu chí kết thúc. Broker xác minh grant, lập khóa cache từ chủ đề công khai đã chuẩn hóa, nguồn cho phép, khu vực và phiên bản policy. Lưu liên kết từ yêu cầu riêng của từng reviewer tới artifact dùng chung. Trước blind seal chỉ được chia sẻ **tư liệu gốc** cho các assignment có cùng quyền. Không kèm số người yêu cầu, kết luận, tên requester, ghi chú hoặc evidence của peer. Worker chỉ nhận bản trích và metadata qua handle nội bộ.

| Loại nguồn | Dùng để trả lời | Cách giới hạn diễn giải |
|---|---|---|
| Tài liệu chính thức, policy nền tảng và cơ quan quản lý | API cam kết gì, policy áp dụng ở đâu và từ ngày nào | Pin bản phát hành/hiệu lực, jurisdiction và người chịu trách nhiệm khi cần tư vấn |
| Source GitHub công khai | Hợp đồng kỹ thuật, license hoặc tương thích | Repository, commit, path, dòng, phạm vi license và trích đoạn |
| Cộng đồng Marketing và thảo luận công khai | Khó khăn, ngôn ngữ khách hàng, giả thuyết cần kiểm chứng | Trích ẩn danh theo điều kiện sử dụng; ghi sai lệch chọn mẫu và thời điểm |
| Báo cáo thị trường | Quy mô, phân khúc hoặc xu hướng có định nghĩa | Phương pháp, mẫu, đơn vị, thời kỳ và quyền trích dẫn |
| Sản phẩm và đánh giá đối thủ | Giá/điều kiện công bố và mô tả trải nghiệm | Đánh dấu tài liệu first-party, nhận xét trải nghiệm và tuyên bố chưa đối chứng riêng |

Fetcher chỉ dùng adapter đọc đã duyệt, HTTPS public allowlist và hạn mức request/bytes/thời gian; kiểm tra mỗi đích redirect và DNS, chặn địa chỉ nội bộ, file cục bộ, binary ngoài policy. Egress gateway tự tạo request tối thiểu từ topic ID và bộ từ khóa công khai. Mã AMC, diff, token, email, tên khách, query nguyên văn của reviewer và nội dung từ run riêng không được truyền ra ngoài. Cache theo phạm vi truy cập, license, ngày hết hạn và ngôn ngữ; quota dùng chung theo host, run và nguồn. Không đăng nhập cộng đồng cá nhân, gửi bài hoặc gọi dịch vụ trả phí mặc định. Khi quyền sử dụng không rõ, ghi thiếu nguồn và chuyển owner xác minh.

Mỗi observation bất biến có `source_id`, publisher, URL canonical và URL truy xuất, retrieved_at UTC, published_at/effective_until nếu biết, phiên bản, locale/jurisdiction, tiêu đề, trích đoạn tối thiểu kèm locator, SHA-256 nội dung và trích đoạn, adapter/version, license/retention, nhãn chất lượng, lý do phân loại và evidence dây chuyền. Chất lượng đánh giá theo authority cho **câu hỏi cụ thể**, độ mới, phương pháp và khả năng kiểm chứng. Ví dụ, bảng giá của đối thủ có quyền mô tả giá họ niêm yết. Một review công khai tạo giả thuyết về trải nghiệm. Reviewer phải xác minh tỷ lệ chuyển đổi bằng dữ liệu có mẫu số phù hợp.

Đóng băng source digest tại lúc cấp context, kể cả khi TTL hết giữa run. Nếu nguồn bị rút hoặc sửa, phát event invalidation tới mọi finding phụ thuộc qua reverse index. Mở disposition mới sau khi verifier tìm căn cứ thay thế. Khi chưa đủ căn cứ, chuyển finding sang unresolved, giữ nguyên lịch sử và thông báo vào báo cáo sửa đổi. Trích dẫn và trang web luôn là dữ liệu chưa tin cậy. Broker lọc nội dung theo policy, ghi nguồn cho excerpt và từ chối hành động phát sinh từ chỉ dẫn trong tài liệu.

## B6 · Nhận PR, phản biện và bàn giao

| Chuyển trạng thái | Điều kiện và hành động bền vững |
|---|---|
| Received → admitted | Ingress kiểm HMAC SHA-256 trên bytes gốc bằng bí mật webhook, so sánh constant-time trước parse. Kiểm installation, repository ID và danh sách event/action cho phép. Ghi inbox duy nhất theo installation + delivery ID và payload digest rồi mới ACK. Khác digest cùng ID bị cách ly. [GitHub về chữ ký](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) |
| Admitted → current | Với PR mở/mở lại/đồng bộ/đổi base, đọc PR metadata bằng GitHub App read-only. Xác nhận trạng thái và base/head đầy đủ. Push trên nhánh có PR chỉ đánh thức bước reconcile. Trong cùng generation, gộp các delivery về cùng repo + PR + base + head + policy digest. Khi current head đã đổi rồi quay về SHA trước, tạo generation mới. Tái kiểm PR đang mở sau mất sự kiện. [Sự kiện và delivery headers](https://docs.github.com/en/webhooks/webhook-events-and-payloads) |
| Current → dispatched | Giữ khóa theo PR, tăng generation và trỏ current run tới đúng cặp SHA bằng giao dịch. Supersede run cũ, đóng admission, thu hồi lease; receipt đến muộn chỉ đối soát usage. Event đến sai thứ tự không được lùi head. |
| Dispatched → reviewed | Planner chọn reviewer theo nghĩa vụ và rủi ro. Ghi lý do, ngân sách, deadline và khoảng trống. Broker cấp packet riêng. Chờ blind seal rồi exchange, kiểm chứng, phân xử, lưu dissent theo [hợp đồng](CONTRACTS.md). |
| Reviewed → assigned | Đối chiếu lại current generation và cặp SHA. Tách verified findings thành draft package chứa ID, affected scope, proof, expected/actual, ưu tiên, tiêu chí chấp nhận, fixture và trách nhiệm. Journal lưu content digest, decision và gaps. |
| Assigned → handoff acknowledged | Adapter handoff có allowlist repo/branch, recipient capability, policy version và approval còn hạn của chủ repo. Ghi outbox và idempotency key theo run + package digest + recipient. Bên nhận ACK cùng key; sau crash hoặc ACK không rõ kiểm receipt trước retry. Chưa cấu hình quyền tích hợp Codex thì xuất file local và đặt trạng thái awaiting authorized handoff. |
| New head → re-review | Khi Codex push, GitHub gửi event mới. Liên kết parent run và finding IDs. Truy ngược bằng chứng và hồi quy bị ảnh hưởng trước khi đóng finding. SHA mới bắt buộc có run mới. |
| Closed / exhausted → terminal | PR đóng, bị rút, hết hạn, chạm trần tiền/token hoặc thiếu đối chứng thì dừng và ghi gap/owner. Kết quả incomplete ở báo cáo mang trạng thái inconclusive. |

Mặc định đề xuất tối đa **2 vòng sửa** sau run đầu, 2 vòng debate/run, 1 retry có thể đối soát/attempt, deadline 45 phút/run targeted và deadline cả chuỗi do owner cấp lúc nhận PR. Ràng buộc đồng thời ngân sách chung của chuỗi và policy từng run. Không cấp lại 88.000 token cho mỗi lần push nếu trần chuỗi đã hết. Dừng sớm khi cùng finding, cùng căn cứ và cùng hướng sửa lặp lại hai lần, thiếu căn cứ mới hoặc còn bất đồng business có ảnh hưởng. Gói escalation tới đúng owner gồm SHA, blocker, quan sát cần bổ sung, ngân sách còn lại và mốc chờ quyết định. Tác vụ merge/deploy, chi phí trả ngoài và publication Marketing nằm ngoài capability của reporter và handoff adapter.

## Điều kiện nghiệm thu tích hợp

- **B5.1** Ba reviewer cùng yêu cầu tài liệu công khai nhận một lần truy xuất trong TTL. Mỗi người chỉ đọc excerpt có quyền và lịch sử đọc không lộ nội dung blind của người khác.
- **B5.2** Fixture community có thông tin nhận dạng và câu yêu cầu nhúng được xử lý theo redaction. Kiểm log request outbound trên mock server để chứng minh chỉ topic công khai rời broker.
- **B5.3** Hai thị trường có ngày hiệu lực khác nhau nhận artifact tương ứng. Nguồn 404/hết quyền, trả nội dung khác digest hoặc bị rút dẫn đến gap/reverification có lịch sử.
- **B6.1** Chữ ký sai, sai repo, quá kích thước và event ngoài allowlist sinh 0 assignment. Redelivery, push + PR event cùng SHA và restart sau ACK vẫn tạo tối đa 1 run hợp lệ.
- **B6.2** Mô phỏng A → B → A với generation riêng. Kết quả từ lần A cũ không phát handoff. Nếu cùng cặp SHA tái xuất, reuse artifact theo policy phải kèm generation mới và audit quyết định.
- **B6.3** Hủy trong dispatch rồi nhận output, giao việc xong nhưng mất ACK, webhook đến đảo thứ tự và PR bị đóng đều có phép đối soát cụ thể. Ledger vẫn giữ usage chưa xác nhận.
- **B6.4** Hết token, tiền, thời gian hoặc số vòng trước đủ coverage sinh inconclusive; bất đồng trọng yếu có owner. Kiểm chứng theo kết quả quan sát được của fixture.
- **B6.5** Trên repo dev riêng có owner cấp quyền, một change vô hại đi từ PR đến package và ACK của implementer. Mọi ID từ delivery tới receipt và package tái dựng được từ journal.

Trình tự giao việc engineering là mock fetcher + cache và invalidation; sau đó ingress/outbox ở chế độ quan sát; cuối cùng thử handoff vào repo dev có ủy quyền. Có thể rollback từng adapter bằng cách ngừng consumer, đóng admission tương ứng, giữ journal để đối soát. Product runtime AMC tiếp tục dùng quá trình cấp quyền và ngân sách riêng.
