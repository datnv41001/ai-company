-- An in-flight legacy journal append must either commit before this boundary or be rejected afterwards.
LOCK TABLE public.knowledge_commands IN ACCESS EXCLUSIVE MODE;
CREATE FUNCTION amc_acl.require_sandbox_writer() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
    IF NEW.operation='campaign_sandbox_v1'
        OR current_setting('amc.sandbox_protocol',true) IS DISTINCT FROM 'ops/2' THEN
        RAISE EXCEPTION 'Restart the campaign API with the current sandbox journal protocol' USING ERRCODE='55000';
    END IF;
    RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_acl.require_sandbox_writer() FROM PUBLIC;
CREATE TRIGGER campaign_sandbox_writer BEFORE INSERT ON public.knowledge_commands FOR EACH ROW
    WHEN (NEW.operation IN ('campaign_sandbox_v1','campaign_sandbox_v2','campaign_plan','campaign_plan_approve'))
    EXECUTE FUNCTION amc_acl.require_sandbox_writer();
INSERT INTO public.amc_schema_versions(version) VALUES (26);
