# Khi nào Marketing có thể bàn giao một yêu cầu cho Sales hoặc Service?

## 1. Phiên bản đã tích hợp

Maintainer đã merge PR #56 vào main tại `bbb0b9c41b92e666e133499e9c71f53592828c3d`. Cả bảy head #49–55 đều là tổ tiên của head #56. Tree của merge trùng với tree đã review ở trial. Quyết định này đóng sáu finding R53-01/02 và R55-01–04 cho phát triển nội bộ. Phần dưới mô tả công việc **sau** merge, dành cho vòng phản biện tiếp theo. [Git objects, CI và JUnit của main](MAIN-56.json) · [Quyết định #56](https://github.com/datnv41001/ai-company/pull/56)

## 2. Nguồn và phạm vi quan sát

Vòng này đối chiếu cả bảy URL khởi đầu. Đọc được tài liệu HubSpot, bài về qualification, một thảo luận SalesOps và README của Promptfoo. YouTube chỉ cung cấp tiêu đề cho một video, nên dẫn riêng văn bản đối thoại do CloudTalk đăng trên LinkedIn. Video còn lại và bài Reddit thứ hai chưa truy xuất được nội dung. Các thẻ phân biệt lời kể cá nhân, tài liệu nền tảng, vấn đề trên GitHub và nghiên cứu thực nghiệm. Các nguồn về social, quảng cáo, search, CRO và đo lường có phạm vi và điều kiện tái sử dụng ghi theo từng dòng. [Sổ nguồn](../../research/SOURCE_REGISTRY.md) · [Thẻ kiến thức](../../research/KNOWLEDGE_CARDS.md)

## 3. Nhu cầu người dùng

Khi khách sửa số lượng, đổi lịch hoặc rút yêu cầu, người điều phối cần xác định dữ liệu nào còn hiệu lực. Người nhận cần biết ai đã nhận trách nhiệm, điều gì còn thiếu và ai được duyệt điều kiện thương mại. Một lần chuyển chủ sở hữu trong CRM chưa chứng minh rằng Sales đã tiếp nhận hoặc liên lạc. Thread SalesOps là quan sát định tính của một nhóm tự chọn. Tần suất vấn đề, mức tổn thất và mức sẵn lòng chi trả tại doanh nghiệp Việt Nam còn chưa đo. [Cơ hội O-09](../../research/PRODUCT_OPPORTUNITIES.md)

## 4. Năng lực có thể tận dụng

WF-14 và WF-20 có intake theo phiên bản, điều phối trong phạm vi quyền và lịch sử quyết định. WF-18 có số liệu đối soát theo giai đoạn. Ma trận khảo sát chín nhóm việc, từ nghiên cứu thị trường đến tối ưu, chỉ rõ ai giao việc, SOP, đầu ra, người nghiệm thu, lỗi và phần AMC đã có. Giữ nguyên danh mục V1 gồm 49 module, 37 vai trò và 24 workflow. [Ma trận nghiệp vụ](../../research/APPLICABILITY_MATRIX.md) · [Sổ năng lực](../DEPARTMENT-CAPABILITY-REGISTER.md)

## 5. Khoảng trống đã kiểm tra

Trên 12 tình huống tổng hợp mới, mỗi tình huống có bản Việt và Anh, quy tắc dựa vào ô đã điền đánh dấu đủ thông tin ở 14/16 thẻ còn cần làm rõ. Cả ba phương pháp đều chưa tạo được quyết định chuyển người có thẩm quyền **đúng hợp đồng** ở bất kỳ thẻ nào trong tám thẻ cần bước đó. Việc lưu đúng hồ sơ khách điều chỉnh, phân biệt câu hỏi cho người mua với câu hỏi nội bộ, và đo chi phí xử lý thật là ba vấn đề khác nhau. [Điểm theo lớp và từng hồ sơ](../department-study/advisory/PROSPECTIVE-HANDOFF.md)

## 6. Phương án đã chọn và đã loại

Dùng hành động hủy hiện có, yêu cầu lý do và revision hiện hành qua bàn điều phối. Nhu cầu thay thế bắt đầu bằng biểu mẫu có consent mới. Pilot v2 hỏi producer về việc biết treatment trong hay ngoài assignment, giữ khai báo chấm mù cho các vai trò còn lại. Chọn đánh giá Qwen ở lab. Chưa chọn đưa quy tắc thử nghiệm hoặc Qwen vào runtime CRM. Chưa có căn cứ để thêm một CRM khác, thay framework đánh giá hoặc tự cấp thẩm quyền báo giá và đặt lịch. [Hành trình](../business-intake/CONSULTATION.md) · [Quy trình pilot](../department-study/PILOT-ABCD/OFFICIAL.md) · [Giả thuyết đã loại](../../research/REJECTED_HYPOTHESES.md)

## 7. Bằng chứng AI

Phương pháp, rubric, cohort, đáp án và ngân sách được khóa trước inference. Sau khi Product Owner duyệt, Qwen2.5-1.5B-Instruct Q4_K_M chạy local một lần trên mỗi thẻ. Dự đoán ba nhánh và 24 receipt được niêm phong trước khi mở đáp án. Quy tắc hiện hữu đạt 8/24, quy tắc bổ sung 8/24 với đầu ra giống hệt, Qwen đạt 7/24. Qwen đúng 7/8 khi cần hỏi, nhưng 13/24 kết quả vi phạm hợp đồng đầu ra và 0/8 thẻ đã đủ thông tin có quyết định sử dụng được. Điểm Qwen VI/EN là 3/12 và 4/12. Ngưỡng tiến bước không đạt. [Protocol trước inference](https://github.com/datnv41001/ai-company/blob/cf65816334b4a25a0fd368f9e66387308acc3e17/tests/evaluation/department/handoff-v2/PROTOCOL.md) · [Bản lưu trước khi mở đáp án](https://github.com/datnv41001/ai-company/blob/1b34b81a57770c6f43461fe90649199e7f52043b/tests/evaluation/department/handoff-v2/FIRST-RUN.zip) · [Điểm, nhận xét và lệnh chấm lại offline](../department-study/advisory/PROSPECTIVE-HANDOFF.md)

Các mốc nghiên cứu cũ giữ nguyên. Control đạt 24/36 nghĩa vụ chuyên môn, Qwen rewrite 17/36 trên hai brief khác nhau. Đối chứng handoff cũ đạt 14/24 với tám false-ready. Không thể quy chênh lệch của hai brief cho ngôn ngữ hoặc so hai holdout như cùng một mẫu. [Obligations](../department-study/advisory/OBLIGATIONS.md) · [Handoff v1](../department-study/advisory/HANDOFF-BENCHMARK.md)

## 8. Đầu ra người tiếp quản dùng được

- Điều phối viên có thể hủy yêu cầu trước phân công, tra lý do và tiếp nhận một RFQ mới. Kiểm thử theo dõi cả RFQ cũ, consent mới và doanh thu. Giao diện có ảnh thực ở 390, 820 và 1280 px, hai theme. [Hướng dẫn và sáu ảnh](../business-intake/CONSULTATION.md)
- Điều phối viên pilot có thể phát và đối soát phiếu theo vai trò, truy ngược từng quyết định về bản sản xuất tương ứng và đọc lại vault v1. Các lượt lộ nhãn thật vẫn phải ghi nhận. [Runbook và lệnh](../department-study/PILOT-ABCD/OFFICIAL.md)
- Reviewer có thể chấm lại thí nghiệm trên máy khác mà không gọi model. Đối chiếu decision, field, câu hỏi, phiếu chấm mù và SHA trước khi đề xuất thay đổi. [Artifact và replay](../department-study/advisory/PROSPECTIVE-HANDOFF.md)

## 9. Chất lượng, thời gian và chi phí

Lượt Qwen dùng 5.536 token vào, 1.043 token ra, 235,75 giây gồm khởi động, phí dịch vụ 0. Chi phí điện và nhân sự chưa đo. Hai bản ngôn ngữ của một tình huống phụ thuộc nhau. Nhận xét của AI trên dữ liệu tổng hợp chỉ phục vụ kiểm tra câu hỏi. Số người hành nghề tham gia và số việc doanh nghiệp đã chấp nhận đều bằng 0.

Với pilot A/B/C/D, lưu quyết định bản đầu trước biên tập, claim và nguồn, điểm chuyên môn cùng dẫn chứng, thời gian sản xuất/biên tập/QA, thời gian lịch từ nhận brief tới bản dùng được, số việc được chấp nhận và lỗi nghiêm trọng. Tử số chi phí đầy đủ tính cả lao động, compute, thẩm định và lần thất bại. Mẫu số là số việc người nhận chấp thuận sử dụng. Khi mẫu số bằng 0 hoặc thiếu đơn giá, chỉ số là **chưa xác định**. [Hồ sơ A/B/C/D](../department-study/PILOT-ABCD/OFFICIAL.md)

## 10. Câu hỏi cho Independent Reviewer

1. Lần theo một yêu cầu bị rút trước khi bàn giao. Phiếu cũ, người ghi lý do, revision, consent mới và các chỉ số Sales có chứng minh được hai yêu cầu riêng biệt không?
2. So phiếu producer biết đúng nhánh mình được giao với một incident lộ khóa phân bổ cho người chấm. Hai trường hợp có đi đến đúng quyết định pilot, kể cả khi đọc vault cũ?
3. Từ tệp đã niêm phong, đối chiếu một ca Qwen phát hiện dữ liệu cũ và một ca đoán đúng nhãn nhưng gửi sai hợp đồng. Nếu sửa hợp đồng, người nhận có thật sự ra quyết định đúng hơn hay chỉ tăng số đầu ra hợp lệ?
4. Bước nghiên cứu tiếp theo là kiểm tra cách một điều phối viên xác minh **một** trường đã bị khách sửa và nguồn có thẩm quyền, với tiêu chí dừng và cohort mới nếu cần model. Người phụ trách pilot xác nhận consent và cách đo trước khi mời người hành nghề.

Quyết định hiện tại là tiếp tục phát triển nội bộ. Production và Commercial GA giữ **NO-GO**.
