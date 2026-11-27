# Biên nhận kiểm tra tiếp quản · 27/11/2026

**Cold handoff bằng AI mới: NOT_VERIFIABLE.** Chỉ thị yêu cầu một AI không có lịch sử và đồng thời giới hạn chạy inference chỉ cho audit. Tại thời điểm lập biên nhận, chưa có xác nhận riêng cho phép mở phiên mới. Số phiên AI độc lập đã chạy phép thử trên cây này là **0**. Vì vậy không có transcript AI mới, điểm chấm hay kết luận PASS. Phép kiểm dưới đây xác minh phần có thể tái hiện bằng công cụ.

**Checkout thử:** detached `fe61923e7f53a28e215a191491e53f80cbfef000`, tree `39afcde89b4bf5d2e7f449216f24dbc51721b1cd`. Người chạy: Codex đang thực hiện audit, biết ngữ cảnh. Windows, PowerShell 7.6.9, Git 2.49.0.windows.1, gh 2.103.3, Python 3.12.14. Dùng dependencies từ venv local đã có và SQLite in-memory. Cổng health được gọi qua FastAPI TestClient trong process. Thử nghiệm này không đo cài mới dependency, Docker hoặc PostgreSQL.

| Lệnh hoặc phép kiểm | Kết quả quan sát |
|---|---|
| `git worktree add --detach ../kc-cold-01 fe61923e7f53a28e215a191491e53f80cbfef000` | Bản đọc tách biệt đúng commit. |
| `python -m pytest -q -p no:cacheprovider tests/test_research_strategy.py::test_witness_and_terminal_contract --junitxml=<output>/cold-smoke.xml` | 1 đạt trong 1,32 giây. Test kiểm cả manifest hợp lệ và kết quả khi xóa predecessor bắt buộc. |
| `TestClient(app).get('/api/health')` | HTTP 200. status=ok, stage=engineering_bootstrap, environment=local, production_ready=false. |
| Đếm ID duy nhất trong section 3 đặc tả, hai file JSON catalog; đối chiếu P00–P12 | 49 / 37 / 24 và 13 pha. |
| Kiểm đường dẫn và anchor Markdown tương đối trong 7 tài liệu chính sửa đổi cùng báo cáo audit, đọc blob Git | 420 tham chiếu tại checkout thử, 0 lỗi. Kết quả cho commit bàn giao cuối trong gói đối chiếu. Kiểm riêng PR, tag và CI qua GitHub. |
| So diff với main và đối chiếu các dòng cũ theo thứ tự | 9 file tài liệu/template/biên nhận tại checkout thử. Tất cả dòng có nội dung của 7 tài liệu cũ vẫn tồn tại theo thứ tự. Lịch sử bằng chứng trước audit không có diff. |
| Băm ZIP ở proof commit cố định và kiểm CRC từng entry | Khớp SHA-256, số byte và 69 entry của [biên nhận](KC-AUDIT-01-REFS.json). |
| Kiểm tên và mẫu credential có độ đặc hiệu cao trên cây thử | 1.347 file tracked; 0 tên .env/key riêng/bundle PKCS#12 theo danh sách đã kiểm. Một trùng mẫu trong URL bài LinkedIn công khai ở `docs/research/SOURCE_REGISTRY.md:71` (chuỗi “ask-” trong slug). Diff mới có 0 trùng mẫu. |
| Kiểm chứng remote lần bàn giao | `gh pr view`, `gh api`, đối chiếu Git ancestry và so toàn bộ biên nhận trừ timestamp: khớp. |

Kiểm thủ công phần được thêm gồm vai trò chuyên môn, định danh commit, CI, đường dẫn công khai, mô tả fixture và kết quả tổng hợp. Kiểm mẫu không thể chứng nhận mọi binary, toàn bộ lịch sử Git, PII, quyền tái sử dụng hoặc độ kín của benchmark. Chủ dữ liệu và security owner giữ các gate đó. Nếu được duyệt mở phiên mới, chỉ cấp checkout và SHA, giao các câu hỏi trong [quy trình tiếp quản](../../KNOWLEDGE_MAP.md#cold-start), lưu nguyên văn trả lời và kiểm từng dẫn chứng trước khi đổi verdict. [Cold drill #53](FINAL-53.md) là kết quả của SHA lịch sử.
