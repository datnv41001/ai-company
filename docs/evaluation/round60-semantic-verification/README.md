# PR #60 · Independent Review

Base `4140563a89539acd19f1a7d5a16662c8dec5f6af` · head cũ `555b968c85b09d52d50d2fd165ea9ff320e5afcd` · head mới `edbca9483f59a20f8c3d1f54123a92e353cc3426` · trial `7a506789ca4183f59d9e6e0d2b9486a86d692879`. Hai cây head/trial cùng là `1c40c678b0556cfa512b0a5f59c4eef457c60ef6`.

Người duyệt có thể mở JSON ở từng hàng để đối chiếu hai checkpoint, câu chữ thực, các trường khóa, quyết định QA, journal và provenance. Mỗi lượt chạy dùng nguồn tổng hợp độc lập. Cột “đổi hook” là bản scoped editor đã nộp và người thứ hai đã duyệt. Biên nhận QA trong cột cũ cho thấy vì sao chỉ kiểm tra HTTP thành công đã bỏ sót lỗi.

[JUnit RED trên ứng dụng cũ](red-pinned/junit.xml) · [JUnit GREEN và hồi quy WF-08 trên checkout mới](green/junit.xml) · [So ảnh Chromium sau khi giải nén](ui/COMPARE.html) · [Diễn tập quay lại runtime cũ](rollback.json)

Ca chẩn đoán trên cây cũ cho thấy bốn tổ hợp appointment/choose_session × concise/formal đã thực sự được duyệt với câu mời báo giá. Ma trận cuối còn yêu cầu nhận ra hành động đích ngay trong câu mở của hai biến thể có kiểm soát; một câu chung chung cũng trượt điều kiện bổ sung đó. Tổng 15 lỗi trên 16 phép thử RED gồm các điều kiện khác nhau, không phải 15 trường hợp mời báo giá sai. [Lượt giữ nguyên cây cũ với tiêu chí ban đầu](red-final/junit.xml) · [Hash và nguồn phép thử cuối](red-pinned/source.json)

| Hành động | Văn phong | Hook gốc cũ | Đổi hook cũ | Hook gốc mới | Đổi hook mới | CTA mới | Hai hồ sơ |
|---|---|---|---|---|---|---|---|
| rfq | plain | Cần kiểm tra điều gì? | Hãy xem điều kiện trước. | Bạn cần báo giá gì? | Hỏi báo giá cần chuẩn bị gì? | Yêu cầu báo giá | [Cũ](red-pinned/outputs/rfq-plain.json) · [Mới](green/outputs/rfq-plain.json) |
| rfq | concise | Kiểm tra đâu trước? | Báo giá cần gì? | Cần báo giá? | Hỏi báo giá cần gì? | Yêu cầu báo giá | [Cũ](red-pinned/outputs/rfq-concise.json) · [Mới](green/outputs/rfq-concise.json) |
| rfq | formal | Quý vị cần đối chiếu gì? | Quý vị cần báo giá? | Quý vị cần báo giá? | Quý vị muốn hỏi báo giá nào? | Yêu cầu báo giá | [Cũ](red-pinned/outputs/rfq-formal.json) · [Mới](green/outputs/rfq-formal.json) |
| rfq | friendly | Mình cùng xem nhé? | Mình xem điều kiện nhé? | Mình cần báo giá gì nhỉ? | Mình xem gì trước khi hỏi báo giá? | Yêu cầu báo giá | [Cũ](red-pinned/outputs/rfq-friendly.json) · [Mới](green/outputs/rfq-friendly.json) |
| appointment | plain | Cần kiểm tra điều gì? | Hãy xem điều kiện trước. | Bạn muốn hẹn lúc nào? | Bạn cần biết gì trước khi hẹn? | Gửi đề nghị khảo sát | [Cũ](red-pinned/outputs/appointment-plain.json) · [Mới](green/outputs/appointment-plain.json) |
| appointment | concise | Kiểm tra đâu trước? | Báo giá cần gì? | Hẹn khi nào? | Cần gì trước khi hẹn? | Gửi đề nghị khảo sát | [Cũ](red-pinned/outputs/appointment-concise.json) · [Mới](green/outputs/appointment-concise.json) |
| appointment | formal | Quý vị cần đối chiếu gì? | Quý vị cần báo giá? | Quý vị muốn đề nghị lịch hẹn nào? | Quý vị cần biết gì trước khi hẹn? | Gửi đề nghị khảo sát | [Cũ](red-pinned/outputs/appointment-formal.json) · [Mới](green/outputs/appointment-formal.json) |
| appointment | friendly | Mình cùng xem nhé? | Mình xem điều kiện nhé? | Mình muốn hẹn khi nào nhỉ? | Mình xem gì trước khi hẹn nhé? | Gửi đề nghị khảo sát | [Cũ](red-pinned/outputs/appointment-friendly.json) · [Mới](green/outputs/appointment-friendly.json) |
| choose_session | plain | Cần kiểm tra điều gì? | Hãy xem điều kiện trước. | Bạn muốn chọn buổi nào? | Buổi nào hợp với bạn? | Chọn buổi | [Cũ](red-pinned/outputs/choose_session-plain.json) · [Mới](green/outputs/choose_session-plain.json) |
| choose_session | concise | Kiểm tra đâu trước? | Báo giá cần gì? | Chọn buổi nào? | Buổi nào phù hợp? | Chọn buổi | [Cũ](red-pinned/outputs/choose_session-concise.json) · [Mới](green/outputs/choose_session-concise.json) |
| choose_session | formal | Quý vị cần đối chiếu gì? | Quý vị cần báo giá? | Quý vị muốn chọn buổi nào? | Buổi nào phù hợp với quý vị? | Chọn buổi | [Cũ](red-pinned/outputs/choose_session-formal.json) · [Mới](green/outputs/choose_session-formal.json) |
| choose_session | friendly | Mình cùng xem nhé? | Mình xem điều kiện nhé? | Mình chọn buổi nào nhỉ? | Buổi nào hợp với mình nhỉ? | Chọn buổi | [Cũ](red-pinned/outputs/choose_session-friendly.json) · [Mới](green/outputs/choose_session-friendly.json) |

### Điều kiện thương mại trước CTA

Ở brief đặt lịch có điều kiện thương mại đã ký, QA trả 200. Ở brief chọn buổi có yêu cầu trình bày điều kiện nhưng thiếu căn cứ, QA trả 409. Cả hai ca trên bản sửa đều giữ CTA và câu mở đúng hành động đã duyệt. [Đặt lịch](green/outputs/terms-appointment.json) · [Chọn buổi](green/outputs/terms-choose_session.json)

### Phạm vi và bằng chứng tái kiểm

- **AMC-R60-01** có kiểm thử trên Content, editor và quyết định QA thực của một reviewer khác. [Nguồn artifact Windows và ba checkout CI](source-provenance.json) · [Lịch sử các lần chạy gồm cả thử nghiệm lỗi](trials.json)
- **AMC-R60-02** đã tái hiện và sửa lỗi xuống dòng F1. Lỗi cắt chữ trên dropdown cũ chưa tái hiện ở 390 px; bộ ảnh và phép đo cho thấy tên lựa chọn mới vừa vùng hiển thị. Bản sửa hiện hai nhiệm vụ của Director và cho phép kiểm lại digest. [Ảnh đối chứng khi mở gói tại máy](ui/COMPARE.html)
- **AMC-R60-03** còn mở ở cổng production. Bài đo tải, thời gian giữ khóa và recovery nằm trong backlog; đợt này chưa có số đo công suất renderer.

[Chỉ mục mọi tệp và SHA-256](files.json) · [CI và JUnit](ci.json) · [Diff bản sửa](https://github.com/datnv41001/ai-company/compare/555b968c85b09d52d50d2fd165ea9ff320e5afcd...edbca9483f59a20f8c3d1f54123a92e353cc3426) · [Hồ sơ, rollback và đề xuất pilot](https://github.com/datnv41001/ai-company/blob/edbca9483f59a20f8c3d1f54123a92e353cc3426/docs/evaluation/connected-workforce/SEMANTIC-REVIEW.md)
