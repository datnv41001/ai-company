# Phiếu quyết định cho Product Owner · pilot nghiệp vụ bốn nhánh

**Đề xuất giữ ở bước chuẩn bị.** Mục tiêu là biết Sales hoặc Service có dùng bản giao ở revision 3 và việc đạt mức đó tốn bao nhiêu công. Còn thiếu người thực hiện, chủ vault, người giữ digest độc lập, quyền sử dụng hai brief mới, nguồn bản AI hợp lệ và trần kinh phí. Số work order đã cấp, practitioner tham gia và quyết định tiếp nhận trong vòng này đều bằng 0. [Quy trình chính thức official-department-pilot/2](../department-study/PILOT-ABCD/OFFICIAL.md)

## Số lượt cần bố trí và thời gian giả định

Hai brief mới gồm một RFQ và một yêu cầu đặt lịch dịch vụ. Mỗi brief có A viết tay, B control tất định, C nhận draft AI và D nhận cùng draft AI kèm QA sản xuất độc lập. Mỗi ô brief × nhánh là một việc. Ước lượng dưới đây dùng để xin lịch và ngân sách, chưa đo trên người thật.

| Vai trò | Số lượt và tài sản bàn giao | Phút giả định |
|---|---|---:|
| Marketing | 8 lượt, lưu bản đầu, phản hồi từng điểm sửa và nộp bản cuối | 8 × 45–75 = 360–600 |
| Reviewer nghiệp vụ độc lập | 8 lượt r1 trước biên tập + 8 lượt r3, ghi lý do đạt/trả và vị trí lỗi | 16 × 15–25 = 240–400 |
| Sales hoặc Service | 4 RFQ cho Sales, 4 lịch cho Service, mỗi việc một quyết định dùng/trả/từ chối trên r3 | 8 × 10–20 = 80–160 |
| QA sản xuất | 2 việc D, mỗi lần rà nguồn, nêu sửa đổi và ký nhận cặp r2/r3 | 2 × 20–35 = 40–70 |
| Custodian | Lập và đóng vault, kiểm quyền tài liệu, phát và nhận gói riêng, đối soát mọi phiếu | 60–90 + 8 × 10–20 = 140–250 |
| Người giữ digest độc lập | Đối chiếu cam kết thiết kế trước phát gói và khi đóng mẫu | 15–30 |

**Tổng 875–1.510 phút lao động**, tương ứng 14 giờ 35 phút đến 25 giờ 10 phút. Ước lượng bao gồm một vòng biên tập thông thường trong lượt Marketing. Giờ chờ theo lịch, tuyển người, mua quyền tư liệu, tạo bản AI, sửa quá vòng, sự cố và khôi phục chưa định lượng. Mỗi người dùng một alias, giữ một loại vai trò. Từng việc A/B/C có ba người khác nhau, D có bốn. C và D của cùng brief cần hai người chấm first-pass khác nhau. Roster là số lượt dự kiến. Số người thực tế do custodian đối soát tiếp xúc trước và tính độc lập.

## Các quyết định có thể ghi trước khi phát phiếu

| Chủ quyết định | Nội dung cần phê duyệt và giới hạn |
|---|---|
| Product Owner và chủ tư liệu | Chọn hai brief tổng hợp chưa phát, mục đích nội bộ và người được xem. Chứng từ phải cho phép dùng khi sản xuất, đưa cho người chấm và lưu theo thời hạn. Mỗi brief cần control và một draft AI có nguồn, revision/digest, quyền dùng và căn cứ chi phí. C và D dùng đúng cùng byte. Nếu cần sinh mới thì chờ quyền và ngân sách inference riêng. |
| Chủ ngân sách | Điền trần VND, đơn giá theo vai trò, quy tắc trả thời gian thực tế, khoản cho ca hỏng/rút và giới hạn rework. Tính tổng giờ × đơn giá từng vai trò, cộng compute, model, tools, phí tư liệu và overhead có chứng từ. Phân bổ một lần chi phí draft dùng chung giữa C/D. Đối soát các khoản với chứng từ. Các trường tiền đang là null. |
| Custodian + người giữ digest | Chọn vai trò độc lập, vault riêng được kiểm soát quyền, backup có kiểm thử, thời hạn lưu/xóa và quy trình phát riêng từng packet. Người thứ hai nắm digest trước khi giao việc. Bảng danh tính, alias, consent, mã assignment, tư liệu và phiếu gốc nằm ngoài Git. |
| Người tham gia | Trước khi nhận việc, đọc mục đích, dữ liệu sẽ thu, quyền truy cập, cách trả công, thời hạn lưu và kênh rút consent. Tự nguyện chọn tham gia từng vai trò. Cung cấp thông tin liên hệ riêng của custodian và mốc cuối còn có thể truy ra từng cá nhân trước khi đồng ý. [Mẫu lời mời và consent đang có](../department-study/PILOT-ABCD/INVITATION.md) |

Khi có yêu cầu rút, custodian dừng giao/chấm việc liên quan, đối chiếu phạm vi đồng ý còn lại và xử lý bản cá nhân, bản sao và chi phí theo điều khoản đã thông báo. Chỉ giữ trạng thái và số tổng hợp còn được phép. Công việc đã cấp tiếp tục nằm trong mẫu số ở mức tổng hợp được phép, ghi thiếu quyết định và lý do phù hợp. Khi đã ẩn danh không thể đảo ngược, thông báo trước phần dữ liệu không thể truy lại để gỡ. Mọi ca chưa rõ quyền hoặc có sự cố mù chuyển về custodian.

## Trước khi nhận một kết quả

1. Phát A trước khi người viết nhìn thấy draft cùng brief hoặc bố trí người riêng. Chọn tên tệp trung lập, kiểm metadata, nguồn lộ nhánh, nội dung quen thuộc. Reviewer và người nhận ghi phơi nhiễm/nghi ngờ riêng trước khi mở khóa. Hai người chấm C/D cùng brief nhận packet riêng. Nếu nhận ra cặp C/D, ghi incident cả hai và giữ cả hai trong mẫu số đã cấp.
2. Custodian chốt r1 cùng digest và phiếu first-pass trước bất cứ chỉnh sửa nào. B/C/D phải khớp draft đã khóa. Lưu r2 nếu sửa và trong mọi D. QA của D gắn nguồn/claim, công sửa, receipt và quyết định với r2→r3. Gắn ba phiếu cuối cùng đúng r3. Người nhận chỉ ra căn cứ đủ để xử lý hoặc lý do trả lại.
3. Với RFQ, đòi SKU, unit, lượng, điều kiện và thẩm quyền có nguồn. Với appointment, đòi đúng loại yêu cầu, phạm vi phục vụ, thông tin cần xác minh và người có quyền nhận. Việc khách giao dịch nằm ngoài phép đo pilot.
4. Báo cáo đủ các trạng thái completed, pending, failed, unblinded trên **tất cả việc đã cấp**. Công bố first-pass, final acceptance, lỗi, số ca chưa có phiếu, thời gian theo vai trò, chờ và chi phí do sửa/hỏng. Mẫu số chính thức vẫn bằng 0 trước khi cấp. Chi phí trên mỗi việc được nhận bằng tổng chi phí của mọi việc đã cấp chia số việc có quyết định dùng hợp lệ. Khi thiếu khoản hoặc mẫu số bằng 0, trả null. Một lượt trong mỗi ô chỉ giúp phát hiện lỗi quy trình.
