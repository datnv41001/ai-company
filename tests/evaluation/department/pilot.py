"""Prepare source-blind complete packages and validate separately submitted practitioner observations."""

import argparse
import hashlib
import json
from pathlib import Path
import re
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


LABELS = {
    "company": "Doanh nghiệp",
    "brand": "Thương hiệu",
    "product": "Sản phẩm hoặc dịch vụ",
    "audience": "Người mua",
    "objective": "Mục tiêu",
    "kpi": "Chỉ số kết quả",
    "kpi_method": "Cách đo",
    "kpi_window": "Kỳ đo",
    "hypotheses": "Giả thuyết",
    "exclusions": "Giới hạn tuyên bố",
    "cta": "Bước người mua cần làm",
    "buyer_action": "Hành động mục tiêu",
    "campaign": "Kế hoạch chiến dịch",
    "strategy": "Chiến lược",
    "research": "Nghiên cứu",
    "measurement": "Đo lường",
    "client_strategy": "Chiến lược giao doanh nghiệp",
    "client_measurement": "Đo lường giao doanh nghiệp",
    "landing": "Trang đích và tìm kiếm",
    "copy": "Nội dung trang",
    "seo": "SEO",
    "assets": "Nội dung theo kênh",
    "headline": "Tiêu đề",
    "value_proposition": "Giá trị đề xuất",
    "benefit": "Lợi ích",
    "commercial_terms": "Điều kiện thương mại",
    "call_to_action": "Lời mời hành động",
    "page_title": "Tiêu đề tìm kiếm",
    "meta_description": "Mô tả tìm kiếm",
    "search_intent": "Nhu cầu tìm kiếm",
    "social": "Bài mạng xã hội",
    "ad": "Nội dung quảng cáo",
    "creative_brief": "Brief thiết kế",
    "calendar": "Lịch công việc",
    "approved_description": "Mô tả được duyệt",
    "approved_price": "Giá và điều kiện được duyệt",
}


def markdown(data, level=2):
    if isinstance(data, dict):
        return "\n\n".join("#" * min(level, 6) + " " + LABELS.get(key, key.replace("_", " ")) + "\n\n" + markdown(v, level + 1) for key, v in data.items())
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
        "delivered_artifact_sha256": None,
        "sales_usefulness_0_2": None,
        "business_accepted": None,
        "effort": {k: None for k in EFFORT},
        "allocated_cost_vnd": None,
        "cost_source": None,
        "overhead": {"compute_vnd": None, "tools_vnd": None, "other_vnd": None, "receipt_refs": [], "includes_failed_attempts": False},
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
            for role in ROLES:
                manual.writestr(case + "/observation-" + role + ".json", dump(blank("manual", case) | {"role": role}))
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
                for role in ROLES:
                    blind.writestr(prefix + "/observation-" + role + ".json", dump(blank(alias, case) | {"role": role}))
        blind.writestr("ORDER.txt", "\n".join(order))
    (out / "custodian.json").write_text(dump(labels), encoding="utf-8")


def verify_artifact(name, observations, directory, staged=False):
    """Bind three independent submissions to the bytes retained for this blind package."""
    if set(observations) != set(ROLES):
        return {"status": "missing_roles"}
    digests = [row["delivered_artifact_sha256"] for row in observations.values()]
    if not all(digests):
        return {"status": "missing_declared_digest"}
    references = {row["reference_to_delivered_revision"] for row in observations.values()}
    if len(set(digests)) != 1 or len(references) != 1:
        return {"status": "different_submitted_revisions"}
    if directory is None:
        return {"status": "artifact_unavailable"}
    root = directory.resolve()
    path = (root / Path(name).name / "delivered/artifact.md" if staged else root / name / "delivered.artifact").resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return {"status": "artifact_unavailable"}
    with path.open("rb") as artifact:
        digest = hashlib.file_digest(artifact, "sha256").hexdigest()
    status = "verified" if digest == digests[0] else "artifact_mismatch"
    return {"status": status, "retained_sha256": digest, "submitted_revision": next(iter(references))}


def check(key, rows, artifacts=None, *, staged=False):
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
        revision = row["reference_to_delivered_revision"]
        if not row["decision_reason"] or not isinstance(revision, str) or not revision.strip():
            raise ValueError("Record the decision basis and reviewed revision")
        declared = row.get("delivered_artifact_sha256")
        if declared is not None and (not isinstance(declared, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", declared)):
            raise ValueError("Artifact digest must be SHA-256 hex")
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
        overhead = row["overhead"]
        for field in ("compute_vnd", "tools_vnd", "other_vnd"):
            val = overhead[field]
            if val is not None and (type(val) is not int or val < 0):
                raise ValueError("Invalid overhead")
        if any(overhead[k] is not None for k in ("compute_vnd", "tools_vnd", "other_vnd")) and (role != "marketer" or not overhead["receipt_refs"]):
            raise ValueError("The marketer supplies a single allocation with receipt references")
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
                "overhead",
                "reference_to_delivered_revision",
            )
        }
        by["observations"][role]["delivered_artifact_sha256"] = declared.lower() if declared else None
    for name, arm in key.items():
        out = result.setdefault(name, {"arm": arm, "observations": {}})
        obs = out["observations"]
        out["missing_roles"] = [r for r in ROLES if r not in obs]
        out["artifact_verification"] = verify_artifact(name, obs, artifacts, staged)
        out["verified_business_decision"] = (
            obs["sales_or_owner"]["business_accepted"] if out["artifact_verification"]["status"] == "verified" else None
        )
        out["recorded_labor_cost_per_business_accepted_vnd"] = (
            sum(v["allocated_cost_vnd"] for v in obs.values())
            if out["verified_business_decision"] is True and all(v["allocated_cost_vnd"] is not None for v in obs.values())
            else None
        )
        evidence = obs.get("marketer", {}).get("overhead", {})
        nonlabor = [evidence.get(k) for k in ("compute_vnd", "tools_vnd", "other_vnd")]
        labor = [v["allocated_cost_vnd"] for v in obs.values()]
        observed = (
            not out["missing_roles"] and evidence.get("receipt_refs") and evidence.get("includes_failed_attempts") is True and None not in labor + nonlabor
        )
        out["recorded_total_vnd"] = sum(labor + nonlabor) if observed else None
        out["all_in_cost_per_business_accepted_vnd"] = out["recorded_total_vnd"] if out["verified_business_decision"] is True else None
    return result


def by_arm(packages):
    result = {}
    for arm in sorted({p["arm"] for p in packages.values()}):
        commissioned = [p for p in packages.values() if p["arm"] == arm]
        accepted = sum(p["verified_business_decision"] is True for p in commissioned)
        unknown = sum(p["verified_business_decision"] is None for p in commissioned)
        costs = [p["recorded_total_vnd"] for p in commissioned]
        result[arm] = {
            "commissioned": len(commissioned),
            "business_accepted": accepted,
            "unverified_decisions": unknown,
            "recorded_cost_per_business_accepted_vnd": sum(costs) / accepted if accepted and not unknown and None not in costs else None,
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="cmd", required=True)
    for command in ("pack", "check"):
        sub = subs.add_parser(command)
        sub.add_argument("first", type=Path)
        sub.add_argument("second", type=Path)
        if command == "check":
            sub.add_argument("--artifacts", type=Path, help="Retained delivery files arranged as <brief>/<blind alias>/delivered.artifact")
    args = parser.parse_args()
    if args.cmd == "pack":
        pack(args.first, args.second)
    else:
        packages = check(read(args.first), read(args.second), args.artifacts)
        print(dump({"mode": "fixture_replay", "packages": packages, "arms": by_arm(packages)}))
