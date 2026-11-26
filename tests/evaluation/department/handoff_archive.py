"""Seal a first pass or prepare randomized blind reading packets without opening ground truth."""

import argparse
from pathlib import Path
import secrets
import zipfile

from handoff_comparison import check_cards, load, save


def archive(cards, controls, inference, destination):
    cohort = load(cards)
    check_cards(cohort)
    members = {"control.json": controls / "control.json", "rules.json": controls / "rules.json"}
    for name in ("host.json", "run.json", "qwen.json"):
        members[name] = inference / name
    for card in cohort:
        name = "receipts/" + card["id"] + ".json"
        members[name] = inference / name
    with zipfile.ZipFile(destination, "x") as out:
        for name, path in sorted(members.items()):
            out.writestr(zipfile.ZipInfo(name), path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def blind(cards, zip_path, directory):
    import json

    cohort = load(cards)
    check_cards(cohort)
    deck = {c["id"]: c for c in cohort}
    key = {}
    records = []
    with zipfile.ZipFile(zip_path) as source:
        for arm in ("control", "rules", "qwen"):
            for answer in json.loads(source.read(arm + ".json")):
                fields = tuple(answer.get(k) for k in ("id", "decision", "field", "question"))
                if fields not in key:
                    token = secrets.token_hex(7)
                    key[fields] = {"item": token, "arms": [], "id": fields[0]}
                    records.append(
                        {"item": token, "source": deck[fields[0]], "candidate": dict(zip(("decision", "field", "question"), fields[1:], strict=True))}
                    )
                key[fields]["arms"].append(arm)
        # A partial or misattributed reply can still contain customer-facing promises.
        # Retain the actual text for the authority read without repairing the scored output.
        for card in cohort:
            receipt = json.loads(source.read("receipts/" + card["id"] + ".json"))
            if receipt.get("status") != "returned" and receipt.get("raw_output"):
                token = secrets.token_hex(7)
                key[(card["id"], token)] = {"item": token, "arms": ["qwen"], "id": card["id"]}
                records.append({"item": token, "source": card, "candidate": {"raw_partial": receipt["raw_output"]}})
    secrets.SystemRandom().shuffle(records)
    directory.mkdir(exist_ok=False, parents=True)
    save(directory / "anonymous.json", records)
    save(directory / "private-key.json", list(key.values()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action, names in (("archive", ("cards", "controls", "inference", "destination")), ("blind", ("cards", "archive", "directory"))):
        p = sub.add_parser(action)
        for name in names:
            p.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.action == "archive":
        archive(args.cards, args.controls, args.inference, args.destination)
    else:
        blind(args.cards, args.archive, args.directory)
