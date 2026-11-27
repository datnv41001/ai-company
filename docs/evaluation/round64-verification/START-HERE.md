# Runtime Research → Strategy → Content

Draft #64 · head `d79f76373af99585b6b8b720b2a60a93f882c48b` · base `053410d161b15285a1ef264f853d4920a3d559e1` · trial `3d37b1b2d34a69cc80e8def2083bccbd37ebb3c8` · tree `a19ba1ccdd4a7e85ffe12e004e62c64d61d0f59b`.

Đọc [hướng dẫn nghiệm thu trên candidate](https://github.com/datnv41001/ai-company/blob/d79f76373af99585b6b8b720b2a60a93f882c48b/docs/evaluation/round64/README.md). Dữ liệu tổng hợp của cùng một lượt thử trên trial trong [biên nhận commission và công việc](lineage/lineage.json). Đối chiếu [quyền](lineage/authority.json), [bằng chứng trước sửa](review/BASELINE-63.json), [CI](ci.json), [các lượt model chuẩn](model-resources.json) và [manifest digest tệp](files.json).

## Ảnh Chromium trên trial

- [draft-1280-dark](screens/draft-1280-dark.png)
- [draft-1280-light](screens/draft-1280-light.png)
- [draft-390-dark](screens/draft-390-dark.png)
- [draft-390-light](screens/draft-390-light.png)
- [draft-820-dark](screens/draft-820-dark.png)
- [draft-820-light](screens/draft-820-light.png)
- [hold-1280-dark](screens/hold-1280-dark.png)
- [hold-1280-light](screens/hold-1280-light.png)
- [hold-390-dark](screens/hold-390-dark.png)
- [hold-390-light](screens/hold-390-light.png)
- [hold-820-dark](screens/hold-820-dark.png)
- [hold-820-light](screens/hold-820-light.png)
- [reviewer-source-revisions](screens/reviewer-source-revisions.png)
- [stale-revision](screens/stale-revision.png)
- [worker-proposal-and-qa](screens/worker-proposal-and-qa.png)

Worker trong bài kiểm luồng tích hợp sử dụng fixture có kiểm soát. Nguồn Qwen chuẩn được ghi theo đúng lượt model và SHA. Production và Commercial GA NO-GO.

## Đối chiếu

1. Kiểm SHA-256 của ZIP với checksum trong mô tả PR, sau đó chạy `python -m zipfile -t runtime-handoff.zip`. Sau khi giải nén, so sánh SHA-256 từng tệp với `files.json`.
2. Mở [claim ban đầu, chỉnh sửa và quyết định nhận việc](lineage/lineage.json). Trong worker_requests, mỗi completed_attempt_id gắn với đúng role và run. So sánh trường buyer_problem trước/sau, nguồn đã ký, content_digest, revision và receipt_id trong hai phiên người dùng.
3. Kiểm [trường hợp giữ việc](lineage/negative-cases.json), [quyền nhận bản nháp tại quầy](lineage/placement.json), [cô lập client](lineage/client-scope.json) và [số đo Chromium](screens/browser-measurements.json). Ảnh trình duyệt xuất phát từ commission thử UI riêng. Dùng run_id trong số đo để nhận diện.
4. [Raw output Qwen trên từng checkout](actual-model.json), [tài nguyên theo job](model-resources.json), [các lượt native kể cả lượt chưa đạt](native-runs.json) và [chỉ dẫn cách đọc kết quả](review/ACCEPTANCE.md). Các JUnit CI được giữ nguyên byte. JUnit native đã bỏ hostname của máy người phát triển.
