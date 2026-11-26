# G01 — Kế hoạch đến request của worker

Ba lượt chạy dưới PostgreSQL và Qwen 0.5B cục bộ, dữ liệu tổng hợp. Đây là mẫu kiểm tra việc chuyển đúng yêu cầu vào công việc. Số token lấy từ biên nhận inference, thời gian là thời gian thực của từng lượt trên máy Windows đang dùng chung. Cả ba lượt đạt `awaiting_qa`.

| Tác vụ | Run ID | Token vào / ra | Giây | Bản giao và bằng chứng |
|---|---|---:|---:|---|
| Tấm gỗ tiêu âm, chiến lược và đo lường | `45948667-44fe-4acb-910c-aef1ffeb1949` | 2.317 / 385 | 44,453 | [Bản giao](acoustic-panel/strategy/deliverable.md) · [3 request](acoustic-panel/strategy/commission-receipts.json) |
| Tấm gỗ tiêu âm, trang đích và SEO | `938c348e-d4a1-493a-8aac-0290c9bbbebd` | 1.545 / 264 | 11,375 | [Bản giao](acoustic-panel/landing/deliverable.md) · [3 request](acoustic-panel/landing/commission-receipts.json) |
| Bảo trì máy bơm, trang đặt lịch và SEO | `6c35d678-500a-4b68-84f1-7fb8181dd6f3` | 1.559 / 258 | 11,344 | [Bản giao](pump-service/landing/deliverable.md) · [3 request](pump-service/landing/commission-receipts.json) |

Tổng 5.421 token vào, 907 token ra; phí nhà cung cấp 0 USD. Chi phí điện, khấu hao, công người và mức chấp thuận nghiệp vụ chưa đo. Đây là bản chụp trong quá trình phát triển; artifact CI gắn với head và integration là nguồn để tái kiểm trước khi merge.

| Chromium | Sáng | Tối | Thời gian chọn chiến dịch đến khi hiển thị |
|---|---|---|---:|
| Desktop 1280 × 850 | [Ảnh](ui/workspace-1280.png) | [Ảnh](ui/workspace-1280-dark.png) | 250 ms |
| Tablet 820 × 1180 | [Ảnh](ui/workspace-820.png) | [Ảnh](ui/workspace-820-dark.png) | 172 ms |
| Mobile 390 × 844 | [Ảnh](ui/workspace-390.png) | [Ảnh](ui/workspace-390-dark.png) | 218 ms |

Browser đăng nhập bằng người quản lý agency tổng hợp, chọn campaign có run, dùng Enter ở cả sáu nút điều hướng, kiểm focus tới đúng vùng và reflow tại từng độ rộng. Hai theme sử dụng token hiện hữu. Thời gian là một quan sát cho mỗi viewport trên localhost. Chưa có đánh giá bằng trình đọc màn hình hoặc chuyên viên ngoài dự án. [Phiên trình duyệt](ui/sessions.json)
