"""Verified ownership and local-only, out-of-band delivery for synthetic accounts."""

import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from .identity_quota import admit
from .access import set_context
from .database import APP_ENV, get_db
from .delivery import as_utc, lock_document
from .models import AuditEvent, Client, IdentityChallenge, Membership, Tenant, User, utcnow
from .security import current_user, sign_challenge

router = APIRouter(prefix="/api", tags=["Identity"])


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr = Field(min_length=43, max_length=128)


class MailboxConfigurationError(RuntimeError):
    pass


def deliver(email, message, *, invitation_id=None):
    """Development delivery boundary. The caller commits only after delivery succeeds."""
    if APP_ENV not in {"local", "development", "test"}:
        raise MailboxConfigurationError("Local mailbox requires a development environment")
    root = Path(os.getenv("AMC_DEV_MAILBOX_DIR", ".dev-mailbox")).resolve()
    if root.is_relative_to(Path(__file__).resolve().parent):
        raise MailboxConfigurationError("Configure a private mailbox outside application sources")
    directory = root / hashlib.sha256(email.encode()).hexdigest()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if invitation_id:
        directory = directory / "invitations"
        directory.mkdir(mode=0o700, exist_ok=True)
    # Random filenames keep successive deliveries separate and prevent overwrites.
    path = directory / ((invitation_id or secrets.token_hex(16)) + ".txt")
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w", encoding="ascii") as target:
        target.write(message)


def issue(db, user, **reservation):
    lock_document(db, user.id)
    if db.get(User, user.id, populate_existing=True).verified_at:
        raise HTTPException(409, "Email already verified")
    token = secrets.token_urlsafe(32)
    row = db.get(IdentityChallenge, user.id)
    if row is None:
        row = IdentityChallenge(user_id=user.id, **reservation)
        db.add(row)
    row.digest = hashlib.sha256(token.encode()).hexdigest()
    row.expires_at = utcnow() + timedelta(minutes=20)
    with db.no_autoflush:
        sign_challenge(db, user.id, "issue", row.digest)
    db.flush()
    # A failed local handoff rolls back the new digest. A file left by a failed
    # database commit is unusable and the account can request another delivery.
    deliver(user.email, token)


@router.post("/auth/request-verification", status_code=204)
def request_verification(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    admit(db, request, "verification_issue", actor=user.id)
    issue(db, user)
    db.commit()


@router.post("/auth/verify-email", status_code=204)
def verify_email(body: Verification, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    admit(db, request, "verification_redeem", actor=user.id)
    lock_document(db, user.id)
    row = db.get(IdentityChallenge, user.id)
    digest = hashlib.sha256(body.token.get_secret_value().encode()).hexdigest()
    if row is None or not hmac.compare_digest(row.digest, digest) or as_utc(row.expires_at) <= utcnow():
        raise HTTPException(400, "Invalid or expired verification")
    workspace, name, mode = row.workspace_id, row.organization_name, row.mode
    if db.get_bind().dialect.name == "postgresql":
        sign_challenge(db, user.id, "redeem", digest)
        if not db.scalar(text("SELECT amc_acl.verify_email(:digest)"), {"digest": digest}):
            raise HTTPException(400, "Invalid or expired verification")
    else:
        user.verified_at = utcnow()
        db.delete(row)
        if workspace:
            db.add(Tenant(id=workspace, name=name, mode=mode))
            db.flush()
            db.add(Membership(tenant_id=workspace, user_id=user.id, role="owner"))
            db.flush()
    if workspace:
        set_context(db, actor=user.id, tenant=workspace)
        if mode == "inhouse":
            db.add(Client(tenant_id=workspace, name="Internal Marketing", sector="Internal"))
        db.add(AuditEvent(tenant_id=workspace, user_id=user.id, event="tenant.created", subject_id=workspace, details={"mode": mode}))
    db.commit()


def deliver_invitation(email, iid, secret):
    origin = os.getenv("AMC_PUBLIC_ORIGIN") or "http://127.0.0.1:" + os.getenv("AMC_HTTP_PORT", "8000")
    url = urlsplit(origin)
    if url.scheme not in ("https", "http") or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
        raise RuntimeError("Configure AMC_PUBLIC_ORIGIN with the application origin")
    deliver(email, origin.rstrip("/") + "/#invite=" + secret, invitation_id=iid)


class WorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    organization_name: str = Field(min_length=2, max_length=150)
    mode: Literal["agency", "inhouse"]


@router.post("/me/workspaces", status_code=201)
def create_workspace(body: WorkspaceRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.verified_at is None:
        raise HTTPException(403, "Hãy xác minh email trước khi tạo workspace.")
    # Actor-specific stable ID also serializes concurrent retries in PostgreSQL.
    tid = str(uuid5(NAMESPACE_URL, f"amc:workspace:{user.id}:{body.request_id}"))
    lock_document(db, tid)
    set_context(db, actor=user.id, tenant=tid)
    existing = db.get(Tenant, tid)
    if existing:
        owner = db.get(Membership, (tid, user.id))
        if not owner or owner.role != "owner" or (existing.name, existing.mode) != (body.organization_name, body.mode):
            raise HTTPException(409, "Yêu cầu tạo đã được dùng với thông tin khác.")
    else:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT amc_acl.create_verified_workspace(:t,:n,:m)"), {"t":tid,"n":body.organization_name,"m":body.mode})
        else:
            db.add(Tenant(id=tid, name=body.organization_name, mode=body.mode))
            db.flush()
            db.add(Membership(tenant_id=tid, user_id=user.id, role="owner"))
            db.flush()
        if body.mode == "inhouse":
            db.add(Client(tenant_id=tid, name="Internal Marketing", sector="Internal"))
        db.add(AuditEvent(tenant_id=tid, user_id=user.id, event="tenant.created", subject_id=tid, details={"mode":body.mode}))
    db.commit()
    return {"tenant_id":tid}
