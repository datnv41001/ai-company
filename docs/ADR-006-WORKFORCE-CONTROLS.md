# ADR-006 · Quyền người gửi brief, ngân sách và bằng chứng marketing

Áp dụng cho schema 6 của nhánh AI Workforce nội bộ. Người nhận bàn giao bắt đầu ở [HANDOFF](../HANDOFF.md). Thiết kế nền và giao thức checkpoint ở [ADR-005](ADR-005-AI-WORKFORCE.md).

## Quyền trong lúc chạy

Người nhận brief cần quyền xem đúng tenant, client, brand và campaign khi tạo run. PostgreSQL khóa hàng grant khi chèn run để giao dịch tạo run và giao dịch thu hồi quyền có thứ tự. Trigger chạy với quyền chủ migration, dùng search_path cố định. Hàm dành cho trigger thu hồi quyền EXECUTE của PUBLIC. Runtime tiếp tục chịu RLS. SQLite có trigger tương ứng cho môi trường thử.

Khi xóa grant hoặc thu hẹp phạm vi, DB đánh dấu run queued/running bị ảnh hưởng là failed với recipient_revoked ngay trong giao dịch đổi quyền. DB xóa lease, kết thúc attempt đang mở và ghi một audit event cho run. Thay đổi quyền bình luận hoặc quyết định vẫn cho phép xử lý nếu quyền xem còn hiệu lực. Cấp lại quyền cần tạo brief và run mới. Migration áp dụng chính sách này cho cả run đang dở ở v5.

Worker kiểm tra lại lease trước khi gửi và khóa hàng run trước khi lưu kết quả. Nếu thu hồi thắng giao dịch hoàn tất, kết quả về muộn bị bỏ. Nếu checkpoint hoặc snapshot đã commit trước, lịch sử được giữ và quyền đọc về sau do cổng duyệt thực thi. Có một khoảng giữa lần kiểm tra cuối và lúc gửi HTTP. Nếu yêu cầu đã đi hoặc vừa đi trong khoảng này, hệ thống không thể rút lại dữ liệu từ provider. Khoản dự phòng vẫn được giữ với trạng thái usage_unconfirmed. Quyết định hủy là quyết định cuối, kể cả khi worker khởi động lại.

## Phí, timeout và retry

Endpoint chiến lược trước đây trả HTTP 410 cho editor hợp lệ. Khi cần tạo nội dung, tạo brief và run rồi xử lý qua worker. API và migrate không được mount thư mục khóa. Worker đọc file bí mật khi thực sự dùng provider trả phí. Các cấu hình và lệnh chạy có trong [handoff](../HANDOFF.md).

Ngân sách là điều kiện cho phép gửi *từng attempt* trong một run. Worker khóa hàng và giữ chi phí dự kiến của input cùng output tối đa trước HTTP. Độ dài UTF-8, biên dự phòng và giá cấu hình theo triệu token chỉ cho một ước tính. Tokenizer, phần schema do provider xử lý, giá model, cache, làm tròn và phụ phí có thể làm hóa đơn khác số ghi nhận. Khi usage hợp lệ, worker ghi token và tính lại phí bằng bảng giá đã cấu hình. Khi mất phản hồi, số liệu bất thường hoặc thu hồi quyền giữa chừng, dự phòng có thể cao hoặc thấp hơn hóa đơn.

Timeout kết thúc việc chờ ở máy chạy worker. Provider có thể hoàn thành hoặc ghi phí sau đó. Lease và token ngăn hai worker ghi trùng checkpoint, nhưng thời gian máy lệch, worker chết, trả lời muộn hoặc mạng ngắt có thể dẫn tới gọi lại sau khi hết lease. Mỗi bước tối đa ba attempt, mỗi lượt cần dự phòng riêng. Tổng ngân sách của agency, đối soát hóa đơn, giá có phiên bản, cảnh báo sai lệch và khóa idempotency được nhà cung cấp bảo đảm vẫn là việc cần hoàn thiện trước khi cho phép chi tiền thật. Không dùng số ước tính này làm hard spending cap.

## Marketing Quality & Evidence Engine

Phiên bản marketing-evidence-1 phát hiện một tập cách diễn đạt tiếng Việt/Anh về giá, khuyến nghị, vị trí dẫn đầu và cam kết kết quả. Mỗi phát hiện giữ câu, mục nội dung, loại claim và ID nguồn. Chỉ câu trùng sau chuẩn hóa với một câu trong trích đoạn được dẫn mới mang nhãn source_quote. Thiếu khớp mang nhãn needs_evidence. Ví dụ “Giá phải chăng.” đi cùng nguồn chỉ ghi “Sổ có 80 trang.” vẫn cần người viết bổ sung bằng chứng. Kiểm tra con số và xác thực ID nguồn vẫn chạy.

Câu được trích chính xác có thể xuất phát từ nguồn sai, cũ hoặc thiếu ngữ cảnh. Câu diễn đạt lại, từ lóng và phủ định có thể bị bỏ sót hoặc bị gắn cờ thừa. Người QA độc lập xem tài liệu nguồn và bản nháp trong giao diện nội bộ trước khi chia sẻ. Khách chỉ nhận tiêu đề và preview của bản đã đóng phiên bản. Bước đánh giá kế tiếp cần bộ mẫu song ngữ do người gán nhãn, đo precision/recall theo loại claim và kiểm tra nguồn theo sản phẩm, địa bàn, thời hạn.

## Xác minh và phục hồi

Suite Workforce bao gồm thu hồi trong lúc provider đang chạy, cấp lại quyền, đổi scope, retry, bảo vệ giữa khách, QA và snapshot. CI chạy suite SQLite/PostgreSQL, năm đường nâng từ v1–v5, Compose với Chromium desktop/mobile và model local thật. Lệnh cụ thể nằm trong [workflow](../.github/workflows/ci.yml).

Trước khi nâng cấp, sao lưu DB và giữ SHA ứng dụng đi kèm. Nếu cần quay lại, dừng worker và API, phục hồi bản trước migration vào DB riêng, kiểm tra version, grant, snapshot và bản kê attempt trước khi đổi kết nối. Giữ API cũ cách ly khóa trả phí và vô hiệu hóa đường strategy. Giữ DB v6 để đối chiếu các thu hồi, bản giao và chi phí phát sinh sau điểm sao lưu. Phục hồi snapshot cũ có thể khôi phục quyền đã rút, cần áp lại các thu hồi trước khi mở dịch vụ.
