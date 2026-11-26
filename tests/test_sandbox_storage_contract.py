"""The reader folds both journal generations while the database retires legacy writes."""
from types import SimpleNamespace
import sqlite3

import pytest
from sqlalchemy import create_engine

from app.campaign_operations import OP, state_of
from app.database import prepare_database
from app.main import app  # noqa: F401 -- register every table before initialising a local file


def test_file_retires_v1_and_preserves_pre_cutover_backup(tmp_path):
    source=tmp_path/"sandbox.sqlite"
    # Simulate the predecessor's ordinary SQLite driver. Keep its connection live across cutover.
    old=sqlite3.connect(source)
    old.create_function("amc_channel_writer_v5",0,lambda:5)
    old.create_function("amc_edition_writer_v4",0,lambda:4)
    ddl="CREATE TABLE synthetic_archive(id text primary key,operation text, receipt text)"
    old.execute(ddl)
    old.execute("INSERT INTO synthetic_archive VALUES ('legacy','campaign_sandbox_v1','original')")
    old.commit()
    with sqlite3.connect(tmp_path/"rollback.sqlite") as backup:
        old.backup(backup)
    current=create_engine("sqlite:///"+source.as_posix())
    try:
        prepare_database(current)
        prepare_database(current)
        assert old.execute("SELECT receipt FROM synthetic_archive").fetchone()==("original",)
        with pytest.raises(sqlite3.OperationalError,match="amc_sandbox_writer_v2"):
            old.execute("INSERT INTO knowledge_commands(operation) VALUES ('campaign_sandbox_v1')")
        old.rollback()
        with current.begin() as connection:
            with pytest.raises(Exception,match="retired campaign sandbox format"):
                connection.exec_driver_sql("INSERT INTO knowledge_commands(operation) VALUES ('campaign_sandbox_v1')")
        with sqlite3.connect(tmp_path/"rollback.sqlite") as restored:
            assert restored.execute("SELECT receipt FROM synthetic_archive").fetchone()==("original",)
    finally:
        old.close()
        current.dispose()


def test_new_reader_retains_legacy_and_typed_receipt_sequence():
    old = SimpleNamespace(operation="campaign_sandbox_v1",result={"sequence":1,"entity":"actions","entity_id":"A","value":{"state":"scheduled"}})
    appointment=SimpleNamespace(operation=OP,result={"sequence":2,"entity":"appointments","entity_id":"B","value":{"state":"requested"}})
    settlement=SimpleNamespace(operation=OP,result={"sequence":3,"entity":"actions","entity_id":"A","value":{"state":"cancelled"}})
    assert OP=="campaign_sandbox_v2"
    final=state_of([appointment,settlement,old])
    assert final["appointments"]["B"]["state"]=="requested" and final["actions"]["A"]["state"]=="cancelled"
    assert old.result["value"]=={"state":"scheduled"}
