# Security, Reliability and General Availability (GA) Blockers

**Current status: NO-GO for production.** The bootstrap is intentionally safe for local development and demonstrates scoped API behavior; it is not a commercial service.

Schema 3 enforces PostgreSQL row policies for client delivery and includes populated upgrade tests. See the [handoff](../HANDOFF.md) for current coverage. The checklist below addresses the full product.

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
- JWT bearer token is held only in frontend memory; refresh requires re-login. Production session UX needs redesign.
- No connector credentials are stored by this starter. All actual side effects are disabled.
- LLM draft has no confirmed external factual evidence; do not present output as research or final recommendations without human review.
- No stable migration script; production app startup is intentionally refused.
- Global role catalog declares 37 roles only: none automatically executes.
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
