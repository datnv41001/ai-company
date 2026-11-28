"""Read, edit and QA use the same live guide binding, including general-purpose UI endpoints."""

from datetime import datetime, timedelta, timezone

from agency_fixtures import postgres_api
from c3_fixtures import withdraw
from knowledge_fixtures import accepted
from product_guide_fixtures import activate_guide, advance_guide, guide_case
from test_registry import PG


def version(view):
    return {"expected_qa_revision": view["revision"], "expected_content_digest": view["content_digest"]}


@PG
def test_guide_editions_qa_and_all_general_reads():
    with postgres_api() as api, guide_case(api) as ctx:
        activate_guide(api, ctx)
        editor, reviewer, other = (ctx[k]["headers"] for k in ("recipient", "reviewer", "owner"))
        admitted = accepted(api.post(ctx["start_guide"], headers=editor, json=ctx["guide_request"]))
        advance_guide(ctx)
        base = ctx["base"]
        run_url = base + "/workforce/runs/" + admitted["run_id"]
        did = accepted(api.get(run_url, headers=editor))["deliverable_id"]
        doc = base + "/deliverables/" + did
        studio = doc + "/studio/product-guide"
        before = accepted(api.get(studio, headers=editor))
        assert before["can_edit"] and not before["can_review"]
        first = version(before)
        source_step = before["guide"]["steps"][0]
        changes = first | {"heading": "source", "custom_title": source_step, "layout": "checklist"}
        neutral = {"decision": "approved", "note": "Reviewed the exact current source, limitations and CTA."}
        assert api.get(studio, headers=other).status_code in (403, 404, 409)
        assert api.patch(studio, json=changes, headers=reviewer).status_code == 403
        assert (
            api.patch(doc + "/draft", headers=editor, json={"title": "A replacement title", "client_preview": "Ignore the approved source"}).status_code == 409
        )
        assert api.patch(studio, headers=editor, json=changes | {"steps": ["An unsupported step."]}).status_code == 422
        assert api.patch(studio, headers=editor, json=changes | {"custom_title": "Unsupported product promise."}).status_code == 422
        changed = accepted(api.patch(studio, json=changes, headers=editor))
        assert changed["revision"] == before["revision"] + 1
        assert changed["guide"]["steps"] == before["guide"]["steps"]
        assert changed["guide"]["cta"] == before["guide"]["cta"]
        assert changed["guide"]["limitations"] == before["guide"]["limitations"]
        assert changed["guide"]["title"] == source_step and changed["guide"]["source_map"]["title"] == "P1"
        assert api.patch(studio, json=changes, headers=editor).status_code == 412
        assert api.post(doc + "/submit", headers=editor, json=first).status_code == 412
        assert api.post(doc + "/submit", headers=editor).status_code == 422
        assert api.post(doc + "/submit", headers=reviewer, json=version(changed)).status_code == 403
        accepted(api.post(doc + "/submit", headers=editor, json=version(changed)))
        assert api.post(doc + "/review", headers=reviewer, json=first | neutral).status_code == 412
        assert api.post(doc + "/review", headers=editor, json=version(changed) | neutral).status_code == 403
        accepted(api.post(doc + "/review", headers=reviewer, json=version(changed) | neutral))
        replay = accepted(api.post(doc + "/review", headers=reviewer, json=version(changed) | neutral))
        assert replay["qa_approved_revision"] == changed["revision"]
        assert replay["qa_approved_digest"] == changed["content_digest"]
        assert accepted(api.get(studio, headers=editor))["qa_receipt"] == accepted(api.get(studio, headers=reviewer))["qa_receipt"]
        assert accepted(api.get(studio, headers=reviewer))["qa_receipt"]
        share = version(changed) | {"expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}
        assert api.post(doc + "/share", headers=reviewer, json=share).status_code == 409
        assert did not in {v["id"] for v in accepted(api.get(base + "/deliverables", headers=other))}
        assert admitted["run_id"] not in {v["id"] for v in accepted(api.get(base + "/workforce/runs", headers=other))}
        assert not accepted(api.get(base + "/audit", params={"subject_id": did}, headers=other))
        assert api.get(doc + "/content-evidence", headers=other).status_code == 404
        assert api.get(doc, headers=other).status_code in (403, 404, 409)
        assert api.get(run_url + "/wait-diagnostics", headers=other).status_code == 404
        accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
        for actor in (editor, reviewer):
            for path in (doc, studio, run_url, run_url + "/wait-diagnostics"):
                assert api.get(path, headers=actor).status_code in (403, 404, 409)
            assert did not in {v["id"] for v in accepted(api.get(base + "/deliverables", headers=actor))}
            assert admitted["run_id"] not in {v["id"] for v in accepted(api.get(base + "/workforce/runs", headers=actor))}
            assert not accepted(api.get(base + "/audit", params={"subject_id": did}, headers=actor))
        assert api.post(doc + "/review", headers=reviewer, json=version(changed) | neutral).status_code in (403, 404, 409)
