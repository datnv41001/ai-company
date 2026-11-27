"""Round 63. Adversarial checks on synthetic evidence, current source rights and the draft handoff."""
from copy import deepcopy
import json

import pytest

from scripts.strategy_study import baseline, fixture
from scripts import strategy_workpaper
from scripts.strategy_workpaper import build_workpaper, eligible_sources


def project(case):
    return build_workpaper(case["packet"], baseline(case)["checkpoints"])


def test_catalog_change_under_the_same_workflow_version_is_rejected(tmp_path, monkeypatch):
    case = fixture("route-tray")
    checkpoints = baseline(case)["checkpoints"]
    manifest = json.loads(strategy_workpaper.CATALOG.read_bytes())
    manifest["required_outputs"] = []
    changed = tmp_path / "research-strategy-v3.json"
    changed.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(strategy_workpaper, "CATALOG", changed)
    with pytest.raises(ValueError, match="reviewed catalog"):
        build_workpaper(case["packet"], checkpoints)


def source(case, ident):
    return next(row for row in case["packet"]["sources"] if row["id"] == ident)


def test_foreign_scope_filtered_before_fields_and_older_revision_cannot_resurface():
    case = fixture("route-tray")
    row = source(case, "tray-one")
    other = {**row, "scope": {**row["scope"], "client_id": "different-client"},
             "excerpt": "private canary never returned", "recorded_at": "not accessible"}
    withdrawn = {**row, "revision": 2, "permitted_use": "withdrawn"}
    future = {**row, "revision": 3, "recorded_at": "2027-01-01T00:00:00Z"}
    case["packet"]["sources"].extend([other, withdrawn, future])
    visible = eligible_sources(case["packet"])
    assert not any(s["id"] == row["id"] for s in visible)
    assert "private canary" not in json.dumps(visible)


def test_replayed_source_is_one_record_conflicting_same_version_fails_closed():
    case = fixture("route-tray")
    orig = project(case)
    case["packet"]["sources"].append(deepcopy(source(case, "tray-one")))
    replay = project(case)
    assert orig["strategy"] == replay["strategy"]
    assert orig["research"]["observations"] == replay["research"]["observations"]
    case["packet"]["sources"][-1]["excerpt"] = "Changed copy of the same revision."
    with pytest.raises(ValueError, match="Conflicting copies"):
        eligible_sources(case["packet"])


def test_binding_rejects_wrong_scope_packet_revision_source_and_modified_checkpoint():
    case = fixture("route-tray")
    original = baseline(case)["checkpoints"]
    for key, value in (("packet_sha256", "other packet"), ("scope", {"tenant_id": "other"}),
                       ("source_revisions", {key: 9 for key in original["binding"]["source_revisions"]}),
                       ("source_refs", {})):
        test = deepcopy(original)
        test["binding"][key] = value
        with pytest.raises(ValueError, match="mismatch"):
            build_workpaper(case["packet"], test)
    test = deepcopy(original)
    test["strategy"]["sections"]["rationale"] = "Replace a checked output after validation"
    with pytest.raises(ValueError, match="differs from the validated"):
        build_workpaper(case["packet"], test)


def test_only_cited_whole_sources_can_have_literal_status():
    case = fixture("fold-studio")
    controls = project(case)["research"]["checkpoint_field_review"]
    problem = next(r for r in controls if r["role"] == "research" and r["field"] == "buyer_problem")
    assert problem["status"] == "literal_source_text" and problem["literal_sources"] == ["studio-one"]
    rationale = next(r for r in controls if r["role"] == "strategy" and r["field"] == "rationale")
    assert rationale["status"] == "needs_editor_review" and rationale["literal_sources"] == []
    assert "Every learner wants" not in json.dumps(project(case))


def test_negative_unattributed_or_conflicting_channel_never_places_commissioned_asset():
    case = fixture("route-tray")
    channel = source(case, "tray-channel")
    assert project(case)["department_handoff"]["asset"] == case["packet"]["brief"]["options"][0]["asset"]
    for values in ({"excerpt": "The owned product page is unavailable throughout this pilot."},
                   {"authority_role": "unassigned reviewer"}, {"revoked_at": case["packet"]["as_of"]},
                   {"applies_to": ["audit"]}):
        changed = deepcopy(case)
        source(changed, "tray-channel").update(values)
        output = project(changed)
        assert output["strategy"]["selected_option"] == "handoff"
        assert output["strategy"]["channel"]["value"] is None
        assert output["department_handoff"]["status"] == "hold"
        assert output["department_handoff"]["asset"] is output["department_handoff"]["message"] is None
        assert "product page" not in json.dumps(output["department_handoff"]["internal_concept"])
    alternative = "owned counter card"
    case["packet"]["sources"].append({**channel, "id": "second-channel-decision", "value": alternative,
                                      "excerpt": f"Available for an internal draft: {alternative}."})
    output = project(case)
    assert output["strategy"]["channel"]["status"] == "conflicting"
    assert output["department_handoff"]["asset"] is None


def test_negative_or_non_authoritative_metric_cannot_activate_measurement():
    case = fixture("route-tray")
    marker = source(case, "tray-measure")
    marker["excerpt"] = "No reliable method can measure " + marker["value"] + "."
    result = project(case)
    assert result["strategy"]["measurement"] == {
        "status": "unknown", "value": None, "sources": [], "needs_owner_verification": ["tray-measure"]}


def test_competing_product_claims_are_visible_to_research_but_no_claim_is_handed_on():
    case = fixture("route-tray")
    case["packet"]["sources"].append({**source(case, "tray-fact"), "id": "other-product-record",
                                      "excerpt": "The tray identifies each person holding a part."})
    result = project(case)
    assert result["strategy"]["selected_option"] == "handoff"
    assert {s["source_id"] for s in result["research"]["product_facts"]} == {"tray-fact", "other-product-record"}
    assert "owner reconciliation of competing product wording" in result["research"]["missing"]
    handoff = result["department_handoff"]
    assert handoff["status"] == "hold"
    assert handoff["message"] is handoff["asset"] is handoff["internal_concept"] is None


def test_amended_field_note_cannot_carry_an_earlier_observation_code():
    case = fixture("route-tray")
    row = source(case, "tray-one")
    row["revision"] += 1
    row["excerpt"] = "The supervisor did not use the layout at the shift handover."
    result = project(case)
    assert result["strategy"]["selected_option"] is None
    assert result["department_handoff"]["asset"] is None
    assert result["research"]["awaiting_observation_review"][0]["source_id"] == row["id"]
