# Giao một storyboard cho AI Video/Storyboard trong môi trường phát triển

Người dùng là trưởng Creative giao một tờ dựng dọc cho người biên tập. Bản phát hành `WF-08/video-storyboard@1` gắn vai trò catalog `ai-video-storyboard` với một công việc agency dùng tiếng Việt. Worker dựng minh họa tất định, soạn lời từ nguồn đã duyệt, timeline, VTT, chỉ dẫn hình và điều kiện quyền tư liệu. Đây là một phần WF-08. Thuật toán hiện hỗ trợ yêu cầu báo giá, đề nghị hẹn và chọn buổi; tất cả đều dùng khung dọc 9:16 và thời lượng 12–32 giây theo brief.

## Chạy lại trên máy phát triển

Dùng PostgreSQL phát triển và quy trình khởi tạo trong [HANDOFF](../../../HANDOFF.md). [Pool runbook](../../POOL-RUNBOOK.md) mô tả cách tạo các login dispatcher/worker, cả ba mật khẩu riêng, route chính xác đến tenant, client, brand, campaign và editor. Khi diễn tập WF-08, dùng pool cô lập trên cùng bản build với các job storyboard. Tạo cấu hình pool trước khi chạy hai lệnh ở thư mục gốc:

```sh
docker compose -p amc-dev run --rm migrate python migrations/apply.py --publish-registry catalog/video-storyboard-v1.json
docker compose -p amc-dev --env-file .env --env-file .env.pool -f compose.yaml -f compose.pool.yaml up -d --build dispatcher worker-one
```

Publisher hiện hữu xác minh runtime lock và định nghĩa bất biến; có thể gọi lại trên database v26 cũ hoặc mới. Admin vào endpoint registry có sẵn `PUT /api/tenants/{tenant}/workforce/registry/{campaign}` với `{"workflow":"WF-08/video-storyboard@1","action":"activate","skills":["director","storyboard"]}`. Budget của run bằng 0. Đặt route, năng lực pool và kỳ ngân sách trước khi giao việc. Sổ ledger ghi giữ và phí model bằng 0 cho binding này. Rollback bằng thao tác disable/revoke của registry theo runbook, giữ lại lịch sử PDF/JSON, checkpoint, bản ký QA và các release khác.

## Quy trình và trách nhiệm

1. Agency mở brief được cấp đúng recipient và campaign. Recipient nộp task loại `video_storyboard` với ICP, sản phẩm, khu vực/ngôn ngữ, kênh, hành động khách hàng, `aspect_ratio="9:16"`, `duration_seconds` và `rights="synthetic_illustration_only"`. Trên Business Workspace, ghim brief nội bộ, Brand Kit, claim có người duyệt, điều kiện thương mại, KPI và hướng dẫn thương hiệu vào manifest cho đúng release. Bản này nhận agency brief; SQLite có thể kiểm thuật toán dựng, hàng đợi registry chạy PostgreSQL.
2. Editor có quyền đọc nguồn gửi `POST /api/tenants/{tenant}/workforce/briefs/{brief}/run` với `workflow="dynamic-v1"`, `registry_workflow="WF-08/video-storyboard@1"`, `knowledge_manifest={"id":…,"digest":…}`, `budget_microusd=0`. API trả run ở trạng thái queued. Kiểm tại `GET /api/tenants/{tenant}/workforce/runs/{run}`. Director đóng băng một node storyboard, dispatcher cấp lease, worker nhận và chạy adapter bản đã khóa; bên nhận kết quả dựng và đối chiếu độc lập với input đã ghim trước khi lưu. Hook, shot, source ID, VTT và quyền xuất hiện trong checkpoint cuối. Tính từ văn bản, giá, đơn vị, thuế, MOQ và điều kiện đều từ nguồn đã duyệt. Trường hợp chưa công bố giá có thẻ riêng. Những giá/điều khoản quá dài hoặc nằm ngoài phạm vi xử lý dừng có biên nhận.
3. Đường biên QA tái kiểm hồ sơ nguồn hiện hành, campaign registry binding và nội dung trước khi ký. Có thể xem lịch sử checkpoint cũ sau khi nguồn bị rút. Worker tạo bản nháp từ manifest đã ghim; thẩm quyền hiện hành được kiểm vào lúc xếp hàng, biên tập và phê duyệt. QA yêu cầu đúng `expected_qa_revision` và `expected_content_digest`. Dùng `POST .../workforce/runs/{run}/storyboard-edition` với hai trường đó và `hook_variant="audience"` hoặc `"direct"` để tạo một phiên bản mới. Submit rồi người duyệt độc lập review bằng endpoint deliverable hiện hữu. Nguồn hạn chế cần người có quyền với nguồn đó. Các tờ dựng ở phạm vi tiền kỳ nội bộ. Hình, người thật, phép xuất bản và tác động ngoài nằm ngoài quyền của binding.
4. Phản hồi đã kiểm chứng được ghi cùng ID run, manifest, revision, lỗi đọc giá hoặc CTA và thời gian biên tập. Đề nghị thay đổi SOP/thuật toán qua phiên bản mới và đối chiếu lại các ca hồi quy cùng brief mới. Mỗi kết quả chấm nghiệp vụ cần người hành nghề có consent.

## Bằng chứng kỹ thuật và kiểm thử

Bộ test mở brief, nộp việc, tạo nguồn có approval, chụp manifest bằng API và activate binding. Nó chạy dispatcher và hai hàm take/report bằng các login PostgreSQL giới hạn thật. Worker đi qua cùng hàm sản xuất `run_job` như trong vòng lặp service. Giữ raw ở checkpoint, QA revision tiếp theo và người duyệt. Các case sử dụng synthetic test accounts. Không có lượt inference model trong binding này.

```sh
python -m pytest -q tests/test_video_storyboard.py
```

Để chạy đầy đủ, dùng fixture PostgreSQL đã cấu hình `AMC_TEST_PG=1` như CI với database `amc_test*` trên loopback. Có thể đặt `AMC_STORYBOARD_EVIDENCE` thành thư mục trống để xuất raw, reviewed, source chain và journal của từng run. Mỗi lần tái lập tạo ID mới. Ba hồ sơ ở cùng thư mục tài liệu là bản đã lưu. Tính hữu ích thực tế, công sửa của người dựng, ROI và chi phí trên mỗi công việc được doanh nghiệp chấp nhận đang chờ pilot.

Đối chiếu cơ chế đang chạy ở [manifest phát hành](../../../catalog/video-storyboard-v1.json), [SOP được ghim](../../../catalog/video-storyboard-sop-v1.json), [worker](../../../app/video_storyboard.py) và [test](../../../tests/test_video_storyboard.py).
