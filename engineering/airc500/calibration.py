"""Unit-level scorer for adjudicated matches. The public example is a math fixture."""
import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def ratio(part, total):
    return part / total if total else None


def score(units, flagged, baseline):
    universe = {u["id"] for u in units}
    if len(universe) != len(units):
        raise ValueError("duplicated evaluation unit")
    if any(type(u["present"]) is not bool for u in units):
        raise ValueError("each unit needs a verified boolean label")
    for matches in (flagged, baseline):
        if set(matches) - universe or len(matches) != len(set(matches)):
            raise ValueError("matches must be adjudicated unique IDs from the casebook")
    positive = {u["id"] for u in units if u["present"]}
    critical = {u["id"] for u in units if u["present"] and u["severity"] in ("P0", "P1")}
    flagged = set(flagged)
    missed_by_author = positive - set(baseline)
    tp, fp = len(flagged & positive), len(flagged - positive)
    fn, tn = len(positive - flagged), len(universe - positive - flagged)
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "false_positive_rate": ratio(fp, fp + tn),
            "critical_detected": len(flagged & critical), "critical_total": len(critical),
            "recovered_author_misses": len(flagged & missed_by_author),
            "total_author_misses": len(missed_by_author)}


if __name__ == "__main__":
    cases = json.loads((FIXTURES / "units.json").read_text(encoding="utf-8"))
    sample = json.loads((FIXTURES / "scoring-example.json").read_text(encoding="utf-8"))
    print(json.dumps({"kind": sample["kind"], "measured_model_invocations": 0,
                      "scores": score(cases, sample["flagged_units"],
                                      sample["implementer_flagged_units"])}, indent=2))
