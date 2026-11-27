# RFQ history and current Business Desk authority

The proposed card reads a published, synthetic acceptance fixture offline. Its audience is Sales and Marketing evaluating the prototype. It exposes no tenant history endpoint. A real customer's records require a separate access design before this prototype can be used with them.

The [pinned capture](../../../tests/fixtures/rfq_evidence/lineage.json) records KG-P at one box at `2026-11-27T04:10:30.346121Z` (sequence 12) and five boxes at `2026-11-27T04:10:33.289134Z` (sequence 13). The [authority observations](desk-authority.json) record the expected and actual values for all 25 role and scope checks on that capture.

| Current actor | Existing live Business Desk result | Evidence available to the card |
| --- | --- | --- |
| Agency owner or admin | The existing sandbox can inspect its restricted scope. The role-specific Desk requires its own campaign grant. | Only the three synthetic source receipts included in the pinned fixture. |
| Marketing operator or business owner with a current grant | Latest value for each eligible case in that campaign. | Published synthetic fixture only. |
| Sales recipient with a current grant | Latest lead snapshot for cases currently assigned to that person. Reassignment removes the former recipient's access. | Published synthetic fixture only. |
| Service assignee | Latest assigned appointments. RFQs belong to the Sales desk. | Published synthetic fixture only. |
| Reviewer | ID, plan, state and revision. The role does not provide a lead's answers, commercial data or event history. | Published synthetic fixture only. |
| Client portal or unrelated tenant | No internal Desk access. Each client viewer can list its own client record. Raw agency campaign rows are internal. | Published synthetic fixture only. |
| Revoked grantee | Role-specific inbox returns HTTP 404. An earlier cutoff does not restore access. | Published synthetic fixture only. |

[Desk.inspect and the role checks](../../../app/campaign_role_desk.py) use the [signed PostgreSQL procedure](../../../migrations/campaign_desk_function.sql). After taking the brand lock, the procedure checks the current membership epoch, grant and campaign scope. Its inbox selects the highest journal sequence per entity. Separate role grants remain separate when a user holds two. The application has no role-filtered history query for constructing a Sales card. Fetching restricted history with an owner session on behalf of a Sales or reviewer session would exceed those rights.

## Repeat the two-cutoff capture

Use the [existing local PostgreSQL acceptance environment](../../CODEX_LOCAL_HANDOFF.md) with a disposable database and the project's test dependencies. Run this command from the repository root.

```sh
python -m pytest -q -rs tests/test_rfq_desk_authority.py
```

The test requires `AMC_TEST_PG=1` and the runtime and migration connections used by the existing PostgreSQL suite. A skipped test supplies no database evidence. To retain an independent capture, set `AMC_RFQ_EVIDENCE` to a new, empty directory. It produces `lineage.json` and `authority.json`. IDs, timestamps and digests will differ across fixtures. A reproduction must preserve the sequence and assertions, including both populated client campaigns; keep its files separate from the pinned capture.

The [integration test](../../../tests/test_rfq_desk_authority.py) obtains the intake, visit and correction from their existing authenticated HTTP writers. Its privileged setup is confined to the synthetic lab. The captured inquiry and correction share an inquiry ID, signed plan, intake contract and unit. The original form answer remains one box even after completion sets the lead quantity to five. The correction receipt supplies a new recorded time and sequence; the writer supplies no business occurrence time for that correction.

The same test exercises the current Desk through real user sessions. Two independent clients have separate populated campaigns with identical names. The before/after command count uses an authorized agency fixture session and the runtime database role. Direct restricted journal counts use each named staff member's own signed transaction. The genuine desk GET accepts no cutoff parameter in its contract. Sending an earlier cutoff to the existing route in these tests still returns only the current authorized projection, including an empty inbox after reassignment and HTTP 404 after revocation.

The synthetic test uses the existing correction writer to generate the second observation. The two funnel responses are the existing `intake-funnel/2` outputs: the rule counter moves from 0 to 1 when the quantity reaches five. Sales acceptance, sandbox quotes, orders and confirmed revenue remain at zero in both cuts. Measurements and assignment experiments were taken separately; assignment events created after the second cutoff are excluded from the pinned source bundle.

## Fixture corrections during acceptance

1. The first attempt expected a client viewer to list its own raw agency campaign. PostgreSQL returned an empty list; the application intentionally hides internal campaign rows from client viewers. The test now verifies visibility of the viewer's own client record, absence of raw campaigns and denial on both Business Desks. The independently granted operator provides the positive control for each populated Desk.
2. The first attempt at creating the second populated case selected a synthetic customer whose profile already had a revision. The existing writer rejected the attempted initial revision. The final fixture creates a fresh customer in the same agency and uses the ordinary first-revision flow. Both failure observations concern fixture setup or expectations; the production permission and writer code was preserved.
