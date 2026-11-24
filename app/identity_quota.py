"""Admission for public identity commands. Charge attempts before the business transaction."""

import hashlib
import hmac
import ipaddress
import json
import logging
import os
from pathlib import Path
import time

from fastapi import HTTPException
from sqlalchemy import BigInteger, Column, Index, Integer, MetaData, String, Table, event, text
from sqlalchemy.exc import SQLAlchemyError

from .database import Base
from .security import SECRET, sign_actor

POLICY = json.loads((Path(__file__).resolve().parents[1] / "migrations/021_quota_policy.json").read_text(encoding="utf-8"))
KEY = hmac.digest(SECRET.encode(), b"amc/identity-quota/v1", "sha256")
LOG = logging.getLogger("amc.identity_limits")
# SQLite keeps development counters separately from the tenant-domain schema.
DEV_WINDOWS = Table(
    "identity_windows_dev",
    MetaData(),
    Column("digest", String(64), primary_key=True),
    Column("action", String, nullable=False),
    Column("dimension", String, nullable=False),
    Column("until_epoch", BigInteger, nullable=False),
    Column("used", Integer, nullable=False),
    Column("denied", BigInteger, nullable=False),
    Index("identity_window_dev_expiry", "until_epoch"),
)


@event.listens_for(Base.metadata, "after_create")
def create_dev_counters(metadata, connection, **kwargs):
    if connection.dialect.name == "sqlite":
        DEV_WINDOWS.create(connection, checkfirst=True)


def trusted_proxies(value):
    return tuple(ipaddress.ip_network(item.strip()) for item in value.split(",") if item.strip())


TRUSTED_PROXIES = trusted_proxies(os.getenv("AMC_IDENTITY_TRUSTED_PROXIES", ""))


def origin(request):
    peer = request.client.host if request.client else ""
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return "unknown-peer"
    # Supported launchers disable Uvicorn's header rewriting. A configured
    # immediate proxy must overwrite X-Real-IP with one validated client IP.
    if any(address in network for network in TRUSTED_PROXIES):
        forwarded = request.headers.getlist("x-real-ip")
        if len(forwarded) == 1:
            try:
                address = ipaddress.ip_address(forwarded[0])
            except ValueError:
                pass
    if address.version == 6:
        if address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network((address, 64), strict=False))
    return str(address)


def sqlite_charge(db, action, keys):
    conn = db.connection()
    if not conn.connection.driver_connection.in_transaction:
        conn.exec_driver_sql("BEGIN IMMEDIATE")
    stamp = int(time.time())
    rows = []
    for dimension, (limit, seconds) in POLICY[action].items():
        key = keys[dimension]
        row = conn.exec_driver_sql("SELECT until_epoch,used FROM identity_windows_dev WHERE digest=?", (key,)).first()
        rows.append((dimension, key, limit, seconds, row))
    blocked = [(key, row[0] - stamp) for _, key, limit, _, row in rows if row and row[0] > stamp and row[1] >= limit]
    for key, _ in blocked:
        conn.exec_driver_sql("UPDATE identity_windows_dev SET denied=denied+1 WHERE digest=?", (key,))
    if not blocked:
        for dimension, key, _, seconds, row in rows:
            if row and row[0] > stamp:
                conn.exec_driver_sql("UPDATE identity_windows_dev SET used=used+1 WHERE digest=?", (key,))
            else:
                conn.exec_driver_sql("INSERT OR REPLACE INTO identity_windows_dev VALUES(?,?,?,?,1,0)", (key, action, dimension, stamp + seconds))
    conn.exec_driver_sql(
        """DELETE FROM identity_windows_dev WHERE digest IN (SELECT digest FROM identity_windows_dev
                            WHERE until_epoch<? ORDER BY until_epoch LIMIT 64)""",
        (stamp - 86400,),
    )
    return max((delay for _, delay in blocked), default=0)


def admit(db, request, action, *, actor=None, address=None, tenant=None):
    ip = origin(request)
    subjects = {"origin": [ip], "account": [actor], "address": [address], "origin_address": [ip, address], "tenant": [tenant], "recipient": [tenant, address]}
    keys = {}
    for scope in POLICY[action]:
        values = subjects[scope]
        if not all(values):
            raise ValueError("Incomplete identity quota scope")
        encoded = json.dumps([action, scope, *values], ensure_ascii=False, separators=(",", ":")).encode()
        keys[scope] = hmac.new(KEY, encoded, hashlib.sha256).hexdigest()
    # No business mutation may precede this commit. Failed logins and failed
    # mailbox delivery must consume their attempts across workers and restarts.
    if db.new or db.dirty or db.deleted:
        raise RuntimeError("Identity admission requires a clean transaction")
    try:
        if db.get_bind().dialect.name == "postgresql":
            delay = db.scalar(text("SELECT amc_acl.consume_identity_quota(:a,cast(:keys as jsonb))"), {"a": action, "keys": json.dumps(keys)})
        else:
            delay = sqlite_charge(db, action, keys)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        LOG.error("identity_admission_unavailable action=%s", action)
        raise HTTPException(503, "Temporary service interruption", headers={"Retry-After": "5", "Cache-Control": "no-store"}) from None
    if delay:
        LOG.info("identity_admission_limited action=%s retry_after=%d", action, delay)
        raise HTTPException(429, "Vui lòng thử lại sau.", headers={"Retry-After": str(delay), "Cache-Control": "no-store"})
    if actor:
        sign_actor(db, actor)
