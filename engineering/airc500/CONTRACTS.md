# Hợp đồng thực thi v1

[JSON Schema 2020-12](contracts.schema.json) mô tả hình dạng tám bản ghi trao đổi. Các invariant liên bản ghi và quyền dưới đây là điều kiện bắt buộc khi triển khai dịch vụ. Schema một record không xác thực chữ ký, quyền truy cập hoặc việc model đã chạy.

## Định danh và lưu bằng chứng

- Run gắn với repo được duyệt, số PR, base/head SHA 40 hex đầy đủ, merge base, catalog/policy/source/dependency digest. Importer xác minh Git objects thực, kể cả source base cho dòng đã xóa. Bản integration nếu có được lưu bằng SHA riêng. Phát hiện head thay đổi thì kết thúc run với lý do superseded và lập run mới; lịch sử vẫn truy xuất theo run cũ.
- Mỗi assignment thuộc một run, reviewer, principal, phase, round, capability grant và context digest. Chính coordinator cấp ID. Cấm principal/session đã viết patch nhận vai reviewer của patch đó. Tách credential, storage và lịch sử ngữ cảnh của hai bên; ghi nhóm model/family trùng nhau khi không đủ đa dạng. Người hoặc model tự khai vai trò không cấp được quyền.
- Hash blob trên byte gốc. Adapter pin artifact và metadata thực thi từ môi trường local do operator sở hữu. Model không truy cập khóa ký hoặc journal. Định dạng chữ ký và quy tắc xác minh nằm ở phần triển khai pilot bên dưới.
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


## Pilot local · receipt và checkpoint thực thi được

Các entry point được kiểm thử là `Signer.sign`, `verify_signature`, `Journal.ingest`, `Journal.checkpoint` và `Journal.recover`. Cài thư viện từ `requirements-pilot.txt`. Unit test dùng dữ liệu giả có nhãn test. Chúng kiểm cơ chế ký thật; không tính là một lượt inference.

**Chữ ký.** Định dạng `receipt.v1` yêu cầu trường `signature` là object chứa đúng `key_id`, `algorithm="Ed25519"`, `signature_version=1`, `value` (64 byte chữ ký, base64 chuẩn có padding). `key_id` là SHA-256 hex của 32 byte public key Ed25519 dạng raw. Protected header gồm ba trường đầu. Message ký là tiền tố byte ASCII `AMC-AIRC-RECEIPT` tiếp theo byte NUL, rồi RFC 8785 UTF-8 của object gồm `header` (protected header) và `payload` (tất cả trường receipt ngoại trừ `signature`). Cả thuật toán lẫn phiên bản phải khớp allowlist. Các ID bao gồm model GGUF digest, adapter identity, model/version/family, run/base/head, assignment, reviewer, phase/round, attempt, lease epoch, giờ dispatch, context hash và output hash. Verifier luôn hash lại output từ byte gốc.

**Gốc tin cậy.** Operator cấp public trust map cho coordinator trước khi start. Map gắn một fingerprint với public key, adapter, model/version/family và model digest; có thể thu hẹp thêm bằng `not_before`/`not_after`. Trust theo run là bất biến, deadline/lease được kiểm riêng khi chấp nhận. Private key chỉ ở adapter. Khi chuyển máy, lấy fingerprint qua kênh operator hoặc commit đã review rồi đối chiếu. Public key nằm trong cùng bundle với chứng cứ không tự xác nhận ai đã cấp quyền cho adapter. Verifier giải attempt từ sự kiện reserve duy nhất, đọc model binding trong trust map khởi tạo và gắn với thời điểm dispatch thật. Signed receipt thiếu dispatch, sai SHA, sai key, sai lease/bundle, sai model hoặc sai output bị từ chối. Việc ký chứng minh nguồn gốc kết quả; phán quyết đúng/sai vẫn cần verifier nghiệp vụ.

**Journal.** Một file SQLite riêng cho engineering, chế độ WAL, synchronous FULL và BEGIN IMMEDIATE cho mỗi lệnh. Bản ghi start chốt manifest/trust/deadline; reserved chốt assignment, hạn lease, run epoch, attempt epoch và hai reservation. Lệnh dispatched commit trước khi adapter gọi model. Mỗi event có số thứ tự và SHA-256 của RFC 8785 trên `[run_id,seq,kind,data,parent_hash]`. Coordinator đọc lại chuỗi trước mỗi mutation. Checkpoint chỉ rõ sequence, parent/event root, deadline, epoch, khoản đang giữ gồm attempt/lease/hạn/token/tiền, hash của danh sách này, blind seal và trạng thái cancel. Khi phục hồi từ backup, truyền checkpoint đã lưu riêng: `recover(run_id, checkpoint)` đối chiếu toàn bộ projection tại sequence đó, kiểm tiếp journal tail rồi fence attempt còn mở. Operator phải dừng coordinator cũ trước recovery. Sao lưu bằng SQLite backup API hoặc dừng process và checkpoint WAL trước khi copy. Giữ bản checkpoint tin cậy ngoài file DB nếu cần phát hiện cắt mất phần cuối. So sánh checksum khi restore; file SQLite đang hoạt động có thể cần WAL đi kèm.

| Tình huống tại transaction boundary | Xử lý và quan sát |
|---|---|
| Crash/cancel trước dispatch | Lease mất hiệu lực; reservation giải phóng. Retry cấp attempt và lease epoch mới nếu còn quota. |
| Crash/timeout/cancel sau dispatch | Fenced, exposure giữ ở uncertain. Chưa có receipt đáng tin thì không chạy lại assignment đó. |
| Signed usage đến sau cancel/timeout | Đối chiếu lease cũ và raw bytes, settle ledger một lần. Không cấp accepted output hoặc sửa blind seal. |
| Receipt unknown rồi có usage thật | Chỉ cho đối soát lại đúng key, attempt và execution ID. Trạng thái đã fenced vẫn ledger-only. |
| Gửi trùng receipt | Cùng byte và output đúng là no-op; receipt khác cho một khoản đã đối soát bị từ chối. Trùng execution ID trên hai attempt cùng key cũng bị từ chối. |
| Hết ngân sách / thiếu coverage | Admission từ chối vượt trần, `coverage` trả inconclusive. Số tiền API có thể là 0 trong khi token chưa đối soát còn dương. |
| Kết quả vượt reservation | Giữ usage thực đã đối soát, đánh dấu over-budget, chặn lease mới và không nhận output đó. |
| Crash giữa hai lần đọc checkpoint | Replay prefix đã tin cậy + tail trong transaction; thu hồi lease của coordinator cũ, không tái mở seal hoặc dispatch trùng. |

Giai đoạn pilot dùng một journal local cho toàn host, tối đa hai slot, cap phí API bằng 0. Retry tối đa một lần và vòng tranh luận tối đa hai theo manifest/schema. Số dispatch bền vững có thể lớn hơn số inference có chứng cứ nếu crash sát ranh giới gọi model. Báo cáo tách accepted receipts, telemetry có execution ID và exposure chưa rõ. Lệnh `python -m unittest discover -s engineering/airc500 -p test_journal.py -v` kiểm chữ ký, ràng buộc identity/revision, retry, cancel, concurrent admission và phục hồi.

Để bàn giao qua máy khác, `export_events(run_id)` xuất journal thứ tự sequence dưới dạng JSON. `Journal.verify_events(run_id, events, checkpoint, trust)` tái dựng hạn mức, lease, dispatch, blind seal, cancellation, số ID tham gia và token đã đối soát, đồng thời kiểm từng chữ ký và hash của raw output. Phải pin digest của gói hoặc checkpoint từ commit/kênh engineering đã duyệt để phát hiện việc cắt mất phần đuôi journal hoặc thay thế toàn bộ manifest. Không đưa private key hay database AMC vào gói.
