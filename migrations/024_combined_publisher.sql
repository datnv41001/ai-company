-- The publisher validates installed SQL, business v3, RLS-sensitive grants and
-- A1 key continuity in this transaction before making the combined core visible.
INSERT INTO amc_schema_versions(version) VALUES (24);
