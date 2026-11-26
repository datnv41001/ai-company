"""Archive a completed synthetic run or issue anonymous specialist reading packets."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
from zipfile import ZIP_DEFLATED, ZipFile

from pilot import dump, markdown, read

DATA = Path(__file__).parent / "semantic-v1"
SPLITS = ("inputs", "stress-inputs")
ROLES = ("research", "strategy", "content", "seo_geo", "media", "creative")


def pack(run, archive):
    entries = ["host.json"]
    for split in SPLITS:
        entries.append(split + "-predictions.json")
        entries.extend("receipts/" + row["id"] + ".json" for row in read(DATA / (split + ".json")))
    for brief in read(DATA / "briefs.json"):
        entries.append(brief["id"] + "-work.json")
        entries.extend(f"receipts/{brief['id']}-{role}.json" for role in ROLES)
    if not all((run / name).is_file() for name in entries):
        raise ValueError("Run is incomplete")
    with ZipFile(archive, "x", ZIP_DEFLATED) as z:
        for name in sorted(entries):
            z.write(run / name, name)


def anonymize(archive, bundle, key):
    records = []
    keymap = {}
    with ZipFile(archive) as z:
        for brief in read(DATA / "briefs.json"):
            work = json.loads(z.read(brief["id"] + "-work.json"))
            for role, arms in work.items():
                for arm, value in arms.items():
                    identifier = secrets.token_hex(5)
                    records.append({"id": identifier, "brief": brief["id"], "task": role, "draft": markdown(value)})
                    keymap[identifier] = arm
    secrets.SystemRandom().shuffle(records)
    with bundle.open("x", encoding="utf-8") as stream:
        stream.write(dump(records))
    with key.open("x", encoding="utf-8") as stream:
        stream.write(dump(keymap))


def reconcile(archive, bundle, key, verdicts):
    cards = read(bundle)
    mapping = read(key)
    votes = read(verdicts)
    ids = {r["id"] for r in cards}
    if len(ids) != 24 or len(votes) != len(cards) or ids != set(mapping) or ids != {r["id"] for r in votes}:
        raise ValueError("Missing or duplicate blind candidate")
    selections = {v["id"]: v for v in votes}
    readings = []
    jobs = set()
    with ZipFile(archive) as source:
        for card in cards:
            identifier = card["id"]
            job = card["brief"], card["task"], mapping[identifier]
            vote = selections[identifier]
            draft = json.loads(source.read(job[0] + "-work.json"))[job[1]][job[2]]
            if job in jobs or card["draft"] != markdown(draft):
                raise ValueError("Candidate differs from sealed archive or appears twice")
            jobs.add(job)
            if len(vote["marks"]) != 3 or any(type(v) is not int or v not in (0, 1) for v in vote["marks"]):
                raise ValueError("Need one binary score per obligation")
            if not vote["evidence"].strip() or not vote["needed_edit"].strip():
                raise ValueError("Missing supporting text")
            readings.append({"brief": job[0], "task": job[1], "arm": job[2], **vote})
    return {"blind_cards_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
            "blind_verdicts_sha256": hashlib.sha256(verdicts.read_bytes()).hexdigest(),
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "readings": sorted(readings, key=lambda r: (r["task"], r["brief"], r["arm"]))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("pack")
    b = sub.add_parser("anonymize")
    c = sub.add_parser("reconcile")
    for cmd, names in ((a, ("run", "archive")), (b, ("archive", "bundle", "key")), (c, ("archive", "bundle", "key", "verdicts", "out"))):
        for name in names:
            cmd.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.command == "pack":
        pack(args.run, args.archive)
    elif args.command == "anonymize":
        anonymize(args.archive, args.bundle, args.key)
    else:
        args.out.write_text(dump(reconcile(args.archive, args.bundle, args.key, args.verdicts)), encoding="utf-8", newline="\n")
