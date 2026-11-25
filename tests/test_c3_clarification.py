"""Replay the 20 previously blocked synthetic briefs through normal task and commercial approvals."""

import json
import os
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agency_fixtures import account
from app import c3_actions, c3_order_units, c3_releases, c3_skill_library, registry_adapters
from c3_task_fixtures import internal_workspace
from evaluation.c3.recovery_fixture import attestation, prepare_recovered, start_recovery
from knowledge_fixtures import accepted

SOURCE = Path(__file__).parent / "evaluation/c3/holdout-v1.json"
CASES = [c for c in json.loads(SOURCE.read_text(encoding="utf8"))["cases"] if c["persona"] in ("service", "inhouse")]


def setup_case(api, case):
    owner, base, client, brand, campaign = internal_workspace(api)
    s, intent = start_recovery(api, case, owner, base, client, brand, campaign)
    return owner, s, intent


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_guided_unit_recovery(api, case):
    owner, s, intent = setup_case(api, case)
    selected = s["params"]
    reviewer = s["commercial_reviewer"]

    def post(endpoint, data, who=owner):
        return api.post(s["marketing"] + "/" + endpoint, headers=who["headers"], json=data)

    start = monotonic()
    first = accepted(post("readiness", selected))
    assert first["status"] == "needs_input" and len(first["clarifications"]) == 1
    issue = first["clarifications"][0]
    assert issue["field"] == "price.unit" and issue["terms"]["unit"] == "service"
    commercial = next(f for f in case["facts"] if f.get("category") == "price")
    # The synthetic operator reads the explicit price card. Never deduce a unit from the industry.
    original_wording = commercial["wording"]
    correction = attestation(case, issue)
    unit = correction["unit"]
    proposal = {"selection": selected, "correction": correction}
    if case["id"] == "service-01":
        assert post("clarifications/propose", proposal, account(api, "OtherTenant")).status_code == 404
        stale = {**correction, "offer_digest": "0" * 64}
        assert post("clarifications/propose", proposal | {"correction": stale}).status_code == 409
        assert post("clarifications/propose", proposal | {"correction": correction | {"confirm_same_terms": False}}).status_code == 422
    staged = accepted(post("clarifications/propose", proposal))
    assert accepted(post("clarifications/propose", proposal)) == staged
    after_proposed = monotonic()
    inbox = accepted(api.get(s["marketing"] + "/clarifications", headers=reviewer["headers"]))["items"]
    assert len(inbox) == 1 and "selection" not in inbox[0] and inbox[0]["excerpt"] == original_wording
    issue = inbox[0]
    pending = issue["proposal"]
    assert pending["state"] == "draft" and pending["required_qualification"] == "unclassified" and not pending["own"]
    decision = {
        "key": str(uuid4()),
        "proposal": pending["id"],
        "qualification_revision": pending["qualifications"][0],
        "reason": "Đối chiếu đúng đơn vị trong bản giá tổng hợp.",
    }
    if case["id"] == "service-01":
        assert post("clarifications/approve", decision).status_code == 409
        # Failing the last approval rolls back every preceding transition in that command.
        assert accepted(api.get(s["path"] + "/revisions/" + staged["offer"], headers=owner["headers"]))["state"] == "draft"
    resolved = accepted(post("clarifications/approve", decision, reviewer))
    assert accepted(post("clarifications/approve", decision, reviewer)) == resolved
    after_approved = monotonic()
    saved = accepted(api.get(s["marketing"] + "/clarifications", headers=owner["headers"], params={"workspace_brief_id": selected["workspace_brief_id"]}))[
        "items"
    ]
    assert len(saved) == 1 and saved[0]["selection"]["target"] == selected["target"] and saved[0]["status"] == "approved"
    if case["id"] == "service-01":
        assert accepted(post("readiness", selected))["clarifications"][0]["proposal"]["state"] == "approved"
    replacement = {**selected, "key": str(uuid4()), "claims": [resolved["claim"] if v == resolved["original_claim"] else v for v in selected["claims"]]}
    assert accepted(post("readiness", replacement))["status"] == "ready"
    snap = accepted(post("manifests", replacement))
    after_manifest = monotonic()
    projection = snap["projection"]
    assert projection["task_intent"] == intent
    pricing = next(f for f in projection["facts"] if f.get("price"))
    assert pricing["price"] == {**issue["terms"], "unit": unit}
    public = c3_order_units.render(selected["workflow"], projection, {})
    assert ("/ 1 lượt" if unit == "visit" else "/ 1 người") in public["body"]
    prior = accepted(api.get(s["path"] + "/revisions/" + issue["claim"], headers=owner["headers"]))
    assert prior["data"]["assertion"]["price"]["unit"] == "service" and prior["state"] == "superseded"
    if folder := os.getenv("AMC_CORRECTION_EVIDENCE"):
        out = Path(folder)
        out.mkdir(parents=True, exist_ok=True)
        result = {
            "case": case["id"],
            "workflow": selected["workflow"],
            "from_unit": "service",
            "attested_unit": unit,
            "task_id": selected["target"]["brief_id"],
            "new_manifest": snap["id"],
            "manifest_digest": snap["digest"],
            "unit_source_excerpt": original_wording,
            "price_fields_preserved": True,
            "status": "ready_for_generation",
            "test_seconds": {
                "propose": round(after_proposed - start, 4),
                "review": round(after_approved - after_proposed, 4),
                "resume": round(after_manifest - after_approved, 4),
                "overall": round(after_manifest - start, 4),
            },
            "model_invocations": 0,
            "practitioner_minutes": None,
        }
        (out / (case["id"] + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")


@pytest.mark.parametrize("case", [c for c in CASES if c["id"] in ("inhouse-09", "service-09")], ids=lambda c: c["id"])
def test_recovery_generation_handoff(api, case):
    handoff = prepare_recovered(api, case, *internal_workspace(api))
    expected = ("rfq", "photo") if case["id"] == "service-09" else ("submit_reference", "sample")
    intent = handoff["manifest"]["projection"]["task_intent"]
    assert (intent["buyer_action"], intent["buyer_input"]) == expected
    assert handoff["correction"]["requested_cta"] == case["cta"]
    receipt = handoff["correction"]
    assert receipt["original_source"] != receipt["source"] and receipt["original_binding"] != receipt["binding"]
    assert receipt["proposal_receipt"]


@pytest.mark.parametrize("action", c3_actions.ACTIONS)
def test_v2_buyer_action_reaches_public_model_prompt(action, monkeypatch):
    projection = {
        "task_intent": {"buyer_action": action, "editorial_style": "formal", "buyer_input": "photo", "requirements": ["PRIVATE-OPERATOR-NOTE"]},
        "brand_guidelines": {"guidance": "PRIVATE-STYLE-DOC"},
    }
    run = SimpleNamespace(
        knowledge={"sources": {"F1": {}}, "registry": {"workflow": "WF-13/landing-seo-draft@6", "contracts": {"content": {}}}, "c3_projection": projection}
    )
    monkeypatch.setattr(registry_adapters, "resolve", lambda _: SimpleNamespace(request=c3_skill_library.request))
    request = registry_adapters.specialist_request(run, "local", node=SimpleNamespace(skill="content"), assignment="PRIVATE-PLAN", predecessors={})
    user = request["messages"][1]["content"]
    assert json.loads(user)["reference"] == c3_releases.role_view(run.knowledge["registry"]["workflow"], "content", projection)
    assert json.loads(user)["reference"]["buyer_action"] == action and "PRIVATE-" not in user
    assert json.loads(user)["reference"]["buyer_input"] == "photo"
