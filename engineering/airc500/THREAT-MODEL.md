# Threat model cho hội đồng engineering

**Tài sản cần bảo vệ** gồm mã chưa phát hành, thông tin trong snapshot, khóa ký adapter, nhãn chấm mù, output trước trao đổi, sổ chi phí và quyền quyết định release. Các ranh giới tin cậy tách importer, planner, sandbox, model adapter, verifier và người duyệt. Mọi input từ PR, model hoặc tài liệu nghiên cứu đều là dữ liệu chưa tin cậy.

| Tình huống | Kiểm soát phải nằm ngoài prompt | Bằng chứng nghiệm thu |
|---|---|---|
| Nội dung PR yêu cầu reviewer cấp thêm quyền hoặc gửi dữ liệu | Broker chỉ cấp handle đọc theo manifest; chính sách ngoài model, network deny; nghiên cứu bằng snapshot allowlist | Fixture chứa chỉ dẫn vô hại đi ngược policy; grant và audit egress giữ nguyên |
| Source bundle chứa dữ liệu khách, token hoặc path trỏ ra ngoài | Import theo Git object; từ chối symlink/submodule chưa khai báo, binary ngoài allowlist, log chưa scrub; chỉ fixture tổng hợp | Dummy marker bị loại trước khi tạo bundle; inventory chỉ có object cho phép |
| Lộ dữ liệu giữa hai khách hoặc hai run | Namespace theo repo/run/scope/assignment, object ACL cả lúc resolve; hạn chế cache và content indexing | Cặp khách A/B cùng agency nhận đúng tập fixture, artifact run cũ không được cấp |
| Reviewer sửa code, tự duyệt hoặc cùng phiên làm cả hai vai | Tách principal implementer/adapter/reviewer/verifier, source read-only, checkout credentials vắng mặt; cấm tác giả làm referee cho claim mình viết | Ma trận principal x action; thử các yêu cầu thao tác qua policy stub với dữ liệu tổng hợp |
| Lộ câu trả lời của peer hoặc answer key trước blind seal | Store tách namespace, không dùng shared chat, event ACL và log cắt lượt đọc; coordinator thực thi barrier | Audit manifest input của hai peer; packet trước seal bị từ chối |
| Model bịa invocation, citation hoặc test log | Receipt do adapter tin cậy ký, attestation từ runner khác; đối chiếu hash, source và scope | Receipt tự khai, marker thiếu hoặc locator sai SHA bị quarantine; số participation không tăng |
| Evidence đúng từ commit trước bị dùng lại | Run gắn hai SHA, integration riêng, source và catalog digest; head đổi tạo run mới | Đổi head với cùng nội dung fixture; quyết định cũ vẫn truy xuất riêng |
| Bỏ qua thiểu số vì đa số cùng model | Lưu family/checkpoint, yêu cầu counterevidence, arbitration giữ dissent; tỷ lệ đồng ý không là release gate | Một claim đúng có chứng cứ đối đầu nhiều claim yếu dẫn tới disposition theo chứng cứ |
| Thất thoát budget qua retry hoặc deadline | Trần cứng hai chiều, reserve trước dispatch, lease fencing, timeout và đối soát uncertain | Test hai worker cùng tranh slot cuối, cancel rồi nhận receipt trễ |
| Sandbox hoặc artifact gây tác dụng ngoài phạm vi | Test service dùng image đã ký/pin và ca allowlist; scratch có quota, source chỉ đọc, không mount socket/keys; không chạy lệnh PR tự cung cấp | Kiểm manifest image, quyền mount, egress và quota trên fixture |
| Kho research thiếu căn cứ, nguồn cũ hoặc không đúng thẩm quyền | Giới hạn publisher/purpose, pin digest/ngày/khu vực; đoạn trích đi với provenance; yêu cầu người phụ trách khi thiếu | Nguồn không ngày hoặc ngoài phạm vi được đánh insufficient, legal chuyển counsel |
| Dữ liệu journal bị sửa hoặc phát lại | Khóa ký nằm ngoài worker, trust root pin, hash chain và backup checksum tách quyền | Đổi một byte fixture, duplicate attempt, key hết hiệu lực; verifier ghi lý do từ chối |
| Báo cáo bị dùng để tự merge, deploy, trả phí hoặc gửi thông điệp | Reporter chỉ tạo artifact engineering; không có gateway ra các tác vụ trên. Phê duyệt ngân sách và release là quyền riêng | Kiểm inventory capability của mọi reviewer và mặt ghi của reporter |

Run đầy đủ có thể khuếch đại sai lệch của một checkpoint hoặc một nguồn dữ liệu dù mọi receipt hợp lệ. Evaluation owner công bố model families thực tế và dùng holdout. Engineering owner chịu trách nhiệm admin/key compromise, snapshot sanitization và kiểm tra phục hồi. Chủ dữ liệu quyết định retention, phạm vi nghiên cứu và nguồn được phép. Khi thiếu signer đáng tin hoặc nguồn ground truth, trạng thái tương ứng là **unverified/inconclusive**.
