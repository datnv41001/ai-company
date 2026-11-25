"""Module migration 002 uses the same bounded predicate on both database engines."""

import re

from app.catalog_identity import MASTER_CONFLICT


def install_catalog(conn):
    sql = re.sub(r":(tenant_id|client_id|brand_id|kind|subject|label|code|guided)\b", r"p_\1", MASTER_CONFLICT)
    signature = "amc_business.catalog_conflict(text,text,text,text,text,text,text,boolean)"
    conn.execute(
        """CREATE FUNCTION amc_business.catalog_conflict(p_tenant_id text,p_client_id text,p_brand_id text,
      p_kind text,p_subject text,p_label text,p_code text,p_guided boolean) RETURNS boolean
      LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $rule$
      SELECT amc_acl.knowledge_read(p_tenant_id,'internal') IS NOT TRUE
      OR EXISTS (SELECT 1 FROM public.knowledge_revisions r WHERE """
        + sql
        + ") $rule$"
    )
    conn.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    # A direct caller cannot enumerate sensitive SKU labels by querying this helper.
    # The app passes the checked request through the signed brand-write function below.
    conn.execute(f"REVOKE ALL ON FUNCTION {signature} FROM amc_runtime")
    conn.execute("""CREATE FUNCTION amc_business.check_catalog(doc text,proof text) RETURNS boolean
      LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
      DECLARE v jsonb:=doc::jsonb;
      BEGIN
       IF amc_acl.valid_knowledge_append('catalog-identity',doc,proof) IS NOT TRUE THEN RAISE insufficient_privilege; END IF;
       PERFORM amc_acl.lock_knowledge(v->>'tenant_id',v->>'client_id',v->>'brand_id');
       RETURN amc_business.catalog_conflict(v->>'tenant_id',v->>'client_id',v->>'brand_id',v->>'kind',
              v->>'subject',v->>'label',v->>'code',(v->>'guided')::boolean);
      END $$""")
    conn.execute("REVOKE ALL ON FUNCTION amc_business.check_catalog(text,text) FROM PUBLIC")
    conn.execute("GRANT EXECUTE ON FUNCTION amc_business.check_catalog(text,text) TO amc_runtime")
    conn.execute("INSERT INTO amc_business.versions VALUES(2)")
