"""Runtime and publisher both require the enabled campaign journal fence."""
SANDBOX_FENCE = """
SELECT EXISTS(SELECT FROM pg_catalog.pg_trigger WHERE tgrelid='public.knowledge_commands'::regclass
    AND tgname='campaign_sandbox_writer' AND tgtype=7 AND tgenabled IN ('O','A')
    AND tgfoid=to_regprocedure('amc_acl.require_sandbox_writer()'))
"""

ROLE_DESK = """
SELECT coalesce(has_function_privilege('amc_runtime',to_regprocedure('amc_acl.campaign_desk(text,text)'),'EXECUTE'),false)
 AND to_regclass('amc_acl.campaign_member_epochs') IS NOT NULL
 AND EXISTS(SELECT FROM pg_trigger WHERE tgrelid='public.memberships'::regclass AND tgname='campaign_membership_changed'
     AND tgenabled IN ('A','O') AND tgfoid=to_regprocedure('amc_acl.advance_campaign_membership()'))
 AND EXISTS(SELECT FROM pg_trigger WHERE tgrelid='public.knowledge_commands'::regclass AND tgname='campaign_rfq_intake'
     AND tgenabled IN ('A','O') AND tgfoid=to_regprocedure('amc_acl.approved_rfq_intake()'))
"""
