### Rehearse C2 and A1 publisher order on a synthetic cluster

The two development publishers have separate compatibility contracts. At C2 commit `84e2034ce5845fdf26e81a66bc425c18f7c2de92` and A1 commit `322752384813b959515eb9bbb677199326a4fb74`, PostgreSQL 16.16 produced these results.

| Order | Observed result |
| --- | --- |
| C2 v22 + business module v2, then A1 | Core reached v23. The exact synthetic workspace record, business module versions 1/2 and the desk/catalog function definitions and runtime execute grants survived. A1 replaced the commercial conflict rule with its own pinned definition. The expected database-proof key and quota/restore fingerprints matched. |
| A1 v23, then C2 | C2 explicitly refused the newer schema. The business module was absent before and after. Across both cases, A1 replay and C2 refusal preserved the measured application rows, table grants/RLS flags, policies, routine definitions, comments and grants. |

Use Python 3.12 with the repository requirements, Git, and a **dedicated synthetic loopback PostgreSQL 16 database server**. A native instance or a container published on loopback works. Give the process a complete, locally supplied maintenance connection string in `AMC_ORDER_ADMIN_DSN` pointing to the `postgres` maintenance database. Use a sandbox administrator with database creation privileges and the repository’s existing unprivileged `amc_runtime` login. On a fresh disposable cluster the administrator can initialize that login with `CREATE ROLE amc_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;`. The rehearsal never sets the runtime role’s password. Check out each Git commit in a separate directory. Run from the directory containing the script.

~~~text
python check_publisher_order.py --c2-checkout ../c2 --c2-sha 84e2034ce5845fdf26e81a66bc425c18f7c2de92 --identity-checkout ../identity --identity-sha 322752384813b959515eb9bbb677199326a4fb74 --report publisher-order.json
~~~

Only committed publisher inputs are loaded. Each order uses fresh generated keys and its own temporary database. The JSON report contains the source pins, rule hashes, checks and cleanup count. The row-level security comparison fingerprints installed definitions. Runtime authorization and commercial precedence still require behavioral integration tests.

**Gate for a future combined publisher.** Before accepting a combined release, exercise fresh installation, populated C2-first and A1-first databases, replay and fail-closed rollback. Pin the intended C2 commercial-rule digest and test buyer, payment and service-level precedence, geographic aliases and scoped read/write behavior across clients and brands using the runtime login. Confirm the C2 signed operations use A1’s separate database proof key, and exercise JWT rotation, active quota continuity and restore fencing through the application. Include existing and newly created records, retained snapshots and ledger history. The measured publisher-order behavior describes the two individually scoped releases. Approval of a combined publisher requires its own migration and behavior evidence.
