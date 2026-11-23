# AI Marketing Company (AMC) — Engineering Bootstrap

**[Chạy bằng Docker và tiếp quản trên máy mới → HANDOFF.md](HANDOFF.md)**

**QA theo phiên bản.** Khi sửa tiêu đề hoặc nội dung gửi khách, hệ thống đánh giá lại claim và yêu cầu người QA duyệt đúng SHA-256 của bản đang xem. [Hợp đồng API, nâng cấp v7 và phục hồi](docs/ADR-007-QA-EVIDENCE-REVISION.md).

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

- Register an organization as Agency or In-house; login with bearer JWT and Argon2 password hashing.
- Persist clients, brands, campaigns, workflow skeleton tasks, deliverables, action approvals and audit events.
- Scope API resources by tenant and client. Each external membership belongs to one client per agency. It can read that client profile and explicitly shared snapshots. Commenting and deciding require separate grants. PostgreSQL enforces row policies in addition to the API checks. Internal `viewer` members retain agency-wide read access.
- Create an idempotent **deterministic** 7-task marketing campaign plan (NOT an LLM-generated plan).
- Agency staff queue a sourced brief through Workforce. Model credentials and provider calls belong to the budgeted worker.
- Independent human review of deliverables and external-action proposals; self-approval is forbidden.
- External publishing, ad spending, emailing, CRM writes and deletes are **hard-disabled**, even after approval, pending official connectors and policy checks.
- Simple responsive UI at `/` plus interactive API docs at `/docs`.
- Local SQLite for engineering smoke tests; Docker Compose + Postgres for **development only**.

## What's not implemented yet (must not be represented as production-ready)

All remaining full-scope modules (billing, invitations, SSO/MFA, full RLS, distributed execution, LangGraph/Temporal worker runtime, connectors, object storage, data quality, complete 37-agent contracts, 24 end-to-end workflows, brand-level policy, app reviews, queue and disaster recovery) still need development, tests and deployment qualification. See `docs/PRODUCT_SPEC_V1.md` and `docs/SECURITY_AND_GA_BLOCKERS.md`.

## Run locally (Windows PowerShell)

Install Python 3.12+ and Git. From repository folder:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Edit .env: set a unique random JWT_SECRET
python -m pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and http://127.0.0.1:8000/docs.

## Run locally (macOS/Linux)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
# Set a strong JWT_SECRET.
python -m pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Docker + Postgres (development, not production)

Set separate random `POSTGRES_PASSWORD`, `AMC_RUNTIME_PASSWORD` and `JWT_SECRET` values in `.env` (do not commit secrets). Use URL-safe database passwords. The migration service runs before the API, which uses the restricted `amc_runtime` login.

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 api
```

Bound to localhost only: http://127.0.0.1:8000. **Development use only.** Hardened rate limits and email verification remain outstanding. For migration, client grants, evidence and rollout of existing viewers, see the [PostgreSQL client isolation report](docs/reviews/POSTGRES_CLIENT_ISOLATION_20261123.md).

## First interactive workflow

1. Register a tenant; choose `agency` or `inhouse`.
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
