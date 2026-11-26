"""Runtime and publisher both require the enabled campaign journal fence."""
SANDBOX_FENCE = """
SELECT EXISTS(SELECT FROM pg_catalog.pg_trigger WHERE tgrelid='public.knowledge_commands'::regclass
    AND tgname='campaign_sandbox_writer' AND tgtype=7 AND tgenabled IN ('O','A')
    AND tgfoid=to_regprocedure('amc_acl.require_sandbox_writer()'))
"""
