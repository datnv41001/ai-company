"""Exercise the actual eff86cda predecessor against the same private acceptance database."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from check_c3_cutover import unpack


PIN = "eff86cda2f99dd10244dc8127451e941bb546a3c"
CLIENT = """
import json, sys
from pathlib import Path
from fastapi.testclient import TestClient
from app import production_studios
from app.main import app
assert Path(production_studios.__file__).resolve().is_relative_to(Path.cwd())
with TestClient(app) as client:
    print("ready", flush=True)
    for line in sys.stdin:
        cmd=json.loads(line)
        try:
            r=client.request(**cmd)
            result={"status":r.status_code,"body":r.json()}
        except Exception as e:
            cause=getattr(e,"orig",e)
            result={"status":500,"sqlstate":getattr(cause,"sqlstate",None),
                    "guard":str(cause).splitlines()[0]}
        print(json.dumps(result),flush=True)
"""


@contextmanager
def previous_api():
    with TemporaryDirectory() as tmp:
        old = unpack(PIN, Path(tmp))
        paths = [s for s in os.getenv("PYTHONPATH", "").split(os.pathsep) if s and Path(s).resolve() != Path.cwd()]
        env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(old), *paths])}
        with subprocess.Popen([sys.executable, "-u", "-c", CLIENT], env=env, cwd=old, text=True,
                              encoding="utf-8", stdin=subprocess.PIPE, stdout=subprocess.PIPE) as worker:
            try:
                assert worker.stdout.readline().strip() == "ready"
                def call(method, path, actor, data=None):
                    worker.stdin.write(json.dumps({"method": method, "url": path, "headers": actor["headers"], "json": data}) + "\n")
                    worker.stdin.flush()
                    return json.loads(worker.stdout.readline())
                yield call
            finally:
                worker.stdin.close()
                worker.wait(timeout=30)
