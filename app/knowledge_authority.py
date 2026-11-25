"""Resolve exact revision identity, commercial context and current authority under the brand guard."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from migrations.knowledge_commerce import conflict_query

from . import knowledge_models as m
from .commercial_scope import same_placement
from .knowledge_contracts import TYPES, approval_category, price_wording
from .knowledge_store import canonical, conflict, digest, in_window, parse_time, restrictive
from .models import Campaign, Membership


def invalid(reason):
    raise HTTPException(422, reason)


REF_KINDS = {
    "product": ("product", "service"),
    "variant": ("variant",),
    "market": ("market",),
    "offer": ("offer",),
    "availability": ("availability",),
    "policy": ("policy",),
    "source": ("source",),
    "binding": ("binding",),
    "parent": ("objective",),
    "objective": ("objective",),
}


def scoped_references(store, data):
    """Collect typed references, including SKU-specific entries within multi-subject evidence."""
    found = {}

    def visit(node):
        if isinstance(node, list):
            for item in node:
                visit(item)
        if not isinstance(node, dict):
            return
        for name, value in node.items():
            if name in REF_KINDS and isinstance(value, str):
                key = (name, value)
                if key not in found:
                    target = store.get(m.KnowledgeRevision, value)
                    if target.kind not in REF_KINDS[name]:
                        invalid("Wrong revision kind for " + name)
                    found[key] = target
            elif isinstance(value, (list, dict)):
                visit(value)
        if {"product", "variant", "market", "locale", "channel", "region"} == node.keys():
            if node.get("variant") and found["variant", node["variant"]].data["product"] != node["product"]:
                invalid("Variant belongs to another product revision")
            if node["locale"] not in found["market", node["market"]].data["locales"]:
                invalid("Locale outside market")

    visit(data)
    return found


def check_business_data(store, kind, subject, data):
    refs = scoped_references(store, data)
    if kind == "objective":
        if data["campaign_id"]:
            campaign = store.db.get(Campaign, data["campaign_id"])
            if not campaign or campaign.tenant_id != store.scope["tenant_id"] or campaign.brand_id != store.scope["brand_id"]:
                invalid("Campaign outside knowledge scope")
        parent = refs.get(("parent", data["parent"]))
        levels = {"brand": "company", "campaign": "brand"}
        if parent and (parent.subject == subject or parent.data["level"] != levels.get(data["level"])):
            invalid("Objective hierarchy or parent identity differs")
        while parent:
            if parent.subject == subject:
                invalid("Objective cycle")
            parent = store.get(m.KnowledgeRevision, parent.data["parent"]) if parent.data.get("parent") else None
    if kind == "offer":
        for field in ("availability", "policy"):
            if data.get(field) and not same_placement(refs[field, data[field]].data["placement"], data["placement"]):
                invalid("Offer terms refer to another subject or market")
    if kind == "binding":
        src = refs["source", data["source"]]
        entry = next((e for e in src.data["entries"] if e["locator"] == data["locator"]), None)
        if not entry or entry["assertion"] != data["assertion"]:
            invalid("No matching assertion at this source locator")
    if kind == "claim" and refs["binding", data["binding"]].data["assertion"] != data["assertion"]:
        invalid("Claim differs from bound subject, terms, qualifiers or wording")
    return refs


def new_revision(store, body, at):
    from .knowledge_store import stamp

    try:
        data = TYPES[body.kind].model_validate(body.data).model_dump(mode="json")
    except ValidationError as exc:
        invalid(str(exc.errors(include_input=False, include_url=False, include_context=False)))
    prior = store.db.scalar(store.query(m.KnowledgeRevision).filter_by(subject=body.subject).order_by(m.KnowledgeRevision.revision.desc()).limit(1))
    if (prior.revision if prior else 0) != body.expected_revision or (prior and prior.kind != body.kind):
        conflict("Revision changed or subject has another type")
    if prior and prior.visibility != body.visibility:
        conflict("Visibility is pinned to the subject")
    refs = check_business_data(store, body.kind, body.subject, data)
    if body.kind == "qualification":
        if not store.approver or body.visibility != "restricted" or data["approver_id"] == store.actor:
            conflict("An independent administrator must document a restricted qualification")
        member = store.db.get(Membership, (store.scope["tenant_id"], data["approver_id"]))
        if not member or member.role not in ("admin", "owner"):
            conflict("Reviewer is not an authorized administrator in this workspace")
    revision = body.expected_revision + 1
    signature = digest(canonical(dict(subject=body.subject, kind=body.kind, revision=revision, visibility=body.visibility, data=data)))
    row = store.insert(
        m.KnowledgeRevision,
        body.visibility,
        subject=body.subject,
        kind=body.kind,
        revision=revision,
        digest=signature,
        data=data,
        author=store.actor,
        created_at=at,
    )
    for (relation, target_id), target in refs.items():
        store.insert(m.KnowledgeLink, restrictive(row.visibility, target.visibility), revision_id=row.id, target_id=target_id, relation=relation)
    return {**store.summary(row, at), "created_at": stamp(at)}


def linked(store, row):
    if row.kind == "source":
        # A withdrawal concerning SKU B on a multi-SKU sheet does not invalidate A's other locator.
        # A binding links the selected assertion's SKU and commercial revisions independently.
        return []
    return [target for target in scoped_references(store, row.data).values()]


def eligible(store, row, at, seen, *, include_root=True):
    if row.id in seen:
        return
    if len(seen) >= 192:
        conflict("Dependency budget exceeded")
    if include_root and store.summary(row, at)["state"] != "approved":
        conflict("Revision lacks current approved authority")
    if not in_window(row.data, at):
        conflict("Revision is outside its validity interval")
    if row.kind == "availability" and parse_time(row.data["observed_at"]) > at:
        conflict("Availability observation is in the future")
    seen[row.id] = row
    for target in linked(store, row):
        eligible(store, target, at, seen)
    if include_root and row.kind == "claim":
        decision = store.events(row)
        category = approval_category(row.data["assertion"])
        if category:
            if not decision or not decision.qualification_id or decision.actor == row.author:
                conflict("This exact claim needs a new independently qualified approval")
            mandate = store.get(m.KnowledgeRevision, decision.qualification_id)
            if mandate.kind != "qualification" or mandate.data["category"] != category or mandate.data["approver_id"] != decision.actor:
                conflict("Prior approval does not cover the complete public claim")
            eligible(store, mandate, at, seen)


def check_assertion(store, assertion, at):
    field = assertion["category"]
    if field == "price":
        requested = assertion["price"]
        qty = Decimal(assertion["quantity"])
        if qty < max(Decimal(requested["moq"]), Decimal(requested["tier_min"])) or requested["tier_max"] and qty > Decimal(requested["tier_max"]):
            conflict("Quantity is outside the authorized commercial tier")
        chosen = store.get(m.KnowledgeRevision, assertion["offer"])
        if not same_placement(chosen.data["placement"], assertion["placement"]) or chosen.data["price"] != requested:
            conflict("Quoted price differs from the exact offered terms")
        if assertion["wording"] != price_wording(requested):
            conflict("Published price wording differs from its typed amount, currency, unit or tax basis")
        # Compare commercially valid alternatives under the same selection basis.
        # Different prices for that same basis are ambiguous, including equal-valued duplicates.
        matches = []
        product = assertion["placement"]["product"]
        candidates = (
            store.query(m.KnowledgeRevision)
            .filter_by(kind="offer", visibility="public")
            .join(m.KnowledgeLink, m.KnowledgeLink.revision_id == m.KnowledgeRevision.id)
            .where(m.KnowledgeLink.relation == "product", m.KnowledgeLink.target_id == product)
            .limit(257)
        )
        candidates = store.db.scalars(candidates).all()
        if len(candidates) > 256:
            conflict("Offer selector requires operator reconciliation")
        for other in candidates:
            terms = other.data["price"]
            if not same_placement(other.data["placement"], assertion["placement"]) or not terms or store.summary(other, at)["state"] != "approved":
                continue
            if any(terms[k] != requested[k] for k in ("currency", "unit", "basis_quantity", "tax")) or not set(terms["conditions"]).issubset(
                assertion["qualifiers"]
            ):
                continue
            if qty < max(Decimal(terms["moq"]), Decimal(terms["tier_min"])) or terms["tier_max"] and qty > Decimal(terms["tier_max"]):
                continue
            matches.append(other.id)
        if matches != [chosen.id]:
            conflict("Marketing offer missing or ambiguous")
        if not set(requested["conditions"]).issubset(assertion["qualifiers"]):
            conflict("Price qualifiers omit a commercial condition")
    elif field in ("availability", "payment", "warranty"):
        name = "availability" if field == "availability" else "policy"
        row = store.get(m.KnowledgeRevision, assertion[name])
        observed = row.data["status" if field == "availability" else field]
        if not same_placement(row.data["placement"], assertion["placement"]) or not observed or observed == "unknown":
            conflict("Unknown or mismatched availability or policy")
        if observed != assertion["wording"]:
            conflict("Copy does not match the approved policy or stock declaration")
        if row.data.get("applicability") != assertion.get("applicability"):
            conflict("Claim must preserve the exact commercial applicability")
        facet = "status" if field == "availability" else field
        params = dict(tenant=row.tenant_id, client=row.client_id, brand=row.brand_id, revision=row.id, facet=facet, at=at)
        if store.postgres:
            query = "SELECT amc_acl.knowledge_commercial_conflict(:tenant,:client,:brand,:revision,:facet,:at)"
        else:
            # SQLite's built-in date functions round to milliseconds. Keep exact
            # microsecond boundaries and compare equivalent offsets as in PG.
            store.db.connection().connection.driver_connection.create_function("amc_commerce_instant", 1, sqlite_instant, deterministic=True)
            query = conflict_query(False)
            params["at"] = at.isoformat()
        if store.db.scalar(text(query), params):
            conflict("Commercial authority disputed")


def sqlite_instant(value):
    if value is None:
        return None
    delta = parse_time(value) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def change_state(store, row, command, at):
    if not store.approver:
        from .knowledge_store import missing

        missing()
    latest = store.events(row)
    seq = latest.sequence if latest else 0
    old = latest.state if latest else "draft"
    if command.expected_digest != row.digest or command.expected_sequence != seq:
        conflict("Authority history changed")
    transitions = {
        "draft": {"approved", "withdrawn", "disputed"},
        "approved": {"disputed", "withdrawn", "superseded"},
        "disputed": {"withdrawn", "superseded"},
        "superseded": {"withdrawn"},
        "withdrawn": set(),
    }
    if command.state not in transitions[old]:
        conflict("Invalid authority transition; create a new revision for a replacement")
    if command.preferred_revision:
        if command.state != "superseded" or row.kind not in ("availability", "policy"):
            invalid("A preference is recorded when retiring a stock or policy declaration")
        preferred = store.get(m.KnowledgeRevision, command.preferred_revision)
        if (
            preferred.id == row.id
            or preferred.kind != row.kind
            or not same_placement(preferred.data["placement"], row.data["placement"])
            or preferred.data.get("applicability") != row.data.get("applicability")
        ):
            conflict("Preferred authority must cover the same placement and order conditions")
        if row.kind == "policy" and any(row.data.get(term) and not preferred.data.get(term) for term in ("warranty", "payment", "shipping")):
            conflict("Preferred policy must cover each term of the retired policy")
        eligible(store, preferred, at, {})
        store.insert(
            m.KnowledgeLink, restrictive(row.visibility, preferred.visibility), revision_id=row.id, target_id=preferred.id, relation="preferred_authority"
        )
    if command.state == "approved":
        head = store.db.scalar(store.query(m.KnowledgeRevision).filter_by(subject=row.subject).order_by(m.KnowledgeRevision.revision.desc()).limit(1))
        if head.id != row.id:
            conflict("Cannot approve an older draft")
        sensitive = approval_category(row.data["assertion"]) if row.kind == "claim" else None
        if sensitive:
            if row.author == store.actor or not command.qualification_revision:
                conflict("Independent qualified approver required")
            mandate = store.get(m.KnowledgeRevision, command.qualification_revision)
            if mandate.kind != "qualification" or mandate.data["approver_id"] != store.actor or mandate.data["category"] != sensitive:
                conflict("Qualification does not cover this actor and category")
            eligible(store, mandate, at, {})
        elif command.qualification_revision:
            invalid("Qualification applies only to a sensitive claim approval")
        if row.kind == "qualification" and (row.data["approver_id"] == store.actor or store.role != "owner"):
            conflict("A different workspace owner must approve the reviewer's qualification")
        if row.kind == "source" and not row.data["entries"]:
            conflict("A legacy source needs reviewed, scoped assertions")
        eligible(store, row, at, {}, include_root=False)
        if row.kind in ("claim", "binding"):
            check_assertion(store, row.data["assertion"], at)
        for prev in store.db.scalars(store.query(m.KnowledgeRevision).filter_by(subject=row.subject).where(m.KnowledgeRevision.revision < row.revision)):
            prior = store.events(prev)
            if prior and prior.state == "approved":
                store.append_event(prev, prior.sequence + 1, "superseded", "New revision approved", at)
    elif command.qualification_revision:
        invalid("Qualification applies only to approval")
    store.append_event(row, seq + 1, command.state, command.reason, at, command.qualification_revision)
    return store.summary(row, at)
