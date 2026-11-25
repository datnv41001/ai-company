"""Human-facing catalog over C1 append-only revisions, authority events and command receipts."""

import re
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import func, or_

from .business_knowledge import reader, writer
from .catalog_identity import MASTERS, master_subject
from .company_objectives import check_company_reference, current_state, latest_decision
from .commercial_scope import CONDITION_LABELS, CONDITION_BY_LABEL, TERRITORIES
from .knowledge_authority import new_revision, invalid
from .knowledge_contracts import Code, Command, RevisionIn, Subject, Visibility
from .knowledge_models import KnowledgeCommand, KnowledgeRevision as Row
from .knowledge_store import missing
from .models import Campaign, new_id

CatalogKind = Literal["product", "service", "variant", "market", "policy", "availability", "offer", "guidelines", "segment", "icp", "objective", "kpi"]
LookupKind = Literal["product", "service", "variant", "market", "policy", "availability", "source", "objective", "kpi", "offer", "guidelines", "segment", "icp"]
router = APIRouter(prefix="/api/tenants/{tenant_id}/clients/{client_id}/brands/{brand_id}/catalog", tags=["marketing catalog"])
REFS = {"product", "variant", "market", "policy", "availability", "source", "parent", "objective"}


class CatalogSave(Command):
    kind: CatalogKind
    code: Code | None = None
    subject: Subject | None = None
    expected_revision: Annotated[int, Field(ge=0, strict=True)]
    visibility: Visibility = "internal"
    data: dict


def display_money(value, currency):
    decimals = 0 if currency in ("VND", "JPY") else 2
    return format(Decimal(value).scaleb(-decimals), f".{decimals}f")


def normalize_offer(data):
    price = data.get("price")
    if price is None:
        return data
    if not isinstance(price, dict):
        invalid("Price must have named fields")
    price = price.copy()
    amount = price.pop("amount", None)
    if "amount_minor" in price or not isinstance(amount, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?", amount):
        invalid("Enter a decimal amount without currency symbols or thousands separators")
    currency = price.get("currency")
    if not isinstance(currency, str):
        invalid("Choose a currency")
    minor = Decimal(amount).scaleb(0 if currency in ("VND", "JPY") else 2)
    if minor != minor.to_integral_value():
        invalid("Amount cannot be expressed exactly in this currency")
    ids = price.pop("condition_ids", [])
    if "conditions" in price or not isinstance(ids, list) or not all(isinstance(k, str) and k in CONDITION_LABELS for k in ids):
        invalid("Choose registered commercial conditions")
    return data | {"price": price | {"amount_minor": int(minor), "conditions": [CONDITION_LABELS[k][0] for k in ids]}}


@router.post("/items", status_code=201)
def save(body: CatalogSave, s=Depends(writer)):
    def record(at):
        data = body.data.copy()
        if body.kind in MASTERS:
            if not body.code:
                invalid("Supply an explicit SKU or market code")
            subject = master_subject(body.kind, body.code)
            if body.subject and body.subject != subject:
                invalid("A catalog master keeps its original code")
            data["catalog_code"] = body.code
            if body.kind != "market":
                data.setdefault("sku", body.code)
        else:
            if body.code:
                invalid("Only master records have a business code")
            subject = body.subject or ("item-" + new_id())
        if body.kind == "offer":
            data = normalize_offer(data)
        request = RevisionIn(key=body.key, subject=subject, kind=body.kind, expected_revision=body.expected_revision, visibility=body.visibility, data=data)
        return new_revision(s, request, at), body.visibility, None

    return s.command("catalog", body, record)


def label(row):
    d = row.data
    if row.kind == "offer":
        p = d.get("price")
        return f"{p['currency']} {display_money(p['amount_minor'], p['currency'])} / {p['basis_quantity']} {p['unit']}" if p else "Báo giá đang chuẩn bị"
    return (
        d.get("name")
        or d.get("guidance")
        or d.get("document")
        or d.get("warranty")
        or d.get("payment")
        or d.get("shipping")
        or d.get("status")
        or "Điều khoản đang chuẩn bị"
    )


def card(s, row):
    return {
        **s.summary(row),
        "label": label(row)[:160],
        "code": row.data.get("catalog_code"),
        "sku": row.data.get("sku"),
        **({"level": row.data["level"]} if row.kind == "objective" else {}),
        "identity": "registered" if row.data.get("catalog_code") else ("unmapped" if row.kind in MASTERS else None),
    }


@router.get("/items")
def items(kind: LookupKind, q: str = Query("", max_length=100), after: str = Query("", max_length=64), limit: int = Query(20, ge=1, le=50), s=Depends(reader)):
    # Select the current revision before searching its name or SKU. A renamed product must leave the old search.
    heads = s.query(Row).with_only_columns(Row.subject, func.max(Row.revision).label("latest")).filter_by(kind=kind).group_by(Row.subject).subquery()
    query = s.query(Row).join(heads, (heads.c.subject == Row.subject) & (heads.c.latest == Row.revision)).where(Row.subject > after)
    if q.strip():
        value = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        match = "%" + value + "%"
        query = query.where(
            or_(
                Row.subject.ilike(match, escape="\\"),
                *[Row.data[k].as_string().ilike(match, escape="\\") for k in ("name", "sku", "catalog_code", "document", "guidance")],
            )
        )
    rows = list(s.db.scalars(query.order_by(Row.subject).limit(limit + 1)))
    visible = rows[:limit]
    names = ("product", "variant", "market")
    refs = {p[k] for row in visible if (p := row.data.get("placement")) for k in names if p.get(k)}
    titles = {r.id: label(r) for r in s.db.scalars(s.query(Row).where(Row.id.in_(refs)))} if refs else {}
    cards = []
    for row in visible:
        view = card(s, row)
        place = row.data.get("placement")
        if place:
            context = [titles.get(place[k], "Hạn chế") for k in names if place.get(k)]
            context.extend([place["region"], place["channel"], place["locale"]])
            context.extend(str(v) for v in (row.data.get("applicability") or {}).values() if v is not None)
            view["scope_label"] = " · ".join(context)
        cards.append(view)
    return {"items": cards, "next": visible[-1].subject if len(rows) > limit else None}


@router.get("/items/{revision_id}")
def details(revision_id: str, s=Depends(reader)):
    row = s.get(Row, revision_id)
    if row.kind not in ("product", "service", "variant", "market", "policy", "availability", "offer", "guidelines", "icp", "segment", "objective", "kpi"):
        missing()
    data = dict(row.data)
    refs = {}

    def redact(node):
        if not isinstance(node, dict):
            return node
        out = {}
        for k, v in node.items():
            if k in ("company_parent", "company_objective") and isinstance(v, str):
                company = check_company_reference(s, v, require_approved=False)
                refs[k] = {
                    "id": v,
                    "label": company.name,
                    "revision": company.revision,
                    "scope": "company",
                    "state": current_state(s.db, company, latest_decision(s.db, company)),
                }
                out[k] = v
            elif k in REFS and isinstance(v, str):
                r = s.db.scalar(s.query(Row).where(Row.id == v))
                if r:
                    refs[k] = {"id": v, "label": label(r)[:160], "revision": r.revision}
                    out[k] = v
                else:
                    refs[k] = {"status": "restricted"}
                    out[k] = None
            else:
                out[k] = redact(v)
        return out

    data = redact(data)
    if row.kind == "objective" and data.get("campaign_id"):
        campaign = s.db.get(Campaign, data["campaign_id"])
        if campaign and campaign.brand_id == row.brand_id and campaign.tenant_id == row.tenant_id:
            refs["campaign_id"] = {"id": campaign.id, "label": campaign.name}
    if row.kind == "offer" and data.get("price"):
        price = data["price"].copy()
        price["amount"] = display_money(price.pop("amount_minor"), price["currency"])
        labels = price.pop("conditions")
        price["condition_ids"] = [CONDITION_BY_LABEL[x] for x in labels if x in CONDITION_BY_LABEL]
        price["unmapped_conditions"] = [x for x in labels if x not in CONDITION_BY_LABEL]
        data["price"] = price
    missing_fields = [k for k in ("source", "baseline", "target", "actual") if data.get(k) is None] if row.kind == "kpi" else []
    return {
        **card(s, row),
        "data": data,
        "references": refs,
        "missing_fields": missing_fields,
        "evidence_state": ("linked" if row.data.get("source") else "missing") if row.kind in ("segment", "icp", "kpi") else None,
    }


@router.get("/dictionary")
def dictionary(s=Depends(reader)):
    return {"territories": TERRITORIES, "conditions": CONDITION_LABELS, "can_approve": s.approver}


@router.get("/commands/{key}")
def receipt(key: str, s=Depends(reader)):
    command = s.db.scalar(s.query(KnowledgeCommand).filter_by(actor=s.actor, key=key, operation="catalog"))
    if not command:
        missing()
    return command.result
