"""One synthetic commission, real PostgreSQL dispatcher/worker and signed Studio actor sessions."""
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
from uuid import uuid4

from app import c3_assets, c3_skill_library as skills
from app.pool_worker import report
from c3_fixtures import capture, prepared
from c3_task_fixtures import internal_workspace
from knowledge_fixtures import accepted, revision
from migrations.apply import publish_registry
from scripts.provision_pool import internal_route
from test_c3_internal_worker import InternalPool
from test_claim_desk import reader


OBSERVATION = "One shift supervisor used the two-tone tray to separate outgoing batches."
PRODUCT = "The passive tray has two separate compartments."
SECOND_OBSERVATION = "During another shift handover a supervisor asked to see the tray specifications before sorting outgoing batches."
PARAPHRASE = "At the observed handover one supervisor separated outgoing batches with the two-tone tray."
UNSUPPORTED = "Both sites requested individual worker tracking."
INTENT = dict(product="Route Tray", audience="Shift supervisors", region="HN", locale="en-US", channel="web",
              purpose="Choose a useful product guide for a shift handover.", deliverable_type="marketing_strategy", buyer_action="catalogue_download",
              editorial_style="concise", requirements=["Prepare a practical guide for one shift handover."], exclusions=["automatic worker tracking"],
              acceptance_criteria=["Tie the proposed asset to an observed task."])
PURCHASE_OBSERVATION = "A purchasing director compared the specification cards before ordering the two-compartment tray."
PURCHASE_INTENT = INTENT | {
    "audience": "Purchasing directors", "channel": "owned counter card",
    "purpose": "Help purchasing directors compare the tray specifications before ordering.",
    "requirements": ["Prepare a counter card for comparing tray specifications before ordering."],
    "acceptance_criteria": ["Show the approved tray specifications and the catalogue action on the card."],
}


def _workers(lab, run, cited, intent, controlled=None):
    requests, outputs = {}, {}
    replies = {
        "director": dict(primary_assignment="Review the observed use in the selected segment.",
                         secondary_assignment="Compare feasible options for the selected audience."),
        "research": dict(segment="Shift supervisors", buyer_problem=UNSUPPORTED,
                         research_question="What happened at the last shift handover?", evidence_needed="Review a second site independently."),
        "strategy": dict(positioning="Explain the tray layout for supervisors.", channel_choice="Prepare a draft for the owned product page.",
                         rationale="Investigate batch separation at shift handover.", test_hypothesis="Test whether a two-panel explanation is useful.",
                         measurable_action="Count reviewed requests for the use guide.",
                         measurement_method="Review unique request identifiers at the next review."),
    }
    if intent == PURCHASE_INTENT:
        replies["research"] = dict(segment=intent["audience"], buyer_problem=PURCHASE_OBSERVATION,
                                   research_question="Which tray specifications did the director compare before ordering?",
                                   evidence_needed="Review the purchasing interaction at another counter.")
        replies["strategy"] = dict(positioning=PRODUCT, channel_choice=intent["channel"],
                                   rationale="Explain the product specifications when buyers compare the trays.",
                                   test_hypothesis="Test whether a printed specifications card helps buyers compare the trays.",
                                   measurable_action="Count completed catalogue downloads.",
                                   measurement_method="Count completed unique catalogue downloads per eligible visit.")
    for stage in ("director", "research", "strategy"):
        worker = lab.workers[0]
        assert worker.take() is None
        assert lab.dispatch(), (stage, lab.owner.execute(
            "select state,last_error from workforce_runs where id=%s", (run["id"],)).fetchone())
        job = worker.take()
        assert job and job["run"] == run["id"]
        schema = job["body"]["response_format"]["json_schema"]
        assert schema["name"] == "c3_skills_" + stage
        raw = dict(replies[stage], **(controlled or {}).get(stage, {}))
        if stage != "director":
            raw["source_ids"] = cited
        requests[stage] = {"schema": schema["name"], "context": json.loads(job["body"]["messages"][-1]["content"])}
        outputs[stage] = raw
        assert report(worker.conn, job, [raw, 80, 28]) and lab.consume()
        completed = lab.owner.execute(
            "SELECT a.status,t.skill FROM amc_ops.attempts a JOIN amc_ops.tasks t "
            "ON (t.run,t.step,t.tenant)=(a.run,a.step,a.tenant) WHERE a.id=%s AND a.run=%s",
            (job["id"], run["id"]),
        ).fetchone()
        assert completed == ("closed", stage)
        requests[stage]["completed_attempt_id"] = str(job["id"])
    return requests, outputs


@contextmanager
def commission_lab(api, *, intent=INTENT, observation=OBSERVATION, product_statement=PRODUCT, source_facts=None, controlled=None):
    """No credentials are serialized. Browser callers may log in using the two fixture accounts."""
    lab = InternalPool(api, os.environ["AMC_MIGRATION_DSN"])
    try:
        owner, base, client, brand, campaign = internal_workspace(api)
        reviewer = reader(api, owner, "admin")
        recipient = reader(api, owner, "admin")
        lab.configure(owner, 10000)
        definition = json.loads((Path(skills.__file__).resolve().parents[1] / "catalog/research-strategy-v3.json").read_bytes())
        with lab.owner.transaction():
            internal_route(lab.owner, lab.worker_name, owner["tenant"], client, brand, campaign)
            publish_registry(lab.owner, definition)
        api.put(base + "/workforce/registry/" + campaign, headers=owner["headers"], json={
            "workflow": c3_assets.RESEARCH, "action": "activate", "skills": definition["required"]
        }).raise_for_status()
        task = accepted(api.post(base + "/workforce/internal-tasks", headers=owner["headers"], json={
            "key": uuid4().hex, "campaign_id": campaign, "intent": intent,
        }))
        info = dict(product=intent["product"], audience=intent["audience"], locale=intent["locale"], region=intent["region"],
                    channel=intent["channel"], objective=intent["purpose"], sku="TRAY-2", facts=[
                        {"wording": observation, "qualifiers": [], "excerpt": observation},
                        {"wording": PRODUCT, "qualifiers": [], "excerpt": PRODUCT},
                        {"wording": SECOND_OBSERVATION, "qualifiers": [], "excerpt": SECOND_OBSERVATION}])
        if source_facts is not None:
            info["facts"] = source_facts
        state = prepared(api, owner, base, client, brand, campaign, task["id"], c3_assets.RESEARCH, case=info)
        guide = revision(api, owner, state["path"], "route-studio-guidance", "guidelines", {"guidance": "Use the approved product description."})
        state["params"]["guidelines"] = guide["id"]
        snap = capture(api, owner, state)
        terms = dict(registry_workflow=c3_assets.RESEARCH, workflow="dynamic-v1", budget_microusd=10000,
                     knowledge_manifest={"id": snap["id"], "digest": snap["digest"]})
        queue = base + "/workforce/briefs/" + task["id"] + "/run"
        run = accepted(api.post(queue, headers=owner["headers"], json=terms))
        assert accepted(api.post(queue, headers=owner["headers"], json=terms))["id"] == run["id"]
        facts = {row["wording"]: row["id"] for row in snap["projection"]["facts"]}
        requests, raw = _workers(lab, run, [facts[observation], facts[product_statement]], intent, controlled)
        report_url = base + "/workforce/runs/" + run["id"]
        trace = accepted(api.get(report_url, headers=owner["headers"]))
        assert trace["state"] == "awaiting_qa"
        doc = base + "/deliverables/" + trace["deliverable_id"]
        mandate = revision(api, owner, state["path"], "handoff-mandate", "qualification", {
            "approver_id": reviewer["id"], "category": "unclassified", "basis": "Synthetic independent research review.",
            "valid_until": "2099-01-01T00:00:00Z"}, visibility="restricted")
        yield dict(lab=lab, owner=owner, author=owner, reviewer=reviewer, recipient=recipient, base=base, doc=doc, studio=doc+"/studio",
                   run=run, snap=snap, task=task, state=state, scope={"tenant_id":owner["tenant"], "client_id":client,
                   "brand_id":brand, "campaign_id":campaign}, raw=raw, requests=requests, mandate=mandate, report_url=report_url)
    finally:
        lab.release_connections()


def studio_save(api, ctx, groups):
    studio, headers = ctx["studio"], ctx["author"]["headers"]
    current = accepted(api.get(studio, headers=headers))
    return accepted(api.patch(studio, headers=headers, json={"expected_revision":current["revision"], "groups":groups}))


def prepare_review(api, ctx, *, problem=OBSERVATION, channel="web", positioning=PRODUCT):
    """Edit an unsupported Research sentence; keep the buyer preview and sign the exact three asset groups."""
    auth, qa = ctx["author"]["headers"], ctx["reviewer"]["headers"]
    studio, doc = ctx["studio"], ctx["doc"]
    start = accepted(api.get(studio, headers=auth))
    groups = {name: deepcopy(start["suggestions"][name]) for name in start["groups"]}
    groups["research"]["buyer_problem"] = problem
    groups["strategy"]["positioning"] = positioning
    groups["strategy"]["channel_choice"] = channel
    updated = studio_save(api, ctx, groups)
    assert not updated["quality_issues"], updated["quality_issues"]
    accepted(api.post(doc + "/submit", headers=auth))
    findings = accepted(api.get(doc + "/content-evidence", headers=qa))
    if problem == PARAPHRASE:
        statement = next(row for row in findings["statements"] if row["field"] == "studio.research.buyer_problem")
        assert statement["outcome"] == "unresolved"
        support = next(h for h, source in findings["references"].items() if source["statement"] == OBSERVATION)
        body = {"expected_qa_revision": updated["revision"], "expected_content_digest": findings["content_digest"],
                "statement_id": statement["id"], "qualification_revision": ctx["mandate"]["id"],
                "handle": support, "reason": "One supervisor and one handover are retained; the tray separates outgoing batches."}
        endpoint = doc + "/content-evidence/resolutions"
        assert api.post(endpoint, headers=auth, json=body).status_code in (403, 409)
        accepted(api.post(endpoint, headers=qa, json=body))
        findings = accepted(api.get(doc + "/content-evidence", headers=qa))
    pending = [(row["field"], row["text"], row["outcome"]) for row in findings["statements"]
               if row["outcome"] not in ("editorial", "verified", "reviewed")]
    assert not pending, pending
    for group in ("research", "strategy", "measurement"):
        accepted(api.post(studio + "/approvals", headers=qa, json={
            "group": group, "expected_revision": updated["revision"], "expected_asset_digest": updated["asset_digests"][group],
            "note":"Reviewed the current internal asset against the pinned research and product statement."}))
    evid = accepted(api.get(doc + "/content-evidence", headers=qa))
    approved = accepted(api.post(doc + "/review", headers=qa, json={"decision":"approved", "note":"Checked this synthetic commission.",
                        "expected_qa_revision":updated["revision"], "expected_content_digest":evid["content_digest"]}))
    return {"studio":updated, "evidence":evid, "approval":approved}
