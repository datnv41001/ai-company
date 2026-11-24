"""Verified ownership and local-only, out-of-band delivery for synthetic accounts."""

import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from .access import set_context
from .database import APP_ENV, get_db
from .delivery import as_utc, lock_document
from .models import AuditEvent, Client, IdentityChallenge, Membership, Tenant, User, utcnow
from .security import current_user

router = APIRouter(prefix="/api/auth", tags=["Identity"])


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr = Field(min_length=43, max_length=128)


def deliver(email, token):
    if APP_ENV not in {"local", "development", "test"}:
        raise RuntimeError("Local mailbox requires a development environment")
    root = Path(os.getenv("AMC_DEV_MAILBOX_DIR", ".dev-mailbox")).resolve()
    if root.is_relative_to(Path(__file__).resolve().parent):
        raise RuntimeError("Configure a private mailbox outside application sources")
    directory = root / hashlib.sha256(email.encode()).hexdigest()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Random filenames keep successive deliveries separate and prevent overwrites.
    path = directory / (secrets.token_hex(16) + ".txt")
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w", encoding="ascii") as target:
        target.write(token)


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
    db.flush()
    # A failed local handoff rolls back the new digest. A file left by a failed
    # database commit is unusable and the account can request another delivery.
    deliver(user.email, token)


@router.post("/request-verification", status_code=204)
def request_verification(user: User = Depends(current_user), db: Session = Depends(get_db)):
    issue(db, user)
    db.commit()


@router.post("/verify-email", status_code=204)
def verify_email(body: Verification, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lock_document(db, user.id)
    row = db.get(IdentityChallenge, user.id)
    digest = hashlib.sha256(body.token.get_secret_value().encode()).hexdigest()
    if row is None or not hmac.compare_digest(row.digest, digest) or as_utc(row.expires_at) <= utcnow():
        raise HTTPException(400, "Invalid or expired verification")
    workspace, name, mode = row.workspace_id, row.organization_name, row.mode
    if db.get_bind().dialect.name == "postgresql":
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
