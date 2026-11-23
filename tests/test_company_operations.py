from types import SimpleNamespace

import pytest

from app.workforce_gateway import CORE, request_body


@pytest.mark.parametrize("error,expected", [
    ("incomplete_output", "compact"),
    ("invalid_plan", "assignments"),
    ("invalid_source", "S1"),
    ("timeout", "timeout"),
])
def test_director_repairs_are_error_specific(error, expected):
    run = SimpleNamespace(plan=CORE, checkpoints=[], knowledge={"sources": {"S1": {"excerpt": "Notebook"}}}, last_error=error)
    instruction = request_body(run, "local")["messages"][0]["content"]
    assert error in instruction and expected in instruction


def test_pool_contract_is_installed():
    import os
    from app.database import engine as pg_runtime
    if os.getenv("AMC_TEST_PG") != "1":
        pytest.skip("requires PostgreSQL")
    from sqlalchemy import text
    with pg_runtime.connect() as conn:
        assert conn.scalar(text("select to_regprocedure('amc_ops.take()') is not null"))
        assert conn.scalar(text("select to_regprocedure('amc_ops.report(uuid,jsonb,text)') is not null"))
