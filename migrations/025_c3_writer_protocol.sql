-- These tables contain the QA decision and the immutable customer snapshot.
-- Hold all three locks before publishing the marker: an earlier write finishes
-- on v24, or its statement encounters the fence after commit.
LOCK TABLE public.deliverables, public.client_reviews, public.review_entries IN ACCESS EXCLUSIVE MODE;

CREATE FUNCTION amc_acl.require_c3_writer() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF session_user = 'amc_runtime'
       AND current_setting('amc.delivery_protocol', true) IS DISTINCT FROM 'c3/1' THEN
        RAISE EXCEPTION 'The delivery writer is incompatible; restart the API with the matching release'
            USING ERRCODE = '55000';
    END IF;
    RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.require_c3_writer() FROM PUBLIC;

CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.deliverables
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_c3_writer();
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.client_reviews
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_c3_writer();
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.review_entries
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_c3_writer();
INSERT INTO public.amc_schema_versions(version) VALUES (25);
