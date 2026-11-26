# Bàn giao CTA và tiếp nhận yêu cầu

Người biên tập, Sales và Service có thể đọc cùng một bước tiếp theo trên nội dung theo kênh, ảnh và trang đích. Tất cả đầu vào, lượt gửi và người duyệt trong diễn tập là dữ liệu tổng hợp. Ảnh hình học là artwork thử kỹ thuật.

| Hồ sơ | Mở bản giao | Sau khi gửi trong Studio |
| --- | --- | --- |
| Luồng Rõ | [Copy theo kênh](receipt-map/channel.json) · [ảnh dọc](receipt-map/portrait.png) · [landing](receipt-map/landing.html) · [storyboard v2](../campaign-production-review/receipt-map/edit.json) | Cả bốn dùng **Gửi đề nghị khảo sát**. Form yêu cầu địa điểm, ca nhận hàng và consent. Lượt gửi ghi `requested`, chưa có người nhận và chưa có lịch xác nhận. [Biên nhận](receipt-map/evidence.json) |
| Khe Gọn | [Copy theo kênh](index-tray/channel.json) · [ảnh dọc](index-tray/portrait.png) · [landing](index-tray/landing.html) | Form giải thích có thể gửi nhu cầu dưới mức tối thiểu để được tư vấn. Khách nhập 3 hộp khi MOQ là 5. Có 1 inquiry, 0 qualified RFQ, 0 lần Sales tiếp nhận, 0 báo giá, 0 đơn và 0 doanh thu đã xác nhận. [Biên nhận](index-tray/evidence.json) |

## Đường sửa một bản đã duyệt

Phép thử riêng tái hiện CTA “Đặt lịch” của phiên bản trước trên cùng một tài liệu, qua API Studio. Editor sửa từ revision 2 sang 3. API từ chối lượt duyệt cũ bằng HTTP 412. Người duyệt độc lập trong sandbox ký lại các nhóm và từng package. Ảnh và HTML mới mang version 2 và digest mới. Kiểm tra lại file cũ và snapshot khách cũ vẫn khớp từng byte và digest. Form cũ bị chặn dùng tiếp, form hiện hành ghi nhận một đề nghị khảo sát. [Hai revision với ID và quyết định QA](revision.json)

Hai bộ asset ở bảng trên được xuất từ một lượt diễn tập khác, sử dụng cùng brief. Bằng chứng trình duyệt cũng có plan và package digest của lượt dựng riêng. Trên checkout khác, xác minh từng liên kết bằng ID và digest trong cùng lượt. [Bản đối chứng #58 được giữ nguyên](../campaign-production-review/README.md)

## Nghiệm thu trong Chromium

Ở 1280, 820 và 390 px, kiểm tiêu đề form, metadata, liên kết CTA, nút gửi, trường bắt buộc, consent, điều hướng bằng bàn phím và chiều rộng trang. Ở 390 px, gửi form trong iframe Studio và kiểm thông báo của biên nhận. File HTML mở riêng chỉ xem được. Chromium 158.0.8127.88 chạy trên Windows local. Thời gian 193,47 giây gồm khởi tạo hai hành trình, phần API, trình duyệt và thu bằng chứng. Thời gian người hành nghề làm việc và hiệu quả quảng cáo chưa đo.

| | Desktop | Tablet | Mobile | Trạng thái sau gửi trên mobile |
| --- | --- | --- | --- | --- |
| Luồng Rõ | [1280](receipt-map/screens/intake-1280.png) | [820](receipt-map/screens/intake-820.png) | [390](receipt-map/screens/intake-390.png) | [Sáng](receipt-map/screens/form-390.png) · [tối](receipt-map/screens/form-390-dark.png) · [kích thước và decoder](receipt-map/screens/sessions.json) |
| Khe Gọn | [1280](index-tray/screens/intake-1280.png) | [820](index-tray/screens/intake-820.png) | [390](index-tray/screens/intake-390.png) | [Sáng](index-tray/screens/form-390.png) · [tối](index-tray/screens/form-390-dark.png) · [kích thước và decoder](index-tray/screens/sessions.json) |

## Tái lập

Trong môi trường dev của repo với Chromium đã cấu hình, chạy từ thư mục gốc:

```sh
python -m pytest -q tests/test_appointment_action_revision.py tests/test_service_landing_edit.py
python -m pytest -q tests/test_production_studios.py -k "index-tray or receipt-map"
python -m pytest -q tests/browser_production_studios.py -k "index-tray or receipt-map"
```

Để giữ biên nhận mới, đặt `AMC_CTA_REVISION_EVIDENCE`, `AMC_PRODUCTION_EVIDENCE`, `AMC_INTAKE_EVIDENCE`, `AMC_CHANNEL_EVIDENCE` và `AMC_PRODUCTION_SCREENS` vào năm thư mục đầu ra mới. Gói có digest đã giao được giữ lại cho lần đối chiếu. Phép thử này bắt đầu với nguồn Studio đã có; nó chứng minh biên tập, QA, render, submit và readback. Việc điều phối role WF-08 có bằng chứng riêng.

Người phản biện có thể yêu cầu người mua đọc form, nói rõ tại thời điểm nào nhận được lịch và liệu gửi nhu cầu 3 hộp đã tạo báo giá hay chưa. Chi phí đầy đủ và số việc được doanh nghiệp chấp nhận cần đo với người hành nghề theo protocol riêng.
