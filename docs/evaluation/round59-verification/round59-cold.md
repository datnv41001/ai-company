# Kiểm tra bàn giao độc lập từ Git objects

Người đọc kỹ thuật AI khởi đầu không có lịch sử chat, chỉ đọc cây Git tại `01295a7eaf8a4650c417df4f9dbcba751addc7c0` qua broker đọc tệp. [Nhật ký đọc](cold-reader-paths.jsonl). Người vận hành chạy các lệnh theo yêu cầu của người đọc trên source export sạch tại cùng SHA. [Lệnh và HTTP](round59-operator.json) · [JUnit PostgreSQL](junit.zip).

| Mục bàn giao | Kết quả của người đọc |
| --- | --- |
| Người dùng và quyết định | Xác định owner/agency, người dựng và QA; cần quyết định của doanh nghiệp theo brief/revision để tính một accepted work unit. |
| Mốc phiên bản | Phân biệt main sau #58, tree PR #59 và bản AI đã đánh giá trước khi sửa hình/ghi chú giá. |
| Truy nguyên giao việc | Lần theo brief Luồng Rõ, run `c4e496d3-599a-4f75-be05-4e8340003bec`, hai worker attempts và tài liệu chờ QA. Tìm đúng hook được sửa, timeline, VTT và cách đối chiếu SHA-256 của output/render/decode. |
| Giới hạn hành trình | Phân biệt Studio v2→v3 với raw→reviewed v1→v2 của worker. Lượt diễn tập Studio có 1 visit, 1 request, 0 lịch xác nhận và chưa giao người xử lý. Hai phép thử dùng cùng tình huống; chưa có một trace duy nhất nối run này tới request trên form. |
| Chạy dev | Operator khởi tạo từ archive SHA-256 `286378baf23e673241dc247b059fd44e1b15a234e77730fd8466540b58c3e373`. Trang chính, docs và health trả HTTP 200, production_ready=false. Với hai tệp test do người đọc chọn, SQLite 4 pass/4 skip trong 2,98 giây; PostgreSQL role ứng dụng hạn chế, v26, 8 pass trong 65,79 giây. |
| Quay lui | Disable chặn run mới, revoke dừng quyền đang dùng. Khi lùi binary, phục hồi archive vào database riêng, giữ bản hiện hành và đối chiếu giao dịch phát sinh sau backup. |
| Bước tiếp theo | Thu consent cho một brief mới, đo phút sửa của editor và yêu cầu người mua nói rõ ai xác nhận lịch. Commercial GA và production còn NO-GO. |
| Chẩn đoán v16 | Người đọc tìm đúng thứ tự kiểm tra và hướng dẫn restore pre-016 khi database có marker 016 nhưng thiếu 015. Bài diễn tập riêng xác nhận ledger, lease và snapshot được bảo toàn. |

Người đọc xác nhận đủ bằng chứng diễn tập kỹ thuật. Người vận hành đã dừng dịch vụ kiểm tra và dọn database thử. Chưa có phiếu người hành nghề hoặc quyết định nghiệm thu của khách hàng thật.
