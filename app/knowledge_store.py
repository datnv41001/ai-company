"""Transaction boundary, immutable persistence and authenticated reads for C1."""

import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from . import knowledge_models as m
from .models import Brand, Membership, new_id
from .security import require_tenant
from .session_keys import key


VISIBILITY = ("public", "internal", "restricted")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def conflict(reason):
    raise HTTPException(409, reason)


def missing():
    raise HTTPException(404, "Knowledge resource not found")


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def stamp(value):
    return aware(value).isoformat()


def signed_document(db, actor, name, values):
    """Bind a validated append to its table, actor and current PostgreSQL transaction."""
    tx = db.scalar(text("SELECT txid_current()"))
    doc = canonical({k: stamp(v) if isinstance(v, datetime) else v for k, v in values.items()})
    message = "\n".join(("knowledge-v22", actor, str(tx), name, doc))
    return dict(doc=doc, proof=hmac.new(key("AMC_DB_PROOF_KEY"), message.encode(), "sha256").hexdigest())


def restrictive(*classes):
    return max(classes, key=VISIBILITY.index)


class Store:
    def __init__(self, db, user, tenant_id, client_id, brand_id, *, write):
        self.db, self.actor = db, user.id
        self.scope = dict(tenant_id=tenant_id, client_id=client_id, brand_id=brand_id)
        self.postgres = db.get_bind().dialect.name == "postgresql"
        if write and not self.postgres and not db.connection().connection.driver_connection.in_transaction:
            db.execute(text("BEGIN IMMEDIATE"))
        role = require_tenant(db, user, tenant_id, "editor" if write else "viewer").role
        if role == "client_viewer" or db.info.get("amc_worker_scope"):
            missing()
        self.brand = db.scalars(select(Brand).filter_by(tenant_id=tenant_id, client_id=client_id, id=brand_id)).one_or_none()
        if self.brand is None:
            missing()
        if write and self.postgres:
            try:
                db.execute(text("SELECT amc_acl.lock_knowledge(:tenant_id,:client_id,:brand_id)"), self.scope)
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) == "42501":
                    missing()
                raise
        self.role = db.scalar(select(Membership.role).filter_by(tenant_id=tenant_id, user_id=user.id))
        if self.role not in ("owner", "admin", "editor", "viewer") or write and self.role == "viewer":
            missing()

    @property
    def approver(self):
        return self.role in ("admin", "owner")

    def now(self):
        if self.postgres:
            return self.db.scalar(text("SELECT clock_timestamp()"))
        return datetime.now(timezone.utc)

    def query(self, table):
        stmt = select(table).filter_by(**self.scope)
        if not self.approver:
            stmt = stmt.where(table.visibility.in_(("public", "internal")))
        return stmt

    def get(self, table, key):
        obj = self.db.scalar(self.query(table).where(table.id == key))
        if obj is None:
            missing()
        return obj

    def insert(self, table, visibility, **fields):
        if visibility == "restricted" and not self.approver:
            missing()
        values = {"id": new_id(), "visibility": visibility, **self.scope, **fields}
        try:
            self._append(table, values)
        except IntegrityError as exc:
            duplicate = getattr(exc.orig, "sqlstate", None) == "23505" or getattr(exc.orig, "sqlite_errorname", "") in (
                "SQLITE_CONSTRAINT_PRIMARYKEY",
                "SQLITE_CONSTRAINT_UNIQUE",
            )
            if duplicate and table is m.KnowledgeRevision:
                conflict("Revision changed or subject has another type")
            if duplicate and table is m.KnowledgeCommand:
                conflict("Command key already used with different inputs")
            raise
        return table(**values)

    def _append(self, table, values):
        if self.postgres:
            name = table.__tablename__
            self.db.execute(text("SELECT amc_acl.append_knowledge(:rel,:doc,:proof)"), dict(rel=name, **signed_document(self.db, self.actor, name, values)))
        else:
            self.db.execute(table.__table__.insert().values(**values))

    def events(self, row):
        return self.db.scalar(self.query(m.KnowledgeEvent).filter_by(revision_id=row.id).order_by(m.KnowledgeEvent.sequence.desc()).limit(1))

    def summary(self, row, at=None):
        event = self.events(row)
        state = event.state if event else "draft"
        if state == "approved" and not in_window(row.data, at or self.now()):
            state = "expired" if ended(row.data, at or self.now()) else "pending_effective"
        return dict(
            id=row.id,
            subject=row.subject,
            kind=row.kind,
            revision=row.revision,
            digest=row.digest,
            visibility=row.visibility,
            state=state,
            sequence=event.sequence if event else 0,
        )

    def append_event(self, row, sequence, state, reason, at, qualification=None):
        self.insert(
            m.KnowledgeEvent,
            row.visibility,
            revision_id=row.id,
            sequence=sequence,
            state=state,
            reason=reason,
            actor=self.actor,
            effective_at=at,
            qualification_id=qualification,
        )

    def command(self, operation, payload, action, target=None, prepare=None, fingerprint_input=None):
        inputs = payload.model_dump(mode="json") if fingerprint_input is None else fingerprint_input
        fingerprint = digest(canonical([operation, target, inputs]))
        old = self.db.scalar(self.query(m.KnowledgeCommand).filter_by(actor=self.actor, key=payload.key))
        if old:
            if old.request_digest != fingerprint:
                conflict("Command key already used with different inputs")
            return old.result
        if prepare:
            prepare()
        at = self.now()
        result, visibility, snapshot = action(at)
        queued = self.now() if operation == "queue" else None
        record = dict(
            key=payload.key,
            operation=operation,
            actor=self.actor,
            request_digest=fingerprint,
            result=result,
            snapshot_id=snapshot,
            effective_at=at,
            queued_at=queued,
        )
        if operation in ("queue", "qa", "share"):
            # The protocol exposes the immutable command receipt ID.
            result["effective_at"] = stamp(at)
            result["queued_at"] = stamp(queued) if queued else None
            result["id"] = new_id()
            record["result"] = result
            record["id"] = result["id"]
        self.insert(m.KnowledgeCommand, visibility, **record)
        self.db.commit()
        return result


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ended(data, at):
    return bool(data.get("valid_until") and at >= parse_time(data["valid_until"]))


def in_window(data, at):
    return (not data.get("valid_from") or at >= parse_time(data["valid_from"])) and not ended(data, at)
