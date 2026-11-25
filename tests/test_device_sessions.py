"""Synthetic device sessions across requests, SQL connections and API workers."""

from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
import os
from threading import Event
from uuid import uuid4

import jwt
import psycopg
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import set_context
from app.database import engine
from app.models import Client
from fastapi import HTTPException
from identity_fixtures import start_registration, verify_registration
from app.device_api import CSRF, REFRESH
from app.security import ISSUER, SECRET, sign_actor
from app.session_state import DeviceSession, verify_access


def signup(api):
    body = {"email": f"{uuid4().hex}@example.com", "password": uuid4().hex}
    assert api.post("/api/auth/register", json=body).status_code == 202
    return body


def login(api, body):
    res = api.post("/api/auth/login", json=body)
    assert res.is_success, res.text
    jar = SimpleCookie()
    for raw in res.headers.get_list("set-cookie"):
        jar.load(raw)
    access = res.json()["access_token"]
    sid = jwt.decode(access, SECRET, algorithms=["HS256"], audience="amc-api", issuer=ISSUER)["sid"]
    grant = jar[REFRESH + sid]
    assert grant["secure"] and grant["httponly"] and grant["samesite"] == "lax" and not grant["domain"]
    cookie = "; ".join(f"{k}={p.value}" for k, p in jar.items())
    return access, {"Cookie": cookie, "X-AMC-CSRF": jar[CSRF + sid].value, "X-AMC-Session": sid, "Origin": str(api.base_url).rstrip("/")}


def bearer(token):
    return {"Authorization": "Bearer " + token}


def test_device_owner_logout_and_legacy_cutover(api):
    account = signup(api)
    one, _ = login(api, account)
    two, _ = login(api, account)
    stranger, _ = login(api, signup(api))
    devices = api.get("/api/me/sessions", headers=bearer(one)).json()
    assert len(devices) == 2 and sum(d["current"] for d in devices) == 1
    other = next(d["id"] for d in devices if not d["current"])
    assert api.delete("/api/me/sessions/" + other, headers=bearer(stranger)).status_code == 404
    reauth = api.post("/api/auth/reauthenticate", headers=bearer(one), json={"password": account["password"]})
    assert reauth.status_code == 204, reauth.text
    assert api.delete("/api/me/sessions/" + other, headers=bearer(one)).status_code == 204
    assert api.get("/api/me", headers=bearer(two)).status_code == 401
    assert api.get("/api/me", headers=bearer(one)).status_code == 200
    claims = jwt.decode(one, SECRET, algorithms=["HS256"], audience="amc-api", issuer=ISSUER)
    assert claims["exp"] - claims["iat"] <= 300
    for field in ("sid", "ce", "se"):
        claims.pop(field)
    assert api.get("/api/me", headers=bearer(jwt.encode(claims, SECRET, algorithm="HS256"))).status_code == 401
    assert api.post("/api/auth/logout", headers=bearer(one)).status_code == 204
    assert api.get("/api/me", headers=bearer(one)).status_code == 401


def test_refresh_response_loss_reuse_and_csrf(api):
    token, proof = login(api, signup(api))
    for altered in ({"Origin": "https://invalid.example"}, {"X-AMC-CSRF": "wrong"}):
        assert api.post("/api/auth/refresh", headers=proof | altered).status_code == 403
    fresh = api.post("/api/auth/refresh", headers=proof)
    assert fresh.is_success, fresh.text
    assert api.post("/api/auth/refresh", headers=proof).status_code == 401
    for access in (token, fresh.json()["access_token"]):
        assert api.get("/api/me", headers=bearer(access)).status_code == 401


def test_refresh_requires_tab_family_before_grant_consumption(api):
    first, a = login(api, signup(api))
    second, b = login(api, signup(api))
    def mismatch(proof):
        headers = dict(b)
        headers.update(proof)
        response = api.post("/api/auth/refresh", headers=headers)
        assert response.status_code == 409 and "set-cookie" not in response.headers

    mismatch({"X-AMC-Session": ""})
    mismatch({"X-AMC-Session": a["X-AMC-Session"]})
    ok = api.post("/api/auth/refresh", headers=b)
    assert ok.is_success
    mismatch({"X-AMC-Session": a["X-AMC-Session"]})  # Even a spent B grant cannot revoke B on this mismatch.
    for token in (first, second, ok.json()["access_token"]):
        assert api.get("/api/me", headers=bearer(token)).is_success


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires disposable PostgreSQL")
def test_wrong_tab_leaves_postgres_family_and_history_unchanged(api):
    if str(api.base_url).rstrip("/") == "http://testserver":
        pytest.skip("PostgreSQL storage assertions")
    _, a = login(api, signup(api))
    _, b = login(api, signup(api))
    def snapshot():
        with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
            return owner.execute(
                "SELECT d.id,d.current_digest,d.seen,d.revoked,d.epoch, "
                "(SELECT count(*) FROM used_refresh_grants u WHERE u.session_id=d.id) "
                "FROM device_sessions d WHERE d.id IN (%s,%s) ORDER BY d.id",
                (a["X-AMC-Session"], b["X-AMC-Session"]),
            ).fetchall()
    before = snapshot()
    assert len(before) == 2
    for path in ("refresh", "logout-cookie"):
        response = api.post("/api/auth/" + path, headers=b | {"X-AMC-Session": a["X-AMC-Session"]})
        assert response.status_code == 409 and "set-cookie" not in response.headers
    assert snapshot() == before
    assert api.post("/api/auth/refresh", headers=b).is_success
    assert snapshot() != before


def test_logout_of_expired_browser_access_with_live_cookie(api):
    token, proof = login(api, signup(api))
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], audience="amc-api", issuer=ISSUER)
    expired = jwt.encode(dict(claims, iat=claims["iat"] - 600, exp=claims["iat"] - 300), SECRET, algorithm="HS256")
    assert api.post("/api/auth/logout", headers=bearer(expired)).status_code == 401
    target = proof | {"X-AMC-Session": claims["sid"]}
    assert api.post("/api/auth/logout-cookie", headers=target | {"X-AMC-Session": str(uuid4())}).status_code == 409
    assert api.post("/api/auth/logout-cookie", headers=target).status_code == 204
    assert api.post("/api/auth/logout-cookie", headers=target).status_code == 204
    assert api.post("/api/auth/refresh", headers=proof).status_code == 401


def test_old_tab_revokes_its_bearer_and_leaves_new_browser_cookie(api):
    first, _ = login(api, signup(api))
    second, other_cookie = login(api, signup(api))
    response = api.post("/api/auth/logout", headers=bearer(first) | {"Cookie": other_cookie["Cookie"]})
    assert response.status_code == 204 and "set-cookie" not in response.headers
    assert api.get("/api/me", headers=bearer(first)).status_code == 401
    assert api.get("/api/me", headers=bearer(second)).is_success
    assert api.post("/api/auth/refresh", headers=other_cookie).is_success


def test_storage_outage_denies_read(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app import session_state

    token, _ = login(client, signup(client))

    def unavailable(*args):
        raise OperationalError("synthetic", {}, Exception("offline"))

    monkeypatch.setattr(session_state, "active", unavailable)
    assert client.get("/api/me", headers=bearer(token)).status_code == 503


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires disposable PostgreSQL")
def test_worker_readiness_does_not_require_end_user_keys(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(repo))
    for name in ("JWT_SECRET", "AMC_DB_PROOF_KEY", "AMC_QUOTA_KEY", "AMC_SESSION_GENERATION"):
        env.pop(name, None)
    code = (
        "from app.workforce_worker import engine,prepare_database; "
        "from app import delivery_models,knowledge_models,session_state; "
        "prepare_database(engine,verify_identity=False)"
    )
    result = subprocess.run([sys.executable, "-c", code], env=env, cwd=tmp_path, capture_output=True, timeout=20)
    assert result.returncode == 0
    blocked = subprocess.run(
        [sys.executable, "-c", "from app.security import access_key; access_key()"], env=env, cwd=tmp_path, capture_output=True, timeout=20
    )
    assert blocked.returncode and b"unique strong JWT_SECRET" in blocked.stderr


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires disposable PostgreSQL")
def test_rotate_proof_preserves_quota_and_switches_every_consumer():
    import hashlib
    import hmac
    import secrets
    from migrations.apply import maintain_identity

    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
        before = owner.execute("SELECT * FROM amc_acl.session_keys").fetchone()
        old = bytes.fromhex(os.environ["AMC_DB_PROOF_KEY"])
        new = secrets.token_bytes(32)
        uid = str(uuid4())
        owner.execute("SELECT set_config('amc.user_id',%s,true)", (uid,))
        tx = owner.execute("SELECT txid_current()").fetchone()[0]

        def results(key):
            def tag(message):
                return hmac.digest(key, message.encode(), "sha256").hex()

            digest = hashlib.sha256(b"synthetic-token").hexdigest()
            owner.execute(
                "SELECT set_config('amc.identity_proof',%s,true),set_config('amc.challenge_proof',%s,true)",
                (tag(f"{uid}:{tx}"), tag(f"challenge:issue:{uid}:{tx}:{digest}")),
            )
            return owner.execute(
                """SELECT amc_acl.authenticated_actor(),amc_acl.challenge_authorized('issue',%s),
                 amc_acl.valid_knowledge_append('knowledge_commands','{}',%s)""",
                (digest, tag(f"knowledge-v22\n{uid}\n{tx}\nknowledge_commands\n{{}}")),
            ).fetchone()

        assert results(old) == (True, True, True)
        maintain_identity(owner, "rotate-proof", new.hex())
        assert results(old) == (False, False, False)
        assert results(new) == (True, True, True)
        assert before == owner.execute("SELECT * FROM amc_acl.session_keys").fetchone()
        with pytest.raises(ValueError, match="reused"):
            maintain_identity(owner, "rotate-proof", os.environ["AMC_QUOTA_KEY"])
        owner.rollback()


@pytest.mark.skipif(os.getenv("AMC_TEST_PG") != "1", reason="requires disposable PostgreSQL")
def test_two_workers_commit_orders_and_credential_change(api):
    if str(api.base_url).rstrip("/") == "http://testserver":
        pytest.skip("real HTTP and PostgreSQL case")
    import httpx
    import socket
    import subprocess
    import sys
    import time

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--no-proxy-headers",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
            "--no-access-log",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ) as server:
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=8, trust_env=False) as second:
                for _ in range(150):
                    assert server.poll() is None, "isolated API worker exited during startup"
                    try:
                        if second.get("/api/health").is_success:
                            break
                    except httpx.ConnectError:
                        pass
                    time.sleep(0.05)
                else:
                    pytest.fail("isolated API worker did not become healthy")
                account = {"email": f"{uuid4().hex}@example.com", "password": uuid4().hex}
                registered = start_registration(api, **account, organization_name="Session ordering lab", mode="agency")
                verify_registration(api, account["email"], registered)
                tenant = registered["tenant_id"]
                token, proof = login(api, account)
                claims = jwt.decode(token, SECRET, algorithms=["HS256"], audience="amc-api", issuer=ISSUER)
                uid = claims["sub"]
                with Session(engine) as bare:
                    set_context(bare, actor=uid)
                    assert bare.scalar(select(DeviceSession.id).where(DeviceSession.id == claims["sid"])) is None
                # Two tabs reaching different API listeners share one durable family.
                with ThreadPoolExecutor(max_workers=2) as pool:
                    attempts = [pool.submit(c.post, "/api/auth/refresh", headers=proof | {"Origin": str(c.base_url).rstrip("/")}) for c in (api, second)]
                    assert sorted(x.result().status_code for x in attempts) == [200, 401]
                assert second.get("/api/me", headers=bearer(token)).status_code == 401
                token, _ = login(api, account)
                claims = jwt.decode(token, SECRET, algorithms=["HS256"], audience="amc-api", issuer=ISSUER)
                with Session(engine) as pending:
                    set_context(pending, actor=uid, tenant=tenant)
                    sign_actor(pending, uid)
                    pending.info["amc_access_session"] = claims
                    verify_access(pending, claims)
                    denied_id = str(uuid4())
                    pending.add(Client(id=denied_id, tenant_id=tenant, name="Uncommitted fixture client"))
                    pending.flush()
                    assert second.post("/api/auth/logout", headers=bearer(token)).status_code == 204
                    with pytest.raises(HTTPException) as revoked:
                        pending.commit()
                    assert revoked.value.status_code == 401
                    pending.rollback()
                    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as observer:
                        assert observer.execute("SELECT id FROM clients WHERE id=%s", (denied_id,)).fetchone() is None
                token, _ = login(api, account)
                claims = jwt.decode(token, SECRET, algorithms=["HS256"], audience="amc-api", issuer=ISSUER)
                signal = Event()

                def retire():
                    signal.set()
                    return second.post("/api/auth/logout", headers=bearer(token)).status_code

                with ThreadPoolExecutor(max_workers=1) as pool, Session(engine) as first:
                    set_context(first, actor=uid, tenant=tenant)
                    sign_actor(first, uid)
                    first.info["amc_access_session"] = claims
                    verify_access(first, claims, commit=True)
                    allowed_id = str(uuid4())
                    first.add(Client(id=allowed_id, tenant_id=tenant, name="Committed fixture client"))
                    future = pool.submit(retire)
                    assert signal.wait(2)
                    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"], autocommit=True) as observer:
                        for _ in range(100):
                            waiting = observer.execute(
                                """SELECT EXISTS(SELECT FROM pg_locks WHERE locktype='advisory' AND NOT granted
                                AND database=(SELECT oid FROM pg_database WHERE datname=current_database())
                                AND classid=(hashtextextended(%s,23001)>>32)::int::oid AND objid=hashtextextended(%s,23001)::bit(32)::int::oid)""",
                                (uid, uid),
                            ).fetchone()[0]
                            if waiting:
                                break
                            time.sleep(0.02)
                        assert waiting, "revocation must wait for the already authorized commit"
                    first.commit()
                    assert future.result(timeout=8) == 204
                    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as observer:
                        assert observer.execute("SELECT id FROM clients WHERE id=%s", (allowed_id,)).fetchone() == (allowed_id,)
                assert api.get("/api/me", headers=bearer(token)).status_code == 401
                one, _ = login(api, account)
                two, _ = login(second, account)
                with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
                    owner.execute("UPDATE users SET password_hash=%s WHERE id=%s", ("synthetic-credential-replaced", uid))
                assert api.get("/api/me", headers=bearer(one)).status_code == 401
                assert second.get("/api/me", headers=bearer(two)).status_code == 401
        finally:
            server.terminate()
            server.wait(timeout=10)
