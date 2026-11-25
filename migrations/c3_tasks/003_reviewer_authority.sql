-- A decision can depend on another staff member's earlier signoff or resolution.
-- Lock that member in their own tenant, after the existing scope/target locks.
CREATE FUNCTION amc_acl.lock_c3_reviewer(t text, reviewer text) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
    IF amc_acl.knowledge_read(t,'restricted') IS NOT TRUE THEN RETURN false; END IF;
    PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=reviewer
        AND role IN ('admin','owner') FOR SHARE;
    RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION amc_acl.lock_c3_reviewer(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.lock_c3_reviewer(text,text) TO amc_runtime;

-- Older APIs omit third-party reviewer locks. Fence their delivery writes at cutover.
LOCK TABLE public.deliverables, public.client_reviews, public.review_entries, public.knowledge_commands IN ACCESS EXCLUSIVE MODE;
CREATE FUNCTION amc_acl.require_reviewer_writer() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF session_user = 'amc_runtime' AND
       current_setting('amc.delivery_protocol', true) IS DISTINCT FROM 'c3/3' THEN
        RAISE EXCEPTION 'Restart the API with the current Studio reviewer protocol' USING ERRCODE='55000';
    END IF;
    RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.require_reviewer_writer() FROM PUBLIC;
DROP TRIGGER c3_writer_protocol ON public.deliverables;
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.deliverables
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_reviewer_writer();
DROP TRIGGER c3_writer_protocol ON public.client_reviews;
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.client_reviews
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_reviewer_writer();
DROP TRIGGER c3_writer_protocol ON public.review_entries;
CREATE TRIGGER c3_writer_protocol BEFORE INSERT OR UPDATE OR DELETE ON public.review_entries
    FOR EACH STATEMENT EXECUTE FUNCTION amc_acl.require_reviewer_writer();
-- A group signoff can append a receipt without updating the working copy.
CREATE TRIGGER c3_reviewer_receipt AFTER INSERT ON public.knowledge_commands
    FOR EACH ROW WHEN (NEW.operation IN ('c3_studio_qa','c3_resolve','c3_qa','c3_share'))
    EXECUTE FUNCTION amc_acl.require_reviewer_writer();
INSERT INTO amc_c3.versions(version) VALUES (3);
