"""Generate distinct URL-safe development secrets, only when .env does not exist."""

import os
from pathlib import Path
from secrets import token_hex

root = Path(__file__).resolve().parents[1]
template = (root / ".env.example").read_text(encoding="utf-8").splitlines()
secret_keys = {"POSTGRES_PASSWORD", "AMC_RUNTIME_PASSWORD", "JWT_SECRET"}
lines = []
for line in template:
    key = line.partition("=")[0]
    lines.append(key + "=" + token_hex(40) if key in secret_keys else line)
try:
    fd = os.open(root / ".env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
except FileExistsError:
    print("Existing .env retained. Use the original passwords for an existing database volume.")
else:
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")
    print("Created .env for local development.")
