"""Start the Windows development instance with native PostgreSQL and loopback HTTP."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import psycopg
from psycopg.conninfo import make_conninfo


ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
DB_PORT = 55432
API_PORT = 8000


def listening(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, port)) == 0


def hidden_process(command, log, env):
    with log.open("ab") as output:
        return subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                stdout=output, stderr=output, creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, help="Directory containing postgres.exe and initdb.exe")
    parser.add_argument("--state", type=Path, default=ROOT / ".local", help="Persistent private local instance directory")
    args = parser.parse_args()
    state = args.state.resolve()
    pg_bin = args.pg_bin
    if pg_bin is None:
        binary = shutil.which("postgres.exe")
        if not binary:
            parser.error("Pass --pg-bin pointing to your PostgreSQL bin directory")
        pg_bin = Path(binary).parent
    pg_bin = pg_bin.resolve()
    state.mkdir(parents=True, exist_ok=True)
    conf = state / "local-secrets.json"
    data = state / "pgdata"
    if not conf.exists():
        if data.exists():
            raise RuntimeError("Existing cluster requires its original local-secrets.json")
        with conf.open("x", encoding="utf-8") as f:
            json.dump({key: secrets.token_hex(40) for key in ("owner", "runtime", "jwt")}, f)
    keys = json.loads(conf.read_text(encoding="utf-8"))
    flags = subprocess.CREATE_NO_WINDOW
    if not (data / "PG_VERSION").exists():
        pwfile = state / "initdb-password.tmp"
        try:
            pwfile.write_text(keys["owner"], encoding="ascii")
            subprocess.run([pg_bin / "initdb.exe", "-D", data, "-U", "amc_local_owner", "-A", "scram-sha-256",
                            "--encoding=UTF8", "--locale=C", "--pwfile", pwfile], check=True, creationflags=flags)
        finally:
            pwfile.unlink(missing_ok=True)
    owner = make_conninfo(host=HOST, port=DB_PORT, user="amc_local_owner", password=keys["owner"], dbname="postgres", connect_timeout=2)
    if not listening(DB_PORT):
        db_process = hidden_process([pg_bin / "postgres.exe", "-D", data, "-h", HOST, "-p", str(DB_PORT)], state / "postgres.log", os.environ.copy())
        for _ in range(100):
            if db_process.poll() is not None:
                raise RuntimeError("PostgreSQL stopped during startup. See postgres.log")
            if listening(DB_PORT):
                break
            time.sleep(0.1)
    for attempt in range(30):
        try:
            conn = psycopg.connect(owner, autocommit=True)
            break
        except psycopg.OperationalError:
            if attempt == 29:
                raise
            time.sleep(0.2)
    with conn:
        if Path(conn.execute("SHOW data_directory").fetchone()[0]).resolve() != data:
            raise RuntimeError("Port 55432 belongs to a different PostgreSQL cluster")
        if conn.execute("SELECT 1 FROM pg_database WHERE datname='amc_local'").fetchone() is None:
            conn.execute("CREATE DATABASE amc_local")
    migration_env = dict(os.environ, AMC_MIGRATION_DSN=make_conninfo(owner, dbname="amc_local"),
                         AMC_RUNTIME_PASSWORD=keys["runtime"], JWT_SECRET=keys["jwt"])
    subprocess.run([sys.executable, "migrations/apply.py"], cwd=ROOT, env=migration_env, check=True, creationflags=flags)
    pidfile = state / "api.pid"
    if listening(API_PORT):
        listing = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, creationflags=flags)
        expected_pid = pidfile.read_text().strip() if pidfile.exists() else ""
        if not any(len(parts) == 5 and parts[1] == f"{HOST}:{API_PORT}" and parts[2] == "0.0.0.0:0"
                   and parts[4] == expected_pid for parts in map(str.split, listing.splitlines())):
            raise RuntimeError("Port 8000 is already in use by another service")
    else:
        api_env = dict(os.environ, APP_ENV="development", JWT_SECRET=keys["jwt"],
                       DATABASE_URL=f"postgresql+psycopg://amc_runtime:{keys['runtime']}@{HOST}:{DB_PORT}/amc_local")
        for name in ("AMC_MIGRATION_DSN", "POSTGRES_PASSWORD", "AMC_RUNTIME_PASSWORD", "OPENAI_API_KEY", "AMC_WORKER_KEY_FILE"):
            api_env.pop(name, None)
        # python.exe from a Windows venv can be a redirector. The server records its actual PID.
        hidden_process([sys.executable, str(Path(__file__).resolve()), "--serve", str(pidfile)], state / "api.log", api_env)
    for _ in range(100):
        try:
            with urlopen(f"http://{HOST}:{API_PORT}/api/health", timeout=1) as r:
                if json.load(r).get("stage") == "engineering_bootstrap":
                    print(f"Ready at http://{HOST}:{API_PORT} (PostgreSQL {DB_PORT})")
                    return
        except OSError:
            pass
        time.sleep(0.15)
    raise RuntimeError("API startup failed. See api.log")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--serve"]:
        import uvicorn
        sys.path.insert(0, str(ROOT))
        Path(sys.argv[2]).write_text(str(os.getpid()), encoding="ascii")
        uvicorn.run("app.main:app", host=HOST, port=API_PORT, access_log=False, proxy_headers=False)
    else:
        main()
