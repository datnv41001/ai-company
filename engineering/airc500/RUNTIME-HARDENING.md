# Hợp đồng admission, tài nguyên máy và tiếp nhận PR

## Quyền kết luận của một run

Coordinator gọi `Journal.start_planned(run, adapter_trust, plan, verifier_public_key)` trước khi cấp bất kỳ lease nào. Event đầu ghi manifest, fingerprint catalog, 2 SHA, danh sách assignment/reviewer/phase/artifact, mọi nghĩa vụ và public key của verifier. Mở lại cùng run với kế hoạch hoặc khóa khác bị từ chối. Khi đọc lại archive mới, cung cấp `expected_plan_digest` và `verifier_key` từ hồ sơ admission tin cậy. Digest ngoài archive hoặc commit đã review xác định bộ pin được tin. Archive v1 đã bàn giao vẫn kiểm được theo hợp đồng khi phát hành.

| Kết quả | Nguồn và cách hiểu |
|---|---|
| Execution coverage | Đếm assignment trong kế hoạch có signed receipt và output được nhận. Thiếu arbiter bắt buộc nằm trong `execution.missing`. |
| Evidence coverage | Đếm obligation có observation `verified` do key riêng của verifier ký. Observation tham chiếu plan digest, run ID, assignment, output digest và nguồn. Verifier kiểm căn cứ của claim trong fixture. `insufficient` và `rejected` không lấp khoảng trống. |
| Review quality | Quality runner tính so với oracle đóng băng theo từng mốc. `covered` chỉ mô tả độ phủ. |
| Quyết định | Thiếu một assignment, thiếu căn cứ cần thiết, hủy hoặc vi phạm budget cho kết quả `inconclusive`. Caller không thể truyền danh sách ngắn hơn để đạt đủ. |

Một run cũ không có plan không được dùng API để tự xác nhận đủ coverage. Phiếu đầu tiên trên mỗi cặp assignment/obligation là bất biến. Nếu cần thẩm định lại trên nguồn đã sửa, tạo run mới giữ liên kết bằng SHA. Với fixture local, coordinator và assessor là các thành phần tin cậy trên cùng máy. Adapter ký execution, verifier ký căn cứ theo domain chữ ký khác, reviewer chỉ nhận message nội bộ và không có các signing key. Việc tách key trong phần mềm chưa chứng minh OS principal độc lập.

## Giới hạn vật lý và gốc tin cậy runtime

`host_capacity.machine_slot` dùng hai cổng TCP loopback cố định **41981 và 41982** trong host network namespace. Giới hạn độc lập với worktree, journal, user config và run ID. Supervisor bind độc quyền rồi truyền handle/FD vào process model thật. Linux dùng `pass_fds`, Windows dùng explicit handle list. Mỗi server chỉ có một slot inference. Supervisor giải phóng lease logic hoặc chết không làm mất slot physical của process còn sống. Khi đóng adapter bình thường, supervisor terminate, wait, rồi kill và wait nếu cần. Cổng bận bởi ứng dụng khác làm giảm capacity. Sau crash giữa dispatch và receipt, journal giữ exposure chưa biết và chỉ đối soát usage tới muộn. Máy ảo hoặc container có network namespace khác cần control plane chung trước khi được coi là cùng pool.

Trên Windows, launcher kiểm executable cùng toàn bộ **29 DLL** của distribution theo [manifest enrollment](runtime-pins/windows-x64.json). Đã so các entry với file ZIP local có SHA-256 `0e2ff97a5ef40de3e4ca910231676c044e0813c54727b2012022a2d2401e1fa9`; đây là kiểm tra byte so với cache đã dùng cho pilot. Binary và GGUF có digest pin riêng. Launcher copy vào thư mục riêng, kiểm hash trên chính bản sẽ chạy, rồi mới tạo process. Không copy file khác cùng thư mục do người gọi đưa vào. PATH dành cho runtime đã thu hẹp, môi trường con chỉ có biến hệ thống tối thiểu, server chỉ nhận loopback request với ephemeral key. Trên nền tảng khác, operator phải cấp manifest có danh sách tên và SHA-256 của executable và các thư viện private phù hợp, lấy từ kênh đã duyệt. OS loader và binary launcher vẫn là thành phần tin cậy.

**Phạm vi hiện được phép là fixture tổng hợp.** Bộ nhập v1 chỉ chấp nhận đúng cặp Git SHA đã duyệt. Bộ quality tạo corpus fixture từ mã nguồn engineering. Reviewer so sánh dữ kiện có launcher Docker Linux và probe filesystem, mạng, secret. Các lượt Qwen native và vai trò giữ khóa vẫn cần sandbox OS riêng. Event của repo AMC thật chỉ có metadata. Tính năng lấy source thật và phát lệnh sửa chủ động tiếp tục HOLD. [Chạy lại và xác minh lớp cô lập](SANDBOX-CONTAINER.md).

## Tiếp nhận event và tạo bàn giao cục bộ

`event_intake.py` là CLI offline/worker cho chương trình tiếp nhận nội bộ. Receiver truyền nguyên raw bytes body, GitHub delivery ID, event type và chữ ký HMAC-SHA256. Secret tối thiểu 32 byte được operator cung cấp qua `AIRC_WEBHOOK_SECRET`. Xác minh trước khi đọc JSON. SQLite ghi delivery ID, content digest, PR revision, deadline và cycle trong một transaction; body lặp, revision trùng, conflict delivery ID hoặc head cũ không tạo công việc mới. Khi repo là AMC, bước đối chiếu dùng GET metadata vào GitHub public API cho đúng repo/PR, không theo redirect, không cần token. Khi repo là fixture, bước đối chiếu dùng lịch sử Git tổng hợp. Tối đa hai revision trong một cửa sổ 45 phút, sau đó chuyển `human_escalation`.

Ví dụ lệnh chạy từ gốc repository:

```sh
python engineering/airc500/event_intake.py --db /path/to/engineering-inbox.sqlite --delivery <delivery-id> receive --body event.json --signature <signature-header>
python engineering/airc500/event_intake.py --db /path/to/engineering-inbox.sqlite --delivery <delivery-id> handoff --directory engineering/airc500/evidence/qwen-marketing-01 --archive-sha256 <reviewed-archive-pin> --trust-sha256 <reviewed-public-trust-pin>
```

Event fixture hợp lệ tạo kế hoạch targeted theo domain và phạm vi dependency. Lệnh handoff chỉ xuất JSON draft ra stdout sau khi đối chiếu lại head, replay archive và khớp source SHA. Mọi assignment kèm finding, tiêu chí và evidence. Hiện chưa cài webhook/repo write token trên GitHub, chưa nối daemon tự dispatch model, chưa chuyển gói sang Codex qua mạng. Operator có thể chạy cùng fixture bằng lệnh pilot rồi dùng handoff trên gói được duyệt. Mở research công khai và real repo ingestion vẫn theo [roadmap đã duyệt](RESEARCH-AND-REVIEW-LOOP.md).

## Nghiệm thu và rollback

```sh
python -m pip install -r engineering/airc500/requirements-pilot.txt
python -m unittest discover -s engineering/airc500 -p "test_runtime_hardening.py" -v
python -m unittest discover -s engineering/airc500 -p "test_journal.py" -v
```

Ca kiểm tra gồm sai catalog, thiếu artifact hoặc arbitration, thu hẹp scope, lọt output thiếu căn cứ, khóa verifier giả, đổi SHA/plan, ký sai, replay, archive hỏng, event stale/trùng, giới hạn vòng và process vật lý thực còn giữ slot. Fixture socket test khởi chạy process con riêng, xác nhận slot còn bận sau khi coordinator trả handle, chờ OS xác nhận con kết thúc rồi mới nhận lại slot. Rollback bằng cách ngừng launcher và inbox worker, xác nhận PID model con đã kết thúc; giữ journal/receipt/archive để truy vết. AMC không có migration hay quyền mới từ phần tooling này.
