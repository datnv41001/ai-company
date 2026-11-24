"""Compare two locked blind sheets before opening either the scorer or the technical labels."""

import argparse
from pathlib import Path
import json
from evaluate import CASES, digest, expected_labels, index, read


def compare(first, second, reviewer):
    pack = read(CASES)
    cases = index(pack["cases"])
    signature = digest(pack)
    ballots = (first, second)
    names = [sheet["reviewer"].strip() for sheet in ballots]
    if any(sheet["basis"] != "independent-human" for sheet in ballots) or len({name.casefold() for name in names}) != 2:
        raise ValueError("Provide two independent human sheets with distinct reviewer identifiers")
    if not reviewer.strip():
        raise ValueError("Supply the adjudicator identifier")
    votes = [expected_labels(sheet, cases, signature) for sheet in ballots]
    original = [index(sheet["cases"]) for sheet in ballots]
    result = {
        "basis": "independent-human",
        "reviewer": reviewer.strip(),
        "cases_digest": signature,
        "reviewers": names,
        "sheet_digests": [digest(sheet) for sheet in ballots],
        "cases": [],
    }
    for cid in cases:
        fields = [{(field, rule) for key, field, rule in vote if key == cid} for vote in votes]
        agreed = fields[0] == fields[1]
        item = {"id": cid, "reviewed": agreed, "findings": [{"field": f, "rule": r} for f, r in sorted(fields[0] & fields[1])], "note": ""}
        if not agreed:
            item["votes"] = [
                {"reviewer": name, "findings": rows[cid]["findings"], "note": rows[cid].get("note", "")} for name, rows in zip(names, original, strict=True)
            ]
        result["cases"].append(item)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheets", type=Path, nargs=2)
    parser.add_argument("--reviewer", required=True, help="Name or ID of the person adjudicating disagreements")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(*map(read, args.sheets), args.reviewer)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(sum(not row["reviewed"] for row in result["cases"]), "cases require adjudication")
