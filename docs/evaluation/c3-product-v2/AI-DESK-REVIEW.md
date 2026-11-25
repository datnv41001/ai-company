# Hai lượt đọc mù bằng AI

Hai agent đọc độc lập theo chuyên môn. Một agent đọc ba cặp chiến lược, một agent đọc năm cặp copy/SEO. Từng agent chỉ nhận brief, nguồn và hai bộ trường A/B theo thứ tự ngẫu nhiên trước khi nộp phiếu. Mỗi bộ có một người chấm AI. Mẫu ghép gồm tám brief có bản Qwen để so sánh trong mười brief được giao. Hai brief dừng ở bước lập kế hoạch được tính trong tỷ lệ tạo bản của cả bộ.

| Phương án | Đủ dùng ở lần đọc đầu | Cần sửa đáng kể | Chưa dùng được |
| --- | ---: | ---: | ---: |
| Qwen 0.5B + composer | 0/8 | 4/8 | 4/8 |
| Composer tất định | 2/8 | 6/8 | 0/8 |

Ở v2-02, giá chưa bao gồm khắc tên nhưng đầu ra Qwen suy diễn thành “không cần khắc tên”. Ở v2-04, Qwen thêm cam kết tiến độ mà nguồn chưa xác nhận. Ở v2-03, phần phương pháp đo dùng chữ “web_search”, chưa xác định sự kiện ghi nhận yêu cầu mẫu. Những trường hợp này cần sửa nội dung và đối chiếu nguồn trước khi giao khách.

Các điểm trên là nhận định của AI trên tám cặp có đủ đầu ra. Mức chấp nhận của chuyên viên, độ tin cậy giữa hai người chấm trên cùng một bài và mức giảm thời gian làm việc vẫn chưa đo. [Phiếu và khóa A/B sau chấm](AI-DESK-REVIEW.json)
