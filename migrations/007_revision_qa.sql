-- Existing working drafts inherit FORCE RLS. NULL represents an unassessed legacy revision.
ALTER TABLE deliverables ADD COLUMN qa_evidence json, ADD COLUMN qa_approved_digest varchar(64);
ALTER TABLE deliverables FORCE ROW LEVEL SECURITY;
-- Bound the reverse lookup to rows which actually have a submitted artifact.
CREATE INDEX ix_workforce_deliverable ON workforce_runs (tenant_id, campaign_id, deliverable_id)
    WHERE deliverable_id IS NOT NULL;
