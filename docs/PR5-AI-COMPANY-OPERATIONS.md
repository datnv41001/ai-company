# Kế hoạch PR #5 · Điều phối nhiều dự án và ngân sách agency

**Đề xuất cho phát triển nội bộ.** Mốc thiết kế là schema 8 tại [commit merge PR #4](https://github.com/datnv41001/ai-company/commit/45e5c701132a5e7a6baa6fd6bf8cbacee3d5330f). Bài nghiệm thu chính là hai khách A và B của cùng agency có hai chiến dịch chạy đồng thời, khách C thuộc agency khác cũng có việc. Mỗi đầu ra, lần gọi model và khoản phí phải truy ngược được về đúng chiến dịch.

## Từ một worker theo chiến dịch đến một nhóm worker

Hiện mỗi tiến trình worker nhận một campaign cấu hình sẵn. `claim()` giữ dự phòng theo run và tạo lease. `finish()` kiểm tra lại lease trước khi ghi checkpoint và bàn giao. Director hiện đưa chỉ dẫn cho các bước do backend sắp thứ tự. PR #5 nên tái sử dụng các điểm kiểm soát này. [Worker](../app/workforce_worker.py) · [Model hiện hành](../app/workforce_models.py) · [Quyền Workforce](../migrations/005_workforce.sql)

| Thành phần đề xuất | Hành vi và quyền |
|---|---|
| AI Director | Từ brief đã nhận và các kỹ năng được agency cho phép, đề xuất công việc, phụ thuộc, hạn và ưu tiên. Backend kiểm tra chu trình, số bước, giới hạn run, quyền người nhận và nguồn. Chỉ các task có đủ đầu vào mới được chuyển sang sẵn sàng. |
| Dispatcher | Chọn task đã sẵn sàng, luân phiên giữa các agency còn suất rồi xét ưu tiên, hạn và thời gian chờ trong agency. Dispatcher chỉ đọc metadata hàng đợi như ID, scope, kỹ năng và thời điểm. Nội dung brief và nguồn ở luồng worker có phân quyền. |
| Worker pool | Worker xác thực bằng danh tính dịch vụ đã đăng ký. DB cấp đúng một lease cho task mà danh tính đó được phép nhận. Backend lấy scope từ task đã lưu, kiểm tra lại khi nhận việc và khi ghi kết quả. Mỗi giao dịch đặt lại context; session dùng lại cho khách B phải qua kiểm tra quyền mới. |
| Ngân sách và sổ cái | Owner/admin cấu hình ngân sách agency theo kỳ. Mỗi attempt có dự phòng riêng trong cả giới hạn agency và giới hạn run. Sự kiện tài chính giữ lịch sử ngay cả khi worker hết lease hoặc kết quả nội dung bị loại. |
| Màn hình điều hành | Nhân sự agency lọc tiến độ theo client/campaign, xem task bị chặn, chờ QA, khoản đang giữ và phí chưa xác nhận. Đầu ra khách được tra qua cổng snapshot và quyết định phiên bản hiện có. |

## Dữ liệu và giao dịch đề xuất

- Dùng campaign làm phạm vi dự án đầu tiên. Task mang khóa tenant, client, brand, campaign và run, có khóa ngoại ghép đến đúng run. Quan hệ phụ thuộc chỉ nối task trong cùng run. Định danh logic của bước là duy nhất trong run để replay kế hoạch không tạo bản sao. Một công việc làm lại sau chỉnh sửa cần có quan hệ với công việc trước.
- Bảng đăng ký worker ghi danh tính, kỹ năng và phạm vi đã được cấp. Thiết kế thủ tục claim chỉ trả về việc thuộc các scope hợp lệ của danh tính đã xác thực. Các giá trị session dùng cho RLS được đặt từ DB sau khi xác thực lease. Viết test quyền cho worker, dispatcher và API trước khi đề xuất thay đổi policy. Các bảng mới dùng FORCE RLS; kiểm tra bằng kết nối runtime bị giới hạn.
- Trong giao dịch claim, kiểm tra lại grant, phụ thuộc, giới hạn đồng thời và số dư. Khóa các hàng ngân sách, task và run theo một thứ tự thống nhất với luồng thu hồi. Ghi attempt, dự phòng và lease trong cùng giao dịch. Chỉ gọi model sau commit. Giao dịch hoàn tất cần đúng token lease và được phép ghi tối đa một kết quả cho task. Worker đến muộn có thể bổ sung bằng chứng phí cho attempt cũ qua đường đối soát riêng.
- Dùng micro-USD nguyên, kiểu có đủ dung lượng cho tổng agency. Mỗi attempt mang ID riêng, kỳ ngân sách, model, phiên bản giá, usage, mã request provider nếu có. Sổ cái chỉ thêm sự kiện giữ tiền, ghi nhận usage, giải phóng hoặc điều chỉnh. Mỗi sự kiện có khóa chống ghi trùng. Số khả dụng bằng hạn mức trừ chi phí đã ghi nhận và các khoản giữ còn mở; việc chuyển một khoản giữ thành chi phí phải nguyên tử.
- Timeout hoặc worker chết sau khi gửi giữ khoản dự phòng ở trạng thái chưa xác nhận. Retry cần dự phòng mới. Nhập chứng từ provider theo ID đã đối chiếu, ghi phần chênh lệch, cảnh báo nếu vượt hạn mức và chặn attempt trả phí mới. Chứng từ không ghép chắc chắn được đưa vào danh sách cần xử lý. Đối soát muộn điều chỉnh đúng kỳ gốc. Chi phí ước tính khi gửi lệnh có thể khác hóa đơn thực. Trong PR nội bộ, dùng Qwen local và chứng từ thử có kiểm soát.

## Thứ tự triển khai và bằng chứng để review

1. **Khóa hợp đồng dữ liệu và quyền.** Chốt mô hình task, attempt, kỳ ngân sách, ledger và danh tính worker trong ADR. Chuẩn bị migration kế tiếp từ v8 cùng fixture có run đang chạy, reservation chưa đóng, snapshot đã duyệt và grant đã thu hồi. Xác định điểm chuyển giao giữa worker cũ và pool để một run có đúng một bộ xử lý.
2. **Hoàn thiện claim và kế toán trước khi tăng số worker.** Trên PostgreSQL thật, cho hai worker tranh một task và hai campaign tranh khoản cuối cùng của cùng agency. Ví dụ với hạn mức 1.000 micro-USD, hai attempt cùng đòi giữ 700 thì chỉ một attempt được gọi provider. Kiểm tra retry, crash sau commit, lease hết hạn, usage về muộn, đối soát cùng chứng từ hai lần và tổng dư khớp sổ cái.
3. **Nối Director, dispatcher và pool.** Chạy đồng thời A, B và C với dữ liệu thử phân biệt. Kiểm tra task phụ thuộc phải chờ, task ưu tiên thấp vẫn tiến triển, một worker dùng lại kết nối không đọc được dữ liệu ngoài scope. Thu hồi quyền của A giữa lúc gọi model phải chặn kết quả và retry của A; B và C vẫn hoàn tất. Truy vấn trực tiếp với role runtime phải cho kết quả cách ly tương tự API.
4. **Nghiệm thu qua giao diện và Docker.** Cho ít nhất hai chiến dịch qua Qwen thật với hai worker. Đối chiếu chuỗi brief → run → task → attempt → ledger → deliverable → revision/digest → snapshot. Browser desktop/mobile kiểm tra hàng chờ, phí chưa xác nhận, QA độc lập, A → B → A trả 412 và giới hạn đọc của khách. Chạy lại toàn bộ suite schema 8 cùng đường nâng cấp mới, so từng snapshot và quyết định trước/sau migration.
5. **Phục hồi trên DB thử.** Sao lưu trước migration. Khi cần dừng pool, ngừng nhận task mới, kiểm kê lease và khoản giữ, chờ hoặc đóng từng attempt theo chứng từ. Chỉ chuyển quyền xử lý khi đã đối chiếu. Giữ bản DB mới để truy vết khoản phát sinh sau backup.

Khi review thiết kế, cần chốt kỳ ngân sách và múi giờ agency, số run đồng thời mặc định, cách xử lý khi hóa đơn cao hơn dự phòng, quyền điều chỉnh sổ cái và ai được chuyển giao task. Bộ kiểm thử PR #4 là mốc hồi quy cho mọi thay đổi liên quan đến RLS, QA và snapshot.
