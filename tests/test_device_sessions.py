"""Synthetic device sessions across requests, SQL connections and API workers."""

from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
import os
from threading import Event
from uuid import uuid4

import jwt
import psycopg
import pytest
from sqlalchemy.orm import Session

from app.access import set_context
from app.database import engine
from app.models import Client
from fastapi import HTTPException
from identity_fixtures import start_registration, verify_registration
from app.device_api import CSRF, REFRESH
from app.security import ISSUER, SECRET, sign_actor
from app.session_state import verify_access


def signup(api):
    body = {"email":f"{uuid4().hex}@example.com","password":uuid4().hex}
    assert api.post("/api/auth/register",json=body).status_code == 202
    return body


def login(api, body):
    res = api.post("/api/auth/login",json=body)
    assert res.is_success, res.text
    jar = SimpleCookie()
    for raw in res.headers.get_list("set-cookie"):
        jar.load(raw)
    assert jar[REFRESH]["secure"] and jar[REFRESH]["httponly"] and jar[REFRESH]["samesite"]=="lax" and not jar[REFRESH]["domain"]
    cookie = "; ".join(f"{k}={p.value}" for k,p in jar.items())
    return res.json()["access_token"], {"Cookie":cookie, "X-AMC-CSRF":jar[CSRF].value, "Origin":str(api.base_url).rstrip("/")}


def bearer(token):
    return {"Authorization":"Bearer "+token}


def test_device_owner_logout_and_legacy_cutover(api):
    account = signup(api)
    one,_ = login(api,account)
    two,_ = login(api,account)
    stranger,_ = login(api,signup(api))
    devices = api.get("/api/me/sessions",headers=bearer(one)).json()
    assert len(devices)==2 and sum(d["current"] for d in devices)==1
    other = next(d["id"] for d in devices if not d["current"])
    assert api.delete("/api/me/sessions/"+other,headers=bearer(stranger)).status_code==404
    reauth=api.post("/api/auth/reauthenticate",headers=bearer(one),json={"password":account["password"]})
    assert reauth.status_code==204, reauth.text
    assert api.delete("/api/me/sessions/"+other,headers=bearer(one)).status_code==204
    assert api.get("/api/me",headers=bearer(two)).status_code==401
    assert api.get("/api/me",headers=bearer(one)).status_code==200
    claims=jwt.decode(one,SECRET,algorithms=["HS256"],audience="amc-api",issuer=ISSUER)
    assert claims["exp"]-claims["iat"]<=300
    for field in ("sid","ce","se"):
        claims.pop(field)
    assert api.get("/api/me",headers=bearer(jwt.encode(claims,SECRET,algorithm="HS256"))).status_code==401
    assert api.post("/api/auth/logout",headers=bearer(one)).status_code==204
    assert api.get("/api/me",headers=bearer(one)).status_code==401


def test_refresh_response_loss_reuse_and_csrf(api):
    token, proof = login(api,signup(api))
    for altered in ({"Origin":"https://invalid.example"},{"X-AMC-CSRF":"wrong"}):
        assert api.post("/api/auth/refresh",headers=proof|altered).status_code==403
    fresh = api.post("/api/auth/refresh",headers=proof)
    assert fresh.is_success, fresh.text
    assert api.post("/api/auth/refresh",headers=proof).status_code==401
    for access in (token,fresh.json()["access_token"]):
        assert api.get("/api/me",headers=bearer(access)).status_code==401


def test_storage_outage_denies_read(client,monkeypatch):
    from sqlalchemy.exc import OperationalError
    from app import session_state
    token,_ = login(client,signup(client))
    def unavailable(*args):
        raise OperationalError("synthetic",{},Exception("offline"))
    monkeypatch.setattr(session_state,"active",unavailable)
    assert client.get("/api/me",headers=bearer(token)).status_code==503


@pytest.mark.skipif(os.getenv("AMC_TEST_PG")!="1", reason="requires disposable PostgreSQL")
def test_two_workers_commit_orders_and_credential_change(api):
    if str(api.base_url).rstrip("/")=="http://testserver":
        pytest.skip("real HTTP and PostgreSQL case")
    import httpx
    import socket
    import threading
    import time
    import uvicorn
    from app.main import app
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        server = uvicorn.Server(uvicorn.Config(app,log_level="error",access_log=False,proxy_headers=False))
        thread=threading.Thread(target=server.run,kwargs={"sockets":[sock]})
        thread.start()
        try:
            for _ in range(200):
                if server.started:
                    break
                time.sleep(0.025)
            assert server.started
            with httpx.Client(base_url=f"http://127.0.0.1:{sock.getsockname()[1]}",timeout=8,trust_env=False) as second:
                account={"email":f"{uuid4().hex}@example.com","password":uuid4().hex}
                registered = start_registration(api,**account,organization_name="Session ordering lab",mode="agency")
                verify_registration(api,account["email"],registered)
                tenant=registered["tenant_id"]
                token,proof=login(api,account)
                claims=jwt.decode(token,SECRET,algorithms=["HS256"],audience="amc-api",issuer=ISSUER)
                uid=claims["sub"]
                # Two tabs reaching different API listeners share one durable family.
                with ThreadPoolExecutor(max_workers=2) as pool:
                    attempts=[pool.submit(c.post,"/api/auth/refresh",headers=proof|{"Origin":str(c.base_url).rstrip("/")}) for c in (api,second)]
                    assert sorted(x.result().status_code for x in attempts)==[200,401]
                assert second.get("/api/me",headers=bearer(token)).status_code==401
                token,_=login(api,account)
                claims=jwt.decode(token,SECRET,algorithms=["HS256"],audience="amc-api",issuer=ISSUER)
                with Session(engine) as pending:
                    set_context(pending,actor=uid,tenant=tenant)
                    sign_actor(pending,uid)
                    pending.info["amc_access_session"]=claims
                    verify_access(pending,claims)
                    denied_id=str(uuid4())
                    pending.add(Client(id=denied_id,tenant_id=tenant,name="Uncommitted fixture client"))
                    pending.flush()
                    assert second.post("/api/auth/logout",headers=bearer(token)).status_code==204
                    with pytest.raises(HTTPException) as revoked:
                        pending.commit()
                    assert revoked.value.status_code==401
                    pending.rollback()
                    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as observer:
                        assert not observer.execute("SELECT FROM clients WHERE id=%s",(denied_id,)).fetchone()
                token,_=login(api,account)
                claims=jwt.decode(token,SECRET,algorithms=["HS256"],audience="amc-api",issuer=ISSUER)
                signal=Event()
                def retire():
                    signal.set()
                    return second.post("/api/auth/logout",headers=bearer(token)).status_code
                with ThreadPoolExecutor(max_workers=1) as pool, Session(engine) as first:
                    set_context(first,actor=uid,tenant=tenant)
                    sign_actor(first,uid)
                    first.info["amc_access_session"]=claims
                    verify_access(first,claims,commit=True)
                    allowed_id=str(uuid4())
                    first.add(Client(id=allowed_id,tenant_id=tenant,name="Committed fixture client"))
                    future=pool.submit(retire)
                    assert signal.wait(2)
                    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"],autocommit=True) as observer:
                        for _ in range(100):
                            waiting=observer.execute("""SELECT EXISTS(SELECT FROM pg_locks WHERE locktype='advisory' AND NOT granted
                                AND database=(SELECT oid FROM pg_database WHERE datname=current_database())
                                AND classid=(hashtextextended(%s,23001)>>32)::int::oid AND objid=hashtextextended(%s,23001)::bit(32)::int::oid)""",(uid,uid)).fetchone()[0]
                            if waiting:
                                break
                            time.sleep(.02)
                        assert waiting, "revocation must wait for the already authorized commit"
                    first.commit()
                    assert future.result(timeout=8)==204
                    with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as observer:
                        assert observer.execute("SELECT id FROM clients WHERE id=%s",(allowed_id,)).fetchone()==(allowed_id,)
                assert api.get("/api/me",headers=bearer(token)).status_code==401
                one,_=login(api,account)
                two,_=login(second,account)
                with psycopg.connect(os.environ["AMC_MIGRATION_DSN"]) as owner:
                    owner.execute("UPDATE users SET password_hash=%s WHERE id=%s",("synthetic-credential-replaced",uid))
                assert api.get("/api/me",headers=bearer(one)).status_code==401
                assert second.get("/api/me",headers=bearer(two)).status_code==401
        finally:
            server.should_exit=True
            thread.join(10)
