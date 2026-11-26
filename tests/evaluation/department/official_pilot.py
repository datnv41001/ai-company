"""Offline custody, staged blind scoring and reconciliation for one preregistered four-arm pilot."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from four_arm_pilot import ARMS, KIT, score
from pilot import ROLES, ROOT, RUBRIC, blank, by_arm, dump, read

JOURNEYS = ("rfq", "appointment")
STAGES = ("initial", "edited", "delivered")
REVISION = dict(initial=1, edited=2, delivered=3)
SCHEMA = "official-department-pilot/1"
COSTS = ("labor_vnd", "model_vnd", "compute_vnd", "tools_vnd", "other_vnd")


def require(valid, reason):
    if not valid:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private_path(path):
    path = Path(path).resolve()
    require(not path.is_relative_to(ROOT) and not any((p / ".git").exists() for p in (path, *path.parents)), "Keep private study files outside Git checkouts")
    return path


def create_vault(path):
    path.mkdir(mode=0o700, exist_ok=False)
    if os.name == "nt":
        # Windows 3.12 deployments may inherit the parent's ACL. Restrict the empty vault before writing any keys.
        who = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True)
        sid = re.search(r"S-1-[0-9-]+", who).group()
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"], check=True, stdout=subprocess.DEVNULL)


def write_once(path, data):
    with path.open("xb") as f:
        f.write(data)


def rubric_text():
    text = (ROOT / "docs/evaluation/department-study/PROTOCOL.md").read_text(encoding="utf-8")
    return ("## Rubric" + text.split("## Rubric", 1)[1]).encode()


def public_hashes():
    hashes = set()
    for archive in (KIT / "02-candidates.zip", KIT.parent / "PILOT-ABCD/work-orders.zip"):
        with ZipFile(archive) as z:
            hashes.update(
                sha(z.read(name).replace(b"\r\n", b"\n").strip())
                for name in z.namelist()
                if name.endswith(("/brief.md", "/first.md", "/starting.md", "/reviewed.md"))
            )
    return hashes


def blind_text(raw, labels=()):
    text = raw.decode("utf-8")
    require(text.strip() and len(raw) <= 2_000_000 and all(c.isprintable() or c in "\n\r\t" for c in text), "Use a nonempty anonymized UTF-8 text artifact")
    require(
        not re.search(
            r"\b(?:Qwen\w*|GPT-?\d\w*|ARM [ABCD]|nhánh [ABCD]|ai_assisted|ai_plus_independent_qa|P-[0-9a-f]{8,}|(?:work|card)-[0-9a-f]{16,})\b", text, re.I
        )
        and not any(label.lower() in text.lower() for label in labels),
        "Possible treatment, alias or participant disclosure in blinded text",
    )


def roles_for(arm):
    return set(ROLES) | ({"production_qa"} if arm == ARMS[-1] else set())


def validate_design(design):
    orders = design["orders"]
    require(design["version"] == SCHEMA and len(orders) == 8, "Official design requires eight commissioned work orders")
    require(
        Counter((o["brief"], o["arm"]) for o in orders.values()) == Counter((brief, arm) for brief in JOURNEYS for arm in ARMS), "Need each arm once per brief"
    )
    people, cards = {}, set()
    for name, order in orders.items():
        require(re.fullmatch(r"work-[0-9a-f]{32}", name) and set(order["roles"]) == roles_for(order["arm"]), "Invalid assignment")
        for role, actor in order["roles"].items():
            require(
                isinstance(actor, str) and re.fullmatch(r"[A-Za-z0-9_-]{4,50}", actor) and actor == actor.lower() and people.setdefault(actor, role) == role,
                "Actor roles must remain independent study-wide",
            )
        require(set(order["cards"]) == set(STAGES), "Missing stage cards")
        for card in order["cards"].values():
            require(re.fullmatch(r"card-[0-9a-f]{32}", card) and card not in cards, "Fresh unique blind card required")
            cards.add(card)


def issue(vault, materials):
    vault, materials = private_path(vault), private_path(materials)
    roster = read(materials / "roster.json")
    require(set(roster) == set(JOURNEYS) and all(set(r) == set(ARMS) for r in roster.values()), "Roster must cover eight work orders")
    forbidden = public_hashes()
    design = {"version": SCHEMA, "run": secrets.token_hex(16), "rubric_sha256": sha(rubric_text()), "orders": {}}
    files = {}
    for brief in JOURNEYS:
        folder = materials / brief
        text = (folder / "brief.md").read_bytes()
        c = (folder / "ai.md").read_bytes()
        b = (folder / "control.md").read_bytes()
        require(sha(c) != sha(b), "Distinct deterministic and AI comparison required")
        for data in (text, b, c):
            blind_text(data)
            require(sha(data.replace(b"\r\n", b"\n").strip()) not in forbidden, "Public fixture bytes cannot be used in the official pilot")
        arms = list(ARMS)
        secrets.SystemRandom().shuffle(arms)
        for arm in arms:
            alias = "work-" + secrets.token_hex(16)
            start = {"manual": b"", "control": b, "ai_assisted": c, "ai_plus_independent_qa": c}[arm]
            design["orders"][alias] = {
                "brief": brief,
                "arm": arm,
                "roles": roster[brief][arm],
                "brief_sha256": sha(text),
                "start_sha256": sha(start),
                "cards": {stage: "card-" + secrets.token_hex(16) for stage in STAGES},
            }
            files[alias] = (text, start)
    validate_design(design)
    require(len({o["brief_sha256"] for o in design["orders"].values()}) == 2, "Two distinct briefs required")
    create_vault(vault)
    for alias, (text, start) in files.items():
        folder = vault / alias
        folder.mkdir()
        (folder / "brief.md").write_bytes(text)
        (folder / "starting.md").write_bytes(start)
        order = design["orders"][alias]
        blind_text(text, order["roles"].values())
        with ZipFile(folder / "producer.zip", "x") as z:
            z.writestr("brief.md", text)
            z.writestr("starting.md", start)
            z.writestr("work-order.json", dump({"work_order": alias, "arm": order["arm"], "starting_sha256": sha(start)}))
    (vault / "rubric.md").write_bytes(rubric_text())
    write_once(
        vault / "outcomes-template.json",
        dump({alias: {"status": "pending", "reason": "Awaiting assigned participants"} for alias in design["orders"]}).encode(),
    )
    lock = dump(design).encode()
    # The key becomes visible to the CLI only after every work order has been written.
    write_once(vault / "design.json", lock)
    return sha(lock)


def load(vault, lock):
    vault = private_path(vault)
    raw = (vault / "design.json").read_bytes()
    require(sha(raw) == lock, "Design differs from the independently escrowed lock")
    design = json.loads(raw)
    validate_design(design)
    require(sha((vault / "rubric.md").read_bytes()) == design["rubric_sha256"], "Changed rubric")
    for name, order in design["orders"].items():
        for file, key in (("brief.md", "brief_sha256"), ("starting.md", "start_sha256")):
            require(sha((vault / name / file).read_bytes()) == order[key], "Changed commissioned brief or starting draft")
    return design


def reference(order, stage, data):
    return {"card": order["cards"][stage], "revision": REVISION[stage], "sha256": sha(data)}


def retained(folder, order, stage):
    snap = folder / stage
    require((snap / "artifact.md").is_file(), f"Missing {stage} artifact")
    raw = (snap / "artifact.md").read_bytes()
    ref = reference(order, stage, raw)
    require(read(snap / "receipt.json") == ref, f"Retained {stage} digest or revision mismatch")
    return raw, ref


def blank_grade(ref, stage, role):
    if stage == "initial":
        require(role == "independent_reviewer", "The independent reviewer grades first pass")
        return {
            "reference": ref,
            "actor_code": None,
            "consent": None,
            "accepted": None,
            "reason": None,
            "unblinded": None,
            "rubric": {k: {"score_0_2": None, "evidence": None} for k in RUBRIC},
        }
    if stage == "edited":
        require(role in ("marketer", "production_qa"), "Edited handoff is for the producer or production QA")
        if role == "production_qa":
            return {
                "actor_code": None,
                "input": ref,
                "output": None,
                "decision": None,
                "consent": None,
                "findings_or_no_change_reason": None,
                "qa_seconds": None,
                "labor_vnd": None,
                "cost_ref": None,
            }
        return {"reference": ref, "actor_code": None, "decision": None, "reason": None}
    if role == "production_qa":
        return {
            "actor_code": None,
            "input": None,
            "output": ref,
            "decision": None,
            "consent": None,
            "findings_or_no_change_reason": None,
            "qa_seconds": None,
            "labor_vnd": None,
            "cost_ref": None,
        }
    require(role in ROLES, "Choose the recipient of this delivery scorecard")
    form = blank("", "")
    for k in ("brief", "package", "first_pass_accepted", "reference_to_delivered_revision", "delivered_artifact_sha256"):
        del form[k]
    form.update(role=role, reference=ref, unblinded=None)
    if role == "marketer":
        form["overhead"]["model_vnd"] = None
    return form


def capture(vault, lock, alias, stage, source):
    order = load(vault, lock)["orders"][alias]
    require(stage in STAGES, "Unknown stage")
    folder = vault / alias
    require(not (folder / "delivered").exists(), "Delivery already sealed")
    data = private_path(source).read_bytes()
    blind_text(data, order["roles"].values())
    if stage == "initial" and order["arm"] != "manual":
        require(sha(data) == order["start_sha256"], "Initial artifact must match the commissioned unchanged starting bytes")
    if stage != "initial":
        first, ref = retained(folder, order, "initial")
        require(
            (folder / "initial-grade.json").exists() and read(folder / "initial-grade.json")["reference"] == ref,
            "Seal the first-pass grade before editing or delivery",
        )
        if stage == "delivered" and (data != first or order["arm"] == ARMS[-1] or (folder / "edited").exists()):
            edited, _ = retained(folder, order, "edited")
            if order["arm"] != ARMS[-1]:
                require(edited == data, "Edited bytes must match delivery without a separate production QA stage")
    ref = reference(order, stage, data)
    temp = Path(tempfile.mkdtemp(dir=folder))
    try:
        (temp / "artifact.md").write_bytes(data)
        (temp / "receipt.json").write_text(dump(ref), encoding="utf-8")
        temp.rename(folder / stage)  # A previously captured non-empty stage cannot be replaced.
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return ref


def packet(vault, lock, alias, stage, destination, role="independent_reviewer"):
    order = load(vault, lock)["orders"][alias]
    require(stage in STAGES, "Unknown stage")
    require(role in order["roles"], "Role was not commissioned for this work order")
    raw, ref = retained(vault / alias, order, stage)
    form = blank_grade(ref, stage, role)
    dest = private_path(destination)
    require(dest.name == ref["card"] + ".zip" and not dest.is_relative_to(vault.resolve()), "Use only the assigned blind card filename outside custody")
    with ZipFile(dest, "x") as z:
        z.writestr("brief.md", (vault / alias / "brief.md").read_bytes())
        z.writestr("artifact.md", raw)
        z.writestr("rubric.md", (vault / "rubric.md").read_bytes())
        z.writestr("card.json", dump(ref))
        z.writestr("scorecard.json", dump(form))
    return ref


def validate_first_grade(form, ref, order):
    require(form["reference"] == ref, "First-pass decision must cite the original card, revision and digest")
    require(
        form["actor_code"] == order["roles"]["independent_reviewer"]
        and form["consent"] is True
        and type(form["accepted"]) is bool
        and type(form["unblinded"]) is bool
        and form["reason"].strip(),
        "Incomplete initial decision or wrong reviewer",
    )
    for key in RUBRIC:
        mark = form["rubric"][key]
        require(type(mark["score_0_2"]) is int and mark["score_0_2"] in (0, 1, 2) and mark["evidence"].strip(), "Incomplete first-pass rubric")


def first_grade(vault, lock, alias, form):
    order = load(vault, lock)["orders"][alias]
    _, ref = retained(vault / alias, order, "initial")
    validate_first_grade(form, ref, order)
    write_once(vault / alias / "initial-grade.json", dump(form).encode())


def failed_cost(row):
    amounts = [row.get(k) for k in COSTS]
    require(all(v is None or type(v) is int and v >= 0 for v in amounts), "Invalid failed-attempt cost")
    return sum(amounts) if None not in amounts and row.get("includes_failed_attempts") is True and row.get("receipt_refs") else None


def report(vault, lock, outcomes):
    design = load(vault, lock)
    orders = design["orders"]
    require(set(outcomes) == set(orders), "Include all eight work orders, even failed or pending orders")
    treatments, rows, reviews, stages = {}, [], [], {}
    for alias, order in orders.items():
        name = order["brief"] + "/" + alias
        treatments[name] = order["arm"]
        folder = vault / alias
        outcome = outcomes[alias]
        state = outcome["status"]
        require(state in ("completed", "pending", "failed", "unblinded"), "Unknown disposition")
        opened = {}
        for stage in STAGES:
            if (folder / stage).exists():
                _, opened[stage] = retained(folder, order, stage)
        grade_file = folder / "initial-grade.json"
        grade = read(grade_file) if grade_file.exists() else None
        if grade is not None:
            validate_first_grade(grade, opened.get("initial"), order)
        incident = (folder / "unblinding.json").is_file() or bool(grade and grade["unblinded"])
        stages[name] = {
            "status": state,
            "evidence": opened,
            "first_pass_accepted": grade["accepted"] if grade and not incident else None,
            "unblinded": incident or state == "unblinded",
        }
        if state != "completed":
            require(isinstance(outcome.get("reason"), str) and outcome["reason"].strip(), "Record why this work order is outstanding")
            stages[name]["reason"] = outcome["reason"]
            if state == "failed":
                require("delivered" not in opened, "Use business rejection on a delivered work order")
                stages[name]["failed_attempt_cost_vnd"] = failed_cost(outcome.get("cost", {}))
            continue
        require("initial" in opened and grade is not None, "Missing initial artifact or independent first-pass decision")
        require("delivered" in opened, "Missing delivered artifact")
        delivered = opened["delivered"]
        edited = opened.get("edited")
        if order["arm"] == ARMS[-1] or opened["initial"]["sha256"] != delivered["sha256"]:
            require(edited is not None, "Missing edited/pre-QA artifact")
        if edited:
            edit = outcome.get("edited_decision") or {}
            require(
                edit.get("reference") == edited
                and edit.get("actor_code") == order["roles"]["marketer"]
                and edit.get("decision") == "submitted"
                and edit.get("reason"),
                "Bind marketer handoff to edited revision",
            )
        final_forms = outcome["observations"]
        require(len(final_forms) == 3 and {form["role"] for form in final_forms} == set(ROLES), "Three independent delivery observations required")
        for form in final_forms:
            role = form["role"]
            require(
                form["actor_code"] == order["roles"][role] and form["reference"] == delivered,
                "Delivered observation must match the commissioned actor, blind card, revision and digest",
            )
            require(type(form["unblinded"]) is bool, "Missing exposure declaration")
            incident |= form["unblinded"]
            if role == "independent_reviewer":
                require(form.get("first_pass_accepted") is None or form["first_pass_accepted"] is grade["accepted"], "Conflicting first-pass decision")
            rows.append(
                form
                | {
                    "brief": order["brief"],
                    "package": alias,
                    "reference_to_delivered_revision": delivered["card"] + "/r" + str(delivered["revision"]),
                    "delivered_artifact_sha256": delivered["sha256"],
                    "first_pass_accepted": grade["accepted"] if role == "independent_reviewer" else None,
                }
            )
        stages[name]["unblinded"] = incident
        if order["arm"] == ARMS[-1]:
            qa = outcome.get("production_qa") or {}
            require(
                qa.get("actor_code") == order["roles"]["production_qa"]
                and qa.get("input") == edited
                and qa.get("output") == delivered
                and qa.get("decision") == "approved"
                and qa.get("findings_or_no_change_reason"),
                "Missing independent production QA on edited and delivered revisions",
            )
            reviews.append(qa | {"name": name, "first_sha256": edited["sha256"], "final_sha256": delivered["sha256"]})
        else:
            require(not outcome.get("production_qa"), "Unexpected production QA outside D")
    packages = score(treatments, rows, reviews, vault, staged=True)["packages"]
    for name, row in packages.items():
        record = stages[name]
        row.update(record)
        if row["status"] == "completed":
            require(row["artifact_verification"]["status"] == "verified" and row.get("preqa_verified", True), "Independent evidence is incomplete")
        if row["unblinded"]:
            row.update(
                status="unblinded",
                verified_business_decision=None,
                first_pass_accepted=None,
                all_in_cost_per_business_accepted_vnd=None,
                recorded_labor_cost_per_business_accepted_vnd=None,
            )
        elif row["status"] == "failed":
            row["recorded_total_vnd"] = record["failed_attempt_cost_vnd"]
        # Package-level spend is observable, but cost per accepted work unit also depends on failed and incomplete peers.
        del row["all_in_cost_per_business_accepted_vnd"], row["recorded_labor_cost_per_business_accepted_vnd"]
    # A failed production attempt is a known non-acceptance for the denominator, distinct from a Sales rejection.
    arms = by_arm(
        {
            name: row | {"verified_business_decision": False if row["status"] == "failed" else row["verified_business_decision"]}
            for name, row in packages.items()
        }
    )
    for arm, s in arms.items():
        units = [v for v in packages.values() if v["arm"] == arm]
        s["dispositions"] = dict(Counter(v["status"] for v in units))
        s["first_pass_scored"] = sum(v["first_pass_accepted"] is not None for v in units)
        s["first_pass_accepted"] = sum(v["first_pass_accepted"] is True for v in units)
    return {"mode": "official_locked_design", "run": design["run"], "design_sha256": lock, "commissioned": len(orders), "packages": packages, "arms": arms}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for command, positional in {
        "issue": ("materials",),
        "capture": ("alias", "stage", "source"),
        "packet": ("alias", "stage", "destination"),
        "grade": ("alias", "form"),
        "incident": ("alias", "note"),
        "report": ("outcomes",),
    }.items():
        s = sub.add_parser(command)
        s.add_argument("vault", type=Path)
        if command != "issue":
            s.add_argument("--lock", required=True, help="Digest held independently before unblinding")
        if command == "packet":
            s.add_argument("--role", choices=(*ROLES, "production_qa"), default="independent_reviewer")
        if command == "report":
            s.add_argument("--out", type=Path, required=True, help="New audit file inside the private vault")
        for arg in positional:
            s.add_argument(arg, type=str if arg in ("alias", "stage", "note") else Path)
    a = parser.parse_args()
    if a.action == "issue":
        print(issue(a.vault, a.materials))
    elif a.action == "capture":
        print(dump(capture(a.vault, a.lock, a.alias, a.stage, a.source)))
    elif a.action == "packet":
        packet(a.vault, a.lock, a.alias, a.stage, a.destination, a.role)
    elif a.action == "grade":
        first_grade(a.vault, a.lock, a.alias, read(private_path(a.form)))
    elif a.action == "incident":
        require(a.alias in load(a.vault, a.lock)["orders"] and a.note.strip(), "Expected work order and a de-identified incident note")
        write_once(a.vault / a.alias / "unblinding.json", dump({"note": a.note}).encode())
    else:
        out = private_path(a.out)
        require(out.is_relative_to(a.vault.resolve()), "Detailed results belong in the private vault")
        result = report(a.vault, a.lock, read(private_path(a.outcomes)))
        write_once(out, dump(result).encode())
        print(dump({"design_sha256": a.lock, "commissioned": result["commissioned"], "arms": result["arms"]}))


if __name__ == "__main__":
    main()
