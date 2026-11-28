# Security, Reliability and General Availability (GA) Blockers

**AMC-R68-01 · P3 · OPEN (static).** Sau khi phân loại câu thủ tục, trường diagnostic cũ có thể còn trên span. Marketing Studio có thể hiển thị diagnostic trước outcome. Cần phân biệt signoff lịch sử với eligibility QA hiện tại khi mandate bị thu hồi. Chưa tái hiện bằng browser. Trong lần chỉnh presentation có liên quan, viết RED browser/API rồi sửa hiển thị nếu xác nhận; giữ nguyên canonical report và historical receipt digest. [Vị trí cần kiểm](../app/static/marketing-studio.js#L124) · [Nguồn trạng thái](../app/c3_evidence_review.py#L135)

**AMC-R67-01 (P2)** có đường xử lý nội bộ giới hạn theo từng câu và từng lần lưu, chờ Independent Review. **AMC-R67-02 (P2 diagnostic)** tái hiện lời hứa giao nhanh trong Strategy; hai biến thể đều bị từ chối ký và không tạo lệnh bàn giao. Giới hạn phát hiện của structural QA vẫn còn. [Tái hiện, denial và bằng chứng quyết định](evaluation/research-instruction/README.md)

**WF-08, AMC-R60-03 — production qualification open.** Preview rendering currently holds database locks while it consumes CPU and writes media. Infrastructure and the Workforce owner must measure lock duration, concurrent work across tenants, request latency, CPU, peak memory, storage and rollback/recovery on synthetic data before production approval. [Test design and decision criteria](evaluation/connected-workforce/SEMANTIC-REVIEW.md#render)

PR #59 merged for internal development at `4140563a89539acd19f1a7d5a16662c8dec5f6af`. Production and Commercial GA remain **NO-GO**. Connected synthetic events establish traceability only. Practitioner acceptance, customer rights, media authority, measured outcomes and full costs are open. [Scope and technical receipts](evaluation/connected-workforce/README.md)

PR #58 merged for internal engineering at `1c40ad3185ac49415c3f555bb5b6406e2cdd8cb1`. The WF-08 follow-up uses synthetic material with a scoped job, revision-bound QA and a local deterministic producer. External publishing, model budgets, customer media rights, real outcomes and practitioner release approval remain separate gates. [Run evidence and outstanding gates](evaluation/workforce-video/README.md)

The internal merge of #57 at `26578088519d99f4aed5be9c516ac247f3d4735e` includes the corrected commercial unit, scoped pre-assignment withdrawal and role-specific treatment disclosure. Production and Commercial GA are **NO-GO**. Sandbox campaign receipts, local grammar validation and technical editorial scores do not establish practitioner acceptance, provider permissions or actual unit economics. [Internal merge CI](https://github.com/datnv41001/ai-company/actions/runs/45780019694) · [Current handoff](../HANDOFF.md)

Main after #56 includes synthetic Sales permissions, intake metrics and the private practitioner-pilot procedure. Producer disclosure and customer withdrawal are under follow-up review. Practitioner acceptance, full costs per accepted job and authorization for external platform writes remain outstanding. Production and Commercial GA are **NO-GO**. [Main receipt](evaluation/department-review/MAIN-56.json) · [Review scope](evaluation/department-review/MARKET-HANDOFF.md)

AIRC v3 chỉ được sử dụng trên fixture tổng hợp. Kiểm định độc lập theo nghĩa vụ, custody giữa các OS principal, coverage ngữ nghĩa và mở rộng reviewer vẫn là cổng riêng. [Kết quả và các ngưỡng thử nghiệm](../engineering/airc500/UNION-STUDY.md).


Engineering review tooling remains fixture-only. Production and autonomous real-repository review are still on hold pending independent host isolation, signing-key custody, and domain-quality gates. [Runtime boundary](../engineering/airc500/RUNTIME-HARDENING.md) · [Measured fixture evaluation](../engineering/airc500/QUALITY-EVALUATION.md).

**Current status: NO-GO for production.** The bootstrap is intentionally safe for local development and demonstrates scoped API behavior; it is not a commercial service.

Schema 3 introduced PostgreSQL row policies for client delivery. At the PR #48 baseline the schema is v26, with Business v3, C3 v5 and sandbox ops/2. The unchecked gates below cover the entire product. An internal control can have passing tests while the broader production gate remains open. [Current scope and evidence](IMPLEMENTATION_STATUS.md) · [Handoff](../HANDOFF.md)

## Stop-ship (P0) before ANY public deployment

- [ ] Auth: verified email, invitation acceptance, rate limits, time-limited abuse protection, password reset, MFA and optional SSO; secure cookie/session strategy and CSRF policy; JWT signing key rotation and explicit revocation.
- [ ] Tenant isolation: Postgres row-level security with session-scoped tenant identity, enforced default-deny RLS policies on ALL business tables; tenant/brand/client relationship constraints; regression tests on IDOR at API/DB/file/vector/cache/queue/logs.
- [ ] Replace `Base.metadata.create_all()` with reviewed Alembic migrations; automatically block incompatible migrations and test rollback/restore.
- [ ] Worker runtime: durable persistent run state, retries with upper bounds, timeout, idempotency keys, DLQ, cancellation and checkpoint; secure job runner with task-scoped credentials and policy snapshot.
- [ ] Real LLM safety: per-tenant budgets/rate limits, model fallback policy, structured outputs, source evidence, anti-injection tests, redaction of personal data/secrets, versioned prompts/skills, actual usage-cost ledger.
- [ ] External actions: official OAuth permissions, connection ownership, secret vault, approval policy including two-person rule or explicit owner override governance, prepared action payload hash, connector-specific idempotency/receipts, reconciliation and rollback.
- [ ] Billing: PSP integration, subscription entitlement enforcement, invoices/tax/refund/trial handling, webhook signature checks and strict event idempotency; distinguish SaaS revenue, AI usage cost and client advertising spend ledgers.
- [ ] Background services: queue, scheduled jobs, database backup & tested restore, monitoring/alerts and incident response; readiness/liveness probes and staging/production separation.
- [ ] Privacy and legal: DPA, subprocessors, deletion/export, lawful basis for customer data, ad-platform rules, content/IP rights, consent and unsubscribe enforcement.
- [ ] Secure deployment: production secret vault/KMS, TLS, CSP, HSTS, SAST/dependency audits, SBOM, restricted network egress, sandbox hardening; no shared Docker socket/host root privileges.
- [ ] Independent security review, threat model, load test and resilience exercises; capture evidence and signoff.

## Current temporary compromises (not acceptable for GA)

- SQLite for local smoke testing; only application-level tenant checks, not Postgres RLS.
- SAA-02 verifies addresses through a private synthetic mailbox and requires acceptance for invited members. Production email delivery, abuse protection and account recovery remain open. See the [verified identity handoff](PR15-IDENTITY.md) and [v19 onboarding threat model and backlog](PR16-ONBOARDING.md).
- The v21 candidate limits registration, login, email verification and invitation delivery. Public ingress quotas, abuse monitoring and NAT threshold tuning still need operational acceptance.
- Device sessions support bounded refresh, revocation and reauthentication. Production ingress and recovery qualification remain open. [Device session behavior](DEVICE-SESSIONS-A1.md)
- No connector credentials are stored by this starter. All actual side effects are disabled.
- LLM draft has no confirmed external factual evidence; do not present output as research or final recommendations without human review.
- The reviewed migration runner and tested upgrade paths cover the supported development schema. Production backup custody, restore drills in the target environment and operational signoff remain release gates. [Migration runner](../migrations/apply.py) · [Writer cutover](evaluation/sandbox-operations/CUTOVER.md)
- The global catalog declares 37 logical roles. Named profiles execute a measured subset on authorized jobs. See the [register](IMPLEMENTATION_STATUS.md) for role and workflow evidence.
- Campaign `plan` creates 7 deterministic placeholder tasks. It is **not** a running multi-agent workflow.
- Audit events are app-managed, not immutable or cryptographically sealed. No PII retention policy yet.
- No test that can certify an AI provider's data retention terms or guarantee content rights.

## Mandatory negative tests to add

1. Tenant A user cannot read/write/approve B brands, campaigns, tasks, artifacts, knowledge, traces, skills, secrets or action receipts.
2. Agency A client reviewer cannot access another client/brand inside the same tenant.
3. User-controlled IDs in request body cannot override verified tenant/session scope.
4. Agent tool calls cannot change policies, roles, OAuth scopes, budget or approvals by text instructions.
5. Failed/replayed webhooks cannot duplicate ad spend, postings, emails or invoices.
6. Revoked token, suspended tenant, zero budget and expired approval all fail closed.
7. Third-party prompt injection embedded in marketing research pages does not gain tool authority.
8. Accidental error/trace/log response cannot reveal secrets or other tenants' data.

## Completion evidence standard

Each product module and each of the 24 workflows needs: scenario ID, code commit, fixture, inputs, expected output, automated tests, recorded run artifact, negative tests, reviewer identity, and decision. All 49 modules and 24 workflows must be GA-approved for the single complete V1.0.

## Giới hạn thao tác danh tính đang review nội bộ

Schema đề xuất v21 cho đăng ký, đăng nhập, xác minh và cấp/gửi lại lời mời. Hồ sơ nghiệm thu tiếp tục theo dõi ngưỡng NAT, telemetry, ranh giới proxy, email vận hành, vòng đời session, phục hồi mật khẩu, MFA/SSO và chuyển quyền owner. [Thiết kế, nghiệm thu và rollback](IDENTITY-ADMISSION.md).

## Business Profile và Brand Intelligence · gate đang mở

C1 v22 đã có kiểm thử PostgreSQL native 16.16 cho signed LOGIN, giao dịch thu hồi trước/sau QA/share và giới hạn dữ liệu được đưa vào snapshot. Gate thương mại còn chờ review ứng dụng, phân quyền worker và portal khi kích hoạt C3, qualification thực của người duyệt và kiểm thử các tuyên bố Marketing ngoài fixture. [Bằng chứng và phạm vi còn mở](business-profile/C1-RUNBOOK.md)

C0 có fixture tổng hợp cho dữ kiện thương mại và tính hợp lệ của nguồn. Để đóng gate sử dụng dữ liệu Marketing, C1 phải chứng minh cô lập tenant/client/brand, đúng SKU/variant/offer, quyền sử dụng nguồn và hai thứ tự transaction thu hồi/share. C2–C4 cần bằng chứng desktop/mobile, WF-03/WF-13 trên đúng snapshot và thẩm định nghiệp vụ độc lập. Commercial GA giữ NO-GO. [Kế hoạch và phép đo](business-profile/README.md)

## SAA-02 · session và recovery

[Thiết kế và tiêu chí nghiệm thu](IDENTITY-SESSION-RECOVERY.md) bao gồm thu hồi giữa hai worker, recovery khi cooldown, xoay khóa và so sánh OIDC. Những gate này chờ triển khai và kiểm thử độc lập.
