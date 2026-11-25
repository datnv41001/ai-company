-- Both binaries use amc_runtime. Change only the existing delivery writer capability.
-- Preserve its OID so all four existing triggers switch at the same commit.
LOCK TABLE public.deliverables, public.client_reviews, public.review_entries, public.knowledge_commands IN ACCESS EXCLUSIVE MODE;
ALTER FUNCTION amc_acl.require_reviewer_writer() RENAME TO require_edition_writer;
CREATE OR REPLACE FUNCTION amc_acl.require_edition_writer() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF session_user = 'amc_runtime' AND
       current_setting('amc.delivery_protocol', true) IS DISTINCT FROM 'c3/4' THEN
        RAISE EXCEPTION 'Restart the API with the customer edition writer protocol' USING ERRCODE='55000';
    END IF;
    RETURN NULL;
END $$;
INSERT INTO amc_c3.versions(version) VALUES (4);
