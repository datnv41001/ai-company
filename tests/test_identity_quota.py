"""Synthetic API acceptance and independent database sessions for fixed-window admission."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from starlette.requests import Request

from agency_fixtures import account
from identity_fixtures import capture, start_registration
from app import identity_quota as quota
from app.database import Base, engine


def peer(ip="192.0.2.15", headers=()):
    return Request({"type": "http", "client": (ip, 8000), "headers": headers})


def email():
    return f"fixture-{uuid4().hex}@example.com"


def check_cooldown(response, maximum):
    assert response.status_code == 429
    assert 0 < int(response.headers["retry-after"]) <= maximum
    assert response.headers["cache-control"] == "no-store"


def test_generic_registration_and_login(api):
    address = email()
    original = uuid4().hex

    def register(password):
        return api.post("/api/auth/register", json={"email": address, "password": password})

    first = register(original)
    token = capture(address)
    alternative = uuid4().hex
    second = register(alternative)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json() == {"status": "accepted"}
    assert capture(address) == token

    def login(address, password):
        return api.post("/api/auth/login", json={"email": address, "password": password})

    unknown = login(email(), alternative)
    wrong = login(address, alternative)
    assert unknown.status_code == wrong.status_code == 401 and unknown.json() == wrong.json()
    assert login(address, original).is_success
    for _ in range(2):
        assert register(alternative).status_code == 202
    check_cooldown(register(alternative), 600)
    for _ in range(10):
        assert login(address, alternative).status_code == 401
    check_cooldown(login(address, original), 60)
    assert login(email(), alternative).status_code == 401


def test_verification_scopes_and_no_new_mail_on_denial(api):
    address = email()
    user = start_registration(api, address, uuid4().hex)
    h = {"Authorization": "Bearer " + user["access_token"]}
    for _ in range(4):
        assert api.post("/api/auth/request-verification", headers=h).status_code == 204
    last = capture(address)
    check_cooldown(api.post("/api/auth/request-verification", headers=h), 300)
    assert capture(address) == last
    for _ in range(10):
        assert api.post("/api/auth/verify-email", headers=h, json={"token": "a" * 43}).status_code == 400
    check_cooldown(api.post("/api/auth/verify-email", headers=h, json={"token": last}), 300)
    other = start_registration(api, email(), uuid4().hex)
    assert api.post("/api/auth/request-verification", headers={"Authorization": "Bearer " + other["access_token"]}).status_code == 204


def test_invite_and_resend_share_recipient_quota_per_tenant(api):
    owner = account(api, "QuotaOwner")
    other = account(api, "OtherQuotaOwner")
    payload = {"email": email(), "role": "editor"}
    path = f"/api/tenants/{owner['tenant']}/invitations"
    created = api.post(path, headers=owner["headers"], json=payload)
    assert created.status_code == 201
    for _ in range(5):
        created = api.post(path + "/" + created.json()["id"] + "/resend", headers=owner["headers"])
        assert created.status_code == 201
    iid = created.json()["id"]
    check_cooldown(api.post(path + "/" + iid + "/resend", headers=owner["headers"]), 600)
    check_cooldown(api.post(path, headers=owner["headers"], json=payload), 600)
    listed = api.get(path, headers=owner["headers"]).json()
    assert any(row["id"] == iid and row["state"] == "pending" for row in listed)
    assert api.post(f"/api/tenants/{other['tenant']}/invitations", headers=other["headers"], json=payload).status_code == 201


def test_only_configured_transport_peer_can_supply_single_ip(monkeypatch):
    monkeypatch.setattr(quota, "TRUSTED_PROXIES", quota.trusted_proxies("192.0.2.80/32"))
    headers = [(b"x-real-ip", b"198.51.100.22"), (b"x-forwarded-for", b"203.0.113.1")]
    assert quota.origin(peer(headers=headers)) == "192.0.2.15"
    assert quota.origin(peer("192.0.2.80", headers)) == "198.51.100.22"
    assert quota.origin(peer("192.0.2.80", headers + [headers[0]])) == "192.0.2.80"
    assert quota.origin(peer("2001:db8::2")) == quota.origin(peer("2001:db8::77")) == "2001:db8::/64"
    with pytest.raises(ValueError):
        quota.trusted_proxies("invalid")


@pytest.mark.parametrize("provider", ["sqlite", "postgres"])
def test_durable_concurrent_admission_and_expiration(provider, tmp_path, caplog):
    import logging

    caplog.set_level(logging.INFO, logger=quota.LOG.name)
    if provider == "postgres":
        if os.getenv("AMC_TEST_PG") != "1":
            pytest.skip("Requires a disposable PostgreSQL runtime")
        database = engine
    else:
        database = create_engine("sqlite:///" + str(tmp_path / "quota.sqlite3"))
        Base.metadata.create_all(database)
    address = email()

    def charge(_):
        with Session(database) as db:
            try:
                quota.admit(db, peer(), "register", address=address)
                return 0
            except HTTPException as exc:
                assert exc.status_code == 429
                return int(exc.headers["Retry-After"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        delays = list(pool.map(charge, range(10)))
    assert Counter(value == 0 for value in delays) == {True: 4, False: 6}
    assert all(0 <= x <= 600 for x in delays)
    assert "action=register" in caplog.text and address not in caplog.text
    if provider == "sqlite":
        with database.begin() as conn:
            rows = conn.execute(text("select digest,used,denied from identity_windows_dev where dimension='address'")).all()
            assert len(rows) == 1 and len(rows[0][0]) == 64 and rows[0][1:] == (4, 6)
            conn.execute(text("update identity_windows_dev set until_epoch=0"))
        assert charge(0) == 0
        database.dispose()
    else:
        import hashlib
        import hmac
        import json
        import psycopg

        assert database.url.database.startswith("amc_test")
        digest = hmac.new(quota.KEY, json.dumps(["register", "address", address], separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
            assert owner.execute("select used,denied from amc_acl.identity_windows where digest=%s", (digest,)).fetchone() == (4, 6)
            owner.execute("update amc_acl.identity_windows set until_epoch=0 where digest=%s", (digest,))
        assert charge(0) == 0
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
            assert owner.execute("select used,denied from amc_acl.identity_windows where digest=%s", (digest,)).fetchone() == (1, 0)
        with database.connect() as conn:
            assert not conn.scalar(text("select has_table_privilege(current_user,'amc_acl.identity_windows','SELECT,UPDATE,DELETE')"))
            assert not conn.scalar(text("select has_table_privilege(current_user,'amc_acl.quota_policy','UPDATE')"))


def test_quota_storage_outage_returns_retry_without_business_mutations(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def offline(*args):
        raise OperationalError("unavailable", {}, Exception("synthetic"))

    with monkeypatch.context() as patch:
        patch.setattr(quota, "sqlite_charge", offline)
        address = email()
        original = uuid4().hex
        response = client.post("/api/auth/register", json={"email": address, "password": original})
        assert response.status_code == 503 and int(response.headers["retry-after"]) > 0
    assert client.post("/api/auth/login", json={"email": address, "password": original}).status_code == 401


def test_registration_mailbox_outage_is_generic_and_recoverable(api, monkeypatch, caplog):
    from app import identity

    existing, fresh = email(), email()
    password = uuid4().hex

    def register(address):
        return api.post("/api/auth/register", json={"email": address, "password": password})

    assert register(existing).status_code == 202
    original = capture(existing)

    def offline(*args):
        raise OSError("synthetic mailbox outage")

    with monkeypatch.context() as patch:
        patch.setattr(identity, "deliver", offline)
        known, unknown = register(existing), register(fresh)
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json() == {"status": "accepted"}
    assert capture(existing) == original
    assert "identity_delivery_unavailable action=register" in caplog.text and fresh not in caplog.text
    assert api.post("/api/auth/login", json={"email": fresh, "password": password}).status_code == 401
    assert register(fresh).status_code == 202
    assert api.post("/api/auth/login", json={"email": fresh, "password": password}).status_code == 200


def test_native_dotenv_loads_trusted_peer(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    (tmp_path / ".env").write_text("AMC_IDENTITY_TRUSTED_PROXIES=192.0.2.80/32\n", encoding="utf8")
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]), DATABASE_URL="sqlite://")
    env.pop("AMC_IDENTITY_TRUSTED_PROXIES", None)
    subprocess.run(
        [sys.executable, "-c", "from app.identity_quota import TRUSTED_PROXIES; assert [str(item) for item in TRUSTED_PROXIES] == ['192.0.2.80/32']"],
        check=True,
        cwd=tmp_path,
        env=env,
    )


def test_login_rejects_oversize_password_before_hashing(client, monkeypatch):
    from app import main

    def unexpected(*args):
        pytest.fail("Verifier called outside the registered credential contract")

    monkeypatch.setattr(main, "check_password", unexpected)
    oversized = "synthetic-password-" * 8
    response = client.post("/api/auth/login", json={"email": email(), "password": oversized})
    assert response.status_code == 422 and oversized not in response.text


@pytest.mark.parametrize("provider", ["sqlite", "postgres"])
def test_one_origin_keeps_its_limit_across_distinct_addresses(provider, tmp_path):
    if provider == "postgres":
        if os.getenv("AMC_TEST_PG") != "1":
            pytest.skip("Requires disposable PostgreSQL")
        database = engine
    else:
        database = create_engine("sqlite:///" + str(tmp_path / "origin.sqlite3"))
        Base.metadata.create_all(database)
    limit, seconds = quota.POLICY["register"]["origin"]
    request = peer("2001:db8:45:15::1")
    with Session(database) as db:
        for _ in range(limit):
            quota.admit(db, request, "register", address=email())
        with pytest.raises(HTTPException) as denied:
            quota.admit(db, request, "register", address=email())
        assert denied.value.status_code == 429
        assert 0 < int(denied.value.headers["Retry-After"]) <= seconds
        quota.admit(db, peer("2001:db8:45:16::1"), "register", address=email())
    if provider == "sqlite":
        database.dispose()
