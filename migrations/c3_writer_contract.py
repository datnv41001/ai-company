"""Check the effective delivery protocol, including the three enabled statement triggers."""

WRITER_FENCE = """
SELECT count(*) = 3 AND EXISTS (
    SELECT FROM pg_catalog.pg_trigger WHERE tgname='c3_reviewer_receipt'
      AND tgrelid='public.knowledge_commands'::regclass AND tgtype=5 AND tgenabled IN ('O','A')
      AND tgfoid=to_regprocedure('amc_acl.require_reviewer_writer()')
) FROM pg_catalog.pg_trigger
 WHERE tgname='c3_writer_protocol' AND tgenabled IN ('O','A') AND tgtype=30
   AND tgfoid=to_regprocedure('amc_acl.require_reviewer_writer()')
   AND has_function_privilege('amc_runtime', to_regprocedure('amc_acl.lock_c3_reviewer(text,text)'), 'EXECUTE')
   AND tgrelid IN ('public.deliverables'::regclass,'public.client_reviews'::regclass,'public.review_entries'::regclass)
"""
