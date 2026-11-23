# ADR-008 · Agency dispatch, worker identity and cost ownership

Status: accepted for internal development. Base: 906683711e19893fa0510a9c9597a006af56c4b6.

## Trust and cutover

PostgreSQL authenticates each inference process with a dedicated LOGIN and SCRAM secret. The pool worker group has EXECUTE on two mailbox functions. These functions derive identity from session_user, reject expired or withdrawn leases and expose only the body assigned to this login. They do not accept campaign or user IDs. Workers have no application-table privileges. Deploy workers with separate credentials, without the API or dispatcher password. The trusted dispatcher runs separately, inherits the application's editor capabilities, selects an explicitly provisioned route, and applies existing QA through the existing finish path. API roles still use transaction-local context; it is never worker authentication.

Enrollment applies at run creation only. Historical and active v8 runs remain legacy, including reservations and snapshots. Pool work is invisible to legacy worker queries and cannot be updated by the old login. Operations staff drain old jobs before enabling routes. Stop the dispatcher to pause issuance; drain completions, keep accounting evidence, disable new enrollment and restart legacy processing for fresh runs. Never replay an uncertain outbound call under its old lease.

## Scheduling and task graph

Serialise short scheduling decisions using one PostgreSQL transaction advisory lock; lock the run, then its agency budget period. Never hold database locks during inference. Select the least recently served eligible agency, then its oldest ready run, then an available authorized worker. Skip exhausted agencies and occupied workers. One active mailbox per worker and one attempt per run; the agency sets a concurrent-attempt limit. Tasks follow the frozen ordered skill plan with an immediate same-run predecessor. Store task scope via a composite run FK. Consume one opaque lease exactly once; an expired result cannot create a checkpoint. Withdrawal invalidates the run even if a recipient regains access.

## Money and authority

Hold integer micro-USD against the agency's UTC calendar month before exposing a request. Commit the hold and mailbox in one transaction. Preserve holds for errors with unknown usage, revocation and expiry. Convert measured usage into estimated spend once. An owner/admin may reconcile the charge to the provider's absolute amount using a unique receipt for the originating attempt. A conflicting replay fails. Adjust via append-only deltas booked to the original period. A late overage is visible and blocks future reservations. Only the agency owner/admin can configure limits or reconcile. Deployment registers logins and grants campaign routes separately. Workers cannot set cost rates or write ledger entries.

## Director and release gates

Retain the three-attempt ceiling. Distinguish truncation, assignment shape, bad source references and timeout. Rebuild each prompt from the frozen evidence and current error. Monitor first-attempt checkpoint success, error counts, known tokens and attempts without confirmed usage. Keep deterministic interleaving and accounting tests separate from pinned local Qwen acceptance. PostgreSQL is required for pool mode. SQLite retains its original single-campaign development path.

The dispatcher offers work only to logins that polled their mailbox within the previous ten seconds. A worker can collect an offer once. An offer that expires before collection releases both limits and does not consume a provider retry. A sent request with uncertain usage retains its hold. Enrollment and run creation share the scheduler lock so a concurrent legacy enqueue cannot straddle cutover.

## Run budget and provider receipts

For each pooled run, exposure in micro-USD is the sum of all outstanding holds and net spend across all its attempts and UTC periods. The ledger is authoritative. The legacy-named reserved_microusd column materializes that value for admission and API reads. Each new attempt must fit both the lifetime run cap and its agency period cap. A timeout or recipient withdrawal after collection leaves the hold in place. An absolute receipt replaces the prior exposure of that attempt. On a refund or late overage the run total changes by the same net delta as the agency ledger. Existing receipt keys replay without a second change. The scheduler and reconciliation take the same transaction lock before checking balances. If an otherwise affordable retry is temporarily blocked by exposure, it stays queued. A financial adjustment cannot restore a revoked run.

An unsent ledger entry is durable evidence that the worker never collected the offer. Ordinary reconciliation rejects every receipt for it, including zero and historical replays. Schema 10 rebuilds the run totals from immutable v9 history and preserves all receipts; historical v9 invoices for unsent offers remain identifiable for audit. There is no exception billing endpoint.
