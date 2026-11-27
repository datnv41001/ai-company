"""Acceptance cases for an offline sandbox card. Fixture policy is never an operational rule."""
import copy
import json
import os
from pathlib import Path

import pytest

from scripts.rfq_evidence import ARCHIVE_SHA256, archived_khe_gon, build_card, with_plan_provenance


FIXTURES = Path(__file__).parent / "fixtures" / "rfq_evidence"
BASE = "2026-11-01T10:00:00Z"
LATER = "2026-11-02T10:00:00Z"
SCOPE = {"tenant_id": "example-agency", "client_id": "client-a", "brand_id": "brand-a", "campaign_id": "campaign-a"}


def lead(quantity="1", moqs=("5",)):
    missing = ["commercial_moq"] if len(moqs) > 1 or (moqs and int(quantity) < int(moqs[0])) else []
    return {"id": "synthetic-intake", "campaign_id": SCOPE["campaign_id"], "scope": dict(SCOPE),
            "plan_id": "plan-a", "sequence": 7, "kind": "rfq", "entity": "leads", "entity_id": "inquiry-a",
            "recorded_at": BASE, "value": {"id": "inquiry-a", "plan_id": "plan-a", "revision": 1,
            "product_id": "demo-product", "unit": "box", "quantity": quantity, "minimum_order_quantities": list(moqs),
            "intake": {"revision": 1, "contract_digest": "fixture-contract", "consent": {"granted": True, "purpose": "quote_request"},
                       "fields": [{"maps_to": "quantity", "unit": "box"}]},
            "contact_purpose": "quote_request", "location": "test site", "required_date": "2026-11-09", "assignee_id": None,
            "occurred_at": "2026-10-31T09:00:00Z", "last_event_at": "2026-10-31T09:00:00Z",
            "session_id": "session-a", "missing": missing, "state": "received" if missing else "qualified",
            "sales_accepted": False, "quoted": False, "ordered": False, "confirmed": False,
            "gross_vnd": 0, "refunded_vnd": 0}}


def next_event(prior, *, kind="complete_rfq", step=None, **updates):
    event = copy.deepcopy(prior)
    revision = prior["value"]["revision"] + 1
    event.update(id=f"synthetic-revision-{revision}", sequence=prior["sequence"] + 1, recorded_at=LATER, kind=kind, step=step)
    event["value"].update(revision=revision, **updates)
    if kind == "sales":
        event["value"]["last_event_at"] = LATER
    return event


def project(events, cutoff=LATER, **kwargs):
    return build_card(events=events, scope=SCOPE, inquiry_id="inquiry-a", recorded_as_of=cutoff, generated_at=LATER, **kwargs)


def compare(case, *, source, cutoff, revision, expected, actual):
    # Export from the assertions themselves, including observed failures, when collecting a review pack.
    record = dict(case=case, source=source, recorded_as_of=cutoff, revision=revision,
                  expected=expected, actual=actual, result="pass" if expected == actual else "fail")
    directory = os.environ.get("AMC_RFQ_TEST_EVIDENCE")
    if directory:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{case}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert actual == expected


def test_immutable_archive_condition_and_source():
    raw = (FIXTURES / "khe-gon.json").read_bytes()
    data = json.loads(raw)
    original = archived_khe_gon(raw, generated_at="2026-11-27T12:00:00Z")
    observed = {k: original["request"][k] for k in ("sku", "quantity", "unit")}
    observed.update(moq=original["commercial"]["recorded_minimums"], status=original["commercial"]["status"],
                    missing=original["rule"]["missing"], attribution=original["attribution"]["status"],
                    source=original["commercial"]["contract_digest"], visit=original["attribution"]["visit_receipt"],
                    approval=original["qualification"]["status"], assigned=original["assignment"]["assignee_id"])
    compare("01-original", source={"archive_sha256": ARCHIVE_SHA256}, cutoff=original["recorded_as_of"], revision=1,
            expected=dict(sku=None, quantity="1", unit="box", moq=["5"], status="below_minimum", missing=["commercial_moq"],
                          attribution="creative_to_submission", source=data["measurement"]["contract_digest"],
                          visit=data["visit"]["id"], approval="no_authorized_receipt", assigned=None), actual=observed)
    assert original["feedback"]["hypotheses"]
    assert data["crm"]["value"] == data["submission"]["value"]
    with pytest.raises(ValueError, match="digest"):
        archived_khe_gon(raw + b" ")


def test_boundary_and_separate_stages():
    row = lead("5")
    card = project([row])
    compare("02-moq-boundary", source=row, cutoff=LATER, revision=1,
            expected=["complete", "meets_recorded_minimum", "no_authorized_receipt"],
            actual=[card["rule"]["status"], card["commercial"]["status"], card["qualification"]["status"]])
    compare("10-no-sales", source=row, cutoff=LATER, revision=1,
            expected=["no_receipt"] * 4, actual=[s["status"] for s in card["milestones"].values()])


def test_revision_cutoff_and_late_business_time():
    first = lead()
    second = next_event(first, quantity="5", missing=[], state="qualified", location="revision-two-marker")
    before, after = (project([second, first], cutoff=c) for c in (BASE, LATER))
    source = [first, second]
    compare("03-two-cutoffs", source=source, cutoff=[BASE, LATER], revision=[1, 2],
            expected=[[1, "1", "below_minimum"], [2, "5", "meets_recorded_minimum"]],
            actual=[[c["revision"], c["request"]["quantity"], c["commercial"]["status"]] for c in (before, after)])
    compare("04-no-future", source=source, cutoff=BASE, revision=1, expected=[True, False, False],
            actual=[before == project([first], BASE), "revision-two-marker" in json.dumps(before),
                    second["id"] in json.dumps(before)])
    compare("05-times", source=source, cutoff=LATER, revision=2,
            expected=[["2026-10-31T09:00:00Z", BASE], [None, LATER]],
            actual=[[h["occurred_at"], h["recorded_at"]] for h in after["history"]])
    with pytest.raises(LookupError):
        project(source, "2026-11-01T09:00:00Z")
    with pytest.raises(ValueError, match="history"):
        project([second])


def policy(**overrides):
    return {"id": "fixture-policy", "revision": 1, "provenance": "synthetic_sales_operations_fixture", "scope": dict(SCOPE),
            "plan_id": "plan-a", "product_id": "demo-product", "unit": "box", "mode": "not_applicable",
            "status": "active", "recorded_at": BASE, "valid_from": BASE, "valid_until": None, **overrides}


def test_absent_moq_waiver_requires_recorded_effective_policy():
    source = lead("5", ())
    unknown = project([source])
    p = policy(recorded_at=LATER)
    before = project([source], BASE, policy=p)
    after = project([source], LATER, policy=p)
    compare("06-explicit-waiver", source=[source, p], cutoff=[BASE, LATER], revision=1,
            expected=["complete", "unknown_moq", True, "explicit_no_minimum", "no_authorized_receipt"],
            actual=[unknown["rule"]["status"], unknown["commercial"]["status"], before == project([source], BASE),
                    after["commercial"]["status"], after["qualification"]["status"]])
    with pytest.raises(ValueError, match="scope"):
        project([source], policy=policy(scope={**SCOPE, "client_id": "other"}))


@pytest.mark.parametrize(("name", "moqs", "p", "adjust", "status"), [
    ("07-conflicting-receipt", ("5", "6"), None, None, "conflicting_moq"),
    ("07-conflicting-policy", ("5",), policy(mode="minimum", minimum="4"), None, "conflicting_moq"),
    ("08-expiry", (), policy(valid_until=LATER), None, "policy_outside_validity"),
    ("08-future-effective", (), policy(valid_from="2026-12-01T00:00:00Z"), None, "policy_outside_validity"),
    ("08-revoked-policy", (), policy(status="revoked"), None, "policy_revoked"),
    ("08-revoked-source", ("5",), None, "source", "source_revoked"),
    ("08-expired-consent", ("5",), None, "consent", "consent_unavailable"),
    ("09-wrong-unit", ("5",), None, "unit", "unit_mismatch"),
    ("09-invalid-discrete", ("5",), None, "fraction", "invalid_quantity_or_unit"),
])
def test_conditions(name, moqs, p, adjust, status):
    row = lead("5", moqs)
    if adjust == "source":
        row["value"]["landing_source"] = {"revoked_at": BASE}
    elif adjust == "consent":
        row["value"]["intake"]["consent"]["valid_until"] = LATER
    elif adjust == "unit":
        row["value"]["unit"] = "kg"
    elif adjust == "fraction":
        row["value"]["quantity"] = "4.5"
    c = project([row], policy=p)
    compare(name, source={"event": row, "synthetic_policy": p}, cutoff=LATER, revision=1, expected=status,
            actual=c["commercial"]["status"])


def test_scope_linkage_replay_and_cross_client_name():
    first = lead("5")
    foreign = copy.deepcopy(first)
    foreign["scope"]["client_id"] = "client-b"
    foreign["campaign_name"] = first["campaign_name"] = "Identical campaign label"
    event_replay = copy.deepcopy(first)
    event_replay["value"]["location"] = "divergent"
    c = project([first, first])
    compare("09-replay-missing-link", source=[first, first], cutoff=LATER, revision=1,
            expected=[1, "unlinked", True], actual=[len(c["history"]), c["attribution"]["status"], c == project([first])])
    with pytest.raises(ValueError, match="replay"):
        project([first, event_replay])
    with pytest.raises(ValueError, match="scope") as err:
        project([foreign])
    compare("13-same-agency-name", source=[first, foreign], cutoff=LATER, revision=None,
            expected="Receipt scope mismatch", actual=str(err.value))


def test_attribution_requires_matching_digest_plan_scope_session_and_time():
    archive = json.loads((FIXTURES / "khe-gon.json").read_bytes())
    base_visit, submission = archive["visit"], archive["submission"]
    scope = archive["distribution"]["scope"]
    for mismatch in ("digest", "plan", "session", "time", "missing-creative", "only-copied-creative-pointer"):
        visit = copy.deepcopy(base_visit)
        inquiry = copy.deepcopy(submission)
        if mismatch == "digest":
            visit["value"]["landing_digest"] = "other"
        elif mismatch == "plan":
            visit["plan_id"] = visit["value"]["plan_id"] = "other"
        elif mismatch == "session":
            visit["entity_id"] = visit["value"]["id"] = "other"
        elif mismatch == "time":
            visit["value"]["occurred_at"] = "2027-01-01T00:00:00Z"
        elif mismatch == "missing-creative":
            for e in (visit, inquiry):
                e["value"]["landing_source"]["storyboard_distribution"].pop("digest")
        c = build_card(scope=scope, events=[visit, inquiry], inquiry_id=inquiry["entity_id"],
                       recorded_as_of=inquiry["recorded_at"], generated_at=inquiry["recorded_at"])
        expected = "landing_to_submission" if mismatch in ("only-copied-creative-pointer", "missing-creative") else "unlinked"
        assert c["attribution"]["status"] == expected


def test_quoted_corrected_cancelled_history_no_real_revenue():
    events = [lead("5")]
    for step, state, updated in [
        ("assign", "assigned", {"assignee_id": "sandbox-sales"}),
        ("accept", "accepted", {"sales_accepted": True}), ("quote", "quoted", {"quoted": True}),
    ]:
        events.append(next_event(events[-1], kind="sales", step=step, state=state, **updated))
    stages = project(events)["milestones"]
    compare("11-sandbox-quote", source=events, cutoff=LATER, revision=4,
            expected=["sandbox_recorded", events[-1]["id"], "no_receipt", "no_receipt"],
            actual=[stages["quote"]["status"], stages["quote"]["receipt_id"], stages["order"]["status"],
                    stages["confirmed_revenue"]["status"]])
    for step, state, updated in [
        ("order", "ordered", {"ordered": True}), ("confirm", "confirmed", {"confirmed": True, "gross_vnd": 1000}),
        ("correct", "confirmed", {"gross_vnd": 800}), ("cancel", "cancelled", {}),
    ]:
        events.append(next_event(events[-1], kind="sales", step=step, state=state, **updated))
    card = project(list(reversed(events)))
    stage = card["milestones"]["confirmed_revenue"]
    compare("12-correction-cancellation", source=events, cutoff=LATER, revision=8,
            expected=["cancelled", 0, events[5]["id"], [1000, 800, 800]],
            actual=[stage["current_disposition"], stage["sandbox_net_vnd"], stage["receipt_id"],
                    [h["sandbox_gross_vnd"] for h in card["history"] if "sandbox_gross_vnd" in h]])


def test_read_purity_archive_funnel():
    raw = (FIXTURES / "khe-gon.json").read_bytes()
    data = json.loads(raw)
    now = data["submission"]["recorded_at"]
    a, b = (archived_khe_gon(raw, generated_at=now) for _ in range(2))
    compare("15-repeat-pure", source={"sha256": ARCHIVE_SHA256}, cutoff=now, revision=1,
            expected=[True, True, "no_authorized_receipt"], actual=[a == b, raw == (FIXTURES / "khe-gon.json").read_bytes(),
                                                                   a["qualification"]["status"]])
    m = a["archived_measurement"]
    compare("16-legacy-funnel", source={"sha256": ARCHIVE_SHA256}, cutoff=now, revision=1,
            expected=[True, "intake-funnel/2", 0, None], actual=[m["intake_funnel"] == data["measurement"],
                                                                 m["intake_funnel"]["version"],
                                                                 m["intake_funnel"]["qualified_rfqs"], m["primary_measurement"]])


def test_scoped_plan_binds_labels_contract_revision_and_cutoff():
    source = json.loads((FIXTURES / "lineage.json").read_bytes())
    plan = source["provenance"]
    for key, quantity in (("revision_1", "1"), ("revision_2", "5")):
        card = build_card(scope=source["scope"], inquiry_id=source["inquiry_id"], events=source["events"],
                          recorded_as_of=source["cutoffs"][key], generated_at=source["generated_at"])
        result = with_plan_provenance(card, plan)
        assert card["request"]["sku"] is None and "SKU" in card["unknowns"]
        assert result["request"]["quantity"] == quantity and result["request"]["sku"] == plan["sku"]
        assert result["plan_provenance"]["observing_submission_receipt"] == source["events"][1]["id"]
        assert result["plan_provenance"]["approval_effective_at"] == plan["approval"]["at"]
        assert result["qualification"]["status"] == "no_authorized_receipt"
        assert "SKU" not in result["unknowns"]
        future = {**plan, "approval": {**plan["approval"], "at": "2099-01-01T00:00:00Z"}}
        assert with_plan_provenance(card, future) == card
        for wrong in ({**plan, "digest": "wrong-plan"}, {**plan, "product_id": "wrong-subject"},
                      {**plan, "sku": "wrong-item"}, {**plan, "plan_snapshot": {**plan["plan_snapshot"], "sku": "wrong-item"}},
                      {**plan, "manifest": {"id": "wrong-manifest"}},
                      {**plan, "intake_contract": {**plan["intake_contract"], "locale": "wrong-locale"}}):
            with pytest.raises(ValueError, match="linkage"):
                with_plan_provenance(card, wrong)
