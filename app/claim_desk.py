"""Brand-scoped, read-time claim desk. No approval or evidence visibility is inferred from a projection."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from sqlalchemy import select, text

from migrations.claim_display import rule
from . import knowledge_models as m
from .business_knowledge import history, impact, reader, writer
from .knowledge_authority import check_assertion, new_revision, scoped_references, sqlite_instant
from .knowledge_contracts import Assertion, Command, Name, Ref, RevisionIn, Subject, Window, approval_category
from .knowledge_store import conflict, missing, stamp
from .models import Membership


router = APIRouter(prefix="/api/tenants/{tenant_id}/clients/{client_id}/brands/{brand_id}/knowledge/claim-desk", tags=["source and claim review"])


class Draft(Command, Window):
    subject: Subject | None = None
    expected_revision: Annotated[int, Field(ge=0)]
    source_revision: Ref
    locator: Name
    assertion: Assertion


def no_cache(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


def brief(s, row):
    return s.summary(row) | {"label": row.subject}


def visible(s, key):
    return s.db.scalar(s.query(m.KnowledgeRevision).filter_by(id=key))


def display(s, row):
    """Read only current, explicitly public wording. Suppress all hidden handles and notes."""
    if row.visibility != "public" or row.kind != "claim":
        return None
    statement = row.data["assertion"]
    args = dict(tenant=row.tenant_id, client=row.client_id, brand=row.brand_id, claim=row.id, category=approval_category(statement))
    if s.postgres:
        query = "SELECT amc_business.claim_display_current(:tenant,:client,:brand,:claim,:category)"
    else:
        connection = s.db.connection()
        if not connection.info.get("amc_claim_instant"):
            connection.connection.driver_connection.create_function("amc_claim_instant", 1, sqlite_instant)
            connection.info["amc_claim_instant"] = True
        query = rule(False)
        args["at"] = stamp(s.now())
    if not s.db.scalar(text(query), args):
        return None
    try:
        # Same current pricing and contradiction rules used by C1. An opaque
        # selector or unreadable commercial declaration fails closed.
        check_assertion(s, statement, s.now())
    except HTTPException as exc:
        if exc.status_code in (404, 409):
            return None
        raise
    place = statement["placement"]
    context = {k: place[k] for k in ("locale", "channel", "region")}
    for k in ("product", "variant", "market"):
        if not place.get(k):
            continue
        target = visible(s, place[k])
        if target is None:
            return None
        context[k] = target.data["name"]
    return {
        **{k: statement[k] for k in ("wording", "qualifiers", "category", "price", "quantity", "applicability") if statement.get(k) is not None},
        "placement": context,
        "valid_from": row.data.get("valid_from"),
        "valid_until": row.data.get("valid_until"),
    }


def page(s, kind, offset, count):
    query = s.query(m.KnowledgeRevision).filter_by(kind=kind).order_by(m.KnowledgeRevision.created_at.desc(), m.KnowledgeRevision.id)
    rows = s.db.scalars(query.offset(offset).limit(count + 1)).all()
    items = []
    for row in rows[:count]:
        item = brief(s, row)
        if kind == "source":
            item["label"] = row.data["document"]
        elif kind == "claim" and s.approver:
            item["label"] = row.data["assertion"]["wording"]
        elif kind == "claim":
            published = display(s, row)
            item["label"] = published["wording"] if published else "Nhận định chờ kiểm tra"
        items.append(item)
    return items, len(rows) > count


@router.get("", dependencies=[Depends(no_cache)])
def board(claim_offset: int = Query(0, ge=0), source_offset: int = Query(0, ge=0), s=Depends(reader)):
    claims, more_claims = page(s, "claim", claim_offset, 20)
    sources, more_sources = page(s, "source", source_offset, 20)
    return {
        "claims": claims,
        "sources": sources,
        "more_claims": more_claims,
        "more_sources": more_sources,
        "can_edit": s.role != "viewer",
        "can_approve": s.approver,
    }


@router.get("/sources/{source_id}", dependencies=[Depends(no_cache)])
def source(source_id: str, s=Depends(reader)):
    row = s.get(m.KnowledgeRevision, source_id)
    if row.kind != "source":
        missing()
    entries = []
    for entry in row.data["entries"]:
        try:
            refs = scoped_references(s, entry["assertion"])
        except HTTPException as exc:
            if exc.status_code == 404:
                continue
            raise
        names = {
            key: refs[key, value].data["name"] for key, value in entry["assertion"]["placement"].items() if key in ("product", "variant", "market") and value
        }
        entries.append(dict(entry, names=names))
    return brief(s, row) | {key: row.data.get(key) for key in ("publisher", "document", "valid_from", "valid_until")} | {"entries": entries}


@router.get("/qualifications", dependencies=[Depends(no_cache)])
def qualifications(offset: int = Query(0, ge=0), s=Depends(reader)):
    if not s.approver:
        missing()
    items, more = page(s, "qualification", offset, 30)
    for item in items:
        data = s.get(m.KnowledgeRevision, item["id"]).data
        item.update(
            category=data["category"], basis=data["basis"], valid_until=data["valid_until"], reviewer=data["approver_id"], mine=data["approver_id"] == s.actor
        )
    # Email disclosure is outside this desk; staff use membership labels or the reviewer's own reference.
    members = s.db.scalars(
        select(Membership).filter_by(tenant_id=s.scope["tenant_id"]).where(Membership.role.in_(("admin", "owner"))).order_by(Membership.user_id)
    ).all()
    return {"items": items, "more": more, "reviewers": [{"id": mbr.user_id, "role": mbr.role, "self": mbr.user_id == s.actor} for mbr in members]}


@router.get("/placements", dependencies=[Depends(no_cache)])
def placements(term: str = Query("", max_length=100), s=Depends(reader)):
    result = {}
    for name, kinds in (("products", ("product", "service")), ("variants", ("variant",)), ("markets", ("market",))):
        query = s.query(m.KnowledgeRevision).where(m.KnowledgeRevision.kind.in_(kinds))
        if term:
            query = query.where(m.KnowledgeRevision.data["name"].as_string().icontains(term, autoescape=True))
        rows = s.db.scalars(query.order_by(m.KnowledgeRevision.created_at.desc(), m.KnowledgeRevision.id).limit(51)).all()
        result[name] = [dict(id=row.id, label=row.data["name"], product=row.data.get("product"), locales=row.data.get("locales", [])) for row in rows[:50]]
        result[name + "_more"] = len(rows) > 50
    return result


@router.get("/{claim_id}", dependencies=[Depends(no_cache)])
def detail(claim_id: str, s=Depends(reader)):
    claim = s.get(m.KnowledgeRevision, claim_id)
    if claim.kind != "claim":
        missing()
    bound = visible(s, claim.data["binding"])
    source_row = visible(s, bound.data["source"]) if bound else None
    evidence = None
    editable = None
    if source_row and bound:
        found = source(source_row.id, s)
        entry = next((e for e in found["entries"] if e["locator"] == bound.data["locator"]), None)
        if entry:
            evidence = {
                "source": brief(s, source_row),
                "document": found["document"],
                "publisher": found["publisher"],
                "valid_until": found["valid_until"],
                "binding": brief(s, bound),
                "locator": entry["locator"],
                "excerpt": entry["excerpt"],
                "assertion": entry["assertion"],
            }
            editable = claim.data["assertion"]
    events = history(claim_id, s)
    if not s.approver:
        events = [{k: e[k] for k in ("sequence", "state", "effective_at")} for e in events]
    other = s.db.scalars(s.query(m.KnowledgeRevision).filter_by(subject=claim.subject).order_by(m.KnowledgeRevision.revision.desc()).limit(100)).all()
    return {
        "claim": brief(s, claim),
        "public_wording": display(s, claim),
        "evidence": evidence,
        "assertion": editable,
        "valid_from": claim.data.get("valid_from"),
        "valid_until": claim.data.get("valid_until"),
        "required_qualification": approval_category(editable) if editable else None,
        "events": events,
        "revisions": [brief(s, r) for r in other],
        "impact": impact(claim_id, 30, s),
    }


@router.post("/drafts", status_code=201, dependencies=[Depends(no_cache)])
def save_draft(body: Draft, s=Depends(writer)):
    def save(at):
        src = s.get(m.KnowledgeRevision, body.source_revision)
        assertion = body.assertion.model_dump(mode="json")
        entry = next((e for e in src.data.get("entries", []) if e["locator"] == body.locator), None)
        if src.kind != "source" or entry is None:
            missing()
        if entry["assertion"] != assertion:
            conflict("Nội dung, điều kiện và phạm vi phải khớp với mục chứng cứ đã chọn. Hãy đối chiếu hoặc chọn nguồn thay thế.")
        subject = body.subject or "claim-" + uuid4().hex
        bound = new_revision(
            s,
            RevisionIn(
                key=body.key,
                kind="binding",
                subject="binding-" + uuid4().hex,
                expected_revision=0,
                visibility=src.visibility,
                data={"source": src.id, "locator": body.locator, "assertion": assertion},
            ),
            at,
        )
        row = new_revision(
            s,
            RevisionIn(
                key=body.key,
                kind="claim",
                subject=subject,
                expected_revision=body.expected_revision,
                visibility="public",
                data={"binding": bound["id"], "assertion": assertion, "valid_from": body.valid_from, "valid_until": body.valid_until},
            ),
            at,
        )
        return row, src.visibility, None

    return s.command("desk_claim_draft", body, save)
