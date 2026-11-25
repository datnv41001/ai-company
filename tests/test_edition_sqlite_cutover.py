"""File-backed Studio writers must understand customer editions across a local process restart."""
import sqlite3

import pytest
from sqlalchemy import create_engine

from app.database import prepare_database


def test_file_backed_edition_cutover_keeps_reader_and_requires_current_writer(tmp_path):
    db = tmp_path / "edition.sqlite"
    # Both connections below use the same sqlite3 driver as the predecessor.
    # Keep one connection open from before the transactional trigger installation.
    old = sqlite3.connect(db)
    engine = create_engine("sqlite:///" + db.as_posix())
    try:
        prepare_database(engine)
        with engine.begin() as current:
            current.exec_driver_sql("""INSERT INTO deliverables (id,tenant_id,campaign_id,title,content,status,created_by,qa_revision)
                VALUES ('draft','tenant','campaign','Working copy','{}','draft','editor',1)""")
            current.exec_driver_sql("UPDATE deliverables SET qa_revision=2 WHERE id='draft'")
        for connection in (old, sqlite3.connect(db)):
            try:
                assert connection.execute("SELECT qa_revision FROM deliverables WHERE id='draft'").fetchone() == (2,)
                with pytest.raises(sqlite3.OperationalError, match="amc_edition_writer_v4"):
                    connection.execute("UPDATE deliverables SET qa_revision=3 WHERE id='draft'")
                connection.rollback()
                assert connection.execute("SELECT qa_revision FROM deliverables WHERE id='draft'").fetchone() == (2,)
            finally:
                connection.close()
        engine.dispose()
        prepare_database(engine)
        with engine.begin() as current:
            current.exec_driver_sql("UPDATE deliverables SET qa_revision=3 WHERE id='draft'")
            assert current.exec_driver_sql("SELECT qa_revision FROM deliverables WHERE id='draft'").scalar_one() == 3
    finally:
        old.close()
        engine.dispose()
