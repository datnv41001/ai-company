-- Studio stores field-level approval inside the existing delivery revision.
-- The v25/c3-v1 API can authenticate, but does not evaluate the Studio contract.
LOCK TABLE public.deliverables, public.client_reviews, public.review_entries IN ACCESS EXCLUSIVE MODE;
CREATE FUNCTION amc_acl.require_studio_writer() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF session_user = 'amc_runtime'
       AND current_setting('amc.delivery_protocol', true) IS DISTINCT FROM 'c3/2' THEN
        RAISE EXCEPTION 'Studio requires a matching delivery writer; restart the API'
            USING ERRCODE = '55000';
    END IF;
    RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.require_studio_writer() FROM PUBLIC;

-- The predecessor startup verifies the trigger function identity, not only its name.
DROP TRIGGER c3_writer_protocol ON public.deliverables;
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.deliverables
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_studio_writer();
DROP TRIGGER c3_writer_protocol ON public.client_reviews;
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.client_reviews
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_studio_writer();
DROP TRIGGER c3_writer_protocol ON public.review_entries;
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.review_entries
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_studio_writer();
INSERT INTO amc_c3.versions(version) VALUES (2);
