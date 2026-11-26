"""Compile two caption tracks for editorial review and cross-check approved synthetic Studio files."""

import argparse
import hashlib
import json
from pathlib import Path
import re
from shutil import copyfile


CASES = {"index-tray": "rfq", "receipt-map": "appointment"}
FOLDER = Path(__file__).resolve().parents[3] / "docs/evaluation/campaign-production-review"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tracks(edit):
    hooks = edit["hooks"]
    shots = edit["shots"]
    if set(hooks) != {"A", "B"} or len(set(hooks.values())) != 2 or not all(v.strip() for v in hooks.values()):
        raise ValueError("Two distinct hook lines required")
    if not shots or shots[0]["caption"] != "{hook}" or any("{hook}" in s["caption"] for s in shots[1:]):
        raise ValueError("Only the opening line varies")
    last = 0
    for shot in shots:
        if type(shot["end"]) is not int or shot["start"] != last or not last < shot["end"] <= 59:
            raise ValueError("Use one continuous timeline shorter than a minute")
        if not shot["picture"].strip() or not shot["caption"].strip():
            raise ValueError("Every shot requires a visual action and captions")
        last = shot["end"]
    return {
        key: "WEBVTT\n\n" + "\n\n".join(
            f"00:00:{s['start']:02}.000 --> 00:00:{s['end']:02}.000\n{s['caption'].replace('{hook}', line)}" for s in shots
        ) + "\n"
        for key, line in hooks.items()
    }


def check_price_and_readability(edit, approved_terms):
    """Read the Vietnamese indicative-price clause used by these two signed fixtures."""
    terms = re.search(
        r"Giá tham khảo: ([\d.]+) VND / 1 ([^,]+), đã gồm thuế\. Đơn tối thiểu: (\d+) \2\.", approved_terms
    )
    if not terms:
        raise ValueError("Review the current approved pricing terms before using this editorial check")
    amount, unit, minimum = terms.groups()
    price_cues = [s["caption"] for s in edit["shots"] if amount in s["caption"]]
    if len(price_cues) != 1:
        raise ValueError("Use one price card for the approved amount")
    cue = " ".join(price_cues[0].lower().split())
    if (f"giá tham khảo {amount} đồng/{unit}" not in cue or "đã gồm thuế" not in cue
            or not re.search(r"(?:tối thiểu|đơn từ) " + re.escape(f"{minimum} {unit}") + r"\b", cue)):
        raise ValueError("Retain indicative price, selling unit, tax and minimum on the price card")
    for shot in edit["shots"]:
        options = edit["hooks"].values() if shot["caption"] == "{hook}" else [shot["caption"]]
        for value in options:
            lines = value.splitlines()
            if len(lines) > 2 or max(map(len, lines)) > 40 or len(" ".join(lines)) > 15 * (shot["end"] - shot["start"]):
                raise ValueError("Review caption line length or reading hold")


def check_bundle(folder):
    for case, action in CASES.items():
        root = folder / case
        data, edit = read(root / "evidence.json"), read(root / "edit.json")
        visit, submission = data["events"]
        creative, landing, intake = data["creative"], data["landing"], data["intake"]
        if not intake["synthetic"] or not (intake["case"] == edit["case"] == case):
            raise ValueError("Wrong or non-synthetic fixture")
        if creative["master"]["headline"] != edit["product"] or edit["approval"] != "editorial_candidate":
            raise ValueError("Incorrect product or editorial status")
        check_price_and_readability(edit, intake["commercial_terms"])
        for package in (creative, landing):
            if package["plan_digest"] != intake["plan_digest"] or package["plan_id"] != intake["plan_id"]:
                raise ValueError("Mismatched plan and package")
            if package["production_qa"]["digest"] != package["digest"] or package["production_qa"]["reviewer"] == package["created_by"]:
                raise ValueError("A separate package-specific QA decision is required")
        for package, file in ((creative, "portrait.png"), (landing, "landing.html")):
            if sha((root / file).read_bytes()) != package["files"][file]["sha256"]:
                raise ValueError(f"Published bytes disagree with signed receipt for {file}")
        if landing["id"] != intake["package_id"] or landing["digest"] != intake["package_digest"] or intake["contract"]["action"] != action:
            raise ValueError("Intake points to another package or action")
        if (visit["id"], submission["id"]) != (intake["visit_id"], intake["submitted_id"]):
            raise ValueError("Visit or submission receipt mismatch")
        for key, vtt in tracks(edit).items():
            if (root / f"{key}.vtt").read_text(encoding="utf-8") != vtt:
                raise ValueError(f"Caption edits diverge from storyboard in {case}/{key}")


def capture(studio, forms, destination):
    for case, action in CASES.items():
        dest = destination / case
        dest.mkdir(parents=True, exist_ok=True)
        archive = studio / action
        evidence = {k: read(archive / k / "receipt.json") for k in ("creative", "landing")}
        evidence["events"] = read(archive / "landing/sandbox-events.json")
        evidence["intake"] = read(forms / case / "receipts.json")
        with (dest / "evidence.json").open("x", encoding="utf-8", newline="\n") as file:
            json.dump(evidence, file, ensure_ascii=False, indent=2)
            file.write("\n")
        for kind, name in (("creative", "portrait.png"), ("landing", "landing.html")):
            if (dest / name).exists():
                raise FileExistsError(dest / name)
            copyfile(archive / kind / name, dest / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("verify").add_argument("folder", type=Path)
    render = subs.add_parser("captions")
    render.add_argument("edit", type=Path)
    render.add_argument("destination", type=Path)
    collect = subs.add_parser("capture")
    for arg in ("studio", "forms", "destination"):
        collect.add_argument(arg, type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        check_bundle(args.folder)
        print("Verified both creative and landing receipts, form transactions and four caption tracks.")
    elif args.command == "capture":
        capture(args.studio, args.forms, args.destination)
    else:
        args.destination.mkdir(parents=True, exist_ok=True)
        for key, vtt in tracks(read(args.edit)).items():
            with (args.destination / f"{key}.vtt").open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(vtt)
