# GitHub Reuse Audit — AI Marketing Company, 23 Nov 2026

## Research standard

This is repository metadata and README/license inspection, **not** runtime certification, penetration testing or legal opinion. Dates, stars and feature claims change. Keep an upstream ref/commit, SPDX or original license notice and explicit product owner for every copied file. No upstream code is copied into this bootstrap.

### Primary sources and decisions

| Project | Primary GitHub URL | Licensing status reviewed | Reuse direction | Engineering caveat |
|---|---|---|---|---|
| Paperclip | https://github.com/PaperclipAI/paperclip | MIT | **Reference / isolated proof-of-concept only** | Strong organization, budgets, approval, multi-company; recurring high/critical advisories incl tenant breaks and RCE; large merge surface |
| Opensoul | https://github.com/iamevandrake/opensoul | MIT | **Reuse role/department concepts** | Marketing-specific Paperclip configuration, not independently proven commercial SaaS |
| Outclaw | https://github.com/outmarkhq/outclaw | MIT | **Study 21-role design, structured brief, org chart** | Small repository, limited evidence of integrations, no production E2E certification |
| Digital Marketing Pro | https://github.com/indranilbanerjee/digital-marketing-pro | MIT | **Selective skills & business workflows after eval** | Thousands of lines of marketing instructions do not imply tested API operations; version and claim verification needed |
| Marketing Skills OS | https://github.com/scayver/marketing-skills | MIT | **Selective templates/evaluation ideas** | Large skill surface; inspect prompts against injection, false claims, regulations |
| LangGraph | https://github.com/langchain-ai/langgraph | MIT | **Primary AI workflow runtime recommendation** | Persistent state is not automatically business idempotency, payroll, consent, approvals or external retries |
| CrewAI | https://github.com/crewAIInc/crewAI | MIT | **Alternative/benchmark, not a second mandatory core** | Role-based composition easy but risk mixing orchestration stacks |
| OpenAI Agents SDK | https://github.com/openai/openai-agents-python | MIT | **Alternative runtime/adapter** | Good tools and handoffs; still own tenancy, state and cost controls |
| Activepieces Community | https://github.com/activepieces/activepieces | MIT CE, commercial enterprise parts | **Optional connectors service** | Verify exact included CE features and embedding/cloud restrictions before choosing |
| LiteLLM | https://github.com/BerriAI/litellm | MIT core, separate enterprise | **Model gateway candidate** | OSS core only; gateway must enforce tenant IDs, secrets, budgets and rate policies |
| Langfuse | https://github.com/langfuse/langfuse | MIT core, enterprise folders separate | **Observability/eval candidate** | Do not leak prompts, PII, secrets or cross-tenant traces |
| Mixpost Lite | https://github.com/inovector/mixpost | MIT Lite | **Investigate social schedule service** | Only a subset of channels in Lite; PHP service and lower maintenance cadence |
| Postiz | https://github.com/gitroomhq/postiz-app | AGPL-3.0 | **External comparison; legal review before code reuse** | Broad connectors; network app approvals still necessary; network-AGPL implications |
| Mautic | https://github.com/mautic/mautic | GPL-3.0+ (LICENSE.txt) | **External API reference/integration** | Mature CRM/lifecycle automation; copyleft if distributing derived code; extra infrastructure |
| Umami | https://github.com/umami-software/umami | MIT | **Analytics integration candidate** | Does not replace Google Ads, GA4 or actual conversions without sources |
| GrowthBook | https://github.com/growthbook/growthbook | MIT core + enterprise | **Experimentation integration candidate** | Advanced product-analytics scope is separate from AMC OLTP |
| n8n | https://github.com/n8n-io/n8n | Sustainable Use License | **Not a freely rebrandable workflow SaaS engine** | Need permission/license for selling workflows to tenants |
| Dify | https://github.com/langgenius/dify | Apache-like modified, specific conditions | **Reference, not primary multi-tenant SaaS base** | Multi-tenant resale and front-end branding restrictions may apply |
| Kortix CompanyOS | https://github.com/kortix-ai/CompanyOS | Elastic License 2.0 | **Reference only** | Hosted managed-service restrictions; not MIT/Apache |

### Security evidence

- Paperclip advisories: https://github.com/PaperclipAI/paperclip/security/advisories
- Cross-tenant API key IDOR: https://github.com/PaperclipAI/paperclip/security/advisories/GHSA-3xx2-mqjm-hg9x (affected <= 2026.410.0-canary.1; patched 2026.416.0)
- Required negative tests from Paperclip threat model: https://github.com/PaperclipAI/paperclip/blob/master/doc/connections/SECURITY-THREAT-MODEL.md
- **Risk assessment:** Even if the identified historical bugs are patched, we cannot certify a fork secure without independent route-level and deployment tests.

### Important vendor API facts

- Meta Marketing API access tiers/App Review: https://developers.meta.com/blog/updates-to-ads-management-standard-access-feature/ (May 4, 2026)
- Google Ads API developer-token sunset Sept 9, 2026: https://developers.google.com/google-ads/api/docs/api-policy/developer-token . New projects use Cloud API enablement and appropriate production-access tier. Do NOT depend on old token-specific onboarding.
- Official OAuth permissions, quota, business verification, token expiry, content policies and webhooks are per-platform, not automatically granted by any GitHub social scheduler.

### Community field reports (anecdotal, not representative statistics)

- https://www.reddit.com/r/AI_Agents/comments/1v0xs0p/is_anyone_actually_orchestrating_multiagent/ — silent failures and retry runaway.
- https://www.reddit.com/r/aiagents/comments/1rpq0cy/lessons_from_running_a_12_agent_coordination/ — strict schema and handoff checkpoints.
- https://www.reddit.com/r/aiagents/comments/1tunuvc/anyone_actually_using_multiagent_ai_in_production/ — deterministic router, actor scopes, human approval.
- https://www.reddit.com/r/marketingagency/comments/1xszs4a/what_it_actually_takes_to_make_an_agency_team_23x/ — shared client context and repeatable agency workflows.
- https://www.reddit.com/r/agency/comments/1qoffyt/the_automation_that_made_the_biggest_difference/ — connectors and normalized reports can outperform complex agent chat.

### Combination rules

1. **Do not fork two whole SaaS platforms into one codebase.** Maintain bounded integration interfaces and component responsibility.
2. Prefer **one primary AI graph framework**, not LangGraph + CrewAI + Agents SDK loops in a circle.
3. Skills are **untrusted procedural content**. Run evaluations and compliance review before enabling skills or granting tools.
4. Every connector needs a manifest: supported actions, required scopes, rate limits, quota, preview, write permissions, approval policy, reconciliation, receipt and retry.
5. Keep the source of truth of brand facts, legal claims, spend ceilings and marketing metrics separate from natural-language agent memory.
6. A successful user story requires a business-accepted deliverable or verified external action receipt; a well-formed LLM response alone is insufficient.

### Additional confirmation needed before code import

- Pin commit SHAs; inspect subfolders and transitive licenses; scan known CVEs.
- Write adapter contract and sandbox spike with at least two independent tenants/brands.
- Confirm marketing-skill quality with real annotated briefs and expert QA; do not run all at once.
- Obtain product-owner sign-off on licensing and third-party terms before shipping third-party-derived code.
