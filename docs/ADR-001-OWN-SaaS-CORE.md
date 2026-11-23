# ADR-001 — Own the SaaS and Marketing Domain Core; Integrate OSS Modules by Contract

Date: 2026-11-23 | Status: **Proposed for independent Codex challenge, not irrevocably frozen**

## Context

AMC is a **commercial multi-tenant Marketing AI Company** with two operating modes (agency/in-house), 37 logical roles, 49 product modules and 24 approved workflows. We need true tenant/brand isolation, accountable humans, billable consumption, versioned work products and safe external actions. An AI-agent demo or generic orchestration dashboard does not provide these guarantees automatically.

## Options reviewed

A. **Fork Paperclip into a multi-tenant Marketing SaaS.** Mature company organization, goals, agent scheduling, budgets, approvals; MIT. But very large code surface and repeated public severe security advisories including cross-tenant API token minting and unauthorized RCE. Must conduct independent penetration test, pin patched release, review all endpoint authorization, runtime permissions, and identity/secret access. Risk of heavy upstream merge conflicts and Marketing domain mismatch.

B. **Build AMC SaaS & Marketing domain, import or integrate selected OSS components.** More initial code, but clear domain/tenant model, commercial ownership, controlled dependencies, simpler product specialization. Use OSS framework for agent planning, specialized marketing skills after audit, and optional external tools via strict adapters. Requires discipline to avoid rewriting the whole ecosystem.

C. **Fork Opensoul or Outclaw.** Marketing roles and workflows closely match concept but repos are small/dated; Opensoul is preconfigured Paperclip, not an independently security-audited SaaS. Better as reference role/brief templates.

## Decision: Option B as initial engineering recommendation

- **Frontend target:** Next.js/TypeScript for the finished customer SaaS; the bootstrap has an intentionally small native responsive UI for API smoke testing.
- **Core API and data ownership:** FastAPI/Python in bootstrap, Postgres as system of record; keep domain modules and APIs explicit. A later all-TypeScript core is not ruled out but needs an ADR showing clear cost benefit. Avoid a mixed backend split without boundaries.
- **Durable business processes:** plan Temporal for long-lived processes, approvals, timers, retries and external idempotent calls; introduce only when an end-to-end workflow requires it. LangGraph is the **single preferred AI graph runtime** for agent work, with structured state and checkpoints. Distinguish Temporal business workflow from AI graph; do not use CrewAI + LangGraph + Agents SDK in the same main execution path by default.
- **Model gateway:** optional LiteLLM OSS gateway, customer-owned BYOK and managed-provider accounting. Source license: MIT for OSS code outside enterprise directory; evaluate gateway as service or library under actual terms.
- **Observability:** OpenTelemetry + optional self-hosted Langfuse OSS; exclude enterprise-only folders unless licensed.
- **Knowledge:** Postgres + pgvector, object storage with tenant-scoped authorization. Do not merge knowledge from different clients/brands.
- **Marketing skills:** select and adapt specific MIT files from Digital Marketing Pro and Marketing Skills OS, with attribution and validation; do not wholesale ingest hundreds of instructions.
- **Social publishing:** own capability contract; use official API adapters and consider optional service integration. Postiz AGPL, Mautic GPL: no code copying into a closed-source SaaS without legal review. Mixpost Lite MIT has limited network breadth and PHP dependency.
- **Integration flows:** Activepieces Community MIT may be a separate connector engine; enterprise modules require separate license. Avoid unlicensed resale of restricted n8n functionality.
- **Security:** tenant-permission checks in code + Postgres RLS before GA; security tests, signed side-effect approval, secret isolation, consent, allowlist and egress controls. User prompts never grant new permissions.

## Explicit non-decisions

- No deployment to production, no GitHub repository creation, no external account connection, no commercial license approval have occurred.
- The bootstrap does **not** claim all 37 roles, 24 workflows or 49 modules are running.
- 2026 vendor APIs and pricing must be reverified before each integration build.

## Challenge criteria for Codex

Codex may reject this ADR with **reproducible evidence**, such as a 2-tenant security exploit, license contradiction, migration test, cost model or a superior documented design. Require side-by-side pros/cons, precise repository+file evidence, final recommendation and migration plan. Do not silently rewrite the ADR.
