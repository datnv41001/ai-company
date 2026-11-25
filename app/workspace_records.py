"""One append-only record is both a scoped revision and its durable command receipt."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, DDL, ForeignKeyConstraint, Index, JSON, String, UniqueConstraint, event, text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class WorkspaceRecord(Base):
    __tablename__ = "business_workspace_records"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "client_id"], ["clients.tenant_id", "clients.id"]),
        ForeignKeyConstraint(["tenant_id", "client_id", "brand_id"], ["brands.tenant_id", "brands.client_id", "brands.id"]),
        CheckConstraint("revision > 0"),
        CheckConstraint("(kind='company' AND brand_id IS NULL AND scope='company') OR (kind IN ('brand','brief') AND brand_id IS NOT NULL AND scope=brand_id)"),
        UniqueConstraint("tenant_id", "client_id", "scope", "actor", "command_key"),
        Index(
            "uq_workspace_profile_revision",
            "tenant_id",
            "client_id",
            "scope",
            "revision",
            unique=True,
            sqlite_where=text("kind <> 'brief'"),
            postgresql_where=text("kind <> 'brief'"),
        ),
        Index("ix_workspace_owned_briefs", "tenant_id", "client_id", "brand_id", "actor", "kind", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36))
    client_id: Mapped[str] = mapped_column(String(36))
    brand_id: Mapped[str | None] = mapped_column(String(36))
    scope: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(12))
    revision: Mapped[int]
    actor: Mapped[str] = mapped_column(String(36))
    command_key: Mapped[str] = mapped_column(String(96))
    request_digest: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


for operation in ("UPDATE", "DELETE"):
    event.listen(
        WorkspaceRecord.__table__,
        "after_create",
        DDL(
            f"CREATE TRIGGER workspace_immutable_{operation} BEFORE {operation} ON business_workspace_records "
            "BEGIN SELECT RAISE(ABORT,'Immutable workspace revision'); END"
        ).execute_if(dialect="sqlite"),
    )
