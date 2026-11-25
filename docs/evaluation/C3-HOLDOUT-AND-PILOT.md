# Đo chất lượng WF-03 và WF-13

Bộ holdout v1 gồm 50 brief tiếng Việt, năm nhóm người dùng và hai workflow. Mỗi giao điểm có năm brief với sản phẩm, quyết định mua, điều kiện áp dụng và mục tiêu riêng. Dữ liệu do nhóm kỹ thuật tạo cho thí nghiệm. Bộ năm doanh nghiệp cũ tiếp tục dùng cho phát triển và hồi quy. Cố định tập, thứ tự chọn mẫu và thang điểm trước khi xem đầu ra mới. Nếu điều chỉnh prompt theo kết quả, chuyển tập này sang bộ hồi quy và lập holdout khác cho vòng tiếp theo.

[Tệp brief cố định](../../tests/evaluation/c3/holdout-v1.json) có SHA-256 `c497ff707c986acaa3c48ba799ab1a378f194d3e7cd4262834d41a4aae0fe477` với UTF-8 và LF. Chỉ các trường trong hợp đồng tiếp nhận đi vào model. Phần ghi chú của người chấm ở ngoài prompt. Giá kiểu dịch vụ chung trong một số hồ sơ đòi hỏi xác nhận đơn vị bán. Ghi yêu cầu làm rõ là một kết quả của hệ thống. Giữ cả các brief này trong mẫu số.

## Thực nghiệm

Trên một PostgreSQL thử nghiệm cục bộ đã migrate, chạy từng suite tuần tự với tài khoản ứng dụng hạn chế và một Qwen loopback. Dùng cấu hình và đường dẫn model như job `workforce-model`. Thư mục kết quả mới cho từng SHA và lần lặp.

```bash
python tests/evaluation/c3/qualification.py smoke-receipts
python tests/evaluation/c3/verify_receipts.py smoke-receipts "$(git rev-parse HEAD)"
python tests/evaluation/c3/qualification.py paired-results --holdout tests/evaluation/c3/holdout-v1.json --arms projected improved
```

Giữ cùng weights, locale, số worker, ngân sách và bộ brief khi so sánh các phiên bản. Chạy lại bằng thư mục mới để đo độ lặp lại. Tách thời gian chờ, tốc độ suy luận, token đầu vào/đầu ra, phí nhà cung cấp, peak RAM của model và công biên tập. Đối chiếu checkpoint gốc và phần được renderer tạo tất định trước khi quy một kết quả cho năng lực model. Ghi nhận mọi lần thử, lần cần làm rõ, lỗi, thiếu output và lần thử lại. Tách thời gian người dùng cung cấp thông tin khỏi thời gian CPU. Mức phí trả nhà cung cấp bằng 0 vẫn có chi phí máy và nhân công.

## Pilot nghiệp vụ

Chọn trước các ca số 01 và 02 của mỗi nhóm để có mười nhiệm vụ, mỗi workflow năm nhiệm vụ. Hoán đổi thứ tự điều kiện và ẩn tên model, release, thời gian chạy, tên nhánh khỏi tài liệu gửi người chấm. Với WF-03, cung cấp bản chiến lược, nghiên cứu và kế hoạch đo. Với WF-13, cung cấp trang đích, SEO và bản xem trước. Gửi nguồn tổng hợp được phép đối chiếu trong cả hai điều kiện.

Hai chuyên viên Marketing độc lập phân công theo khối cân bằng. Mỗi người làm một phiên thủ công và một phiên dùng AMC trên hai brief khác nhau nhưng cùng nhóm và workflow. Người thứ hai đảo điều kiện trên cùng cặp brief. Dùng hai ca mới tương đương từ mỗi ô khi cần tránh hiệu ứng ghi nhớ. Người chấm chất lượng nhận đầu ra ẩn danh trước khi xem điểm của đồng nghiệp. Giữ cả hai phiếu, điểm bất đồng và kết luận có dẫn chứng. AI có thể cung cấp đánh giá tham khảo riêng. Ghi tên vai trò, kinh nghiệm và xung đột lợi ích khi có chuyên viên tham gia.

| Tiêu chí | Đơn vị chấm và điều kiện đạt |
| --- | --- |
| Đúng dữ kiện | Đối chiếu từng SKU, variant, giá, tiền tệ, đơn vị, thuế, số lượng với revision nguồn. Lưu trường, câu và chứng cứ cho mỗi lỗi. |
| Phạm vi áp dụng | Tất cả điều kiện bắt buộc đi cùng nhận định. Ghi lỗi địa bàn, thời hạn, kênh và ngoại lệ. |
| Nguồn thực sự hỗ trợ | Đếm câu vật chất được nguồn đang hiệu lực hỗ trợ chia cho tổng câu cần nguồn. Chỉ ghi đúng handle chưa đủ. |
| Hữu ích cho người mua | Đúng người mua, giải đáp được quyết định trong brief, có bước tiếp theo khả thi. |
| Chuyên môn | WF-03 nêu vấn đề, định vị, kênh có lý do, giả thuyết có thể bác bỏ và sự kiện đo được. WF-13 có tiêu đề, lợi ích có căn cứ, CTA, SEO title, meta và ý định tìm kiếm nhất quán. |
| Khẳng định thiếu căn cứ | Ghi rõ từng câu và mức độ. Một vi phạm nghiêm trọng loại bản giao. |
| Đạt lần đầu | Chuyên viên có thể nhận dùng sau lượt đầu và không cần sửa nội dung nghiệp vụ. Lỗi kỹ thuật và thiếu dữ liệu đều nằm trong mẫu số được giao. |
| Thời gian và chi phí | Bắt đầu khi nhận brief, kết thúc khi chuyên viên chấp nhận. Tách phút lập kế hoạch, tạo nội dung, tìm nguồn, chỉnh sửa, QA và đợi. Báo cả median, khoảng và từng cặp. |

Phiếu trống ở [pilot-form.json](../../tests/evaluation/c3/pilot-form.json). Công thức tiết kiệm thời gian theo cặp là `1 − tổng phút AMC / tổng phút thủ công`. Chi phí mỗi bản đạt bằng tổng phí model, chi phí máy và nhân công của cả các lần thất bại chia cho số bản đã được chấp nhận. Nếu mẫu số bằng 0 hoặc chưa có đơn giá, ghi “chưa xác định”. Ngưỡng đề xuất cho pilot là đúng 100% giá trị có cấu trúc, 0 vi phạm nghiêm trọng, nguồn hỗ trợ ít nhất 95%, ít nhất 80% đạt nghiệp vụ lần đầu và giảm ít nhất 30% tổng thời gian. Đánh giá độc lập hiện còn chờ chuyên viên.

## Căn cứ phương pháp

Thu riêng nội dung gốc, chỉ mục và ghi chú diễn giải; dùng liên kết revision để truy ngược nguồn trong AMC. Bài viết của Trần Quốc Huy mô tả kinh nghiệm tổ chức tri thức cá nhân. Chưa có phép đo hiệu quả ở agency nhiều khách từ nguồn này. Đọc bài công khai ngày 25/11/2026. [Wecommit](https://www.wecommit.com.vn/bai-viet/second-brain-voi-agentic-ai-va-obsidian)

Kiểm tra SEO title có mô tả trang cụ thể và trả lời đúng ý định người tìm kiếm. Phân biệt hành động gửi yêu cầu với doanh thu đã ghi nhận. Hướng dẫn của nền tảng làm căn cứ cho tiêu chí, còn hiệu quả chuyển đổi phải đo tại từng chiến dịch. [Google Search Central](https://developers.google.com/search/docs/appearance/title-link) · [Google Analytics, generate_lead](https://developers.google.com/analytics/devguides/collection/protocol/ga4/reference/events#generate_lead)
