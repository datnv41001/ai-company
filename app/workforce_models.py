"""Public intake and private worker checkpoints have separate database policies."""

from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, JSON, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, new_id, utcnow


class WorkforceBrief(Base):
    __tablename__ = "workforce_briefs"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "client_id", "brand_id"], ["brands.tenant_id", "brands.client_id", "brands.id"]),
        ForeignKeyConstraint(["tenant_id", "brand_id", "campaign_id"], ["campaigns.tenant_id", "campaigns.brand_id", "campaigns.id"]),
        UniqueConstraint("tenant_id", "client_id", "brand_id", "campaign_id", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    client_id: Mapped[str] = mapped_column(String(36))
    brand_id: Mapped[str] = mapped_column(String(36))
    campaign_id: Mapped[str] = mapped_column(String(36))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(150))
    payload: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkforceRun(Base):
    __tablename__ = "workforce_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "client_id", "brand_id", "campaign_id", "brief_id"],
            ["workforce_briefs.tenant_id", "workforce_briefs.client_id", "workforce_briefs.brand_id", "workforce_briefs.campaign_id", "workforce_briefs.id"],
        ),
        ForeignKeyConstraint(["tenant_id", "campaign_id", "deliverable_id"], ["deliverables.tenant_id", "deliverables.campaign_id", "deliverables.id"]),
        UniqueConstraint("brief_id"),
        Index("ix_workforce_deliverable", "tenant_id", "campaign_id", "deliverable_id",
              postgresql_where=text("deliverable_id IS NOT NULL"), sqlite_where=text("deliverable_id IS NOT NULL")),
        Index("ix_workforce_queue", "tenant_id", "campaign_id", "state", "ready_at"),
        CheckConstraint("state IN ('queued','running','failed','awaiting_qa')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36))
    client_id: Mapped[str] = mapped_column(String(36))
    brand_id: Mapped[str] = mapped_column(String(36))
    campaign_id: Mapped[str] = mapped_column(String(36))
    brief_id: Mapped[str] = mapped_column(String(36))
    deliverable_id: Mapped[str | None] = mapped_column(String(36))
    knowledge: Mapped[dict] = mapped_column(JSON)
    plan: Mapped[list] = mapped_column(JSON)
    checkpoints: Mapped[list] = mapped_column(JSON, default=list)
    journal: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[str] = mapped_column(String(20), default="queued")
    lease: Mapped[str | None] = mapped_column(String(36))
    ready_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    attempts: Mapped[int] = mapped_column(default=0)
    budget_microusd: Mapped[int]
    reserved_microusd: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
