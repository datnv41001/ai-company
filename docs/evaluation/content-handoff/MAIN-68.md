# Chứng nhận main sau PR #68 · AMC-RES-QA-01-FINAL-ACCEPTANCE

GitHub ghi nhận merge lúc 07:18:38 ngày 28/11/2026 (UTC+7). Đã đối chiếu base, head, trial tree và 9 job bắt buộc trước merge. Git commit sau merge có hai parent theo đúng thứ tự dưới đây. [PR #68](https://github.com/datnv41001/ai-company/pull/68) · [Commit trên main](https://github.com/datnv41001/ai-company/commit/7446bc8ba32578554d1e9179e2caa3799e474358)

| Đối tượng | Git SHA |
|---|---|
| Main sau merge | `7446bc8ba32578554d1e9179e2caa3799e474358` |
| Parent 1, main trước merge | `fe0110bd2fa524619c527420478edb9f7b94a0b6` |
| Parent 2, head đã duyệt | `c9e4870c654e36706768f31130ea9c5453c32d6b` |
| Trial merge đã duyệt | `571023974c40693fd1eb000230beef7d1e189963` |
| Tree chung của trial và main sau merge | `1790a2b4d544052b8004ba26b0866f5e3f785b1e` |

Tính lại SHA-256 từ byte của Git blob trên main cho đủ **29/29** mục trong manifest #68. Manifest có SHA-256 `24fd0b971d6c04451e21bbf06b0975f12396ef80b0e33f809002f1910d11ee1c`. R67-01 đóng trong contract /1 cho bảy câu đã review. R67-02 đóng trong hai ca Delivery đã kiểm. Khả năng suy luận Research tổng quát vẫn chưa được chứng minh. [Hồ sơ #68 cố định](https://github.com/datnv41001/ai-company/tree/7446bc8ba32578554d1e9179e2caa3799e474358/docs/evaluation/research-instruction)

## Kết quả CI trên chính commit merge

**PASS cho phát triển nội bộ.** Workflow push trên main chạy đúng một lần (`run_attempt=1`). API, compose-browser và workforce-model đều thành công. Job matched-model tùy chọn được bỏ qua. [GitHub Actions run 46087196986](https://github.com/datnv41001/ai-company/actions/runs/46087196986) · [Kết quả đọc lại từ GitHub API, JUnit và log](main-result.json)

- JUnit của API ghi 797 ca, **795 đạt, 2 skip, 0 lỗi**. Hai skip là biến thể SQLite của phép kiểm riêng cho PostgreSQL. SHA-256 của XML gốc là `34ef186bf2561bd29d4dac60b288ca9fb617729309cadc0df5ebd241015a5d54`. [JUnit gốc](https://github.com/datnv41001/ai-company/actions/runs/46087196986/artifacts/15240466937)
- Kiểm đủ **22** đường nâng database đã có dữ liệu từ từng phiên bản v1–v22 lên v26 và chạy lại migration. Log xác nhận restore v26 sang database riêng, dữ liệu trong **34 bảng** giống nhau. [Job API và migration](https://github.com/datnv41001/ai-company/actions/runs/46087196986/job/140799432333)
- Compose và Chromium chạy thành công. Kết quả này thuộc tree của #68. PR Content Handoff mới chỉ bổ sung test và tài liệu. [Job compose-browser](https://github.com/datnv41001/ai-company/actions/runs/46087196986/job/140799432536)

## Tài nguyên và lỗi quan sát trong job Qwen

Job `workforce-model` chạy một lần, từ 07:18:42 đến 07:27:53 (9 phút 11 giây, UTC+7). Model dùng llama.cpp loopback, build `b12648-44d50873b`, SHA-256 trọng số `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`. Giữ nguyên cấu hình CI và dữ liệu tổng hợp. [Job Qwen](https://github.com/datnv41001/ai-company/actions/runs/46087196986/job/140799432491) · [Receipt và số liệu được trích từ artifact](main-model-usage.json)

| Phần có telemetry | Lần thử đầu | Retry ở runtime | Token vào / ra đo được | Lỗi hoặc giới hạn |
|---|---:|---:|---:|---|
| Các bản đo campaign có `stage_attempts` | 38, trong đó 34 thành công ngay | 1 | 11.117 / 3.532 | 3 denial `recipient_revoked` không xác nhận được usage. 1 lần `invalid_source` trong Research → Strategy, sau retry run đến `awaiting_qa`. |
| 7 journey có `run_id` và journal riêng | 21, tất cả thành công ngay | 0 | 12.524 / 2.165 | Cả 7 đến `awaiting_qa`. Receipt cho biết tổng phí provider 0 USD. |
| Kiểm tra 2 specialist chạy song song | Artifact ghi 2 real specialist calls | Không có journal theo attempt trong bản đo này | 518 / 188 | Ước tính 0 micro-USD, 1 approved snapshot. |

Mỗi dòng là một phạm vi đo riêng của workflow. Không tính cộng gộp thành tổng token hay hóa đơn cho cả job. Đợt CI dùng provider local và không gọi API model trả phí. GitHub không cung cấp hóa đơn runner, điện năng hay tổng chi phí máy trong artifact. Lần thử lại do runtime xử lý khác với số lần GitHub chạy workflow. 72 lượt nghiên cứu D/A/C vẫn ở trạng thái đề xuất. [Artifact gốc](https://github.com/datnv41001/ai-company/actions/runs/46087196986/artifacts/15239439088)
