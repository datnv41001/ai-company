"""Exercise WF-03 through PostgreSQL, the signed HTTP API and scoped dispatcher/worker roles."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from psycopg.types.json import Jsonb

from agency_fixtures import account, create, postgres_api
from app.knowledge_store import canonical, digest
from c3_fixtures import withdraw
from identity_fixtures import invite_member
from knowledge_fixtures import accepted
from strategy_runtime_fixtures import (
    INTENT, OBSERVATION, PARAPHRASE, PRODUCT, PURCHASE_INTENT, PURCHASE_OBSERVATION, SECOND_OBSERVATION,
    UNSUPPORTED, commission_lab, prepare_review, studio_save,
)
from test_claim_desk import reader


pytestmark = pytest.mark.skipif(os.environ.get("AMC_TEST_PG") != "1", reason="Requires disposable authentic PostgreSQL roles")


def export(name, data):
    if directory := os.environ.get("AMC_RUNTIME_STRATEGY_EVIDENCE"):
        path = Path(directory) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def terms(view, ctx, observation=OBSERVATION):
    handles = {row["excerpt"]: row["handle"] for row in view["references"]}
    return {"expected_revision": view["revision"], "expected_content_digest": view["content_digest"],
            "qualification_revision": ctx["mandate"]["id"], "recipient_id": ctx["recipient"]["id"],
            "option": "explain_use", "asset_type": "web_use_guide", "evidence_state": "supported",
            "release": {"brief_digest":view["brief_release"]["digest"], "review":"aligned",
                        "situation":"work_handover", "direction":"demonstrate_use"},
            "support_handle": handles[observation], "product_handle": handles[PRODUCT], "observation_kind": "observed_behaviour",
            "observation_excerpt": observation, "interpretation": "An annotated use guide could help at shift handover.",
            "buyer_persona": view["audience"], "buying_situation": "A supervisor checks outgoing batches at shift change.",
            "sample_limit": "One observed shift at one site. Use in other sites and buyer segments remains unverified."}


def immutable_counts(ctx):
    db = ctx["lab"].owner
    cid = ctx["scope"]["campaign_id"]
    return {
        "workforce_runs": db.execute("SELECT count(*) FROM workforce_runs WHERE campaign_id=%s", (cid,)).fetchone()[0],
        "action_requests": db.execute("SELECT count(*) FROM action_requests WHERE campaign_id=%s", (cid,)).fetchone()[0],
        "ledger_events": db.execute("SELECT count(*) FROM amc_ops.ledger WHERE tenant=%s",
                                    (ctx["owner"]["tenant"],)).fetchone()[0],
        "other_commands": db.execute("SELECT count(*) FROM knowledge_commands WHERE tenant_id=%s AND operation != 'c3_strategy_decision'",
                                      (ctx["owner"]["tenant"],)).fetchone()[0],
    }


def check_content_readback(signer, downstream, payload, intent):
    """Compare independently authenticated projections to the original commissioning intent."""
    order = downstream["work_order"]
    assert order == {k: v for k, v in signer["work_order"].items() if k != "sources"}
    assert downstream["decision"]["receipt_id"] == signer["decision"]["receipt_id"]
    brief = order["brief"]
    assert brief["purpose"] == intent["purpose"] and brief["objective"] == intent["purpose"]
    for key in ("audience", "buyer_action", "editorial_style", "requirements", "exclusions", "acceptance_criteria"):
        assert brief[key] == intent[key], key
    assert brief["cta"] == "Download the catalogue"
    assert order["message"] == PRODUCT and order["approval"] and order["recipient"] == "Content lead"
    assert order["measurement"]["status"] == "planned_only" and order["measurement"]["execution_authorized"] is False
    situations = {"work_handover":"At a work or shift handover.", "purchase_review":"During a purchasing review before ordering."}
    directions = {"demonstrate_use":"Show how to use the product in the reviewed situation.",
                  "clarify_terms":"Clarify the information needed before ordering using only the approved wording."}
    assert order["guidance"]["situation"] == situations[payload["release"]["situation"]]
    assert order["guidance"]["direction"] == directions[payload["release"]["direction"]]
    assert "Wider demand or performance remains unverified" in order["guidance"]["sample_scope"]
    assert set(downstream["decision"]) == {"receipt_id", "at"}
    text = json.dumps(downstream)
    for private_text in (payload["sample_limit"], payload["buying_situation"], payload["interpretation"],
                         payload["observation_excerpt"], payload["qualification_revision"], payload["recipient_id"],
                         signer["decision"]["actor"], "PRIVATE_SYNTHETIC", "private locator"):
        assert private_text not in text
    assert "budget" not in brief and "deadline" not in brief and "kpi" not in brief


def test_runtime_edits_qualified_decisions_and_recipient(api_for_strategy):
    api = api_for_strategy
    with commission_lab(api) as ctx:
        studio, doc = ctx["studio"], ctx["doc"]
        endpoint = studio + "/content-handoff"
        author, reviewer, recipient = (ctx[name]["headers"] for name in ("author", "reviewer", "recipient"))
        original = accepted(api.get(studio, headers=author))
        raw = ctx["raw"]
        assert raw["research"]["buyer_problem"] == original["groups"]["research"]["buyer_problem"] == UNSUPPORTED
        handles = {r["wording"]: r["id"] for r in ctx["snap"]["projection"]["facts"]}
        assert raw["research"]["source_ids"] == [handles[OBSERVATION], handles[PRODUCT]]
        before = studio_save(api, ctx, original["groups"])
        accepted(api.post(doc + "/submit", headers=author))
        evidence = accepted(api.get(doc + "/content-evidence", headers=reviewer))
        incorrect = next(r for r in evidence["statements"] if r["field"] == "studio.research.buyer_problem")
        assert incorrect["outcome"] == "unresolved" and incorrect["text"] == UNSUPPORTED
        group_sign = api.post(studio + "/approvals", headers=reviewer, json={"expected_revision": before["revision"],
                              "group":"research", "expected_asset_digest":before["asset_digests"]["research"],
                              "note":"Inspect an unsupported claim with valid worker source IDs."})
        final = api.post(doc + "/review", headers=reviewer, json={"expected_qa_revision": before["revision"],
                         "expected_content_digest": evidence["content_digest"], "decision":"approved", "note":"Inspect the current final QA gate."})
        assert group_sign.status_code == final.status_code == 409
        assert accepted(api.get(endpoint, headers=reviewer))["work_order"] is None
        export("baseline.json", {"type":"Candidate rerun against the inherited final QA gate", "worker":raw["research"],
               "original_groups":before["groups"], "assertion":incorrect, "group_status":409, "final_qa":final.json(),
               "scope":ctx["scope"], "run_id":ctx["run"]["id"]})
        fixed = prepare_review(api, ctx, problem=PARAPHRASE)
        assert len(fixed["evidence"]["decisions"]) == 1
        ready = accepted(api.get(endpoint, headers=reviewer))
        assert ready["status"] == "needs_decision" and ready["can_decide"] and len(ready["options"]) >= 2
        assert ready["measurement_status"] == "planned_only" and not ready["measurement"]["execution_authorized"]
        assert ready["provenance"]["brief_id"] == ctx["task"]["id"] and ready["provenance"]["run_id"] == ctx["run"]["id"]
        assert ready["provenance"]["manifest"]["id"] == ctx["snap"]["id"]
        assert all(UNSUPPORTED not in json.dumps(ready[k]) for k in ("permitted_product_wording", "work_order"))
        payload = terms(ready, ctx)
        assert api.post(endpoint, headers=author, json=payload).status_code == 403
        assert api.post(endpoint, headers=reviewer, json=payload | {"support_handle":"F99"}).status_code == 409
        counts = immutable_counts(ctx)
        with ThreadPoolExecutor(max_workers=2) as requests:
            submissions = [requests.submit(api.post, endpoint, headers=reviewer, json=payload) for _ in range(2)]
            first, concurrent = [accepted(result.result(timeout=10)) for result in submissions]
        # The client missed the first acknowledgment and submits the same decision again.
        repeat = accepted(api.post(endpoint, headers=reviewer, json=payload))
        assert first == concurrent == repeat
        assert ctx["lab"].owner.execute("SELECT count(*) FROM knowledge_commands WHERE snapshot_id=%s AND operation='c3_strategy_decision'",
                                        (ctx["snap"]["id"],)).fetchone()[0] == 1
        assert api.post(endpoint, headers=reviewer, json=payload | {"sample_limit":"Different signed decision."}).status_code == 409
        obtained = accepted(api.get(endpoint, headers=recipient))
        check_content_readback(first, obtained, payload, INTENT)
        order = obtained["work_order"]
        assert obtained["audience_mode"] == "recipient" and order["asset_type"] == "web_use_guide"
        assert order["placement"] == "web" and order["message"] == PRODUCT
        assert obtained["decision"]["receipt_id"] == first["decision"]["receipt_id"]
        assert obtained["provenance"] == {} and obtained["references"] == []
        assert all(s not in json.dumps(obtained) for s in (UNSUPPORTED, OBSERVATION, "PRIVATE_SYNTHETIC", payload["qualification_revision"]))
        assert immutable_counts(ctx) == counts
        unassigned = reader(api, ctx["owner"], "admin")
        denied = accepted(api.get(endpoint, headers=unassigned["headers"]))
        assert denied["work_order"] is None and not denied["references"]
        # Privileged setup represents an administrator demoting an existing member; reads use the original session.
        ctx["lab"].owner.execute("UPDATE memberships SET role='editor' WHERE tenant_id=%s AND user_id=%s",
                                 (ctx["owner"]["tenant"], ctx["recipient"]["id"]))
        demoted = accepted(api.get(endpoint, headers=recipient))
        assert not demoted["work_order"] and not demoted["references"]
        signer_after = accepted(api.get(endpoint, headers=reviewer))
        assert not signer_after["work_order"]
        ctx["lab"].owner.execute("UPDATE memberships SET role='admin' WHERE tenant_id=%s AND user_id=%s",
                                 (ctx["owner"]["tenant"], ctx["recipient"]["id"]))
        groups = deepcopy(fixed["studio"]["groups"])
        groups["research"]["buyer_problem"] = SECOND_OBSERVATION
        changed = studio_save(api, ctx, groups)
        stale = api.post(endpoint, headers=reviewer, json=payload)
        assert stale.status_code == 412 and changed["revision"] > fixed["studio"]["revision"]
        assert accepted(api.get(endpoint, headers=recipient))["work_order"] is None
        revised = prepare_review(api, ctx, problem=SECOND_OBSERVATION)
        revised_view = accepted(api.get(endpoint, headers=reviewer))
        extra = next(ref for ref in revised_view["references"] if ref["excerpt"] == SECOND_OBSERVATION)
        revised_terms = terms(revised_view, ctx) | {"support_handle":extra["handle"], "observation_excerpt":SECOND_OBSERVATION,
                        "option":"explain_terms", "asset_type":"web_terms_panel",
                        "buying_situation":"The supervisor checks specifications before sorting outgoing batches at handover.",
                        "sample_limit":"One supervisor during a second handover; applicability elsewhere remains unverified.",
                        "interpretation":"This buyer asked to compare specifications before a demonstration."}
        revised_terms["release"].update(direction="explain_specifications")
        updated = accepted(api.post(endpoint, headers=reviewer, json=revised_terms))
        assert updated["work_order"]["asset_type"] == "web_terms_panel"
        assert updated["decision"]["receipt_id"] != first["decision"]["receipt_id"]
        new_order = accepted(api.get(endpoint, headers=recipient))["work_order"]
        assert new_order["message"] == PRODUCT and new_order["asset_type"] != order["asset_type"]
        assert new_order["guidance"]["direction"] != order["guidance"]["direction"]
        changed_strategy = deepcopy(revised["studio"]["groups"])
        changed_strategy["strategy"]["channel_choice"] = "owned counter card"
        strategy_edit = studio_save(api, ctx, changed_strategy)
        assert accepted(api.get(endpoint, headers=recipient))["work_order"] is None
        assert api.post(endpoint, headers=reviewer, json=revised_terms).status_code == 412
        export("lineage.json", {"execution":"Real PostgreSQL-provisioned loopback worker; controlled role replies, zero model invocation",
               "actors":"Distinct synthetic staff sessions author, qualified reviewer, assigned downstream recipient",
               "scope":ctx["scope"], "worker_requests":ctx["requests"], "worker_replies":raw, "original":original["groups"],
               "corrected":fixed["studio"]["groups"], "paraphrase_resolution":fixed["evidence"]["decisions"],
               "signed_review":first, "delivered":obtained, "changed_research":updated, "changed_recipient_order":new_order,
               "invalidating_strategy_revision":strategy_edit["revision"], "durable_counts_before_and_after_handoff":counts,
               "contributions":{"worker":"Controlled scripted suggestions, no new inference.", "deterministic":"Manifest, evidence classification, version gates, replay, scoped delivery.",
                                "staff":"Synthetic authenticated edit, qualification decision and explicit option/recipient selection."}})
        export("authority.json", {"source":"PostgreSQL signed requests", "scope":ctx["scope"], "original_recipient":obtained["decision"],
               "unassigned":denied["reasons"], "demoted_recipient":demoted["reasons"], "demoted_recipient_signer_view":signer_after["reasons"],
               "author_post":403, "invalid_handle":409, "conflicting_retry":409, "stale_after_research_edit":412,
               "stale_after_strategy_edit":412, "concurrent_submissions":2, "committed_decisions":1,
               "lost_ack_receipt":repeat["decision"]["receipt_id"]})


@pytest.fixture
def api_for_strategy():
    with postgres_api() as api:
        yield api


def test_signed_holds_and_withdrawn_source(api_for_strategy):
    api = api_for_strategy
    with commission_lab(api) as ctx:
        endpoint = ctx["studio"] + "/content-handoff"
        signer, downstream = ctx["reviewer"]["headers"], ctx["recipient"]["headers"]
        results = {}
        for label, change, reason in (
            ("unsupported passage with valid ID", {"observation_excerpt":UNSUPPORTED}, "observation_unverified"),
            ("real passage from unrelated research", {"observation_excerpt":SECOND_OBSERVATION, "support_handle":"alternate"}, "observation_unverified"),
            ("substitution of another stakeholder", {"buyer_persona":"Purchasing directors"}, "buyer_scope_mismatch"),
            ("conflicting source", {"evidence_state":"conflicting", "contrary_handle":"alternate"}, "contradictory_evidence"),
            ("missing evidence", {"evidence_state":"insufficient", "support_handle":None}, "missing_observation"),
            ("request clarification", {"evidence_state":"needs_clarification"}, "clarify_commission"),
            ("incorrect placement", {"asset_type":"counter_use_card"}, "asset_placement_mismatch"),
            ("product assertions need Strategy adoption", {"product_handle":"alternate"}, "source_purpose_mismatch"),
            ("missing permission to transfer", {"release":None}, "brief_release_required"),
            ("different signed brief", {"release":{"brief_digest":"0"*64}}, "brief_release_required"),
            ("reviewer withholds private material", {"release":{"review":"private"}}, "brief_disclosure_blocked"),
            ("reviewer flags editorial conflict", {"release":{"review":"conflict"}}, "brief_conflict"),
            ("changed buying situation conflicts with approved brief", {"release":{"situation":"purchase_review"}}, "brief_conflict"),
            ("editorial instruction promotes excluded feature", {"interpretation":"Promote automatic worker tracking during handover."}, "brief_conflict"),
        ):
            prepare_review(api, ctx)
            ready = accepted(api.get(endpoint, headers=signer))
            alternate = next(ref["handle"] for ref in ready["references"] if ref["excerpt"] == SECOND_OBSERVATION)
            body = terms(ready, ctx)
            for key, value in change.items():
                if key == "release" and isinstance(value, dict):
                    body[key].update(value)
                else:
                    body[key] = alternate if value == "alternate" else value
            held = accepted(api.post(endpoint, headers=signer, json=body))
            delivery = accepted(api.get(endpoint, headers=downstream))
            assert held["status"] == "hold" and reason in held["reasons"], (label, held["reasons"])
            assert delivery["work_order"] is None and not delivery["references"]
            assert held["decision"]["receipt_id"] == delivery["decision"]["receipt_id"]
            results[label] = {"revision":held["revision"], "receipt":held["decision"]["receipt_id"],
                              "reasons":held["reasons"], "next_owner":held["next_owner"]}
        prepare_review(api, ctx)
        ready = accepted(api.get(endpoint, headers=signer))
        body = terms(ready, ctx)
        positive = accepted(api.post(endpoint, headers=signer, json=body))
        assert accepted(api.get(endpoint, headers=downstream))["work_order"]["message"] == PRODUCT
        accepted(withdraw(api, ctx["owner"], ctx["state"]))
        for actor in (signer, downstream):
            after = accepted(api.get(endpoint, headers=actor))
            assert after["status"] == "hold" and not after["work_order"] and not after["references"]
        assert api.post(endpoint, headers=signer, json=body).status_code == 409
        results["source withdrawn after final QA"] = {"before":positive["decision"]["receipt_id"],
                                                      "after":after["reasons"], "retry":409}
        export("negative-cases.json", results)


def test_restricted_locator_inside_signed_brief_is_withheld(api_for_strategy):
    api = api_for_strategy
    private_instruction = "Put the source reference private locator on the finished card."
    with commission_lab(api, intent=INTENT | {"requirements":[private_instruction]}) as ctx:
        prepare_review(api, ctx)
        endpoint = ctx["studio"] + "/content-handoff"
        qa = ctx["reviewer"]["headers"]
        ready = accepted(api.get(endpoint, headers=qa))
        assert private_instruction in ready["brief_release"]["fields"]["requirements"]
        signed = accepted(api.post(endpoint, headers=qa, json=terms(ready, ctx)))
        assert signed["status"] == "hold" and "brief_disclosure_blocked" in signed["reasons"]
        downstream = accepted(api.get(endpoint, headers=ctx["recipient"]["headers"]))
        assert not downstream["work_order"] and "private locator" not in json.dumps(downstream)
        export("private-handoff.json", {"case":"Current private source locator copied into a signed requirement",
               "signer_reasons":signed["reasons"], "recipient_reasons":downstream["reasons"], "released":False})


def test_counter_channel_and_changed_buyer_withdrawn_qualification(api_for_strategy):
    api = api_for_strategy
    observed = PURCHASE_OBSERVATION
    channel = PURCHASE_INTENT["channel"]
    with commission_lab(api, intent=PURCHASE_INTENT, observation=observed) as ctx:
        signer, recipient = ctx["reviewer"]["headers"], ctx["recipient"]["headers"]
        endpoint = ctx["studio"] + "/content-handoff"
        prepare_review(api, ctx, problem=observed, channel=channel)
        ready = accepted(api.get(endpoint, headers=signer))
        assert ready["placement"] == channel and ready["audience"] == "Purchasing directors"
        body = terms(ready, ctx, observed) | {"option":"explain_terms", "asset_type":"web_terms_panel",
                    "buying_situation":"A director compares printed specifications before ordering.",
                    "interpretation":"A printed terms card could explain the offer during purchasing.",
                    "sample_limit":"One purchasing director observed at one counter during one order comparison."}
        body["release"].update(situation="purchase_review", direction="clarify_terms")
        wrong = accepted(api.post(endpoint, headers=signer, json=body))
        assert wrong["status"] == "hold" and "asset_placement_mismatch" in wrong["reasons"]
        prepare_review(api, ctx, problem=observed, channel=channel)
        current = accepted(api.get(endpoint, headers=signer))
        body.update(expected_revision=current["revision"], expected_content_digest=current["content_digest"], asset_type="counter_terms_card")
        body["release"]["brief_digest"] = current["brief_release"]["digest"]
        correct = accepted(api.post(endpoint, headers=signer, json=body))
        delivered = accepted(api.get(endpoint, headers=recipient))
        assert delivered["work_order"]["asset_type"] == "counter_terms_card" and delivered["work_order"]["message"] == PRODUCT
        check_content_readback(correct, delivered, body, PURCHASE_INTENT)
        assert not any(word in json.dumps(delivered).lower() for word in ("shift handover", "observed shift"))
        assert "one purchasing director" in correct["decision"]["sample_limit"].lower()
        accepted(withdraw(api, ctx["owner"], ctx["state"], ctx["mandate"]))
        revoked = accepted(api.get(endpoint, headers=recipient))
        assert revoked["status"] == "hold" and not revoked["work_order"]
        assert api.post(endpoint, headers=signer, json=body).status_code == 409
        export("placement.json", {"scope":ctx["scope"], "signed_placement":channel, "buyer":ready["audience"],
               "observed":observed, "wrong":wrong["reasons"], "counter_order":correct["work_order"],
               "signed_sample_limit":body["sample_limit"], "readback":delivered["work_order"],
               "recipient":delivered["decision"], "qualification_withdrawn":revoked["reasons"]})


def test_two_similarly_named_agency_campaigns_are_not_authority(api_for_strategy):
    api = api_for_strategy
    owner = account(api, "Agency")
    base = "/api/tenants/" + owner["tenant"]
    actors = []
    for name in ("North", "South"):
        actor = account(api, name)
        client = create(api, base + "/clients", owner, {"name":name})
        brand = create(api, base + "/brands", owner, {"name":"Tray", "client_id":client["id"]})
        campaign = create(api, base + "/campaigns", owner, {"name":"Tray pilot", "brand_id":brand["id"],
                         "brief":"Consumer research", "objective":"Explain the tray."})
        doc = create(api, base + "/deliverables", owner, {"campaign_id":campaign["id"], "title":"Product guide", "content":{"draft":name}})
        invite_member(api, base, owner["headers"], actor["headers"], email=actor["email"], role="client_viewer", client_id=client["id"])
        actors.append((actor, client, campaign, doc))
    checks = []
    for actor, own, campaign, _ in actors:
        assert [row["id"] for row in accepted(api.get(base + "/clients", headers=actor["headers"]))] == [own["id"]]
        for _, other, named, doc in actors:
            assert named["name"] == campaign["name"]
            endpoint = base + "/deliverables/" + doc["id"] + "/studio/content-handoff"
            response = api.get(endpoint, headers=actor["headers"])
            assert response.status_code in (403, 404)
            checks.append({"client":own["id"], "requested_client":other["id"], "campaign":named["id"], "status":response.status_code})
    export("client-scope.json", {"workspace":"Synthetic agency", "campaign_name":"Tray pilot", "checks":checks})


def test_legacy_decision_requires_a_fresh_review(api_for_strategy):
    api = api_for_strategy
    archived = Path(__file__).resolve().parents[1] / "docs/evaluation/round64/closure/reviewed-handoff-red.json"
    old_order = json.loads(archived.read_text(encoding="utf-8"))["recipient"]["work_order"]
    with commission_lab(api) as ctx:
        prepare_review(api, ctx)
        endpoint = ctx["studio"] + "/content-handoff"
        qa, recipient = ctx["reviewer"]["headers"], ctx["recipient"]["headers"]
        ready = accepted(api.get(endpoint, headers=qa))
        current_post = terms(ready, ctx)
        # Import the historical /1 storage shape into this already signed QA revision.
        # The privileged fixture writes one immutable row. All subsequent reads and writes use real staff sessions.
        old_request = {k: v for k, v in current_post.items() if k != "release"}
        old_request["contrary_handle"] = None
        row_id, version = str(uuid4()), "amc.internal-strategy-handoff/1"
        key = "strategy:" + digest(canonical([version, ready["provenance"]["document_id"], ready["revision"]]))
        by_handle = {r["handle"]:r for r in ready["references"]}
        selected = {h:by_handle[h] for h in (old_request["support_handle"], old_request["product_handle"])}
        old = dict(version=version, request=old_request, scope=ctx["scope"], placement=ready["placement"],
                   provenance=ready["provenance"], qa_receipt=ready["provenance"]["qa_receipt"],
                   revision=ready["revision"], content_digest=ready["content_digest"], reasons=[],
                   work_order=old_order | {"sources":{"observation":selected[old_request["support_handle"]],
                                                      "product":selected[old_request["product_handle"]]}},
                   selected_references=selected)
        db = ctx["lab"].owner
        db.execute("INSERT INTO knowledge_commands (id,tenant_id,client_id,brand_id,visibility,key,actor,operation,"
                   "request_digest,result,snapshot_id,effective_at) VALUES (%s,%s,%s,%s,'restricted',%s,%s,"
                   "'c3_strategy_decision',%s,%s,%s,clock_timestamp())",
                   (row_id,ctx["scope"]["tenant_id"],ctx["scope"]["client_id"],ctx["scope"]["brand_id"],key,
                    ctx["reviewer"]["id"],digest(canonical(old)),Jsonb(old),ctx["snap"]["id"]))
        held = []
        for actor in (qa, recipient):
            projection = accepted(api.get(endpoint, headers=actor))
            assert projection["status"] == "hold" and "legacy_decision_requires_review" in projection["reasons"]
            assert projection["work_order"] is None
            held.append(projection["reasons"])
        for post in (old_request, current_post):
            assert api.post(endpoint, headers=qa, json=post).status_code == 409
        prepare_review(api, ctx)
        fresh = accepted(api.get(endpoint, headers=qa))
        assert fresh["revision"] > ready["revision"]
        body = terms(fresh, ctx)
        signed = accepted(api.post(endpoint, headers=qa, json=body))
        delivered = accepted(api.get(endpoint, headers=recipient))
        check_content_readback(signed, delivered, body, INTENT)
        assert signed["decision"]["receipt_id"] != row_id
        assert db.execute("SELECT result FROM knowledge_commands WHERE id=%s", (row_id,)).fetchone()[0] == old
        export("legacy-handoff.json", {"historical_receipt_fixture":row_id, "historical_version":version,
               "historical_revision":ready["revision"], "signer_and_recipient_holds":held, "same_revision_retries":409,
               "fresh_revision":fresh["revision"], "fresh_contract":signed["version"], "fresh_receipt":delivered["decision"]})
