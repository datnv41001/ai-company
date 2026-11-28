# Studio cutover regression on the first draft

The first draft head was `1eb5187b74aa035c213e9c7778348c1c9253d74a`. Its trial merge was `21c606fb4074da6af78b31fa37da35ec0fb18825`. The product guide browser exercise, full regression and v26 archive ran before a later Studio upgrade check failed. [Push workflow](https://github.com/datnv41001/ai-company/actions/runs/46095542152) · [Pull request workflow](https://github.com/datnv41001/ai-company/actions/runs/46095553782)

On a historical Studio database missing both guards, startup raised the WF-06 authority error before reaching the shared Studio writer check. The historical upgrade test requires the operator to receive the shared writer diagnostic first. Both checks denied startup. The repair places the guide check after the shared database checks and before worker readiness can return. The historical assertion is unchanged. JUnit upload now also runs when a later upgrade step fails.

The Windows run that spanned edits before the first commit recorded 814 passed, 10 failed and 2 skipped. The failing cases involved worker readiness, a worker subprocess or dispatcher telemetry. The clean predecessor checkout recorded 802 passed and 2 skipped. For an exact candidate comparison use the checkout and test logs for each GitHub job.

## Model usage for the first draft

All three API jobs recorded 824 passing tests and two skips. Each separately restored 34 populated tables, the guide authorization check and four guide documents before the Studio diagnostic failed. The three Compose/Chromium jobs and the three standard Qwen jobs passed on workflow attempt 1. The optional model was skipped.

After the repair, all four local PostgreSQL Studio rehearsals from writer v1, v2, v3 and v4 to v5 passed using the original historical binaries. Each rejected three old-writer operations, accepted the current writer and preserved eight populated tables through rollback and migration replay. The 22 guide tests and the 10 Windows cases identified above also passed on a fresh database. [Guide JUnit](repaired-guide.xml) · [Windows regression JUnit](repaired-windows.xml) · [Rehearsal and pinned historic versions](../../../tests/check_studio_cutover.py)

Each row links to the standard Qwen artifact from one job. The campaign, named journal and parallel measurements cover different parts of the exercise. The artifact records model provider fees for the named journals. GitHub runner billing was unavailable.

| Revision | Job seconds | First-pass stages | Runtime retries | Campaign tokens in/out | Campaign outcomes | Named journals, tokens in/out and provider fees | Two-slot measurement |
|---|---:|---:|---:|---:|---|---|---|
| [push/head](https://github.com/datnv41001/ai-company/actions/runs/46095542152/artifacts/15243164111) | 478 | 35/38 | 0 | 10767 / 3517 | {'recipient_revoked': 3, 'ok': 35}, unconfirmed 3 | {'ok': 21}, 12544 / 2180, USD 0 | 2 calls, 518 / 185 |
| [pull_request/head](https://github.com/datnv41001/ai-company/actions/runs/46095553782/artifacts/15243293904) | 454 | 35/38 | 0 | 10767 / 3517 | {'recipient_revoked': 3, 'ok': 35}, unconfirmed 3 | {'ok': 21}, 12554 / 2245, USD 0 | 2 calls, 518 / 193 |
| [pull_request/integration](https://github.com/datnv41001/ai-company/actions/runs/46095553782/artifacts/15243087683) | 451 | 34/38 | 1 | 11125 / 3417 | {'recipient_revoked': 3, 'ok': 35, 'invalid_source': 1}, unconfirmed 3 | {'ok': 21}, 12566 / 2173, USD 0 | 2 calls, 518 / 203 |
