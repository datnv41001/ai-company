"""Replay two public synthetic WF-03 tasks with fixed decoder replies and export paired workpapers.

Run from the repository root with python -m scripts.strategy_study --output <new-directory>.
This comparison calls the released request builder, validator and staff composer in-process.
All source records and decoder responses are development fixtures. No model or database runs.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile

from app import c3_order_units, c3_studio, registry_adapters
from migrations.runtime_bundle import canonical_hash
from scripts.strategy_workpaper import build_workpaper, coding_digest, eligible_sources


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/strategy_study"
WORKFLOW = "WF-03/research-strategy-draft@3"


def fixture(name):
    return json.loads((FIXTURES / (name + ".json")).read_bytes())


def cases():
    """Open counterfactuals. Only a named input condition changes; the decoder is held fixed."""
    tray, studio = fixture("route-tray"), fixture("fold-studio")
    suite = {"route-shift": tray, "studio-first-visit": studio}

    keep = deepcopy(tray)
    keep["packet"]["brief"].update(segment="storekeepers", situation="quarterly stock count",
                                    decision="Which use should lead a page for a storekeeper preparing a stock count?",
                                    objective="Help the storekeeper review the count-sheet workflow.")
    suite["route-storekeeper"] = keep

    changed = deepcopy(tray)
    original = next(s for s in changed["packet"]["sources"] if s["id"] == "tray-one")
    replacement = {**original, "revision": 2, "recorded_at": "2026-11-14T08:00:00Z", "option": "audit",
                   "excerpt": "Corrected observation: at shift handover the supervisor used the inventory audit layout."}
    replacement["coding_digest"] = coding_digest(replacement)
    changed["packet"]["sources"].append(replacement)
    suite["route-corrected-observation"] = changed

    split = deepcopy(tray)
    opposite = {**original, "id": "tray-counter", "record_id": "separate-tray-event", "option": "audit",
                "excerpt": "At a different staged handover a shift supervisor used the quarterly count layout.",
                "sample": "One supervisor in a separate staged handover."}
    opposite["coding_digest"] = coding_digest(opposite)
    split["packet"]["sources"].append(opposite)
    suite["route-disagreement"] = split

    withdrawn = deepcopy(tray)
    for source in withdrawn["packet"]["sources"]:
        if source["kind"] == "channel":
            source["revoked_at"] = "2026-11-15T12:00:00Z"
        if source["kind"] == "measurement":
            source["valid_until"] = "2026-11-15T12:00:00Z"
    suite["route-withdrawn-channel-expired-measure"] = withdrawn

    unclear = deepcopy(studio)
    unclear["packet"]["brief"].update(segment=None, situation=None)
    suite["studio-clarify"] = unclear

    indirect = deepcopy(studio)
    for source in indirect["packet"]["sources"]:
        if source["kind"] == "observation":
            source.update(segment="facilitators", situation="rehearsing an instructor demonstration")
            source["coding_digest"] = coding_digest(source)
    suite["studio-unrepresented"] = indirect

    foreign = deepcopy(studio)
    record = deepcopy(foreign["packet"]["sources"][1])
    record["scope"]["client_id"] = "another-synthetic-client"
    record.update(id="other-client-observation", record_id="other-client-event",
                  excerpt="Synthetic foreign-client canary. A group organizer used the private note.",
                  option="group_booking")
    foreign["packet"]["sources"].append(record)
    suite["studio-foreign-record"] = foreign
    return suite


def baseline(case):
    packet, replies = case["packet"], case["controlled_replies"]
    if packet["workflow"] != WORKFLOW:
        raise ValueError("The replay requires the reviewed WF-03 release")
    manifest = json.loads((ROOT / "catalog/research-strategy-v3.json").read_bytes())
    brief = packet["brief"]
    visible = eligible_sources(packet)
    sources = {s["id"]: s for s in visible}
    facts = []
    for source in visible:
        # Preserve observation, source purpose, sample, topic and provenance as seen by the candidate.
        # Metadata is reference material in each role prompt, not a desired decision or a scored label.
        metadata = {k: v for k, v in source.items() if k not in ("id", "excerpt", "scope")}
        facts.append({"id": source["id"], "wording": source["excerpt"],
                      "qualifiers": [json.dumps(metadata, ensure_ascii=False, sort_keys=True)]})
    channels = [s["value"] for s in visible if s["kind"] == "channel"]
    methods = [s["value"] for s in visible if s["kind"] == "measurement"]
    intent = {"purpose": brief["decision"], "requirements": [json.dumps(brief, ensure_ascii=False, sort_keys=True)],
              "audience": brief["segment"] or "", "product": brief["product"], "exclusions": brief["constraints"],
              "buyer_action": brief["buyer_action"], "editorial_style": "plain",
              "acceptance_criteria": ["Keep observations separate from market-wide claims."]}
    projection = {"product": brief["product"], "audience": brief["segment"] or "", "objective": brief["objective"],
                  "brand": packet["scope"]["brand_id"], "region": "synthetic study site", "locale": "en-US",
                  "channel": "; ".join(channels), "kpi": "; ".join(methods), "facts": facts,
                  "task_intent": intent, "hypotheses": [brief["assumption"]], "gaps": []}
    registry = {"workflow": WORKFLOW, "contracts": manifest["contracts"]}
    run = SimpleNamespace(knowledge={"registry": registry, "sources": sources, "c3_projection": projection})
    verified, contexts = {}, {}
    for role in ("research", "strategy"):
        adapter = registry_adapters.resolve(manifest["contracts"][role])
        if not adapter or adapter.version != 4:
            raise ValueError("Reviewed adapter is unavailable on this checkout")
        body = registry_adapters.specialist_request(run, "offline-controlled-decoder", node=SimpleNamespace(skill=role),
                                                    predecessors=deepcopy(verified), assignment=brief["decision"])
        contexts[role] = json.loads(body["messages"][-1]["content"])
        verified[role] = adapter.validate(replies[role], role, [], sources, registry)
    groups = c3_studio.compose(WORKFLOW, projection, verified)
    bindings = {"workflow": WORKFLOW, "scope": packet["scope"], "packet_sha256": canonical_hash(packet),
                "source_refs": {s: s for s in sources}, "source_revisions": {s: row["revision"] for s, row in sources.items()}}
    return {"kind": "synthetic fixed decoder; released request/validation and staff composition",
            "model_calls": 0, "packet_sha256": bindings["packet_sha256"], "checkpoints": {**verified, "binding": bindings},
            "request_contexts": contexts, "staff_groups": groups,
            "staff_findings": c3_studio.quality_issues(WORKFLOW, groups, projection),
            "source_report": c3_order_units.artifacts(WORKFLOW, projection, verified)["evidence_report"]}


def compare(case):
    before = baseline(case)
    return before, build_workpaper(case["packet"], before["checkpoints"])


def work_order(case, after):
    research, strategy, handoff = (after[key] for key in ("research", "strategy", "department_handoff"))
    lines = ["# " + case["packet"]["brief"]["product"], "", research["decision"], "",
             "## Research", "", research["interpretation"], "",
             f"Segment: {research['segment'] or 'clarify'}. Buying situation: {research['buying_episode'] or 'clarify'}.",
             "", "### Observations in this context", ""]
    for row in research["observations"]:
        lines.append(f"- {row['quote']} [{row['source_id']} · revision {row['revision']}] {row['sample']}")
    if not research["observations"]:
        lines.append("No directly comparable episode in this packet.")
    lines.extend(["", "### Questions for the next research session", ""])
    lines.extend("- " + question for question in research["questions"])
    lines.extend(["", "### Limits and contrary evidence", ""])
    lines.extend("- " + sample for sample in research["limitations"])
    lines.extend("- Counterevidence: " + row["quote"] + " [" + row["source_id"] + "]" for row in research["counterevidence"])
    lines.extend(["", "## Strategy", "", f"Status: {strategy['status']}. Proposed option: {strategy['selected_option'] or 'pending'}.",
                  "", strategy["positioning"] or "Clarify the decision before positioning.", ""])
    for option in strategy["options"]:
        lines.append(f"- {option['label']}. {option['tradeoff']}")
    lines.extend(["", *strategy["rationale"], "", "Test hypothesis: " + (strategy["test_hypothesis"] or "pending"),
                  "", "Reconsider when: " + strategy["reconsider_if"], "",
                  "Channel: " + (strategy["channel"]["value"] or "unconfirmed"),
                  "", "Measurement: " + (strategy["measurement"]["value"] or "unconfirmed"),
                  "", "## Content handoff", "", "Status: " + handoff["status"],
                  "", "Recipient: " + handoff["recipient"], "", "Objective: " + handoff["objective"],
                  "", "Asset: " + (handoff["asset"] or "Hold assignment pending evidence and approval."), ""])
    if handoff["message"]:
        lines.append(handoff["message"]["direction"])
        lines.extend(handoff["message"]["product_wording"])
    lines.extend(["", *("- " + limit for limit in handoff["claim_limits"]),
                  "", "Approver: " + str(handoff["approval"]["role"]), "", handoff["approval"]["action"],
                  "", "Full scope, source revisions, checkpoint review and comparisons are in after.json."])
    return "\n".join(lines) + "\n"


def export(destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("Choose a new output directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        staged = Path(tmp) / "study"
        staged.mkdir()
        index = []
        for key, case in cases().items():
            before, after = compare(case)
            directory = staged / key
            directory.mkdir()
            entry = {"case": key, "packet_sha256": before["packet_sha256"]}
            for filename, data in (("before", before), ("after", after)):
                encoded = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
                (directory / (filename + ".json")).write_bytes(encoded)
                entry[filename + "_sha256"] = sha256(encoded).hexdigest()
            (directory / "WORK-ORDER.md").write_text(work_order(case, after), encoding="utf-8")
            entry.update(status=after["strategy"]["status"], selected=after["strategy"]["selected_option"],
                         handoff=after["department_handoff"]["status"])
            index.append(entry)
        (staged / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        staged.rename(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    export(parser.parse_args().output)
