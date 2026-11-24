# Reviewer tổng hợp trong Docker Linux

Lệnh này kiểm tra một dữ kiện trong bộ Marketing đã ghim. Reviewer so sánh giá trị được duyệt với nội dung đang xét và trả về cả hai giá trị. Trường `model_invocations` bằng 0 vì worker thực hiện phép so sánh xác định. Kết quả kiểm tra quyền của container chỉ áp dụng cho tiến trình này. Các receipt Qwen sử dụng launcher native giữ nguyên xuất xứ.

## Chạy và đọc kết quả

Dùng máy Linux có Python 3.11+, Docker Engine với socket cục bộ `/var/run/docker.sock`, Go 1.20+ và seccomp mặc định. Docker daemon và toolchain của máy là thành phần tin cậy. Tài khoản thực hiện lệnh cần quyền truy cập daemon. Reviewer trong container chạy bằng UID/GID 65532.

```sh
python3 engineering/airc500/sandbox_container.py --case H01
AIRC_TEST_LINUX_DOCKER=1 python3 -m unittest discover -s engineering/airc500 -p test_sandbox_container.py -v
```

H01 có chênh lệch giá và H02 khớp nguồn. Cả hai trả về mã băm của runtime, gói dữ liệu đã đọc, bộ fixture và ID image. JSON chứa kết quả kiểm tra mount, quyền hệ điều hành và mạng. Chỉ công nhận kết quả sau khi container đã thoát thành công, bộ kiểm tra host đối chiếu đúng digest, finding và đủ 12 phép kiểm tra. CI chạy hai ca thực trong job `contain-synthetic-review`. Khi chạy bộ unit test thiếu biến môi trường trên, phần Docker được đánh dấu skipped.

## Phạm vi của reviewer

- Launcher chỉ nhận ID trong fixture có SHA-256 đã ghim. Mỗi container chỉ nhận ID, tên trường, giá trị được duyệt và nội dung hiện tại của đúng ca đó. Mount chỉ đọc chứa một file. Kho mã, nhãn, khóa ký và cấu hình Docker của người vận hành nằm ngoài container.
- Host build worker Go từ thư viện chuẩn với tải module và toolchain tự động bị vô hiệu. Image rỗng được nhập vào daemon bằng tar chứa binary, thư mục mount và file giữ chỗ. Container chạy đúng image ID vừa tạo, không pull. Compiler, Docker socket và CLI thuộc host.
- Host đối chiếu cấu hình daemon trước khi chạy. Worker kiểm tra mount gốc và file fixture chỉ đọc, seccomp, capabilities đã bỏ, UID, `no_new_privs`, duy nhất loopback, danh sách tên biến môi trường, file canary không xuất hiện và khả năng tạo rồi xóa file trong tmpfs. Probe mạng chỉ kiểm tra interface đang tồn tại.
- Tmpfs 4 MiB có `noexec,nosuid,nodev`. Container có giới hạn 64 MiB bộ nhớ, 0,5 CPU, 32 PID, private cgroup namespace, không có IPC chia sẻ, cổng công bố hay network interface nối ra ngoài. Host dùng Docker config trống, môi trường tối thiểu và kiểm tra container đã kết thúc sau tối đa 15 giây chạy worker.
- Tên container cố định giới hạn một lượt của loại reviewer này trên daemon. Nếu coordinator bị tắt đột ngột, lượt sau gặp lỗi trùng tên. Để phục hồi, kiểm tra `docker inspect airc-synthetic-fact-review`, đối chiếu label `airc.synthetic` và image ID của lượt gián đoạn, đợi hoặc dừng chính container đó rồi dọn container và image theo ID đã đối chiếu. Lượt chạy bình thường tự dọn tài nguyên nó tạo.

Chứng cứ này đo lớp cô lập của Docker với fixture. Hệ thống vẫn giữ cổng đọc mã repository thật ở trạng thái HOLD. Tách key custodian sang danh tính hệ điều hành riêng, attestation của host, đóng gói và kiểm định runtime Qwen Linux là các bước tiếp theo trước khi mở rộng phạm vi. Báo cáo JSON dựa trên host tin cậy và log CI, không phải chứng thực mật mã của kernel.
