"""Offline field-level evaluation for the reviewed landing QA policies."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CASES = HERE / "cases.json"
RELEASE_MANIFEST_DIGEST = "f47ddd7984fc1aa9d4fe3ba325ce917b49e8cfa4d504debd1ad8d7bb58003c9a"
FIELDS = {"content": ("headline", "body_copy", "call_to_action"), "seo": ("page_title", "meta_description", "search_intent")}
RULES = {
    "content": {
        "cta_action": ["call_to_action"],
        "brief_alignment": ["body_copy"],
        "brand_alignment": ["body_copy"],
        "audience_alignment": ["body_copy"],
        "offer_alignment": ["body_copy"],
        "brand_instruction": FIELDS["content"],
    },
    "seo": {
        "page_alignment": ["page_title", "meta_description"],
        "intent_alignment": ["search_intent"],
        "metadata_length": ["page_title", "meta_description"],
        "duplicate_metadata": ["meta_description"],
    },
}
for role, fields in FIELDS.items():
    RULES[role].update(claim_evidence=fields, quote_context=fields)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def index(rows):
    items = {row["id"]: row for row in rows}
    if len(items) != len(rows):
        raise ValueError("Duplicate case ID")
    return items


def expected_labels(sheet, cases, corpus_digest):
    if sheet["cases_digest"] != corpus_digest:
        raise ValueError("Labels refer to a different casebook")
    if sheet["basis"] not in {"independent-human", "technical-provisional"} or not sheet["reviewer"].strip():
        raise ValueError("Supply label provenance and a reviewer identifier")
    rows = index(sheet["cases"])
    if rows.keys() != cases.keys():
        raise ValueError("Labels must cover exactly the casebook IDs")
    expected = set()
    for cid, row in rows.items():
        if row.get("reviewed") is not True or not isinstance(row.get("findings"), list):
            raise ValueError(f"{cid}: complete the review, including explicit empty findings")
        rules = RULES[cases[cid]["role"]]
        for item in row["findings"]:
            key = (cid, item["field"], item["rule"])
            if key[1] not in rules.get(key[2], ()) or key in expected:
                raise ValueError(f"Invalid or duplicate annotation: {key}")
            expected.add(key)
    return expected


def predict(pack, cases):
    # Exercise the released validators and rule functions. Casebook parent references
    # supply the frozen Content inputs; PostgreSQL edge selection is covered in CI.
    sys.path.insert(0, str(ROOT))
    from app import landing_qa
    from app.registry_adapters import resolve
    from app.registry_compatibility import validate_manifest
    from migrations.runtime_bundle import runtime_fingerprint

    manifest = read(ROOT / "catalog" / "landing-seo-v4.json")
    if pack["workflow"] != f"{manifest['workflow_id']}@{manifest['workflow_version']}":
        raise ValueError("Workflow mismatch")
    manifest_digest = digest(manifest)
    if manifest_digest != RELEASE_MANIFEST_DIGEST:
        raise ValueError("Expected the PR 11 release manifest")
    validate_manifest(manifest)
    outputs = {}
    for cid, case in cases.items():
        skill = case["role"]
        contract = manifest["contracts"][skill]
        adapter = resolve(contract)
        raw = {**case["sections"], "source_ids": case["source_ids"]}
        outputs[cid] = adapter.validate(raw, skill, [], pack["briefs"][case["brief"]]["sources"], manifest)
    predictions = set()
    for cid, case in cases.items():
        output = outputs[cid]
        brief = pack["briefs"][case["brief"]]
        citations = {k: brief["sources"][k]["excerpt"] for k in output["source_ids"]}

        def flag(field, rule, evidence, severity="warning"):
            if field not in RULES[case["role"]].get(rule, ()):
                raise ValueError(f"Review the evaluation rubric for {rule}/{field}")
            predictions.add((cid, field, rule))

        if case["role"] == "content":
            landing_qa.content_findings(output["sections"], brief, flag)
        else:
            pid = case["parent"]
            if cases[pid]["role"] != "content" or cases[pid]["brief"] != case["brief"]:
                raise ValueError(f"{cid}: invalid Content predecessor")
            landing_qa.seo_findings(output["sections"], manifest["contracts"]["seo"]["qa_limits"], {pid: outputs[pid]}, flag)
        landing_qa.claim_findings(output["sections"], citations, flag)
    return predictions, runtime_fingerprint(), manifest_digest


def ratio(numerator, denominator):
    return f"{numerator / denominator:.1%}" if denominator else "n/a"


def score_report(sheet, cases, expected, predicted, fingerprint, manifest_digest):
    hits, extras, misses = expected & predicted, predicted - expected, expected - predicted
    counts = [Counter((cases[cid]["role"], rule) for cid, _, rule in group) for group in (hits, extras, misses)]
    lines = [
        "# Landing QA evaluation",
        "",
        f"- Label basis · {sheet['basis']} ({sheet['reviewer']})",
        f"- Cases · {len(cases)}",
        f"- Casebook SHA-256 · `{sheet['cases_digest']}`",
        f"- Manifest digest · `{manifest_digest}`",
        f"- Runtime fingerprint · `{fingerprint}`",
        "",
        "Each case, field and rule counts once. A zero denominator is shown as n/a.",
        "",
        "| Role | Rule | Labels + | TP | FP | FN | Precision | Recall |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for role, rules in RULES.items():
        for rule in rules:
            tp, fp, fn = (c[role, rule] for c in counts)
            lines.append(f"| {role} | {rule} | {tp + fn} | {tp} | {fp} | {fn} | {ratio(tp, tp + fp)} | {ratio(tp, tp + fn)} |")
    tp, fp, fn = map(len, (hits, extras, misses))
    lines += [
        f"| Both | **Micro** | {tp + fn} | {tp} | {fp} | {fn} | {ratio(tp, tp + fp)} | {ratio(tp, tp + fn)} |",
        "",
        "## Disagreements",
        "",
        "| Case | Field | Rule | Result |",
        "|---|---|---|---|",
    ]
    for kind, group in (("FP", extras), ("FN", misses)):
        for cid, field, rule in sorted(group):
            lines.append(f"| {cid} | {field} | {rule} | {kind} |")
    return "\n".join(lines) + "\n"


def blind_casebook(pack):
    lines = ["# Bộ đề landing QA", ""]
    for key, brief in pack["briefs"].items():
        lines += [
            f"## {key}",
            "",
            f"**Mục tiêu** {brief['objective']}",
            f"**Đối tượng** {brief['audience']}",
            f"**Đề nghị** {brief['offer']}",
            f"**Hướng dẫn thương hiệu** {brief['brand_rules']}",
            "",
        ]
        for source_id, source in brief["sources"].items():
            lines += [f"- **{source_id} · {source['label']}** {source['excerpt']}"]
        for case in (row for row in pack["cases"] if row["brief"] == key):
            lines += ["", f"### {case['id']} · {case['role']}", "", "Nguồn đã dẫn · " + ", ".join(case["source_ids"])]
            if "parent" in case:
                lines.append("Trang Content tiền nhiệm · " + case["parent"])
            lines.append("")
            for field, value in case["sections"].items():
                lines.append(f"- **{field}** {value}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--template", action="store_true", help="Prepare a blind label sheet")
    group.add_argument("--packet", action="store_true", help="Create a blind reviewer ZIP with --output")
    group.add_argument("--labels", type=Path, help="Score a completed label sheet")
    parser.add_argument("--output", type=Path, help="Create a new UTF-8 report or sheet")
    args = parser.parse_args()
    pack = read(CASES)
    cases = index(pack["cases"])
    signature = digest(pack)
    if args.template or args.packet:
        sheet = {
            "cases_digest": signature,
            "basis": "independent-human",
            "reviewer": "",
            "cases": [{"id": cid, "reviewed": False, "findings": [], "note": ""} for cid in cases],
        }
        output = json.dumps(sheet, ensure_ascii=False, indent=2) + "\n"
        if args.packet:
            if not args.output:
                parser.error("--packet requires --output")
            with ZipFile(args.output, "x", compression=ZIP_DEFLATED) as archive:
                archive.write(HERE / "REVIEWER.md", "REVIEWER.md")
                archive.write(CASES, "cases.json")
                archive.writestr("cases.md", blind_casebook(pack))
                archive.writestr("blind-labels.json", output)
            return
    else:
        sheet = read(args.labels)
        expected = expected_labels(sheet, cases, signature)
        predicted, fingerprint, manifest_digest = predict(pack, cases)
        output = score_report(sheet, cases, expected, predicted, fingerprint, manifest_digest)
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
