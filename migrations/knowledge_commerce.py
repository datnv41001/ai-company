"""One conflict predicate for SQLite evaluation and PostgreSQL's scoped boolean function."""

TABLES = ("knowledge_revisions", "knowledge_links", "knowledge_events")


def conflict_query(postgres):
    prefix = "public." if postgres else ""
    rev, link, events = (prefix + name for name in TABLES)

    def param(name):
        return f"p_{name}" if postgres else f":{name}"

    def clock(value):
        return f"CAST({value} AS timestamptz)" if postgres else f"amc_commerce_instant({value})"

    when = clock(param("at"))
    facet = param("facet")
    equal = "IS NOT DISTINCT FROM" if postgres else "IS"

    def prop(row, field):
        return f"({row}.data->'applicability'->>'{field}')"

    def overlap(field):
        a, b = prop("a", field), prop("b", field)
        return f"({a} IS NULL OR {b} IS NULL OR {a}={b})"

    def range_meets(first, second):
        a, b = prop(first, "minimum"), prop(second, "maximum")
        return f"({a} IS NULL OR {b} IS NULL OR CAST({a} AS NUMERIC)<=CAST({b} AS NUMERIC))"

    location = " AND ".join(
        f"(a.data->'placement'->>'{k}') {equal} (b.data->'placement'->>'{k}')" for k in ("product", "market", "variant", "channel", "locale", "region")
    )

    def meaning(row):
        # Only declared equivalent spellings collapse. Other prose needs an explicit decision.
        value = f"({row}.data->>{facet})"
        vn_months = f"{value} ~ '^[1-9][0-9]? tháng$'" if postgres else f"({value} GLOB '[1-9] tháng' OR {value} GLOB '[1-9][0-9] tháng')"
        return f"""CASE WHEN {facet}='payment' AND {value} IN ('Prepaid','Trả trước') THEN 'Prepaid'
          WHEN {facet}='payment' AND {value} IN ('Cash on delivery','Thanh toán khi nhận hàng') THEN 'Cash on delivery'
          WHEN {facet}='warranty' AND {vn_months}
             THEN replace({value},' tháng',' months')
          ELSE {value} END"""

    can_read = "AND amc_acl.knowledge_read(r.tenant_id,r.visibility) AND p_at BETWEEN transaction_timestamp() AND clock_timestamp()" if postgres else ""
    # Frozen SQL fragments only. All application inputs are SQL parameters.
    return f"""WITH target AS (
       SELECT r.* FROM {rev} r WHERE (r.tenant_id,r.client_id,r.brand_id,r.id)=
         ({param("tenant")},{param("client")},{param("brand")},{param("revision")}) {can_read}
         AND ((r.kind='availability' AND {facet}='status') OR (r.kind='policy' AND {facet} IN ('warranty','payment')))
    )
    SELECT (NOT EXISTS(SELECT 1 FROM target)) OR EXISTS (
      SELECT 1 FROM target a
      JOIN {link} l ON (l.tenant_id,l.client_id,l.brand_id)=(a.tenant_id,a.client_id,a.brand_id)
        AND l.relation='product' AND l.target_id=(a.data->'placement'->>'product')
      JOIN {rev} b ON b.id=l.revision_id AND b.kind=a.kind AND b.id<>a.id
      WHERE {location} AND {overlap("option")} AND {overlap("unit")}
        AND {range_meets("a", "b")} AND {range_meets("b", "a")}
        AND b.data->>{facet} IS NOT NULL AND b.data->>{facet}<>'unknown'
        AND {meaning("a")}<>{meaning("b")}
        AND (b.data->>'valid_from' IS NULL OR {clock("(b.data->>'valid_from')")}<={when})
        AND (b.data->>'valid_until' IS NULL OR {when}<{clock("(b.data->>'valid_until')")})
        AND (b.kind<>'availability' OR {clock("(b.data->>'observed_at')")}<={when})
        AND (SELECT e.state FROM {events} e WHERE e.revision_id=b.id ORDER BY e.sequence DESC LIMIT 1) IN ('approved','disputed')
        AND EXISTS(SELECT 1 FROM {events} e WHERE e.revision_id=b.id AND e.state='approved')
    )"""


def install(conn):
    # The function sees restricted competing facts. Callers receive only a
    # boolean about a revision they can already read in this signed scope.
    for table in TABLES:
        conn.execute(f"DROP POLICY IF EXISTS knowledge_commerce_publisher ON public.{table}")
        conn.execute(f"CREATE POLICY knowledge_commerce_publisher ON public.{table} FOR SELECT TO CURRENT_USER USING(true)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_commerce_product ON public.knowledge_links(tenant_id,client_id,brand_id,target_id,revision_id) WHERE relation='product'"
    )
    signature = "amc_acl.knowledge_commercial_conflict(text,text,text,text,text,timestamptz)"
    conn.execute(
        "CREATE OR REPLACE FUNCTION amc_acl.knowledge_commercial_conflict(p_tenant text,p_client text,p_brand text,p_revision text,p_facet text,p_at timestamptz)"
        + " RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $rule$ "
        + conflict_query(True)
        + " $rule$"
    )
    conn.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    conn.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO amc_runtime")
