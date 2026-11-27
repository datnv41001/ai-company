# Giả thuyết đã bác bỏ hoặc hoãn

**AMC-AI-RS-01 · Giữ baseline WF-03.** Trên bốn cặp tổng hợp, cách sắp xếp context và hướng dẫn B giảm số trường cần sửa ở một cặp, ba cặp hòa; cả bốn B mất ràng buộc. Ngưỡng đã khóa là cải thiện ở ít nhất ba cặp và giữ đủ ràng buộc. Hai nhánh cùng đạt 1/8 cho câu hỏi nghiên cứu và bằng chứng cần tìm. Hướng xem xét lại là kế thừa nghĩa vụ xác định từ projection và đo riêng chất lượng lập luận trên cohort mới. [Phiếu điểm, kết quả và đề xuất](../evaluation/rs01/FINAL.md)

**R59.** Hoãn giả thuyết đổi renderer sẽ cải thiện hiệu quả Marketing. Giấy phép, chi phí SaaS, footage, audio và mức độ người nhận chấp nhận là các câu hỏi riêng. Không suy ra causal lift từ hai file khác hook hay một chuỗi sandbox. [Phạm vi và nguồn đã đọc](CONNECTED-CREATIVE.md)

| ID | Giả thuyết | Quyết định và căn cứ | Điều kiện xem lại |
| --- | --- | --- | --- |
| R-01 | Có thể áp mô hình vault cá nhân làm kho chung cho mọi khách của agency. | **Bác bỏ cho kiến trúc AMC.** Bài Wecommit mô tả kho của một người. C1 kiểm quyền tới client/brand và mức nhạy cảm. Kho chung có thể đưa ghi chú và nguồn riêng vào câu trả lời ngoài phạm vi. [K-01](KNOWLEDGE_CARDS.md#k-01) | Chỉ xem xét bản thiết kế giữ nguyên quyền theo tenant/client/brand ở từng lần lấy dữ liệu. |
| R-02 | Nạp toàn bộ kho tri thức và toàn bộ skill vào mọi lượt để cải thiện chất lượng. | **Hoãn.** Chưa đo độ chính xác, chi phí và quyền qua các role. Đọc muộn cũng có thể bỏ mất điều kiện quan trọng. [K-02](KNOWLEDGE_CARDS.md#k-02) · [K-03](KNOWLEDGE_CARDS.md#k-03) | So hai cách trên cùng brief, cùng model và ngân sách với counterexample có qualifier/expiry. |
| R-03 | Chuyển đổi tăng như một case trên Brands Vietnam, hoặc tìm đủ 1.000 khách vì AI đã lập kế hoạch. | **Bác bỏ làm forecast.** Một số liệu được cộng đồng thuật lại thiếu dữ liệu thô; mục tiêu của ví dụ HubSpot là giả định. [K-05](KNOWLEDGE_CARDS.md#k-05) · [K-07](KNOWLEDGE_CARDS.md#k-07) | Một forecast riêng cho AMC cần baseline thật được phép dùng, phạm vi, dữ liệu và bất định. |
| R-04 | 500 hồ sơ reviewer hoặc một receipt tải nguồn chứng minh 500 reviewer đã học. | **Bác bỏ.** Registry đếm vai trò, receipt xác nhận một thao tác. Năng lực cần task mới có nhãn, run xác định model, finding đúng và đối chứng. [K-09](KNOWLEDGE_CARDS.md#k-09) · [K-10](KNOWLEDGE_CARDS.md#k-10) | Chỉ báo số invocation có chứng cứ; đánh giá riêng chất lượng và mức độc lập. |
| R-05 | Một conversion GA4 là một hóa đơn đã thu tiền; dùng clicks của Search Console làm mẫu số sessions không cần đối soát. | **Bác bỏ.** Hành vi được gắn event, phiên web, giao dịch và dòng tiền có nguồn, định nghĩa và cửa sổ khác nhau. [K-08](KNOWLEDGE_CARDS.md#k-08) | Chốt định nghĩa nghiệp vụ, nối khóa đúng scope, kiểm nguồn đơn hàng, hoàn tiền và kỳ ghi nhận. |
| R-06 | Asset hoặc claim từng được duyệt có thể tự động đưa sang kênh mới. | **Bác bỏ.** Kênh, tiếng, đối tượng, quyền sử dụng và điều kiện công bố có thể đổi. [K-06](KNOWLEDGE_CARDS.md#k-06) | Ghim revision gốc, so context và quyền, QA biến thể trước khi giao. |
| R-07 | Có thể thay platform bằng một swarm hoặc vẽ doanh thu, số agent đang làm từ số vai trò cấu hình. | **Bác bỏ trong increment này.** Hợp đồng DAG và ngân sách đang phục vụ công việc thật. Trạng thái execution phải truy về task/run; doanh thu cần nguồn riêng. [K-04](KNOWLEDGE_CARDS.md#k-04) · [K-11](KNOWLEDGE_CARDS.md#k-11) | Phải có vấn đề người dùng, phép đo, cơ chế quyền tương đương và ADR riêng cho thay đổi nền tảng. |

## Giả thuyết đối chiếu trong vòng bàn giao Sales/Service

| ID | Giả thuyết và quyết định | Bằng chứng và điều kiện xem lại |
|---|---|---|
| R-08 | Chuyển owner hoặc có task là đã liên hệ, đã nhận dịch vụ hay tạo doanh thu. **Bác bỏ** việc dùng một cờ thay nhiều mốc. | Đối soát từng mốc với nguồn, scope và bên nhận. Hiện chưa có acceptance thực địa. [K-12](KNOWLEDGE_CARDS.md#k-12) |
| R-09 | Áp BANT bắt buộc cho mọi yêu cầu, hoặc người nói chuyện đủ quyền xác nhận mọi điều khoản. **Bác bỏ** quy tắc chung này. | Kiểm theo ý định và chính sách cho đúng deal. Đánh dấu sự kiện có điều kiện và người có quyền quyết định. Ca được phép tư vấn dưới MOQ không mặc nhiên trở thành báo giá được duyệt. [K-13](KNOWLEDGE_CARDS.md#k-13) · [Consultation](../evaluation/business-intake/CONSULTATION.md) |
| R-10 | Có video/tên issue hoặc trang đăng nhập thì có thể suy ra toàn bộ hội thoại và nhu cầu. **Loại khỏi bằng chứng** khi thiếu nội dung. | Thu nhận thông tin khi có trang đọc được hoặc văn bản được nhà sản xuất cho phép. Ghi riêng phạm vi, tác giả và nguồn thay thế. [Nhật ký nguồn](SOURCE_REGISTRY.md#src-cloud) |
| R-11 | Mẫu quảng cáo được chọn, số view, retention, điều kiện index hoặc số lần hiển thị chứng minh hiệu quả doanh thu. **Bác bỏ** suy luận. | Dùng chúng để phát sinh câu hỏi, đối soát kết quả kinh doanh theo cohort và nguồn riêng. Cần mô hình nhận dạng nhân quả phù hợp trước khi tuyên bố hiệu quả tăng thêm. [K-15](KNOWLEDGE_CARDS.md#k-15) · [K-16](KNOWLEDGE_CARDS.md#k-16) |
| R-12 | Cần thay framework hiện hành để có đối chứng, hoặc có thể dùng lại nhãn công khai cũ làm holdout. **Bác bỏ** cho vòng này. | Repo đã có harness và rubric. Khóa cohort mới và giữ riêng receipt thật, mức đối chứng, công việc không chạy và giới hạn. [K-14](KNOWLEDGE_CARDS.md#k-14) |
| R-13 | Điểm khác nhau giữa hai brief chuyên môn chứng minh một ngôn ngữ tốt hơn hoặc xác lập mức tiết kiệm lao động. **Bác bỏ** diễn giải. | Dùng cặp cùng nghĩa vụ/ngữ cảnh để kiểm ngôn ngữ và đo giờ thật của practitioner cho suy luận kinh tế. [K-14](KNOWLEDGE_CARDS.md#k-14) · [O-09](PRODUCT_OPPORTUNITIES.md#o-09) |

## Quyết định vòng review #57

- Loại phương án lấy video cũ của một sản phẩm khác hoặc giữ MOQ của brief lịch sử để minh họa một offer mới. Phải đối chiếu bản gốc, SKU/dịch vụ, điều kiện, revision và đường nhận yêu cầu.
- Loại phương án dùng tỷ lệ tăng trưởng trong case study TikTok để dự báo kết quả AMC. Chỉ tái sử dụng cách lập giả thuyết, chọn một biến, người nghiệm thu và mẫu số.
- Loại phương án coi consent xử lý RFQ là quyền gửi sự kiện cho Google hoặc gọi validateOnly lên tài khoản thật. Quyền dữ liệu, adapter, destination, đối soát và thẩm quyền phát hành là các dependency riêng.
- Loại việc diễn giải 14/24 nhãn thô của Qwen thành 14 bản bàn giao dùng được. Lịch sử chấm đủ hợp đồng là 7/24. Khả năng grammar loại lỗi định dạng và khả năng hiểu nghiệp vụ cần hai phép thử riêng. [Kết quả đã khóa](../evaluation/department-study/advisory/PROSPECTIVE-HANDOFF.md)

## R58 · Diễn giải hiệu quả creative

Bác giả thuyết có thể xếp hạng creative từ tỷ lệ xác nhận trên số người đã gửi form. Mẫu số đó loại cả những người được phân bổ nhưng không chuyển đổi, còn thời điểm Service xác nhận phụ thuộc nhân sự. Điều kiện xem xét lại gồm receipt phân bổ, theo dõi chung cho cả hai nhánh và outcome đã khóa. Tách thử thay hook khỏi so sánh nhiều concept. [Protocol và đọc lại hai receipt](../evaluation/workforce-video/MEASUREMENT.md)
