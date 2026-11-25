"""A signed-scope yes/no read of private authority. No evidence rows leave the database."""

from hashlib import sha256


def rule(postgres):
    table = "public." if postgres else ""
    v = (lambda k: "p_" + k) if postgres else (lambda k: ":" + k)
    scoped = " AND ".join(f"{name}={v(key)}" for name, key in (("tenant_id", "tenant"), ("client_id", "client"), ("brand_id", "brand")))
    signed = f" AND amc_acl.knowledge_read({v('tenant')},'public')" if postgres else ""
    clock = (lambda x: f"CAST({x} AS timestamptz)") if postgres else (lambda x: f"amc_claim_instant({x})")
    at = "statement_timestamp()" if postgres else ":at"
    now = at if postgres else clock(at)
    revs, links, events = (table + "knowledge_" + name for name in ("revisions", "links", "events"))
    # Qualification is a private dependency of the approval event. C1 source
    # sheets can cover several SKUs, so only a binding's selected entry contributes its SKU links.
    return f"""WITH RECURSIVE
    root AS (SELECT id, author FROM {revs} WHERE {scoped} AND kind='claim' AND visibility='public' AND id={v("claim")}{signed}),
    decision AS (SELECT actor,qualification_id FROM {events} WHERE {scoped}
                 AND revision_id=(SELECT id FROM root) ORDER BY sequence DESC LIMIT 1),
    edges(parent,child) AS NOT MATERIALIZED (
       SELECT l.revision_id,l.target_id FROM {links} l JOIN {revs} r ON r.id=l.revision_id
       WHERE r.kind<>'source' AND {" AND ".join("l." + p for p in scoped.split(" AND "))}
       UNION ALL SELECT root.id,decision.qualification_id FROM root,decision WHERE qualification_id IS NOT NULL),
    reachable(id) AS (
       SELECT id FROM root UNION SELECT edges.child FROM reachable JOIN edges ON edges.parent=reachable.id),
    bounded AS MATERIALIZED (SELECT id FROM reachable LIMIT 193)
    SELECT EXISTS(SELECT 1 FROM root) AND (SELECT count(*) FROM bounded)<=192
    AND ({v("category")} IS NULL OR EXISTS(
       SELECT 1 FROM decision d JOIN {revs} q ON q.id=d.qualification_id JOIN root ON 1=1
       WHERE q.kind='qualification' AND q.data->>'category'={v("category")}
       AND q.data->>'approver_id'=d.actor AND d.actor<>root.author))
    AND NOT EXISTS (
       SELECT 1 FROM bounded b LEFT JOIN {revs} r ON r.id=b.id WHERE r.id IS NULL
       OR COALESCE((SELECT e.state FROM {events} e WHERE e.revision_id=r.id ORDER BY e.sequence DESC LIMIT 1),'draft')<>'approved'
       OR {clock("(r.data->>'valid_from')")}>{now}
       OR {clock("(r.data->>'valid_until')")}<={now}
       OR (r.kind='availability' AND {clock("(r.data->>'observed_at')")}>{now}))"""


SIGNATURE = "amc_business.claim_display_current(text,text,text,text,text)"
DIGEST = sha256(rule(True).encode()).hexdigest()
CURRENT = f"SELECT obj_description(to_regprocedure('{SIGNATURE}'),'pg_proc') IS NOT DISTINCT FROM '{DIGEST}'"


def install(conn):
    if conn.execute(CURRENT).fetchone()[0]:
        return
    conn.execute(
        "CREATE OR REPLACE FUNCTION amc_business.claim_display_current(p_tenant text,p_client text,p_brand text,p_claim text,p_category text) "
        "RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $predicate$ " + rule(True) + " $predicate$"
    )
    conn.execute(f"REVOKE ALL ON FUNCTION {SIGNATURE} FROM PUBLIC")
    conn.execute(f"GRANT EXECUTE ON FUNCTION {SIGNATURE} TO amc_runtime")
    conn.execute(f"COMMENT ON FUNCTION {SIGNATURE} IS '{DIGEST}'")
