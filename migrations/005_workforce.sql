CREATE TABLE workforce_briefs (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	recipient_id VARCHAR(36) NOT NULL,
	title VARCHAR(150) NOT NULL,
	payload JSON,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	FOREIGN KEY(tenant_id, brand_id, campaign_id) REFERENCES campaigns (tenant_id, brand_id, id),
	UNIQUE (tenant_id, client_id, brand_id, campaign_id, id),
	FOREIGN KEY(recipient_id) REFERENCES users (id)
);

CREATE INDEX ix_workforce_briefs_tenant_id ON workforce_briefs (tenant_id);

CREATE TABLE workforce_runs (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	brief_id VARCHAR(36) NOT NULL,
	deliverable_id VARCHAR(36),
	knowledge JSON NOT NULL,
	plan JSON NOT NULL,
	checkpoints JSON NOT NULL,
	journal JSON NOT NULL,
	state VARCHAR(20) NOT NULL,
	lease VARCHAR(36),
	ready_at TIMESTAMP WITH TIME ZONE NOT NULL,
	attempts INTEGER NOT NULL,
	budget_microusd INTEGER NOT NULL,
	reserved_microusd INTEGER NOT NULL,
	last_error VARCHAR(40),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, client_id, brand_id, campaign_id, brief_id) REFERENCES workforce_briefs (tenant_id, client_id, brand_id, campaign_id, id),
	FOREIGN KEY(tenant_id, campaign_id, deliverable_id) REFERENCES deliverables (tenant_id, campaign_id, id),
	UNIQUE (brief_id),
	CHECK (state IN ('queued','running','failed','awaiting_qa'))
);

CREATE INDEX ix_workforce_queue ON workforce_runs (tenant_id, campaign_id, state, ready_at);

ALTER TABLE workforce_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workforce_briefs FORCE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE(payload) ON workforce_briefs TO amc_runtime;
CREATE FUNCTION amc_acl.brief_recipient(t text,c text,b text,p text,u text) RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT u=current_setting('amc.user_id',true) AND amc_acl.member_role(t)='client_viewer' AND EXISTS (
    SELECT FROM public.portal_grants g WHERE g.tenant_id=t AND g.user_id=u AND g.client_id=c
      AND (g.brand_id IS NULL OR g.brand_id=b) AND (g.campaign_id IS NULL OR g.campaign_id=p))
$$;
REVOKE ALL ON FUNCTION amc_acl.brief_recipient(text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.brief_recipient(text,text,text,text,text) TO amc_runtime;
CREATE POLICY brief_read ON workforce_briefs FOR SELECT TO amc_runtime USING (
 amc_acl.member_role(tenant_id) IN ('owner','admin','editor','viewer') OR
 amc_acl.brief_recipient(tenant_id,client_id,brand_id,campaign_id,recipient_id));
CREATE POLICY brief_open ON workforce_briefs FOR INSERT TO amc_runtime WITH CHECK (
 amc_acl.member_role(tenant_id) IN ('owner','admin') AND payload IS NULL AND EXISTS (
 SELECT FROM portal_grants g WHERE g.tenant_id=workforce_briefs.tenant_id AND g.user_id=recipient_id
 AND g.client_id=workforce_briefs.client_id AND (g.brand_id IS NULL OR g.brand_id=workforce_briefs.brand_id)
 AND (g.campaign_id IS NULL OR g.campaign_id=workforce_briefs.campaign_id)));
CREATE POLICY brief_submit ON workforce_briefs FOR UPDATE TO amc_runtime
 USING(payload IS NULL AND amc_acl.brief_recipient(tenant_id,client_id,brand_id,campaign_id,recipient_id))
 WITH CHECK(payload IS NOT NULL AND amc_acl.brief_recipient(tenant_id,client_id,brand_id,campaign_id,recipient_id));

ALTER TABLE workforce_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workforce_runs FORCE ROW LEVEL SECURITY;
GRANT SELECT,INSERT,UPDATE(checkpoints,journal,state,lease,ready_at,attempts,reserved_microusd,last_error,deliverable_id)
 ON workforce_runs TO amc_runtime;
CREATE POLICY run_read ON workforce_runs FOR SELECT TO amc_runtime USING (
 amc_acl.member_role(tenant_id) IN ('owner','admin','editor','viewer'));
CREATE POLICY run_queue ON workforce_runs FOR INSERT TO amc_runtime WITH CHECK (
 amc_acl.member_role(tenant_id) IN ('owner','admin','editor') AND state='queued' AND deliverable_id IS NULL);
CREATE POLICY worker_checkpoint ON workforce_runs FOR UPDATE TO amc_runtime
 USING (amc_acl.member_role(tenant_id)='editor'
 AND client_id=current_setting('amc.worker_client',true) AND brand_id=current_setting('amc.worker_brand',true)
 AND campaign_id=current_setting('amc.worker_campaign',true));
CREATE POLICY worker_scope ON workforce_runs AS RESTRICTIVE FOR SELECT TO amc_runtime USING (
 nullif(current_setting('amc.worker_campaign',true),'') IS NULL OR
 (campaign_id=current_setting('amc.worker_campaign',true) AND brand_id=current_setting('amc.worker_brand',true)
 AND client_id=current_setting('amc.worker_client',true)));
