# Account lifecycle and invitation-first onboarding

Internal development, synthetic mail only. PR #15 merged at ece8ecc84b4938900821ff85403bb5b8243534c6 after review of cc0e980c. [Post-merge CI](https://github.com/datnv41001/ai-company/actions/runs/45363202327).

## Journeys and state

Previously registration reserved an organization and verification created its first owner. Clients needed an account before an agency could invite them. The web registration now creates an individual account. Verification leads to a workspace picker or an empty state. A verified user may create an organization explicitly or accept a named invitation. A client joining an agency obtains just the offered client scope. Existing callers that send an organization name keep their original registration contract.

| Entity | Transitions |
| --- | --- |
| Account | Registered → verified. Either state can have zero memberships. Existing memberships survive upgrade. |
| Invitation | Pending → accepted or revoked. Expiry is computed from the stored deadline. Resend replaces the pending offer atomically with a new ID, deadline and secret. Terminal offers remain historical. |
| Membership | Absent → owner on explicit creation, or absent → stored role on acceptance. Repeated acceptance cannot add another grant or acceptance event. Membership scope and removal retain their existing handlers. |

## Storage and upgrade

A user has many memberships across tenants. A tenant has many invitations addressed to an email. A pending invitation may precede its recipient user. Acceptance binds the matching user and creates that user's membership, optional client grant and audit in the same transaction. Composite brand/campaign foreign keys continue to constrain scope. v19 allows a null invitation user, adds a nullable unique link digest and enforces one pending offer per tenant and normalized email. Historical invitations have no link and remain accessible in the verified inbox. Preserve historical migration files. Snapshot the v18 database with its signer's secret, test restoring it to a separate database, compare identity, grant, registry, ledger and snapshot rows. Stop writes and reconcile new users, memberships and decisions before switching back to that restore and its v18 binary.

## API, UI and permission matrix

| Actor | Operation | Outcome |
| --- | --- | --- |
| Visitor | POST /api/auth/register with email/password | Account only. An explicit legacy organization name reserves its workspace for verification. |
| Verified account | POST /api/me/workspaces with name, mode and a request UUID | One owner workspace per actor/request. Retrying with conflicting parameters returns 409. |
| Verified owner/admin | POST tenant invitations or POST invitations/{id}/resend | Freeze server-validated terms. Deliver a seven-day link to the addressed synthetic mailbox. Only owners may invite admins. |
| Signed-in verified recipient | POST /api/me/invitation-link with the secret | Read the addressed terms. Wrong account, expired, consumed or revoked links get a generic unavailable result. |
| Signed-in verified recipient | POST /api/me/invitation-link/accept, or accept a visible invitation through the inbox | Explicit consent. The same locked grant operation revalidates issuer authority for both paths. |
| Anonymous/unverified | Open link | Offer registration/login or verification. Opening the page never grants access. |

The URL uses a fragment, removed from browser history on entry and retained only in page memory. The client sends the secret in a POST body. A wrong-account screen offers switching accounts. A verified account can see its pending invitations, create a workspace and switch existing memberships. Both the desktop and mobile acceptance views show stored rights before the action.

## Threat model and operational boundaries

A bare runtime database login cannot mint a verified actor proof. A valid end-user session can exercise its own signed transaction but cannot choose another actor or use a preceding transaction's signature. Context restoration after commit restores identifiers only. Identity challenges are sensitive even within an authenticated database transaction. Binding challenge issuance and redemption to purpose, digest, actor and transaction prevents a general actor signature or a readable database digest from authorizing either operation. The API signs redemption only after comparing the submitted private code. API compromise or loss of the signing key compromises this boundary. Restrict the publisher, worker, mailbox and process secret independently.

Invitation links use 32 random bytes. Store only their purpose-prefixed SHA-256 digest. Separate invitation deliveries from verification-code files. Both use a private local transport. Write before commit so a delivery failure rolls back. A link left by a failed commit has no active row. Recipient identity comes from the verified user. Store all offered fields on the invitation. Serialize replacement, revocation and acceptance on the invitation row. Never echo link secrets in API responses, redirects, validation errors, screenshots or logs. Issuers can already see their own workspace membership roster. Issue the same response for registered and unregistered non-members. Existing registration conflicts, password timing, bulk sending and per-IP/per-recipient quotas require abuse controls before external use. Workload RLS outside identity and worker impersonation require a separate cross-service review.

## Acceptance and follow-up

ONB-T01–02 check account-only verification and idempotent explicit creation. T03–09 cover unregistered address, bind after verification, wrong account, expiry, revoke, concurrent accepts, issuer changes and immutable terms. T10–12 exercise zero/multiple memberships and the client portal at 1280/390. T13 replaces a link. T14–15 upgrade a populated v18 and rehearse restoring the previous snapshot. Re-run SQLite/PostgreSQL, Chromium, full migration history and Qwen on head and integration. Commercial GA remains NO-GO.

Separate increments: (1) rate limits and invitation quotas, (2) session inventory, refresh, logout and revocation, (3) recovery, MFA and signer rotation, (4) team lifecycle and ownership transfer, (5) transactional email outbox, delivery retries and suppression, (6) OIDC/SSO and a database/worker identity audit. Evaluate managed Auth0 or self-hosted Keycloak for established account/session factors against operating cost, data residency and organization isolation. Keep AMC's campaign scopes, client consent and ledger in AMC. Avoid moving account storage or introducing a second identity system in this PR. Business Profile, Brand Kit and Knowledge Center can advance independently after scope contracts stabilize. [Auth0 invitations](https://auth0.com/docs/manage-users/organizations/configure-organizations/invite-members) · [Keycloak guides](https://www.keycloak.org/documentation) · [OWASP token guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
