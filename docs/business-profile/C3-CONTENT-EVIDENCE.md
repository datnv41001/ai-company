# Kiểm chứng từng nhận định trước khi duyệt bản Marketing

Hợp đồng `amc.content-evidence/1` áp dụng cho bản làm việc do WF-03 @2/@3 hoặc WF-13 @5/@6 tạo. Liên kết Workforce run → deliverable do worker ghi xác định phạm vi. Một bản soạn thủ công có chuỗi F1 hoặc ID run trong JSON vẫn dùng quy trình riêng của bản đó.

## Quy trình biên tập

1. Mở **Phê duyệt**, chọn bản làm việc, rồi mở **Đối chiếu nội dung với bằng chứng**. Mỗi dòng chỉ vị trí trong tiêu đề hoặc nội dung khách sẽ đọc. Khoảng `[start,end)` tính theo Unicode code point của chính văn bản đã lưu.
2. Một giá được công bố cùng tiền tệ, đơn vị, cơ sở tính, thuế, số lượng, MOQ, bậc giá và điều kiện. Khi sửa giá, dùng toàn bộ công bố hiện hành. So sánh theo mẫu giá của đúng release và locale. Cách diễn đạt kết quả định lượng khác mẫu cần biên tập lại.
3. Với nội dung mâu thuẫn, sửa bản làm việc và gửi QA lại. Với diễn giải định tính, người có ủy quyền đúng chuyên môn có thể chọn công bố đã ghim và ghi rõ lý do công bố đó hỗ trợ câu viết. Hệ thống đối chiếu lĩnh vực, điều kiện và quyền đang hiệu lực. Hành động duyệt nội dung vẫn độc lập với tác giả hoặc người sửa gần nhất.
4. Xem **Lịch sử phiên bản và quyết định** để mở đánh giá ban đầu theo lần lưu và SHA-256. Một câu quay lại sau chuỗi sửa A → B → A nhận mã quyết định mới. Bản khách đã nhận tiếp tục đọc được qua lịch sử bàn giao.

## Dữ liệu và quyền

Mỗi assessment lưu phiên bản hợp đồng, lần lưu, SHA-256 tiêu đề và preview, digest manifest, scope và các nhận định kèm trường, span, loại, handle, kết quả và lý do. Một khối giá được coi là một nhận định gồm cả điều kiện. `PRODUCT` và `MARKET` trỏ tới revision dữ liệu chủ. Các handle `F1…` trỏ tới claim, binding và nguồn của chính manifest. Quyền đọc chi tiết nguồn gốc được kiểm tra ở phía server. Nhân sự biên tập nhận phần nội dung và kết quả tự động. Người duyệt đủ quyền có thể xem nguồn, digest, điều kiện, tài liệu và vị trí gốc.

Endpoint `GET /api/tenants/{tenant}/deliverables/{id}/content-evidence` mở đánh giá. Endpoint `POST …/content-evidence/resolutions` yêu cầu `expected_qa_revision`, `expected_content_digest`, `statement_id`, `handle`, `qualification_revision` và `reason`. Quyết định được lưu dưới dạng lệnh có chữ ký trong cùng scope. QA và chia sẻ kiểm tra lại quyền nguồn, quyền hiện tại của người xác minh, kết quả từng nhận định và digest đánh giá ngay trong giao dịch. Dịch vụ trả 409 khi còn vấn đề và 412 khi phiên bản gửi lên đã cũ. Replay một bản chia sẻ có sẵn trả đúng snapshot đã ghi.

Lớp so sánh chấp nhận văn bản công bố đúng mẫu, cùng một số trường danh tính/phạm vi được gắn revision. Diễn giải mới được giữ chờ phản biện. Các nguồn Marketing được trích trong cả checkpoint giúp truy vết công việc của model. Quyết định duyệt một câu chỉ dựa trên công bố phù hợp với câu đó. Một quyết định ngữ nghĩa lưu nhận định và lý do của người xác minh. Việc đánh giá chất lượng Marketing vẫn cần một pilot nghiệp vụ độc lập.

## Chạy lại bằng dữ liệu tổng hợp

```bash
python -m pytest -q tests/test_c3_content_gate.py
AMC_KNOWLEDGE_EVIDENCE=./knowledge-browser-evidence python -m pytest -q tests/browser_c3_content_gate.py -k sqlite
```

Trên Windows dùng `$env:AMC_KNOWLEDGE_EVIDENCE` để đặt thư mục nhận ảnh. Bộ Chromium mở API loopback và database SQLite dùng riêng, đăng nhập thật ở 1280, 820, 390 px, kiểm phản biện, quyết định có ủy quyền và lịch sử. File `content-evidence/acceptance.json` ghi viewport và kết quả. Job API PostgreSQL còn chạy `test_published_content_gate` qua registry worker trên database tổng hợp, dùng `AMC_TEST_PG=1` và cấu hình job hiện hữu.

Ở head trước sửa `6a2d65f3`, năm nội dung tổng hợp đều được API duyệt với HTTP 200. Các ca gồm giảm giá giả, sai giá, mở phạm vi ra toàn quốc, bỏ điều kiện và nêu so sánh thiếu chứng cứ nhưng có handle hợp lệ. Điều kiện nghiệm thu của bản sửa là cả năm trả 409 rồi bản đã sửa được duyệt và chia sẻ. Các ca khác kiểm mandate bị thu hồi, lần lưu A → B → A, quyền đọc nguyên bản và trùng lệnh khi mất phản hồi.

Khi cần ngưng sử dụng, quản trị viên dừng tiếp nhận việc mới theo release và giữ nguyên lịch sử. Quyết định đưa phiên bản dịch vụ về trước gate phải tính tới việc phiên bản đó từng chấp nhận cả năm ca nói trên. Mọi nghiệm thu hiện tại dùng dữ liệu phát triển nội bộ.
