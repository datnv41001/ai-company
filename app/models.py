from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(150))
    mode: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "client_id"], ["clients.tenant_id", "clients.id"]),
        CheckConstraint("(role = 'client_viewer' AND client_id IS NOT NULL) OR "
                        "(role IN ('viewer','editor','admin','owner') AND client_id IS NULL)", name="membership_scope"),
    )
    client_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16))


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_clients_tenant_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    sector: Mapped[str] = mapped_column(String(160), default="")


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_brands_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "client_id"], ["clients.tenant_id", "clients.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    brand_guidelines: Mapped[str] = mapped_column(Text, default="")
    product_truth: Mapped[str] = mapped_column(Text, default="")


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_campaigns_tenant_id"),
        ForeignKeyConstraint(["tenant_id", "brand_id"], ["brands.tenant_id", "brands.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    brief: Mapped[str] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")


class WorkTask(Base):
    __tablename__ = "work_tasks"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "campaign_id"], ["campaigns.tenant_id", "campaigns.id"]),
        UniqueConstraint("campaign_id", "workflow_key", name="uq_campaign_workflow_task"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    workflow_key: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(160))
    role_slug: Mapped[str] = mapped_column(String(90))
    expected_output: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="backlog")


class Deliverable(Base):
    __tablename__ = "deliverables"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "campaign_id"], ["campaigns.tenant_id", "campaigns.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_by: Mapped[str] = mapped_column(String(36))
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ActionRequest(Base):
    __tablename__ = "action_requests"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "campaign_id"], ["campaigns.tenant_id", "campaigns.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    action_kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(30), default="proposed")
    proposed_by: Mapped[str] = mapped_column(String(36))
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36))
    event: Mapped[str] = mapped_column(String(90))
    subject_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
