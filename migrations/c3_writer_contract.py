"""Check the effective delivery protocol, including the three enabled statement triggers."""

WRITER_FENCE = """
SELECT count(*) = 3 FROM pg_catalog.pg_trigger
 WHERE tgname='c3_writer_protocol' AND tgenabled IN ('O','A') AND tgtype=30
   AND tgfoid=to_regprocedure('amc_acl.require_c3_writer()')
   AND tgrelid IN ('public.deliverables'::regclass,'public.client_reviews'::regclass,'public.review_entries'::regclass)
"""
