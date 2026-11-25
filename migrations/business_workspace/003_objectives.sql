-- Client-owned objectives are separate from historical brand-local "company" records.
CREATE TABLE public.business_company_objectives (
 id varchar(36) PRIMARY KEY,tenant_id varchar(36) NOT NULL,client_id varchar(36) NOT NULL,
 revision_id varchar(36) NOT NULL,subject varchar(36) NOT NULL,revision int NOT NULL,sequence int NOT NULL,
 state varchar(12) NOT NULL,name varchar(160) NOT NULL,owner_name varchar(160) NOT NULL,actor varchar(36) NOT NULL,
 command_key varchar(96) NOT NULL,request_digest varchar(64) NOT NULL,digest varchar(64) NOT NULL,
 reason varchar(160) NOT NULL,created_at timestamptz NOT NULL,
 UNIQUE(tenant_id,client_id,id),FOREIGN KEY(tenant_id,client_id) REFERENCES public.clients(tenant_id,id),
 FOREIGN KEY(tenant_id,client_id,revision_id) REFERENCES public.business_company_objectives(tenant_id,client_id,id),
 UNIQUE(tenant_id,client_id,actor,command_key),UNIQUE(tenant_id,client_id,subject,revision,sequence),
 CHECK(revision>0 AND sequence>=0),
 CHECK((sequence=0 AND revision_id=id AND state='draft') OR (sequence>0 AND revision_id<>id AND state IN ('approved','disputed','withdrawn','superseded')))
);
ALTER TABLE public.business_company_objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_company_objectives FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.business_company_objectives FROM PUBLIC,amc_runtime;
GRANT SELECT ON public.business_company_objectives TO amc_runtime;
CREATE POLICY objective_read ON public.business_company_objectives FOR SELECT USING(amc_acl.knowledge_read(tenant_id,'internal'));
CREATE POLICY objective_append ON public.business_company_objectives FOR INSERT TO CURRENT_USER WITH CHECK(actor=current_setting('amc.user_id',true));
CREATE TRIGGER immutable_objectives BEFORE UPDATE OR DELETE ON public.business_company_objectives FOR EACH ROW EXECUTE FUNCTION amc_acl.immutable_knowledge();

CREATE TABLE public.business_company_objective_edges (
 revision_id varchar(36) PRIMARY KEY,company_revision_id varchar(36) NOT NULL,
 tenant_id varchar(36) NOT NULL,client_id varchar(36) NOT NULL,brand_id varchar(36) NOT NULL,
 FOREIGN KEY(tenant_id,client_id,brand_id,revision_id) REFERENCES public.knowledge_revisions(tenant_id,client_id,brand_id,id),
 FOREIGN KEY(tenant_id,client_id,company_revision_id) REFERENCES public.business_company_objectives(tenant_id,client_id,id)
);
CREATE INDEX ix_company_objective_usage ON public.business_company_objective_edges(tenant_id,client_id,company_revision_id);
ALTER TABLE public.business_company_objective_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_company_objective_edges FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.business_company_objective_edges FROM PUBLIC,amc_runtime;
GRANT SELECT ON public.business_company_objective_edges TO amc_runtime;
CREATE POLICY edge_read ON public.business_company_objective_edges FOR SELECT TO amc_runtime USING
 (EXISTS (SELECT FROM public.knowledge_revisions k WHERE k.id=revision_id) AND amc_acl.knowledge_read(tenant_id,'internal'));
CREATE POLICY edge_append ON public.business_company_objective_edges FOR INSERT TO CURRENT_USER WITH CHECK(amc_acl.knowledge_read(tenant_id,'internal'));
CREATE TRIGGER immutable_objective_edges BEFORE UPDATE OR DELETE ON public.business_company_objective_edges FOR EACH ROW EXECUTE FUNCTION amc_acl.immutable_knowledge();

CREATE FUNCTION amc_business.link_objective() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE ref text:=CASE NEW.kind WHEN 'objective' THEN NEW.data->>'company_parent' WHEN 'kpi' THEN NEW.data->>'company_objective' END;
BEGIN
 IF ref IS NOT NULL THEN
  IF NOT EXISTS(SELECT FROM public.business_company_objectives o WHERE (o.tenant_id,o.client_id,o.id,o.sequence)=(NEW.tenant_id,NEW.client_id,ref,0))
  THEN RAISE EXCEPTION 'Unknown company objective revision' USING ERRCODE='23503'; END IF;
  INSERT INTO public.business_company_objective_edges VALUES(NEW.id,ref,NEW.tenant_id,NEW.client_id,NEW.brand_id);
 END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_business.link_objective() FROM PUBLIC,amc_runtime;
CREATE TRIGGER link_company_objective AFTER INSERT ON public.knowledge_revisions FOR EACH ROW EXECUTE FUNCTION amc_business.link_objective();

CREATE FUNCTION amc_business.append_objective(doc text,proof text) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE v jsonb:=doc::jsonb;
BEGIN
 IF amc_acl.valid_knowledge_append('business_company_objectives',doc,proof) IS NOT TRUE
 OR v->>'actor' IS DISTINCT FROM current_setting('amc.user_id',true) THEN RAISE insufficient_privilege; END IF;
 PERFORM amc_business.lock_client(v->>'tenant_id',v->>'client_id');
 IF (v->>'sequence')::int>0 AND amc_acl.member_role(v->>'tenant_id') NOT IN ('owner','admin') THEN RAISE insufficient_privilege; END IF;
 INSERT INTO public.business_company_objectives SELECT * FROM jsonb_populate_record(NULL::public.business_company_objectives,v);
END $$;
REVOKE ALL ON FUNCTION amc_business.append_objective(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_business.append_objective(text,text) TO amc_runtime;
INSERT INTO amc_business.versions VALUES(3);
