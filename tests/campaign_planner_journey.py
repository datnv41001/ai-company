"""Exercise two new campaign inputs on disposable PostgreSQL and a real, pinned loopback Qwen model."""

# ruff: noqa: E402 -- the operational script shares the existing restricted Workforce lab.
import argparse
from dataclasses import replace
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "tests/evaluation/c3")]

from app import c3_assets, c3_studio
from app.models import utcnow
from campaign_planner_editor import reviewed_edition
from campaign_planner_fixtures import CASES, prepare_inputs
from knowledge_fixtures import accepted
from migrations.apply import publish_registry
from qualification import conditions
from run_comparison import MarketingLab, app, lab_client, run_one
from test_c3_content_gate import approve
from test_claim_desk import reader


def save(out, value):
    out.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sign_edition(api, path, owner, customer, editor, qa_actor, snap, folder, record=None):
    studio = path + "/studio"
    proposal = accepted(api.get(studio, headers=editor["headers"]))
    edition = proposal["customer_edition"]
    baseline = c3_studio.compose(snap["workflow"], snap["projection"]) | edition["groups"]
    groups, result, trail = reviewed_edition(api, path, editor, qa_actor, proposal, baseline, record)
    submitted = accepted(api.post(path + "/submit", headers=editor["headers"]))
    terms = {"expected_qa_revision": result["revision"], "expected_content_digest": submitted["qa_evidence"]["content_digest"]}
    assessment = accepted(api.get(path + "/content-evidence", headers=qa_actor["headers"]))
    rejected = [e for e in assessment["statements"] if e["outcome"] not in ("verified", "editorial", "reviewed")]
    save(
        folder / "editor-review.json",
        {
            "groups": groups,
            "unresolved": rejected,
            "terms": terms,
            "field_history": trail,
            "retained_distinct_model_fields": sum(item["decision"] == "retained_model_verbatim" for item in trail.values()),
        },
    )
    for group in groups:
        accepted(
            api.post(
                studio + "/approvals",
                headers=qa_actor["headers"],
                json={
                    "expected_revision": result["revision"],
                    "expected_asset_digest": result["asset_digests"][group],
                    "group": group,
                    "note": "Đã đối chiếu các trường và điều kiện với manifest của chiến dịch tổng hợp.",
                },
            )
        )
    accepted(approve(api, path, owner, terms))
    review = accepted(api.post(path + "/share", headers=owner["headers"], json={**terms, "expires_at": (utcnow() + timedelta(days=2)).isoformat()}))
    base = path.split("/deliverables/")[0]
    accepted(api.put(base + "/members/" + customer["id"] + "/review-rights", headers=owner["headers"], json={"can_comment": True, "can_decide": True}))
    receipt = accepted(
        api.post(
            base + "/reviews/" + review["id"] + "/events",
            headers=customer["headers"],
            json={"kind": "approved", "digest": review["digest"], "request_key": "accept-synthetic-edition"},
        )
    )
    return (
        terms,
        review["id"],
        {
            "source": "scripted editor and QA, synthetic customer",
            "groups": groups,
            "approval_terms": terms,
            "snapshot": {k: receipt[k] for k in ("id", "version", "digest", "status", "preview")},
        },
    )


def execute_case(lab, case, folder, meta, *, downstream=True):
    base, owner, customer, client_id, campaign = lab.cases[0]
    api = lab.api
    path = base + "/campaigns/" + campaign + "/engine"
    workflows = (c3_assets.RESEARCH, c3_assets.LANDING) if case["buyer_action"] == "rfq" else (c3_assets.LANDING,)
    for workflow in workflows:
        file = "research-strategy-v3.json" if workflow == c3_assets.RESEARCH else "landing-seo-v6.json"
        release = json.loads((ROOT / "catalog" / file).read_text(encoding="utf-8"))
        publish_registry(lab.owner, release)
        accepted(
            api.put(
                base + "/workforce/registry/" + campaign,
                headers=owner["headers"],
                json={"action": "activate", "workflow": workflow, "skills": release["required"]},
            )
        )
    snaps, _ = prepare_inputs(api, owner, customer, client_id, lab.brand, campaign, case, workflows)
    save(folder / "approved-inputs.json", snaps)
    proposal = accepted(
        api.post(
            path + "/plans",
            headers=owner["headers"],
            json={"key": uuid4().hex, "expected_revision": 0, "budget_vnd": 3_000_000, "duration_days": 21, "manifest_ids": [s["id"] for s in snaps]},
        )
    )
    accepted(
        api.post(path + "/plans/" + proposal["id"] + "/approve", headers=owner["headers"], json={"key": uuid4().hex, "expected_digest": proposal["digest"]})
    )
    plan = accepted(api.get(path + "/planner", headers=owner["headers"]))["active"]
    assert plan["selling_unit"] == case["unit"]
    editor, reviewer = reader(api, owner, "editor"), reader(api, owner, "admin")
    summary = {
        "case": case["id"],
        "conditions": meta,
        "plan": plan,
        "runs": [],
        "accepted_editions": [],
        "participants": "Scripted synthetic operator, editor, reviewer and customer. Practitioner results unmeasured.",
    }
    save(folder / "journey.json", summary)
    for snap in snaps:
        kind = "strategy" if snap["workflow"] == c3_assets.RESEARCH else "landing"
        rid = accepted(api.post(path + "/plans/" + plan["id"] + "/runs/" + kind, headers=owner["headers"]))["id"]
        repeat = accepted(api.post(path + "/plans/" + plan["id"] + "/runs/" + kind, headers=owner["headers"]))
        assert repeat["id"] == rid
        location = folder / kind
        location.mkdir(exist_ok=True)
        record = run_one(lab, "WF-03" if kind == "strategy" else "WF-13", "improved", location, queued=(rid, snap["workflow"]))
        summary["runs"].append(
            {k: record[k] for k in ("run_id", "state", "last_error", "input_tokens", "output_tokens", "runtime_s", "provider_fee_usd", "attempts")}
        )
        save(location / "worker.json", record)
        save(folder / "journey.json", summary)
        if not record.get("deliverable"):
            continue
        did = record["deliverable"]["id"]
        terms, review_id, receipt = sign_edition(api, base + "/deliverables/" + did, owner, customer, editor, reviewer, snap, location, record)
        summary["accepted_editions"].append(receipt)
        save(folder / "journey.json", summary)
        if kind == "landing" and case["buyer_action"] == "rfq" and downstream:
            from campaign_operations_journey import exercise

            summary["operating_result"] = exercise(api, base, owner, plan, did, terms, customer, approver=reviewer, review_id=review_id)
    summary["production"] = accepted(api.get(path + "/plans/" + plan["id"] + "/production", headers=owner["headers"]))
    save(folder / "journey.json", summary)
    if os.environ.get("AMC_ENGINE_EVIDENCE") and case["buyer_action"] == "rfq":
        from browser_c3_content_gate import local_api
        from campaign_engine_browser import capture_campaign

        with local_api() as origin:
            capture_campaign(origin, owner["email"], owner["password"], owner["tenant"], campaign, Path(os.environ["AMC_ENGINE_EVIDENCE"]))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    meta, url = conditions(Path(__file__).with_name("campaign_planner_fixtures.py"))
    failures = []
    for case in CASES:
        folder = args.out / case["id"]
        folder.mkdir(parents=True, exist_ok=False)
        with lab_client(app) as api:
            lab = MarketingLab(api, os.environ["AMC_MIGRATION_DSN"], case)
            try:
                lab.config = replace(lab.config, model=os.getenv("AMC_WORKFORCE_MODEL", "amc-local"), url=url)
                result = execute_case(lab, case, folder, meta)
                if not all(run["state"] == "awaiting_qa" for run in result["runs"]):
                    raise RuntimeError("Workforce run failed; see preserved attempts and outputs")
            except Exception as error:
                import traceback

                failures.append(case["id"])
                save(folder / "failure.json", {"case": case["id"], "error": str(error)})
                traceback.print_exc()
            finally:
                lab.close()
    if failures:
        raise SystemExit("Incomplete synthetic journeys: " + ", ".join(failures))


if __name__ == "__main__":
    main()
