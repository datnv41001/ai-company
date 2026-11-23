# ADR-003 · Bàn giao và duyệt nội dung theo phiên bản

Mốc đầu vào là commit 55dada3. Chủ sản phẩm yêu cầu giao bản, QA nội bộ và quyết định của khách trong cùng sản phẩm V1.0. Bản hai khách cách ly được dữ liệu theo client, nhưng cùng client vẫn xem được bản nháp nội bộ. Schema 3 thu hẹp hợp đồng đọc này.

## Quyết định

- Membership tiếp tục xác định một client cho mỗi người trong một agency. Grant của cổng duyệt có thể giới hạn thêm brand và campaign, với hai quyền độc lập là bình luận và quyết định. Request gửi cho nhóm của client thuộc đúng phạm vi. Khi cần nhiều client cho một người, chuyển sang nhiều grant sau một migration riêng. Viewer nội bộ giữ nguyên.
- Gộp snapshot và request trong một hàng bất biến vì một lần chia sẻ tạo đúng một phiên bản và một yêu cầu. Khoá ngoại ghép chứng minh chuỗi tenant → client → brand → campaign → deliverable. Mỗi lần chia sẻ có số phiên bản tăng. Chỉ tiêu đề và trường văn bản dành cho khách được chiếu sang snapshot. Bản cũ giữ nguyên sau khi sửa.
- Mỗi quyết định hoặc bình luận là một sự kiện chỉ thêm, gắn actor, thời gian, digest và khoá lặp. Một unique index có điều kiện cho phép đúng một sự kiện kết thúc trên mỗi request. Khoá giao dịch tuần tự hóa chia sẻ, quyết định và đóng yêu cầu của cùng tài liệu. Hết hạn được tính ở thời điểm xử lý.
- Editor sửa bản làm việc thì phải gửi QA lại. Người QA khác người soạn. Admin chia sẻ sau QA. Một bản chia sẻ mới đóng yêu cầu đang chờ trước đó. Chỉ khách có grant quyết định mới được duyệt, từ chối hoặc yêu cầu sửa. Module này không gọi connector.
- API v2 cũ tiếp tục phục vụ nhân sự nội bộ. Client bên ngoài chỉ có hồ sơ client của mình và cổng review mới. Bảng brand/campaign thô chứa hướng dẫn nội bộ và brief nên cũng giới hạn nhân sự. RLS dùng cùng ranh giới. Các bảng lịch sử chỉ cấp SELECT/INSERT cho runtime.

## Migration và phục hồi

Migration 003 chạy cùng giao dịch, giữ bản nháp, lịch sử QA và memberships cũ. Backfill quyền xem theo client cho membership bên ngoài, mặc định không có quyền bình luận/quyết định. Các draft cũ không tự sinh snapshot. Chi tiết có trong SQL của migration.

Trước nâng cấp, dừng ghi, tạo bản sao PostgreSQL và thử phục hồi trên DB riêng. Khi migration thất bại, giao dịch rollback. Sau khi đã có quyết định mới, ưu tiên sửa tiến về phía trước. Nếu cần quay lại phiên bản 2, ngừng phục vụ cổng khách, giữ nguyên DB v3 làm bằng chứng và khôi phục bản sao v2 sang DB khác cho ứng dụng v2. Chỉ mở lại sau khi chủ dữ liệu quyết định cách đối soát các sự kiện phát sinh. Bản v2 có ranh giới hiển thị bản nháp rộng hơn.
