# ADR-007 · QA theo phiên bản nội dung

Áp dụng từ schema 7. Nền tảng là commit main `47cdc585c46e123015cb0e1842b71c4dcfe6693e`. Hai trường hợp thúc đẩy thay đổi là cảnh báo “Giá phải chăng” còn sót sau khi sửa và người QA duyệt từ trang đã mở trước khi biên tập viên thay nội dung.

## Bản mà người QA nhìn thấy

Mã băm nội dung là SHA-256 của JSON UTF-8 gồm hai khóa `preview`, `title`, được sắp xếp, dùng dấu phân cách compact và giữ nguyên Unicode. Khoảng trắng, dấu tiếng Việt, ngắt dòng và tiêu đề đều tham gia băm. API dùng cùng hàm cho báo cáo, quyết định và snapshot. Bản nội bộ chỉ có metadata được xét với preview rỗng. Chia sẻ vẫn yêu cầu preview có nội dung. Hai lần lưu chính xác cùng cặp tiêu đề/preview có cùng digest.

Schema 8 bổ sung số lần lưu `qa_revision` bắt đầu ở 1 cho mỗi tài liệu. PATCH bản nháp tăng số này dưới khóa của tài liệu, kể cả khi editor lưu nội dung giống hệt. Đánh giá lại và gửi QA giữ nguyên số lần lưu. Báo cáo và audit giữ số tương ứng. Khi QA duyệt, server ghi `qa_approved_revision` cùng digest. Thử trên commit 4181a92 cho thấy trang A cũ nhận HTTP 200 sau A → B → A. Schema 8 dùng cả hai giá trị của bản đã xem để phát hiện lượt lưu xen giữa.

Schema 7 thêm `deliverables.qa_evidence` và `qa_approved_digest`; cả hai nằm trên hàng bản làm việc có FORCE RLS. Tách cột giúp phân biệt dữ liệu backend với JSON tùy ý đã tồn tại trước v7. Chỉ mục một phần trên liên kết từ run đến deliverable giới hạn chi phí tra nguồn. Findings được lưu cùng nhau ở JSON vì màn hình QA đọc trọn báo cáo cho một bản. Lịch sử báo cáo nằm ở các sự kiện `deliverable.qa_evaluated` của đúng tenant và subject; mỗi sự kiện giữ digest, ruleset, thời điểm và findings. Audit quyết định ghi người duyệt, quyết định, digest và ruleset. Admin tra lại bằng GET `.../audit?subject_id=<deliverable_id>&offset=0`, mỗi trang tối đa 100 sự kiện. Checkpoint cũ giữ nguyên.

## Nguồn, kết quả và giới hạn

Khi worker tạo bản đầu hoặc editor lưu bản sửa, giao dịch quét toàn bộ tiêu đề và preview. Bộ quy tắc chạy cục bộ. Backend tìm Workforce run qua tenant, campaign và khóa ngoại deliverable. Các mã nguồn đối chiếu là hợp của những ID mà các checkpoint chuyên môn đã dẫn và có trong registry đóng băng của run. Danh sách này cho biết phạm vi tìm kiếm. Editor có thể thêm một câu mới vào bản sửa, nhưng không thể thêm nguồn đáng tin bằng JSON gửi lên API.

Mỗi finding ghi câu, trường, loại claim, các nguồn được xét, nguồn có câu trùng, và trạng thái. `source_quote` chỉ biểu thị câu trùng sau chuẩn hóa. Nguồn có thể sai, lỗi thời hoặc có liên quan đến sản phẩm khác. Phủ định có thể bị gắn cờ, diễn đạt lại có thể bị bỏ sót. `source_unavailable` vẫn hiển thị claim phát hiện được cùng cảnh báo thiếu nguồn. Số liệu trong checkpoint mô tả đầu ra lịch sử của model. QA độc lập chịu trách nhiệm đối chiếu ngữ cảnh và tính đúng đắn.

## Hợp đồng API nội bộ

1. Đọc bản làm việc qua GET deliverable. Trường top-level `qa_evidence` là báo cáo do backend sở hữu. Khi báo cáo thiếu số lần lưu hiện tại hoặc là null, giao diện hiển thị chưa đánh giá và cho phép editor/admin thực hiện POST `.../assessment`, rồi tải lại bản đã lưu.
2. Lưu tiêu đề và preview qua PATCH `.../draft`. Cùng giao dịch, server đánh giá lại, hủy quyết định nội bộ cũ và xử lý yêu cầu khách đang chờ theo chính sách hiện có. Nút Gửi QA bị khóa khi tiêu đề hoặc preview có thay đổi chưa lưu. Lưu xong, giao diện tải lại bản ghi trước khi cho gửi QA.
3. POST `.../review` bắt buộc `expected_qa_revision` (số nguyên dương) và `expected_content_digest` cho cả approved và rejected. Client giữ cả số lần lưu và digest từ lúc hiển thị nội dung. Thiếu hoặc sai định dạng trả 422. Số lần lưu cũ, digest sai hoặc báo cáo chưa hợp lệ trả 412. Sai trạng thái trả 409. Cả đường sửa, duyệt và chia sẻ khóa theo cùng document. Số lần lưu và digest đã duyệt được ghi cùng quyết định. Khi chia sẻ, server tính lại digest rồi so với báo cáo và quyết định trước khi thêm snapshot.
4. Snapshot và sự kiện phản hồi của khách tiếp tục dùng quyền và định dạng cũ. Nguồn, checkpoint, report và lịch sử nội bộ chỉ đi qua các API nội bộ có phân quyền.

## Nâng cấp, nghiệm thu và phục hồi

Dừng API và worker của phiên bản trước, sao lưu DB phát triển, chạy migration trước khi khởi động phiên bản mới. Migration không backfill từ JSON của editor. Bản approved trước v8 cần tạo báo cáo, đọc lại và được QA độc lập duyệt với số lần lưu và digest trước lần chia sẻ kế tiếp. Bản đã giao vẫn mở được với version, preview và digest ban đầu. SQLite bổ sung cột lúc khởi động đối với file cũ.

[Workflow nghiệm thu](../.github/workflows/ci.yml) chạy bảy đường nâng DB v1–v7, lặp migration, test vai trò, thử các giao dịch cạnh tranh, giao diện desktop/mobile và Qwen thật trong Compose. Khi xem giao diện, chọn **Soạn và bàn giao cho khách** và một bản làm việc. Khu **Kiểm tra phiên bản đang xem** hiển thị đầu của SHA-256, ruleset, trạng thái nguồn và từng câu cần đối chiếu. Khi gõ sửa, báo cáo đã lưu được ẩn. Sau khi lưu, màn hình tải lại bản và kết quả của server.

Nếu cần rollback, dừng các tiến trình v8, giữ bản sao DB v8 để đối chiếu audit và phục hồi bản mã tương ứng cùng backup trước migration vào DB riêng. Kiểm tra các quyền bị thu hồi, quyết định và snapshot phát sinh sau mốc backup trước khi cho phép tiếp tục nội bộ. Các bản trước v8 dùng hợp đồng duyệt cũ; chỉ mở lại luồng duyệt khi đã chấp nhận rủi ro này hoặc đã có bản sửa tương thích.

## Đề xuất từ Business Profile C0

Khi tích hợp phiên bản Workforce mới, QA/share phải kiểm đồng thời revision/digest nội dung đã duyệt và quyền dùng từng claim/source ở thời điểm giao dịch. C0 đề xuất authority guard, immutable source revision và lịch sử invalidation. Mã nghiệp vụ hiện tại sẽ chỉ nhận thay đổi sau khi C1/C3 được review. [Thứ tự thu hồi, QA và share](business-profile/C1-PLAN.md#thu-hồi-qa-và-share)
