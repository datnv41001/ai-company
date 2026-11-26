# AMC-R50-01 · Handoffs across the two business APIs

This was a verification request. On the synthetic campaign the same restricted database login served a pinned pre-desk API and the current Role Desk. A delegated reviewer could add feedback and could only coordinate an appointment after receiving a separate Marketing grant. Removing the Marketing grant removed that authority while preserving the independently granted feedback action. Removing membership invalidated feedback replay. Replaying a successful legacy intake also required the actor to retain organizational authority.

## Which operations can change Sales or Service state?

The integrated rehearsal issues and approves the historical plan with the pinned #49 API, then exercises both writers on that plan. This separates the predecessor's valid authority from the new writer requirement for plans carrying an intake contract. The intake rehearsal separately uses the actual #54 API on the same application schema. Replaying an old receipt and starting a new transaction are tested separately.

| Entry point | Authority and effect | Acceptance evidence |
|---|---|---|
| Campaign `/sandbox/commands` | The organizational owner/admin can enter sandbox observations and settle business cases under the existing state machines. The Sales contract explicitly permits a campaign approver to settle a lead. A completed service visit requires the assigned actor. The API checks organizational authority before returning an earlier receipt. A desk role by itself does not grant this route. | [RFQ and Sales steps](../../../tests/test_campaign_operations.py), [service lifecycle](../../../tests/test_campaign_appointments.py), [dual-version test](../../../tests/test_business_authority_paths.py). |
| Campaign `/business-desk/grants` and role `/decisions` | Owner/admin grants a named campaign role to an internal member. Sales and service recipients see their own assigned entities. Reviewers see case ID, revision, state and plan and can record feedback. Each command evaluates the selected role, current membership, assignment and plan before replay. The journal and brand transaction lock coordinate the two paths. | [Grant, visibility, reassignment, feedback and revocation](../../../tests/test_campaign_role_desk.py), [SQL function and membership epochs](../../../migrations/campaign_desk.sql). |
| Studio production `/{pid}/visits` and `/{pid}/submissions` | An authorized sandbox actor opens a signed current landing and submits to the same scoped plan. This creates an intake record. Assigning, accepting, canceling or confirming the case uses the business transitions above. | [Production packages on restricted PostgreSQL](../../../tests/test_production_studios.py) and the intake verification in this change set. |
| Dispatcher | The loopback dispatcher consumes authorized scheduled marketing actions. Its typed execute endpoint cannot post a Sales or service decision. Real external writes remain disabled. | [Dispatch integration](../../../tests/test_department_dispatch_integration.py) and [typed command contracts](../../../app/campaign_operations_contracts.py). |

## Mapping the review scenarios

| Situation | Proof |
|---|---|
| Campaign grant revoked; membership role changed and restored | Existing role-desk journey checks replay denial after revoke and requires a new grant after the member epoch changes. |
| Membership removed; lost acknowledgement | Additional test deletes only the fixture reviewer's membership and checks replay of its previous feedback. Separately, an admin loses admin authority after recording a successful intake and both APIs reject that replay. An authorized reader can still retrieve the original receipt. |
| Reassignment and out-of-date inbox | Existing test transfers the case, removes it from the old service inbox, rejects the old assignee's completion and rejects the replacement's obsolete revision. |
| Two writers at the same revision | Additional test releases two legitimate requests together. One uses the archived #49 API with organizational authority, the other uses the current Marketing desk. The results must be one 200 and one 409, with a single transition to revision 2. |
| Combined roles and reviewer authority | The same actor holds reviewer and Marketing grants. Selecting reviewer still cannot confirm. After only the Marketing grant is revoked the reviewer can replay its own feedback. |
| Second customer in the same agency; unrelated tenant | Existing test covers campaign, recipient and feedback scope. Additional test uses a second customer and an unrelated tenant's actual signed-in account against the valid campaign. |
| Compatible previous API | Git archive `0498949e64f4d030cc9ba2f0f961ab4dfc2e2ab0` boots using the same disposable PostgreSQL and the runtime credentials as the current HTTP app. The test asserts the runtime login is neither superuser nor BYPASSRLS and checks RLS on the journal table. |

## Reproduce and interpret

Use the disposable PostgreSQL environment from the API job in [CI](../../../.github/workflows/ci.yml) and enable `AMC_TEST_PG=1`. Use a full Git checkout with the pinned predecessor available. Run:

```text
python -m pytest -q tests/test_campaign_role_desk.py tests/test_campaign_appointments.py tests/test_campaign_operations.py tests/test_production_studios.py
python -m pytest -q tests/test_business_authority_paths.py
```

The first four files were replayed on the #54 source `eff86cda2f99dd10244dc8127451e941bb546a3c`: 14 passed. The extra concurrency and mixed-version scenario was added because two sequential requests against one API could not establish that both paths use the same revision boundary. The assertion that the final state is revision 2 is independent of which request wins. Exact durations, case names and outcomes of the targeted runs are in [authority-runs.json](authority-runs.json).

The requested cases support the documented distinction between a workspace-wide admin and a delegated campaign worker. The results provide no basis to remove the existing admin contract. The change adds regression coverage and leaves the authorization runtime intact. Revert the test and its evidence on a separate branch if required. No production data or measured savings were involved. For independent review, compare the receipt owner, grant epoch, winning revision and final state under both possible winners.
