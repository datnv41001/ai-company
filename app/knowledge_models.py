"""Append-only business knowledge rows. Exact revision references include the complete scope."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, JSON, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ScopedKnowledge:
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36))
    client_id: Mapped[str] = mapped_column(String(36))
    brand_id: Mapped[str] = mapped_column(String(36))
    visibility: Mapped[str] = mapped_column(String(12))


SCOPE = ("tenant_id", "client_id", "brand_id")


def scope_key(column, parent):
    return ForeignKeyConstraint([*SCOPE, column], [*(f"{parent}.{name}" for name in SCOPE), f"{parent}.id"])


def boundaries(*rules):
    return (
        UniqueConstraint(*SCOPE, "id"),
        ForeignKeyConstraint(SCOPE, ["brands.tenant_id", "brands.client_id", "brands.id"]),
        CheckConstraint("visibility IN ('public','internal','restricted')"),
        *rules,
    )


class KnowledgeRevision(ScopedKnowledge, Base):
    __tablename__ = "knowledge_revisions"
    __table_args__ = boundaries(UniqueConstraint(*SCOPE, "subject", "revision"), CheckConstraint("revision > 0"))
    subject: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(24))
    revision: Mapped[int]
    data: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    author: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class KnowledgeLink(ScopedKnowledge, Base):
    __tablename__ = "knowledge_links"
    __table_args__ = boundaries(
        scope_key("revision_id", "knowledge_revisions"), scope_key("target_id", "knowledge_revisions"), UniqueConstraint("revision_id", "relation", "target_id")
    )
    revision_id: Mapped[str] = mapped_column(String(36))
    target_id: Mapped[str] = mapped_column(String(36))
    relation: Mapped[str] = mapped_column(String(24))


class KnowledgeEvent(ScopedKnowledge, Base):
    __tablename__ = "knowledge_events"
    __table_args__ = boundaries(
        scope_key("revision_id", "knowledge_revisions"), scope_key("qualification_id", "knowledge_revisions"), UniqueConstraint("revision_id", "sequence")
    )
    revision_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int]
    qualification_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    state: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(400))
    actor: Mapped[str] = mapped_column(String(36))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class KnowledgeSnapshot(ScopedKnowledge, Base):
    __tablename__ = "knowledge_snapshots"
    __table_args__ = boundaries(
        CheckConstraint("(campaign_id IS NULL) = (brief_id IS NULL)"),
        ForeignKeyConstraint([*SCOPE, "campaign_id", "brief_id"], [f"workforce_briefs.{k}" for k in (*SCOPE, "campaign_id", "id")]),
    )
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    brief_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Exact UTF-8 representation is served from this stored string, including snapshot_as_of.
    canonical: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    snapshot_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    preview_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class KnowledgeDependency(ScopedKnowledge, Base):
    __tablename__ = "knowledge_dependencies"
    __table_args__ = boundaries(
        scope_key("snapshot_id", "knowledge_snapshots"),
        scope_key("revision_id", "knowledge_revisions"),
        UniqueConstraint("snapshot_id", "revision_id"),
        Index("ix_knowledge_usage", "revision_id", "snapshot_id"),
    )
    snapshot_id: Mapped[str] = mapped_column(String(36))
    revision_id: Mapped[str] = mapped_column(String(36))


class KnowledgeCommand(ScopedKnowledge, Base):
    __tablename__ = "knowledge_commands"
    __table_args__ = boundaries(UniqueConstraint(*SCOPE, "actor", "key"), scope_key("snapshot_id", "knowledge_snapshots"))
    key: Mapped[str] = mapped_column(String(96))
    actor: Mapped[str] = mapped_column(String(36))
    operation: Mapped[str] = mapped_column(String(24))
    request_digest: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON)
    snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def install_sqlite_guard(table, connection, **kwargs):
    if connection.dialect.name == "sqlite":
        for action in ("UPDATE", "DELETE"):
            connection.exec_driver_sql(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table.name}_{action} BEFORE {action} ON {table.name} "
                "BEGIN SELECT RAISE(ABORT,'immutable knowledge history'); END"
            )


for model in (KnowledgeRevision, KnowledgeLink, KnowledgeEvent, KnowledgeSnapshot, KnowledgeDependency, KnowledgeCommand):
    event.listen(model.__table__, "after_create", install_sqlite_guard)
