# Combined PostgreSQL publisher (core 024)

The release joins C2 commit `068b85170cf47106c8d08a8c573548e3f530647c` and Identity A1 commit `322752384813b959515eb9bbb677199326a4fb74`. It uses the existing C2 business module versions 1–3 and device migration 023. Marker 024 records their combined contract. All DDL, capability installation, proof transition and version markers run under one PostgreSQL transaction and publisher advisory lock.

| Starting state | Accepted transition |
| --- | --- |
| Empty synthetic database | Install the existing core chain, business module v3, device schema and combined marker. |
| C2 v22/business v3 | Validate the old JWT-derived database proof, carry forward the quota key when windows are active, replace the database proof with the separate A1 key and preserve all business rows. Existing memory-only access tokens require a new login. |
| A1 v23 | Validate the stored database proof and both quota/restore fingerprints against the supplied key set. Install the reviewed C2 rule and business module. Existing device epochs and family revocations survive. |
| Combined v24 | Recheck capabilities, module history, identity domains and current rule definitions. Both pinned predecessor publishers refuse core v24 when invoked in migration mode. |

The commercial and claim-display contracts verify the body and publisher digest, stable SQL security-definer configuration, search path and execute grants. The migration recognizes the predecessor A1 commercial body, then installs C2’s buyer/payment/service precedence. The C1 append, business profile, catalog and objective clients sign with `AMC_DB_PROOF_KEY`. The quota key, independent restore generation and JWT issuer have separate purposes.

## Operate a disposable development instance

Stop the API and workers for the target development database during cutover. Use the reviewed migration identity and retain the database’s existing JWT issuer. For populated C2 with active v21 quota windows, provision the legacy quota HMAC described in the A1 runbook, a separate fresh 32-byte database proof and an independent 32-byte restore generation. For populated A1 use its authoritative three existing identities. Preserve the issuer and keys in separate protected storage. The API uses the restricted `amc_runtime` account. [Device key provisioning and rotation](DEVICE-SESSIONS-A1.md)

From the repository root with a configured synthetic Compose project:

~~~sh
docker compose run --rm migrate
docker compose up -d api
~~~

For native startup set `AMC_MIGRATION_DSN` only on the publisher, supply the project’s corresponding four identities, and run `python -m migrations.apply`. Use a runtime DSN belonging to `amc_runtime` for the application. On schema mismatch the API stops at startup. Restore or repair the reported input before reopening traffic. The controls apply to the reviewed default migration command and current runtime. Privileged SQL or offline admin subcommands require operator custody.

## Verify the release

The integration workflow runs the application tests with the actual restricted login, historical upgrades, a combined archive round trip, both predecessor orders, Chromium delivery/device, company profile, catalog, claim desk, company objectives and the C2 integrated journeys. The predecessor tests use Git archives from the exact pins and the predecessors’ own APIs to populate the tables. They require full Git history, pinned Python dependencies and a fresh loopback `amc_test*` database **for each command**. Set `AMC_TEST_PG=1`, `PYTHONPATH=.`, the two DSNs, and the authoritative key material described above.

~~~sh
python tests/check_combined_upgrade.py c2
python tests/check_combined_upgrade.py a1
~~~

These commands compare exact JSON rows for snapshots, ledger receipts, attempts, quota buckets, C2 records/edges or A1 families/consumed refresh grants. They exercise a failed transaction, publisher replay, a restricted API startup and both older publishers’ refusals. The ordinary API suite covers commercial precedence, client/brand isolation, public claim wording, signed writes and both revocation/worker commit orders. The archived v22 publisher-order script documents why integration was required.

Before cutover take a separately restorable backup of the original database and its key lineage. A binary rollback from v24 requires a separate restoration of the matching pre-upgrade backup. To restore a **combined** backup, compare the restore to the archive first, keep ingress closed, generate a fresh external restore generation, then run `python -m migrations.apply --identity-operation restore-fence` on the restored database before starting any API. This invalidates pre-restore device grants. The archive test also verifies that an API process retaining the previous generation is refused. [Archive and identity recovery details](DEVICE-SESSIONS-A1.md)

This handoff concerns isolated development databases. The legacy pools retain their own publisher, signing state and deployment approval.
