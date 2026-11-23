# Kế hoạch PR #6 · AI Director và workflow có đồ thị phụ thuộc

**Trạng thái:** Đề xuất để review kiến trúc. Điểm xuất phát là schema PostgreSQL v10 sau PR #5, commit `6657ef81364c941fe1fe13d1f92efcdd7ce334d0`. Mục tiêu đầu tiên là chứng minh một brief có thể tách thành hai nhánh công việc và chỉ được đưa sang QA khi đã nhận đủ đầu vào bắt buộc.

## Kịch bản nghiệm thu

Một brief ra mắt sản phẩm cần Research trước Strategy. Sau Strategy, Content viết bản nháp và SEO soạn tiêu đề cùng mô tả tìm kiếm. Hai bước này đều có thể sẵn sàng. Bước tổng hợp phải đợi cả hai hoàn tất. QA nhận một bản giao có thể truy ngược từng phần đến checkpoint và phiên bản kế hoạch đã sinh ra nó. Dùng hai khách A/B trong cùng agency và khách C ở agency khác để kiểm tra phân quyền theo cùng kịch bản của PR #5.

## Các hợp đồng cần chốt trong ADR kế tiếp

| Quyết định đề xuất | Điều kiện kiểm chứng |
| --- | --- |
| Director đề xuất các node và cạnh. Server cấp ID, đối chiếu danh sách skill được phép, kiểm tra giới hạn số node, cạnh và độ sâu. Kế hoạch được khóa phiên bản trước khi xếp việc. | Từ chối chu trình, node thiếu hoặc trùng, node cô lập ngoài đường đến đầu ra, cạnh khác run và skill thiếu quyền trước khi cấp lease hoặc giữ tiền. |
| Mỗi node thuộc đúng run và phạm vi tenant/client/brand/campaign. Cạnh nối hai node trong cùng phiên bản của run bằng khóa ngoại ghép. | Thử gắn node của B vào kế hoạch A phải thất bại tại database. Worker chỉ nhận payload của node đã được giao qua mailbox hiện có. |
| Node sẵn sàng khi mọi predecessor bắt buộc đã thành công. Checkpoint lưu theo node và revision. Bước tổng hợp đọc đầu vào theo thứ tự xác định của kế hoạch. | Hai request hoàn tất cùng một node chỉ tạo một checkpoint. Khi thiếu nhánh SEO, node tổng hợp và QA vẫn chờ. Một nhánh lỗi hết lượt thử làm rõ lý do các node phụ thuộc bị chặn. |
| Trong đợt đầu, tiếp tục dùng một lease đang mở trên mỗi run. Nhiều run vẫn được pool điều phối đồng thời. | Có thể kiểm tra điều kiện của đồ thị độc lập với việc thay đổi mức song song. Chỉ đề xuất mở nhiều lease trong cùng run sau kiểm thử tranh hạn mức và tạo bản giao duy nhất. |
| Mỗi attempt vẫn giữ ngân sách trước inference. Việc điều chỉnh kế hoạch sau khi chạy cần revision mới và quy tắc hủy các node chưa bắt đầu. PR đầu tiên chỉ nhận kế hoạch đã đóng băng. | Timeout sau khi gửi, thu hồi quyền, kết quả đến muộn, receipt trùng hoặc refund phải giữ đúng số dư run và agency. Receipt cho offer `unsent` trả 409. |

## Thứ tự triển khai

1. **ADR và test RED.** Ghi schema đầu ra của Director, người có quyền kích hoạt template, giới hạn đồ thị và chính sách khi nhánh thất bại. Tạo fixture đồ thị hình thoi, đồ thị lỗi và hai worker. Đo chi phí kiểm tra một kế hoạch trước khi giữ ngân sách.
2. **Schema và chuyển tiếp.** Thêm cách lưu phiên bản template, node, cạnh và checkpoint theo node. Chỉ bật biểu diễn mới cho run mới của agency thử nghiệm. Các run v10 đang có lease tiếp tục theo đường cũ tới khi kết thúc. Diễn tập nâng từ v10 có hold, receipt, snapshot và quyết định khách; so sánh dữ liệu trước–sau và chạy migration hai lần.
3. **Director và dispatcher.** Thay phần suy ra stage từ `len(run.checkpoints)` trong đường chạy mới. Chọn node sẵn sàng theo các cạnh, truyền đúng đầu ra của predecessor và dùng lease để chặn kết quả cũ. Giữ cơ chế chọn agency công bằng, LOGIN riêng của worker và khóa giữ ngân sách của v10. Chỉ tạo một deliverable khi đủ các đầu ra bắt buộc.
4. **Giao diện và bằng chứng.** Người vận hành nhìn thấy phiên bản workflow, node đang chờ, predecessor còn thiếu, số lượt và chi phí theo run. Kiểm tra desktop 1280 px và mobile 390 px. Trên Qwen local, ghi riêng lỗi lập kế hoạch, tỷ lệ đạt lần đầu, số lần sửa và token đã xác nhận.
5. **Điều kiện mở rộng.** CI phải giữ bộ hồi quy v10 và thêm kịch bản nhánh/join, thu hồi–cấp lại quyền giữa hai nhánh, crash sau inference, tranh 700/1.000 micro-USD, thứ tự checkpoint khác nhau và duyệt snapshot theo đúng digest/revision. Đo thời gian chờ giữa hai agency trước khi đặt mục tiêu tải.

## Chuyển về luồng tuyến tính

Tắt tạo run đồ thị mới; hoàn tất hoặc hủy có audit các run đồ thị còn mở và đối soát từng khoản giữ. Run mới sau chuyển đổi dùng template tuyến tính. Giữ nguyên phiên bản kế hoạch, checkpoint, ledger và snapshot đã phát sinh. Khi review PR triển khai, yêu cầu bằng chứng rằng một kết quả đến muộn sau khi tắt tính năng không thể tạo thêm bản giao.

Các điểm đối chiếu của v10 gồm [dispatcher](../app/pool_dispatch.py), [worker và checkpoint](../app/workforce_worker.py), [gateway](../app/workforce_gateway.py), [migration pool](../migrations/009_company_operations.sql) và [đối soát run](../migrations/010_run_reconciliation.sql).
