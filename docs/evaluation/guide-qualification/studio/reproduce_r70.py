"""Run against the exact merged R70 runtime before implementing R70-02."""

import os
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tests"))
from agency_fixtures import postgres_api
from knowledge_fixtures import accepted
import product_guide_fixtures as cases


def test_ordered_checklist_should_not_sign(monkeypatch):
    mandatory = "Show a numbered sequence. The sleeve must be opened before inserting the card."
    monkeypatch.setattr(cases, "INTENT", cases.INTENT | {"requirements": [mandatory]})
    monkeypatch.setattr(cases, "STEPS", ["Open the sleeve.", "Insert the batch card into the opened sleeve."])
    with postgres_api() as api, cases.guide_case(api) as ctx:
        cases.activate_guide(api, ctx)
        editor, reviewer = (ctx[key]["headers"] for key in ("recipient", "reviewer"))
        task = accepted(api.post(ctx["start_guide"], headers=editor, json=ctx["guide_request"]))
        cases.advance_guide(ctx)
        run = accepted(api.get(ctx["base"] + "/workforce/runs/" + task["run_id"], headers=editor))
        doc = ctx["base"] + "/deliverables/" + run["deliverable_id"]
        studio = doc + "/studio/product-guide"
        view = accepted(api.get(studio, headers=editor))

        def revision(v):
            return {"expected_qa_revision": v["revision"], "expected_content_digest": v["content_digest"]}

        edit = accepted(api.patch(studio, headers=editor, json=revision(view) | {"heading": "product", "layout": "checklist"}))
        accepted(api.post(doc + "/submit", headers=editor, json=revision(edit)))
        qa = accepted(api.get(studio, headers=reviewer))
        answer = api.post(doc + "/review", headers=reviewer, json=revision(edit) | {"decision": "approved", "note": "Reviewed the source."})
        after = accepted(api.get(studio, headers=reviewer))
        evidence = dict(
            requirement=ctx["order"]["brief"]["requirements"],
            steps=qa["guide"]["steps"],
            layout=qa["guide"]["choices"]["layout"],
            visible=mandatory in json.dumps(qa),
            review_http=answer.status_code,
            status=after["status"],
            qa_receipt=after["qa_receipt"],
            manifest=task["manifest_id"],
            run=task["run_id"],
            revision=after["revision"],
            content_digest=after["content_digest"],
        )
        Path(os.environ["AMC_RED_FILE"]).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        assert answer.status_code == 409, evidence
