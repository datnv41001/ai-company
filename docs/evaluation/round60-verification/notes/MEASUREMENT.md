# Quyết định đo RFQ cho Khe Gọn

**Trạng thái hiện hành.** Khe Gọn có `primary_measurement=null`. `intake-funnel/2` đọc các event thuộc `approved_plan_lifetime`. Một visit, submission hoặc dòng CRM liên kết được với creative trong sandbox là bằng chứng vận hành. Tác động của hook với người mua còn chưa đo. [Đối chứng hai ca](../workforce-video/MEASUREMENT.md)

| Câu hỏi | Định nghĩa và chủ sở hữu |
| --- | --- |
| Lead đi từ đâu? | Attribution giữ ID distribution, phiên bản creative và landing, visit, submission, plan, scope và event time. Một lần gửi chỉ đóng góp một hồ sơ duy nhất theo quy tắc chống replay. |
| Sales đã xử lý được chưa? | Sales operations đối chiếu consent, SKU/đơn vị, số lượng và tính hợp lệ theo policy tại thời điểm, ghi đủ điều kiện, chấp nhận, báo giá và đơn hàng thành các sự kiện riêng. Yêu cầu dưới MOQ vẫn có thể là inquiry. |
| Hook thay đổi kết quả bao nhiêu? | Thiết kế đề xuất: phân bổ ngẫu nhiên ổn định trong 21 ngày, theo dõi 7 ngày kể từ từng assignment. Mẫu số là tất cả đơn vị đã phân bổ, tử số là các đơn vị có ít nhất một RFQ đủ điều kiện trong cửa sổ. Giữ cả đơn vị chưa đến landing. Khóa phân phối, quyền, định nghĩa và offer trước T0. |

Đường xây dựng đề xuất cho chủ KPI là một definition riêng có version (ví dụ `rfq.qualified_per_assigned`), owner, eligibility và nguồn event được duyệt. Tái sử dụng quy tắc thời điểm, scope và bằng chứng trong [measurement_integrity.py](../../../app/measurement_integrity.py). Hợp đồng appointment hiện chỉ nhận xác nhận/hoàn tất lịch. Việc mở rộng cần authority phát hành định nghĩa RFQ, assignment ledger, quan hệ giữa đơn vị phân bổ và qualification thực sự, cách loại trùng và xử lý mất liên kết, sửa/hủy hoặc xác nhận muộn. Thứ tự triển khai là duyệt định nghĩa, xây kiểm thử thời gian/tenant/replay, rồi xin quyền pilot với quy tắc dừng và cỡ mẫu. Cả KPI mới và phân bổ 21+7 hiện ở mức đề xuất.
