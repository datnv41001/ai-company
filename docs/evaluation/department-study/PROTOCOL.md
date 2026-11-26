# Thử nghiệm trọn gói công việc Marketing

**Giả thuyết đăng ký trước.** Khi giữ nguyên brief, nguồn, hợp đồng vai trò và giới hạn token, model 7B có thể tạo nhiều nội dung khác phương án xác định mà vẫn đạt gate, đồng thời giao bộ tài liệu dễ dùng hơn trong hai tình huống mua khác nhau. Thành công về giao dịch và chất lượng nghiệp vụ là hai kết quả riêng.

**Đầu vào khóa.** Hai brief B2B mới trong [tập brief](../../../tests/evaluation/department/briefs-v1.json) dùng dữ kiện tổng hợp đã duyệt. Cả hai có phân tích người mua/thị trường, định vị, chiến lược, landing, SEO, social, ad, kế hoạch đo lường, creative brief và lịch. Giá phải đi cùng đơn vị và điều kiện. Giả thuyết về người mua cần được trình bày như điều phải kiểm chứng. Tài liệu phải phân biệt báo giá theo hộp với đặt lịch khảo sát. Điện trở/an toàn/chứng nhận, mức tiết kiệm và số liệu ngoài hồ sơ đều cần nguồn được duyệt.

**Ba nhánh.** Đối chứng dùng bộ soạn xác định và phiên bản kiến thức giống hai nhánh model. Với Qwen 0.5B và 7B, chạy thật từ director qua research/strategy, content/SEO bằng WF-03 và WF-13, ghi cả thất bại đầu tiên. Một lượt biên tập social và ad có schema riêng trong dụng cụ thử nghiệm dùng kết quả hai workflow. Ghi nhãn đầu ra này là ứng viên nghiên cứu theo kênh. Mẫu brief sáng tạo và lịch xác định được đưa vào gói hoàn chỉnh. Vai trò ứng dụng không tự được thăng hạng bởi kết quả thử nghiệm. Một model bổ sung chỉ tham gia khi có đủ tài nguyên và xác minh được điều kiện tương đương.

**Phạm vi so sánh.** Cùng task, ưu tiên, chứng cứ, giọng điệu, schema, thứ tự vai trò, nhiệt độ, seed và chính sách chỉnh sửa giữa các nhánh model. Nội dung trung gian sinh ra có thể khác. Giữ nguyên lần gọi đầu, retry, toàn bộ bản nháp, biên tập do script và bộ giao cuối. Giới hạn mỗi model một lượt trên mỗi brief; sự cố hạ tầng được ghi và cho phép chạy tiếp phần chưa có kết quả. Không chọn lượt chạy hoặc câu có lợi cho một model. Đo cả token đầu vào/ra, wall time, bộ nhớ khi đo được, chi phí provider; chi phí máy, lao động chưa quan sát ghi là thiếu. Không suy diễn bằng 0.

## Rubric khóa trước khi chạy

Mỗi gói chấm tám tiêu chí bên dưới, mỗi tiêu chí 0–2. 0 là thiếu hoặc mâu thuẫn, 1 là có nội dung nhưng người làm tiếp còn phải bổ sung thông tin, 2 là có căn cứ và người nhận có thể hành động. Người chấm dẫn nguyên văn trường liên quan và nêu phần cần biên tập. Một tuyên bố thương mại trái nguồn, nhầm hành động người mua hoặc bỏ điều kiện trọng yếu là blocker, không bù bằng điểm tổng. Giữ báo cáo kỹ thuật tự động và kết luận nghề nghiệp riêng.

| Tiêu chí | Điều người chấm phải đối chiếu |
|---|---|
| Người mua & thị trường | Phân khúc, vấn đề cần xác minh, câu hỏi hoặc phép thử có thể thực hiện. |
| Định vị | Giá trị gắn với tình huống của người mua và dữ kiện có thể kiểm chứng. |
| Chiến lược | Lựa chọn hành động/kênh có lý do, bước tiếp theo sau kết quả thử. |
| Landing | Lời mời phù hợp brief, thông tin cần cung cấp, điều kiện giá/đơn vị và ranh giới claim. |
| SEO | Title, intent và mô tả khớp trang, ngôn ngữ và nhu cầu tìm kiếm. |
| Social | Mở bài, giá trị, lời mời phù hợp hoàn cảnh đọc; không dùng lời hứa thiếu bằng chứng. |
| Quảng cáo | Message ngắn có sự khác biệt với bài xã hội, liên kết đúng offer và bước tiếp theo. |
| Đo lường | Biến cố và mẫu số, kỳ quan sát, trách nhiệm đối soát, xử lý thiếu nguồn hoặc hủy. |

Chấm toàn bộ gói ở lần đầu và bản dùng được sau QA. Đối chiếu các trường giữ nguyên văn với receipt của model. Kiểm tra riêng tính nhất quán giữa các tài sản và ghi rõ khi một câu lặp qua các kênh. Một cặp brief chỉ cung cấp tín hiệu định tính, chưa đủ để ước lượng hiệu quả thực tế hoặc mức sẵn sàng thương mại. Thử nghiệm thủ công có đồng thuận với người làm Marketing, reviewer và Sales/owner dùng cùng bộ brief và rubric.

