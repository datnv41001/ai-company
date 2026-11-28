"""The independent Content signer assesses the released Strategy obligations on the exact guide edition."""

import json
import os
from pathlib import Path

import pytest

from agency_fixtures import postgres_api
from knowledge_fixtures import accepted
from product_guide_fixtures import activate_guide, advance_guide, guide_case, order_assessment, qualification_cases
from test_product_guide_studio import version
from test_registry import PG


def produce(api, ctx):
    editor = ctx["recipient"]["headers"]
    activate_guide(api, ctx)
    task = accepted(api.post(ctx["start_guide"], headers=editor, json=ctx["guide_request"]))
    advance_guide(ctx)
    run = accepted(api.get(ctx["base"] + "/workforce/runs/" + task["run_id"], headers=editor))
    return task, ctx["base"] + "/deliverables/" + run["deliverable_id"]


def record(case, value):
    if folder := os.getenv("AMC_GUIDE_QUAL_RESULTS"):
        target = Path(folder) / (case + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@PG
@pytest.mark.parametrize("case", qualification_cases(), ids=lambda c: c["case_id"])
def test_order_review_preserves_obligations_and_gates_approval(case):
    with postgres_api() as api, guide_case(api, case=case) as ctx:
        editor, signer = (ctx[name]["headers"] for name in ("recipient", "reviewer"))
        task, doc = produce(api, ctx)
        studio = doc + "/studio/product-guide"

        def inspect():
            return accepted(api.get(studio, headers=signer))

        draft = inspect()
        rows = draft["work_order"]["obligations"]
        brief = ctx["order"]["brief"]
        for field in ("purpose", "audience", "buyer_action", "cta", "editorial_style", "requirements", "exclusions", "acceptance_criteria"):
            expected = brief[field] if isinstance(brief[field], list) else [brief[field]]
            assert [r["text"] for r in rows if r["field"] == field] == expected
        for field in ("placement", "claim_limits"):
            value = ctx["order"][field]
            assert [r["text"] for r in rows if r["field"] == field] == (value if isinstance(value, list) else [value])
        assert [r["text"] for r in rows if r["field"] == "measurement"] == [ctx["order"]["measurement"]["status"]]
        assert [r["text"] for r in rows if r["field"] == "measurement_execution"] == ["not_authorized"]
        assert set(draft["work_order"]) == {"obligations", "digest"}
        for private in (
            "PRIVATE_SYNTHETIC",
            "private locator",
            ctx["mandate"]["id"],
            ctx["reviewer"]["id"],
            "One observed shift at one site.",
            "An annotated use guide could help at shift handover.",
        ):
            assert private not in json.dumps(draft, ensure_ascii=False)
        edit = accepted(api.patch(studio, headers=editor, json=version(draft) | {"heading": "use_case", "layout": "checklist"}))
        assert edit["guide"]["steps"] == case["steps"] and edit["guide"]["limitations"] == case["qualifiers"]
        accepted(api.post(doc + "/submit", headers=editor, json=version(edit)))
        approve = version(edit) | {"decision": "approved", "note": "Compared the signed order and P1 to the current guide."}

        def post(body):
            return api.post(doc + "/review", headers=signer, json=body)

        assert post(approve).status_code == 409
        assessment = order_assessment(edit, case["procedure_kind"])
        assert post(approve | {"guide_review": assessment | {"order_digest": "0" * 64}}).status_code == 412
        assert post(approve | {"guide_review": assessment | {"obligations": {}}}).status_code == 409
        assert post(approve | {"guide_review": assessment | {"sequence": "unclear"}}).status_code == 409
        obligations = assessment["obligations"] | {"requirements.1": "unsupported", "acceptance_criteria.1": "needs_information"}
        unresolved = assessment | {"obligations": obligations}
        assert post(approve | {"guide_review": unresolved}).status_code == 409
        returned_id = None
        if case["procedure_kind"] == "ordered":
            assert post(approve | {"guide_review": assessment}).status_code == 409
            assert inspect()["qa_receipt"] is None
            returned = approve | {"decision": "rejected", "guide_review": unresolved}
            accepted(post(returned))
            returned_view = inspect()
            assert returned_view["status"] == "rejected" and returned_view["guide_review"] == unresolved
            returned_id = returned_view["order_review_receipt"]
            assert returned_id and not returned_view["qa_receipt"]
            accepted(post(returned))
            assert inspect()["order_review_receipt"] == returned_id
            assert post(returned | {"guide_review": assessment}).status_code == 409
            original = edit
            edit = accepted(api.patch(studio, headers=editor, json=version(edit) | case["editor_choice"]))
            assert edit["revision"] == original["revision"] + 1 and not edit["guide_review"]
            assert edit["guide"]["steps"] == original["guide"]["steps"] and edit["work_order"] == original["work_order"]
            accepted(api.post(doc + "/submit", headers=editor, json=version(edit)))
            assert post(approve | {"guide_review": assessment}).status_code == 412
        decision = approve | version(edit) | {"guide_review": assessment}
        accepted(post(decision))
        accepted(post(decision))
        approved = inspect()
        assert approved["guide_review"] == assessment
        assert approved["qa_receipt"] == approved["order_review_receipt"] and approved["qa_receipt"]
        assert post(decision | {"guide_review": unresolved}).status_code == 409
        assert api.post(doc + "/review", headers=editor, json=decision).status_code == 403
        record(
            case["case_id"],
            {
                "run": task["run_id"],
                "manifest": task["manifest_id"],
                "handoff": ctx["guide_request"]["receipt_id"],
                "received_requirements": brief["requirements"],
                "steps": approved["guide"]["steps"],
                "limitations": approved["guide"]["limitations"],
                "layout": approved["guide"]["choices"]["layout"],
                "revision": approved["revision"],
                "content_digest": approved["content_digest"],
                "return_receipt": returned_id,
                "qa_receipt": approved["qa_receipt"],
                "review": approved["guide_review"],
            },
        )


@PG
def test_historical_qa_receipt_remains_identifiable_and_readable(monkeypatch):
    from app import c3_boundaries

    with postgres_api() as api, guide_case(api) as ctx:
        editor, signer = (ctx[name]["headers"] for name in ("recipient", "reviewer"))
        task, doc = produce(api, ctx)
        studio = doc + "/studio/product-guide"
        draft = accepted(api.get(studio, headers=signer))
        accepted(api.post(doc + "/submit", headers=editor, json=version(draft)))
        decision = version(draft) | {"decision": "approved", "note": "Historical edition"}
        original = c3_boundaries.record_approval

        def write_r70_shape(store, snap, values):
            # Seed precisely the older immutable result shape at insertion; no UPDATE or retroactive signature.
            original(store, snap, {key: value for key, value in values.items() if key != "guide_review"})

        with monkeypatch.context() as patch:
            patch.setattr(c3_boundaries, "record_approval", write_r70_shape)
            accepted(api.post(doc + "/review", headers=signer, json=decision | {"guide_review": order_assessment(draft, "ordered")}))
        before = (
            ctx["lab"]
            .owner.execute("SELECT id,request_digest,result FROM knowledge_commands WHERE snapshot_id=%s AND operation='c3_qa'", (task["manifest_id"],))
            .fetchall()
        )
        assert len(before) == 1 and "guide_review" not in before[0][2]
        read = accepted(api.get(studio, headers=editor))
        assert read["qa_receipt"] == before[0][0] and not read["guide_review"] and not read["order_review_receipt"]
        accepted(api.post(doc + "/review", headers=signer, json=decision))
        assert api.post(doc + "/review", headers=signer, json=decision | {"guide_review": order_assessment(draft)}).status_code == 409
        assert (
            ctx["lab"]
            .owner.execute("SELECT id,request_digest,result FROM knowledge_commands WHERE snapshot_id=%s AND operation='c3_qa'", (task["manifest_id"],))
            .fetchall()
            == before
        )
