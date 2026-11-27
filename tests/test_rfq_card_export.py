from hashlib import sha256
import json

import pytest

from scripts import rfq_card


def test_altered_revision_fixture_leaves_no_partial_report(tmp_path, monkeypatch):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "khe-gon.json").write_bytes((rfq_card.FIXTURES / "khe-gon.json").read_bytes())
    (fixtures / "lineage.json").write_bytes(b"{}")
    monkeypatch.setattr(rfq_card, "FIXTURES", fixtures)
    with pytest.raises(ValueError, match="digest mismatch"):
        rfq_card.export(tmp_path / "report")
    assert not (tmp_path / "report").exists()


def test_three_reports_bind_the_two_cases_and_preserve_existing_exports(tmp_path):
    dest = tmp_path / "cards"
    rfq_card.export(dest)
    original, before, after = [json.loads((dest / (key + ".json")).read_bytes()) for key in rfq_card.CASES]
    assert original["inquiry_id"] != before["inquiry_id"] == after["inquiry_id"]
    assert (before["revision"], after["revision"]) == (1, 2)
    assert before["recorded_as_of"] < after["recorded_as_of"]
    assert before["history"] == after["history"][:1]
    assert before["archived_measurement"]["intake_funnel"]["qualified_rfqs"] == 0
    assert after["archived_measurement"]["intake_funnel"]["qualified_rfqs"] == 1
    assert after["archived_measurement"]["primary_measurement"] is None
    assert after["history"][-1]["occurred_at"] is None
    hashes = {p.name: sha256(p.read_bytes()).hexdigest() for p in dest.iterdir()}
    with pytest.raises(FileExistsError):
        rfq_card.export(dest)
    assert {p.name: sha256(p.read_bytes()).hexdigest() for p in dest.iterdir()} == hashes
