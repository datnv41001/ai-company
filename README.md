# AI Marketing Company (AMC)

**[Chạy bằng Docker và tiếp quản trên máy mới → HANDOFF.md](HANDOFF.md)**

Tiếp quản bằng [bản đồ tài liệu và bằng chứng](docs/KNOWLEDGE_MAP.md). Tra một module, vai trò AI hoặc workflow trong [sổ trạng thái V1](docs/IMPLEMENTATION_STATUS.md) trước khi kết luận về mức hoàn thành.

AMC lấy công việc Marketing được doanh nghiệp nghiệm thu làm đơn vị đo. Đọc tôn chỉ để biết đầu ra nào cần bàn giao và phải đo gì trước khi kết luận AMC giúp giảm việc. [Product Mission & Commercial North Star](docs/PRODUCT_MISSION.md)

Đăng ký tài khoản, xác minh email rồi chọn tạo workspace hoặc nhận lời mời vào workspace hiện hữu. [Onboarding và lời mời trên máy mới](docs/PR16-ONBOARDING.md). Chủ workspace có thể mời nhân viên hoặc khách hàng đã đăng ký. [Hướng dẫn Docker, hộp thư và lời mời](docs/PR15-IDENTITY.md).

**QA theo phiên bản.** Khi sửa tiêu đề hoặc nội dung gửi khách, hệ thống đánh giá lại claim và yêu cầu người QA duyệt đúng số lần lưu và SHA-256 của bản đang xem. [Hợp đồng API, nâng cấp v8 và phục hồi](docs/ADR-007-QA-EVIDENCE-REVISION.md).

**AI Workforce nội bộ.** Luồng brief → Director → Research → Strategy → Content tạo bộ tài sản chờ QA. [Chạy worker và model](HANDOFF.md#chạy-ai-workforce-trên-máy-mới) · [Thiết kế và bằng chứng](docs/ADR-005-AI-WORKFORCE.md).


## Chạy cục bộ với PostgreSQL trên Windows

Sau khi cài `requirements-dev.txt` trong môi trường Python 3.12, chạy lệnh dưới đây từ thư mục mã nguồn. Thay đường dẫn `--pg-bin` bằng thư mục PostgreSQL đã cài. Ứng dụng dùng PostgreSQL trên cổng 55432 và giao diện tại [127.0.0.1:8000](http://127.0.0.1:8000). Trang [API docs](http://127.0.0.1:8000/docs) liệt kê các endpoint. Đăng ký tổ chức trên trang chủ để bắt đầu.

```powershell
.\.venv\Scripts\python.exe scripts/start_local.py --pg-bin "C:\Program Files\PostgreSQL\16\bin"
```

Lần đầu, script tạo cluster, khóa cục bộ và chạy migration. Lần sau dùng lại cùng thư mục trạng thái. Mặc định dữ liệu và log nằm trong `.local/` đã được Git bỏ qua. Có thể chọn đường dẫn riêng bằng `--state`.

**Status: engineering bootstrap, NOT the finished commercial product.** This codebase is the first runnable foundation for the **single full-scope AI Marketing Company V1.0** specified in `docs/PRODUCT_SPEC_V1.md`. We are not splitting V1.0 into multiple products; engineering delivery is staged internally only.

The completed product must support Agency Mode + In-house Mode, 49 product modules, 37 logical AI roles and 24 business workflows. The inventories under `catalog/` are **specifications**, not a claim that those agents or workflows are implemented.

## What already works in this starter

- Register an account, verify its email in the development mailbox and choose or create a workspace. The workspace supports Agency and In-house modes.
- Persist clients, brands, campaigns, workflow skeleton tasks, deliverables, action approvals and audit events.
- Scope API resources by tenant and client. Each external membership belongs to one client per agency. It can read that client profile and explicitly shared snapshots. Commenting and deciding require separate grants. PostgreSQL enforces row policies in addition to the API checks. Internal `viewer` members retain agency-wide read access.
- Create an idempotent **deterministic** 7-task marketing campaign plan (NOT an LLM-generated plan).
- Agency staff queue a sourced brief through Workforce. Model credentials and provider calls belong to the budgeted worker.
- Independent human review of deliverables and external-action proposals; self-approval is forbidden.
- External publishing, ad spending, emailing, CRM writes and deletes are **hard-disabled**, even after approval, pending official connectors and policy checks.
- Simple responsive UI at `/` plus interactive API docs at `/docs`.
- Local SQLite for engineering smoke tests; Docker Compose + Postgres for **development only**.

## Phạm vi đang phát triển

Workforce, registry, QA theo phiên bản và journal chiến dịch có các đường chạy nội bộ được kiểm thử. Những phần còn mở gồm billing thật, adapter Marketing có quyền ghi, phục hồi vận hành production và nghiệm thu bởi người hành nghề. Xem trạng thái theo từng phạm vi trong [sổ V1](docs/IMPLEMENTATION_STATUS.md) và [cổng phát hành](docs/SECURITY_AND_GA_BLOCKERS.md).

## Run locally (Windows PowerShell)

Install Python 3.12+ and Git. From repository folder:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python scripts/init_env.py
python -m pytest -q
python -m uvicorn app.main:app --no-proxy-headers --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and http://127.0.0.1:8000/docs.

## Run locally (macOS/Linux)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/init_env.py
python -m pytest -q
python -m uvicorn app.main:app --no-proxy-headers --reload --host 127.0.0.1 --port 8000
```

## Docker + Postgres (development, not production)

Run `python scripts/init_env.py` for a fresh checkout or follow the [Docker-only setup](HANDOFF.md#2-chạy-bằng-docker-từ-một-checkout-sạch). For an existing database retain its matching keys and follow the version-specific upgrade instructions. The migration service runs before the API, which uses the restricted `amc_runtime` login.

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 api
```

Open http://127.0.0.1:8000 for development. Local email verification uses a synthetic mailbox. Public delivery and public-ingress qualification remain open. [Identity admission](docs/IDENTITY-ADMISSION.md) · [PostgreSQL client isolation report](docs/reviews/POSTGRES_CLIENT_ISOLATION_20261123.md)

## First interactive workflow

1. Register an account, verify its address using the private development mailbox, then sign in. Create an Agency or In-house workspace, or accept an invitation to an existing workspace. [Onboarding walkthrough](docs/PR16-ONBOARDING.md)
2. Agency: add a Client. In-house: the initial `Internal Marketing` client exists.
3. Create a Brand; record brand rules and verified product facts.
4. Create a Campaign with objective and a meaningful brief.
5. Click **Phân rã việc**. Exactly seven deterministic task records are created; repeat is idempotent.
6. Use **Điều phối Marketing AI** to request a brief, select specialist skills and authorize a budget for the worker.
7. Review API endpoints for deliverables and external actions; they always require independent approval and the actual side effect is disabled.

## Product decisions and collaboration

- Research matrix: `docs/GITHUB_RESEARCH_AND_REUSE.md`
- Architecture decision: `docs/ADR-001-OWN-SaaS-CORE.md`
- Codex local handoff: `docs/CODEX_LOCAL_HANDOFF.md`
- Red-team/checklist: `docs/SECURITY_AND_GA_BLOCKERS.md`
- Original complete Product Spec: `docs/PRODUCT_SPEC_V1.md`
- All 37 logical roles: `catalog/agent_roles.json` (`specification_only`)
- All 24 workflow contracts: `catalog/workflows.json` (`specification_only`)

**Commercial reuse note:** No third-party source files are copied into this starter. Dependencies are installed by package managers. Before selectively importing MIT skill assets or OSS code, review attribution, upstream version, license constraints and test each artifact. See `docs/GITHUB_RESEARCH_AND_REUSE.md`.
