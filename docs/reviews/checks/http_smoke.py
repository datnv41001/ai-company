import json
import os
import socket
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

import uvicorn

def main():
    with tempfile.TemporaryDirectory() as tmp, socket.socket() as sock:
        os.environ.update(APP_ENV="local", OPENAI_API_KEY="", JWT_SECRET=os.urandom(48).hex(),
                          DATABASE_URL="sqlite:///" + (Path(tmp) / "smoke.db").as_posix())
        from app.database import engine
        from app.main import app
        sock.bind(("127.0.0.1", 0))
        base = "http://127.0.0.1:" + str(sock.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [sock]})
        worker.start()
        try:
            for _ in range(150):
                if server.started:
                    break
                time.sleep(0.05)
            assert server.started
            for path in ["/", "/docs", "/openapi.json", "/api/health"]:
                with urlopen(base + path, timeout=5) as r:
                    assert r.status == 200
                    if path == "/api/health":
                        assert json.load(r)["production_ready"] is False
                    print(path, r.status)
            body = {"email": "local-review@example.com", "password": os.urandom(18).hex(),
                    "organization_name": "Local review", "mode": "inhouse"}
            request = Request(base + "/api/auth/register", data=json.dumps(body).encode(),
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=5) as r:
                assert r.status == 201
                account = json.load(r)
                print("register", r.status)
            path = "/api/tenants/" + account["tenant_id"] + "/clients"
            with urlopen(Request(base + path, headers={"Authorization": "Bearer " + account["access_token"]}), timeout=5) as r:
                assert [x["name"] for x in json.load(r)] == ["Internal Marketing"]
                print("inhouse clients", r.status, "Internal Marketing")
        finally:
            server.should_exit = True
            worker.join(10)
            assert not worker.is_alive()
            engine.dispose()

if __name__ == "__main__":
    main()
