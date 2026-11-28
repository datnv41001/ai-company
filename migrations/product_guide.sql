-- Guide-specific predicates are only entered from existing trusted queue/lease routines.
-- No grants to read Knowledge, impersonated user, or worker-supplied provenance.
CREATE FUNCTION amc_c3.guide_revision_current(t text,c text,b text,i text,at_time timestamptz) RETURNS boolean
LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS (
   SELECT FROM public.knowledge_revisions v
   WHERE (v.tenant_id,v.client_id,v.brand_id,v.id)=(t,c,b,i)
     AND coalesce((v.data->>'valid_from')::timestamptz,'-infinity')<=at_time
     AND coalesce((v.data->>'valid_until')::timestamptz,'infinity')>at_time
     AND (SELECT e.state FROM public.knowledge_events e WHERE e.revision_id=v.id ORDER BY e.sequence DESC LIMIT 1)='approved'
 )
$$;
REVOKE ALL ON FUNCTION amc_c3.guide_revision_current(text,text,text,text,timestamptz) FROM PUBLIC;

CREATE FUNCTION amc_c3.guide_authorized(r public.workforce_runs, lock_dependencies boolean) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
 release_name constant text := 'WF-06/product-use-guide@1';
 t text := r.tenant_id; c text := r.client_id; b text := r.brand_id; k text := r.campaign_id;
 child public.workforce_briefs; child_manifest public.knowledge_snapshots; parent public.workforce_runs;
 doc public.deliverables; handoff public.knowledge_commands; qa public.knowledge_commands; source public.knowledge_snapshots;
 binding jsonb; envelope jsonb; decision jsonb; parent_data jsonb; review_ids text[]; rid text; review public.knowledge_commands;
 mandate public.knowledge_revisions; approvals text[]; member_id text; author_id text; objective public.business_company_objectives;
 at_time timestamptz;
BEGIN
 IF r.knowledge::jsonb #>> '{registry,workflow}' IS DISTINCT FROM release_name THEN RETURN true; END IF;
 SELECT * INTO child FROM public.workforce_briefs WHERE (tenant_id,client_id,brand_id,campaign_id,id)=(t,c,b,k,r.brief_id) AND origin='internal';
 binding := child.payload::jsonb->'guide_binding';
 IF child.payload::jsonb->>'task_version' IS DISTINCT FROM 'amc.product-use-guide/1' OR binding IS NULL THEN RETURN false; END IF;

 -- Immutable IDs resolve in the task's scope. Even the migration role must compare all four dimensions.
 SELECT * INTO child_manifest FROM public.knowledge_snapshots WHERE (tenant_id,client_id,brand_id,campaign_id,brief_id,id,digest)=
    (t,c,b,k,child.id,r.knowledge::jsonb#>>'{c3_manifest,id}',r.knowledge::jsonb#>>'{c3_manifest,digest}');
 envelope := child_manifest.canonical::jsonb;
 IF envelope->'guide_binding' IS DISTINCT FROM binding OR envelope->'projection' IS DISTINCT FROM r.knowledge::jsonb->'c3_projection'
    OR envelope IS NULL THEN RETURN false; END IF;
 SELECT * INTO source FROM public.knowledge_snapshots WHERE (tenant_id,client_id,brand_id,campaign_id,id,digest)=
    (t,c,b,k,binding->>'source_manifest',binding->>'source_manifest_digest');
 SELECT * INTO parent FROM public.workforce_runs WHERE (tenant_id,client_id,brand_id,campaign_id,id,brief_id,deliverable_id)=
    (t,c,b,k,binding->>'strategy_run',source.brief_id,binding->>'strategy_document');
 IF NOT FOUND OR parent.knowledge::jsonb#>>'{registry,workflow}' IS DISTINCT FROM 'WF-03/research-strategy-draft@3'
    OR parent.knowledge::jsonb#>>'{registry,manifest_digest}' IS DISTINCT FROM binding->>'source_release_digest'
    OR parent.knowledge::jsonb->'c3_manifest' IS DISTINCT FROM jsonb_build_object('id',source.id,'digest',source.digest)
 THEN RETURN false; END IF;
 SELECT * INTO handoff FROM public.knowledge_commands WHERE (tenant_id,client_id,brand_id,snapshot_id,id,operation)=
    (t,c,b,source.id,binding->>'handoff_receipt','c3_strategy_decision');
 decision:=handoff.result::jsonb;
 IF decision->>'version' IS DISTINCT FROM 'amc.internal-strategy-handoff/2'
    OR decision->'reasons' IS DISTINCT FROM '[]'::jsonb
    OR decision#>>'{request,recipient_id}' IS DISTINCT FROM child.recipient_id
    OR decision#>>'{work_order,asset_type}' IS DISTINCT FROM 'web_use_guide'
    OR coalesce(decision#>>'{work_order,placement}','') NOT IN ('web','owned product page')
    OR decision->'scope' IS DISTINCT FROM jsonb_build_object('tenant_id',t,'client_id',c,'brand_id',b,'campaign_id',k)
    OR decision#>>'{provenance,run_id}' IS DISTINCT FROM parent.id
    OR decision#>>'{provenance,document_id}' IS DISTINCT FROM parent.deliverable_id
    OR decision->>'qa_receipt' IS DISTINCT FROM binding->>'qa_receipt'
    OR decision->>'content_digest' IS DISTINCT FROM binding->>'content_digest'
    OR decision->'revision' IS DISTINCT FROM binding->'revision' THEN RETURN false; END IF;
 SELECT * INTO qa FROM public.knowledge_commands WHERE (tenant_id,client_id,brand_id,snapshot_id,id,operation)=
    (t,c,b,source.id,binding->>'qa_receipt','c3_qa');
 IF NOT FOUND OR qa.result->>'run_id' IS DISTINCT FROM parent.id OR qa.result->>'content_digest' IS DISTINCT FROM decision->>'content_digest'
    OR qa.result->>'qa_revision' IS DISTINCT FROM decision->>'revision' THEN RETURN false; END IF;
 IF qa.id IS DISTINCT FROM (SELECT q.id FROM public.knowledge_commands q WHERE
      (q.tenant_id,q.client_id,q.brand_id,q.snapshot_id,q.actor,q.operation)=(t,c,b,source.id,qa.actor,'c3_qa')
      AND q.result->>'run_id'=parent.id AND q.result->>'qa_revision'=binding->>'revision'
      AND q.result->>'content_digest'=binding->>'content_digest' ORDER BY q.effective_at DESC LIMIT 1)
 THEN RETURN false; END IF;
 parent_data:=source.canonical::jsonb;
 SELECT * INTO objective FROM public.business_company_objectives WHERE (tenant_id,client_id,id,sequence)=
    (t,c,parent_data#>>'{pins,company_objective,0}',0);
 IF NOT FOUND THEN RETURN false; END IF;
 IF lock_dependencies THEN
    -- Human QA acquires these locks before taking the registry scheduler lock. Never wait in reverse order.
    IF NOT pg_try_advisory_xact_lock_shared(hashtextextended('workspace-company:'||t||':'||c,1))
       OR NOT pg_try_advisory_xact_lock_shared(hashtextextended('k22:'||t||':'||c||':'||b,22))
       OR NOT pg_try_advisory_xact_lock_shared(hashtextextended('objective:'||t||':'||c||':'||objective.subject,3))
    THEN RAISE lock_not_available; END IF;
    PERFORM 1 FROM public.deliverables WHERE id=parent.deliverable_id FOR SHARE NOWAIT;
    PERFORM 1 FROM public.tenants WHERE id=t FOR SHARE NOWAIT;
    PERFORM 1 FROM public.campaigns WHERE id=k FOR SHARE NOWAIT;
    PERFORM 1 FROM public.workforce_briefs WHERE id IN (parent.brief_id,child.id) ORDER BY id FOR SHARE NOWAIT;
 END IF;
 at_time:=clock_timestamp();
 SELECT * INTO doc FROM public.deliverables WHERE (tenant_id,campaign_id,id,status,reviewed_by)=(t,k,parent.deliverable_id,'approved',qa.actor)
   AND qa_revision=qa_approved_revision AND qa_revision::text=binding->>'revision' AND qa_approved_digest=binding->>'content_digest';
 IF NOT FOUND OR NOT EXISTS(SELECT FROM public.tenants WHERE id=t AND mode='inhouse') THEN RETURN false; END IF;
 SELECT recipient_id INTO author_id FROM public.workforce_briefs WHERE (id,tenant_id,client_id,brand_id,campaign_id,origin)=
    (parent.brief_id,t,c,b,k,'internal');
 IF NOT FOUND OR parent_data#>>'{target,brief_generation}' IS DISTINCT FROM
       coalesce((SELECT epoch::text FROM amc_acl.knowledge_target_epochs WHERE kind='brief' AND id=parent.brief_id),'0')
    OR parent_data#>>'{target,campaign_generation}' IS DISTINCT FROM
       coalesce((SELECT epoch::text FROM amc_acl.knowledge_target_epochs WHERE kind='campaign' AND id=k),'0')
 THEN RETURN false; END IF;
 IF EXISTS (SELECT FROM (VALUES ('company','company'),('brand',b)) z(kind,scope_key)
    WHERE (SELECT id FROM public.business_workspace_records p WHERE (p.tenant_id,p.client_id,p.scope,p.kind)=(t,c,z.scope_key,z.kind)
           ORDER BY p.revision DESC LIMIT 1) IS DISTINCT FROM parent_data#>>ARRAY['pins',z.kind,'0'])
    OR (SELECT state FROM public.business_company_objectives WHERE (tenant_id,client_id,revision_id)=(t,c,objective.id)
        ORDER BY sequence DESC LIMIT 1) IS DISTINCT FROM 'approved'
    OR EXISTS(SELECT FROM public.business_company_objectives WHERE (tenant_id,client_id,subject)=(t,c,objective.subject)
               AND revision>objective.revision AND state='approved') THEN RETURN false; END IF;

 -- The source manifest was authored under the human Knowledge boundary. Its dependency list is
 -- transitive, including the selected bindings, claims, approved source and qualification revisions.
 IF NOT EXISTS(SELECT FROM jsonb_each_text(parent_data#>'{pins,dependencies}')) OR EXISTS(
    SELECT FROM jsonb_each_text(parent_data#>'{pins,dependencies}') pin
    WHERE NOT amc_c3.guide_revision_current(t,c,b,pin.key,at_time)
       OR NOT EXISTS(SELECT FROM public.knowledge_revisions v WHERE
               (v.tenant_id,v.client_id,v.brand_id,v.id,v.digest)=(t,c,b,pin.key,pin.value))
 ) THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT FROM public.knowledge_revisions m WHERE (m.id,m.kind)=(decision#>>'{request,qualification_revision}','qualification')
    AND m.data->>'approver_id'=handoff.actor AND m.data->>'category'='unclassified'
    AND amc_c3.guide_revision_current(t,c,b,m.id,at_time)) THEN RETURN false; END IF;

 -- Every independent signature used in the original QA proof retains a live approver.
 approvals:=ARRAY[child.recipient_id,qa.actor,handoff.actor];
 SELECT array_agg(value) INTO review_ids FROM (
    SELECT value FROM jsonb_each_text(qa.result::jsonb->'studio_approvals')
    UNION SELECT value FROM jsonb_each_text(qa.result::jsonb->'reviewed_statements')
    UNION SELECT value FROM jsonb_each_text(qa.result::jsonb#>'{internal_research_instructions,receipts}')
 ) refs;
 FOREACH rid IN ARRAY coalesce(review_ids,ARRAY[]::text[]) LOOP
    SELECT * INTO review FROM public.knowledge_commands WHERE (tenant_id,client_id,brand_id,snapshot_id,id)=(t,c,b,source.id,rid);
    IF NOT FOUND OR review.operation NOT IN ('c3_studio_qa','c3_resolve') THEN RETURN false; END IF;
    approvals:=array_append(approvals,review.actor);
    IF review.operation='c3_resolve' AND NOT amc_c3.guide_revision_current(t,c,b,review.result->>'qualification_revision',at_time)
       THEN RETURN false; END IF;
 END LOOP;
 IF lock_dependencies THEN
   PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=ANY(array_append(approvals,author_id))
     ORDER BY user_id FOR SHARE NOWAIT;
 END IF;
 IF NOT EXISTS(SELECT FROM public.memberships WHERE (tenant_id,user_id)=(t,author_id) AND role IN ('owner','admin','editor'))
    OR EXISTS(SELECT FROM unnest(approvals) a(id) WHERE NOT EXISTS(SELECT FROM public.memberships m WHERE (m.tenant_id,m.user_id)=(t,a.id)
       AND m.role IN ('owner','admin'))) THEN RETURN false; END IF;

 -- Application registry_pin authenticates a human. Here only compare the previously signed
 -- campaign bindings, never issue new registry grants or return a private registry manifest.
 IF EXISTS(SELECT FROM (VALUES(parent.knowledge::jsonb->'registry'),(r.knowledge::jsonb->'registry')) z(pin)
    WHERE NOT EXISTS(SELECT FROM amc_ops.registry_releases rel WHERE (rel.workflow,rel.digest)=(z.pin->>'workflow',z.pin->>'manifest_digest'))
    OR (SELECT jsonb_agg(g.skill ORDER BY g.skill) FROM amc_ops.registry_grants g
        WHERE (g.tenant,g.campaign,g.workflow,g.mode)=(t,k,z.pin->>'workflow','activate')) IS DISTINCT FROM z.pin->'skills')
 THEN RETURN false; END IF;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION amc_c3.guide_authorized(public.workforce_runs,boolean) FROM PUBLIC;

-- Extend only the guide pair. Neither a guide brief on an old workflow nor an ordinary
-- internal brief on the new release may cross this insertion boundary.
CREATE OR REPLACE FUNCTION amc_acl.guard_c3_task_origin() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE task public.workforce_briefs; workflow text:=coalesce(NEW.knowledge::jsonb#>>'{registry,workflow}','');
BEGIN
 SELECT * INTO task FROM public.workforce_briefs b WHERE
  (b.id,b.tenant_id,b.client_id,b.brand_id,b.campaign_id)=(NEW.brief_id,NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id);
 IF (task.origin='internal') IS DISTINCT FROM (NEW.knowledge::jsonb @> '{"internal_task":true}') THEN
   RAISE EXCEPTION 'Task origin differs' USING ERRCODE='23514',CONSTRAINT='workforce_recipient_required';
 END IF;
 IF workflow='WF-06/product-use-guide@1' OR task.payload::jsonb ? 'guide_binding'
   OR task.payload->>'task_version'='amc.product-use-guide/1' THEN
    IF task.origin IS DISTINCT FROM 'internal' OR workflow<>'WF-06/product-use-guide@1'
      OR task.recipient_id IS DISTINCT FROM current_setting('amc.user_id',true)
      OR NOT amc_c3.guide_authorized(NEW,true) THEN
      RAISE EXCEPTION 'Guide requires a current signed commission' USING ERRCODE='23514',CONSTRAINT='workforce_recipient_required';
    END IF;
 ELSIF task.origin='internal' AND workflow NOT IN ('WF-03/research-strategy-draft@3','WF-13/landing-seo-draft@6') THEN
   RAISE EXCEPTION 'Internal task unavailable' USING ERRCODE='23514',CONSTRAINT='workforce_recipient_required';
 END IF;
 IF task.origin='internal' AND (NOT (NEW.knowledge::jsonb ? 'c3_manifest') OR
   NOT amc_acl.lock_c3_internal_target(NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.campaign_id,NEW.brief_id)) THEN
   RAISE EXCEPTION 'Internal task unavailable' USING ERRCODE='23514',CONSTRAINT='workforce_recipient_required';
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION amc_ops.candidates() RETURNS TABLE(worker name,tenant text,client text,brand text,campaign text,operator text,run text,step int)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE route record; guide public.workforce_runs;
BEGIN
 FOR route IN SELECT * FROM amc_ops.eligible_routes(NULL) LOOP
   SELECT * INTO guide FROM public.workforce_runs r WHERE r.id=route.run AND r.knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1';
   IF FOUND THEN
     BEGIN
       IF NOT amc_c3.guide_authorized(guide,true) THEN
         UPDATE public.workforce_runs r SET state='failed',last_error='guide_authority_changed' WHERE r.id=guide.id AND r.state='queued';
         CONTINUE;
       END IF;
     EXCEPTION WHEN lock_not_available THEN CONTINUE;
     END;
   END IF;
   worker:=route.worker; tenant:=route.tenant; client:=route.client; brand:=route.brand; campaign:=route.campaign;
   operator:=route.operator; run:=route.run; step:=route.step;
   RETURN NEXT;
 END LOOP;
END $$;

ALTER FUNCTION amc_ops.live(uuid) RENAME TO live_before_guide;
REVOKE ALL ON FUNCTION amc_ops.live_before_guide(uuid) FROM PUBLIC,amc_dispatch;
CREATE FUNCTION amc_ops.live(i uuid) RETURNS boolean
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE guide public.workforce_runs;
BEGIN
 IF NOT amc_ops.live_before_guide(i) THEN RETURN false; END IF;
 SELECT r.* INTO guide FROM amc_ops.attempts a JOIN public.workforce_runs r ON a.run=r.id
 WHERE a.id=i AND r.knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1';
 IF FOUND THEN RETURN amc_c3.guide_authorized(guide,false); END IF;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION amc_ops.live(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.live(uuid) TO amc_dispatch;

-- take() already verifies login, route and lease. Serialize guide disclosure with
-- the same authority locks as consumer acceptance. Busy means try the next poll.
CREATE FUNCTION amc_c3.guard_guide_collection() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE guide public.workforce_runs;
BEGIN
 SELECT * INTO guide FROM public.workforce_runs r WHERE r.id=NEW.run AND r.knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1';
 IF FOUND AND NOT amc_c3.guide_authorized(guide,true) THEN RETURN NULL; END IF;
 RETURN NEW;
EXCEPTION WHEN lock_not_available THEN RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_c3.guard_guide_collection() FROM PUBLIC;
CREATE TRIGGER c3_guide_collection BEFORE UPDATE OF status ON amc_ops.attempts FOR EACH ROW
 WHEN (OLD.status='offered' AND NEW.status='sent') EXECUTE FUNCTION amc_c3.guard_guide_collection();

ALTER FUNCTION amc_ops.fence(uuid) RENAME TO fence_before_guide;
REVOKE ALL ON FUNCTION amc_ops.fence_before_guide(uuid) FROM PUBLIC,amc_dispatch;
CREATE FUNCTION amc_ops.fence(i uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE guide public.workforce_runs;
BEGIN
 IF NOT amc_ops.fence_before_guide(i) THEN RETURN false; END IF;
 SELECT r.* INTO guide FROM amc_ops.attempts a JOIN public.workforce_runs r ON a.run=r.id
 WHERE a.id=i AND r.knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1';
 IF FOUND THEN RETURN amc_c3.guide_authorized(guide,true); END IF;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION amc_ops.fence(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.fence(uuid) TO amc_dispatch;

ALTER FUNCTION amc_ops.report(uuid,jsonb,text) RENAME TO report_before_guide;
REVOKE ALL ON FUNCTION amc_ops.report_before_guide(uuid,jsonb,text) FROM PUBLIC,amc_pool_worker;
CREATE FUNCTION amc_ops.report(i uuid,p jsonb,e text) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF amc_ops.report_before_guide(i,p,e) THEN RETURN true; END IF;
 -- If authority changed in flight, only the assigned worker may submit metering while
 -- its lease is still open. Do not retain revoked output or give it to a checkpoint.
 IF jsonb_typeof(p) IS DISTINCT FROM 'array' OR jsonb_array_length(p)<>3 OR length(p::text)>65536
    OR jsonb_typeof(p->1)<>'number' OR jsonb_typeof(p->2)<>'number' THEN RETURN false; END IF;
 UPDATE amc_ops.attempts a SET result=jsonb_build_array(NULL,p->1,p->2),error=NULL,status='reported'
 FROM public.workforce_runs r WHERE a.id=i AND a.worker=session_user AND a.status='sent' AND a.run=r.id AND a.deadline>clock_timestamp()
    AND r.knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1' AND NOT amc_c3.guide_authorized(r,false);
 RETURN FOUND;
END $$;
REVOKE ALL ON FUNCTION amc_ops.report(uuid,jsonb,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.report(uuid,jsonb,text) TO amc_pool_worker;

ALTER FUNCTION amc_ops.retire(uuid) RENAME TO retire_before_guide;
REVOKE ALL ON FUNCTION amc_ops.retire_before_guide(uuid) FROM PUBLIC,amc_dispatch;
CREATE FUNCTION amc_ops.retire(i uuid) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a amc_ops.attempts; guide public.workforce_runs;
BEGIN
 SELECT * INTO STRICT a FROM amc_ops.attempts WHERE id=i FOR UPDATE;
 SELECT * INTO guide FROM public.workforce_runs r WHERE r.id=a.run AND r.knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1' FOR UPDATE;
 IF FOUND AND a.status<>'closed' AND NOT amc_c3.guide_authorized(guide,false) THEN
   UPDATE public.workforce_runs r SET state='failed',last_error='guide_authority_changed',lease=NULL,
      reserved_microusd=r.reserved_microusd-CASE WHEN a.status='offered' THEN a.reserved ELSE 0 END,
      journal=jsonb_set(r.journal::jsonb,'{-1}',(r.journal::jsonb->-1)||jsonb_build_object(
         'outcome','guide_authority_changed','finished_at',clock_timestamp(),'usage_unconfirmed',a.status<>'offered'))::json WHERE r.id=a.run;
   RETURN 'guide_authority_changed';
 END IF;
 RETURN amc_ops.retire_before_guide(i);
END $$;
REVOKE ALL ON FUNCTION amc_ops.retire(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_ops.retire(uuid) TO amc_dispatch;

-- A reported, priced attempt remains payable even when its output is discarded.
-- finish() normally adjusts the run reservation. This path has no accepted checkpoint.
CREATE FUNCTION amc_c3.settle_revoked_guide() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 UPDATE public.workforce_runs r SET reserved_microusd=r.reserved_microusd+cost.spent-a.reserved,
    journal=jsonb_set(r.journal::jsonb,'{-1}',(r.journal::jsonb->-1)||jsonb_build_object(
      'usage_unconfirmed',false,'input_tokens',NEW.input_tokens,'output_tokens',NEW.output_tokens,'estimated_microusd',cost.spent))::json
 FROM amc_ops.attempts a JOIN amc_ops.ledger cost ON cost.id=a.id AND cost.event='usage'
 WHERE a.id=NEW.id AND r.id=a.run AND r.knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1';
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_c3.settle_revoked_guide() FROM PUBLIC;
CREATE TRIGGER c3_settle_revoked_guide AFTER UPDATE OF status ON amc_ops.attempts FOR EACH ROW
 WHEN (NEW.status='closed' AND OLD.status='reported' AND NEW.outcome='guide_authority_changed' AND NEW.input_tokens IS NOT NULL)
 EXECUTE FUNCTION amc_c3.settle_revoked_guide();

-- A previous API binary handles an unknown document as a generic draft. Preserve
-- old rows while hiding new private guide artifacts on sessions without this edition.
-- This marker provides binary compatibility; it never replaces actor authorization.
CREATE POLICY guide_reader_edition ON public.workforce_briefs AS RESTRICTIVE FOR SELECT TO amc_runtime USING (
 payload->>'task_version' IS DISTINCT FROM 'amc.product-use-guide/1' OR current_setting('amc.product_guide_protocol',true)='guide/1');
CREATE POLICY guide_reader_edition ON public.workforce_runs AS RESTRICTIVE FOR SELECT TO amc_runtime USING (
 knowledge::jsonb#>>'{registry,workflow}' IS DISTINCT FROM 'WF-06/product-use-guide@1' OR current_setting('amc.product_guide_protocol',true)='guide/1');
CREATE POLICY guide_reader_edition ON public.deliverables AS RESTRICTIVE FOR SELECT TO amc_runtime USING (
 NOT (content::jsonb ? 'product_guide') OR current_setting('amc.product_guide_protocol',true)='guide/1');
CREATE POLICY guide_reader_edition ON public.knowledge_snapshots AS RESTRICTIVE FOR SELECT TO amc_runtime USING (
 strpos(canonical,'"guide_binding":')=0 OR current_setting('amc.product_guide_protocol',true)='guide/1');

CREATE FUNCTION amc_c3.guard_guide_activation() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM 1 FROM public.tenants t JOIN public.campaigns c ON c.tenant_id=t.id
 WHERE t.id=NEW.tenant AND c.id=NEW.campaign AND t.mode='inhouse' FOR SHARE OF t,c;
 IF NOT FOUND THEN RAISE EXCEPTION 'Guide release is internal only' USING ERRCODE='23514',CONSTRAINT='guide_inhouse_activation'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_c3.guard_guide_activation() FROM PUBLIC;
CREATE TRIGGER c3_guide_activation BEFORE INSERT OR UPDATE ON amc_ops.registry_grants FOR EACH ROW
 WHEN (NEW.workflow='WF-06/product-use-guide@1' AND NEW.mode='activate') EXECUTE FUNCTION amc_c3.guard_guide_activation();

-- Some QA audit rows quote draft text. Mark them before insertion using the actual
-- producer, because a correlated SELECT on now-hidden rows would return no match for old readers.
CREATE FUNCTION amc_c3.mark_guide_audit() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT FROM public.workforce_briefs WHERE (id,tenant_id)=(NEW.subject_id,NEW.tenant_id)
           AND payload->>'task_version'='amc.product-use-guide/1')
 OR EXISTS(SELECT FROM public.workforce_runs WHERE (id,tenant_id)=(NEW.subject_id,NEW.tenant_id)
           AND knowledge::jsonb#>>'{registry,workflow}'='WF-06/product-use-guide@1')
 OR EXISTS(SELECT FROM public.deliverables WHERE (id,tenant_id)=(NEW.subject_id,NEW.tenant_id)
           AND content::jsonb ? 'product_guide') THEN
   NEW.details:=jsonb_set(coalesce(NEW.details::jsonb,'{}'),'{product_guide_edition}','"guide/1"')::json;
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_c3.mark_guide_audit() FROM PUBLIC;
CREATE TRIGGER c3_guide_audit BEFORE INSERT ON public.audit_events FOR EACH ROW EXECUTE FUNCTION amc_c3.mark_guide_audit();
CREATE POLICY guide_reader_edition ON public.audit_events AS RESTRICTIVE FOR SELECT TO amc_runtime USING (
 details->>'product_guide_edition' IS DISTINCT FROM 'guide/1' OR current_setting('amc.product_guide_protocol',true)='guide/1');
