"""Recompute this internal AI evaluation from the frozen casebook and recorded ballots."""
import argparse
from collections import Counter, defaultdict
from html import escape
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "landing-qa-eval"))
from evaluate import CASES, RULES, digest, expected_labels, index, predict, read  # noqa: E402


def metrics(expected, predicted):
    hits = len(expected & predicted)
    return {
        "tp": hits, "fp": len(predicted - expected), "fn": len(expected - predicted),
        "precision": round(hits / len(predicted), 4) if predicted else None,
        "recall": round(hits / len(expected), 4) if expected else None,
    }


def compare():
    pack = read(CASES)
    cases = index(pack["cases"])
    annotations = {}
    source_hashes = {}
    for name in ("ai-editorial", "ai-campaign", "ai-consensus"):
        sheet = read(HERE / (name + ".json"))
        if sheet["basis"] != "ai-simulated":
            raise ValueError("Expected a simulated AI ballot")
        annotations[name] = expected_labels(sheet, cases, digest(pack))
        source_hashes[name] = digest(sheet)
    reference = annotations["ai-consensus"]
    predictions, fingerprint, manifest = predict(pack, cases)
    ballots = [json.loads(line) for line in (HERE / "panel.jsonl").read_text(encoding="utf-8-sig").splitlines()]
    if len(ballots) != 216 or len({b["review_id"] for b in ballots}) != len(ballots):
        raise ValueError("Expected 216 distinct panel ballots")
    per_case = defaultdict(list)
    votes = Counter()
    by_lens = defaultdict(set)
    lens_coverage = defaultdict(set)
    for ballot in ballots:
        cid = ballot["case_id"]
        role = cases[cid]["role"]
        if ballot["status"] != "simulated" or ballot["node"] != role:
            raise ValueError(f"Unexpected provenance or role for {cid}")
        items = {(cid, f["field"], f["rule"]) for f in ballot["findings"]}
        if len(items) != len(ballot["findings"]) or any(field not in RULES[role].get(rule, ()) for _, field, rule in items):
            raise ValueError(f"Invalid or repeated annotation for {cid}")
        lens = ballot["discipline"]
        if cid in lens_coverage[lens]:
            raise ValueError(f"Repeated discipline {lens} for {cid}")
        lens_coverage[lens].add(cid)
        by_lens[lens].update(items)
        per_case[cid].append(items)
        votes.update(items)
    if set(per_case) != set(cases) or any(len(rows) != 9 for rows in per_case.values()):
        raise ValueError("Expected nine local opinions on each case")
    if len(lens_coverage) != 9 or any(ids != cases.keys() for ids in lens_coverage.values()):
        raise ValueError("Expected each professional discipline on all 24 cases")
    majority = {item for item, count in votes.items() if count >= 5}
    details = {}
    for cid in cases:
        def pick(items):
            return sorted((field, rule) for case_id, field, rule in items if case_id == cid)
        details[cid] = {
            "consensus": pick(reference), "qa": pick(predictions),
            "qa_extra": pick(predictions - reference), "qa_missed": pick(reference - predictions),
            "local_votes": [{"field": f, "rule": r, "votes": votes[cid,f,r]} for f,r in pick(votes)],
            "distinct_local_ballots": len({frozenset(row) for row in per_case[cid]}),
            "specialists_agreed": pick(annotations["ai-editorial"]) == pick(annotations["ai-campaign"]),
        }
    by_role = {}
    for role in RULES:
        def for_role(items):
            return {i for i in items if cases[i[0]]["role"] == role}
        by_role[role] = metrics(for_role(reference), for_role(predictions))
    return {
        "basis": "ai-simulated", "cases_digest": digest(pack), "manifest_digest": manifest,
        "runtime_fingerprint": fingerprint, "ballot_digests": source_hashes,
        "panel_ballots": len(ballots), "panel_model": ballots[0]["model"],
        "specialists_agreed_cases": sum(d["specialists_agreed"] for d in details.values()),
        "qa_against_adjudication": metrics(reference, predictions),
        "qa_against_each_specialist": {n: metrics(annotations[n], predictions) for n in ("ai-editorial","ai-campaign")},
        "qa_by_role": by_role,
        "exact_qa_cases": sum(d["consensus"] == d["qa"] for d in details.values()),
        "cases_with_reference_findings": len({i[0] for i in reference}),
        "cases_with_any_correct_warning": len({i[0] for i in predictions & reference}),
        "panel_majority_against_adjudication": metrics(reference, majority),
        "panel_by_discipline_against_adjudication": {k: metrics(reference, v) for k, v in sorted(by_lens.items())},
        "panel_nonempty_ballots": sum(bool(b["findings"]) for b in ballots),
        "panel_selecting_every_allowed_pair": sum(
            len(b["findings"]) == sum(map(len, RULES[b["node"]].values())) for b in ballots
        ),
        "panel_distinct_personas": len({b["persona"] for b in ballots}),
        "panel_distinct_models": len({b["model"]["gguf_sha256"] for b in ballots}),
        "panel_majority_total_findings": len(majority),
        "cases": details,
    }


def opinions(result):
    """Publish a readable view of the stored opinions, with each panel response left in its recorded language."""
    ballots = defaultdict(list)
    for line in (HERE / "panel.jsonl").read_text(encoding="utf-8-sig").splitlines():
        entry = json.loads(line)
        ballots[entry["case_id"]].append(entry)
    pack = index(read(CASES)["cases"])
    reference = index(read(HERE / "ai-consensus.json")["cases"])

    def cell(value):
        return escape(value.replace("\n", " "), quote=False).replace("|", "&#124;")

    def labels(items):
        return ", ".join(f"{field} · {rule}" for field, rule in items) or "∅"

    lines = ["# 216 nhận xét AI theo ca", "",
             "Mỗi ca có chín lượt chấm của cùng một Qwen local. Nhận định và đề xuất trong bảng giữ nguyên ngôn ngữ model trả lời. "
             "Ký hiệu ∅ chỉ phiếu không chọn cảnh báo. Phần phân xử bằng tiếng Việt đối chiếu với brief và nguồn.", ""]
    for cid, details in result["cases"].items():
        case = pack[cid]
        lines += [f"## {cid}", "", f"**{case['brief']} · {case['role'].upper()}**", ""]
        for field, draft in case["sections"].items():
            lines.append(f"- **{field}** {cell(draft)}")
        lines += ["", "**Phân xử AI.** " + reference[cid]["note"], "",
                  "**Nhãn phân xử** " + labels(details["consensus"]), "",
                  "**Cảnh báo của QA hiện hành** " + labels(details["qa"]), "",
                  "| Lượt và vai trò mô phỏng | Nhận định của model | Đề xuất của model | Nhãn đã chọn |",
                  "| --- | --- | --- | --- |"]
        for b in sorted(ballots[cid], key=lambda item: item["review_id"]):
            selected = [(f["field"], f["rule"]) for f in b["findings"]]
            lines.append(f"| {b['review_id']} · {cell(b['persona'])} | {cell(b['rationale'])} | {cell(b['next_action'])} | {labels(selected)} |")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a UTF-8 JSON report to this path")
    parser.add_argument("--opinions", type=Path, help="Write a Markdown casebook from recorded panel ballots")
    args = parser.parse_args()
    measured = compare()
    if args.opinions:
        args.opinions.write_text(opinions(measured), encoding="utf-8")
    result = json.dumps(measured, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
