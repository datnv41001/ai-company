import os
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .access import set_context
from .database import APP_ENV, DATABASE_URL, get_db
from .models import Membership, User

SECRET = os.getenv("JWT_SECRET", "LOCAL_ONLY_INSECURE_DEVELOPMENT_SECRET")
ISSUER = os.getenv("JWT_ISSUER", "amc-local")
if (APP_ENV == "production" or DATABASE_URL.startswith("postgresql")) and (len(SECRET) < 32 or SECRET == "LOCAL_ONLY_INSECURE_DEVELOPMENT_SECRET" or SECRET.startswith("REPLACE-")):
    raise RuntimeError("A unique strong JWT_SECRET is required with PostgreSQL or in production.")

hasher = PasswordHasher()
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return hasher.hash(password)


def check_password(password: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerifyMismatchError, VerificationError):
        return False


def make_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user.id, "iss": ISSUER, "aud": "amc-api", "iat": now, "exp": now + timedelta(hours=8)}, SECRET, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer authentication required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"], audience="amc-api", issuer=ISSUER)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(401, "Invalid token subject")
    set_context(db, actor=subject)
    user = db.get(User, subject)
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    return user


ROLE_RANK = {"client_viewer": 0, "viewer": 0, "editor": 1, "admin": 2, "owner": 3}


def require_tenant(db: Session, user: User, tenant_id: str, min_role: str = "viewer") -> Membership:
    set_context(db, actor=user.id, tenant=tenant_id)
    membership = db.get(Membership, {"tenant_id": tenant_id, "user_id": user.id})
    if not membership or (membership.role == "client_viewer" and not membership.client_id) or ROLE_RANK.get(membership.role, -1) < ROLE_RANK[min_role]:
        # 404 is intentional: do not leak whether a tenant exists.
        raise HTTPException(status_code=404, detail="Resource not found")
    return membership
