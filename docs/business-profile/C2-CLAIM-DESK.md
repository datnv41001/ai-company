# Đối chiếu nguồn và duyệt nhận định Marketing

Mở **Hồ sơ doanh nghiệp**, chọn khách hàng và thương hiệu, rồi chọn **Nguồn và nhận định**. Một người bán có thể đối chiếu câu mô tả sản phẩm với đúng dòng của tài liệu. Nhân sự Marketing có thể đọc câu đã được phép dùng cùng SKU, thị trường, kênh, ngôn ngữ và điều kiện đi kèm. Người có quyền duyệt kiểm tra nguyên văn riêng trước khi quyết định.

## Thao tác

1. Chọn nguồn và chọn vị trí trích dẫn. Có thể ghi nguồn mới từ tài liệu đã đối chiếu, ghi rõ đơn vị phát hành, tên tài liệu, trang hoặc dòng, thời hạn và phạm vi truy cập. Lưu nguồn tạo một bản nháp. Người duyệt có thể phê duyệt sau khi đối chiếu bản gốc. Với một tuyên bố thương mại có đơn vị giá, thuế hoặc chính sách, chọn mục chứng cứ đã gắn với khai báo thương mại C1 tương ứng.
2. Sửa câu đề xuất, từng qualifier, địa bàn, ngôn ngữ, kênh và điều kiện đơn hàng rồi so với trích dẫn cạnh bên. Bản nháp chỉ lưu khi toàn bộ assertion khớp mục chứng cứ. Đổi bằng chứng khi sửa làm thay đổi ý nghĩa câu. Giao dịch tạo một liên kết và một revision claim. Hai người lưu cùng revision cần tải bản hiện tại để tiếp tục. Sau mất phản hồi, gửi lại cùng nội dung trên form đang mở để dùng lại khóa yêu cầu.
3. Người duyệt kiểm tra phần **Ảnh hưởng đang thấy** và **Lịch sử**. Ghi quyết định cho liên kết chứng cứ, rồi quyết định cho claim. Với câu cần chuyên môn, chọn ủy quyền của chính người duyệt, đúng lĩnh vực và còn hiệu lực. Người viết không được tự ký claim nhạy cảm. Một người có thẩm quyền khác xác nhận ủy quyền theo hợp đồng C1. Dispute và thu hồi đều có lý do, thứ tự và digest của bản đang mở.
4. Với nguồn hạn chế, editor chỉ thấy câu công khai và phạm vi đã duyệt khi toàn bộ phụ thuộc còn hiệu lực. Đối chiếu lại bằng nút **Kiểm tra lại hiệu lực**. Tranh chấp, thu hồi hoặc hết hạn nguồn hay ủy quyền làm câu mất điều kiện hiển thị ở lần đọc tiếp theo. Quyền đọc của người duyệt cho phép họ xem lịch sử và so sánh cả khi thông tin thay đổi.

## Dữ liệu và quyền

Mỗi tab chỉ lưu khóa yêu cầu và SHA-256 của ý định đang chờ, tách theo tài khoản, tenant, khách hàng và thương hiệu. Khi tải lại, desk tìm kết quả đã commit của chính actor trước khi cho gửi lại. Văn bản nguồn, nội dung claim, lý do duyệt và URL có mã nguồn riêng không được ghi vào web storage.

Các route đọc nằm dưới `/api/tenants/{tenant}/clients/{client}/brands/{brand}/knowledge/claim-desk`. Server chọn actor từ bearer và kiểm thành viên, client, brand trước mỗi lần đọc. Board phân trang nguồn và claim. Chi tiết tách câu dùng cho Marketing khỏi đoạn trích, locator, bằng chứng, lịch sử riêng và thông tin ủy quyền. Các response của desk dùng `Cache-Control: private, no-store`. Trình duyệt hủy request và xóa phần chi tiết khi đổi phạm vi. Việc phê duyệt dùng giao dịch và CAS `expected_digest`/`expected_sequence` của C1.

Migration publisher cài bổ sung predicate `amc_business.claim_display_current` bằng `python migrations/apply.py`. Predicate chỉ trả boolean cho phiên đọc đã ký tại đúng tenant, client và brand. Nó kiểm cây phụ thuộc, quyết định và ủy quyền theo thời điểm database. Sau đó server dùng lại quy tắc C1 để kiểm giá và xung đột thương mại. Khi không đủ quyền đọc khai báo thương mại cần so khớp, câu bị giữ lại. Biểu thức SQL quyền đặc biệt không trả dòng dữ liệu nguồn cho API runtime. Khả năng này có dấu hash riêng, chạy lại publisher để nâng hoặc sửa. Giữ core v22 và không chiếm migration 023 của Identity.

GET chi tiết C1 cho source, binding và claim chỉ trả dữ liệu thô khi các tham chiếu tương ứng đọc được. Lịch sử source/binding/claim cho nhân sự không duyệt giữ trạng thái, sequence và thời điểm, bỏ ghi chú tự do và người quyết định. Collection có thể hiển thị ID, subject, digest, phiên bản và trạng thái của các revision người đọc được phép thấy. Impact chỉ liệt kê snapshot trong phạm vi đọc của người gọi. Kiểm các route cụ thể bằng `tests/test_claim_desk.py`. Đây là kiểm chứng giao diện ứng dụng, không phải đánh giá mọi API hay toàn bộ kênh suy luận từ metadata.

## Kiểm lại trên máy khác

1. Dùng `python scripts/init_env.py` và `docker compose up --build -d` trong lab chỉ có dữ liệu tổng hợp. Job migrate dùng publisher. API dùng role `amc_runtime`.
2. Cài `requirements-dev.txt`, chạy `python -m pytest -q tests/test_claim_desk.py tests/test_knowledge_permissions.py`. Biến `AMC_TEST_PG=1` và DSN loopback `amc_test_*` của CI kích hoạt cả SQLite và PostgreSQL thực. Kiểm cả kết quả dương của owner/qualified reviewer và từ chối đọc chéo client/tenant, từ worker hay khi cơ sở duyệt mất hiệu lực.
3. Cài `requirements-browser.txt` và Chromium của Playwright. Đặt `AMC_BROWSER_TEST_URL` bằng origin loopback, `AMC_BROWSER_MAILBOX_PROJECT` bằng project Compose, rồi chạy `python tests/browser_claim_desk.py`. Có thể đặt `AMC_CLAIM_SCREENSHOTS` để lưu ảnh từ dữ liệu tổng hợp. Job Compose chạy cùng các ca ở 1280 px và 390 px. Ca editor kiểm chuỗi canary trong response đã quan sát, DOM, cookie nhìn thấy bằng JavaScript, URL, history, web storage và heap Chromium. Không lưu heap hoặc token thành artifact.
4. Khi rollback, dùng binary và publisher đã chốt trước đó, chỉ mở writer sau khi kiểm trạng thái schema và quyền. Revision, liên kết và quyết định đã ghi dùng bảng C1 append-only nên vẫn còn nguyên. Cần refresh/đăng nhập lại để buộc trình duyệt tải giao diện đã rollback.

Đây là công cụ kiểm tra và duyệt dữ liệu nội bộ. Việc có chứng cứ khớp và revision còn hiệu lực không chứng minh tuyên bố Marketing đúng trong thực tế. Dữ liệu một người đã đọc trước khi bị thu hồi không thể xóa hồi tố khỏi bản họ tự lưu. C3 cần quyết định riêng trước khi gọi Workforce, QA, chia sẻ hoặc phát hành nội dung. Commercial GA tiếp tục NO-GO.
