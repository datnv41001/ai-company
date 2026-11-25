"""Summarize synthetic Studio receipts offline. No model, database, network or expert scoring."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import median

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FROZEN = "993f93551657734fbea73f6c8898633a18df9dd573fcd0ff78b5e01653bc3346"
REGRESSION = "c497ff707c986acaa3c48ba799ab1a378f194d3e7cd4262834d41a4aae0fe477"
WEIGHTS = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
WF = {"WF-03": "WF-03/research-strategy-draft@3", "WF-13": "WF-13/landing-seo-draft@6"}
OLD = {"WF-03": "WF-03/research-strategy-draft@2", "WF-13": "WF-13/landing-seo-draft@5"}
METADATA = ("checkout", "provider", "model_sha256", "build", "cases_sha256", "worker_concurrency")
MODES = {"study": "c3-product-v2", "recovery": "c3-unit-recovery", "smoke": "c3-internal-receipts"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def read(path):
    return json.loads(path.read_bytes())


def plan(root, mode):
    filename, fixed, count = {
        "study": ("qualification-v2.json", FROZEN, 10),
        "recovery": ("holdout-v1.json", REGRESSION, 20),
        "smoke": ("cases.json", None, 2),
    }[mode]
    raw = (root / "tests/evaluation/c3" / filename).read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()
    require(not fixed or fingerprint == fixed, "Unexpected case file digest")
    cases = json.loads(raw)["cases"]
    if mode == "recovery":
        cases = [c for c in cases if c["persona"] in ("service", "inhouse")]
    assignments = {"materials": "WF-03", "seller": "WF-13"} if mode == "smoke" else {c["id"]: c["workflow"] for c in cases}
    require(len(assignments) == count, "Unexpected assigned population")
    return assignments, fingerprint


def pins(root):
    releases = {}
    for kind, name in (("WF-03", "research-strategy-v3"), ("WF-13", "landing-seo-v6")):
        methods = read(root / "catalog" / (name + ".json"))["marketing_methods"]
        releases[kind] = {key: digest(value) for key, value in methods.items()}
    require(len(set().union(*releases.values())) == 7, "Expected seven versioned skills")
    return releases


def profile(groups):
    return {f"{group}.{name}": value for group, fields in groups.items() for name, value in fields.items()}


def composition(base, treatment):
    left, right = profile(base["groups"]), profile(treatment["groups"])
    require(left.keys() == right.keys(), "Composer group/field sets differ")

    def side(value, fields):
        return {
            "groups_digest": digest(value["groups"]),
            "fields": len(fields),
            "nonempty_fields": sum(bool(isinstance(v, str) and v.strip()) for v in fields.values()),
            "structural_findings": len(value["field_findings"]),
            "finding_reasons": dict(Counter(row["reason"] for row in value["field_findings"])),
        }

    return {"first": side(base, left), "second": side(treatment, right), "changed_fields": [k for k in left if left[k] != right[k]]}


def usage(record):
    draws = record["attempts"]
    ids = [a["attempt_id"] for a in draws]
    require(all(isinstance(k, str) and k for k in ids) and len(ids) == len(set(ids)), "Invalid attempt IDs")
    for a in draws:
        require(sha(a["request_sha256"]) and ("raw_output" in a or "error" in a), "Missing request or outcome")
    result = {"attempts": len(draws), "unmetered_attempts": sum("input_tokens" not in a or "output_tokens" not in a for a in draws)}
    for name in ("input_tokens", "output_tokens"):
        observed = [a[name] for a in draws if name in a]
        require(all(type(v) is int and v >= 0 for v in observed), "Invalid token count")
        result[name] = sum(observed)
    require(all(record[k] == result[k] for k in ("input_tokens", "output_tokens", "unmetered_attempts")), "Token totals disagree")
    fee, seconds = record["provider_fee_usd"], record["runtime_s"]
    require(fee == 0 and math.isfinite(seconds) and seconds >= 0, "Invalid local fee or runtime")
    return result | {"provider_fee_usd": fee, "runtime_s": seconds}


def identity(record, meta, cid, workflow, arm):
    require(all(record.get(k) == meta[k] for k in METADATA), "Per-case conditions mismatch")
    require((record["case"], record["workflow"], record["arm"]) == (cid, workflow, arm), "Case/release mismatch")
    require(bool(record["run_id"]), "Missing run ID")


def prior_summary(record, meta, cid, kind):
    identity(record, meta, cid, OLD[kind], "projected")
    return {
        "workflow": record["workflow"],
        "state": record["state"],
        "run": record["run_id"],
        "draft_id": (record.get("deliverable") or {}).get("id"),
        "usage": usage(record),
    }


def matched_control(control, record, kind):
    role = "strategy" if kind == "WF-03" else "content"
    attempts = [a for a in record["attempts"] if a["attempt_id"] == control["paired_treatment_attempt_id"]]
    require(len(attempts) == 1 and attempts[0]["schema"] == "c3_skills_" + role and "raw_output" in attempts[0], "Absent paired full-method role invocation")
    require(control["scope"] == role and control["max_invocations"] == 1 and control["provider_fee_usd"] == 0, "Unbounded or unscoped control invocation")
    require(
        sha(control["same_user_input_digest"])
        and control["same_user_input_digest"] == control["control_user_input_digest"]
        and sha(control["schema_digest"])
        and control["schema_digest"] == control["control_schema_digest"]
        and attempts[0]["request_sha256"] == control["treatment_attempt_request_sha256"],
        "Input/schema/worker request mismatch",
    )
    require(
        sha(control["control_request_digest"])
        and sha(control["treatment_request_digest"])
        and control["control_request_digest"] != control["treatment_request_digest"],
        "Invalid instruction contrast",
    )
    require("raw_output" in control or "error" in control, "Control has no observed result")
    require(math.isfinite(control["seconds"]) and control["seconds"] >= 0, "Invalid control timing")
    for key in ("input_tokens", "output_tokens"):
        require(key not in control or type(control[key]) is int and control[key] >= 0, "Invalid control token usage")
    result = {
        k: control[k]
        for k in (
            "scope",
            "paired_treatment_attempt_id",
            "same_user_input_digest",
            "schema_digest",
            "control_request_digest",
            "treatment_request_digest",
            "treatment_attempt_request_sha256",
            "provider_fee_usd",
            "seconds",
        )
    }
    result.update(
        input_tokens=control.get("input_tokens"), output_tokens=control.get("output_tokens"), returned="raw_output" in control, error=control.get("error")
    )
    if "groups" in control:
        result["generic_vs_full_method"] = composition(control, record["composed"])
    return result


def internal(record, meta, cid, kind, mode, expected_pins):
    identity(record, meta, cid, WF[kind], "improved")
    require(
        record["origin"] == "internal" and record["task_id"] and sha(record["projection_digest"]) and sha(record["guideline"]["digest"]),
        "Missing internal task or pinned projection/guideline",
    )
    require(record["skill_digests"] == expected_pins, "Skill pins differ from release catalog")
    require(record["deterministic"]["model_calls"] == 0, "Deterministic arm used a model")
    seconds = record["automated_journey_seconds"]
    require(math.isfinite(seconds) and seconds >= 0, "Invalid automated journey time")
    result = {
        "workflow": record["workflow"],
        "state": record["state"],
        "run": record["run_id"],
        "task": record["task_id"],
        "buyer_action": record["task_intent"]["buyer_action"],
        "guideline_digest": record["guideline"]["digest"],
        "projection_digest": record["projection_digest"],
        "release_skill_digests": record["skill_digests"],
        "usage": usage(record),
        "automated_journey_s": seconds,
    }
    if mode == "recovery":
        fix = record["correction"]
        require(
            fix["initial_status"] == "needs_input"
            and fix["unit_before"] == "service"
            and fix["unit_confirmed"] != "service"
            and fix["claim"] != fix["original_claim"]
            and fix["offer"] != fix["original_offer"]
            and sha(fix["original_offer_digest"])
            and all(fix[k] for k in ("claim", "offer", "source", "binding", "source_excerpt")),
            "Recovery lacks revision evidence",
        )
        times = fix["timing_seconds"]
        require(
            set(times) == {"seed_and_task", "clarify_and_propose", "approve", "resume"} and all(math.isfinite(v) and v >= 0 for v in times.values()),
            "Missing correction stage timings",
        )
        result["correction"] = {
            k: fix[k]
            for k in (
                "original_claim",
                "claim",
                "original_offer",
                "offer",
                "original_offer_digest",
                "source",
                "binding",
                "unit_before",
                "unit_confirmed",
                "timing_seconds",
            )
        }
    doc = record.get("deliverable")
    if not doc:
        return result
    require(
        sha(record["runtime_fingerprint"])
        and sha(record["manifest"]["digest"])
        and sha(record["binding"]["manifest_digest"])
        and record["binding"]["workflow"] == WF[kind],
        "Missing registry/manifest provenance",
    )
    require(doc["digest"] == digest({"title": doc["title"], "preview": doc["body"]}), "Draft digest mismatch")
    current = record["staff"]["sections"]["customer_preview"]["current"]
    staff_sections = {"research_notes", "strategy_decisions", "buyer_copy", "seo_fields", "evidence_report", "measurement_plan", "customer_preview"}
    require(set(record["staff"]["sections"]) == staff_sections and current["digest"] == doc["digest"], "Unbound staff preview")
    stages = {a["schema"] for a in record["attempts"] if "raw_output" in a}
    roles = ("director", "research", "strategy") if kind == "WF-03" else ("director", "content", "seo")
    require(stages == {"c3_skills_" + r for r in roles}, "Incomplete staged model receipts")
    edit = record["edited_example"]
    before, after = edit["before"], edit["after"]
    oldrev, newrev = before["revision"], after["revision"]
    gate = edit["qa_evidence"]["content_evidence"]
    group, field = edit["field"]
    require(
        doc["qa_revision"] == oldrev
        and newrev == oldrev + 1
        and gate["qa_revision"] == newrev
        and gate["content_digest"] == edit["qa_evidence"]["content_digest"]
        and sha(gate["content_digest"]),
        "Edited field or QA revision mismatch",
    )
    result["draft"] = {
        "id": doc["id"],
        "revision": oldrev,
        "digest": doc["digest"],
        "status": doc["status"],
        "runtime_fingerprint": record["runtime_fingerprint"],
        "knowledge_manifest_digest": record["manifest"]["digest"],
        "registry_manifest_digest": record["binding"]["manifest_digest"],
        "staff_sections": sorted(staff_sections),
        "model_stages_with_output": sorted(stages),
    }
    result["edit"] = {
        "kind": edit["kind"],
        "field": edit["field"],
        "revision": newrev,
        "qa_digest": gate["content_digest"],
        "field_changed": before["groups"][group][field] != after["groups"][group][field],
        "state": after["status"],
        "evidence_outcomes": dict(Counter(s["outcome"] for s in gate["statements"])),
    }
    result["deterministic_vs_full_method"] = composition(record["deterministic"], record["composed"])
    return result


def contrast_totals(comparisons):
    return {
        "paired_drafts": len(comparisons),
        "different_fields": sum(len(c["changed_fields"]) for c in comparisons),
        **{side: {k: sum(c[side][k] for c in comparisons) for k in ("fields", "nonempty_fields", "structural_findings")} for side in ("first", "second")},
    }


def series(folder, mode, checkout, assignments, file_hash, catalog):
    errors = {}
    rows = {}
    all_pins = {k: v for items in catalog.values() for k, v in items.items()}
    meta = None
    try:
        meta = read(folder / "conditions.json")
        require(
            all(k in meta for k in METADATA)
            and meta["checkout"] == checkout
            and meta["cases_sha256"] == file_hash
            and meta["model_sha256"] == WEIGHTS
            and meta["provider"] == "llama.cpp loopback"
            and meta["worker_concurrency"] == 1,
            "Invalid series conditions",
        )
    except (OSError, ValueError, KeyError, TypeError) as e:
        errors["conditions"] = str(e)
    if folder.is_dir() and "conditions" not in errors:
        for path in sorted(folder.glob("*/result.json")):
            try:
                cid = path.parent.name
                require(cid in assignments, "Unassigned case")
                record = read(path)
                kind = assignments[cid]
                row = internal(record, meta, cid, kind, mode, catalog[kind])
                require(row["run"] not in {v["run"] for v in rows.values()}, "Reused run ID")
                rows[cid] = row
                if mode == "study":
                    try:
                        prior = prior_summary(read(path.parent / "previous/result.json"), meta, cid, kind)
                        require(prior["run"] != row["run"], "Reused reference run")
                        row["previous"] = prior
                    except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
                        errors[cid + "/previous"] = str(e)
                    if "draft" in row:
                        try:
                            row["matched_control"] = matched_control(record["matched_instruction_control"], record, kind)
                        except (ValueError, KeyError, TypeError, IndexError) as e:
                            errors[cid + "/matched-control"] = str(e)
            except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
                errors[path.parent.name] = str(e)
    try:
        require(read(folder / "skill-digests.json") == all_pins, "Final skill digests differ from catalog")
    except (OSError, ValueError, KeyError, TypeError) as e:
        errors["skill_registry"] = str(e)
    for_total = list(rows.values())
    controls = [r["matched_control"] for r in for_total if "matched_control" in r]
    previous = [r["previous"] for r in for_total if "previous" in r]

    def aggregate(entries):
        return {k: sum(e[k] for e in entries) for k in ("attempts", "input_tokens", "output_tokens", "unmetered_attempts", "provider_fee_usd")}

    corrected = [r["correction"] for r in for_total if "correction" in r]
    timings = {k: median(c["timing_seconds"][k] for c in corrected) for k in corrected[0]["timing_seconds"]} if corrected else {}
    return {
        "assigned": len(assignments),
        "observed": len(rows),
        "files_present": sum(1 for _ in folder.glob("*/result.json")),
        "missing_or_invalid_case_ids": sorted(set(assignments) - rows.keys()),
        "complete": not errors and rows.keys() == assignments.keys(),
        "errors": errors,
        "conditions": meta,
        "states": dict(Counter(r["state"] for r in for_total)),
        "drafts": sum("draft" in r for r in for_total),
        "edits_with_current_qa": sum("edit" in r for r in for_total),
        "corrected": sum("correction" in r for r in for_total),
        "technical_pairs": sum("previous" in r for r in for_total),
        "confirmed_units": dict(Counter(c["unit_confirmed"] for c in corrected)),
        "median_correction_stage_s": timings,
        "release_pins_on_drafted_cases": {k: v for r in for_total if "draft" in r for k, v in r["release_skill_digests"].items()},
        "observed_treatment_usage": aggregate([r["usage"] for r in for_total]),
        "previous_release_states": dict(Counter(r["state"] for r in previous)),
        "previous_release_drafts": sum(bool(r["draft_id"]) for r in previous),
        "both_releases_generated": sum(bool(r.get("draft") and r.get("previous", {}).get("draft_id")) for r in for_total),
        "observed_previous_usage": aggregate([p["usage"] for p in previous]),
        "matched_role_controls": len(controls),
        "controls_with_comparison": sum("generic_vs_full_method" in v for v in controls),
        "deterministic_vs_full_method": contrast_totals([r["deterministic_vs_full_method"] for r in for_total if "draft" in r]),
        "generic_vs_full_method": contrast_totals([c["generic_vs_full_method"] for c in controls if "generic_vs_full_method" in c]),
        "observed_control_tokens": {k: sum(v[k] for v in controls if v[k] is not None) for k in ("input_tokens", "output_tokens")},
        "unmetered_controls": sum(v["input_tokens"] is None or v["output_tokens"] is None for v in controls),
        "observed_control_provider_fee_usd": sum(v["provider_fee_usd"] for v in controls),
        "median_control_s": median(v["seconds"] for v in controls) if controls else None,
        "median_automated_journey_s": median(r["automated_journey_s"] for r in for_total) if rows else None,
        "cases": rows,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("artifact", type=Path, help="Directory containing the three downloaded C3 artifact directories")
    cli.add_argument("--checkout", required=True, help="Exact expected checkout SHA for all receipts")
    cli.add_argument("--source-root", type=Path, default=ROOT, help="Matching source checkout with the frozen case manifest and catalog")
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--require-complete", action="store_true")
    cli.add_argument("--buyer-journey-out", type=Path,
                     help="Also replay the pinned 45582688602 study as a separate staff-only composer regression")
    args = cli.parse_args()
    if args.buyer_journey_out:
        require(args.buyer_journey_out.resolve() != args.out.resolve(), "Keep candidate and original results separate")
    require(re.fullmatch(r"[0-9a-f]{40}", args.checkout), "Expected exact checkout SHA")
    catalog = pins(args.source_root)
    results = {mode: series(args.artifact / name, mode, args.checkout, *plan(args.source_root, mode), catalog) for mode, name in MODES.items()}
    complete = all(section["complete"] for section in results.values())
    report = {
        "schema": "amc.studio-qualification-summary/1",
        "checkout": args.checkout,
        "complete": complete,
        "series": results,
        "human_accepted": None,
        "expert_evidence_support": None,
        "stronger_model_advantage": None,
        "human_edit_minutes": None,
        "time_saved_vs_manual": None,
        "cost_per_professionally_accepted_asset": None,
        "scope": "Synthetic inputs. Prior releases change multiple components. Only the selected role instruction is paired on matched inputs. Automated journey includes scripted setup, correction, editing and any control invocation.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    if args.buyer_journey_out:
        from grounded_composer_study import save_study
        save_study(args.artifact / MODES["study"], args.buyer_journey_out, args.source_root)
    if args.require_complete and not complete:
        raise SystemExit("Incomplete evidence; see report for missing cases and files")


if __name__ == "__main__":
    main()
