# Đo công việc Marketing trong hành trình báo giá B2B

Campaign Manager đặt sáu đầu ra cho cùng một brief. Copywriter bàn giao trang báo giá cho Sales, hai bản nội dung cho Social và Media, một bộ metadata cho SEO. Designer nhận brief thiết kế và Campaign Manager nhận lịch đa kênh. Từng đầu ra có người nhận và có thể được trả lại để sửa.

## Đơn vị và phép đếm

Hợp đồng `rfq-work-units/v1` dùng ba loại việc và mức phức tạp ghi ngay khi giao. Trang chuyển đổi nhiều phần, nội dung đơn kênh, brief thiết kế và lịch đa kênh có độ phức tạp khác nhau. Khi đối chiếu hiệu suất, so cùng loại việc, cùng độ phức tạp, người nhận, tiêu chí và phạm vi. Tổng số bản giao chỉ thể hiện khối lượng. [Sáu đầu ra được giao trước khi chạy](../../app/campaign_work_units.py)

- Trong lab, khóa đơn vị là cặp kịch bản và vị trí đầu ra. Mỗi lần chạy trả về một ảnh chụp hiện trạng của sáu việc đã giao. Đối chiếu theo khóa khi chạy lại. Nhiều lần retry, đổi model, đổi revision, duyệt lại hoặc mở lại báo cáo vẫn chỉ có một vị trí trong mẫu số. Với pilot có nhiều khách, thêm tenant, campaign và mã yêu cầu độc lập vào khóa trước khi gộp các phiên.
- `fixture_accepted` yêu cầu đúng revision, nội dung, digest và biên nhận của vai trò mô phỏng. Mất bản giao hoặc sửa nội dung vẫn giữ vị trí trong bảng và bỏ dấu đã duyệt cho đến khi có biên nhận tương ứng. Kết quả giữ riêng số đã giao, đã qua QA mô phỏng và đã được doanh nghiệp tiếp nhận. Phải có chuyên viên đúng thẩm quyền chấp nhận đúng revision trong pilot mới được tính cho mục tiêu thương mại.
- Định danh gói hình ảnh là brief cho Designer. Việc dựng ảnh và sản xuất video cần yêu cầu và bản giao riêng. Chi phí media thuộc báo cáo chiến dịch. Chi phí sản xuất bản giao gồm công người làm, compute, model và công cụ cho mọi lần thử, kể cả việc dang dở.

## Pilot có chuyên viên

Khóa trước các cặp việc tương đương, dữ liệu đầu vào, phương pháp đối chứng và rubric. Ghi chủ thể duyệt, căn cứ về thẩm quyền, thời điểm, revision và digest của đúng tài sản. Kết quả kinh tế dùng thời gian thực và chi phí thực tế của các việc có cùng phạm vi. [Bộ phiếu và cách chấm mù](C3-PRACTITIONER-KIT.md)

| Dữ liệu cần ghi | Quy ước |
| --- | --- |
| Mốc thời gian | Ghi nhận brief, lượt đầu, trả sửa, nộp lại và chấp nhận cuối. Thời gian trôi qua gồm cả chờ. Ghi riêng thời lượng chủ động của người làm rõ, biên tập và QA |
| Chất lượng | Ghi chấp nhận ngay lần đầu trên toàn bộ việc đã giao, số claim chưa đủ chứng cứ, lỗi nghiêm trọng, số việc trả lại và số chưa có bản |
| Đường cơ sở và nhánh có AMC | Dùng cùng đơn vị giây và cùng độ phức tạp. So thời gian đến **được chấp nhận**. Giữ lại ca bỏ dở và lý do thay vì bỏ khỏi mẫu |
| Chi phí mỗi bản được chấp nhận | Tổng chi phí phân bổ của toàn bộ việc trong nhóm / số việc được chấp nhận. Thiếu đơn giá, thiếu đường cơ sở hoặc mẫu số bằng 0 thì để trống và nêu lý do |

Trong lần chạy synthetic, `runtime_ms` đo thời gian máy thực hiện kịch bản. Các trường về phút công và chi phí phân bổ có giá trị `null` khi chưa đo. Không cộng chi phí media mô phỏng vào tử số chi phí sản xuất. Chưa có kết quả thay thế lao động.

## Nguồn và quyết định áp dụng · 25/11/2026

| Nguồn đã đọc và loại bằng chứng | Quyết định có thể kiểm tra trong AMC | Giới hạn |
| --- | --- | --- |
| Google Analytics, tài liệu chính thức về vòng đời lead, giao dịch mua và hoàn tiền | Báo riêng RFQ, lead đạt chuẩn, đơn hàng xác nhận và đơn hủy. Đối soát theo mã giao dịch và kiểm thử phát lại sự kiện. [Danh mục sự kiện](https://developers.google.com/analytics/devguides/collection/ga4/reference/events) | Taxonomy tham khảo. Doanh thu dùng chứng từ đơn hàng trong fixture. Chưa kết nối Analytics hay CRM bên ngoài |
| Trần Quốc Huy, Wecommit, bài viết công khai của tác giả về chuẩn hóa công việc trước khi dùng agent | Rubric yêu cầu người giao, người nhận, các bước, đầu ra và tiêu chí nghiệp vụ trước khi đếm việc. [Bài viết của tác giả](https://www.linkedin.com/posts/huytq_đưa-ai-vào-doanh-nghiệp-thì-đừng-bắt-đầu-activity-7487420942252417024-U9w-) | Kinh nghiệm doanh nghiệp. Chỉ dùng phần văn bản công khai. Hiệu quả kinh tế của AMC cần đối chứng riêng |
