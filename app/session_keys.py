"""Each cryptographic domain can change independently of access JWT issuance."""

import hashlib
import os
from fastapi import HTTPException
from sqlalchemy import text

from .database import APP_ENV, DATABASE_URL


def key(name):
    value = os.getenv(name, "")
    if not value and APP_ENV != "production" and DATABASE_URL.startswith("sqlite"):
        return hashlib.sha256(("local-synthetic-only/" + name).encode()).digest()
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        raw = b""
    if len(raw) != 32:
        raise RuntimeError(f"{name} requires a 32-byte hex key")
    return raw


def generation():
    return hashlib.sha256(key("AMC_SESSION_GENERATION")).hexdigest()


def verify_config(db):
    row = db.execute(text("SELECT * FROM amc_acl.session_config()")).one()
    if tuple(row) != (hashlib.sha256(key("AMC_QUOTA_KEY")).hexdigest(), generation()):
        raise HTTPException(503, "Session or quota configuration differs from the publisher")
