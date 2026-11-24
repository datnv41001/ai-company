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
        Index("ix_review_page", "tenant_id", "created_at", "id"),
        Index("ix_client_review_page", "tenant_id", "client_id", "created_at", "id"),
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


class PortalInvitation(Base):
    __tablename__ = "portal_invitations"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "client_id"], ["clients.tenant_id", "clients.id"]),
        ForeignKeyConstraint(["tenant_id", "client_id", "brand_id"], ["brands.tenant_id", "brands.client_id", "brands.id"]),
        ForeignKeyConstraint(["tenant_id", "brand_id", "campaign_id"], ["campaigns.tenant_id", "campaigns.brand_id", "campaigns.id"]),
        CheckConstraint("campaign_id IS NULL OR brand_id IS NOT NULL"),
        CheckConstraint("(role='client_viewer' AND client_id IS NOT NULL AND client_name IS NOT NULL) OR "
                        "(role IN ('viewer','editor','admin') AND client_id IS NULL AND client_name IS NULL "
                        "AND brand_id IS NULL AND campaign_id IS NULL AND NOT can_comment AND NOT can_decide)"),
        CheckConstraint("state IN ('pending','accepted','revoked')"),
        Index("uq_pending_portal_invite", "tenant_id", "user_id", unique=True,
              sqlite_where=text("state='pending'"), postgresql_where=text("state='pending'")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), server_default=text("'client_viewer'"))
    client_id: Mapped[str | None] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    invited_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(String(320))
    workspace_name: Mapped[str] = mapped_column(String(150))
    client_name: Mapped[str | None] = mapped_column(String(160))
    brand_id: Mapped[str | None] = mapped_column(String(36))
    campaign_id: Mapped[str | None] = mapped_column(String(36))
    can_comment: Mapped[bool] = mapped_column(Boolean)
    can_decide: Mapped[bool] = mapped_column(Boolean)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(12), default="pending")
