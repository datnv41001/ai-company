# Hợp đồng thực thi v1

[JSON Schema 2020-12](contracts.schema.json) mô tả hình dạng tám bản ghi trao đổi. Các invariant liên bản ghi và quyền dưới đây là điều kiện bắt buộc khi triển khai dịch vụ. Schema một record không xác thực chữ ký, quyền truy cập hoặc việc model đã chạy.

## Định danh và lưu bằng chứng

- Run gắn với repo được duyệt, số PR, base/head SHA 40 hex đầy đủ, merge base, catalog/policy/source/dependency digest. Importer xác minh Git objects thực, kể cả source base cho dòng đã xóa. Bản integration nếu có được lưu bằng SHA riêng. Phát hiện head thay đổi thì kết thúc run với lý do superseded và lập run mới; lịch sử vẫn truy xuất theo run cũ.
- Mỗi assignment thuộc một run, reviewer, principal, phase, round, capability grant và context digest. Chính coordinator cấp ID. Cấm principal/session đã viết patch nhận vai reviewer của patch đó. Tách credential, storage và lịch sử ngữ cảnh của hai bên; ghi nhóm model/family trùng nhau khi không đủ đa dạng. Người hoặc model tự khai vai trò không cấp được quyền.
- Hash blob trên byte gốc. JSON record ký theo RFC 8785, UTF-8; từ chối duplicate keys, số không hữu hạn và bản ghi vượt quota. Mọi số tiền là số nguyên micro-USD. Adapter ký envelope bằng khóa engineering riêng trên canonical bytes của receipt bỏ trường `signature`. Chữ ký mang key ID và phiên bản thuật toán. Verifier kiểm signer tin cậy, key hiệu lực tại thời điểm gọi, danh tính adapter, context và output bytes. Một output thiếu receipt được cách ly.
- Journal append-only có sequence và digest trước đó. CAS chỉ ghi blob mới theo hash. Kết quả cũ, ý kiến trước phản biện và nhãn fixture gốc được giữ bằng digest. Phân loại lưu trữ, ACL và thời hạn do engineering owner đặt trước khi chạy. Giữ chuỗi digest và lý do tombstone khi xóa nội dung theo retention.

## Một run đi qua 12 bước

| Bước | Đầu ra và điều kiện chuyển tiếp |
|---|---|
| 1. Tiếp nhận | Importer xác minh PR → immutable run manifest, bao gồm danh tính implementer. |
| 2. Phân tích phạm vi | Diff hai phía + dependency graph → bản đồ nghĩa vụ, miền bị ảnh hưởng, khoảng trống và risk. |
| 3. Chọn người | Planner lưu selection/omission kèm lý do; admission kiểm tra family, quyền, ngân sách và giới hạn chạy. |
| 4. Đóng context | Broker cấp bundle riêng gồm nhiệm vụ, rubric, evidence allowlist, ngân sách và source digest. |
| 5. Đánh giá mù | Worker quan sát bundle; gửi finding hoặc review rỗng có nêu coverage. Không dùng chung hội thoại, memory, cache có nội dung hay output của peer. |
| 6. Niêm phong | Sau deadline hoặc khi mọi assignment mù terminal, đóng danh sách output và receipt bằng một barrier digest. Timeout/cancel hiện là gap. Không công bố bản ghi thiếu cho reviewer khác. |
| 7. Trao đổi | Coordinator route finding theo cùng invariant, dependency hoặc business impact. Chỉ phát excerpt tối thiểu sau seal, ẩn ID tác giả khi có thể. |
| 8. Phản biện | Reviewer khác chủ thể gốc đối chiếu biến thể fixture, nguồn trái chiều hoặc consumer contract. Ghi yêu cầu bổ sung, phản đối và phương án sửa vào exchange. |
| 9. Xác minh và gộp | Verifier giải tham chiếu đúng SHA, kiểm provenance, test attestation và căn cứ. Cụm duplicate giữ ID gốc và mọi nguồn. |
| 10. Phân xử | Giao trọng tài độc lập với tác giả, người phản biện và implementer. Lưu lập luận thiểu số, quan sát cần thêm và người xử lý. |
| 11. Báo cáo | Reporter tính số tham gia từ receipt + artifact hợp lệ, độ phủ và quyết định theo bằng chứng. |
| 12. Bàn giao | Sinh draft đầu việc có owner theo vai trò, criterion, fixture hồi quy và SHA cần tái kiểm. Người có thẩm quyền duyệt việc sửa hoặc phát hành. |

Trạng thái run: `planned → admitted → blind → sealed → cross → verify → arbitrate → reported`. Có thể từ verify đi thẳng reported nếu hết tranh chấp và không yêu cầu full-mode arbitration. Nhánh hủy/superseded/over-budget/timeout kết thúc bằng báo cáo incomplete, liệt kê cả phần đã quan sát. Job retry có attempt ID mới với cùng assignment ID. Lease fencing ngăn worker trễ ghi đè kết quả hiện hành.

## Quy tắc verifier

| Bản ghi | Quy tắc ngoài schema |
|---|---|
| `run.v1` | Kiểm SHA trên đúng repo; rủi ro và số người đủ nghĩa vụ; default paid=0; từ chối mode full nếu không đủ chỗ cho 490 chuyên viên và 10 trọng tài. |
| `assignment.v1` | Reviewer ID có trong catalog đã pin; phase phù hợp; capability là tập con; loại xung đột tác giả và chính reviewer khi làm cross/arbitration. |
| `receipt.v1` | Attempt ID duy nhất và gắn assignment; start ≤ end; input/context, run/reviewer/SHA và phase đều khớp. Completed cần output digest + usage đã đối soát, số token/tiền không âm; failed/unknown vẫn có thể phát sinh phí. Cấm suy số token từ độ dài văn bản để lập receipt thật. |
| `review.v1` | Kiểm artifact_kind và proof obligation trong catalog. Accepted submission cần completed receipt ký hợp lệ và output bytes khớp. Output review gồm report và danh sách finding trong cùng payload có digest; artifact_kind là bằng chứng đúng chuyên môn. Review rỗng hợp lệ nếu nêu phần đã đọc và giới hạn. |
| `finding.v1` | Ingest lấy model/version, reviewer, attempt, run và SHA từ receipt; sai một trường thì quarantine. ID trong scope run. Dòng 1-based nằm trong đúng blob, end ≥ start; finding phi mã ghi location=null và lý do. Reproduction có thể null khi kiểm bằng nguồn tài liệu. Bắt buộc có expected, actual, business impact, evidence, proposed fix, acceptance, verification, counterarguments và dissent. |
| `exchange.v1` | Chỉ sau barrier và trong round 1..cap. Người khác có assignment phù hợp. Mỗi request nêu evidence còn thiếu; ý kiến mới nối sự kiện, có thể supersede, không sửa bản ban đầu. |
| `arbitration.v1` | Reviewer thuộc AR và không xung đột; phải giải thích vì sao evidence quyết định được/không quyết định được vấn đề, lưu dissent. Hồ sơ release toàn cục không có finding dùng danh sách ID rỗng và disposition theo độ phủ. |
| `checkpoint.v1` | Sequence/previous digest đơn điệu, xác minh root của journal và ledger, blind seal và cancellation. Khôi phục khóa bằng compare-and-swap trên sequence mới nhất. |

**Payload model và gốc tin cậy.** Model gửi nội dung quan sát và locator trong schema đầu ra của assignment. Adapter đóng gói raw output cùng finding candidates, băm bytes, ghi receipt và chuyển cho ingest. Ingest sinh record dẫn xuất, giữ mapping từ raw output → candidate → verified/rejected. Model chỉ đề xuất severity/status. Chỉ verifier được quyết định trạng thái. Phiếu trao đổi và phiếu phân xử cũng cần receipt đúng attempt trước khi tính là hoạt động của reviewer AI.

**Bằng chứng chấp nhận được.** Pinned blob phải resolve đúng repo/SHA/path/side/lines. Sandbox attestation phải khớp fixture digest, runner, image, lệnh cho phép, expected và actual. Trích dẫn chính thức kèm publisher, version/date, retrieval digest và đoạn liên quan. URL không truy xuất được hoặc phản hồi của AI khác tự nó chỉ tạo yêu cầu bổ sung. Chỉ gọi là verified nếu căn cứ trực tiếp ủng hộ **expected lẫn actual** trên đúng phạm vi; nguồn gián tiếp có thể dẫn đến unresolved. Accepted receipt chứng minh lượt gọi, không chứng minh tính đúng của claim.

**Phân loại và duplicate.** P0 ảnh hưởng nghiêm trọng cần chặn ngay trong phạm vi review; P1 làm sai quyền, chi phí hoặc luồng chính; P2 làm giảm chất lượng có giới hạn; P3 vấn đề nhỏ có căn cứ; IDEA là cơ hội cần thẩm định. Khóa gợi ý cụm gồm invariant + component + nguyên nhân + SHA và side. Người xác minh so cả business effect và regression criterion trước khi gộp; lỗi khác tenant hoặc khác root cause có thể cần ca riêng. Giữ alias, đối chứng, ý kiến phản biện và lý do reject. Không chuyển IDEA thành lỗi vì nhiều người chọn.

**Kết luận.** Một chứng cứ trực tiếp có thể bác bỏ nhiều phiếu đồng thuận. Dùng `changes_requested` nếu có blocker đã kiểm; `inconclusive` nếu thiếu coverage bắt buộc, receipt hoặc bất đồng trọng yếu; `pass_internal_scope` khi các điều kiện bằng chứng đã đạt; `not_reviewed` khi chưa có run. Release gate thuộc chủ thể phát hành, commercial GA giữ NO-GO. Mọi assignment cho Codex chỉ là nội dung để người có quyền triển khai tiếp.
