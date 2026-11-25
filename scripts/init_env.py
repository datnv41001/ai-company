"""Generate distinct URL-safe development secrets, only when .env does not exist."""

import os
import hmac
import sys
import tempfile
from pathlib import Path
from secrets import token_hex

root = Path(__file__).resolve().parents[1]
template = (root / ".env.example").read_text(encoding="utf-8").splitlines()
secret_keys = {"POSTGRES_PASSWORD", "AMC_RUNTIME_PASSWORD", "JWT_SECRET"}
session_keys = {"AMC_DB_PROOF_KEY","AMC_QUOTA_KEY","AMC_SESSION_GENERATION"}
lines = []
for line in template:
    key = line.partition("=")[0]
    lines.append(key + "=" + token_hex(32) if key in session_keys else key + "=" + token_hex(40) if key in secret_keys else line)
try:
    fd = os.open(root / ".env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
except FileExistsError:
    if "--upgrade-identity" in sys.argv:
        from dotenv import dotenv_values
        path = root / ".env"
        existing = dotenv_values(path)
        if any(k in existing for k in session_keys) and not all(existing.get(k) for k in session_keys):
            raise ValueError("Partial v23 configuration; restore the authoritative key set")
        if not all(existing.get(k) for k in session_keys):
            prior = existing.get("JWT_SECRET") or ""
            if len(prior)<32 or prior.startswith("REPLACE-"):
                raise ValueError("Original v21/v22 JWT secret required")
            values = {k:token_hex(32) for k in session_keys}
            values["AMC_QUOTA_KEY"] = hmac.digest(prior.encode(),b"amc/identity-quota/v1","sha256").hex()
            fd, staged = tempfile.mkstemp(dir=root,prefix=".env.")
            try:
                with os.fdopen(fd,"wb") as out:
                    out.write(path.read_bytes().rstrip(b"\r\n") + b"\n")
                    out.write("".join(f"{k}={v}\n" for k,v in sorted(values.items())).encode())
                os.replace(staged,path)
            finally:
                Path(staged).unlink(missing_ok=True)
        print("Identity configuration ready.")
    else:
        print("Existing .env retained. Use --upgrade-identity on an offline v21/v22 installation.")
else:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
    print("Created .env for local development.")
