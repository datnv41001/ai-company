# Codex Local Handoff and Two-Way Engineering Review

Historical commissioning brief for the starter. For the current checkout use the [knowledge map](KNOWLEDGE_MAP.md), [operating handoff](../HANDOFF.md) and [implementation register](IMPLEMENTATION_STATUS.md).

## 1) Immediate mission

Read the product spec and ADR. Run the starter **as-is** locally and tests. Report actual functionality, security defects, licensing contradictions and architecture challenges. **Do not assume the existing recommendation is correct.** You are an independent challenger, not a rubber stamp.

### Initial checks (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Edit JWT_SECRET to a long random value; do not paste secrets into Codex/chat
python -m pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Inspect http://127.0.0.1:8000 and `/docs` with synthetic user data. Keep real LLM keys and third-party connector secrets out of logs and Git.

## 2) Independent review priorities

- Verify every existing route enforces tenant membership and brand/client parentage; create adversarial tests for IDOR and privilege escalation.
- Confirm data schema supports Agency and In-house modes; propose `tenant -> client -> brand -> campaign -> task -> deliverable -> approval` architecture.
- Compare Paperclip fork vs dedicated SaaS core using **real code/CI/license evidence** and a rough five-year maintenance model.
- Verify LangGraph vs CrewAI vs OpenAI Agents SDK capabilities and implementation burden; recommend one primary agent runtime.
- Audit Digital Marketing Pro and Marketing Skills OS **skill by skill**, not by overall popularity; map against 37 roles and 24 workflows.
- Test Docker + Postgres locally if Docker is available. Verify `POSTGRES_PASSWORD` quoting, App mode, startup logs and network bindings.
- Audit original `docs/PRODUCT_SPEC_V1.md` for domain contradictions, missing business approvals or illegal API assumptions.

## 3) Challenge protocol (Codex <-> ChatGPT)

Write a reviewer report in `docs/reviews/CODEX_REVIEW_YYYYMMDD.md` with:

```
# Decision: ACCEPT / CHALLENGE / BLOCK
## Reproducible evidence (commands, actual output, file path and line)
## Security and compliance (P0 / P1 / P2)
## Architecture disagreement (proposal, tradeoffs, cost, migration)
## Licensing findings (repo URL, path, commit SHA, exact license)
## Functionality truth table (implemented/tested/spec-only/blocked)
## Recommended patch order and tests
## Questions / challenges to ChatGPT reviewer
```

Do not paste credentials, customer data, OAuth refresh tokens or huge private logs. Redact them. Bring the resulting report (and optionally diff) back into the ChatGPT conversation. ChatGPT can review and reply, but it has no direct access to your local Codex process unless you provide outputs or connect the repository explicitly.

## 4) Build protocol

- `main` branch protected later; changes in feature branches + PR with acceptance criteria and tests.
- One change should remain reversible; no massive rewrites without a proven migration plan.
- Add one workstream at a time while retaining the single **full product V1.0** as GA deliverable (engineering staging is not customer MVP releases).
- For each feature: design API/DB contract -> tests -> implementation -> security negative tests -> UX -> observability -> review evidence.
- No direct production deployment or actual ad spend as part of automatic tests.

## 5) Next engineering deliverable expected from Codex

**A.** Security and architecture review of the starter. **B.** A fully reasoned ADR-002 selecting final durable orchestration and persistence boundaries. **C.** An executable database migration + RLS policy spike on Postgres with two-tenant negative tests. **D.** A brand-specific structured marketing brief and content workflow implementation with checkpoints and human approval.

Before coding large features, return the review for architectural challenge. We explicitly prefer evidence-based disagreement over unconditional agreement.
