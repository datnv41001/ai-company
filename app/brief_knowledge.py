"""Internal brief references. Selecting working knowledge never authorizes a Marketing claim."""

from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func

from .knowledge_models import KnowledgeRevision
from .knowledge_store import Store

Slot = Literal["product", "audience", "objective", "kpi"]
KINDS = {"product": ("product", "service", "variant"), "audience": ("icp", "segment"), "objective": ("objective",), "kpi": ("kpi",)}


def scoped(workspace, *, write=False):
    return Store(workspace.db, workspace.user, workspace.tenant, workspace.client, workspace.brand, write=write)


def selectable(store):
    # Do not copy confidential evidence or restricted facts into a personal brief,
    # even if its author also holds agency approval privileges.
    return store.query(KnowledgeRevision).where(KnowledgeRevision.visibility.in_(("public", "internal")))


def options(workspace, slot, query):
    store = scoped(workspace)
    row = KnowledgeRevision
    heads = (
        selectable(store)
        .with_only_columns(row.subject, func.max(row.revision).label("latest"))
        .where(row.kind.in_(KINDS[slot]))
        .group_by(row.subject)
        .subquery()
    )
    stmt = selectable(store).join(heads, (row.subject == heads.c.subject) & (row.revision == heads.c.latest)).where(row.kind.in_(KINDS[slot]))
    if query:
        stmt = stmt.where(row.data["name"].as_string().icontains(query, autoescape=True))
    rows = list(store.db.scalars(stmt.order_by(row.subject).limit(51)))
    return {"items": [dict(id=r.id, name=r.data["name"], revision=r.revision, state=store.summary(r)["state"]) for r in rows[:50]], "more": len(rows) > 50}


def pin(workspace, choices):
    store = scoped(workspace, write=True)
    selected = {}
    for slot, key in choices.items():
        row = store.db.scalar(selectable(store).where(KnowledgeRevision.id == key, KnowledgeRevision.kind.in_(KINDS[slot])))
        if row is None:
            raise HTTPException(422, "Choose a visible item from this brand for the correct field")
        state = store.summary(row)["state"]
        if state not in ("draft", "approved"):
            raise HTTPException(422, "The selected revision can no longer be added to a new draft")
        selected[slot] = dict(id=row.id, digest=row.digest, saved_state=state)
    return selected


def render(workspace, pinned):
    store = scoped(workspace)
    ids = [v["id"] for v in pinned.values()]
    rows = {r.id: r for r in store.db.scalars(selectable(store).where(KnowledgeRevision.id.in_(ids)))}
    output = {}
    for slot, record in pinned.items():
        row = rows.get(record["id"])
        if row is None or row.digest != record["digest"] or row.kind not in KINDS[slot]:
            output[slot] = {"available": False}
            continue
        # 'fact' is the operator's classification. The underlying customer evidence
        # still needs independent validation before execution or external use.
        output[slot] = {
            **record,
            "available": True,
            "label": row.data["name"],
            "kind": row.kind,
            "revision": row.revision,
            "basis": row.data.get("basis"),
            "current_state": store.summary(row)["state"],
        }
    return output
