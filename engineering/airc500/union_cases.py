"""Private-to-model answer key and separately committed synthetic source/copy for study v3."""

import tempfile
from pathlib import Path

from pilot_fixture import digest, encoded, git

SEMANTICS = {
    "reservation": (
        "Bookings require an appointment.",
        "Appointments are optional.",
        ("Reserve a visit before coming.", "Visitors must book ahead."),
        ("Walk in without a booking.", "No reservation is needed."),
        "Correct the booking instruction",
    ),
    "wash_care": (
        "Hand washing is required.",
        "Machine washing is permitted.",
        ("Wash this item by hand only.", "Hand wash this item."),
        ("This item can go in the washer.", "Machine washing is fine."),
        "Correct the care instruction",
    ),
    "delivery": (
        "Delivery is limited to store pickup.",
        "Home delivery is available.",
        ("Collect the order in store.", "Pickup at the shop is required."),
        ("Have the order delivered to your home.", "We deliver orders to your door."),
        "Correct the delivery method",
    ),
    "warranty": (
        "The service guarantee excludes accidental damage.",
        "The service guarantee covers accidental damage.",
        ("Accidents fall outside this guarantee.", "Accidental damage is excluded."),
        ("Accidental damage falls under this guarantee.", "The guarantee includes accidents."),
        "Correct the stated coverage",
    ),
}
TYPED = {"sale_price": ("minor units", 25200), "minimum_order": ("pieces", 24), "price_basis": ("pieces per price", 6)}
SEEDS = (19, 47)


def identifier(s):
    return digest(s.encode())[:10]


def holdout():
    rows, labels = [], {}
    for j, (domain, (units, n)) in enumerate(TYPED.items()):
        for i in range(4):
            uid = identifier("meridian-v3/" + domain + str(i))
            expected = {"amount": n + i, "basis": units}
            wrong = i % 2 == 1
            copy = {**expected, "amount": n + i + int(wrong)}
            rows.append(
                dict(
                    id=uid,
                    kind="typed",
                    domain=domain,
                    severity="P1" if j != 1 else "P2",
                    mandatory=True,
                    subject=f"Canal-{j}/{i}",
                    authorized=expected,
                    observation=copy,
                    locator=f"records/{uid}",
                )
            )
            labels[uid] = "defect" if wrong else "clean"
    for j, (domain, (first, second, first_copy, second_copy, _)) in enumerate(SEMANTICS.items()):
        for i, truth in enumerate(("defect", "clean", "unresolved")):
            uid = identifier("meridian-v3/" + domain + str(i))
            subject = f"{('Lark', 'Reed', 'Tern', 'Finch')[j]}-{i + 7}"
            side = (i + j) % 2
            authorized = (first, second)[side] if truth != "unresolved" else "The price list was updated this week."
            claim = (first_copy, second_copy)[side ^ (truth == "defect")][(j + i) % 2]
            sources = [
                dict(
                    ref="R-" + identifier(uid + str(k)),
                    subject=subject if k == 0 else subject + "-Plus",
                    text=authorized if k == 0 else (first, second)[1 - side],
                )
                for k in range(2)
            ]
            rows.append(
                dict(
                    id=uid,
                    kind="semantic",
                    domain=domain,
                    severity="P1" if domain == "warranty" else "P2",
                    mandatory=True,
                    subject=subject,
                    observation=claim,
                    sources=sources,
                )
            )
            labels[uid] = truth
    return sorted(rows, key=lambda r: r["id"]), labels


def manifest(rows):
    with tempfile.TemporaryDirectory(prefix="airc-union-git-") as directory:
        work = Path(directory)
        git(work, "init", "--quiet", "--object-format=sha1")
        (work / "sources.jsonl").write_bytes(b"".join(encoded({k: v for k, v in r.items() if k != "observation"}) + b"\n" for r in rows))
        git(work, "add", "sources.jsonl")
        git(work, "commit", "-q", "-m", "Frozen synthetic sources")
        base = git(work, "rev-parse", "HEAD").decode().strip()
        (work / "draft.jsonl").write_bytes(b"".join(encoded({k: r[k] for k in ("id", "subject", "observation")}) + b"\n" for r in rows))
        git(work, "add", "draft.jsonl")
        git(work, "commit", "-q", "-m", "Unreviewed copy")
        head = git(work, "rev-parse", "HEAD").decode().strip()
        return {
            "base": base,
            "head": head,
            "blobs": {name: digest(git(work, "show", head + ":" + name)) for name in ("sources.jsonl", "draft.jsonl")},
            "bundle": digest(encoded(rows)),
        }
