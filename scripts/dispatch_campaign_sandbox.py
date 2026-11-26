"""Bounded loopback dispatcher for one explicitly scoped synthetic campaign. No provider connector."""
import argparse
import hashlib
import json
import os
import time
from urllib.parse import urlsplit
from uuid import UUID

import httpx


def run(origin,tenant,campaign,ticks,batch,interval):
    url = urlsplit(origin)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1","::1"} or url.username or url.password or url.path not in ("","/") or url.query or url.fragment:
        raise ValueError("Use the literal loopback HTTP origin of the local sandbox API")
    if not (1 <= ticks <= 120 and 1 <= batch <= 25 and .1 <= interval <= 60):
        raise ValueError("Use 1–120 ticks, 1–25 actions per tick and 0.1–60 seconds between ticks")
    scope = f"/api/tenants/{UUID(tenant)}/campaigns/{UUID(campaign)}/sandbox"
    headers = {"Authorization":"Bearer " + os.environ["AMC_SANDBOX_DISPATCH_TOKEN"],"X-AMC-Sandbox-Dispatch":os.environ["AMC_SANDBOX_DISPATCH_KEY"]}
    cursor = ""
    with httpx.Client(base_url=origin,headers=headers,trust_env=False,follow_redirects=False,timeout=10) as api:
        for tick in range(ticks):
            response = api.get(scope+"/dispatch-ready",params={"after":cursor,"limit":batch})
            response.raise_for_status()
            for item in response.json():
                action = item["action_id"]
                identity = json.dumps([tenant,campaign,item["plan_id"],action,item["attempts"]])
                key = hashlib.sha256(identity.encode()).hexdigest()
                payload = {"kind":"execute","request_id":key,"plan_id":item["plan_id"],"action_id":action}
                try:
                    reply = api.post(scope+"/dispatch",json=payload)
                    # Timeout/lost acknowledgements retry the same logical attempt on the next tick.
                    print(json.dumps({"tick":tick,"action":action,"http":reply.status_code,
                                      "receipt":reply.json()["id"] if reply.status_code==200 else None}),flush=True)
                    if reply.status_code in (401,403):
                        reply.raise_for_status()
                except httpx.TransportError:
                    print(json.dumps({"tick":tick,"action":action,"result":"delivery_unknown"}),flush=True)
                cursor = action
            if tick + 1 < ticks:
                time.sleep(interval)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin",required=True)
    parser.add_argument("--tenant",required=True)
    parser.add_argument("--campaign",required=True)
    parser.add_argument("--ticks",type=int,default=1)
    parser.add_argument("--batch",type=int,default=10)
    parser.add_argument("--interval",type=float,default=2.0)
    run(**vars(parser.parse_args()))
