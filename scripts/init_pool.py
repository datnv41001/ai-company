"""Generate isolated local service credentials and provision them on the Compose database."""

import argparse
import os
from pathlib import Path
from secrets import token_hex
import subprocess
from urllib.parse import urlsplit

SERVICES = (
    ("AMC_DISPATCH_URL", "amc_ops_dispatch", "amc_dispatch"),
    ("AMC_POOL_ONE_DSN", "amc_ops_one", "amc_pool_worker"),
    ("AMC_POOL_TWO_DSN", "amc_ops_two", "amc_pool_worker"),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="amc-dev")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    settings = root / ".env.pool"
    if not settings.exists():
        with os.fdopen(os.open(settings, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
            for key, user, group in SERVICES:
                scheme = "postgresql+psycopg" if group == "amc_dispatch" else "postgresql"
                print(f"{key}={scheme}://{user}:{token_hex(40)}@db:5432/amc", file=out)
    values = dict(line.strip().split("=", 1) for line in settings.read_text().splitlines() if line.strip())
    for key, user, group in SERVICES:
        password = urlsplit(values[key]).password
        if not password:
            raise ValueError("Invalid dedicated service URL in .env.pool")
        subprocess.run(
            [
                "docker",
                "compose",
                "-p",
                args.project,
                "run",
                "--no-deps",
                "--rm",
                "-T",
                "-e",
                "AMC_POOL_PASSWORD",
                "migrate",
                "python",
                "scripts/provision_pool.py",
                "login",
                user,
                group,
            ],
            cwd=root,
            env={**os.environ, "AMC_POOL_PASSWORD": password},
            check=True,
        )
    print("Three service identities ready. Keep .env.pool with this local database.")


if __name__ == "__main__":
    main()
