-- Derive immutable intake terms from the release whose digest the database pinned.
CREATE OR REPLACE FUNCTION amc_ops.check_registry_binding() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE binding jsonb := (NEW.knowledge->'registry')::jsonb;
        expected jsonb;
BEGIN
 SELECT coalesce(r.manifest->'required_outputs',
          (SELECT jsonb_agg(skill ORDER BY skill) FROM jsonb_array_elements_text(r.manifest->'required') skill WHERE skill<>'director'))
 INTO expected FROM amc_ops.registry_releases r WHERE r.workflow=binding->>'workflow' AND r.digest=binding->>'manifest_digest';
 IF expected IS NULL OR binding IS DISTINCT FROM amc_ops.registry_pin(NEW.tenant_id,NEW.campaign_id,binding->>'workflow')
 OR NEW.knowledge->>'workflow' IS DISTINCT FROM 'dynamic-v1' OR (NEW.knowledge->'required_outputs')::jsonb IS DISTINCT FROM expected
 THEN RAISE check_violation; END IF;
 RETURN NEW;
END $$;
