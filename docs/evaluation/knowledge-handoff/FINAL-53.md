# Tiếp quản lại head được review của PR #53

Ngày 26/11/2026, một AI mở phiên mới với bộ đọc Git chỉ cho đọc đối tượng tại `56a120cac4bb3f77a4e1fc6fe93298cc838121ea`. Người đọc nhận SHA và các chủ đề cần kiểm tra. Họ tự chọn đường dẫn, trích dẫn, lệnh khởi động, health và tệp test. Người vận hành thực thi lệnh trong bản xuất sạch ở đúng SHA. Bản chạy ở `82d5b246` vẫn là mốc lịch sử. [39 lượt đọc có SHA](final-53-reads.jsonl) · [Biên nhận smoke](final-53-run.json)

| Chủ đề | Điều người tiếp quản tìm được | Nguồn trong cây đã ghim |
|---|---|---|
| Sứ mệnh và phạm vi | Giao công việc Marketing tới đầu ra được doanh nghiệp nghiệm thu. Một V1 gồm 49 module, 37 vai trò, 24 workflow. Số công việc thật được nghiệm thu bằng 0. | Product Mission, Product Spec, IMPLEMENTATION_STATUS |
| Vai trò | `ai-marketing-operations-director` có trong catalog nhưng thiếu binding trong registry adapter. | `catalog/agent_roles.json:10`, `app/registry_adapters.py:17` |
| Workflow | WF-13 gồm cả phân tích A/B, xuất bản và rollback. Tiểu quy trình viết landing, rồi SEO, có ba biên nhận và đạt `awaiting_qa`. Tại mốc đó việc công bố hoặc thử nghiệm với khách thực còn mở. | `catalog/workflows.json:86`, `catalog/landing-seo-v6.json:2`, `docs/evaluation/campaign-engine/commission/README.md:3` |
| Quyền | Product Owner quyết định phạm vi, ưu tiên. Chủ ngân sách có thẩm quyền của tổ chức quyết định chi thật. Maintainer được ủy quyền quyết định merge đúng head đã review. Production cần quyết định theo môi trường và các release gate. | `AGENTS.md:14`, `app/main.py:53`, `docs/SECURITY_AND_GA_BLOCKERS.md` |
| Công việc tiếp theo | Theo tài liệu **tại SHA #53**, đối chiếu trạng thái thực của #49–52 rồi đo kết quả ở vai Marketing, QA và Sales. Khi dùng cây tích hợp sau #55, mục hiện hành của HANDOFF thay cho các ưu tiên lịch sử này. | `HANDOFF.md:9`, `docs/IMPLEMENTATION_STATUS.md:94`, pilot |

**Phép thử trên Windows.** Người vận hành xuất `git archive` đúng head (SHA-256 `cd5a0b07474d2f0c0c1babd3636ff2f414dbf4bc30ba7a261fd92e9ba8cda8dc`), chạy `python scripts/init_env.py` với môi trường phát triển riêng, SQLite in-memory và JWT tạm. Khởi động `python -m uvicorn app.main:app --no-proxy-headers --host 127.0.0.1 --port <cổng trống>`. Ba đường `/`, `/docs`, `/api/health` trả HTTP 200. Health báo `engineering_bootstrap`, `local`, `production_ready=false`. Dừng tiến trình. `python -m pytest -q -p no:cacheprovider tests/test_api.py` đạt **12/12 trong 8,22 giây**.

**Giới hạn.** Môi trường đã có thư viện phát triển. Lượt này dùng SQLite; PostgreSQL, CI ghép thử, nghiệm thu nghiệp vụ và thương mại có bằng chứng riêng. Phiên mới không nhận lịch sử chat. Hồ sơ thử cũ có sẵn trong repo và người đọc mở sau khi chọn test, truy nguồn vai trò và workflow. Điều đó giới hạn mức độc lập khi nhắc lại kết luận cũ. Người đọc còn phát hiện số ADR dự kiến trong đặc tả khác số ADR phát hành thực tế. Bản đồ tri thức ở cây tích hợp hướng người tiếp quản dùng tên, đường dẫn và trạng thái của bản phát hành.
