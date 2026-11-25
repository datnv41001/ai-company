"""Server-side authority for one device family. Only digests of browser secrets persist."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException
from sqlalchemy import BigInteger, ForeignKey, String, event, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base
from .models import User, new_id

ACCESS_SECONDS = 300
IDLE_SECONDS = 24 * 3600
MAX_SECONDS = 7 * IDLE_SECONDS


class DeviceSession(Base):
    __tablename__ = "device_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    epoch: Mapped[int]
    credential_epoch: Mapped[int]
    generation: Mapped[str] = mapped_column(String(64))
    current_digest: Mapped[str] = mapped_column(String(64))
    csrf_digest: Mapped[str] = mapped_column(String(64))
    device: Mapped[str] = mapped_column(String(40))
    created: Mapped[int] = mapped_column(BigInteger)
    seen: Mapped[int] = mapped_column(BigInteger)
    reauthed: Mapped[int] = mapped_column(BigInteger)
    revoked: Mapped[bool] = mapped_column(default=False)


class UsedRefresh(Base):
    __tablename__ = "used_refresh_grants"
    session_id: Mapped[str] = mapped_column(ForeignKey("device_sessions.id", ondelete="CASCADE"), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)


def install_epoch_trigger(conn):
    conn.exec_driver_sql("""CREATE TRIGGER IF NOT EXISTS account_password_epoch AFTER UPDATE OF password_hash ON users
       WHEN NEW.password_hash <> OLD.password_hash BEGIN
         UPDATE users SET credential_epoch=OLD.credential_epoch+1 WHERE id=NEW.id; END""")


@event.listens_for(User.__table__, "after_create")
def sqlite_password_epoch(table, conn, **kwargs):
    if conn.dialect.name == "sqlite":
        install_epoch_trigger(conn)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def unauthorized():
    return HTTPException(401, "Phiên đã hết hiệu lực. Vui lòng đăng nhập lại.", headers={"Cache-Control":"no-store"})


def now(db):
    sql = "SELECT floor(extract(epoch FROM clock_timestamp()))::bigint" if db.get_bind().dialect.name == "postgresql" else "SELECT unixepoch()"
    return db.scalar(text(sql))


def user_lock(db, uid, *, shared=False):
    if db.get_bind().dialect.name == "postgresql":
        lock = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
        db.execute(text("SET LOCAL lock_timeout='5s'"))
        db.execute(text(f"SELECT {lock}(hashtextextended(:uid,23001))"), {"uid":uid})
    else:
        conn = db.connection()
        if not conn.connection.driver_connection.in_transaction:
            conn.exec_driver_sql("BEGIN IMMEDIATE")


def active(db, uid, sid, expected_epoch, credential_epoch):
    from .session_keys import generation, verify_config
    if db.get_bind().dialect.name == "postgresql":
        verify_config(db)
    current = now(db)
    row = db.execute(select(DeviceSession, User.credential_epoch).join(User, User.id == DeviceSession.user_id)
                     .where(DeviceSession.user_id == uid, DeviceSession.id == sid)
                     .execution_options(populate_existing=True)).first()
    if not row:
        raise unauthorized()
    device, live_epoch = row
    if (device.revoked or device.epoch != expected_epoch or credential_epoch != live_epoch
            or device.credential_epoch != live_epoch or device.generation != generation()
            or current >= min(device.created + MAX_SECONDS, device.seen + IDLE_SECONDS)):
        raise unauthorized()
    return device


def verify_access(db, payload, *, commit=False):
    try:
        if commit:
            user_lock(db, payload["sub"], shared=True)
        if now(db) >= payload["exp"]:
            raise unauthorized()
        return active(db, payload["sub"], payload["sid"], payload["se"], payload["ce"])
    except SQLAlchemyError:
        raise HTTPException(503, "Không đọc được trạng thái phiên.", headers={"Cache-Control":"no-store"}) from None


@event.listens_for(Session, "before_commit")
def guard_commit(db):
    # Routes can commit admission and then begin another transaction. Validate
    # against the primary in every committing transaction, with the same lock as revoke.
    payload = db.info.get("amc_access_session")
    if payload:
        from .security import sign_actor
        sign_actor(db, payload["sub"])
        with db.no_autoflush:
            verify_access(db, payload, commit=True)


def issue(db, user, password_hash, agent):
    from .session_keys import generation
    user_lock(db, user.id)
    db.refresh(user)
    if not hmac.compare_digest(user.password_hash, password_hash):
        raise unauthorized()
    stamp = now(db)
    secret, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    label = "Firefox" if "Firefox/" in agent else "Edge" if "Edg/" in agent else "Chrome" if "Chrome/" in agent else "Safari" if "Safari/" in agent else "API"
    device = DeviceSession(id=new_id(), user_id=user.id, epoch=1, credential_epoch=user.credential_epoch,
                           generation=generation(), current_digest=sha(secret), csrf_digest=sha(csrf), device=label,
                           created=stamp, seen=stamp, reauthed=stamp, revoked=False)
    db.add(device)
    db.flush()
    return device, secret, csrf


def access_claims(device, issuer):
    issued = datetime.now(timezone.utc)
    return {"sub":device.user_id, "sid":device.id, "se":device.epoch, "ce":device.credential_epoch,
            "iss":issuer, "aud":"amc-api", "iat":issued,
            "exp":min(issued + timedelta(seconds=ACCESS_SECONDS), datetime.fromtimestamp(device.created + MAX_SECONDS, timezone.utc))}
