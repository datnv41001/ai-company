# Bàn giao cho phiên đọc mới · Connected Marketing Workforce

**SHA do người đọc được cấp:** `555b968c85b09d52d50d2fd165ea9ff320e5afcd`. Người đọc dùng Git object broker chỉ đọc các file đã commit tại SHA này; các lần đọc được ghi trong `reader-paths.jsonl`. Người vận hành thực hiện các lệnh localhost người đọc yêu cầu. Đây là kiểm tra tiếp quản bằng AI, số practitioner Marketing tham gia là 0.

| Câu hỏi | Kết quả đối chiếu |
| --- | --- |
| Ai dùng và giao việc gì? | Chủ doanh nghiệp hoặc agency cần sản phẩm Marketing có thể duyệt và truy ngược về mục tiêu, nguồn, người chịu trách nhiệm và chi phí. Đơn vị giá trị là việc được người có thẩm quyền nhận. Người đọc dẫn `docs/PRODUCT_MISSION.md`. |
| Theo một hành trình | Người đọc lần từ brief và quyền sử dụng tới manifest, lease, Director, checkpoint của Content, Storyboard, revision QA, landing được ký riêng, preview ký độc lập, rồi distribution ID trên visit, submission và inbox. Nguồn gồm `tests/test_storyboard_distribution.py` và `docs/evaluation/connected-workforce/README.md`. |
| Phạm vi hiện tại | Main sau #59 gồm WF-08 @1. Nhánh kế tiếp có @2 opt-in. Phạm vi 49 module, 37 vai trò, 24 workflow mẹ. Production và Commercial GA vẫn NO-GO. Thẩm quyền phát hành thuộc Product Owner. |
| Quyết định và giới hạn | Studio và Storyboard có 2 run với owner và approval riêng. Đường nối kiểm đúng nguồn có phiên bản và đúng file. Ca Khe Gọn tổng hợp cho 1 visit, 1 inquiry, 0 qualified RFQ và 0 đơn. Primary KPI trống. Bản minh họa im lặng 540×960. Hiệu quả creative và chi phí đầy đủ chưa đo. |
| Chạy từ bản sạch | Git archive SHA-256 `9e724c2ab9913a048b0b2c8f1e54d088c4066fc4ef9ba7ac9eee1b77b939ec4a`. Dùng SQLite và dependencies dev đã cài. `scripts/init_env.py` exit 0; loopback `/`, `/docs`, `/api/health` đều HTTP 200. Health trả `production_ready=false`. |
| Chọn và chạy kiểm thử | Người đọc yêu cầu `tests/test_storyboard_brief.py` và `tests/test_storyboard_distribution.py`; 3 đạt, 6 skip trong 2,76 giây. SQLite bỏ qua các ca cần mailbox và CRM PostgreSQL. Các ca PostgreSQL nằm ở lane native và CI. Lệnh và exit code ở `round60-operator.json`. |
| Ưu tiên kế tiếp | Mời một editor có consent sửa một cảnh từ brief đóng băng, gửi đúng revision cho QA độc lập và hỏi người nhận có đủ thông tin sản xuất hay chưa. Ghi số phút từng vai trò, rework, quyết định và chi phí. Không có consent hay quyết định nhận việc thật trong bài tiếp quản này. |

Người vận hành đã đối chiếu mô tả với mã, run và trạng thái health. Giới hạn của bài đọc là operator sử dụng dependencies cài sẵn và SQLite, chưa tái hiện PG bằng riêng bản export này. Hồ sơ CI và JUnit cung cấp kiểm tra PG riêng.
