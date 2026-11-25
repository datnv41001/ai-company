# Tài nguyên máy Windows và vòng đời lab

Ngày 25/11/2026 lúc 13:24 ICT, cụm phát triển loopback có 100 slot, 3 slot dành cho superuser, 64 kết nối client và 33 slot thông thường còn trống. Có 32 kết nối idle ở database test, 31 idle ở database dùng chung và một phiên kiểm kê active. Đọc đủ 78 database cho phép kết nối. Tổng số route bằng 0. Có 38 login có tên theo mẫu fixture, gồm 13 dispatcher và 25 worker. Không login nào trong số này kết nối tại thời điểm chụp. Không có chứng từ liên kết các login cũ với hai lần setup bị gián đoạn. Vì vậy không xóa theo tên, tuổi hay tình trạng idle.

API và dispatcher dùng SQLAlchemy QueuePool với mặc định 5 kết nối giữ lại và tối đa 10 overflow cho mỗi engine PostgreSQL. Mỗi Lab còn mở kết nối owner và hai kết nối worker. Nhiều process tạo engine riêng và bộ test dùng fixture đồng thời có thể nhanh chóng vượt ngân sách. Các lần chạy trước gặp cạn kết nối được giữ là lần chưa hoàn thành. Ghép kết quả chạy bù không tạo thành một lần full-suite thành công.

Trong đợt này model dùng một endpoint llama.cpp riêng. Các bench chạy tuần tự, một worker thực thi mỗi brief. Lab đánh giá dùng PostgreSQL riêng trên 127.0.0.1, cổng ngẫu nhiên, shared_buffers 24 MB và database dùng một lần. Demo và cụm dùng chung có vòng đời riêng. Tên và mật khẩu fixture chỉ tồn tại trong môi trường local. Lấy số đo hiện tại bằng lệnh sau với DSN kiểm kê của cụm local. Báo cáo chỉ chứa tổng số.

```bash
python tests/evaluation/c3/connection_inventory.py
```

Fixture `Lab` tạo login và cấp nhóm quyền trong một giao dịch, lưu danh sách đã cấp cho lần chạy. Nếu khởi tạo dở dang hoặc teardown lỗi, đóng kết nối worker, dispose pool, gỡ route bằng login của đúng lần chạy, xóa các login đó và đóng owner. Test hồi quy cố tình ngắt sau cấp login thứ hai và truy vấn lại cả role lẫn route. Nếu process bị hệ điều hành kết thúc cứng, kiểm kê và đối chiếu log riêng của đợt chạy trước khi dọn.

Tại thời điểm kiểm kê, máy có 15,83 GiB RAM, còn 0,93 GiB khả dụng và 30,16 GiB đĩa trống. Giữ Qwen2.5-0.5B cho kiểm chứng kỹ thuật. Chưa có phép đo trên Qwen2.5-7B-Instruct hoặc Gemma 4 E4B. Trước đánh giá hai ứng viên, xác nhận license của chính artifact, revision, định dạng GGUF/engine tương thích, quantization, RAM cho weights lẫn KV cache tại context đích, dung lượng lưu và giới hạn concurrency. Chạy cùng bộ skill và holdout trên máy đủ dung lượng, đo chất lượng và peak bộ nhớ rồi mới cân nhắc đổi model. [Nghiên cứu ứng viên](../research/C3-QUALITY-AND-REVIEWER-CAPACITY.md)
