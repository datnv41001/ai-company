"""Predict a synthetic buyer handoff from declared fields alone. Never opens a label file."""
import argparse
import json
from pathlib import Path


def baseline(card):
    fields = card["required_fields"]
    received = card["received_fields"]
    vi = card["locale"].lower().startswith("vi")
    if not fields:
        return {"id": card["id"], "decision": "clarify_policy", "field": "", "question": ""}
    for field in fields:
        value = received.get(field["id"])
        if value is None or value == "" or (isinstance(value, str) and not value.strip()):
            label = field["label"]
            question = f"Bạn cho biết {label} được không?" if vi else f"Could you provide the {label}?"
            return {"id": card["id"], "decision": "ask", "field": field["id"], "question": question}
    return {"id": card["id"], "decision": "ready", "field": "", "question": ""}


def predict(cards):
    if len(cards) != len({card["id"] for card in cards}):
        raise ValueError("Duplicate input card")
    return [baseline(card) for card in cards]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cards", type=Path)
    parser.add_argument("predictions", type=Path)
    args = parser.parse_args()
    cards = json.loads(args.cards.read_text(encoding="utf-8"))
    with args.predictions.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(predict(cards), out, ensure_ascii=False, indent=2)
        out.write("\n")
