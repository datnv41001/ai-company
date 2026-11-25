"""Browser refresh credentials stay in secure host cookies. Bearer clients can still sign in explicitly."""

import hmac
import os
import secrets
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import set_context
from .database import get_db
from .identity_quota import admit
from .models import User
from .security import check_password, current_user, make_token, sign_actor
from .session_state import DeviceSession, UsedRefresh, MAX_SECONDS, active, now, sha, unauthorized, user_lock, verify_access

router = APIRouter(prefix="/api", tags=["Device sessions"])
CONTEXT = "__Host-amc-context"
REFRESH = "__Host-amc-refresh-"
CSRF = "__Host-amc-csrf-"


class Reauthentication(BaseModel):
    password: SecretStr = Field(max_length=128)


def allowed_origin(request):
    origin = request.headers.get("origin", "")
    configured = os.getenv("AMC_PUBLIC_ORIGIN", "").rstrip("/")
    if configured:
        return origin == configured
    # Direct lab launch uses an ephemeral HTTP port. All other deployments must
    # configure their canonical HTTPS origin and a trusted transport boundary.
    actual = urlsplit(str(request.base_url))
    return actual.hostname in ("localhost", "127.0.0.1", "::1", "testserver") and origin == str(request.base_url).rstrip("/")


def grant_cookie(response, sid, secret, context, max_age):
    # A delayed refresh only replaces its own family's grant. It cannot select
    # an account, clear another device, or overwrite a later login's credential.
    response.set_cookie(REFRESH + sid, f"{context}.{sid}.{secret}", httponly=True,
                        secure=True, samesite="lax", path="/", max_age=max(0, max_age))
    response.headers["Cache-Control"] = "no-store"


def clear_cookies(response, sid):
    response.delete_cookie(REFRESH + sid, secure=True, httponly=True, samesite="lax", path="/")
    response.delete_cookie(CSRF + sid, secure=True, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"


def clear_matching_device(request, response, sid):
    if REFRESH + sid in request.cookies:
        clear_cookies(response, sid)
    else:
        response.headers["Cache-Control"] = "no-store"


def login_cookies(request, response, device, secret, csrf):
    current = request.cookies.get(CONTEXT, "")
    uid, _, generation = current.partition(".")
    if uid != device.user_id or len(generation) != 32 or not all(c in "0123456789abcdef" for c in generation):
        current = device.user_id + "." + secrets.token_hex(16)
    # Keep the jar bounded after repeated logins. Browser cookie order starts
    # with older cookies for this common path. Stale tabs can sign in again.
    keep = []
    for name, value in request.cookies.items():
        if name.startswith(REFRESH):
            try:
                sid = str(UUID(name[len(REFRESH):]))
            except ValueError:
                continue
            if value.startswith(current + "."):
                keep.append(sid)
            else:
                clear_cookies(response, sid)
    for sid in keep[:-7]:
        clear_cookies(response, sid)
    options = dict(secure=True, samesite="lax", path="/", max_age=MAX_SECONDS)
    response.set_cookie(CONTEXT, current, **options)
    response.set_cookie(CSRF + device.id, csrf, **options)
    grant_cookie(response, device.id, secret, current, MAX_SECONDS)
    return current


def cookie_proof(request, db):
    context = request.cookies.get(CONTEXT, "")
    uid, _, generation = context.partition(".")
    sid = request.headers.get("x-amc-session", "")
    if not allowed_origin(request):
        raise HTTPException(403, "Invalid refresh origin")
    try:
        UUID(uid)
        UUID(sid)
    except ValueError:
        raise HTTPException(409, "Reload and sign in to the intended session") from None
    set_context(db, actor=uid)
    sign_actor(db, uid)
    user_lock(db, uid)
    parts = request.cookies.get(REFRESH + sid, "").split(".")
    if len(parts) != 4 or parts[:3] != [uid, generation, sid]:
        raise HTTPException(409, "A different session is active in this browser")
    token = parts[3]
    csrf = request.headers.get("x-amc-csrf", "")
    if (
        not csrf.isascii()
        or not (20 <= len(csrf) <= 64)
        or not hmac.compare_digest(sha(csrf), sha(request.cookies.get(CSRF + sid, "")))
    ):
        raise HTTPException(403, "Invalid refresh origin or CSRF proof")
    if len(token) != 43:
        raise unauthorized()
    return uid, sid, token, csrf, context


@router.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    uid, sid, token, csrf, context = cookie_proof(request, db)
    device = db.get(DeviceSession, sid)
    if not device or device.user_id != uid or not hmac.compare_digest(device.csrf_digest, sha(csrf)):
        raise unauthorized()
    active(db, uid, sid, device.epoch, device.credential_epoch)
    digest = sha(token)
    if not hmac.compare_digest(digest, device.current_digest):
        if db.get(UsedRefresh, (sid, digest)):
            device.revoked = True
            device.epoch += 1
            db.commit()
        raise unauthorized()
    db.add(UsedRefresh(session_id=sid, digest=digest))
    successor = secrets.token_urlsafe(32)
    device.current_digest = sha(successor)
    device.seen = now(db)
    access = make_token(device)
    grant_cookie(response, sid, successor, context, device.created + MAX_SECONDS - device.seen)
    db.commit()
    return {"access_token": access, "token_type": "bearer"}


@router.get("/me/sessions")
def sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .session_keys import generation
    from .session_state import IDLE_SECONDS

    stamp = now(db)
    devices = db.scalars(
        select(DeviceSession)
        .where(
            DeviceSession.user_id == user.id,
            DeviceSession.revoked.is_(False),
            DeviceSession.credential_epoch == user.credential_epoch,
            DeviceSession.generation == generation(),
            DeviceSession.seen > stamp - IDLE_SECONDS,
            DeviceSession.created > stamp - MAX_SECONDS,
        )
        .order_by(DeviceSession.created.desc(), DeviceSession.id)
    )
    return [
        {"id": d.id, "device": d.device, "created": d.created, "last_seen": d.seen, "current": d.id == db.info["amc_access_session"]["sid"]} for d in devices
    ]


def revoke(db, user, target):
    payload = db.info["amc_access_session"]
    user_lock(db, user.id)
    own = verify_access(db, payload)
    if target != own.id and now(db) - own.reauthed >= 300:
        raise HTTPException(403, "Vui lòng xác thực lại mật khẩu.")
    device = db.scalar(select(DeviceSession).where(DeviceSession.user_id == user.id, DeviceSession.id == target))
    if not device:
        raise HTTPException(404, "Device session not found")
    if not device.revoked:
        device.revoked = True
        device.epoch += 1
    # This operation has already revalidated under the exclusive account lock.
    # Its own commit is allowed to retire the presenting session.
    db.info.pop("amc_access_session")
    db.commit()


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sid = db.info["amc_access_session"]["sid"]
    revoke(db, user, sid)
    clear_matching_device(request, response, sid)


@router.post("/auth/logout-cookie", status_code=204)
def logout_cookie(request: Request, response: Response, db: Session = Depends(get_db)):
    uid, sid, token, csrf, _ = cookie_proof(request, db)
    device = db.get(DeviceSession, sid)
    if device and not device.revoked:
        if device.user_id != uid or not hmac.compare_digest(device.csrf_digest, sha(csrf)) or not hmac.compare_digest(device.current_digest, sha(token)):
            raise unauthorized()
        device.revoked = True
        device.epoch += 1
        db.commit()
    clear_cookies(response, sid)


@router.delete("/me/sessions/{sid}", status_code=204)
def revoke_device(sid: str, request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    current = db.info["amc_access_session"]["sid"]
    revoke(db, user, sid)
    if sid == current:
        clear_matching_device(request, response, sid)


@router.post("/auth/reauthenticate", status_code=204)
def reauthenticate(body: Reauthentication, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    admit(db, request, "login", address=user.email.strip().lower(), actor=user.id)
    user_lock(db, user.id)
    device = verify_access(db, db.info["amc_access_session"])
    db.refresh(user)
    if not check_password(body.password.get_secret_value(), user.password_hash):
        raise HTTPException(401, "Incorrect password")
    device.reauthed = now(db)
    db.flush()
    db.commit()
