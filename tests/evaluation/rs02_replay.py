"""Offline comparison of immutable RS-01 replies at the approved RS-02 baseline."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app import c3_assets, c3_order_units, c3_skill_library, c3_studio  # noqa: E402
from app.c3_tasks import ActionIntent, TaskIntent  # noqa: E402
from app.measurement_integrity import MeasurementDefinition  # noqa: E402

DATA = ROOT / "docs/evaluation/rs01"
OUTPUT = DATA.parent / "rs02/replay.json"


def errors(model, data):
    try:
        model.model_validate(data)
    except ValidationError as exc:
        return {str(e["loc"][0]): e["type"] for e in exc.errors()}
    return {}


def replay():
    with ZipFile(DATA / "ordered-evidence.zip") as archive:
        calls = json.loads(archive.read("journal.json"))["calls"]
        assert len(calls) == 24 and archive.testzip() is None
        for i, call in enumerate(calls, 1):
            raw = json.loads(archive.read(f"call-{i:02d}.raw"))
            assert json.loads(raw["response_text"])["choices"][0]["message"]["content"] == call["first_text"]
    scores = {p["case"]: p["arms"] for p in json.loads((DATA / "FINAL.json").read_bytes())["pairs"]}
    records = []
    for case in json.loads((DATA / "packets.json").read_bytes()):
        projection = case["projection"]
        schema = {model.__name__: errors(model, value) for model, value in (
            (TaskIntent, projection["task_intent"]), (ActionIntent, projection["task_intent"]),
            (MeasurementDefinition, projection["measurement_contract"]))}
        assert all(schema.values())
        for arm in ("A", "B"):
            checkpoints, raw_hashes = {}, {}
            for call in calls:
                if (call["case"], call["arm"]) != (case["id"], arm):
                    continue
                role, first = call["role"], call["first_text"]
                raw_hashes[role] = hashlib.sha256(first.encode()).hexdigest()
                if role != "director":
                    sources = {f["id"]: f for f in projection["facts"]}
                    checkpoints[role] = c3_skill_library.validate(json.loads(first), role, {}, sources)
            assert set(raw_hashes) == {"director", "research", "strategy"}
            workflow = c3_assets.RESEARCH
            try:
                c3_studio.compose(workflow, projection, checkpoints)
            except ValueError as exc:
                locale_failure = str(exc)
            else:
                raise AssertionError("Reassess archive locale compatibility")
            display = {**projection, "locale": "en-US"}
            sections = c3_order_units.artifacts(workflow, display, checkpoints)
            try:
                c3_studio.compose(workflow, display, checkpoints)
            except KeyError as exc:
                failure = str(exc)
            else:
                raise AssertionError("Reassess schema incompatibility before interpreting this replay")
            partial = {k: v for k, v in display.items() if k != "measurement_contract"}
            studio = c3_studio.compose(workflow, partial, checkpoints)
            assert all(f["wording"] in studio["research"]["evidence"] and
                       all(q in studio["research"]["evidence"] for q in f["qualifiers"]) for f in projection["facts"])
            routes = {}
            for field in scores[case["id"]][arm]["edited_fields"]:
                role, key = field.split(".")
                value = checkpoints[role]["sections"][key]
                routes[field] = [f"{group}.{k}" for group, fields in studio.items() for k, v in fields.items() if v == value]
            records.append(dict(case=case["id"], arm=arm, schema_errors=schema, first_text_sha256=raw_hashes,
                                locked_hard_failures=scores[case["id"]][arm]["hard_failures"],
                                full_packet_error=locale_failure, after_locale_only_error=failure, unchanged_edited_field_routes=routes,
                                staff_artifacts=sections, offline_studio_without_incompatible_contract=studio,
                                structural_issues=c3_studio.quality_issues(workflow, studio, partial),
                                authorized_handoff="ineligible: no approved manifest, recipients or reviewed revision"))
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = replay()
    if args.write:
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    elif json.loads(OUTPUT.read_bytes()) != result:
        raise SystemExit("Replay differs from the committed evidence")
    print(f"{len(result)} archived diagnostics; 24 first-response hashes; no provider invoked")
