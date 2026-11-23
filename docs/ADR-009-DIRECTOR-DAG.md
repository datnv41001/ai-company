# ADR-009 · Frozen diamond workflow

Internal development. Base a3c98a1, schema v10. Opt-in workflow diamond-v1 requires an enrolled PostgreSQL agency. Existing requests use the linear contract.

The server installs one trusted template: Director → Research → Strategy → {Content, SEO} → Join. Director writes specialist assignments; it cannot supply nodes, edges, credentials or sources. Enqueue freezes a per-run revision in the transaction that creates it. Director uses an ordinary metered attempt. Join is a database transition with zero model calls. Dynamic graph generation would require a separate bootstrap/validate/freeze contract.

A node ID is a stable name within the immutable scope and plan revision. Edges reference both endpoints within the same tenant, client, brand, campaign, run and revision. Acyclic ordering, a single entry and exit, connectivity and required edges are verified before dispatch. The v10 task slot is a compatibility key for financial attempts. DAG readiness and checkpoints use node identities. Each node gets its own three-try budget. An undelivered offer consumes no provider retry.

The worker receives frozen sources, brief and brand data, the specific Director assignment, and approved direct predecessor output. Sibling checkpoints never enter its request. Both branches may be ready, with at most one active lease per run. Retry prioritizes a ready node with fewer previous attempts. Fencing, receipt reconciliation, agency fairness and withdrawal retain the v10 transaction boundary.

Join consumes exactly the required node checkpoints in fixed template order and atomically records the draft, provenance, QA evidence and unique run/revision delivery link. An expired result cannot open Join. A failed required node blocks its descendants. Source validation precedes checkpoint persistence. A human still reviews the exact revision and digest.

During migration stop dispatch and intake, back up the development DB, migrate, restart matching code and enable the template only for new runs. To roll back intake choose linear for new requests, drain or explicitly withdraw DAG runs, retain ledger, graph history and snapshots. A binary downgrade requires a rehearsed backup restore and reconciliation of newer records.
