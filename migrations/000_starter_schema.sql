-- Frozen schema from the reviewed starter.
CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(320) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE tenants (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	mode VARCHAR(12) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE memberships (
	tenant_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	PRIMARY KEY (tenant_id, user_id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE clients (
	id VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(36) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	sector VARCHAR(160) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_clients_tenant_id ON clients (tenant_id);

CREATE TABLE audit_events (
	id VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	event VARCHAR(90) NOT NULL, 
	subject_id VARCHAR(36) NOT NULL, 
	details JSON NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_audit_events_tenant_id ON audit_events (tenant_id);

CREATE TABLE brands (
	id VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(36) NOT NULL, 
	client_id VARCHAR(36) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	brand_guidelines TEXT NOT NULL, 
	product_truth TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(client_id) REFERENCES clients (id)
);

CREATE INDEX ix_brands_client_id ON brands (client_id);

CREATE INDEX ix_brands_tenant_id ON brands (tenant_id);

CREATE TABLE campaigns (
	id VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(36) NOT NULL, 
	brand_id VARCHAR(36) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	brief TEXT NOT NULL, 
	objective TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(brand_id) REFERENCES brands (id)
);

CREATE INDEX ix_campaigns_brand_id ON campaigns (brand_id);

CREATE INDEX ix_campaigns_tenant_id ON campaigns (tenant_id);

CREATE TABLE work_tasks (
	id VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(36) NOT NULL, 
	campaign_id VARCHAR(36) NOT NULL, 
	workflow_key VARCHAR(80) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	role_slug VARCHAR(90) NOT NULL, 
	expected_output TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_campaign_workflow_task UNIQUE (campaign_id, workflow_key), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id)
);

CREATE INDEX ix_work_tasks_campaign_id ON work_tasks (campaign_id);

CREATE INDEX ix_work_tasks_tenant_id ON work_tasks (tenant_id);

CREATE TABLE deliverables (
	id VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(36) NOT NULL, 
	campaign_id VARCHAR(36) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	content JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	reviewed_by VARCHAR(36), 
	review_note TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id)
);

CREATE INDEX ix_deliverables_campaign_id ON deliverables (campaign_id);

CREATE INDEX ix_deliverables_tenant_id ON deliverables (tenant_id);

CREATE TABLE action_requests (
	id VARCHAR(36) NOT NULL, 
	tenant_id VARCHAR(36) NOT NULL, 
	campaign_id VARCHAR(36) NOT NULL, 
	action_kind VARCHAR(40) NOT NULL, 
	payload JSON NOT NULL, 
	state VARCHAR(30) NOT NULL, 
	proposed_by VARCHAR(36) NOT NULL, 
	reviewed_by VARCHAR(36), 
	review_note TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id)
);

CREATE INDEX ix_action_requests_tenant_id ON action_requests (tenant_id);

CREATE INDEX ix_action_requests_campaign_id ON action_requests (campaign_id);
