# Chấm mù bản nháp Content và SEO

Bạn là người duyệt nghiệp vụ cho bốn chiến dịch Marketing giả lập. Hãy quyết định những cảnh báo mà một người duyệt **nên nhận** khi đọc đầu ra của từng node. Có 24 ca, một nửa Content và một nửa SEO. Mỗi ca có brief, nguồn đã dẫn và bản viết. Với SEO, dùng đúng trang Content có ID ghi trong trường `parent`. Vận dụng hiểu biết tiếng Anh, tiếng Việt và ngữ cảnh của chiến dịch.

## Cách ghi nhãn

1. Đọc `cases.md` hoặc `cases.json`. Đọc toàn văn nguồn, phân biệt nguồn Brand Kit và các nguồn mà node đã dẫn. Dùng quyết định của chính bạn trước khi xem bất kỳ dự đoán hay điểm số nào.
2. Mở `blind-labels.json`, điền tên hoặc mã reviewer. Với mỗi ca, ghi từng cặp `field` và `rule` cần cảnh báo vào `findings`. Ví dụ về cú pháp là `{"field":"call_to_action","rule":"cta_action"}`. Dùng `note` để giải thích quyết định khó, nhất là khi nguồn đang nói về sản phẩm khác hoặc tác giả phủ định một lời hứa.
3. Đánh dấu `reviewed` bằng `true` sau khi đã chấm đủ các trường. Giữ `findings` là `[]` nếu bạn đã xét ca và không cần cảnh báo nào. Mỗi cặp chỉ ghi một lần trong mỗi ca. Giữ nguyên ID, loại nhãn và mã băm bộ đề.
4. Trả lại bản nhãn đã chốt cho người tổng hợp. Nếu hai reviewer bất đồng, lưu cả hai bản gốc và ghi lý do trong bản phân xử trước khi mở kết quả công cụ. Người tổng hợp cần ghi rõ ai đã gán nhãn nghiệp vụ.

## Quy tắc Content

| Rule | Trường cần đánh dấu | Khi nào cần người duyệt xem lại |
|---|---|---|
| `cta_action` | `call_to_action` | Lời kêu gọi mơ hồ, lặp lại thông tin hoặc thiếu hành động có thể thực hiện. Xét cả CTA tự nhiên viết theo cách khác hoặc bằng ngôn ngữ khác. |
| `brief_alignment` | `body_copy` | Xét headline và body cùng nhau. Chủ đề hoặc mục tiêu tổng thể lệch brief. |
| `audience_alignment` | `body_copy` | Thông điệp nhắm sai nhóm hoặc cần đối chiếu lại đối tượng. Cách diễn đạt đồng nghĩa có thể vẫn đúng. |
| `offer_alignment` | `body_copy` | Sản phẩm hay đề nghị trong headline/body khác điều brief giao. |
| `brand_alignment` | `body_copy` | Nội dung nói về sản phẩm khác hoặc mâu thuẫn với mô tả sản phẩm trong Brand Kit. |
| `brand_instruction` | Trường Content chứa vi phạm | Nội dung dùng cách diễn đạt Brand Kit yêu cầu tránh, kể cả khi yêu cầu được viết trong văn xuôi. |

## Quy tắc SEO

| Rule | Trường cần đánh dấu | Khi nào cần người duyệt xem lại |
|---|---|---|
| `page_alignment` | `page_title`, `meta_description` | Trường mô tả sai nội dung của trang Content tiền nhiệm. Một từ khóa chung có thể xuất hiện trong hai chủ đề khác nhau. |
| `intent_alignment` | `search_intent` | Mục đích của người tìm kiếm lệch với nội dung hoặc hành động mà trang cung cấp. |
| `metadata_length` | `page_title`, `meta_description` | Đếm ký tự Unicode như trong manifest. Khoảng gợi ý bao gồm cả hai đầu, title 12–70 và meta 30–170. Gắn nhãn khi ra ngoài khoảng. |
| `duplicate_metadata` | `meta_description` | Meta lặp title mà không cung cấp thông tin bổ sung. |

## Quy tắc dùng ở cả hai vai trò

- `claim_evidence` áp dụng cho trường có nhận định cần bằng chứng nhưng nguồn đã dẫn thiếu căn cứ. Xét số liệu, thứ hạng, cam kết, chứng thực, so sánh và thuộc tính có thể kiểm chứng. Đọc câu phủ định và phần còn lại của đoạn trước khi gán nhãn.
- `quote_context` áp dụng cho trường có câu khẳng định cần rà lại ngữ cảnh dù trích được chính câu đó từ nguồn. Kiểm tra chủ thể, phạm vi, tính chủ quan và các điều kiện đi kèm. Với một claim, chọn trạng thái bằng chứng thích hợp nhất. Một trường chứa nhiều claim có thể cần cả hai rule.

Dùng tên trường gốc của Content là `headline`, `body_copy`, `call_to_action`; các trường SEO là `page_title`, `meta_description`, `search_intent`. Ghi mọi cặp hợp lệ cần xem lại, kể cả khi có nhiều vấn đề trong cùng ca. Quyết định duyệt cuối cùng vẫn thuộc người duyệt.
