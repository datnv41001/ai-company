# Một reviewer và phản biện chéo trên cùng ngân sách

Trong tám ca mới, thêm một chuyên gia cùng checkpoint chưa cải thiện số ca đúng đồng thời kết luận, nguồn, lý do và hành động. Qwen đạt 0/8 ở cả hai nhánh. SmolLM2 đạt 1/8 khi một reviewer tự đối chiếu và 0/8 khi dùng hai reviewer. Ca J1 duy nhất đạt trọn bốn tiêu chí ở nhánh SmolLM2 một người là phép tính chi phí trên mỗi lead đủ điều kiện.

| Checkpoint / người quyết định | Đúng cả bốn | Verdict | Nguồn | Lý do | Hành động | Token vào / ra theo nhánh |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen2.5 1.5B · MK-022 (solo) | 0/8 | 3 | 7 | 1 | 4 | 3726 / 905 |
| Qwen2.5 1.5B · MK-052 (pair) | 0/8 | 3 | 7 | 1 | 4 | 3732 / 905 |
| SmolLM2 1.7B · MK-022 (solo) | 1/8 | 4 | 6 | 4 | 3 | 4140 / 848 |
| SmolLM2 1.7B · MK-052 (pair) | 0/8 | 3 | 7 | 4 | 3 | 4145 / 785 |

## Ma trận năng lực theo người quyết định và checkpoint

Ô ghi số ca đạt trọn bốn tiêu chí trên số ca có nhãn năng lực đó. Một ca có thể có nhiều nhãn. Mỗi năng lực mới chỉ được thử trên tình huống hữu hạn.

| Chuyên môn | MK-022 Qwen | MK-052 Qwen | MK-022 SmolLM2 | MK-052 SmolLM2 |
| --- | --- | --- | --- | --- |
| Actionable repair | 0/2 | 0/2 | 1/2 | 0/2 |
| Architecture | 0/1 | 0/1 | 0/1 | 0/1 |
| Code logic | 0/1 | 0/1 | 0/1 | 0/1 |
| Marketing reasoning | 0/3 | 0/3 | 1/3 | 0/3 |
| Regression analysis | 0/2 | 0/2 | 0/2 | 0/2 |
| Security | 0/1 | 0/1 | 0/1 | 0/1 |
| Semantic contradiction | 0/2 | 0/2 | 0/2 | 0/2 |
| Source attribution | 0/4 | 0/4 | 0/4 | 0/4 |

## Chi phí thực và giới hạn

Đã chạy 20 invocation ký bởi adapter, hai reviewer ID, hai checkpoint, một bộ seed, 16.173 token thực và 0 USD phí API. Mỗi checkpoint có mười call vật lý; hai nhánh cùng dùng lại hai call vòng đầu. Thống kê token theo nhánh tính cả phần dùng chung. Phần model local trong runner đo 248 giây cho Qwen và 229 giây cho SmolLM2. Working set cực đại lần lượt 1,29 GiB và 2,55 GiB. Số đo VRAM theo tiến trình không có trên host này.

Máy Windows có 15,83 GiB RAM, tại lúc chọn model còn 2,32 GiB khả dụng. Đã dùng tuần tự hai checkpoint đã ghim sẵn cùng runtime 4.096 token. Chưa chạy 7B trên máy đang phục vụ các bài Chromium và PostgreSQL. Người xây dựng fixture đăng ký nhãn trước inference; đợt này chưa có đối chứng do người làm Marketing chấm. Ca security chỉ hỏi quyền nghiệp vụ từ một chính sách tổng hợp; kết quả không xác lập năng lực kiểm toán an ninh.

Giữ HOLD đối với mở rộng reviewer, đọc source thực và giao quyền nghiệm thu. Cần đánh giá ứng viên suy luận mạnh hơn trên máy có đủ bộ nhớ hoặc ngân sách đã được chấp thuận và bộ ca chấm độc lập. [Phương pháp và lệnh replay](RUNBOOK.md) · [Chi tiết đáp án và điểm](results.json) · [Các SHA-256 của archive](release.json) · [Thiết kế nghiên cứu giới hạn](DISCOVERY.md).
