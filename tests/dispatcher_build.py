"""Run one scheduler turn from a separate checkout with only its dispatcher login."""
import json
import os
import subprocess
import sys

PROGRAM = """
import json,sys
from sqlalchemy import create_engine
import psycopg
from app.main import app
from app.pool_dispatch import consume,dispatch
from app.workforce_gateway import Gateway
from migrations.registry_release import adapter_digest
dsn,mode,config=json.load(sys.stdin)
engine=create_engine('postgresql+psycopg://',creator=lambda:psycopg.connect(dsn))
try:
    result={'dispatch':dispatch,'consume':consume}[mode](engine,Gateway(**config))
    print(json.dumps({'worked':result,'digest':adapter_digest()}))
finally:
    engine.dispose()
"""


def turn(path, lab, mode):
    env = {k:v for k,v in os.environ.items() if k.upper() in {"SYSTEMROOT","WINDIR","PATH","TEMP","TMP","HOME","LOCALAPPDATA"}}
    env.update(PYTHONUTF8="1",APP_ENV="local")
    completed = subprocess.run([sys.executable,"-c",PROGRAM],cwd=path,env=env,
        input=json.dumps([lab.logins[0][1],mode,vars(lab.config)]),text=True,capture_output=True,timeout=25)
    if completed.returncode:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)
