"""Receive a synthetic email through the private filesystem, then use the public API."""

import hashlib
import os
from pathlib import Path
import subprocess


def capture(email, project=None, invitation_id=None):
    address = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    if project:
        # The Compose API and the host test runner use different UIDs. Read the
        # private volume as its service account. Never echo captured output.
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                project,
                "exec",
                "-T",
                "api",
                "python",
                "-c",
                "import os,sys; from pathlib import Path; d=Path(os.environ['AMC_DEV_MAILBOX_DIR'])/sys.argv[1]; "
                "p=d/'invitations'/(sys.argv[2]+'.txt') if sys.argv[2] else max(d.glob('*.txt'),key=lambda p:p.stat().st_mtime_ns); "
                "sys.stdout.write(p.read_text())",
                address, invitation_id or "",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    directory = Path(os.getenv("AMC_DEV_MAILBOX_DIR", ".dev-mailbox")) / address
    if invitation_id:
        return (directory / "invitations" / (invitation_id + ".txt")).read_text().strip()
    return max(directory.glob("*.txt"), key=lambda p: p.stat().st_mtime_ns).read_text().strip()


def start_registration(api, email, password, **workspace):
    body = {"email": email, "password": password}
    registered = api.post("/api/auth/register", json={**body, **workspace})
    assert registered.status_code == 202, (registered.status_code, registered.headers.get("Retry-After"))
    assert registered.json() == {"status": "accepted"}
    login = api.post("/api/auth/login", json=body)
    assert login.status_code == 200
    authenticated = login.json()
    return {**authenticated, "tenant_id": authenticated["pending_workspace_id"]}


def verify_registration(api, email, registration, project=None):
    headers = {"Authorization": "Bearer " + registration["access_token"]}
    status = api.post("/api/auth/verify-email", headers=headers, json={"token": capture(email, project)}).status_code
    assert status == 204, status


def invite_member(api, base, owner_headers, recipient_headers, **terms):
    created = api.post(base + "/invitations", headers=owner_headers, json=terms)
    assert created.status_code == 201, created.status_code
    invite = created.json()
    assert invite["state"] == "pending"
    result = api.post("/api/me/invitations/" + invite["id"] + "/accept", headers=recipient_headers)
    assert result.status_code == 204, result.status_code
