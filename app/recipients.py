"""In-app invitations for registered development accounts and the agency's recipient directory."""

from datetime import timedelta
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Literal
from pydantic import EmailStr, SecretStr, Field, model_validator
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .identity_quota import admit
from .identity import deliver_invitation
from .access import set_context
from .database import get_db
from .delivery import Input, Rights, as_utc, lock_document, validate_scope
from .delivery_models import PortalGrant, PortalInvitation
from .models import AuditEvent, Client, Membership, Tenant, User, utcnow
from .security import current_user, require_tenant

router = APIRouter(prefix="/api", tags=["Portal recipients"])


class Invite(Rights):
    email: EmailStr
    client_id: str | None = None
    role: Literal["client_viewer","viewer","editor","admin"] = "client_viewer"
    can_comment: bool = False
    can_decide: bool = False

    @model_validator(mode="after")
    def valid_scope(self):
        if self.role == "client_viewer":
            if not self.client_id:
                raise ValueError("A client invitation requires a client")
        elif any((self.client_id is not None, self.brand_id is not None, self.campaign_id is not None, self.can_comment, self.can_decide)):
            raise ValueError("Staff roles cannot carry portal rights")
        return self


class Acceptance(Input):
    """A recipient accepts the stored terms without supplying replacement fields."""


class InvitationLink(Input):
    token: SecretStr = Field(min_length=43, max_length=128)


def link_digest(secret):
    return hashlib.sha256(("amc-invitation:" + secret).encode()).hexdigest()


def summary(i):
    return {
        **{
            k: getattr(i, k)
            for k in (
                "id",
                "tenant_id",
                "user_id",
                "client_id",
                "workspace_name",
                "client_name",
                "brand_name",
                "campaign_name",
                "brand_id",
                "campaign_id",
                "can_comment",
                "can_decide",
                "email",
                "role",
            )
        },
        "state": "expired" if i.state == "pending" and as_utc(i.expires_at) <= utcnow() else i.state,
        "expires_at": as_utc(i.expires_at),
    }


def lock_recipient(db, tenant_id, email):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT amc_acl.lock_recipient(:tenant,:email)"), {"tenant":tenant_id,"email":email})
    else:
        lock_document(db, email)  # SQLite serializes writers using BEGIN IMMEDIATE.


def lock_offer_recipient(db, tenant_id, iid):
    email = db.scalar(select(PortalInvitation.email).where(
        PortalInvitation.id == iid, PortalInvitation.tenant_id == tenant_id))
    if email is None:
        raise HTTPException(404, "Lời mời không còn hiệu lực.")
    lock_recipient(db, tenant_id, email)


def revoke_pending(db, tenant_id, uid, email):
    db.execute(update(PortalInvitation).where(
        PortalInvitation.tenant_id == tenant_id, PortalInvitation.state == "pending",
        (PortalInvitation.user_id == uid) | (func.lower(func.trim(PortalInvitation.email)) == email.strip().lower())
    ).values(state="revoked"))


@router.get("/tenants/{tenant_id}/recipients")
def recipients(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    if db.get_bind().dialect.name == "postgresql":
        emails = dict(db.execute(text("SELECT uid,email FROM amc_acl.recipient_emails(:t)"), {"t": tenant_id}).all())
    else:
        emails = dict(db.execute(select(User.id, User.email).join(PortalGrant, PortalGrant.user_id == User.id).where(PortalGrant.tenant_id == tenant_id)).all())
    grants = db.scalars(select(PortalGrant).where(PortalGrant.tenant_id == tenant_id).order_by(PortalGrant.user_id))
    return [
        {**{k: getattr(g, k) for k in ("user_id", "client_id", "brand_id", "campaign_id", "can_comment", "can_decide")}, "email": emails.get(g.user_id)}
        for g in grants
    ]


@router.get("/tenants/{tenant_id}/invitations")
def outgoing(tenant_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    return [
        summary(i)
        for i in db.scalars(
            select(PortalInvitation)
            .where(PortalInvitation.tenant_id == tenant_id, PortalInvitation.state == "pending")
            .order_by(PortalInvitation.expires_at.desc())
        )
    ]


@router.post("/tenants/{tenant_id}/invitations", status_code=201)
def invite(tenant_id: str, body: Invite, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    admit(db, request, "invitation", actor=user.id, tenant=tenant_id, address=str(body.email).strip().lower())
    return issue_invitation(tenant_id, body, user, db)


def issue_invitation(tenant_id, body, user, db):
    issuer = require_tenant(db, user, tenant_id, "admin")
    if user.verified_at is None or (body.role == "admin" and issuer.role != "owner"):
        raise HTTPException(403, "Verified issuer with sufficient authority required")
    client = brand = campaign = None
    if body.client_id is not None:
        client = db.get(Client, body.client_id)
        if client is None or client.tenant_id != tenant_id:
            raise HTTPException(404, "Client unavailable")
        brand, campaign = validate_scope(db, tenant_id, client.id, body)
    email = str(body.email).lower().strip()
    set_context(db, actor=user.id, tenant=tenant_id, email=email)
    lock_recipient(db, tenant_id, email)
    recipient = db.scalar(select(User).where(User.email == email))
    if recipient and db.get(Membership, (tenant_id, recipient.id)):
        raise HTTPException(409, "Tài khoản đã thuộc workspace này.")
    db.execute(
        update(PortalInvitation)
        .where(
            PortalInvitation.tenant_id == tenant_id,
            PortalInvitation.email == email,
            PortalInvitation.state == "pending",
            PortalInvitation.expires_at <= utcnow(),
        )
        .values(state="revoked")
    )
    secret = secrets.token_urlsafe(32)
    invitation = PortalInvitation(
        tenant_id=tenant_id,
        link_digest=link_digest(secret),
        invited_by=user.id,
        email=email,
        workspace_name=db.get(Tenant, tenant_id).name,
        client_name=client.name if client else None,
        brand_name=brand.name if brand else None,
        campaign_name=campaign.name if campaign else None,
        expires_at=utcnow() + timedelta(days=7),
        **body.model_dump(exclude={"email"}),
    )
    db.add(invitation)
    try:
        db.flush()
        db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, event="portal.invitation_created", subject_id=invitation.id, details={}))
        deliver_invitation(email, invitation.id, secret)
        response = summary(invitation)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Đã có lời mời đang chờ.") from None
    return response


@router.delete("/tenants/{tenant_id}/invitations/{iid}", status_code=204)
def withdraw(tenant_id: str, iid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    lock_offer_recipient(db, tenant_id, iid)
    result = db.execute(
        update(PortalInvitation)
        .where(PortalInvitation.tenant_id == tenant_id, PortalInvitation.id == iid, PortalInvitation.state == "pending")
        .values(state="revoked")
    )
    if result.rowcount != 1:
        raise HTTPException(404, "Pending invitation unavailable")
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, event="portal.invitation_revoked", subject_id=iid, details={}))
    db.commit()


@router.get("/me/invitations")
def incoming(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.verified_at is None:
        return []
    return [
        summary(i)
        for i in db.scalars(
            select(PortalInvitation)
            .where(PortalInvitation.email == user.email, (PortalInvitation.user_id.is_(None) | (PortalInvitation.user_id == user.id)),
                   PortalInvitation.state == "pending", PortalInvitation.expires_at > utcnow())
            .order_by(PortalInvitation.expires_at)
        )
    ]


@router.post("/me/invitations/{iid}/accept", status_code=204)
def accept(iid: str, body: Acceptance | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.verified_at is None:
        raise HTTPException(403, "Verify your email before accepting an invitation")
    if db.get_bind().dialect.name == "postgresql":
        accepted = db.scalar(text("SELECT amc_acl.accept_portal_invitation(:i)"), {"i": iid})
        if not accepted:
            raise HTTPException(404, "Invitation unavailable")
    else:
        lock_document(db, iid)
        i = db.get(PortalInvitation, iid, populate_existing=True)
        if not i or i.user_id not in (None, user.id) or i.state != "pending" or as_utc(i.expires_at) <= utcnow() or db.get(Membership, (i.tenant_id, user.id)):
            raise HTTPException(404, "Invitation unavailable")
        issuer = db.get(Membership, (i.tenant_id, i.invited_by))
        if not issuer or issuer.role not in ("admin", "owner") or (i.role == "admin" and issuer.role != "owner") or not db.get(User, i.invited_by).verified_at:
            raise HTTPException(404, "Invitation unavailable")
        if i.email != user.email:
            raise HTTPException(404, "Invitation unavailable")
        i.user_id = user.id
        db.add(Membership(tenant_id=i.tenant_id, user_id=user.id, client_id=i.client_id, role=i.role))
        db.flush()
        if i.role == "client_viewer":
            validate_scope(db, i.tenant_id, i.client_id, i)
            db.add(PortalGrant(**{k: getattr(i, k) for k in ("tenant_id", "user_id", "client_id", "brand_id", "campaign_id", "can_comment", "can_decide")}))
        i.state = "accepted"
        db.add(AuditEvent(tenant_id=i.tenant_id, user_id=user.id, event="portal.invitation_accepted", subject_id=i.id, details={"role":i.role}))
    db.commit()


@router.post("/tenants/{tenant_id}/invitations/{iid}/resend", status_code=201)
def resend(tenant_id: str, iid: str, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    email = db.scalar(select(PortalInvitation.email).where(PortalInvitation.tenant_id == tenant_id, PortalInvitation.id == iid))
    if email is None:
        raise HTTPException(404, "Lời mời không còn hiệu lực.")
    admit(db, request, "invitation", actor=user.id, tenant=tenant_id, address=email.strip().lower())
    return replace_invitation(tenant_id, iid, user, db)


def replace_invitation(tenant_id, iid, user, db):
    require_tenant(db, user, tenant_id, "admin")
    lock_offer_recipient(db, tenant_id, iid)
    old = db.scalar(select(PortalInvitation).where(PortalInvitation.id == iid, PortalInvitation.tenant_id == tenant_id,
                                                  PortalInvitation.state == "pending").with_for_update())
    if old is None:
        raise HTTPException(404, "Lời mời không còn hiệu lực.")
    terms = Invite(**{key: getattr(old, key) for key in Invite.model_fields})
    old.state = "revoked"
    db.flush()
    db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, event="portal.invitation_revoked", subject_id=iid, details={"reason":"resend"}))
    # Issuance rechecks the current sender and scope. A failure rolls back revocation as well.
    return issue_invitation(tenant_id, terms, user, db)


def addressed_link(body, user, db):
    if user.verified_at is None:
        raise HTTPException(403, "Hãy xác minh email để xem lời mời.")
    row = db.scalar(select(PortalInvitation).where(
        PortalInvitation.link_digest == link_digest(body.token.get_secret_value()), PortalInvitation.email == user.email,
        (PortalInvitation.user_id.is_(None) | (PortalInvitation.user_id == user.id)), PortalInvitation.state == "pending",
        PortalInvitation.expires_at > utcnow()))
    if row is None:
        raise HTTPException(404, "Lời mời đã hết hạn, đã dùng, bị thu hồi hoặc dành cho email khác.")
    return row


@router.post("/me/invitation-link")
def preview_link(body: InvitationLink, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return summary(addressed_link(body, user, db))


@router.post("/me/invitation-link/accept", status_code=204)
def accept_link(body: InvitationLink, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Resend issues a different ID. The locked acceptance path rechecks state and expiry.
    return accept(addressed_link(body, user, db).id, None, user, db)
