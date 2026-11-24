# SAA-02 · Verified identity and workspace invitations

This release is for local development with synthetic accounts. Use the PR's head or merge it after independent review. The base schema is v16 at `d81df0bee0d381007acfd0cf0b786a7f56e38719`. The target schema is v17.

## Run on another machine

Use a fresh Compose project and a dedicated database. From the repository root run:

```sh
python scripts/init_env.py
docker compose -p amc-identity-dev up -d --build
docker compose -p amc-identity-dev ps
```

Open the app at http://127.0.0.1:8000 (or set `AMC_HTTP_PORT` before starting). Register a synthetic Agency or In-house organization. Registration reserves its identifier. The membership list is initially empty. The bearer authenticates the account. It does not verify the address.

For this internal test the operator controls the synthetic mailbox. Its volume belongs to the API service account. To open the most recent delivery in a private terminal, replace the example address with the registered synthetic address. The command reads a local file. Keep that terminal out of recordings and shared logs.

```sh
docker compose -p amc-identity-dev exec api python -c "import hashlib,os,sys; from pathlib import Path; d=Path(os.environ['AMC_DEV_MAILBOX_DIR'])/hashlib.sha256(sys.argv[1].strip().lower().encode()).hexdigest(); print(max(d.glob('*.txt'),key=lambda p:p.stat().st_mtime_ns).read_text())" owner@example.com
```

Paste the code in **Xác minh email**. In a native checkout the same mailbox layout is under `.dev-mailbox/`, or the private directory in `AMC_DEV_MAILBOX_DIR`. The mailbox is outside the public mount, ignored by Git, and excluded from the Docker build context. The latest code remains usable for 20 minutes and one successful verification. Requesting another code replaces the database digest. Mailbox access is the trust boundary of this local delivery mechanism.

The verified first owner receives a newly created workspace and, in In-house mode, its internal client. Use **Quản lý người nhận và lời mời** to invite another registered account. Choose a workspace role or a client scope. Log in as the recipient, verify their address and accept. Existing v16 members retain their previous workspace rights and start with an unverified address. They can request a code after login. Verification of a legacy account creates no additional owner workspace. An older pending invitation requires verified issuer and recipient at acceptance. Owners can invite admins. Admins can invite editors, viewers and scoped clients.

## Database and API contract

- The existing `portal_invitations` table, inbox, revoke endpoint and audit event names carry all four invited roles. An invitation is pending until acceptance. The former direct-grant endpoint returns HTTP 410. A role/scope supplied to acceptance returns 422.
- New identities obtain a 256-bit code in the private local mailbox. The database stores a SHA-256 digest and expiry. Issuance and redemption serialize per user. Verification consumes the row, records ownership and bootstraps the reserved workspace in one transaction.
- The API signs the validated actor ID and PostgreSQL transaction ID with a domain-separated HMAC key. The migration owner installs the derived key in the private ACL schema. PostgreSQL checks that proof on identity and invitation writes. The runtime LOGIN lacks direct membership and portal-grant INSERT, verified-column write access, signing-key access and bootstrap EXECUTE. Existing controls continue to govern business-table reads using the backend's tenant context.
- Configure the **same strong JWT_SECRET** on migration and API. Startup checks the signer against the database. Keep the original secret with its database in protected operator storage. Schema v17 requires PostgreSQL's pgcrypto extension. SQL functions resolve objects under a fixed search path.
- Acceptance locks the addressed invitation and rechecks its state, expiry, recipient, verified identities and issuer's current membership. A share lock serializes the issuer check with role changes. Composite foreign keys enforce the stored scope. Membership, optional portal grant, accepted state and audit commit together. Revocation updates only a pending row. Replays return 404.
- Client-scope reassignment still operates on an existing membership. PostgreSQL creates the replacement grant from the authorized row transition. Historical client decisions, role QA, worker admission and ledger contracts have no schema changes in v17.

## Preflight and rollback evidence

Preflight used the reviewed v16 migrator on a fresh synthetic PostgreSQL database. The source, cold template backup and restored copy had identical counts and row digests across ten tables. The source held 30 users, 52 memberships, 12 portal grants, 5 attempts, 10 ledger entries, 2 snapshots and 3 review entries. No lease or hold remained active at backup. Two dispatcher LOGINs were exercised against the inventory, session and freshness checks. Both reported the approved native v16 fingerprint `d300bafe3f36ed9948565d206899786d0b0e74d1273ad01435ca7907649d60ef`. The three older development pools were sampled read-only at versions 10, 11 and 13. Each had one dispatcher connection, zero open attempts, zero ledger entries and zero snapshots.

On an isolated native test cluster with the workload stopped and other sessions disconnected, the rehearsal used PostgreSQL `CREATE DATABASE backup_name TEMPLATE source_name` and then `CREATE DATABASE restore_name TEMPLATE backup_name`. Verify the restored copy, including ledger totals, versions, active leases, snapshot digests, users, memberships and portal grants, before changing a connection. The local cold copies share a cluster and are intended for this synthetic rollback rehearsal.

Before withdrawing v17, stop new accounts, invitations and worker intake. Drain or reconcile outstanding leases and reports under the current worker contract. Reconcile identity and grant changes since the backup together with ledger entries, snapshot decisions and checkpoints. Switch to a validated v16 restore and matching v16 binary only after that reconciliation. Preserve the v17 database for audit. The migrator rejects gaps and an isolated v16 missing 015. An older binary must use its matching history.

## Repeatable acceptance

`tests/test_verified_identity.py` exercises the public API and restricted LOGIN. Two acceptors race on separate sessions. For both accept/revoke orderings, the test runs the first real handler inside an outer transaction, observes the other backend blocked in PostgreSQL, then releases the lock. Counts cover membership, portal grant, audit, workforce runs, attempts and ledger. Prior isolation and delivery fixtures now establish membership through a real invitation accepted by the recipient. The original scope, history and QA assertions remain in place.

| RED at `e6033991a8fa6175bb82a1c640ec289cd8e7afff` | Expected | Observed on the base implementation |
| --- | --- | --- |
| `test_new_owner_requires_private_single_use_proof` | Empty initial membership list | Immediate owner in SQLite and PostgreSQL |
| `test_retired_direct_grant` | 410 | 201 in both backends |
| `test_invitation_requires_verified_recipient_and_frozen_scope` | 403 before verification | 204 in both backends |
| `test_runtime_has_no_direct_membership_or_bootstrap_grant` | Runtime lacks membership INSERT | Privilege present |
| `test_accept_race_single_audit_and_issuer_authority` | Staff invitation supported | 422 at invitation creation |

Those eight parameterized RED cases stopped at their first failing assertion. Later assertions and the deterministic lock-order tests are measured on v17. The v16 baseline suite passed all 187 cases. The new path is included in `tests/check_postgres_upgrade.py --from-v16`; it forces an error at the final migration marker, verifies rollback, migrates again and checks retained data. The CI workflow also runs the preceding fifteen populated upgrade paths, the orphan case, Chromium at both viewport sizes, and local Qwen for WF-03/WF-13. Use the checks and artifacts on the PR's exact head for signoff.

The registry release review compared adapter, QA, scheduler, worker, manifest and pinned dependency sources to the base. Historical lock entries are preserved. The two added identities apply the prior five adapter digests to this identity-only source change. Native CPython 3.12.14 is measured locally. The pinned Linux CPython 3.12.16 identity is derived from the previous CI image's measured package set and checked by the real worker in CI. A changed or unknown execution bundle continues to fail closed.
