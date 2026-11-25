# Campaign Center · Bằng chứng Chromium

Các ảnh chụp sau thao tác bằng bàn phím trên giao diện thật. Người dùng tổng hợp đã đăng nhập, chọn chiến dịch và chạy API qua HTTP cục bộ. Test so doanh thu và số tài sản trên giao diện với đúng phản hồi của API, mở nội dung của bản giao đầu tiên và kiểm tra reflow. Mỗi viewport có một lần đo từ khi nhấn nút tới khi nội dung hiển thị. [Điều kiện và thời gian đo](sessions.json) · [Kiểm thử có thể chạy lại](../../../tests/browser_campaign_lab.py)

| Viewport | Kế hoạch và sản xuất | Phễu và đối soát |
| --- | --- | --- |
| Desktop 1280 × 850 | [Sáng](campaign-1280.png) · [Tối](campaign-1280-dark.png) | [Sáng](measurement-1280.png) · [Tối](measurement-1280-dark.png) |
| Tablet 820 × 1180 | [Sáng](campaign-820.png) · [Tối](campaign-820-dark.png) | [Sáng](measurement-820.png) · [Tối](measurement-820-dark.png) |
| Mobile 390 × 844 | [Sáng](campaign-390.png) · [Tối](campaign-390-dark.png) | [Sáng](measurement-390.png) · [Tối](measurement-390-dark.png) |

Số tiền và các lần chấp nhận là dữ liệu fixture. Bài kiểm tra không đo khả năng sử dụng của chuyên viên hoặc thời gian làm việc thủ công.
