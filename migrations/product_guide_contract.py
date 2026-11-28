"""The guide release requires its private pool checks and old-reader policies on existing tables."""

GUIDE_FENCE = """
SELECT
  (SELECT count(*)=5 FROM pg_catalog.pg_policy p
    WHERE polname='guide_reader_edition' AND NOT polpermissive AND polcmd='r'
      AND polrelid IN ('public.workforce_briefs'::regclass,'public.workforce_runs'::regclass,
                       'public.deliverables'::regclass,'public.knowledge_snapshots'::regclass,'public.audit_events'::regclass)
      AND strpos(pg_get_expr(polqual,polrelid),'amc.product_guide_protocol')>0)
  AND (SELECT count(*)=4 FROM pg_catalog.pg_trigger t
    JOIN pg_catalog.pg_proc f ON f.oid=t.tgfoid
    JOIN pg_catalog.pg_namespace n ON n.oid=f.pronamespace
    JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
    JOIN pg_catalog.pg_namespace table_ns ON table_ns.oid=c.relnamespace
    WHERE n.nspname='amc_c3' AND (table_ns.nspname,c.relname,tgname,proname) IN (
        ('amc_ops','attempts','c3_guide_collection','guard_guide_collection'),
        ('amc_ops','attempts','c3_settle_revoked_guide','settle_revoked_guide'),
        ('amc_ops','registry_grants','c3_guide_activation','guard_guide_activation'),
        ('public','audit_events','c3_guide_audit','mark_guide_audit'))
      AND tgenabled IN ('O','A'))
  AND (SELECT count(*)=6 FROM pg_catalog.pg_proc f JOIN pg_catalog.pg_namespace n ON n.oid=f.pronamespace
    WHERE n.nspname='amc_c3' AND f.proname IN ('guide_authorized','guide_revision_current','guard_guide_collection','settle_revoked_guide','guard_guide_activation','mark_guide_audit')
      AND NOT has_function_privilege('amc_runtime',f.oid,'execute')
      AND NOT has_function_privilege('amc_dispatch',f.oid,'execute')
      AND NOT has_function_privilege('amc_pool_worker',f.oid,'execute'))
  AND (SELECT count(*)=6 FROM pg_catalog.pg_proc f JOIN pg_catalog.pg_namespace n ON n.oid=f.pronamespace
    WHERE ((n.nspname='amc_acl' AND f.proname='guard_c3_task_origin')
           OR (n.nspname='amc_ops' AND f.proname IN ('candidates','live','report','fence','retire')))
      AND f.prosecdef AND strpos(f.prosrc,'amc_c3.guide_authorized')>0)
"""
