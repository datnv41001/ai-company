-- Composite identities validate the entire parent chain for scoped review records.
ALTER TABLE memberships ADD UNIQUE (tenant_id,user_id,client_id);
ALTER TABLE brands ADD UNIQUE (tenant_id,client_id,id);
ALTER TABLE campaigns ADD UNIQUE (tenant_id,brand_id,id);
ALTER TABLE deliverables ADD UNIQUE (tenant_id,campaign_id,id);

CREATE TABLE portal_grants (
	tenant_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36),
	campaign_id VARCHAR(36),
	can_comment BOOLEAN NOT NULL,
	can_decide BOOLEAN NOT NULL,
	PRIMARY KEY (tenant_id, user_id),
	FOREIGN KEY(tenant_id, user_id, client_id) REFERENCES memberships (tenant_id, user_id, client_id) ON DELETE CASCADE,
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	FOREIGN KEY(tenant_id, brand_id, campaign_id) REFERENCES campaigns (tenant_id, brand_id, id),
	CHECK (campaign_id IS NULL OR brand_id IS NOT NULL)
);

CREATE TABLE client_reviews (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	campaign_id VARCHAR(36) NOT NULL,
	deliverable_id VARCHAR(36) NOT NULL,
	version INTEGER NOT NULL,
	title VARCHAR(160) NOT NULL,
	preview TEXT NOT NULL,
	digest VARCHAR(64) NOT NULL,
	requested_by VARCHAR(36) NOT NULL,
	qa_by VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	FOREIGN KEY(tenant_id, brand_id, campaign_id) REFERENCES campaigns (tenant_id, brand_id, id),
	FOREIGN KEY(tenant_id, campaign_id, deliverable_id) REFERENCES deliverables (tenant_id, campaign_id, id),
	UNIQUE (deliverable_id, version),
	UNIQUE (tenant_id, id, digest),
	CHECK (version > 0 AND expires_at > created_at),
	FOREIGN KEY(requested_by) REFERENCES users (id),
	FOREIGN KEY(qa_by) REFERENCES users (id)
);

CREATE INDEX ix_client_reviews_client_id ON client_reviews (client_id);

CREATE INDEX ix_client_reviews_tenant_id ON client_reviews (tenant_id);

CREATE TABLE review_entries (
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	review_id VARCHAR(36) NOT NULL,
	digest VARCHAR(64) NOT NULL,
	actor_id VARCHAR(36) NOT NULL,
	kind VARCHAR(24) NOT NULL,
	note TEXT NOT NULL,
	request_key VARCHAR(80) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, review_id, digest) REFERENCES client_reviews (tenant_id, id, digest),
	UNIQUE (review_id, actor_id, request_key),
	CHECK (kind IN ('comment','approved','rejected','changes_requested','cancelled','superseded')),
	FOREIGN KEY(actor_id) REFERENCES users (id)
);

CREATE INDEX ix_review_entries_review_id ON review_entries (review_id);

CREATE UNIQUE INDEX uq_review_terminal ON review_entries (review_id) WHERE kind <> 'comment';
