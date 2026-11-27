# AMC-RES-QA-01 · Quyết định cho kế hoạch nghiên cứu nội bộ

**Candidate cho Independent Review.** Marketing Researcher soạn câu hỏi; người có ủy quyền xem đúng câu, chọn mandate và ghi lý do trong mục **Đối chiếu nội dung với bằng chứng**. Quyết định cho phép tiếp tục duyệt phần Research của lần lưu đó. Chưa ghi nhận lần phỏng vấn, bằng chứng mới, chiến lược đã duyệt, quyền liên hệ khách hàng hay lệnh soạn Content.

## Chứng nhận main sau PR #67

| Đối tượng | SHA |
|---|---|
| Base / parent 1 | `9cf1380361efe03d6de4455f9f0313aa32a8db80` |
| Code RS-02 đã test | `578069a82696f2cd7279cf0ad5ddeb0c89f8d611` |
| Approved head / parent 2 | `e4f03cecc2c3315830f59a20258532bb3cc60ab9` |
| Trial đã duyệt | `036dd9eebacc8474263e81e83949de8da9726e16` |
| Merge #67 / base của candidate này | `fe0110bd2fa524619c527420478edb9f7b94a0b6` |
| Tree chung của head, trial và merge | `ac200a697a4b24c42c9ab1ab2b793fd83b34c5df` |

Main, head, trial và policy được đọc lại trước merge. Diff của #67 gồm 13 tệp tài liệu, fixture, test và bằng chứng; ba tệp cuối là manifest, JUnit và receipt. CI trên chính merge SHA không chạy. RS-01 giữ kết quả âm, RS-02 chỉ chấp nhận nội bộ. [Merge #67](https://github.com/datnv41001/ai-company/commit/fe0110bd2fa524619c527420478edb9f7b94a0b6)

## AMC-R67-01 · Phân loại thủ tục và xác minh claim

1. **RED** ở baseline. Edit câu hỏi giao ca trong RS-02, submit, đọc lại cả hai span unresolved. Research signature trả 409, recipient không có work order. Test RED gốc còn nguyên và tiếp tục kiểm đường không có quyết định.
2. **GREEN** ở candidate. Mỗi span chỉ có thể trình theo danh mục câu nguyên văn VI/EN của hợp đồng `amc.research-instruction/1`. Câu hỏi về khay giao ca còn phải khớp sản phẩm và mục đích của brief. Danh mục hữu hạn là giới hạn sản phẩm có chủ đích: câu trung lập ngoài danh mục vẫn có thể bị giữ. Phiên bản sau cần ví dụ phản chứng và review để bổ sung cách diễn đạt.
3. API yêu cầu commission Research nội bộ, bản submitted, reviewer khác tác giả/người sửa, mandate đang hiệu lực, target và source còn quyền. Quyết định lưu exact text, offset, statement ID, document, revision, digest, manifest, scope, reviewer và mandate. Đọc lại cho kết quả editorial, không gắn source handle. Hai POST đồng thời giống nhau trả cùng quyết định; lý do khác trên cùng span của cùng reviewer bị từ chối.
4. Từng câu lân cận tiếp tục được kiểm riêng. Claim nằm trong câu hỏi, lời hứa giá/MOQ/giao hàng, private locator, thiếu qualifier, sửa cùng nội dung qua revision mới, sai tenant và dùng mandate/statement của tài sản khác có đối chứng. Quyết định Research không dùng được trong client preview hay làm quan sát bằng chứng cho handoff. Khi nguồn hoặc mandate bị thu hồi, việc đánh giá hiện tại trở lại unresolved. Lịch sử vẫn lưu quyết định gốc. [Ca API/PostgreSQL](../../../tests/test_research_instruction.py) · [Ca RED gốc](../../../tests/test_rs02_contract_alignment.py)

**Tương thích và rollback.** Dùng KnowledgeCommand và hàng rào PostgreSQL cho `c3_resolve`, phân biệt key `instruction-v1:` với key claim lịch sử. Reader cũ chỉ dùng key claim; receipt cũ vẫn được đọc theo logic xác minh nguồn cũ. Không đổi schema 26, digest adapter, role hoặc danh sách adapter được duyệt. Lock runtime chỉ bổ sung hai identity mới cho source bundle thay đổi. Có thể rollback code bằng revert candidate; giữ các command bất biến, đưa bản cần phân loại về trạng thái chờ. Khi rollout, khởi động lại API nhất quán để tránh replica cũ hiển thị trạng thái tạm giữ.

Trong lượt phát triển đầu, migration từ chối source bundle chưa đăng ký. Hai fingerprint mới kế thừa nguyên danh sách adapter của đúng baseline và dependency set. Lượt API kế tiếp cho thấy “gần nhất” trong câu hỏi về lần mua trước bị xếp vào comparison. Chỉ câu nguyên văn đã rà soát mới được trình reviewer có mandate phân loại; bộ xử lý claim so sánh vẫn áp dụng cho văn bản khác. Receipt cuối của người duyệt ghi mục `internal_research_instructions` riêng với `reviewed_statements`.

## AMC-R67-02 · Lời hứa giao nhanh

Brief RFQ và manifest được tạo qua API. Worker nhận việc và nộp câu trả lời có kiểm soát qua dispatcher/worker PostgreSQL; Strategy Studio thực sự nhận lời hứa đó. Nguồn tổng hợp quy định hàng giao dạng tháo rời, form nhận khung giờ/ghi chú tiếp cận, carrier phải xác nhận bằng văn bản và bốc dỡ bị loại trừ. Hai cách viết đi qua cùng quy trình.

| Điểm kiểm | “ensures quick delivery to the requested site window” | “guarantees rapid arrival” |
|---|---|---|
| Structural QA, nhóm Strategy | Không cảnh báo | Không cảnh báo |
| Content evidence | Contradiction, rule về địa bàn khớp “delivery to” | Unresolved, thiếu căn cứ |
| Phân loại procedural / dùng nguồn không đủ | 409 | 409 |
| Ký riêng Strategy / duyệt toàn tài sản | 409 / 409 | 409 / 409 |
| Preview và recipient | Không chứa lời hứa; không có work order | Không chứa lời hứa; không có work order |

Ca thứ hai tách lỗi thiếu bằng chứng khỏi tín hiệu địa bàn của ca thứ nhất. Không tăng quyền, không đổi gate Delivery. Xem [receipt ca khung giờ](delivery.json) và [receipt ca tốc độ](delivery-speed.json) để đối chiếu từ facts tới attempt, nguyên văn, span và signature.

## Nghiên cứu D/A/C tiếp theo · PROPOSED

Một output phát triển tổng hợp biểu đạt H1/H2 trong buyer_problem, câu hỏi phân biệt trong research_question, cách lấy bằng chứng và quy tắc đổi hướng/giữ việc trong evidence_needed. Độ dài trường là 43–185 ký tự, dưới giới hạn 200. JSON gọn dùng 101 token theo tokenizer của GGUF đã ghim, còn 119 trước cap 220. Message bodies mẫu dùng 621 token ở A và 637 ở C. Đây chưa phải preflight của chat template cho cả 12 brief; phải kiểm cả template, schema, Director, Strategy, context và reserved output trước khi khóa. Không phát sinh generation từ phép đếm. [Fixture phát triển](development.json) · [Số đo](headroom.json)

Studio hiển thị câu hỏi và buyer_problem; evidence_needed cùng switch/hold chỉ giữ ở staff research notes. **Artifact để chấm assembled** phải gồm bản Studio theo revision và phần research_notes.fields của đúng Workforce run/manifest mà editor có quyền đọc. Lấy từ API run report / marketing_artifacts.sections, kiểm cùng document và revision, ký hash hai phần. Không đưa ghi chú riêng vào preview, work order hay phiếu của người không có quyền. Trước pre-registration cần reviewer chấp thuận thay đổi thiết kế gói chấm này và thử quyền trên cả ba nhánh; D ghi rõ không có worker notes. Dùng cùng composition ở A/C và giữ bản điểm Studio-only để thấy phần nào được notes cứu. Giữ bí mật cohort và scoring key.

Giữ 12 brief mới, ba nhánh D/A/C, thứ tự AC/CA 6/6, trái/phải 6/6 từng cặp và đối cân thứ tự raw/assembled. D không inference. Đo riêng thời gian rater đọc/chấm với thời gian editor chỉnh từ lúc mở đến bản có thể dùng. Chưa có custodian hoặc hai evaluator độc lập được bổ nhiệm. Trước khi mở cohort, Product Owner cần chỉ định một custodian giữ khóa, một evaluator Research và một evaluator Strategy; cả hai độc lập với người tạo fixture/treatment và khóa phiếu riêng. Giữ đề xuất 72 lượt, tối đa 108.000 token vào, 15.840 token ra, 60 phút, concurrency 1, không retry; hai editor tối đa 4 giờ/người và 1 giờ phân xử, thời gian chấm riêng chưa có dự toán được duyệt. Không đổi schema hoặc cap. [Protocol nguồn](../rs02/NEXT-PROTOCOL.md)

## Tái hiện và thách thức reviewer

JUnit local ghi 29/29 ca mục tiêu đạt trong 81,99 giây, gồm 20 ca mới, 8 hồi quy RS-02 và một bài Chromium trên ba kích thước, hai theme. Lượt trước các thao tác giao diện hoàn tất nhưng fixture Windows báo lỗi đóng máy chủ; bài browser hiện chờ request kết thúc và rời ứng dụng trước khi đóng trang. Đợt chạy lại đạt cả teardown. [JUnit local](junit-local.xml) · [Danh mục blob SHA-256](MANIFEST.json)

Dùng môi trường dev cách ly theo workflow CI và bật `AMC_TEST_PG=1`. Chạy `python -m pytest -q tests/test_research_instruction.py tests/test_rs02_contract_alignment.py`, sau đó `python -m pytest -q tests/browser_research_instruction.py` với Chromium và full regression `python -m pytest -q`. Biến `AMC_RES_QA_EVIDENCE` xuất JSON tổng hợp; `AMC_RES_QA_SCREENS` xuất ảnh light/dark cùng DOM ở 1280/820/390 px. Chạy `python tests/evaluation/research_instruction_budget.py --tokenizer PATH_TO_LLAMA_TOKENIZE --gguf PATH_TO_APPROVED_GGUF` để đếm token không inference. [DOM, thời gian mở form và overflow](screens/dom.json) · [Receipt EN](en-US.json) · [Receipt VI](vi-VN.json)

Reviewer hãy thử tái sử dụng receipt trên revision kế tiếp có cùng nội dung, ghép một claim ngay sát câu trung lập và đối chiếu quyền đọc ở recipient sau thu hồi. Hai vai trò chưa có bằng chứng nghiệp vụ độc lập là Marketing Researcher và người biên tập Strategy. Chưa có số liệu giảm công, thời gian thị trường hay chi phí vận hành đầy đủ. Production và Commercial GA vẫn NO-GO.
