# Tiếp quản độc lập trên bản tích hợp

Người đọc là một AI mới trong phiên riêng. Đầu vào ban đầu chỉ gồm SHA, bộ đọc file Git có biên nhận và các câu hỏi tiếp quản. Người đọc không nhận lịch sử chat, đáp án, kết quả CI hoặc mô tả các finding. Bộ đọc giới hạn trong các đối tượng Git của head `c5c6329599a66fd2dc6011428e7ab8eed9208df4`. [Nhật ký các lần truy cập](cold-access.json)

## Người đọc tự tìm thấy

- AMC giữ đầy đủ phạm vi 49 module, 37 vai trò và 24 workflow. Đơn vị nghiệm thu là công việc Marketing được người có thẩm quyền chấp nhận, gắn brief/phiên bản. Commercial GA vẫn NO-GO.
- Người đọc xác định đúng chuỗi #49 → #50 → #51 → #52 → #54 và #53 độc lập. Họ phân biệt cổng đo theo cohort với số liệu chiến dịch, nhận diện hai API có thể cùng tác động một revision, tra ra vai trò nào chỉ được ghi phản hồi và yêu cầu xác thực lại quyền khi replay.
- Họ tìm được quan hệ giữa brief, form, consent, CRM, MOQ, điều kiện đặt đơn và phép đo. Với schema core v26, publisher cài bổ sung chốt kiểm writer. Plan lịch sử và receipt đã phát hành có đường đọc lại. Khi rollback phải dừng writer, khôi phục thử ở database riêng, giữ journal mới để đối soát.
- Họ trích được 96 lượt gọi model, mức tăng 20 phát hiện đúng cùng 14 cảnh báo sai, chấm mù 24/36 so với 17/36 và 0 người hành nghề. Đề xuất tiếp theo là thử holdout độc lập mới và đo công sửa trong pilot nghiệp vụ bốn nhánh.

## Smoke do người đọc tự chọn

Người đọc yêu cầu khởi tạo môi trường phát triển cục bộ với SQLite in-memory, JWT ngẫu nhiên, khởi chạy Uvicorn ở loopback, đọc health rồi dừng. Họ chọn `tests/test_optimization_scope.py` và `tests/test_business_intake.py`. Người vận hành thực thi các lệnh này từ `git archive` của chính head, dùng môi trường Python phát triển có sẵn trên Windows. Health, trang gốc và OpenAPI UI đều HTTP 200. Health trả `production_ready=false`. Hai tệp cho 8 ca đạt và 1 ca PostgreSQL bỏ qua ở lượt SQLite. [Hash archive, exit code và kết quả](cold-smoke.json) · [Lượt Windows có PostgreSQL](windows-native.json)

## Các khoảng trống được ghi nhận

1. README và một số đoạn cũ trong tài liệu release gate mô tả các mốc trước. Khi lập kế hoạch, cần phân biệt lịch sử đó với trạng thái của từng tính năng trong HANDOFF và sổ năng lực. [Hướng bàn giao ở head](https://github.com/datnv41001/ai-company/blob/c5c6329599a66fd2dc6011428e7ab8eed9208df4/HANDOFF.md)
2. Hướng dẫn intake mô tả quy trình chuyển đổi nhưng còn thiếu link trực tiếp từ phần đó sang quy trình rollback. Người tiếp quản đã tìm thấy quy trình. Khi rollback cần giữ cả bản sao tiền nâng cấp và journal phát sinh sau thời điểm backup, xác minh restore và quyền trên DB riêng trước khi chuyển writer. [Runbook rollback](https://github.com/datnv41001/ai-company/blob/c5c6329599a66fd2dc6011428e7ab8eed9208df4/docs/evaluation/sandbox-operations/CUTOVER.md)
3. Checkout ngoại tuyến không chứa quyết định merge trực tiếp hay CI phát sinh sau head. Biên nhận GitHub riêng ghép bằng head, parent, tree và các hash JUnit. Lượt tiếp quản này chứng minh một AI tìm tài liệu và chọn đúng smoke. Nó chưa đo thời gian onboarding của kỹ sư mới hoặc mức chấp nhận của người làm Marketing. [CI đã đối chiếu](github-ci.json)
