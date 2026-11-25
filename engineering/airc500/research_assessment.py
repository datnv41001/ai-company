"""Replay paired receipts, export blinded free text and keep semantic grading separate from lexical checks."""

import argparse
from collections import Counter
import json
from pathlib import Path

from local_adapter import file_digest
from pilot_fixture import digest, encoded
from public_research import ROOT, dump
from research_study import ORACLE, enrolled_context, replay

CAPABILITIES = (
    "marketing_reasoning",
    "source_attribution",
    "semantic_contradiction",
    "product_scope",
    "code_logic",
    "security_and_regression",
    "actionable_repairs",
)
DIMENSIONS = ("scope_reason_valid", "attribution_valid", "recommendation_useful")


def blind_packets(records):
    cases = {c["id"]: c for c in enrolled_context()[0]}
    graders, reverse = {}, {}
    for r in records:
        for unit, answer in r["op"].items():
            # Evaluator sees the full actual response and rubric, with treatment assignment and metrics withheld.
            tag = digest(encoded(["paired-blind-v4", r["id"], unit, answer]))[:16]
            graders[tag] = {"case": cases[unit], "answer": answer}
            reverse[tag] = (r["id"].rsplit("-", 1)[1], unit)
    return dict(sorted(graders.items())), reverse


def scoring(records, grading):
    blinded, reverse = blind_packets(records)
    if grading.get("blind_digest") != digest(encoded(blinded)) or set(grading["observations"]) != set(blinded):
        raise ValueError("Semantic assessment does not match the exact blinded packets")
    labels = json.loads(ORACLE.read_bytes())["cases"]
    cases, cards, _ = enrolled_context()
    topics = {c["id"]: c["topic"] for c in cases}
    arms = {"without": {}, "with": {}}
    for key, row in blinded.items():
        arm, uid = reverse[key]
        grade = grading["observations"][key]
        if not (all(type(grade[k]) is bool for k in DIMENSIONS) and isinstance(grade["note"], str) and grade["note"].strip()):
            raise ValueError("Incomplete semantic assessment")
        truth = labels[uid]
        a = row["answer"]
        actual = [c["id"] for c in cards[topics[uid]]] if arm == "with" else []
        arms[arm][uid] = {
            "gold": truth["verdict"],
            "observed": a["verdict"],
            "topic": topics[uid],
            "verdict_correct": a["verdict"] == truth["verdict"],
            "relevant_source_choice": a["source"] in truth["sources"],
            "source_in_context": a["source"] in actual and a["source"] in truth["sources"],
            "literal_repair_match": truth["repair"].casefold() == a["recommendation"].strip().casefold(),
            **{k: grade[k] for k in DIMENSIONS},
            "grader_note": grade["note"],
        }
    summary = {}
    fields = ("verdict_correct", "relevant_source_choice", "source_in_context", "literal_repair_match", *DIMENSIONS)
    for arm, items in arms.items():
        counter = Counter((r["gold"], r["observed"]) for r in items.values())
        calls = [r for r in records if r["id"].rsplit("-", 1)[1] == arm]
        summary[arm] = {
            "cases": len(items),
            "calls": len(calls),
            "input_tokens": sum(r["input"] for r in calls),
            "output_tokens": sum(r["output"] for r in calls),
            "exact": {k: sum(r[k] for r in items.values()) for k in fields},
            "confusion": {target: {pred: counter[target, pred] for pred in ("flag", "keep", "insufficient")} for target in ("flag", "keep", "insufficient")},
            "correct_findings": [uid for uid, r in sorted(items.items()) if r["gold"] == "flag" and r["verdict_correct"]],
            "false_findings": [uid for uid, r in sorted(items.items()) if r["gold"] != "flag" and r["observed"] == "flag"],
            "useful_correct_findings": [uid for uid, r in sorted(items.items()) if r["gold"] == "flag" and r["verdict_correct"] and r["recommendation_useful"]],
        }
    paired = {}
    for field in fields:
        paired[field] = {
            "gain": [u for u in sorted(labels) if not arms["without"][u][field] and arms["with"][u][field]],
            "loss": [u for u in sorted(labels) if arms["without"][u][field] and not arms["with"][u][field]],
        }
    return {
        "arms": summary,
        "paired": paired,
        "case_results": arms,
        "qualification": qualify(arms["with"]),
        "reviewer_ids": ["MK-022"],
        "paid_microusd": 0,
        "calls": len(records),
        "treatment_without_fresh_sources": sorted(u for u, t in topics.items() if not cards[t]),
    }


def qualify(items):
    groups = {
        "marketing_reasoning": (set(items), "scope_reason_valid"),
        "source_attribution": (set(items), "attribution_valid"),
        "semantic_contradiction": ({u for u, r in items.items() if r["gold"] == "flag"}, "verdict_correct"),
        "product_scope": ({u for u, r in items.items() if r["topic"] == "catalog"}, "scope_reason_valid"),
        "code_logic": (set(), None),
        "security_and_regression": (set(), None),
        "actionable_repairs": ({u for u, r in items.items() if r["gold"] == "flag"}, "recommendation_useful"),
    }
    return {
        name: {
            "measured": len(units),
            "correct": sum(items[u][field] and items[u]["verdict_correct"] for u in units),
            "status": "insufficient sample" if units else "unmeasured",
            "promotion": False,
        }
        for name, (units, field) in groups.items()
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["blind", "score"])
    p.add_argument("--out", type=Path, default=ROOT / "evidence")
    p.add_argument("--pin", required=True)
    p.add_argument("--archive-pin", required=True)
    p.add_argument("--file", type=Path)
    args = p.parse_args()
    if file_digest(args.out / "q15.json.gz") != args.archive_pin:
        raise ValueError("Measured archive does not match external pin")
    records = replay(args.out, args.pin)
    if args.mode == "blind":
        payload = blind_packets(records)[0]
        dump(
            args.file,
            {
                "digest": digest(encoded(payload)),
                "rubric": "Use case-specific independent gold. Grade reason if it correctly explains scope and outcome; attribution if the chosen source is relevant and the explanation respects its evidentiary limits; recommendation if concrete, applicable and safe in this case, without invented facts. Equivalent paraphrases count. Assess each dimension separately. For a keep, preserving the bounded statement is a useful action. For missing evidence, request the specific missing evidence. Grade wording as written, without filling gaps.",
                "responses": payload,
            },
        )
    else:
        print(json.dumps(scoring(records, json.loads(args.file.read_bytes())), indent=2))
