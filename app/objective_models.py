"""Immutable company objective decisions and scoped edges from original C1 brand revisions."""

from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, DDL, ForeignKeyConstraint, Index, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class CompanyObjective(Base):
    __tablename__ = "business_company_objectives"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "client_id"], ["clients.tenant_id", "clients.id"]),
        UniqueConstraint("tenant_id", "client_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "client_id", "revision_id"],
            ["business_company_objectives.tenant_id", "business_company_objectives.client_id", "business_company_objectives.id"],
        ),
        UniqueConstraint("tenant_id", "client_id", "actor", "command_key"),
        UniqueConstraint("tenant_id", "client_id", "subject", "revision", "sequence"),
        CheckConstraint("revision > 0 AND sequence >= 0"),
        CheckConstraint(
            "(sequence=0 AND revision_id=id AND state='draft') OR (sequence>0 AND revision_id<>id AND state IN ('approved','disputed','withdrawn','superseded'))"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36))
    client_id: Mapped[str] = mapped_column(String(36))
    revision_id: Mapped[str] = mapped_column(String(36))
    subject: Mapped[str] = mapped_column(String(36))
    revision: Mapped[int]
    sequence: Mapped[int]
    state: Mapped[str] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(160))
    owner_name: Mapped[str] = mapped_column(String(160))
    actor: Mapped[str] = mapped_column(String(36))
    command_key: Mapped[str] = mapped_column(String(96))
    request_digest: Mapped[str] = mapped_column(String(64))
    digest: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CompanyObjectiveEdge(Base):
    __tablename__ = "business_company_objective_edges"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "client_id", "brand_id", "revision_id"],
            ["knowledge_revisions.tenant_id", "knowledge_revisions.client_id", "knowledge_revisions.brand_id", "knowledge_revisions.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "client_id", "company_revision_id"],
            ["business_company_objectives.tenant_id", "business_company_objectives.client_id", "business_company_objectives.id"],
        ),
        Index("ix_company_objective_usage", "tenant_id", "client_id", "company_revision_id"),
    )
    revision_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_revision_id: Mapped[str] = mapped_column(String(36))
    tenant_id: Mapped[str] = mapped_column(String(36))
    client_id: Mapped[str] = mapped_column(String(36))
    brand_id: Mapped[str] = mapped_column(String(36))


for table in (CompanyObjective.__table__, CompanyObjectiveEdge.__table__):
    for action in ("UPDATE", "DELETE"):
        event.listen(
            table,
            "after_create",
            DDL(
                f"CREATE TRIGGER immutable_{table.name}_{action} BEFORE {action} ON {table.name} BEGIN SELECT RAISE(ABORT,'Immutable objective history'); END"
            ).execute_if(dialect="sqlite"),
        )
event.listen(
    CompanyObjectiveEdge.__table__,
    "after_create",
    DDL("""
 CREATE TRIGGER company_objective_edge AFTER INSERT ON knowledge_revisions WHEN
 (NEW.kind='objective' AND json_extract(NEW.data,'$.company_parent') IS NOT NULL) OR
 (NEW.kind='kpi' AND json_extract(NEW.data,'$.company_objective') IS NOT NULL)
 BEGIN
 SELECT CASE WHEN NOT EXISTS (
   SELECT 1 FROM business_company_objectives o WHERE o.id=coalesce(json_extract(NEW.data,'$.company_parent'),json_extract(NEW.data,'$.company_objective'))
   AND o.tenant_id=NEW.tenant_id AND o.client_id=NEW.client_id AND o.sequence=0
 ) THEN RAISE(ABORT,'Unknown company objective revision') END;
 INSERT INTO business_company_objective_edges(revision_id,company_revision_id,tenant_id,client_id,brand_id)
 VALUES(NEW.id,coalesce(json_extract(NEW.data,'$.company_parent'),json_extract(NEW.data,'$.company_objective')),NEW.tenant_id,NEW.client_id,NEW.brand_id);
 END
""").execute_if(dialect="sqlite"),
)
