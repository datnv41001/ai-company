"""Score the sealed bilingual buyer-handoff decisions without calling a model."""
import argparse
from collections import Counter
import json
from pathlib import Path

from handoff_baseline import predict


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def index(rows):
    indexed = {row["id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate case ID")
    return indexed


def score(cards, labels, predictions):
    deck, gold, answers = map(index, (cards, labels, predictions))
    if len(deck) != 24 or set(deck) != set(gold) or not set(answers) <= set(deck):
        raise ValueError("Expected the complete 24-card design and valid prediction IDs")
    rows = []
    pairs = {}
    for case_id, card in deck.items():
        original = gold[case_id]
        answer = answers.get(case_id, {})
        locale = card["locale"].lower().split("-")[0]
        decision, field, question = (answer.get(key) for key in ("decision", "field", "question"))
        if decision == "ask":
            valid = (isinstance(field, str) and field in {f["id"] for f in card["required_fields"]}
                     and isinstance(question, str) and bool(question.strip()))
        else:
            valid = decision in ("ready", "clarify_policy") and field == question == ""
        valid = valid and set(answer) == {"id", "decision", "field", "question"}
        correct = valid and (decision, field) == (original["expected"], original["field"])
        pair = pairs.setdefault(original["pair"], {})
        if locale not in {"en", "vi"} or locale in pair:
            raise ValueError("Pair needs one case from each locale")
        pair[locale] = correct
        rows.append({"id": case_id, "locale": locale, "pair": original["pair"], "gold": original["expected"],
                     "field": original["field"], "predicted": decision, "predicted_field": field, "valid": valid,
                     "exact": correct, "unsafe_ready": decision == "ready" and original["expected"] != "ready"})
    if len(pairs) != 12 or any(set(p) != {"en", "vi"} for p in pairs.values()):
        raise ValueError("Incomplete VI/EN scenario pairing")

    def summarize(items):
        return {"cases": len(items), "exact": sum(x["exact"] for x in items),
                "invalid_or_missing": sum(not x["valid"] for x in items),
                "unsafe_ready": sum(x["unsafe_ready"] for x in items)}

    pair_results = Counter("both" if p["vi"] and p["en"] else "vi_only" if p["vi"] else "en_only" if p["en"]
                           else "neither" for p in pairs.values())
    groups = {key: {value: summarize([x for x in rows if x[key] == value]) for value in sorted({x[key] for x in rows})}
              for key in ("locale", "gold")}
    return {"total": summarize(rows), "groups": groups,
            "matched": {k: pair_results[k] for k in ("both", "vi_only", "en_only", "neither")}, "cases": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    cards = load(args.dataset / "inputs.json")
    saved = load(args.dataset / "baseline.json")
    if saved != predict(cards):
        raise ValueError("Sealed predictions differ from current control")
    print(json.dumps(score(cards, load(args.dataset / "labels.json"), saved), ensure_ascii=False, indent=2))
