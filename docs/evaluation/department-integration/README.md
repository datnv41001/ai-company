# Reproduce the combined department rehearsal

The local rehearsal ran on commit [f1064d29](https://github.com/datnv41001/ai-company/tree/evidence/department-rehearsal-f1064d29), tree `1bbc168142e9c5f314724a9ba4c657ded80e91d0`. The linked [full JUnit](integration-full-junit.xml) records 533 passes and two skips. The [cross-branch JUnit](integration-junit.xml) records the 18 focused cases. On a disposable PostgreSQL instance use the API-test setup in the workflow at that tag. Run `python -m pytest -q --junitxml=full.xml` and compare the collected test names with the focused archive for a scoped rerun.

The journal cutover job in this PR starts the actual preceding main binary at `bb678908b767481d051a1364c9247f55fd8d2e2a`. It uses a disposable fixture and restores the pre-cutover archive. The v26 CI results apply to this PR's head and integration. The earlier JUnit files describe the separate v25 rehearsal.

- integration-full-junit.xml SHA-256 `0ff18f1fa2151937810e27d5163cdf4fb5e5a7421bb767c3269a37bf40e4ca4b`
- integration-junit.xml SHA-256 `ec7ed906b1b054c5f7844be4a3bdcde1196e050111ff7c759d0882e2e3b3c8ee`
