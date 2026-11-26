-- Additive capability on the compatible two-namespace journal. Signed requests bind actor,
-- exact scope, payload and transaction. Only this desk may settle assigned business cases.
CREATE TABLE amc_acl.campaign_member_epochs (tenant_id text NOT NULL,user_id text NOT NULL,epoch bigint NOT NULL,
  PRIMARY KEY(tenant_id,user_id));
REVOKE ALL ON amc_acl.campaign_member_epochs FROM PUBLIC,amc_runtime;
CREATE FUNCTION amc_acl.advance_campaign_membership() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='UPDATE' AND (OLD.role,OLD.client_id) IS NOT DISTINCT FROM (NEW.role,NEW.client_id) THEN RETURN NULL; END IF;
 INSERT INTO amc_acl.campaign_member_epochs VALUES (OLD.tenant_id,OLD.user_id,1)
 ON CONFLICT (tenant_id,user_id) DO UPDATE SET epoch=amc_acl.campaign_member_epochs.epoch+1;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION amc_acl.advance_campaign_membership() FROM PUBLIC;
CREATE TRIGGER campaign_membership_changed AFTER DELETE OR UPDATE OF role,client_id ON public.memberships
 FOR EACH ROW EXECUTE FUNCTION amc_acl.advance_campaign_membership();

CREATE FUNCTION amc_acl.campaign_desk(doc text, proof text) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
 q jsonb := doc::jsonb; t text:=q->>'tenant_id'; c text:=q->>'client_id'; b text:=q->>'brand_id'; cid text:=q->>'campaign_id';
 u text:=current_setting('amc.user_id',true); r text:=q->>'role'; subject text:=q->>'subject'; op text:=q->>'mode';
 items jsonb; notes jsonb; replay jsonb; v jsonb; prior jsonb; seq integer; eligible boolean; allowed boolean; event jsonb;
BEGIN
 IF amc_acl.valid_knowledge_append('campaign_role_desk',doc,proof) IS NOT TRUE
 OR amc_acl.knowledge_read(t,'internal') IS NOT TRUE OR q->>'actor' IS DISTINCT FROM u
 OR r NOT IN ('marketing_operator','business_owner','service_assignee','sales_recipient','reviewer')
 OR current_setting('transaction_isolation') <> 'read committed'
 OR NOT EXISTS(SELECT FROM public.campaigns p JOIN public.brands x ON x.id=p.brand_id AND x.tenant_id=t
   WHERE p.tenant_id=t AND p.id=cid AND x.id=b AND x.client_id=c)
 THEN RAISE insufficient_privilege; END IF;
 -- Same brand lock as existing plan, grant and sandbox writes. Recheck user membership after acquiring.
 PERFORM pg_advisory_xact_lock(hashtextextended('k22:'||t||':'||c||':'||b,22));
 PERFORM 1 FROM public.memberships WHERE tenant_id=t AND user_id=u AND role IN ('owner','admin','editor','viewer') FOR SHARE;
 IF NOT FOUND THEN RAISE insufficient_privilege; END IF;
 IF op IN ('eligible','grant_epoch') THEN
   IF NOT EXISTS(SELECT FROM public.memberships WHERE tenant_id=t AND user_id=subject AND role IN ('owner','admin','editor','viewer') FOR SHARE)
     THEN RETURN 'false'::jsonb; END IF;
 ELSE subject:=u; END IF;
 IF op='grant_epoch' THEN
   IF amc_acl.knowledge_read(t,'restricted') IS NOT TRUE THEN RAISE insufficient_privilege; END IF;
   RETURN to_jsonb(coalesce((SELECT epoch FROM amc_acl.campaign_member_epochs WHERE tenant_id=t AND user_id=subject),0));
 END IF;
 SELECT (k.result->>'enabled')::boolean AND (k.result->>'membership_epoch')::bigint =
    coalesce((SELECT epoch FROM amc_acl.campaign_member_epochs WHERE tenant_id=t AND user_id=subject),0)
 INTO eligible FROM public.knowledge_commands k
 WHERE (k.tenant_id,k.client_id,k.brand_id)=(t,c,b) AND k.operation='campaign_role_grant' AND k.visibility='restricted'
 AND k.result->>'campaign_id'=cid AND k.result->>'subject'=subject AND k.result->>'role'=r
 ORDER BY (k.result->>'revision')::integer DESC LIMIT 1;
 IF op='eligible' THEN RETURN to_jsonb(coalesce(eligible,false)); END IF;
 IF eligible IS NOT TRUE THEN RETURN NULL; END IF;
 WITH newest AS (
  SELECT DISTINCT ON (k.result->>'entity', k.result->>'entity_id') k.result::jsonb AS e FROM public.knowledge_commands k
  WHERE (k.tenant_id,k.client_id,k.brand_id)=(t,c,b) AND k.visibility='restricted'
    AND k.operation IN ('campaign_sandbox_v1','campaign_sandbox_v2') AND k.result->>'campaign_id'=cid
    AND k.result->>'entity' IN ('appointments','leads')
  ORDER BY k.result->>'entity',k.result->>'entity_id',(k.result->>'sequence')::integer DESC
 ), visible AS (
  SELECT e->>'entity' AS entity,e->>'entity_id' AS id,CASE WHEN r='reviewer' THEN jsonb_build_object(
    'id', e->'entity_id','plan_id', e->'plan_id','state',e->'value'->'state','revision',e->'value'->'revision')
    ELSE e->'value' END AS value FROM newest
  WHERE r IN ('marketing_operator','business_owner','reviewer') OR (e->'value'->>'assignee_id'=u AND
     (r='sales_recipient' AND e->>'entity'='leads' OR r='service_assignee' AND e->>'entity'='appointments'))
 ) SELECT coalesce(jsonb_agg(jsonb_build_object('entity',entity,'value',value) ORDER BY entity,id),'[]'::jsonb) INTO items FROM visible;
 SELECT coalesce(max((k.result->>'sequence')::int),0)+1 INTO seq FROM public.knowledge_commands k
 WHERE (k.tenant_id,k.client_id,k.brand_id)=(t,c,b) AND k.operation IN ('campaign_sandbox_v1','campaign_sandbox_v2') AND k.result->>'campaign_id'=cid;
 SELECT jsonb_build_object('digest',k.request_digest,'result',k.result) INTO replay FROM public.knowledge_commands k
 WHERE (k.tenant_id,k.client_id,k.brand_id,k.actor,k.key)=(t,c,b,u,q->>'key')
 AND k.operation IN ('campaign_sandbox_v2','campaign_desk_feedback') AND k.result->>'campaign_id'=cid;
 IF op='inspect' THEN
   SELECT coalesce(jsonb_agg(k.result ORDER BY k.effective_at,k.id),'[]'::jsonb) INTO notes FROM public.knowledge_commands k
   WHERE (k.tenant_id,k.client_id,k.brand_id)=(t,c,b) AND k.operation='campaign_desk_feedback' AND k.result->>'campaign_id'=cid
   AND EXISTS(SELECT FROM jsonb_array_elements(items) x WHERE x->>'entity'=k.result->>'entity'
              AND x->'value'->>'id'=k.result->>'entity_id');
   RETURN jsonb_build_object('items',items,'feedback',notes,'sequence',seq,'replay',replay);
 END IF;
 v=q->'row'; event=v->'result';
 SELECT x->'value' INTO prior FROM jsonb_array_elements(items) x
 WHERE x->>'entity'=event->>'entity' AND x->'value'->>'id'=event->>'entity_id';
 allowed:=CASE WHEN v->>'operation'='campaign_desk_feedback' THEN r IN ('reviewer','business_owner')
   WHEN v->>'operation'='campaign_sandbox_v2' AND event->>'entity'='leads' AND event->>'kind'='sales'
     THEN (r IN ('marketing_operator','business_owner') AND event->>'step' IN ('assign','reassign','cancel')
        OR r='sales_recipient' AND event->>'step' IN ('accept','reject','quote','order'))
   WHEN v->>'operation'='campaign_sandbox_v2' AND event->>'entity'='appointments' AND event->>'kind'='appointment_decision'
     THEN (r IN ('marketing_operator','business_owner') AND event->>'step' IN ('assign','confirm','cancel','reschedule','reassign')
        OR r='service_assignee' AND event->>'step' IN ('complete','no_show','cancel')) ELSE false END;
 IF op IS DISTINCT FROM 'append' OR allowed IS NOT TRUE OR prior IS NULL OR replay IS NOT NULL
 OR prior->>'plan_id' IS DISTINCT FROM event->>'plan_id' OR (prior->>'revision')::integer IS DISTINCT FROM (q->>'prior_revision')::integer
 OR (v->>'tenant_id',v->>'client_id',v->>'brand_id',v->>'actor',v->>'visibility',v->>'key') IS DISTINCT FROM (t,c,b,u,'restricted'::text,q->>'key')
 OR (event->>'campaign_id',event->>'actor',event->>'id',event->>'desk_role') IS DISTINCT FROM (cid,u,v->>'id',r)
 OR (v->>'operation'='campaign_sandbox_v2' AND ((event->>'sequence')::integer IS DISTINCT FROM seq
    OR event->'value'->>'id' IS DISTINCT FROM prior->>'id' OR (event->'value'->>'revision')::integer IS DISTINCT FROM (prior->>'revision')::integer+1))
 THEN RAISE insufficient_privilege; END IF;
 INSERT INTO public.knowledge_commands SELECT * FROM jsonb_populate_record(NULL::public.knowledge_commands,v);
 RETURN event;
END $$;
REVOKE ALL ON FUNCTION amc_acl.campaign_desk(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION amc_acl.campaign_desk(text,text) TO amc_runtime;

-- A compatible predecessor can still boot on core 26. Enforce optional quote intake
-- on append so an older process cannot override the campaign owner's approved journey.
CREATE FUNCTION amc_acl.approved_rfq_intake() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM public.knowledge_commands p JOIN public.knowledge_commands a
      ON (a.tenant_id,a.client_id,a.brand_id,a.result->>'id',a.result->>'digest')=
         (p.tenant_id,p.client_id,p.brand_id,p.result->>'id',p.result->>'digest')
      WHERE p.operation='campaign_plan' AND a.operation='campaign_plan_approve'
      AND (p.tenant_id,p.client_id,p.brand_id,p.result->>'id',p.result->>'campaign_id')=
          (NEW.tenant_id,NEW.client_id,NEW.brand_id,NEW.result->>'plan_id',NEW.result->>'campaign_id')
      AND (p.result->>'buyer_action'='rfq' OR p.result->>'buyer_action'='appointment' AND
           coalesce(p.result::jsonb->'secondary_conversions','[]'::jsonb) @> '["rfq"]'::jsonb))
 THEN RAISE EXCEPTION 'Campaign plan does not authorize quote intake' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION amc_acl.approved_rfq_intake() FROM PUBLIC;
CREATE TRIGGER campaign_rfq_intake BEFORE INSERT ON public.knowledge_commands
 FOR EACH ROW WHEN (NEW.operation='campaign_sandbox_v2' AND NEW.result->>'kind'='rfq')
 EXECUTE FUNCTION amc_acl.approved_rfq_intake();
