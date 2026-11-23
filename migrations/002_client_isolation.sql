-- Run once under the migration owner, in the migration runner's transaction.
ALTER TABLE clients ADD CONSTRAINT uq_clients_tenant_id UNIQUE (tenant_id, id);
ALTER TABLE brands ADD CONSTRAINT uq_brands_tenant_id UNIQUE (tenant_id, id);
ALTER TABLE campaigns ADD CONSTRAINT uq_campaigns_tenant_id UNIQUE (tenant_id, id);
ALTER TABLE brands ADD FOREIGN KEY (tenant_id, client_id) REFERENCES clients (tenant_id, id);
ALTER TABLE campaigns ADD FOREIGN KEY (tenant_id, brand_id) REFERENCES brands (tenant_id, id);
ALTER TABLE work_tasks ADD FOREIGN KEY (tenant_id, campaign_id) REFERENCES campaigns (tenant_id, id);
ALTER TABLE deliverables ADD FOREIGN KEY (tenant_id, campaign_id) REFERENCES campaigns (tenant_id, id);
ALTER TABLE action_requests ADD FOREIGN KEY (tenant_id, campaign_id) REFERENCES campaigns (tenant_id, id);
ALTER TABLE memberships ADD COLUMN client_id varchar(36);
ALTER TABLE memberships ADD FOREIGN KEY (tenant_id, client_id) REFERENCES clients (tenant_id, id);
ALTER TABLE memberships ADD CONSTRAINT membership_scope CHECK (
    (role = 'client_viewer' AND client_id IS NOT NULL) OR
    (role IN ('viewer','editor','admin','owner') AND client_id IS NULL)
);

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA amc_acl;
REVOKE ALL ON SCHEMA amc_acl FROM PUBLIC;
GRANT USAGE ON SCHEMA public, amc_acl TO amc_runtime;

-- These two lookups read the actor's own grant as migration owner. The actor
-- and selected agency come from the authenticated backend transaction.
CREATE FUNCTION amc_acl.member_role(t text) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $$
    SELECT m.role FROM public.memberships m
    WHERE m.tenant_id=t AND t=current_setting('amc.tenant_id',true)
      AND m.user_id=current_setting('amc.user_id',true)
$$;
CREATE FUNCTION amc_acl.client_scope(t text) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $$
    SELECT m.client_id FROM public.memberships m
    WHERE m.tenant_id=t AND t=current_setting('amc.tenant_id',true)
      AND m.role='client_viewer' AND m.user_id=current_setting('amc.user_id',true)
$$;
-- New tenant + first owner are inseparable. An existing tenant ID fails the PK.
CREATE FUNCTION amc_acl.create_workspace(t text, org text, org_mode text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor text := nullif(current_setting('amc.user_id',true),'');
BEGIN
    IF actor IS NULL OR t IS DISTINCT FROM current_setting('amc.tenant_id',true)
       OR org_mode NOT IN ('inhouse','agency') THEN
        RAISE EXCEPTION 'Invalid workspace context' USING ERRCODE='42501';
    END IF;
    INSERT INTO public.tenants(id,name,mode,created_at) VALUES(t,org,org_mode,now());
    INSERT INTO public.memberships(tenant_id,user_id,role) VALUES(t,actor,'owner');
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA amc_acl FROM PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA amc_acl TO amc_runtime;

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT ON users TO amc_runtime;
CREATE POLICY identity_read ON users FOR SELECT TO amc_runtime USING (
    id=current_setting('amc.user_id',true) OR email=current_setting('amc.lookup_email',true)
);
CREATE POLICY identity_create ON users FOR INSERT TO amc_runtime
    WITH CHECK (id=current_setting('amc.user_id',true));

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON tenants TO amc_runtime;
CREATE POLICY tenant_read ON tenants FOR SELECT TO amc_runtime USING (
    EXISTS (SELECT 1 FROM memberships m WHERE m.tenant_id=tenants.id
            AND m.user_id=current_setting('amc.user_id',true))
);
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, DELETE, UPDATE (role,client_id) ON memberships TO amc_runtime;
CREATE POLICY membership_read ON memberships FOR SELECT TO amc_runtime USING (
    user_id=current_setting('amc.user_id',true) OR amc_acl.member_role(tenant_id) IN ('admin','owner')
);
CREATE POLICY membership_grant ON memberships FOR INSERT TO amc_runtime WITH CHECK (
    role IN ('viewer','editor','admin','client_viewer') AND amc_acl.member_role(tenant_id) IN ('admin','owner')
);
CREATE POLICY membership_rescope ON memberships FOR UPDATE TO amc_runtime
    USING (role IN ('viewer','client_viewer') AND amc_acl.member_role(tenant_id) IN ('admin','owner'))
    WITH CHECK (role='client_viewer' AND amc_acl.member_role(tenant_id) IN ('admin','owner'));
CREATE POLICY membership_revoke ON memberships FOR DELETE TO amc_runtime
    USING (role='client_viewer' AND amc_acl.member_role(tenant_id) IN ('admin','owner'));

-- Each child inherits visibility through an RLS-protected parent and a composite FK.
CREATE POLICY scoped_read ON clients FOR SELECT TO amc_runtime USING (
    amc_acl.member_role(tenant_id) IN ('viewer','editor','admin','owner') OR id=amc_acl.client_scope(tenant_id)
);
CREATE POLICY scoped_read ON brands FOR SELECT TO amc_runtime USING (
    EXISTS (SELECT 1 FROM clients p WHERE (p.tenant_id,p.id)=(brands.tenant_id,brands.client_id))
);
CREATE POLICY scoped_read ON campaigns FOR SELECT TO amc_runtime USING (
    EXISTS (SELECT 1 FROM brands p WHERE (p.tenant_id,p.id)=(campaigns.tenant_id,campaigns.brand_id))
);
DO $$
DECLARE tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['work_tasks','deliverables','action_requests'] LOOP
        EXECUTE format('CREATE POLICY scoped_read ON %1$I FOR SELECT TO amc_runtime USING
            (EXISTS (SELECT 1 FROM campaigns p WHERE (p.tenant_id,p.id)=(%1$I.tenant_id,%1$I.campaign_id)))',tbl);
    END LOOP;
    FOREACH tbl IN ARRAY ARRAY['clients','brands','campaigns','work_tasks','deliverables','action_requests'] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',tbl);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',tbl);
        EXECUTE format('GRANT SELECT,INSERT,UPDATE ON %I TO amc_runtime',tbl);
        EXECUTE format('CREATE POLICY staff_insert ON %I FOR INSERT TO amc_runtime
            WITH CHECK (amc_acl.member_role(tenant_id) IN (''editor'',''admin'',''owner''))',tbl);
        EXECUTE format('CREATE POLICY staff_update ON %I FOR UPDATE TO amc_runtime
            USING (amc_acl.member_role(tenant_id) IN (''editor'',''admin'',''owner''))
            WITH CHECK (amc_acl.member_role(tenant_id) IN (''editor'',''admin'',''owner''))',tbl);
    END LOOP;
END $$;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
GRANT SELECT,INSERT ON audit_events TO amc_runtime;
CREATE POLICY audit_read ON audit_events FOR SELECT TO amc_runtime
    USING (amc_acl.member_role(tenant_id) IN ('admin','owner'));
CREATE POLICY audit_append ON audit_events FOR INSERT TO amc_runtime
    WITH CHECK (user_id=current_setting('amc.user_id',true) AND amc_acl.member_role(tenant_id) IN ('editor','admin','owner'));
