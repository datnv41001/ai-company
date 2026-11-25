-- Independent product-module line. The core identity migration sequence stays available.
CREATE SCHEMA amc_business;
REVOKE ALL ON SCHEMA amc_business FROM PUBLIC;
GRANT USAGE ON SCHEMA amc_business TO amc_runtime;
CREATE TABLE amc_business.versions (version integer PRIMARY KEY);
REVOKE ALL ON amc_business.versions FROM PUBLIC,amc_runtime;
GRANT SELECT ON amc_business.versions TO amc_runtime;

CREATE TABLE public.business_workspace_records (
 id varchar(36) PRIMARY KEY, tenant_id varchar(36) NOT NULL, client_id varchar(36) NOT NULL,
 brand_id varchar(36), scope varchar(36) NOT NULL, kind varchar(12) NOT NULL, revision integer NOT NULL CHECK(revision>0),
 actor varchar(36) NOT NULL, command_key varchar(96) NOT NULL, request_digest varchar(64) NOT NULL,
 payload jsonb NOT NULL, created_at timestamptz NOT NULL,
 FOREIGN KEY(tenant_id,client_id) REFERENCES public.clients(tenant_id,id),
 FOREIGN KEY(tenant_id,client_id,brand_id) REFERENCES public.brands(tenant_id,client_id,id),
 CHECK((kind='company' AND brand_id IS NULL AND scope='company') OR (kind IN ('brand','brief') AND brand_id IS NOT NULL AND scope=brand_id)),
 UNIQUE(tenant_id,client_id,scope,actor,command_key)
);
CREATE UNIQUE INDEX uq_workspace_profile_revision ON public.business_workspace_records(tenant_id,client_id,scope,revision) WHERE kind<>'brief';
CREATE INDEX ix_workspace_owned_briefs ON public.business_workspace_records(tenant_id,client_id,brand_id,actor,kind,created_at);

ALTER TABLE public.business_workspace_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_workspace_records FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.business_workspace_records FROM PUBLIC,amc_runtime;
GRANT SELECT ON public.business_workspace_records TO amc_runtime;
CREATE POLICY workspace_staff ON public.business_workspace_records FOR SELECT TO amc_runtime USING (
 amc_acl.knowledge_read(tenant_id,'internal') AND (kind<>'brief' OR actor=current_setting('amc.user_id',true))
);
CREATE POLICY workspace_append ON public.business_workspace_records FOR INSERT TO CURRENT_USER
 WITH CHECK (actor=current_setting('amc.user_id',true) AND amc_acl.knowledge_read(tenant_id,'internal'));
CREATE TRIGGER workspace_immutable BEFORE UPDATE OR DELETE ON public.business_workspace_records
 FOR EACH ROW EXECUTE FUNCTION amc_acl.immutable_knowledge();

-- Every write, including brand overrides and brief pinning, takes the same client
-- lock before reading company/brand revisions. The membership lock orders revocation.
CREATE FUNCTION amc_business.lock_client(t text,c text) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF amc_acl.knowledge_read(t,'internal') IS NOT TRUE OR current_setting('transaction_isolation') <> 'read committed'
 THEN RAISE insufficient_privilege; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('workspace-company:'||t||':'||c,1));
 PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=current_setting('amc.user_id',true)
 AND role IN ('owner','admin','editor') FOR SHARE;
 IF NOT FOUND THEN RAISE insufficient_privilege; END IF;
END $$;
REVOKE ALL ON FUNCTION amc_business.lock_client(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_business.lock_client(text,text) TO amc_runtime;

CREATE FUNCTION amc_business.append_record(doc text,proof text) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE v jsonb:=doc::jsonb;
BEGIN
 IF amc_acl.valid_knowledge_append('business_workspace_records',doc,proof) IS NOT TRUE
 OR v->>'actor' IS DISTINCT FROM current_setting('amc.user_id',true) THEN RAISE insufficient_privilege; END IF;
 PERFORM amc_business.lock_client(v->>'tenant_id',v->>'client_id');
 INSERT INTO public.business_workspace_records SELECT * FROM jsonb_populate_record(NULL::public.business_workspace_records,v);
END $$;
REVOKE ALL ON FUNCTION amc_business.append_record(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_business.append_record(text,text) TO amc_runtime;
INSERT INTO amc_business.versions VALUES(1);
