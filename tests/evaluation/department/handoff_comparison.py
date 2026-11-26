"""Offline competitors and locked scorer for the paired buyer-clarification study."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from handoff_baseline import baseline
from handoff_score import index, load, score

HERE = Path(__file__).parent
DATA = HERE / "handoff-v2"
PROMPT = (
    "Read only the supplied synthetic card. Compare the approved requirement with the buyer's latest statement "
    "and the CRM snapshot. If one required fact is outstanding, ask one brief buyer-facing question in the card "
    "language and return that field's ID. If policy is unclear, escalate it. Otherwise return ready. Do not qualify, "
    "schedule, quote or promise an outcome. Return JSON only with id, decision (ask, ready, clarify_policy), field "
    "and question. Use empty strings for field and question when no buyer question is warranted."
)


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write("\n")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def norm(value):
    text = unicodedata.normalize("NFD", str(value).lower().replace("đ", "d"))
    return " ".join("".join(c for c in text if unicodedata.category(c) != "Mn").split())


# Controlled comparator for short bilingual notes. Keep field-level uncertainty local to the clause.
UNSURE = re.compile(
    r"\b(?:tbc|tbd|unknown|pending|to be confirmed|unconfirmed|expired|obsolete|outdated|"
    r"no longer|not yet|not sure|not valid|don.t know|cannot confirm|not decided|not available|"
    r"ignore (?:my|the) (?:old|previous)|withdr[ae]w|withdraw|chua|khong ro|khong con|het han|"
    r"huy bo|rut lai|khong chac|dang cho|se xac nhan|can kiem tra)\b"
)
POLICY = re.compile(
    r"\b(?:conflict(?:s|ing)?|contradict\w*|inconsistent|unresolved|no approved|not approved|"
    r"authority must|requires (?:owner|manager) approval|no policy|no agreed|mau thuan|xung dot|"
    r"chua thong nhat|chua duyet|chua duoc phe duyet|chua co quy dinh|chua co quy trinh|"
    r"chua xac dinh quy dinh|chua co quyet dinh)\b"
)
CLAUSES = re.compile(r"[.!?;\n]+|\b(?:but|however|nhung|tuy nhien)\b")


def improved(card):
    decision = baseline(card)
    fields = card["required_fields"]
    if not fields or POLICY.search(norm(card["brief"])):
        return dict(decision, decision="clarify_policy", field="", question="")
    clauses = [q.strip() for q in CLAUSES.split(norm(card["buyer_message"])) if q.strip()]
    values = dict(card["received_fields"])
    for f in fields:
        key = f["id"]
        label = norm(f["label"])
        reference = re.compile(r"\b" + re.escape(label) + r"\b")
        explicit = re.compile(reference.pattern + r"\s*(?:[:=]|\b(?:is|will be|la)\b)\s*\S")
        known = values.get(key)
        if known is not None and UNSURE.search(norm(known)):
            values[key] = None
        for clause in clauses:
            if not reference.search(clause) and len(fields) != 1:
                continue
            if UNSURE.search(clause):
                values[key] = None
            elif explicit.search(clause):
                values[key] = clause
    return baseline(dict(card, received_fields=values))


def check_cards(cards):
    if len(index(cards)) != 24 or Counter(c["locale"] for c in cards) != {"vi": 12, "en": 12}:
        raise ValueError("The frozen cohort is 12 VI and 12 EN records")
    if set(c["journey"] for c in cards) != {"rfq", "appointment"}:
        raise ValueError("Both commissioned journeys are required")
    keys = {"id", "locale", "journey", "brief", "buyer_message", "required_fields", "received_fields"}
    for c in cards:
        if set(c) != keys or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", c["id"]) or "<|" in json.dumps(c):
            raise ValueError("Unexpected fields, identifier or chat control sequence")
        if not all(isinstance(c[k], str) and c[k].strip() for k in ("brief", "buyer_message")):
            raise ValueError("Expected a brief and buyer message")
        if not isinstance(c["required_fields"], list) or not isinstance(c["received_fields"], dict):
            raise ValueError("Invalid field projection")
        fields = c["required_fields"]
        if any(set(f) != {"id", "label"} or not all(isinstance(v, str) and v.strip() for v in f.values()) for f in fields):
            raise ValueError("Invalid field definitions")
        if len({f["id"] for f in fields}) != len(fields):
            raise ValueError("Duplicate required field")


def predictions(path, out):
    cards = load(path)
    check_cards(cards)
    out.mkdir(exist_ok=False, parents=True)
    save(out / "control.json", [baseline(c) for c in cards])
    save(out / "rules.json", [improved(c) for c in cards])


def results(path, labels, out):
    cards, gold = load(path), load(labels)
    check_cards(cards)
    refs = index(gold)
    compare = {}
    for arm in ("control", "rules", "qwen"):
        measured = score(cards, gold, load(out / f"{arm}.json"))
        by_problem = {}
        for row in measured["cases"]:
            problem = refs[row["id"]]["phenomenon"]
            stat = by_problem.setdefault(problem, {"cards": 0, "exact": 0, "false_ready": 0})
            stat["cards"] += 1
            stat["exact"] += int(row["exact"])
            stat["false_ready"] += int(row["unsafe_ready"])
        measured["phenomena"] = by_problem
        compare[arm] = measured
    return compare


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="action", required=True)
    for cmd in ("predict", "score"):
        q = s.add_parser(cmd)
        q.add_argument("cards", type=Path)
        q.add_argument("output", type=Path)
        if cmd == "score":
            q.add_argument("labels", type=Path)
    opts = p.parse_args()
    if opts.action == "predict":
        predictions(opts.cards, opts.output)
    else:
        save(opts.output / "metrics.json", results(opts.cards, opts.labels, opts.output))
