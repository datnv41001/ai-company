# Thiết kế PR #7 · Director đề xuất đồ thị và điều phối theo node

Đề xuất để review kiến trúc. Điểm xuất phát là [merge PR #6](https://github.com/datnv41001/ai-company/commit/4bfa8cf15ee0f654f779442debb75007d74f8ec2), schema v11. Hiện `diamond-v1` có một lease mỗi run và dùng thời gian chờ retry cấp run. Thiết kế dưới đây chia công việc thành hai bước có thể nghiệm thu độc lập.

## 1. Director đề xuất, server kiểm tra và đóng băng

Với run thử nghiệm mới, Director nhận brief và danh mục skill được phép cho campaign. Lượt lập kế hoạch đi qua cùng worker identity, lease, hạn mức và ledger như lượt inference hiện tại. Đề xuất chỉ chứa khóa node cục bộ, skill, phân công và danh sách khóa của các predecessor. Server sở hữu scope, nguồn, route, giá và quy tắc bàn giao. Mỗi skill cần có kiểu đầu vào, đầu ra và cách tổng hợp đã đăng ký.

Server đọc JSON theo schema đóng và giới hạn kích thước trước khi phân tích đồ thị. Mốc đề xuất cho đợt thử là tối đa 8 node chuyên môn, 16 cạnh và 5 tầng chuyên môn. Kiểm tra khóa duy nhất, cạnh không trùng, đầu mút tồn tại, đồ thị không chu trình, hợp đồng dữ liệu của từng cạnh và đủ đầu ra bắt buộc cho brief. Mọi node phải đi tới Join duy nhất do server tạo. Các hợp đồng bắt buộc của loại brief được cấu hình phía server. Kiểm thử ít nhất hai đồ thị hợp lệ có cấu trúc khác nhau cho hai brief.

Server cấp ID riêng cho từng node, kể cả hai node dùng cùng skill. Chuẩn hóa thứ tự node, cạnh và đầu vào Join, sau đó lưu revision, digest, scope, phiên bản danh mục và quy tắc tổng hợp trong một giao dịch. Phát lại cùng kết quả lập kế hoạch chỉ tạo một kế hoạch. Kết quả sai được ghi lý do, hạch toán riêng usage đã phát sinh cho Director và kết thúc lần thử. Chỉ kế hoạch đã đóng băng mới được cấp việc và giữ tiền cho node chuyên môn. Muốn đổi đồ thị sau đó phải mở run mới. Bước này chạy với một lease cho mỗi run.

## 2. Cấp lease theo node và giữ ngân sách khi tranh chấp

Chỉ mở mức đồng thời lớn hơn một cho run mới có cấu hình thử nghiệm khi các phép thử bên dưới đã đạt. Mốc ban đầu đề xuất là hai node cùng run. V11 hiện dùng unique index `one_run_slot`, lease và `ready_at` cấp run. Cần chuyển đồng bộ cả đường cấp offer, lấy mailbox, gia hạn nếu có, thu hồi, hết hạn, ghi kết quả và retry sang định danh attempt của node. Giữ giới hạn một mailbox đang mở trên mỗi worker và quy tắc một lease trên mỗi run cho các workflow cũ.

- Mỗi node có trạng thái, `ready_at`, bộ đếm lượt đã gửi và attempt hiện hành theo run/revision. Chọn agency theo cơ chế công bằng hiện tại, rồi chọn run và node đủ điều kiện. Thời gian chờ của Content chỉ trì hoãn Content. Một lỗi hết lượt chặn Join bắt buộc và ghi nguyên nhân. Phải thu hồi các offer còn mở cho run đã kết thúc, phân biệt offer chưa nhận và inference đã gửi.
- Cấp offer, giữ tiền và kiểm tra đồng thời giới hạn agency, run, worker và node trong cùng giao dịch. Tái sử dụng thứ tự khóa của dispatcher/đối soát. Thả khóa trước inference. Đếm cả chi ròng và hold còn mở. Khi sang tháng UTC, giới hạn run vẫn tính xuyên kỳ và receipt hạch toán vào kỳ gốc.
- Khi nhận kết quả, kiểm tra worker LOGIN, quyền hiện hành, revision, node, attempt và hạn lease. Ghi tối đa một checkpoint hợp lệ cho node. Receipt đến muộn vẫn đi qua đường đối soát độc lập. Khi thu hồi quyền, vô hiệu hóa tất cả lease của run trong cùng giao dịch, kể cả hai nhánh đang thực thi.
- Hai checkpoint cuối có thể đến trên hai kết nối. Tuần tự hóa bước xét Join trên bản ghi run, đọc lại đủ predecessor rồi tạo bản giao, provenance và QA trong một giao dịch với một khóa duy nhất cho run/revision. Worker chỉ nhận phân công và đầu ra tiền nhiệm trực tiếp đã đóng băng. QA tiếp tục duyệt đúng revision và digest của bản giao.

## Bằng chứng bắt buộc trước khi bật hai lease

| Kịch bản với PostgreSQL và hai phiên worker riêng | Điều kiện đạt |
| --- | --- |
| Hai node cạnh tranh, mỗi node cần giữ 700 micro-USD khi run còn 1.000. Lặp lại với hai run dùng chung agency còn 1.000. | Chính xác một offer được cấp. Ledger, tổng run và kỳ agency khớp ngay sau commit. Khi đủ ngân sách cho cả hai, chứng minh hai lease thực sự chồng thời gian. |
| Một node timeout sau khi gửi, node anh em sẵn sàng. Một offer khác hết hạn trước lúc worker lấy. | Node anh em có thể chạy trong thời gian backoff. Attempt đã gửi giữ khoản chưa rõ usage. Offer chưa gửi nhả hold, không tốn lượt. Kết quả lease cũ đến sau lease mới không tạo checkpoint. |
| Hai node đang chạy thì thu hồi quyền, sau đó cấp lại. A/B cùng agency và C khác agency. | Cả hai token của run bị thu hồi đều mất hiệu lực. Mailbox, đồ thị, checkpoint và bản giao của từng khách chỉ hiện đúng scope. Đối soát receipt trùng, refund và phí đến muộn cho đúng attempt/kỳ. |
| Hai nhánh hoàn tất đồng thời, đổi thứ tự, dừng dispatcher trước/sau commit Join rồi khởi động lại. | Cùng checkpoint cho cùng digest. Chỉ một bản giao và một liên kết QA. Kiểm tra quyết định QA cũ sau A → B → A và snapshot đã được khách duyệt. |
| Kế hoạch vượt giới hạn, sai kiểu, thiếu đầu ra, tham chiếu ngoài kế hoạch hoặc có chu trình. | Có lý do từ chối và chi phí planner truy vết được. Số offer, hold và checkpoint của specialist đều bằng 0. |

Chạy các ca tranh chấp bằng barrier trên kết nối DB độc lập và đồng hồ kiểm soát được. Đối chiếu trực tiếp bảng attempt, checkpoint, ledger, số dư và bản giao sau commit. Đo thời gian chờ của agency thứ hai khi agency đầu có nhiều node sẵn sàng. Dùng fake provider cho thứ tự sự kiện xác định, sau đó Docker/Qwen local với dữ liệu tổng hợp để kiểm tra tích hợp. Báo cáo riêng số lần planner bị từ chối, số lease chồng thời gian, token xác nhận và usage chưa biết. Kiểm tra màn hình trạng thái theo node ở 1280 px và 390 px.

## Nâng cấp và quay về chế độ một lease

Đề xuất migration kế tiếp theo hướng bổ sung, diễn tập từ mọi schema hỗ trợ và chạy lại lần hai. Fixture v11 phải có run tuyến tính và diamond đang chạy, offer chưa nhận, hold chưa rõ usage, receipt, checkpoint, quyết định QA và snapshot khách. Đối chiếu từng bản ghi trước/sau. Cấu hình mới áp dụng khi tạo run. Triển khai nội bộ lần lượt qua planner với một lease, rồi thử hai lease sau khi đạt các ca trên.

Khi cần dừng, tắt nhận run thử mới, ngừng cấp lease mới, xử lý hoặc thu hồi từng attempt đang mở và đối soát hold trước khi quay về template v11 cho brief mới. Giữ lịch sử đồ thị và sổ cái để kiểm tra. [ADR v11](ADR-009-DIRECTOR-DAG.md) · [Quy tắc tài chính và danh tính worker](ADR-008-COMPANY-OPERATIONS.md) · [Runbook Docker](POOL-RUNBOOK.md).
