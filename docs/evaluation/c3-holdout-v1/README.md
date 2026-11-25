# Chứng từ thực nghiệm WF-03 và WF-13

Bộ [50 brief tổng hợp đã đóng băng](../../../tests/evaluation/c3/holdout-v1.json) được tách khỏi tập phát triển. Mỗi dòng JSONL gồm tên loạt và receipt của một brief ở một cấu hình. Bao gồm cả ca cần làm rõ và ca không có bản giao. Số dòng không biểu thị số bản được QA chấp nhận.

| Tệp | Số dòng | SHA-256 của tệp nén |
| --- | ---: | --- |
| [first-pass.jsonl.gz](first-pass.jsonl.gz) | 150 | `7083733820304e9b7c3ba68f9e1a17240639a1f9632fe9d944fd93225d5a99ba` |
| [repeat.jsonl.gz](repeat.jsonl.gz) | 20 | `caf2eebd66af1cb78795cb683cf8620279b87959698cd2c0e8aacf26aa475d04` |

Đọc bằng Python với `gzip.open(path, "rt", encoding="utf8")` và `json.loads(line)`. Ghép theo case ID, workflow, SKU và tên sản phẩm. Mỗi receipt ghi checkout, weights, phí nhà cung cấp, token, trạng thái và kết quả của lần chạy. Hai dòng có cùng mục tiêu nhưng khác cấu hình là hai phép đo. Xem [số đo lần đầu](quality-summary.json), [đối chiếu lặp](repeat-summary.json), [đánh giá từng ca](../C3-QUALITY-RESULTS.md) và [quy trình chấm](../C3-HOLDOUT-AND-PILOT.md).

Hai ví dụ biên tập dưới đây lấy từ ca phát triển trên SHA riêng đã ghi trong từng tệp. Chúng minh họa hoạt động của cổng và lịch sử phiên bản. [Chiến lược Gốm Bắc](materials-generated-and-edited.md) · [Trang đích An Nhiên](service-generated-and-edited.md)

Cả hai nhánh so sánh và các lần lặp chạy trên checkout `08cc65b4de4ae637d3a3bbd70b7e1e0eb6128f32`. Tệp [điều kiện thực nghiệm](conditions.json) lưu SHA của weights, digest bộ brief, bản llama.cpp và Git object của adapter, renderer, thư viện skill cùng bốn release. Các Git object đã đối chiếu trùng với phiên bản bàn giao. Phiên bản bàn giao có thêm màn hình đọc tài liệu, API cho nhân viên và sửa dọn tài nguyên test. Biên nhận smoke của SHA tích hợp cuối nằm trong artifact GitHub Actions gắn trên PR.
