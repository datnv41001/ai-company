"""Rehearse core v25 -> v26 on synthetic PostgreSQL; use the original publisher and API, then restore the old archive."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from sqlalchemy.engine import make_url

from check_c3_cutover import PUBLISH,ROOT,STARTUP,unpack


PREDECESSOR = "d4c3d6492dead146fa25aecebc7c54b0d944cfc8"
# This archived process only drives ordinary localhost application calls. Its pipe is private to the fixture.
HOST = """
import json,sys
sys.path.insert(0,"tests")
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.exc import DBAPIError
from agency_fixtures import agency
from knowledge_fixtures import accepted
from campaign_planner_fixtures import CASES,prepare_inputs
from app import c3_assets
from uuid import uuid4
from app.campaign_operations import OP
with TestClient(app) as api:
    print(json.dumps({"ready":True,"writer":OP}),flush=True)
    for line in sys.stdin:
        q=json.loads(line)
        if q.get("stop"): break
        if q.get("seed"):
            owner,base,((client,scope),_)=agency.__wrapped__(api)
            cid=next(iter(scope["campaigns"]))
            brand=next(x["brand_id"] for x in accepted(api.get(base+"/campaigns",headers=owner["headers"])) if x["id"]==cid)
            snaps,_=prepare_inputs(api,owner,client,next(iter(scope["clients"])),brand,cid,CASES[1],workflows=(c3_assets.LANDING,))
            root=base+"/campaigns/"+cid
            draft=accepted(api.post(root+"/engine/plans",headers=owner["headers"],json={"key":uuid4().hex,"expected_revision":0,
                "manifest_ids":[snaps[0]["id"]],"duration_days":12,"budget_vnd":20000}))
            approved=accepted(api.post(root+"/engine/plans/"+draft["id"]+"/approve",headers=owner["headers"],
                json={"key":uuid4().hex,"expected_digest":draft["digest"]}))
            print(json.dumps({"headers":owner["headers"],"root":root,"plan":draft,"actor":owner["id"]}),flush=True)
            continue
        if q.get("fixture"):
            # Storage-format sample only. Dispatch of real QA-approved groups has its own integration test.
            from app.database import engine
            from sqlalchemy.orm import Session
            from app.campaign_operations import append,entries
            from app.campaign_planner import campaign_store
            from app.security import current_user
            from fastapi.security import HTTPAuthorizationCredentials
            p=q["plan"]; cid=p["campaign_id"]; tid=p["scope"]["tenant_id"]
            value={"id":"typed-cutover","state":"authorized","execution_mode":"scheduled","plan_id":p["id"],"attempts":0,
                   "deliverable_id":"synthetic-document","asset_revision":1,"asset_digest":"f"*64,"authorized_by":q["actor"],
                   "due_at":"2025-01-01T00:00:00+00:00","cost_vnd":50,"target":{"contract":"sandbox-capability/1","mode":"scheduled"}}
            with Session(engine) as db:
                token=q["headers"]["Authorization"].split(" ",1)[1]
                actor=current_user(HTTPAuthorizationCredentials(scheme="Bearer",credentials=token),db)
                s=campaign_store(db,actor,tid,cid,write=True)
                event=append(s,cid,p["id"],"authorize","actions",value["id"],value,len(entries(s,cid))+1,"synthetic-format-cutover","d"*64)
                db.commit()
            print(json.dumps({"id":event["id"]}),flush=True)
            continue
        try:
            resp=api.request(**q)
            print(json.dumps({"status":resp.status_code,"data":resp.json()}),flush=True)
        except DBAPIError as err:
            print(json.dumps({"sqlstate":err.orig.sqlstate}),flush=True)
"""


@contextmanager
def host(source,env):
    with subprocess.Popen([sys.executable,"-u","-c",HOST],cwd=source,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                          text=True,encoding="utf-8",creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)) as process:
        def rpc(value):
            process.stdin.write(json.dumps(value)+"\n")
            process.stdin.flush()
            return json.loads(process.stdout.readline())
        boot=json.loads(process.stdout.readline())
        try:
            yield boot["writer"],rpc
        finally:
            if process.poll() is None:
                process.stdin.write('{"stop":true}\n')
                process.stdin.flush()
                process.wait(15)


def archive_tool(command,dbname,name,environment,container):
    if container:
        # stdin/stdout carry the archive via pg_dump/pg_restore; secrets stay in environment variables.
        argv=["docker","exec","-i",container,command,"-U",environment["PGUSER"],"-d",dbname]
    else:
        exe=shutil.which(command) or str(Path(os.environ["AMC_TEST_PG_BIN"])/(command + (".exe" if os.name=="nt" else "")))
        argv=[exe,"-d",dbname]
    if command=="pg_dump":
        with name.open("wb") as dest:
            subprocess.run([*argv,"-Fc"],env=environment,stdout=dest,check=True)
    else:
        with name.open("rb") as source:
            subprocess.run([*argv,"--single-transaction","--exit-on-error"],env=environment,stdin=source,check=True)


def run(container=None,physical_copy=False):
    dsn=os.environ["AMC_MIGRATION_DSN"]
    url=make_url(os.environ["DATABASE_URL"])
    assert os.environ.get("AMC_TEST_PG")=="1" and url.host in {"127.0.0.1","localhost","::1"} and url.database.startswith("amc_test")
    suffix=uuid4().hex[:12]
    name,restore="amc_test_cut_"+suffix,"amc_test_restore_"+suffix
    with tempfile.TemporaryDirectory(prefix="cutover_") as td, psycopg.connect(dsn,autocommit=True) as control:
        assert control.info.host==url.host and control.info.dbname==url.database
        old=unpack(PREDECESSOR,Path(td))
        env=os.environ.copy()
        env.pop("PYTHONPATH",None)
        env.update(PYTHONUTF8="1",PGHOST=control.info.host,PGPORT=str(control.info.port),PGUSER=control.info.user,
                   PGPASSWORD=control.info.password or "", AMC_DEV_MAILBOX_DIR=str(Path(td)/"mail"))
        archive=Path(td)/"pre-cutover.dump"
        def configuration(dbname):
            return env | {"DATABASE_URL":url.set(database=dbname).render_as_string(hide_password=False),
                          "AMC_MIGRATION_DSN":make_conninfo(dsn,dbname=dbname)}
        def execute(source,settings,args,*,success):
            result=subprocess.run(args,cwd=source,env=settings,capture_output=True,text=True,encoding="utf8")
            if (result.returncode==0)!=success:
                raise RuntimeError("Unexpected publisher/startup result on disposable DB: "+result.stderr[-500:])
        created=[]
        try:
            for dbname in ((name,) if physical_copy else (name,restore)):
                control.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(dbname)))
                created.append(dbname)
            current=configuration(name)
            execute(old,current,PUBLISH,success=True)
            with host(old,current) as (_,seed_api):
                seed=seed_api({"seed":True})
            if physical_copy:
                saved="amc_test_backup_"+suffix
                control.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(saved),sql.Identifier(name)))
                created.append(saved)
            with host(old,current) as (writer,legacy), psycopg.connect(current["AMC_MIGRATION_DSN"],autocommit=True) as db:
                assert writer=="campaign_sandbox_v1"
                plan=seed["plan"]
                uri=seed["root"]+"/sandbox"
                def get(rpc):
                    reply=rpc({"method":"GET","url":uri,"headers":seed["headers"]})
                    assert reply["status"]==200
                    return reply["data"]
                def command(rpc,kind,key,**args):
                    return rpc({"method":"POST","url":uri+"/commands","headers":seed["headers"],
                                "json":{"kind":kind,"request_id":key,"plan_id":plan["id"],**args}})
                previous=get(legacy)
                original=db.execute("SELECT id,result FROM knowledge_commands WHERE operation='campaign_sandbox_v1' ORDER BY id").fetchall()
                assert original and previous["work_units"]
                if not physical_copy:
                    archive_tool("pg_dump",name,archive,current,container)
                execute(ROOT,current,PUBLISH,success=True)
                execute(ROOT,current,PUBLISH,success=True)
                execute(old,current,PUBLISH,success=False)
                execute(old,current,STARTUP,success=False)
                with host(ROOT,current) as (writer,final):
                    assert writer=="campaign_sandbox_v2"
                    assert [x["id"] for x in get(final)["receipts"]]==[x["id"] for x in previous["receipts"]]
                    apt={"contract":"service-appointment/1","appointment_id":"cutover-apt","product_id":plan["product_id"],"unit":plan["selling_unit"],
                         "quantity":"1","location":"Synthetic local site","service_scope":"Inspection","contact_purpose":"appointment_request",
                         "occurred_at":"2025-01-01T08:00:00Z","requested_for":"2025-01-02T08:00:00Z"}
                    issued=command(final,"appointment","same-request",**apt)
                    assert issued["status"]==200
                    sample=final(seed|{"fixture":True})
                    assert get(final)["appointments"][0]["id"]=="cutover-apt"
                    historical=get(legacy)
                    assert "appointments" not in historical and not any(a["id"]=="typed-cutover" for a in historical["actions"])
                    assert command(legacy,"execute","old-execute",action_id="typed-cutover")["status"]==404
                    assert command(legacy,"labor","old-write",package_id="calendar",phase="qa",seconds=12,observation="retired writer")=={"sqlstate":"55000"}
                with host(ROOT,current) as (_,restarted):
                    assert command(restarted,"appointment","same-request",**apt)==issued
                    assert get(restarted)["actions"][0]["state"]=="authorized"
                assert db.execute("SELECT id,result FROM knowledge_commands WHERE operation='campaign_sandbox_v1' ORDER BY id").fetchall()==original
            rollback=configuration(restore)
            if physical_copy:
                control.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(restore),sql.Identifier(saved)))
                created.append(restore)
            else:
                archive_tool("pg_restore",restore,archive,rollback,container)
            with host(old,rollback) as (_,restored):
                assert get(restored)==previous
            print(json.dumps({"predecessor":PREDECESSOR,"core_transition":[25,26],"backup":"physical snapshot" if physical_copy else "pg_dump/pg_restore",
                              "historical_receipts":len(original),"database_write_refusal":"55000",
                              "old_execute_http":404,"appointment_receipt":issued["data"]["id"],"typed_archive_sample":sample["id"],
                              "restarted_replay":"same receipt","pre_cutover_archive_restore":"same predecessor API response"},sort_keys=True))
        finally:
            for dbname in created:
                control.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(dbname)))


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("--container")
    args.add_argument("--physical-copy",action="store_true",help="Use two offline native PostgreSQL database copies when archive clients are unavailable")
    options=args.parse_args()
    run(options.container,options.physical_copy)
