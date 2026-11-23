"""Versioned client-facing records. The agency working copy stays in Deliverable."""

from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, new_id, utcnow


class PortalGrant(Base):
    __tablename__ = "portal_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "user_id", "client_id"], ["memberships.tenant_id", "memberships.user_id", "memberships.client_id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(["tenant_id", "client_id", "brand_id"], ["brands.tenant_id", "brands.client_id", "brands.id"]),
        ForeignKeyConstraint(["tenant_id", "brand_id", "campaign_id"], ["campaigns.tenant_id", "campaigns.brand_id", "campaigns.id"]),
        CheckConstraint("campaign_id IS NULL OR brand_id IS NOT NULL"),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36))
    brand_id: Mapped[str | None] = mapped_column(String(36))
    campaign_id: Mapped[str | None] = mapped_column(String(36))
    can_comment: Mapped[bool] = mapped_column(Boolean, default=False)
    can_decide: Mapped[bool] = mapped_column(Boolean, default=False)


class ClientReview(Base):
    __tablename__ = "client_reviews"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "client_id", "brand_id"], ["brands.tenant_id", "brands.client_id", "brands.id"]),
        ForeignKeyConstraint(["tenant_id", "brand_id", "campaign_id"], ["campaigns.tenant_id", "campaigns.brand_id", "campaigns.id"]),
        ForeignKeyConstraint(["tenant_id", "campaign_id", "deliverable_id"], ["deliverables.tenant_id", "deliverables.campaign_id", "deliverables.id"]),
        UniqueConstraint("deliverable_id", "version"),
        UniqueConstraint("tenant_id", "id", "digest"),
        CheckConstraint("version > 0 AND expires_at > created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    client_id: Mapped[str] = mapped_column(String(36), index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    campaign_id: Mapped[str] = mapped_column(String(36))
    deliverable_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int]
    title: Mapped[str] = mapped_column(String(160))
    preview: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    qa_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReviewEntry(Base):
    __tablename__ = "review_entries"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "review_id", "digest"], ["client_reviews.tenant_id", "client_reviews.id", "client_reviews.digest"]),
        UniqueConstraint("review_id", "actor_id", "request_key"),
        CheckConstraint("kind IN ('comment','approved','rejected','changes_requested','cancelled','superseded')"),
        Index("uq_review_terminal", "review_id", unique=True, sqlite_where=text("kind <> 'comment'"), postgresql_where=text("kind <> 'comment'")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(36))
    review_id: Mapped[str] = mapped_column(String(36), index=True)
    digest: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(Text, default="")
    request_key: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
