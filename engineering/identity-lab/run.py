"""Exercise a new synthetic provider per invocation; log decisions only."""

import base64
import hashlib
import os
import secrets
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

import httpx
import jwt
from playwright.sync_api import sync_playwright


CLIENT = "amc-synthetic-browser"
USERNAME = "synthetic-operator"


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path != "/callback":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(b"Lab callback complete")

    def log_message(self, *args):
        # The callback query contains a one-time authorization code.
        pass


def realm_setup(api, origin, admin_password, user_password, callback):
    admin = api.post(
        origin + "/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": "lab-admin", "password": admin_password},
    )
    admin.raise_for_status()
    headers = {"Authorization": "Bearer " + admin.json()["access_token"]}
    realm = {
        "realm": "amc-lab", "enabled": True, "revokeRefreshToken": True,
        "refreshTokenMaxReuse": 0, "accessTokenLifespan": 240,
        "clients": [{
            "clientId": CLIENT, "protocol": "openid-connect", "publicClient": True,
            "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
            "redirectUris": [callback], "attributes": {"pkce.code.challenge.method": "S256"},
        }],
        "users": [{
            "username": USERNAME, "enabled": True, "email": "operator@example.invalid",
            "emailVerified": True, "firstName": "Synthetic", "lastName": "Operator",
            "credentials": [{"type": "password", "value": user_password, "temporary": False}],
        }],
    }
    api.post(origin + "/admin/realms", headers=headers, json=realm).raise_for_status()
    response = api.get(origin + "/admin/realms/amc-lab/users", headers=headers,
                       params={"username": USERNAME, "exact": "true"})
    response.raise_for_status()
    user, = response.json()
    return headers, user["id"]


def login(api, discovery, password, callback):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    arguments = {"response_type": "code", "scope": "openid", "client_id": CLIENT,
                 "redirect_uri": callback, "code_challenge": challenge, "code_challenge_method": "S256",
                 "state": state, "nonce": nonce}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("AMC_BROWSER_EXECUTABLE") or None)
        try:
            page = browser.new_page()
            page.goto(discovery["authorization_endpoint"] + "?" + urlencode(arguments))
            page.locator("#username").fill(USERNAME)
            page.locator("#password").fill(password)
            page.locator("#kc-login").click()
            page.wait_for_url(lambda uri: uri.partition("?")[0] == callback, timeout=15000)
            query = parse_qs(urlsplit(page.url).query)
        finally:
            browser.close()
    assert query["state"] == [state]
    tokens = api.post(discovery["token_endpoint"], data={
        "grant_type": "authorization_code", "client_id": CLIENT, "code": query["code"][0],
        "code_verifier": verifier, "redirect_uri": callback,
    })
    tokens.raise_for_status()
    result = tokens.json()
    jwks = api.get(discovery["jwks_uri"])
    jwks.raise_for_status()
    key = jwt.PyJWKSet.from_dict(jwks.json())[jwt.get_unverified_header(result["id_token"])["kid"]]
    claims = jwt.decode(result["id_token"], key.key, algorithms=["RS256"],
                        audience=CLIENT, issuer=discovery["issuer"],
                        options={"require": ["sub", "exp", "iat", "nonce"]})
    assert claims["nonce"] == nonce
    return result, claims["sub"]


def experiment(api, origin, admin_password, callback):
    password = secrets.token_urlsafe(32)
    headers, subject = realm_setup(api, origin, admin_password, password, callback)
    issuer = origin + "/realms/amc-lab"
    metadata = api.get(issuer + "/.well-known/openid-configuration")
    metadata.raise_for_status()
    discovery = metadata.json()
    assert discovery["issuer"] == issuer
    assert "S256" in discovery["code_challenge_methods_supported"]
    for endpoint in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        assert discovery[endpoint].startswith(issuer + "/")
    initial, observed_subject = login(api, discovery, password, callback)
    assert observed_subject == subject
    print("PASS browser login, PKCE S256, signature, issuer, audience, state, nonce and subject")

    def refresh(token):
        return api.post(discovery["token_endpoint"], data={
            "grant_type": "refresh_token", "client_id": CLIENT, "refresh_token": token})

    rotated = refresh(initial["refresh_token"])
    rotated.raise_for_status()
    current = rotated.json()["refresh_token"]
    assert current != initial["refresh_token"]
    print("PASS provider issued a different refresh token")
    user_url = origin + "/admin/realms/amc-lab/users/" + subject
    reset_password = secrets.token_urlsafe(32)
    api.put(user_url + "/reset-password", headers=headers,
            json={"type": "password", "value": reset_password, "temporary": False}).raise_for_status()
    after_reset = refresh(current)
    if after_reset.status_code == 200:
        print("OBSERVED existing device could refresh after administrative password reset")
    else:
        assert after_reset.status_code == 400 and after_reset.json().get("error") == "invalid_grant"
        print("OBSERVED provider refused existing device refresh after administrative password reset")
    active, reset_subject = login(api, discovery, reset_password, callback)
    assert reset_subject == subject
    print("PASS new password login preserves issuer and subject")
    api.post(user_url + "/logout", headers=headers).raise_for_status()
    after_logout = refresh(active["refresh_token"])
    assert after_logout.status_code == 400 and after_logout.json().get("error") == "invalid_grant"
    print("PASS administrative logout prevents further refresh at provider")


def main():
    stack = "amc-oidc-lab-" + uuid4().hex[:12]
    env = {**os.environ, "LAB_DB_PASSWORD": secrets.token_urlsafe(36),
           "LAB_ADMIN_PASSWORD": secrets.token_urlsafe(36)}
    command = ["docker", "compose", "-p", stack, "-f", str(Path(__file__).with_name("compose.yaml"))]
    try:
        subprocess.run([*command, "up", "-d"], env=env, check=True)
        binding = subprocess.check_output([*command, "port", "provider", "8080"], env=env, text=True).strip()
        host, port = binding.split(":")
        assert host == "127.0.0.1" and port.isdigit()
        origin = "http://" + binding
        with httpx.Client(trust_env=False, timeout=15) as api:
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                try:
                    if api.get(origin + "/realms/master/.well-known/openid-configuration").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(2)
            else:
                raise RuntimeError("New lab provider did not become ready")
            with ThreadingHTTPServer(("127.0.0.1", 0), CallbackHandler) as server:
                listener = threading.Thread(target=server.serve_forever, daemon=True)
                listener.start()
                try:
                    callback = f"http://127.0.0.1:{server.server_port}/callback"
                    experiment(api, origin, env["LAB_ADMIN_PASSWORD"], callback)
                finally:
                    server.shutdown()
                    listener.join()
    finally:
        subprocess.run([*command, "down", "--volumes"], env=env, check=True)


if __name__ == "__main__":
    main()
