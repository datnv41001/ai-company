"""Agency group decisions on real runtime, registry, dispatcher and worker logins."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import psycopg
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import c3_assets, c3_skill_library, c3_studio
from app.database import engine
from app.access import set_context
from app.security import sign_actor
from c3_fixtures import capture, prepared
from c3_task_fixtures import INTENT
from knowledge_fixtures import accepted, call, revision
from migrations.apply import publish_registry
from test_c3_authority import doc_and_decision
from test_c3_content_gate import approve
from test_claim_desk import reader
from test_registry import PG, policy, pool as registry_pool
from test_role_qa_rollout import post_output
from test_verified_identity import wait_for_lock
from test_workforce import DATA

pool = registry_pool
pytestmark = PG
WORKFLOW = c3_assets.RESEARCH


def agency_draft(lab, workflow, *, rfq=False, before_queue=None):
    api = lab.api
    base, owner, recipient, client, campaign = lab.cases[0]
    lab.owner.execute("update workforce_runs set ready_at=now()+interval '1 day' where id=any(%s)", (lab.runs,))
    catalog = "research-strategy-v3.json" if workflow == c3_assets.RESEARCH else "landing-seo-v6.json"
    manifest = json.loads((Path(__file__).resolve().parents[1] / "catalog" / catalog).read_text(encoding="utf-8"))
    publish_registry(lab.owner, manifest)
    accepted(policy(lab, "activate", skills=manifest["required"], workflow=workflow))
    bid = accepted(
        api.post(
            base + "/workforce/briefs",
            headers=owner["headers"],
            json={
                "title": "Marketing materials for sample requests",
                "recipient_id": recipient["id"],
                "campaign_id": campaign,
            },
        )
    )["id"]
    brief = base + "/workforce/briefs/" + bid
    path = brief + "/run"
    terms = {"workflow": "dynamic-v1", "budget_microusd": 10000, "max_parallel_nodes": 2}
    kind = "marketing_strategy" if workflow == c3_assets.RESEARCH else "landing_page"
    intent = INTENT | {"product": "Fabric sample", "audience": "Independent interior shops", "deliverable_type": kind}
    case = None
    if rfq:
        intent.update(
            product="Bộ mẫu vải", audience="Xưởng nội thất", purpose="Thông tin nghiệp vụ riêng của đội dự án", buyer_action="rfq", editorial_style="plain"
        )
        case = {"product": intent["product"], "audience": intent["audience"], "facts": [{"wording": "Bề mặt mờ", "qualifiers": ["Dùng trong nhà"]}]}
    accepted(api.put(brief + "/submission", headers=recipient["headers"], json=DATA | {"task_intent": intent}))
    brand = lab.owner.execute("select brand_id from campaigns where id=%s", (campaign,)).fetchone()[0]
    prep = prepared(api, owner, base, client, brand, campaign, bid, workflow, case=case)
    guide = revision(api, owner, prep["path"], "voice", "guidelines", {"guidance": "Use plain words."})
    prep["params"]["guidelines"] = guide["id"]
    snap = capture(api, owner, prep)
    if before_queue:
        before_queue(snap, prep, intent)
    terms.update(knowledge_manifest={"id": snap["id"], "digest": snap["digest"]}, registry_workflow=workflow)
    rid = accepted(api.post(path, headers=owner["headers"], json=terms))["id"]
    for stage in ("director", *c3_assets.ROLES[workflow]):
        if stage == "director":
            reply = {
                "primary_assignment": "Examine the buying decision for the fabric sample.",
                "secondary_assignment": "Develop a channel test and measurement plan for sample requests.",
            }
        else:
            reply = {k: v for ref in c3_skill_library.PACKS[stage] for k, v in c3_skill_library.method(ref)["examples"]["good"].items()}
            reply["source_ids"] = ["F1"]
        post_output(lab, rid, "c3_skills_" + stage, reply)
    doc, _ = doc_and_decision(lab, base, owner, rid)
    return doc, prep["path"], snap


def demote(conn, owner, reviewer):
    conn.execute("update memberships set role='viewer' where tenant_id=%s and user_id=%s", (owner["tenant"], reviewer["id"]))


def test_agency_studio_signoff_and_revocation_order(pool):
    lab, api = pool, pool.api
    with Session(engine) as session:
        assert session.execute(text("select current_user, rolsuper, rolbypassrls from pg_roles where rolname=current_user")).one() == (
            "amc_runtime",
            False,
            False,
        )
    base, owner, recipient, _, _ = lab.cases[0]
    other_customer = lab.cases[1][2]
    doc, knowledge, snap = agency_draft(lab, WORKFLOW)
    editor = reader(api, owner, "editor")
    specialist, strategist, final_reviewer = (reader(api, owner, "admin") for _ in range(3))
    with Session(engine) as session:
        for actor, tenant, target in ((owner, lab.y["tenant"], lab.y["id"]), (recipient, owner["tenant"], specialist["id"])):
            set_context(session, actor=actor["id"], tenant=tenant)
            sign_actor(session, actor["id"])
            assert not session.scalar(text("select amc_acl.lock_c3_reviewer(:tenant,:target)"), {"tenant": tenant, "target": target})
            session.rollback()
    studio = doc + "/studio"
    raw = accepted(api.get(studio, headers=editor["headers"]))
    # An editor replaces synthetic worker suggestions with a complete reviewed draft.
    groups = c3_studio.compose(WORKFLOW, snap["projection"])
    groups["research"]["hypothesis"] = "Test whether buyers prefer the matte finish."
    groups["measurement"]["measurable_action"] = snap["projection"]["product"]
    draft = accepted(api.patch(studio, headers=editor["headers"], json={"groups": groups, "expected_revision": raw["revision"]}))
    submitted = accepted(api.post(doc + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision": draft["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}

    def sign(group, by):
        return api.post(
            studio + "/approvals",
            headers=by["headers"],
            json={
                "group": group,
                "expected_revision": draft["revision"],
                "expected_asset_digest": draft["asset_digests"][group],
                "note": "Examined this asset against the approved business goal and evidence.",
            },
        )

    def share():
        return api.post(doc + "/share", headers=owner["headers"], json=terms | {"expires_at": expires})

    expires = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    assert sign("strategy", editor).status_code in (403, 404)
    assert sign("research", owner).status_code == 409
    assert accepted(sign("strategy", strategist))["approvals"].keys() == {"strategy"}
    mandate = revision(
        api,
        owner,
        knowledge,
        "studio-content-qualification",
        "qualification",
        {
            "approver_id": specialist["id"],
            "category": "unclassified",
            "basis": "Synthetic domain expert",
            "valid_until": "2099-01-01T00:00:00Z",
        },
        visibility="restricted",
    )
    finding = next(s for s in draft["findings"] if s["field"] == "studio.research.hypothesis")
    assert finding["outcome"] == "unresolved"
    resolution = terms | {
        "statement_id": finding["id"],
        "handle": "F1",
        "qualification_revision": mandate["id"],
        "reason": "The approved source documents the matte finish. Preference is explicitly a hypothesis to test.",
    }
    accepted(api.post(doc + "/content-evidence/resolutions", headers=specialist["headers"], json=resolution))
    accepted(sign("research", owner))
    assert approve(api, doc, owner, terms).status_code == 409
    signed = accepted(sign("measurement", owner))
    assert set(signed["approvals"]) == set(groups)
    assert accepted(sign("strategy", strategist))["approvals"] == signed["approvals"]

    # An in-flight demotion of the group reviewer must serialize final QA.
    with ThreadPoolExecutor(1) as jobs, psycopg.connect(lab.dsn) as change:
        demote(change, owner, strategist)
        pending = jobs.submit(approve, api, doc, owner, terms)
        wait_for_lock(lab.owner, change.info.backend_pid)
        change.commit()
        assert pending.result(timeout=10).status_code == 409
    assert "strategy" not in accepted(api.get(studio, headers=owner["headers"]))["approvals"]
    accepted(sign("strategy", owner))
    accepted(approve(api, doc, owner, terms))

    # The semantic resolution and group signoffs have separate authorities.
    demote(lab.owner, owner, specialist)
    assert share().status_code == 409
    lab.owner.execute("update memberships set role='admin' where tenant_id=%s and user_id=%s", (owner["tenant"], specialist["id"]))

    # Withdrawal invalidates the previously resolved claim at the sharing boundary.
    accepted(
        call(
            api,
            owner,
            knowledge,
            "/revisions/" + mandate["id"] + "/events",
            expected_digest=mandate["digest"],
            expected_sequence=1,
            state="withdrawn",
            reason="Synthetic qualification withdrawn.",
        )
    )
    assert share().status_code == 409
    assert accepted(api.get(base + "/reviews", headers=recipient["headers"])) == []
    edited = accepted(api.patch(studio, headers=editor["headers"], json={"groups": groups, "expected_revision": draft["revision"]}))
    assert edited["revision"] > draft["revision"] and edited["approvals"] == {}
    assert sign("strategy", owner).status_code == 412
    # Remove the unresolved hypothesis; the new first-party wording is independently signed.
    groups["research"]["hypothesis"] = c3_studio.compose(WORKFLOW, snap["projection"])["research"]["hypothesis"]
    draft = accepted(api.patch(studio, headers=editor["headers"], json={"groups": groups, "expected_revision": edited["revision"]}))
    submitted = accepted(api.post(doc + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision": draft["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    for group in groups:
        accepted(sign(group, specialist if group == "research" else owner))
    # A final reviewer can lose authority independently of the group reviewers.
    accepted(approve(api, doc, final_reviewer, terms))
    demote(lab.owner, owner, final_reviewer)
    assert share().status_code == 409
    # Restore the same principal solely to exercise the sharing-first ordering below.
    lab.owner.execute("update memberships set role='admin' where tenant_id=%s and user_id=%s", (owner["tenant"], final_reviewer["id"]))

    # Pause the already-authorized share at the actual INSERT. A later demotion
    # waits for that sharing transaction until the snapshot and receipt commit.
    with ThreadPoolExecutor(2) as jobs, psycopg.connect(lab.dsn) as barrier, psycopg.connect(lab.dsn) as change:
        barrier.execute("lock table client_reviews in share mode")
        first = jobs.submit(share)
        wait_for_lock(lab.owner, barrier.info.backend_pid)
        share_pid = lab.owner.execute("select pid from pg_stat_activity where %s=any(pg_blocking_pids(pid))", (barrier.info.backend_pid,)).fetchone()[0]
        second = jobs.submit(demote, change, owner, specialist)
        wait_for_lock(lab.owner, share_pid)
        barrier.commit()
        shared = accepted(first.result(timeout=10))
        second.result(timeout=10)
        change.commit()
    portal = base + "/reviews/" + shared["id"]
    accepted(api.put(base + "/members/" + recipient["id"] + "/review-rights", headers=owner["headers"], json={"can_comment": True, "can_decide": True}))
    before = accepted(
        api.post(
            portal + "/events",
            headers=recipient["headers"],
            json={
                "kind": "approved",
                "digest": shared["digest"],
                "request_key": "customer-decision-1",
            },
        )
    )
    assert before["status"] == "approved" and before["history"][-1]["actor_id"] == recipient["id"]
    assert before["preview"] and "PRIVATE_SYNTHETIC" not in str(before)
    assert api.get(portal, headers=other_customer["headers"]).status_code == 404
    accepted(api.patch(studio, headers=editor["headers"], json={"groups": groups, "expected_revision": draft["revision"]}))
    after = accepted(api.get(portal, headers=recipient["headers"]))
    assert after == before
