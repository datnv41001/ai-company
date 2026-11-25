-- Additive C1 tables. Every foreign revision and snapshot edge includes tenant, client and brand.

CREATE TABLE knowledge_revisions (
	subject VARCHAR(64) NOT NULL,
	kind VARCHAR(24) NOT NULL,
	revision INTEGER NOT NULL,
	data JSON NOT NULL,
	digest VARCHAR(64) NOT NULL,
	author VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	visibility VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (tenant_id, client_id, brand_id, subject, revision),
	CHECK (revision > 0),
	UNIQUE (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	CHECK (visibility IN ('public','internal','restricted'))
);

CREATE TABLE knowledge_snapshots (
    campaign_id VARCHAR(36),
    brief_id VARCHAR(36),
    CHECK ((campaign_id IS NULL) = (brief_id IS NULL)),
    FOREIGN KEY(tenant_id,client_id,brand_id,campaign_id,brief_id)
      REFERENCES workforce_briefs(tenant_id,client_id,brand_id,campaign_id,id),
	canonical TEXT NOT NULL,
	digest VARCHAR(64) NOT NULL,
	snapshot_as_of TIMESTAMP WITH TIME ZONE NOT NULL,
	preview_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	visibility VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	CHECK (visibility IN ('public','internal','restricted'))
);

CREATE TABLE knowledge_commands (
	key VARCHAR(96) NOT NULL,
	actor VARCHAR(36) NOT NULL,
	operation VARCHAR(24) NOT NULL,
	request_digest VARCHAR(64) NOT NULL,
	result JSON NOT NULL,
	snapshot_id VARCHAR(36),
	effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
	queued_at TIMESTAMP WITH TIME ZONE,
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	visibility VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (tenant_id, client_id, brand_id, actor, key),
	FOREIGN KEY(tenant_id, client_id, brand_id, snapshot_id) REFERENCES knowledge_snapshots (tenant_id, client_id, brand_id, id),
	UNIQUE (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	CHECK (visibility IN ('public','internal','restricted'))
);

CREATE TABLE knowledge_dependencies (
	snapshot_id VARCHAR(36) NOT NULL,
	revision_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	visibility VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, client_id, brand_id, snapshot_id) REFERENCES knowledge_snapshots (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id, revision_id) REFERENCES knowledge_revisions (tenant_id, client_id, brand_id, id),
	UNIQUE (snapshot_id, revision_id),
	UNIQUE (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	CHECK (visibility IN ('public','internal','restricted'))
);

CREATE TABLE knowledge_events (
    qualification_id VARCHAR(36),
    FOREIGN KEY(tenant_id, client_id, brand_id, qualification_id) REFERENCES knowledge_revisions (tenant_id, client_id, brand_id, id),
	revision_id VARCHAR(36) NOT NULL,
	sequence INTEGER NOT NULL,
	state VARCHAR(16) NOT NULL,
	reason VARCHAR(400) NOT NULL,
	actor VARCHAR(36) NOT NULL,
	effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	visibility VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, client_id, brand_id, revision_id) REFERENCES knowledge_revisions (tenant_id, client_id, brand_id, id),
	UNIQUE (revision_id, sequence),
	UNIQUE (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	CHECK (visibility IN ('public','internal','restricted'))
);

CREATE TABLE knowledge_links (
	revision_id VARCHAR(36) NOT NULL,
	target_id VARCHAR(36) NOT NULL,
	relation VARCHAR(24) NOT NULL,
	id VARCHAR(36) NOT NULL,
	tenant_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	visibility VARCHAR(12) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, client_id, brand_id, revision_id) REFERENCES knowledge_revisions (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id, target_id) REFERENCES knowledge_revisions (tenant_id, client_id, brand_id, id),
	UNIQUE (revision_id, relation, target_id),
	UNIQUE (tenant_id, client_id, brand_id, id),
	FOREIGN KEY(tenant_id, client_id, brand_id) REFERENCES brands (tenant_id, client_id, id),
	CHECK (visibility IN ('public','internal','restricted'))
);

CREATE INDEX ix_knowledge_usage ON knowledge_dependencies (revision_id, snapshot_id);

CREATE FUNCTION amc_acl.immutable_knowledge() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Immutable knowledge history' USING ERRCODE='55000'; END $$;
REVOKE ALL ON FUNCTION amc_acl.immutable_knowledge() FROM PUBLIC,amc_runtime;

CREATE FUNCTION amc_acl.knowledge_read(t text, v text) RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT amc_acl.authenticated_actor() AND t=current_setting('amc.tenant_id',true)
 AND coalesce(current_setting('amc.worker_campaign',true),'')=''
 AND coalesce(current_setting('amc.worker_client',true),'')='' AND coalesce(current_setting('amc.worker_brand',true),'')=''
 AND (amc_acl.member_role(t) IN ('admin','owner') OR (v IN ('internal','public') AND amc_acl.member_role(t) IN ('editor','viewer')))
$$;
REVOKE ALL ON FUNCTION amc_acl.knowledge_read(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.knowledge_read(text,text) TO amc_runtime;

-- One lock ordering covers edits, approvals, preview, queue, QA and share.
-- The membership lock also serializes against ordinary revocation/demotion.
CREATE FUNCTION amc_acl.lock_knowledge(t text,c text,b text) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF amc_acl.knowledge_read(t,'internal') IS NOT TRUE THEN RAISE insufficient_privilege; END IF;
 IF current_setting('transaction_isolation') <> 'read committed' THEN
   RAISE EXCEPTION 'Business knowledge requires READ COMMITTED' USING ERRCODE='25000';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('k22:'||t||':'||c||':'||b,22));
 PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=current_setting('amc.user_id',true)
   AND role IN ('editor','admin','owner') FOR SHARE;
 IF NOT FOUND THEN RAISE insufficient_privilege; END IF;
END $$;
REVOKE ALL ON FUNCTION amc_acl.lock_knowledge(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.lock_knowledge(text,text,text) TO amc_runtime;

-- Lock current recipient entitlement before campaign/brief facts, to order
-- target authorization against a grant change or a concurrent submission.
CREATE FUNCTION amc_acl.lock_knowledge_target(t text,c text,b text,k text,i text) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE recipient text;
BEGIN
 PERFORM amc_acl.lock_knowledge(t,c,b);
 SELECT recipient_id INTO recipient FROM public.workforce_briefs WHERE (tenant_id,client_id,brand_id,campaign_id,id)=(t,c,b,k,i);
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=recipient AND role='client_viewer' AND client_id=c FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM 1 FROM public.portal_grants WHERE tenant_id=t AND user_id=recipient AND client_id=c
 AND (brand_id IS NULL OR brand_id=b) AND (campaign_id IS NULL OR campaign_id=k) FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM 1 FROM public.campaigns WHERE (tenant_id,brand_id,id)=(t,b,k) FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 PERFORM 1 FROM public.workforce_briefs WHERE (tenant_id,client_id,brand_id,campaign_id,id,recipient_id)=(t,c,b,k,i,recipient) FOR SHARE;
 RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION amc_acl.lock_knowledge_target(text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.lock_knowledge_target(text,text,text,text,text) TO amc_runtime;

-- Track edits on the pre-existing mutable target independently of identical
-- A → B → A content. Logical dump/restore preserves this auxiliary counter.
CREATE TABLE amc_acl.knowledge_target_epochs(kind text NOT NULL,id text NOT NULL,epoch bigint NOT NULL,PRIMARY KEY(kind,id));
REVOKE ALL ON amc_acl.knowledge_target_epochs FROM PUBLIC, amc_runtime;
CREATE FUNCTION amc_acl.bump_knowledge_target_epoch() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 INSERT INTO amc_acl.knowledge_target_epochs VALUES(TG_ARGV[0],NEW.id,1)
 ON CONFLICT(kind,id) DO UPDATE SET epoch=knowledge_target_epochs.epoch+1;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.bump_knowledge_target_epoch() FROM PUBLIC, amc_runtime;
CREATE TRIGGER knowledge_epoch_campaign AFTER UPDATE OF tenant_id,brand_id,name,brief,objective,status ON public.campaigns
 FOR EACH ROW EXECUTE FUNCTION amc_acl.bump_knowledge_target_epoch('campaign');
CREATE TRIGGER knowledge_epoch_brief AFTER UPDATE OF tenant_id,client_id,brand_id,campaign_id,recipient_id,title,payload ON public.workforce_briefs
 FOR EACH ROW EXECUTE FUNCTION amc_acl.bump_knowledge_target_epoch('brief');

CREATE FUNCTION amc_acl.knowledge_target_epoch(t text,c text,b text,k text,i text) RETURNS bigint[]
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT ARRAY[coalesce((SELECT epoch FROM amc_acl.knowledge_target_epochs WHERE kind='campaign' AND id=k),0),
              coalesce((SELECT epoch FROM amc_acl.knowledge_target_epochs WHERE kind='brief' AND id=i),0)]
 WHERE amc_acl.knowledge_read(t,'internal') AND EXISTS(SELECT FROM public.workforce_briefs
 WHERE (tenant_id,client_id,brand_id,campaign_id,id)=(t,c,b,k,i));
$$;
REVOKE ALL ON FUNCTION amc_acl.knowledge_target_epoch(text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.knowledge_target_epoch(text,text,text,text,text) TO amc_runtime;

DO $install$
DECLARE n name; rel name;
BEGIN
 SELECT ns.nspname INTO STRICT n FROM pg_extension e JOIN pg_namespace ns ON ns.oid=e.extnamespace WHERE e.extname='pgcrypto';
 EXECUTE format($body$
   CREATE FUNCTION amc_acl.valid_knowledge_append(rel text, doc text, proof text) RETURNS boolean
   LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog
   BEGIN ATOMIC
    SELECT proof=encode(%I.hmac(convert_to('knowledge-v22'||chr(10)||current_setting('amc.user_id',true)||chr(10)||
         txid_current()::text||chr(10)||rel||chr(10)||doc,'UTF8'),secret,'sha256'::text),'hex')
    FROM amc_acl.identity_key WHERE singleton;
   END
 $body$,n);
 FOREACH rel IN ARRAY ARRAY['knowledge_revisions','knowledge_events','knowledge_links','knowledge_snapshots','knowledge_dependencies','knowledge_commands']
 LOOP
   EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',rel);
   EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY',rel);
   EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC, amc_runtime',rel);
   EXECUTE format('GRANT SELECT ON public.%I TO amc_runtime',rel);
   EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION amc_acl.immutable_knowledge()',rel);
   EXECUTE format('CREATE POLICY knowledge_read ON public.%I FOR SELECT TO amc_runtime USING (amc_acl.knowledge_read(tenant_id,visibility))',rel);
   EXECUTE format('CREATE POLICY signed_append ON public.%I FOR INSERT TO CURRENT_USER WITH CHECK (amc_acl.knowledge_read(tenant_id,visibility))',rel);
 END LOOP;
END $install$;
REVOKE ALL ON FUNCTION amc_acl.valid_knowledge_append(text,text,text) FROM PUBLIC,amc_runtime;

-- Only the authenticated service can attest a whole validated row. A runtime
-- LOGIN with readable data cannot manufacture approvals or mutate history.
CREATE FUNCTION amc_acl.append_knowledge(rel text, doc text, proof text) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE v jsonb:=doc::jsonb; role_name text;
BEGIN
 IF rel NOT IN ('knowledge_revisions','knowledge_events','knowledge_links','knowledge_snapshots','knowledge_dependencies','knowledge_commands')
    OR amc_acl.valid_knowledge_append(rel,doc,proof) IS NOT TRUE
    OR amc_acl.knowledge_read(v->>'tenant_id',v->>'visibility') IS NOT TRUE THEN RAISE insufficient_privilege; END IF;
 PERFORM amc_acl.lock_knowledge(v->>'tenant_id',v->>'client_id',v->>'brand_id');
 role_name:=amc_acl.member_role(v->>'tenant_id');
 IF (rel='knowledge_events' OR v->>'visibility'='restricted') AND role_name NOT IN ('owner','admin') THEN
   RAISE insufficient_privilege;
 END IF;
 IF (v ? 'actor' AND v->>'actor' IS DISTINCT FROM current_setting('amc.user_id',true))
    OR (v ? 'author' AND v->>'author' IS DISTINCT FROM current_setting('amc.user_id',true)) THEN RAISE insufficient_privilege; END IF;
 EXECUTE format('INSERT INTO public.%I SELECT * FROM pg_catalog.jsonb_populate_record(null::public.%I,$1)',rel,rel) USING v;
END $$;
REVOKE ALL ON FUNCTION amc_acl.append_knowledge(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.append_knowledge(text,text,text) TO amc_runtime;
