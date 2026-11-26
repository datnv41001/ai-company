"""Runtime and publisher both require the enabled campaign journal fence."""
SANDBOX_FENCE = """
SELECT EXISTS(SELECT FROM pg_catalog.pg_trigger WHERE tgrelid='public.knowledge_commands'::regclass
    AND tgname='campaign_sandbox_writer' AND tgtype=7 AND tgenabled IN ('O','A')
    AND tgfoid=to_regprocedure('amc_acl.require_sandbox_writer()'))
"""

BUSINESS_INTAKE = """
SELECT EXISTS(SELECT FROM pg_catalog.pg_trigger WHERE tgrelid='public.knowledge_commands'::regclass
    AND tgname='business_intake_writer' AND tgtype=7 AND tgenabled IN ('O','A')
    AND tgfoid=to_regprocedure('amc_acl.check_business_intake()'))
"""


def sqlite_business_intake(connection):
    connection.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS business_intake_writer BEFORE INSERT ON knowledge_commands
      WHEN (NEW.operation IN ('studio_production','studio_landing_v2') AND json_extract(NEW.result,'$.kind')='landing')
        OR (NEW.operation='campaign_sandbox_v2' AND json_extract(NEW.result,'$.entity') IN ('sessions','appointments','leads'))
      BEGIN
        SELECT CASE WHEN NEW.operation IN ('studio_production','studio_landing_v2') AND NOT EXISTS(
          SELECT 1 FROM knowledge_commands p WHERE p.operation='campaign_plan'
          AND (p.tenant_id,p.client_id,p.brand_id,json_extract(p.result,'$.id')) =
              (NEW.tenant_id,NEW.client_id,NEW.brand_id,json_extract(NEW.result,'$.plan_id'))
          AND json_extract(p.result,'$.intake_contract') IS json_extract(NEW.result,'$.master.intake_contract')
          AND (NEW.operation='studio_landing_v2') = (json_extract(p.result,'$.intake_contract') IS NOT NULL))
        THEN RAISE(ABORT, 'Reload the approved business intake with a compatible landing writer') END;
        SELECT CASE WHEN NEW.operation='campaign_sandbox_v2' AND json_extract(NEW.result,'$.intake_writer') IS NOT 'business-intake/1'
          AND EXISTS(SELECT 1 FROM knowledge_commands p WHERE p.operation='campaign_plan'
          AND (p.tenant_id,p.client_id,p.brand_id,json_extract(p.result,'$.id')) =
              (NEW.tenant_id,NEW.client_id,NEW.brand_id,json_extract(NEW.result,'$.plan_id'))
          AND json_extract(p.result,'$.intake_contract') IS NOT NULL)
        THEN RAISE(ABORT, 'Use a compatible writer for the approved business intake') END;
      END""")


ROLE_DESK = """
SELECT coalesce(has_function_privilege('amc_runtime',to_regprocedure('amc_acl.campaign_desk(text,text)'),'EXECUTE'),false)
 AND obj_description(to_regprocedure('amc_acl.campaign_desk(text,text)'), 'pg_proc')='campaign-role-desk/2'
 AND to_regclass('amc_acl.campaign_member_epochs') IS NOT NULL
 AND EXISTS(SELECT FROM pg_trigger WHERE tgrelid='public.memberships'::regclass AND tgname='campaign_membership_changed'
     AND tgenabled IN ('A','O') AND tgfoid=to_regprocedure('amc_acl.advance_campaign_membership()'))
 AND EXISTS(SELECT FROM pg_trigger WHERE tgrelid='public.knowledge_commands'::regclass AND tgname='campaign_rfq_intake'
     AND tgenabled IN ('A','O') AND tgfoid=to_regprocedure('amc_acl.approved_rfq_intake()'))
"""
