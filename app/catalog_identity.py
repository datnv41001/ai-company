"""Exact master identity, shared by lower-level C1 writes and the operator's catalog."""

from sqlalchemy import text

from .knowledge_store import conflict, signed_document


MASTERS = ("product", "variant", "service", "market")


def master_subject(kind, code):
    return ("cm-market-" if kind == "market" else "cm-sku-") + code


def check_master(store, kind, subject, data, prior):
    if kind not in MASTERS:
        return
    code = data.get("catalog_code")
    if (code and subject != master_subject(kind, code)) or (subject.startswith(("cm-market-", "cm-sku-")) and not code):
        conflict("Catalog code and stable master subject must stay together")
    if prior and prior.data.get("catalog_code") != code:
        conflict("An existing master identity is immutable")
    if code and kind != "market" and (data.get("sku") or "").upper() != code:
        conflict("Catalog SKU differs from the explicit master code")
    params = {
        **store.scope,
        "kind": kind,
        "subject": subject,
        "label": data.get("name", "").strip(),
        "code": code or (data.get("sku") or "").upper(),
        "guided": bool(code),
    }
    if store.postgres:
        params = signed_document(store.db, store.actor, "catalog-identity", params)
        query = "SELECT amc_business.check_catalog(:doc,:proof)"
    else:
        query = "SELECT EXISTS(SELECT 1 FROM knowledge_revisions r WHERE " + MASTER_CONFLICT + ")"
    if store.db.scalar(text(query), params):
        conflict("Master identity already reserved or unresolved; reconcile the existing record")


# Only declarations carrying the same explicit SKU/code, or an exact market label, can reserve a code.
# Historical reservations survive withdrawal. Old unregistered C1 records remain readable as unmapped.
MASTER_CONFLICT = """
 (r.tenant_id,r.client_id,r.brand_id)=(:tenant_id,:client_id,:brand_id) AND r.subject<>:subject
 AND (:guided OR r.data->>'catalog_code' IS NOT NULL)
 AND ((:kind='market' AND r.kind='market' AND
    ((:code<>'' AND upper(r.data->>'catalog_code')=:code) OR lower(trim(r.data->>'name'))=lower(:label)))
 OR (:kind<>'market' AND r.kind IN ('service','product','variant') AND :code<>'' AND upper(trim(r.data->>'sku'))=:code))
"""
