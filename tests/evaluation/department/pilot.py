"""Prepare source-blind complete packages and validate separately submitted practitioner observations."""

import argparse
import json
from pathlib import Path
import secrets
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = ("buyer_market", "positioning", "strategy", "landing", "seo", "social", "ad", "measurement")
ROLES = ("marketer", "independent_reviewer", "sales_or_owner")
EFFORT = ("clarification_seconds", "production_seconds", "editing_seconds", "qa_seconds", "time_to_usable_seconds")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def markdown(data, level=2):
    if isinstance(data, dict):
        return "\n\n".join("#" * min(level, 6) + " " + key.replace("_", " ") + "\n\n" + markdown(v, level + 1) for key, v in data.items())
    if isinstance(data, list):
        return "\n".join("- " + markdown(v, level) for v in data)
    return str(data) if data is not None else "(chưa có)"


def brief_text(c):
    fields = (
        "company",
        "brand",
        "product",
        "sku",
        "audience",
        "objective",
        "buyer_action",
        "kpi",
        "kpi_method",
        "kpi_window",
        "hypotheses",
        "exclusions",
        "cta",
    )
    return markdown(
        {k: c[k] for k in fields}
        | {
            "approved_description": c["wording"] + ". " + c["qualifier"],
            "approved_price": f"{c['amount']} VND / 1 {c['unit']}; gồm thuế. Xác nhận số lượng trước khi đặt.",
        }
    )


def blank(alias, brief):
    return {
        "brief": brief,
        "package": alias,
        "actor_code": None,
        "role": None,
        "consent_and_permitted_inputs": False,
        "first_pass_accepted": None,
        "usable_after_editing": None,
        "decision_reason": None,
        "reference_to_delivered_revision": None,
        "sales_usefulness_0_2": None,
        "business_accepted": None,
        "effort": {k: None for k in EFFORT},
        "allocated_cost_vnd": None,
        "cost_source": None,
        "rubric": {k: {"score_0_2": None, "evidence": None} for k in RUBRIC},
        "blocking_issue": None,
    }


def pack(data, out):
    out.mkdir(parents=True, exist_ok=False)
    source = read(ROOT / "tests/evaluation/department/briefs-v1.json")
    labels = {}
    keys = ["control", "qwen05", "qwen7", "qwen15"]
    secrets.SystemRandom().shuffle(keys)
    with ZipFile(out / "01-manual.zip", "w", compression=ZIP_DEFLATED) as manual, ZipFile(out / "02-candidates.zip", "w", compression=ZIP_DEFLATED) as blind:
        rubric = (ROOT / "docs/evaluation/department-study/PROTOCOL.md").read_text(encoding="utf-8").split("## Rubric")[1]
        for zipfile in (manual, blind):
            zipfile.writestr("RUBRIC.md", "## Rubric" + rubric)
            zipfile.writestr("HUONG-DAN.md", (ROOT / "docs/evaluation/department-study/PILOT.md").read_text(encoding="utf-8"))
        order = []
        for i, c in enumerate(source["cases"]):
            case = c["id"]
            for zipfile in (manual, blind):
                zipfile.writestr(case + "/brief.md", brief_text(c))
            labels[case + "/manual"] = "manual"
            manual.writestr(case + "/observation.json", dump(blank("manual", case)))
            manual.writestr(case + "/deliverable.md", "# Bản bàn giao của người làm Marketing\n\n" + "\n\n".join("## " + k for k in RUBRIC))
            for arm in keys if i % 2 == 0 else reversed(keys):
                alias = "P-" + secrets.token_hex(4)
                prefix = case + "/" + alias
                order.append(prefix)
                labels[prefix] = arm
                for stage in ("first", "reviewed"):
                    values = read(data / case / arm / (stage + "-package.json"))
                    # The custodian keeps treatments and provenance outside the packets being scored.
                    visible = {k: v for k, v in values.items() if k != "channel_status"}
                    blind.writestr(prefix + "/" + stage + ".md", markdown(visible))
                blind.writestr(prefix + "/observation.json", dump(blank(alias, case)))
        blind.writestr("ORDER.txt", "\n".join(order))
    (out / "custodian.json").write_text(dump(labels), encoding="utf-8")


def check(key, rows):
    result = {}
    observed = set()
    identities = {}
    for row in rows:
        name = row["brief"] + "/" + row["package"]
        role = row["role"]
        actor = row["actor_code"]
        if name not in key or role not in ROLES or not actor or row["consent_and_permitted_inputs"] is not True:
            raise ValueError("Unrecognized or unauthorized submission")
        if (name, role) in observed or (actor in identities and identities[actor] != role):
            raise ValueError("Duplicate observation or non-independent role")
        identities[actor] = role
        observed.add((name, role))
        if not row["decision_reason"] or not row["reference_to_delivered_revision"]:
            raise ValueError("Record the decision basis and reviewed revision")
        for v in row["effort"].values():
            if v is not None and (type(v) is not int or v < 0):
                raise ValueError("Timing must be a nonnegative number of seconds")
        if role == "independent_reviewer":
            for k in RUBRIC:
                item = row["rubric"][k]
                if type(item["score_0_2"]) is not int or item["score_0_2"] not in (0, 1, 2) or not item["evidence"]:
                    raise ValueError("Incomplete independent score or source")
            if type(row["first_pass_accepted"]) is not bool:
                raise ValueError("First-pass decision required")
        if role == "sales_or_owner" and (
            type(row["business_accepted"]) is not bool or type(row["sales_usefulness_0_2"]) is not int or row["sales_usefulness_0_2"] not in (0, 1, 2)
        ):
            raise ValueError("Sales decision and usefulness required")
        if role == "marketer" and type(row["usable_after_editing"]) is not bool:
            raise ValueError("Marketer usability decision required")
        if row["allocated_cost_vnd"] is not None and (type(row["allocated_cost_vnd"]) is not int or row["allocated_cost_vnd"] < 0 or not row["cost_source"]):
            raise ValueError("Cost needs an observed basis")
        by = result.setdefault(name, {"arm": key[name], "observations": {}})
        by["observations"][role] = {
            k: row[k]
            for k in (
                "actor_code",
                "effort",
                "first_pass_accepted",
                "usable_after_editing",
                "sales_usefulness_0_2",
                "business_accepted",
                "allocated_cost_vnd",
                "cost_source",
            )
        }
    for name, arm in key.items():
        out = result.setdefault(name, {"arm": arm, "observations": {}})
        obs = out["observations"]
        out["missing_roles"] = [r for r in ROLES if r not in obs]
        out["recorded_labor_cost_per_business_accepted_vnd"] = (
            sum(v["allocated_cost_vnd"] for v in obs.values())
            if not out["missing_roles"] and obs["sales_or_owner"]["business_accepted"] and all(v["allocated_cost_vnd"] is not None for v in obs.values())
            else None
        )
        out["all_in_cost_per_business_accepted_vnd"] = None  # Compute, tool and other production costs require separate reconciliation.
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="cmd", required=True)
    for command in ("pack", "check"):
        sub = subs.add_parser(command)
        sub.add_argument("first", type=Path)
        sub.add_argument("second", type=Path)
    args = parser.parse_args()
    if args.cmd == "pack":
        pack(args.first, args.second)
    else:
        print(dump(check(read(args.first), read(args.second))))
