from types import SimpleNamespace

import pytest

from app.workforce_gateway import CORE, request_body


@pytest.mark.parametrize(
    "error,expected",
    [
        ("incomplete_output", "compact"),
        ("invalid_plan", "assignments"),
        ("invalid_source", "S1"),
        ("timeout", "timeout"),
    ],
)
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


def test_truncated_content_repair_changes_grammar_and_reserves_output_room():
    from app.workforce_gateway import MAX_OUTPUT

    run = SimpleNamespace(plan=["content"], checkpoints=[], knowledge={"sources": {"S1": {"excerpt": "Notebook"}}}, last_error=None, attempts=0)
    original = request_body(run, "local")
    run.last_error, run.attempts = "incomplete_output", 1
    repaired = request_body(run, "local")

    def fields(body):
        return body["response_format"]["json_schema"]["schema"]["properties"]

    assert fields(repaired)["body_copy"]["maxLength"] < fields(original)["body_copy"]["maxLength"]
    assert original["max_tokens"] == MAX_OUTPUT < repaired["max_tokens"]
    assert repaired["temperature"] > original["temperature"]
