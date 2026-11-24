"""Inference process. Its dedicated PostgreSQL login can only take and report its own jobs."""

import os
import time

import psycopg
from psycopg.types.json import Jsonb

from migrations.runtime_bundle import reviewed_runtime
from .workforce_gateway import Gateway, GatewayError
from .workforce_worker import bounded_call
from .scheduler_telemetry import worker_heartbeat


def take(conn):
    return conn.execute("select amc_ops.take()").fetchone()[0]


def report(conn, job, result=None, error=None):
    return conn.execute("select amc_ops.report(%s,%s,%s)", (job["id"], Jsonb(result) if result is not None else None, error)).fetchone()[0]


def main():
    # Pool mailboxes may contain registry envelopes. Verify transport and inference
    # code before advertising readiness or collecting the first lease.
    if not reviewed_runtime():
        raise RuntimeError("Unrecognized registry runtime; worker has not registered for offers")
    config = Gateway.configured()
    if config.provider != "local":
        raise ValueError("Pool supports local inference only")
    with psycopg.connect(os.environ["AMC_POOL_DSN"], autocommit=True) as conn:
        next_heartbeat = 0.0
        while True:
            if time.monotonic() >= next_heartbeat:
                worker_heartbeat(conn,config)
                next_heartbeat = time.monotonic()+3
            job = take(conn)
            if job is None:
                time.sleep(0.5)
                continue
            try:
                result = bounded_call(config, job["body"])
            except GatewayError as exc:
                report(conn, job, result=exc.usage, error=str(exc))
            else:
                report(conn, job, result=result)


if __name__ == "__main__":
    main()
