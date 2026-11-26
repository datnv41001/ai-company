"""Historical metrics, source authority and native fixture receipt are replayed without a model."""
import hashlib
import json

from check import HERE, load, replay


def test_retained_receipts_and_grounded_draft():
    recorded = load(HERE / "offline-result.json")
    assert replay() == recorded
    assert recorded["historical"]["raw_type_only"] == 14
    assert recorded["historical"]["full_contract"] == 7
    assert recorded["historical"]["invalid_contract"] == 13
    assert recorded["historical"]["additional_asks_passing_all_per_reader"] == [3, 3]


def test_pinned_native_membership_receipt():
    receipt = load(HERE / "native-result.json")
    grammar = (HERE / "decision.gbnf").read_text(encoding="utf-8").encode("utf-8")
    assert receipt["grammar_sha256_lf"] == hashlib.sha256(grammar).hexdigest()
    fixtures = load(HERE / "grammar-cases.json")
    assert receipt["result"] == {case["name"]: case["accepted"] for case in fixtures}
    assert receipt["fixture_sha256_lf"] == hashlib.sha256(
        (HERE / "grammar-cases.json").read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    for case in fixtures:
        if case["accepted"]:
            assert json.loads(case["text"])["id"] == "demo"
