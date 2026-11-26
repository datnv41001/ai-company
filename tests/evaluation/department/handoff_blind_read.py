"""Reconcile the anonymous technical desk reads against the frozen prospective handoff run."""

import argparse
import json
from pathlib import Path
import zipfile

from handoff_comparison import DATA, load, save

FLAGS = ("one_field", "grounded", "neutral", "language")
ARMS = ("control", "rules", "qwen")


def analyze(archive, directory):
    deck = {x["id"]: x for x in load(DATA / "inputs.json")}
    packet = {x["item"]: x for x in load(directory / "anonymous.json")}
    key = {x["item"]: x for x in load(directory / "key.json")}
    metrics = load(DATA / "metrics.json")
    gained = {
        x["id"]
        for x, y in zip(metrics["qwen"]["cases"], metrics["control"]["cases"], strict=True)
        if x["id"] == y["id"] and x["gold"] == "ask" and x["exact"] and not y["exact"]
    }
    if set(key) != set(packet) or len(key) != len(load(directory / "key.json")):
        raise ValueError("Blind packet and key must match")
    with zipfile.ZipFile(archive) as z:
        original = {(arm, item["id"]): {k: item[k] for k in ("decision", "field", "question")} for arm in ARMS for item in json.loads(z.read(arm + ".json"))}
    coverage = []
    for token, entry in key.items():
        case = entry["id"]
        source = packet[token]
        if source["source"] != deck[case]:
            raise ValueError("Changed source card")
        for arm in entry["arms"]:
            if original[arm, case] != source["candidate"]:
                raise ValueError("Changed blind arm output")
            coverage.append((arm, case))
    if len(coverage) != len(set(coverage)) or set(coverage) != set(original):
        raise ValueError("Incomplete blind arm map")
    readers = []
    all_rows = []
    for reader_name in ("A", "B"):
        info = load(directory / ("reader-" + reader_name + ".json"))
        items = {x["item"]: x for x in info["rows"]}
        if set(items) != set(packet) or len(items) != len(info["rows"]):
            raise ValueError("Reader must return exactly one verdict per packet entry")
        stats = {
            arm: {
                "outputs": 0,
                "asks": 0,
                "asks_passing_all": 0,
                "additional_correct_asks": 0,
                "additional_correct_asks_passing_all": 0,
                "edits_proposed": 0,
                "unauthorized": 0,
            }
            for arm in ARMS
        }
        for token, row in items.items():
            asking = packet[token]["candidate"].get("decision") == "ask"
            if any((type(row[k]) is not bool if asking else row[k] is not None) for k in FLAGS):
                raise ValueError("Expected wording booleans only for ask decisions")
            if type(row["unauthorized"]) is not bool or not isinstance(row["edit"], str) or not row["edit"].strip():
                raise ValueError("Expected authority judgment and single edit or none")
            for arm in key[token]["arms"]:
                s = stats[arm]
                s["outputs"] += 1
                s["asks"] += int(asking)
                passed = asking and all(row[k] for k in FLAGS)
                s["asks_passing_all"] += int(passed)
                added = asking and arm == "qwen" and key[token]["id"] in gained
                s["additional_correct_asks"] += int(added)
                s["additional_correct_asks_passing_all"] += int(added and passed)
                s["edits_proposed"] += int(row["edit"].strip().lower() != "none")
                s["unauthorized"] += int(row["unauthorized"])
        all_rows.append(items)
        readers.append({"reader": info["reader"], "elapsed_seconds": info["elapsed_seconds"], "arms": stats})
    dissent = [item for item in packet if any(all_rows[0][item][k] != all_rows[1][item][k] for k in (*FLAGS, "unauthorized"))]
    edit_dissent = [item for item in packet if (all_rows[0][item]["edit"].strip().lower() == "none") != (all_rows[1][item]["edit"].strip().lower() == "none")]
    return {
        "anonymous_items": len(packet),
        "covered_arm_outputs": len(coverage),
        "readers": readers,
        "flag_disagreements": dissent,
        "disagree_on_edit_needed": edit_dissent,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("out", type=Path)
    opts = p.parse_args()
    save(opts.out, analyze(DATA / "FIRST-RUN.zip", opts.directory))
