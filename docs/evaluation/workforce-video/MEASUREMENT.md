# Đọc lại intake và khóa giả thuyết creative

**Đối tượng sử dụng** là Marketing lead so sánh hai hook và Sales/Service phụ trách xử lý form. Phần đọc lại áp dụng cho hai packet kỹ thuật đã lưu tại #58. Mỗi packet ghi đúng một hành trình tổng hợp trên landing đã duyệt. Với packet có nhiều hành trình, xuất từng đường đi và báo cáo theo phạm vi tương ứng.

| Sự kiện trong journal | Khe Gọn | Luồng Rõ |
| --- | --- | --- |
| Visit có cùng plan, package, revision và digest tệp | 1 | 1 |
| Inquiry → Qualified RFQ → Sales acceptance → Quote → Order | 1 → 0 → 0 → 0 → 0 | Không áp dụng |
| Doanh thu đã xác nhận trong sandbox | 0 đồng | Không áp dụng |
| Đề nghị khảo sát → Lịch có xác nhận | Không áp dụng | 1 → 0 |
| Người được giao tại thời điểm submit | Chưa có | Chưa có |
| KPI đã duyệt | Chưa có primary KPI; funnel tính theo vòng đời kế hoạch | Hợp đồng appointment, định nghĩa và cửa sổ trong receipt |
| Tác động của việc phân bổ người xem cho creative A hoặc B | Chưa đo | Chưa đo |

Công cụ ghép visit/submission bằng ID journal; đối chiếu kế hoạch, bản landing, consent, phiên và hợp đồng đã ký. Sau đó dùng lại `business_intake.funnel` và `measurement_integrity.evaluate`. Một event nhận form và tên người được phân công đều chưa đủ để kết luận người nhận chấp thuận sử dụng bản giao. [Số liệu, digest và receipt](measurement-readback.json) · [Mã đọc lại](../../../tests/evaluation/department/creative_measurement.py)

Từ gốc checkout, chạy `python -m pytest -q tests/test_creative_measurement_readback.py`. Để in lại báo cáo JSON chạy `python -m tests.evaluation.department.creative_measurement docs/evaluation/campaign-production-review/index-tray/evidence.json docs/evaluation/campaign-production-review/receipt-map/evidence.json`.

## Thiết kế đề xuất đã khóa cho sandbox · chưa mở tuyển hoặc chạy quảng cáo

Đã chạy lại cùng phép đối chiếu trên hai package CTA mới. Kết quả mỗi hành trình giữ đúng các tầng ở bảng trên. Receipt, digest và cửa sổ của lượt mới ở [bản đọc lại sau biên tập](aligned-readback.json).

**Câu hỏi cụ thể.** Với cùng một offer Khe Gọn, thay duy nhất câu mở đầu có làm thay đổi tỷ lệ người được phân bổ phát sinh ít nhất một RFQ đủ điều kiện không? Dùng cùng hình, CTA, giá/MOQ, phần sau video, landing, đối tượng đủ điều kiện và quyền xử lý. So nhiều concept khác nhau là một khảo sát sáng tạo riêng.

| Thành phần | Quy tắc đề xuất |
| --- | --- |
| Đơn vị và cửa sổ | Mỗi người đủ điều kiện và có consent có một ID giả danh, một assignment ngẫu nhiên 1:1 cố định. Tuyển trong 21 ngày liên tục từ T0 UTC đã phê duyệt. Theo dõi mỗi người 7 × 24 giờ sau assignment. Khóa dữ liệu sau khi người cuối đã đủ cửa sổ. |
| Mẫu số, tử số | Mẫu số là toàn bộ ID đã được phân bổ ở từng nhánh, kể cả người không mở landing. Tử số là số ID đó có ít nhất một RFQ đủ điều kiện trong cửa sổ. Đếm một lần mỗi ID. Report cả assignment, impression/exposure, visit, inquiry và RFQ có bằng chứng. Mất khả năng liên kết outcome là thiếu dữ liệu, cần báo biên trên/dưới và xem xét dừng. |
| Attribution | Journal phân bổ nối với revision/digest creative, landing cùng scope và dấu thời gian. Loại test traffic theo quy tắc khóa trước. Không đổi nhánh sau render/click. Nhân viên xác nhận Sales, quote, order, revenue và hủy/refund ở dãy vận hành riêng. Tỷ lệ xác nhận lịch trong số người đã gửi đề nghị cảnh báo tắc nghẽn vận hành. |
| Cỡ mẫu giả định | Để lập kế hoạch, nếu tỷ lệ nền 10%, thay đổi tối thiểu 3 điểm phần trăm, kiểm định hai phía α=0,05, power 80%, phân bổ đều, xấp xỉ chuẩn hai tỷ lệ độc lập cho 1.774 người/nhánh. 10% là giả định thiết kế. Nếu traffic, clustering hoặc tỷ lệ liên kết thực khác giả định, phải khóa thiết kế và tính lại trước khi chạy. |
| Điểm dừng và ngân sách | Sandbox dùng dữ liệu tổng hợp, chi media và dịch vụ ngoài được phép 0 đồng. Thử thật cần T0, quota traffic, trần chi và consent riêng. Dừng tuyển khi đủ cỡ mẫu mỗi nhánh hoặc hết 21 ngày, chờ cửa sổ theo dõi rồi phân tích một lần. Thiếu mẫu thì kết luận chưa đủ dữ liệu. Dừng ngay khi scope/consent/offer sai hoặc vượt trần; lưu lý do. |
| Điều kiện kết luận | Báo tỷ lệ từng nhánh, chênh lệch tuyệt đối và khoảng tin cậy 95%, tỷ lệ thiếu liên kết/exposure và biến cố ngoại lệ. Giữ kết quả âm hoặc không xác định. Không suy ra causal lift từ intake-funnel/2, CTR hay doanh thu của một case sandbox. |

Hiện chưa có journal phân bổ người xem, mẫu đủ hoặc ngân sách quảng cáo. Không có connector thật được gọi trong phép đọc lại. [Thư mời và điều kiện pilot A/B/C/D nghiệp vụ](../department-study/PILOT-ABCD/OFFICIAL.md)
