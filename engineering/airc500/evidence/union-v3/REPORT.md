# Kết quả thí nghiệm verifier-union

Trên 24 nghĩa vụ Marketing tổng hợp mới, bộ so sánh định kiểu giữ đủ **6 lỗi và 6 ca sạch** ở cả hai seed, trong mọi nhánh. Hội đồng đầy đủ của Qwen 0.5B chưa bổ sung được kết luận ngữ nghĩa đã xác minh nào. Cả 12 nghĩa vụ ngữ nghĩa còn mở ở nhánh này. Nhánh chạy hai lần cùng một reviewer xác minh thêm một ca ngữ nghĩa sạch ở seed 19. Mọi nhánh giữ quyết định **inconclusive**. Không có bản sửa hoàn chỉnh do AI tự viết.

Bốn ID thực sự tham gia 40 lượt có receipt, gồm MK-022, MK-052, MK-053 và AR-002. Cả ba checkpoint chạy local. Tổng ngân sách đã dùng là **52.855 token, 0 USD phí API**. Một lần xin slot trước khi chạy Qwen 1.5B bị từ chối khi máy còn đủ hai process. Journal ghi 0 dispatch và 0 token cho lần đó. [Checkpoint capacity](no-capacity-preflight.json).

Git fixture `520a835f0809734518d59e58ae936a16ca684825` → `44bf5f0db42652506403cc40a76ca427467e8762`. Enrollment được ghi trước inference tại `030e8730c357b8b7ab659b9bd54c04241d53098d00eaa5cab1264efc34997537`. Index gói đã xác minh là `ed3b34db683d7c710bba58799cfab8367f767552ab488bc770500536bfbdd1b3`. [Enrollment](enrollment.json) · [Kết quả máy đọc được](metrics.json) · [Chứng chỉ verifier](verification.json).

## Bộ nhớ, throughput và thời gian

| Model | Lượt đạt / lỗi sau dispatch | Token input / output | Tổng giây giai đoạn inference | Token sinh / giây của pha đo | Peak working set (MiB) | Peak VRAM toàn GPU (MiB) |
|---|---:|---:|---:|---:|---:|---:|
| Qwen2.5-0.5B-Instruct-Q4_K_M | 32 / 0 | 33138 / 8392 | 543.6 | 15.4 | 879.5 | 1220 |
| Qwen2.5-1.5B-Instruct-Q4_K_M | 4 / 0 | 4096 / 1256 | 177.2 | 7.1 | 1914.6 | 961 |
| SmolLM2-1.7B-Instruct-Q4_K_M | 4 / 0 | 4540 / 1433 | 316.1 | 4.5 | 2883.1 | 1220 |

Context cấu hình 4.096 token. Model share tối đa hai slot của cùng máy. Peak working set lấy từ process Windows; VRAM là số đo toàn board được lấy mẫu trong mỗi arm. NVIDIA driver không cung cấp số byte GPU riêng cho PID của các runtime này. Thời gian pha đo bao gồm admission, dispatch, model và ghi nhận, từ khi server sẵn sàng. Archive lưu latency theo receipt và trần output của từng phép so. [Qwen 0.5B](q05.json.gz) · [Qwen 1.5B](q15.json.gz) · [SmolLM2 1.7B](smol.json.gz).

## So sánh trên cùng nghĩa vụ

Mỗi seed có bốn ca ngữ nghĩa lỗi, bốn ca sạch, bốn ca nguồn không đủ. Cột TP/FP thô chỉ đếm lỗi đúng trên bốn ca lỗi và cờ nhầm trên bốn ca sạch. Cột cờ thiếu nguồn tách các tuyên bố lỗi chưa thể kiểm chứng. Verdict mâu thuẫn giữa nhiều lượt được chấm abstain. Ba cột lý do, nguồn, thao tác độc lập; thao tác đúng chưa chứng minh toàn bộ đề xuất hợp lệ. Số phủ cuối là kết quả của union trên toàn bộ 24 nghĩa vụ.

| Model | Seed | Cấu hình | Call | TP / FP thô | Cờ trên ca thiếu nguồn | Abstain thô | Đúng lý do / 12 | Trỏ đúng nguồn / 12 | Đúng thao tác / 4 lỗi | Lỗi / sạch / còn mở đã kiểm | Token | Giây |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| q05 | 19 | Mù cơ sở | 2 | 4 / 3 | 3 | 0 | 5 | 2 | 0 | 6 / 6 / 12 | 2681 | 35.0 |
| q05 | 19 | Một ID, hai lượt | 4 | 1 / 0 | 0 | 9 | 1 | 1 | 0 | 6 / 7 / 11 | 5371 | 77.0 |
| q05 | 19 | Hai ID đối chứng | 4 | 0 / 0 | 0 | 10 | 1 | 0 | 0 | 6 / 6 / 12 | 5330 | 72.1 |
| q05 | 19 | Đổi chỉ dẫn | 2 | 1 / 1 | 1 | 0 | 4 | 0 | 0 | 6 / 6 / 12 | 2696 | 40.5 |
| q05 | 19 | Chia nhỏ batch | 4 | 1 / 4 | 3 | 0 | 3 | 1 | 0 | 6 / 6 / 12 | 2873 | 42.0 |
| q05 | 19 | Thêm cross | 6 | 0 / 0 | 0 | 10 | 1 | 0 | 0 | 6 / 6 / 12 | 8833 | 113.9 |
| q05 | 19 | Thêm trọng tài | 8 | 0 / 0 | 0 | 10 | 1 | 0 | 0 | 6 / 6 / 12 | 12715 | 158.3 |
| q05 | 47 | Mù cơ sở | 2 | 0 / 0 | 0 | 0 | 4 | 0 | 0 | 6 / 6 / 12 | 2629 | 43.1 |
| q05 | 47 | Một ID, hai lượt | 4 | 0 / 0 | 0 | 0 | 4 | 0 | 0 | 6 / 6 / 12 | 5324 | 82.9 |
| q05 | 47 | Hai ID đối chứng | 4 | 0 / 0 | 0 | 3 | 2 | 0 | 0 | 6 / 6 / 12 | 5271 | 80.1 |
| q05 | 47 | Đổi chỉ dẫn | 2 | 0 / 1 | 0 | 0 | 3 | 1 | 0 | 6 / 6 / 12 | 2715 | 27.5 |
| q05 | 47 | Chia nhỏ batch | 4 | 1 / 1 | 0 | 0 | 3 | 2 | 1 | 6 / 6 / 12 | 2864 | 41.3 |
| q05 | 47 | Thêm cross | 6 | 0 / 0 | 0 | 3 | 2 | 0 | 0 | 6 / 6 / 12 | 8593 | 117.1 |
| q05 | 47 | Thêm trọng tài | 8 | 0 / 0 | 0 | 3 | 2 | 0 | 0 | 6 / 6 / 12 | 12282 | 146.8 |
| q15 | 19 | Mù cơ sở | 2 | 1 / 3 | 2 | 4 | 5 | 5 | 3 | 6 / 6 / 12 | 2796 | 104.5 |
| q15 | 47 | Mù cơ sở | 2 | 2 / 4 | 4 | 2 | 6 | 6 | 3 | 6 / 6 / 12 | 2556 | 72.4 |
| smol | 19 | Mù cơ sở | 2 | 1 / 4 | 2 | 5 | 3 | 5 | 1 | 6 / 6 / 12 | 2971 | 150.9 |
| smol | 47 | Mù cơ sở | 2 | 1 / 0 | 0 | 4 | 4 | 4 | 2 | 6 / 6 / 12 | 3002 | 164.9 |

Các nhánh dùng chung lượt mù để so ghép cặp; cộng các dòng sẽ đếm trùng receipt. Giá trị ở cột thao tác chỉ chấm loại thao tác trên ca lỗi. Mỗi nhánh có 6 hướng sửa định kiểu, 0 hướng sửa kết hợp ở ca ngữ nghĩa và 0 bản thay thế hoàn chỉnh do AI tự viết. Hai seed lặp lại cùng 24 nghĩa vụ, nên không làm tăng kích thước mẫu nghiệp vụ. Một lỗi trên bốn ca của một lớp tương đương 25 điểm phần trăm. Khi không thấy FP nào trong bốn ca sạch, cận trên Wilson 95% vẫn xấp xỉ 49%.

Mức độ nghiêm trọng, danh sách ID của mọi gap, reason, source và action nằm trong metrics theo seed/arm. Với full union mỗi seed, cả sáu lỗi typed được tái tạo, gồm lỗi giá, MOQ và cơ sở tính giá. Nếu claim ngữ nghĩa không trỏ đúng nguồn hoặc thiếu chứng cứ, hệ thống giữ câu hỏi mở cho người có thẩm quyền. Tập này không chứng minh năng lực tư vấn Marketing tổng quát hoặc đủ điều kiện tăng quy mô. [Thiết kế, giới hạn và cách replay](../../UNION-STUDY.md).
