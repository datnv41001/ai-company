-- Revision 1 is the first tracked working copy, including documents upgraded from v7.
-- Earlier approvals have no known revision. Keep their original digest and audit trail.
ALTER TABLE deliverables
    ADD COLUMN qa_revision integer NOT NULL DEFAULT 1,
    ADD COLUMN qa_approved_revision integer;
