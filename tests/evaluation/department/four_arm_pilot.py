"""Custodian-only extension of the existing matched RFQ/service practitioner kit."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
from zipfile import ZIP_DEFLATED, ZipFile

from pilot import ROLES, blank, by_arm, check, dump, read

ARMS = ("manual", "control", "ai_assisted", "ai_plus_independent_qa")
KIT = Path(__file__).resolve().parents[3] / "docs/evaluation/department-study/PILOT-KIT"


def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    key = read(KIT / "custodian.json")
    design = {}
    with ZipFile(KIT / "01-manual.zip") as manual, ZipFile(KIT / "02-candidates.zip") as candidates, \
            ZipFile(out / "work-orders.zip", "w", ZIP_DEFLATED) as work, ZipFile(out / "scorecards.zip", "w", ZIP_DEFLATED) as scores:
        scores.writestr("RUBRIC.md", candidates.read("RUBRIC.md"))
        for brief in sorted({k.split("/")[0] for k in key}):
            brief_text = manual.read(brief + "/brief.md")
            scores.writestr(brief + "/brief.md", brief_text)
            arms = list(ARMS)
            secrets.SystemRandom().shuffle(arms)
            for arm in arms:
                alias = "P-" + secrets.token_hex(5)
                name = brief + "/" + alias
                design[name] = arm
                work.writestr(name + "/brief.md", brief_text)
                if arm == "manual":
                    work.writestr(name + "/starting.md", manual.read(brief + "/deliverable.md"))
                else:
                    prior = "control" if arm == "control" else "qwen15"
                    folder = next(k for k, v in key.items() if k.startswith(brief + "/") and v == prior)
                    work.writestr(name + "/starting.md", candidates.read(folder + "/first.md"))
                # Only the custodian issues work orders. The scoring ZIP contains
                # no D-only form, source model or indicator of the treatment.
                work.writestr(name + "/treatment.txt", arm + "\n")
                if arm == "ai_plus_independent_qa":
                    work.writestr(name + "/preqa.json", dump({"name": name, "actor_code": None, "consent": False,
                        "first_sha256": None, "final_sha256": None, "findings_or_no_change_reason": None,
                        "qa_seconds": None, "labor_vnd": None, "cost_ref": None}))
                for role in ROLES:
                    form = blank(alias, brief) | {"role": role}
                    if role == "marketer":
                        form["overhead"]["model_vnd"] = None
                    scores.writestr(name + "/observation-" + role + ".json", dump(form))
    (out / "custodian.json").write_text(dump(design), encoding="utf-8")


def score(design, submissions, qa_reviews, directory):
    if any(arm not in ARMS for arm in design.values()):
        raise ValueError("Unrecognized arm")
    for submission in submissions:
        overhead = submission["overhead"]
        if overhead.get("model_vnd") is not None and (submission["role"] != "marketer" or not overhead["receipt_refs"]):
            raise ValueError("The marketer supplies model cost and a receipt reference")
    result = check(design, submissions, directory)
    reviewers = {}
    observers = {row["actor_code"] for row in submissions}
    for review in qa_reviews:
        name = review["name"]
        if name in reviewers or design.get(name) != "ai_plus_independent_qa":
            raise ValueError("Unexpected or duplicate independent production QA")
        if not review["actor_code"] or review["actor_code"] in observers or review["consent"] is not True:
            raise ValueError("D requires a separate consenting pre-delivery reviewer")
        for field in ("labor_vnd", "qa_seconds"):
            value = review[field]
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Invalid QA effort")
        if review["labor_vnd"] is not None and not review["cost_ref"]:
            raise ValueError("Pre-delivery labor needs an observed basis")
        reviewers[name] = review
    for name, arm in design.items():
        row = result.setdefault(name, {"arm": arm, "observations": {}, "verified_business_decision": None, "recorded_total_vnd": None})
        producer = row["observations"].get("marketer", {})
        model_cost = producer.get("overhead", {}).get("model_vnd")
        if model_cost is not None and (type(model_cost) is not int or model_cost < 0):
            raise ValueError("Invalid model cost")
        extra_labor = 0
        if arm == "ai_plus_independent_qa":
            review = reviewers.get(name, {})
            path = (directory / name / "first.artifact").resolve()
            previous = None
            if path.is_relative_to(directory.resolve()) and path.is_file():
                with path.open("rb") as data:
                    previous = hashlib.file_digest(data, "sha256").hexdigest()
            final = row.get("artifact_verification", {}).get("retained_sha256")
            row["preqa_verified"] = bool(final and previous and review.get("first_sha256") == previous and
                                          review.get("final_sha256") == final and review.get("findings_or_no_change_reason"))
            row["preqa_seconds"] = review.get("qa_seconds")
            extra_labor = review.get("labor_vnd")
            if not row["preqa_verified"]:
                row["verified_business_decision"] = None
                row["recorded_total_vnd"] = None
            labor = row.get("recorded_labor_cost_per_business_accepted_vnd")
            row["recorded_labor_cost_per_business_accepted_vnd"] = (
                labor + extra_labor if row["verified_business_decision"] is True and None not in (labor, extra_labor) else None
            )
        costs = [row["recorded_total_vnd"], model_cost, extra_labor]
        row["recorded_total_vnd"] = sum(costs) if None not in costs else None
        row["all_in_cost_per_business_accepted_vnd"] = row["recorded_total_vnd"] if row["verified_business_decision"] is True else None
    return {"packages": result, "arms": by_arm(result)}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare").add_argument("out", type=Path)
    scorer = sub.add_parser("score")
    for field in ("design", "observations", "preqa", "artifacts"):
        scorer.add_argument(field, type=Path)
    args = p.parse_args()
    if args.cmd == "prepare":
        prepare(args.out)
    else:
        print(json.dumps(score(read(args.design), read(args.observations), read(args.preqa), args.artifacts), ensure_ascii=False, indent=2))
