"""Typed source admission and real, bounded internal guide production on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agency_fixtures import account, postgres_api
from app.knowledge_contracts import Entry
from app.product_guide_admission import RELEASE
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from product_guide_fixtures import LIMIT, STEPS, activate_guide, advance_guide, guide_case, order_assessment
from test_content_handoff_admission import counts
from test_registry import PG


def export(name, value):
    if location := os.getenv("AMC_PRODUCT_GUIDE_EVIDENCE"):
        target = Path(location) / (name + ".json")
        target.parent.mkdir(exist_ok=True, parents=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_source_steps_require_complete_approved_wording():
    words = " ".join(STEPS)
    obj = {
        "locator": "manual",
        "excerpt": words + " " + LIMIT,
        "guide_procedure": {"version": "amc.product-guide-source/1", "steps": STEPS},
        "assertion": {
            "category": "description",
            "wording": words,
            "qualifiers": [LIMIT],
            "placement": {"product": str(uuid4()), "market": str(uuid4()), "channel": "web", "locale": "en-US", "region": "HN"},
        },
    }
    assert Entry.model_validate(obj).guide_procedure.steps == STEPS
    for key, value in (
        ("excerpt", words),
        ("guide_procedure", {"version": "amc.product-guide-source/1", "steps": list(reversed(STEPS))}),
        ("guide_procedure", {"version": "amc.product-guide-source/1", "steps": [*STEPS, "Improves performance."]}),
    ):
        with pytest.raises(ValidationError):
            Entry.model_validate(obj | {key: value})
    old = deepcopy(obj)
    old.pop("guide_procedure")
    assert "guide_procedure" not in Entry.model_validate(old).model_dump()


@PG
def test_description_without_instructions_holds_before_queue():
    with postgres_api() as api, guide_case(api, instructions=False) as ctx:
        before = counts(ctx)
        response = accepted(api.post(ctx["start_guide"], headers=ctx["recipient"]["headers"], json=ctx["guide_request"]))
        assert response == {"status": "hold", "reasons": ["procedure_source_required"], "task_id": None, "run_id": None, "manifest_id": None}
        assert counts(ctx) == before
        export("hold-vi", {"order": ctx["order"], "decision": response, "before": before, "after": counts(ctx)})


@PG
def test_recipient_commissions_exactly_one_guide_and_edits_for_independent_qa():
    with postgres_api() as api, guide_case(api) as ctx:
        owner, recipient, reviewer = (ctx[k]["headers"] for k in ("owner", "recipient", "reviewer"))
        api_url, body = ctx["start_guide"], ctx["guide_request"]
        before = counts(ctx)
        for actor in (owner, reviewer, account(api, "SeparateWorkspace")["headers"]):
            assert api.post(api_url, headers=actor, json=body).status_code in (403, 404, 409)
        assert api.post(api_url, headers=recipient, json={"receipt_id": str(uuid4())}).status_code in (404, 409)
        for name in ("scope", "cta", "source_ids", "budget_microusd", "key"):
            assert api.post(api_url, headers=recipient, json={**body, name: "client override"}).status_code == 422
        generic = {"workflow": "dynamic-v1", "registry_workflow": RELEASE}
        assert api.post(ctx["base"] + "/workforce/briefs/" + ctx["task"]["id"] + "/run", headers=recipient, json=generic).status_code == 409
        # Even a legitimate order cannot implicitly activate a release on the campaign.
        assert api.post(api_url, headers=recipient, json=body).status_code == 409
        assert counts(ctx) == before
        activate_guide(api, ctx)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(api.post, api_url, headers=recipient, json=body) for _ in range(2)]
            a, b = [accepted(f.result(timeout=25)) for f in futures]
        assert a == b == accepted(api.post(api_url, headers=recipient, json=body))
        after = counts(ctx)
        for k in ("tasks", "manifests", "workforce_runs"):
            assert after[k] == before[k] + 1
        assert after["ledger_events"] == before["ledger_events"] and after["action_requests"] == before["action_requests"]
        assert api.post(ctx["base"] + "/workforce/briefs/" + a["task_id"] + "/run", headers=recipient, json=generic).status_code == 409
        assert api.post(ctx["base"] + "/workforce/briefs/" + a["task_id"] + "/run", headers=recipient, json={}).status_code == 409
        manifest_url = ctx["state"]["marketing"] + "/manifests/" + a["manifest_id"]
        public_manifest = accepted(api.get(manifest_url, headers=recipient))
        assert public_manifest["projection"]["order"] == ctx["order"]
        source_map = accepted(api.get(manifest_url + "/provenance", headers=recipient))
        assert source_map["entries"] == [{"handle": "P1", "wording": ctx["order"]["message"]}]
        assert api.get(manifest_url, headers=owner).status_code in (403, 404, 409)
        forged = {**ctx["state"]["params"], "workflow": RELEASE, "key": str(uuid4())}
        assert api.post(ctx["state"]["marketing"] + "/manifests", headers=recipient, json=forged).status_code == 422
        attempts = advance_guide(ctx, fail_first=True)
        run_url = ctx["base"] + "/workforce/runs/" + a["run_id"]
        run = accepted(api.get(run_url, headers=recipient))
        assert run["state"] == "awaiting_qa"
        doc = ctx["base"] + "/deliverables/" + run["deliverable_id"]
        studio = doc + "/studio/product-guide"
        draft = accepted(api.get(studio, headers=recipient))
        export(
            "guide-before-edit",
            {
                "order": ctx["order"],
                "admission": a,
                "draft": draft,
                "attempts": attempts,
                "parent": ctx["run"]["id"],
                "receipt": body["receipt_id"],
                "before": before,
                "after_admission": after,
            },
        )
        assert all(s in json.dumps(draft, ensure_ascii=False) for s in [*STEPS, LIMIT, ctx["order"]["brief"]["cta"]])
        assert "PRIVATE_SYNTHETIC" not in json.dumps(draft)
        assert api.get(studio, headers=owner).status_code in (403, 404, 409)
        # Replay after completion returns the same task and run.
        assert accepted(api.post(api_url, headers=recipient, json=body))["run_id"] == a["run_id"]
        ledger = (
            ctx["lab"]
            .owner.execute(
                "SELECT a.step,a.ordinal,a.status,a.outcome,a.input_tokens,a.output_tokens,sum(l.held),sum(l.spent) "
                "FROM amc_ops.attempts a JOIN amc_ops.ledger l ON l.id=a.id WHERE a.run=%s "
                "GROUP BY a.id ORDER BY a.step,a.ordinal",
                (a["run_id"],),
            )
            .fetchall()
        )
        assert len(ledger) == 3 and all(row[2] == "closed" and row[6] == 0 for row in ledger)
        assert sum(row[4] or 0 for row in ledger) == 220
        export(
            "ledger",
            {
                "run_id": a["run_id"],
                "columns": ["step", "attempt", "status", "outcome", "input_tokens", "output_tokens", "held", "spent"],
                "rows": [[*row[:6], int(row[6]), int(row[7])] for row in ledger],
            },
        )
        stamp = {"expected_qa_revision": draft["revision"], "expected_content_digest": draft["content_digest"]}
        changes = {"heading": "use_case", "layout": "checklist"}
        assert api.patch(studio, headers=reviewer, json={**stamp, **changes}).status_code == 403
        edited = accepted(api.patch(studio, headers=recipient, json={**stamp, **changes}))
        assert edited["revision"] > draft["revision"] and edited["guide"]["steps"] == STEPS
        assert api.patch(studio, headers=recipient, json={**stamp, **changes}).status_code == 412
        current = {"expected_qa_revision": edited["revision"], "expected_content_digest": edited["content_digest"]}
        accepted(api.post(doc + "/submit", headers=recipient, json=current))
        decision = {**current, "decision": "approved", "note": "Compared each step, limitation and CTA to the authorized source."}
        decision["guide_review"] = order_assessment(edited)
        assert api.post(doc + "/review", headers=recipient, json=decision).status_code == 403
        approved = accepted(api.post(doc + "/review", headers=reviewer, json=decision))
        assert approved["status"] == "approved"
        qa_id, proof = (
            ctx["lab"].owner.execute("SELECT id,result FROM knowledge_commands WHERE snapshot_id=%s AND operation='c3_qa'", (a["manifest_id"],)).fetchone()
        )
        assert (proof["strategy_handoff_receipt"], proof["qa_revision"], proof["run_id"]) == (body["receipt_id"], edited["revision"], a["run_id"])
        export(
            "guide-approved",
            {
                "strategy": ctx["run"]["id"],
                "strategy_document": ctx["doc"].rsplit("/", 1)[-1],
                "handoff": body["receipt_id"],
                "child": a,
                "strategy_binding": ctx["lab"].owner.execute("SELECT payload::jsonb->'guide_binding' FROM workforce_briefs WHERE id=%s", (a["task_id"],)).fetchone()[0],
                "manifest": {"id": a["manifest_id"], "digest": public_manifest["digest"], "source_map": source_map},
                "task_version": "amc.product-use-guide/1",
                "attempts": attempts,
                "initial": draft,
                "edited": edited,
                "qa_receipt": qa_id,
                "proof": proof,
                "state": approved["status"],
                "published": False,
            },
        )
        accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
        for url in (studio, doc, run_url, manifest_url, manifest_url + "/provenance"):
            assert api.get(url, headers=recipient).status_code in (403, 404, 409)
        assert api.post(api_url, headers=recipient, json=body).status_code in (403, 404, 409)
        assert counts(ctx)["workforce_runs"] == after["workforce_runs"]
