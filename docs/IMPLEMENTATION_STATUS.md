# Implementation Truth Table — AI Marketing Company V1.0

These **49** entries are required for commercial GA, and **none** is fully implemented. Partial functionality in the bootstrap must never be described as module acceptance.

| Code | Product module | Starter status | GA acceptance |
|---|---|---|---|
| SAA-01 | Website thương mại & đăng ký | Spec only | NOT PASSED |
| SAA-02 | Identity/Access | Partial: local JWT/Argon2/tenant roles; email/SSO/MFA missing | NOT PASSED |
| SAA-03 | Tenant Lifecycle | Partial: tenant creation; lifecycle missing | NOT PASSED |
| SAA-04 | Company Builder | Partial: role catalog only | NOT PASSED |
| SAA-05 | Subscription & Billing | Spec only | NOT PASSED |
| SAA-06 | Usage & Cost | Spec only | NOT PASSED |
| SAA-07 | Marketplace nội bộ | Spec only | NOT PASSED |
| SAA-08 | Workspace / Team | Spec only | NOT PASSED |
| SAA-09 | Support/Admin | Spec only | NOT PASSED |
| AGY-01 | Client CRM | Partial: client records only | NOT PASSED |
| AGY-02 | Discovery & Brief | Partial: campaign brief only | NOT PASSED |
| AGY-03 | Commercial | Spec only | NOT PASSED |
| AGY-04 | Client Portal | Partial (schema 3): shared review snapshots, scoped grants, portal UI; see [handoff](../HANDOFF.md) | NOT PASSED |
| AGY-05 | Project/PMO | Partial: campaign + 7 deterministic task records | NOT PASSED |
| AGY-06 | Account Operations | Spec only | NOT PASSED |
| AGY-07 | Service Finance | Spec only | NOT PASSED |
| AGY-08 | Feedback & Change | Partial: comments, change requests, resubmission | NOT PASSED |
| MKT-01 | Market Intelligence | Spec only | NOT PASSED |
| MKT-02 | Audience & Customer Journey | Spec only | NOT PASSED |
| MKT-03 | Brand Management | Partial: brand guidelines text only | NOT PASSED |
| MKT-04 | Product Marketing & GTM | Spec only | NOT PASSED |
| MKT-05 | Marketing Strategy | Partial: optional single LLM draft; no full strategy workflow | NOT PASSED |
| MKT-06 | Integrated Campaign | Spec only | NOT PASSED |
| MKT-07 | Content & Editorial | Spec only | NOT PASSED |
| MKT-08 | Creative Asset Studio | Spec only | NOT PASSED |
| MKT-09 | Social & Community | Spec only | NOT PASSED |
| MKT-10 | Paid Media / Ads | Spec only | NOT PASSED |
| MKT-11 | SEO/GEO | Spec only | NOT PASSED |
| MKT-12 | Website & CRO | Spec only | NOT PASSED |
| MKT-13 | CRM & Lifecycle | Spec only | NOT PASSED |
| MKT-14 | PR & Influence | Spec only | NOT PASSED |
| MKT-15 | Ecommerce/Trade | Spec only | NOT PASSED |
| MKT-16 | Marketing Data Hub | Spec only | NOT PASSED |
| MKT-17 | Analytics & Attribution | Spec only | NOT PASSED |
| MKT-18 | Reporting & Intelligence | Spec only | NOT PASSED |
| MKT-19 | Budget & Optimization | Spec only | NOT PASSED |
| MKT-20 | Localization & Regional | Spec only | NOT PASSED |
| AIO-01 | AI Director Command Center | Spec only | NOT PASSED |
| AIO-02 | Orchestration | Spec only | NOT PASSED |
| AIO-03 | Agent Registry | Spec only | NOT PASSED |
| AIO-04 | Model Gateway | Spec only | NOT PASSED |
| AIO-05 | Tools/Connectors Gateway | Spec only | NOT PASSED |
| AIO-06 | Knowledge & Memory | Spec only | NOT PASSED |
| AIO-07 | Human-in-the-loop | Partial: independent agency QA and client decision | NOT PASSED |
| AIO-08 | Artifact/Version | Partial: immutable, hashed client-facing review snapshots | NOT PASSED |
| AIO-09 | Evals & QA | Spec only | NOT PASSED |
| AIO-10 | Security & Audit | Spec only | NOT PASSED |
| AIO-11 | Scheduling & Incident | Spec only | NOT PASSED |
| AIO-12 | Usage Economics | Spec only | NOT PASSED |

## Agent & workflow catalog
- `catalog/agent_roles.json` has **37 role definitions**, status `specification_only`.
- `catalog/workflows.json` has **24 workflow specifications**, status `specification_only`.
- `/campaigns/{id}/plan` creates **7 deterministic work tasks** only.
- AI strategy draft uses one optional provider call and is unapproved by default.

## Reporting rules
Do not show percentages of GA completion based solely on count of repository files or role names. Acceptance requires integrated business workflow test evidence, security and legal signoff.
