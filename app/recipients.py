"""In-app invitations for registered development accounts and the agency's recipient directory."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import EmailStr
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .access import set_context
from .database import get_db
from .delivery import Rights, as_utc, lock_document, validate_scope
from .delivery_models import PortalGrant, PortalInvitation
from .models import AuditEvent, Client, Membership, Tenant, User, utcnow
from .security import current_user, require_tenant

router = APIRouter(prefix="/api", tags=["Portal recipients"])


class Invite(Rights):
    email: EmailStr
    client_id: str


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
                "brand_id",
                "campaign_id",
                "can_comment",
                "can_decide",
                "email",
            )
        },
        "state": "expired" if i.state == "pending" and as_utc(i.expires_at) <= utcnow() else i.state,
        "expires_at": as_utc(i.expires_at),
    }


def revoke_pending(db, tenant_id, uid):
    db.execute(
        update(PortalInvitation)
        .where(PortalInvitation.tenant_id == tenant_id, PortalInvitation.user_id == uid, PortalInvitation.state == "pending")
        .values(state="revoked")
    )


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
def invite(tenant_id: str, body: Invite, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
    client = db.get(Client, body.client_id)
    if client is None or client.tenant_id != tenant_id:
        raise HTTPException(404, "Client unavailable")
    validate_scope(db, tenant_id, client.id, body)
    email = str(body.email).lower().strip()
    set_context(db, actor=user.id, tenant=tenant_id, email=email)
    recipient = db.scalar(select(User).where(User.email == email))
    if recipient is None:
        raise HTTPException(404, "Người nhận cần đăng ký tài khoản trước.")
    if db.get(Membership, (tenant_id, recipient.id)):
        raise HTTPException(409, "Tài khoản đã thuộc workspace này.")
    db.execute(
        update(PortalInvitation)
        .where(
            PortalInvitation.tenant_id == tenant_id,
            PortalInvitation.user_id == recipient.id,
            PortalInvitation.state == "pending",
            PortalInvitation.expires_at <= utcnow(),
        )
        .values(state="revoked")
    )
    invitation = PortalInvitation(
        tenant_id=tenant_id,
        user_id=recipient.id,
        invited_by=user.id,
        email=email,
        workspace_name=db.get(Tenant, tenant_id).name,
        client_name=client.name,
        expires_at=utcnow() + timedelta(days=7),
        **body.model_dump(exclude={"email"}),
    )
    db.add(invitation)
    try:
        db.flush()
        db.add(AuditEvent(tenant_id=tenant_id, user_id=user.id, event="portal.invitation_created", subject_id=invitation.id, details={}))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Đã có lời mời đang chờ.") from None
    return summary(invitation)


@router.delete("/tenants/{tenant_id}/invitations/{iid}", status_code=204)
def withdraw(tenant_id: str, iid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_tenant(db, user, tenant_id, "admin")
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
    return [
        summary(i)
        for i in db.scalars(
            select(PortalInvitation)
            .where(PortalInvitation.user_id == user.id, PortalInvitation.state == "pending", PortalInvitation.expires_at > utcnow())
            .order_by(PortalInvitation.expires_at)
        )
    ]


@router.post("/me/invitations/{iid}/accept", status_code=204)
def accept(iid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.get_bind().dialect.name == "postgresql":
        accepted = db.scalar(text("SELECT amc_acl.accept_portal_invitation(:i)"), {"i": iid})
        if not accepted:
            raise HTTPException(404, "Invitation unavailable")
    else:
        lock_document(db, iid)
        i = db.get(PortalInvitation, iid)
        if not i or i.user_id != user.id or i.state != "pending" or as_utc(i.expires_at) <= utcnow() or db.get(Membership, (i.tenant_id, user.id)):
            raise HTTPException(404, "Invitation unavailable")
        db.add(Membership(tenant_id=i.tenant_id, user_id=user.id, client_id=i.client_id, role="client_viewer"))
        db.flush()
        db.add(PortalGrant(**{k: getattr(i, k) for k in ("tenant_id", "user_id", "client_id", "brand_id", "campaign_id", "can_comment", "can_decide")}))
        i.state = "accepted"
        db.add(AuditEvent(tenant_id=i.tenant_id, user_id=user.id, event="portal.invitation_accepted", subject_id=i.id, details={}))
    db.commit()
