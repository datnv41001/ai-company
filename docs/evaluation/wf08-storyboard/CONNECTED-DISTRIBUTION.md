# From an approved storyboard to an RFQ in the synthetic CRM

The agency operator starts with two independently reviewed editions. The WF-08 edition supplies the storyboard, and the commissioned Studio landing run supplies the buyer-facing form. The two manifests must point to the same internal business brief and match the approved product, variant, audience, objective, channel, action and underlying knowledge revision digests. The operator can use the same synthetic company name in separate campaigns without linking their data.

## Prepare and inspect a distribution

All paths below are relative to the approved landing package at `/api/tenants/{tenant_id}/deliverables/{landing_document_id}/studio/production/{landing_package_id}`. Use the existing authenticated internal API.

1. POST to `/storyboard-distributions` with a UUID `request_id`, `storyboard_document_id`, `expected_run_id`, `expected_revision`, `expected_content_digest`, `expected_landing_digest` and an illustration `style` of `parts`, `route` or `rhythm`. The service resolves the current storyboard from its own workforce document and checks the signed queue, source, independent QA, active plan and page package. An exact retry returns the same distribution ID.
2. A different active approver inspects `/storyboard-distributions/{id}/files/preview.webm`, `poster.png` and `captions.vtt`, plus the approved Studio file `/files/landing.html`. File responses contain base64 bytes and a SHA-256 digest. The preview uses the bundled Studio font and local VP8 renderer under the synthetic illustration rights recorded on the board.
3. The approver posts the `expected_digest` of the distribution and a review `note` to `/storyboard-distributions/{id}/approve`. GET `/storyboard-distributions/{id}` resolves the current pins and the active preview decision. A new board revision, changed page, withdrawn knowledge or inactive approver requires review before another event can be recorded.
4. POST an authenticated `request_id` to `/storyboard-distributions/{id}/visits`, then POST `request_id`, returned visit `entity_id` as `visit_id`, `contract_digest`, `consent` and the approved form's `answers` to `/storyboard-distributions/{id}/submissions`. The same distribution and landing revision follow the visit into the CRM. Reuse a request ID only to retry the identical request.
5. The granted Marketing operator reads the inquiry from the campaign Business Desk inbox. The campaign sandbox exposes the existing approved-plan-lifetime intake funnel. Further sales transitions, revenue, creative effectiveness, audience traffic and commercial acceptance require their own observations.

## Reproduce the evidence

Use the disposable PostgreSQL setup in the repository handoff and run `python -m pytest -q tests/test_storyboard_distribution.py` with `AMC_TEST_PG=1`. Set `AMC_CONNECTED_EVIDENCE` to a new output directory to retain the exact raw worker output, approved edition, rendered preview, captions, poster, landing HTML and joined event receipt. The test checks each output file's SHA-256. Receipt subdirectories `wf08-v1` and `wf08-v2` distinguish the prior workflow from the Content handoff version. The limited Studio landing worker uses controlled provider replies, while the storyboard stages execute the real local deterministic adapter. All tests use synthetic buyer selections.

The Khe Gọn test records the signed plan's ID, digest, approval receipt, landing brief and manifest under `measurement_authority`. It reads the plan's KPI description and any typed primary KPI contract from the approved revision returned by the campaign planner. It then queries the sandbox by the same plan ID. In these fixtures the primary KPI is absent, and qualified RFQ counts come from sandbox receipts over the life of the plan.

Preview rendering is synchronous. The API holds locks on the source documents and scoped knowledge while generating the bounded 9:16 file, so another writer on that scope can wait for the render and commit. The evidence covers short internal rehearsals; concurrent rendering capacity and production latency still require measurement.

The scope of this API is authenticated internal rehearsal. Storyboard, reviewer notes, evidence and distribution controls remain in the agency workspace. Landing content and form fields come only from the separate Studio edition and its independent QA.

