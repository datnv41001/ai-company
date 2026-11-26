"""Matched campaign execution against one business workspace per brief and identical pinned knowledge."""

# ruff: noqa: E402
import argparse
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "tests/evaluation/c3")]
from app import c3_assets, c3_customer_assets, c3_studio
from app.database import engine
from campaign_planner_journey import sign_edition
from channel import invoke
from commissions import WORKFLOWS, commission
from knowledge_fixtures import accepted
from recovery import FIRST_RUN, LabSessions, restore_small
from run_comparison import MarketingLab, app, lab_client, run_one
from server import MODELS, serve
from test_claim_desk import reader

FREEZE = "06c4da2b5508e1607bf44c0db698b2993fe3cfe5"
CASE_FILE = "tests/evaluation/department/briefs-v1.json"
PROTOCOL = "docs/evaluation/department-study/PROTOCOL.md"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_freeze():
    hashes = {}
    for name in (CASE_FILE, PROTOCOL):
        frozen = subprocess.check_output(["git", "show", FREEZE + ":" + name], cwd=ROOT)
        current = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        assert frozen == current
        hashes[name] = hashlib.sha256(current).hexdigest()
    return hashes


def control(plan, snaps):
    pack = {}
    for kind, snap in snaps.items():
        workflow, source = snap["workflow"], snap["projection"]
        groups = c3_studio.compose(workflow, source)
        if workflow == c3_assets.RESEARCH:
            groups.update(c3_customer_assets.strategy(source))
        pack[kind] = groups
    pack["campaign"] = {
        k: plan[k] for k in ("audience", "objective", "buyer_action", "target_outcome", "channels", "research_gaps", "measurement_plan", "work_packages")
    }
    pack["assets"] = {a["kind"]: a["body"] for a in plan["composed_assets"]}
    return pack


def run_treatment(lab, actors, plan, snapshots, api_path, folder, pack):
    base, owner, customer, *_ = lab.cases[0]
    first = {"campaign": pack["campaign"], "assets": dict(pack["assets"])}
    reviewed = {"campaign": pack["campaign"], "assets": dict(pack["assets"])}
    process = []
    for kind, workflow in WORKFLOWS.items():
        sub = folder / kind
        sub.mkdir(parents=True)
        rid = accepted(lab.api.post(api_path + "/plans/" + plan["id"] + "/runs/" + kind, headers=owner["headers"]))["id"]
        requests = {}

        def checkpoint(event, body):
            save(sub / "attempts" / (event["attempt_id"] + ".json"), {"event": event, "request": body})

        record = run_one(
            lab, "WF-03" if kind == "strategy" else "WF-13", "improved", sub, queued=(rid, workflow), request_log=requests, attempt_sink=checkpoint
        )
        save(sub / "requests.json", requests)
        save(sub / "worker.json", record)
        item = {"kind": kind, "run_id": rid, "state": record["state"], "first_attempt_success": record["first_pass_runtime"], "runtime_s": record["runtime_s"]}
        process.append(item)
        if "deliverable" not in record:
            item.update(error=record["last_error"])
            continue
        path = base + "/deliverables/" + record["deliverable"]["id"]
        studio = accepted(lab.api.get(path + "/studio", headers=actors[0]["headers"]))
        first[kind] = studio["groups"] | studio["customer_edition"]["groups"]
        try:
            _, review_id, receipt = sign_edition(lab.api, path, owner, customer, *actors, snapshots[kind], sub, record)
            reviewed[kind] = receipt["groups"]
            item.update(review_id=review_id, approved_snapshot=receipt["snapshot"]["digest"])
            save(sub / "signed-synthetic-edition.json", receipt)
        except AssertionError as error:
            item["edition_error"] = str(error)[:600]
    channel = invoke(lab.config, snapshots["landing"]["projection"], first)
    save(folder / "channel-attempt.json", channel)
    # The model channel assignment is draft-only. Current production customer QA applies to WF03/WF13.
    # Both complete candidate packs carry the same verbatim channel proposals for professional evaluation.
    for output in (first, reviewed):
        for kind in ("social", "ad"):
            output["assets"][kind] = channel["output"][kind] if channel["state"] == "returned" else None
        output["channel_status"] = "research_candidate_unreviewed" if channel["state"] == "returned" else "incomplete"
    save(folder / "first-package.json", first)
    save(folder / "reviewed-package.json", reviewed)
    save(folder / "workflow-evidence.json", process)
    return process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--control-only", action="store_true")
    parser.add_argument("--reuse-small", action="store_true")
    args = parser.parse_args()
    if engine.dialect.name != "postgresql" or engine.url.host not in ("127.0.0.1", "localhost", "::1") or not engine.url.database.startswith("amc_test"):
        raise ValueError("Use the isolated loopback amc_test PostgreSQL database")
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    info = {
        "freeze": FREEZE,
        "frozen_files": verify_freeze(),
        "checkout": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip(),
        "models": {},
        "participants": "scripted synthetic editorial and client roles",
        "issues": [],
    }
    save(out / "study.json", info)
    cases = json.loads((ROOT / CASE_FILE).read_text(encoding="utf-8"))["cases"]
    source_inputs = {}
    arms = list(MODELS)
    if args.reuse_small:
        original, source_inputs = restore_small(ROOT / "docs/evaluation/department-study/FIRST-STUDY.zip", out, info["frozen_files"])
        info["models"]["qwen05"] = original["models"]["qwen05"]
        info["resume"] = {
            "reused_run": FIRST_RUN,
            "interrupted_model": "qwen7",
            "unknown_prior_usage": True,
            "prior_resource_receipt": original["models"]["qwen7"],
            "matched_setup_attempts": {},
        }
        arms.remove("qwen05")
    with ExitStack() as resources:
        scenarios = []
        for case in cases:
            # New IDs protect the original records. Align every actual projected field,
            # including F1/F2 handle order, before doing any further inference.
            expected = {k: s["projection"] for k, s in source_inputs.get(case["id"], {}).items()}
            for setup_attempt in range(1, 25):
                api = resources.enter_context(lab_client(app))
                lab = MarketingLab(api, os.environ["AMC_MIGRATION_DSN"], case)
                owner, customer = lab.cases[0][1:3]
                prep, _, plan, snaps = commission(lab, case, ROOT, 0, None)
                observations = {k: s["projection"] for k, s in snaps.items()}
                if not expected or observations == expected:
                    break
                lab.close()
            else:
                raise ValueError("Failed to reproduce original knowledge projection exactly")
            actors = (reader(api, owner, "editor"), reader(api, owner, "admin"))
            lab.api = LabSessions(api, [lab.x, lab.y, customer, *actors])
            resources.callback(lab.close)
            if args.reuse_small:
                info["resume"]["matched_setup_attempts"][case["id"]] = setup_attempt
            pack = control(plan, snaps)
            folder = out / case["id"] / "control"
            save(folder / "first-package.json", pack)
            save(folder / "reviewed-package.json", pack)
            save(folder / "approved-inputs.json", snaps)
            save(folder / "commission.json", {"plan": plan, "model_attempts": 0, "provider_fee_usd": 0})
            scenarios.append((case, lab, actors, prep, observations))
        if args.control_only:
            return
        for seq, arm in enumerate(arms, 1):
            conditions = {}
            info["models"][arm] = conditions
            try:
                with serve(arm, out.parent / "models" / "department", conditions) as url:
                    for case, lab, actors, prep, observations in scenarios:
                        started = monotonic()
                        lab.config = replace(lab.config, url=url, model="amc-local")
                        _, api_path, plan, snaps = commission(lab, case, ROOT, seq, prep)
                        projection = {k: s["projection"] for k, s in snaps.items()}
                        assert canonical(projection) == canonical(observations), "Approved scope or business facts changed across arms"
                        pack = control(plan, snaps)
                        folder = out / case["id"] / arm
                        save(
                            folder / "commission.json",
                            {
                                "plan": plan,
                                "manifest_projection_sha256": canonical(projection),
                                "manifests": {k: {"id": s["id"], "digest": s["digest"]} for k, s in snaps.items()},
                            },
                        )
                        process = run_treatment(lab, actors, plan, snaps, api_path, folder, pack)
                        conditions.setdefault("case_wall_seconds", {})[case["id"]] = round(monotonic() - started, 3)
                        for result in process:
                            if "approved_snapshot" not in result:
                                info["issues"].append([case["id"], arm, result])
            finally:
                save(out / "study.json", info)
    # Failed or unresolved runs remain in the comparison, rather than being replaced by the control.
    print(json.dumps({"arms": list(info["models"]), "incomplete_workflows": len(info["issues"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
