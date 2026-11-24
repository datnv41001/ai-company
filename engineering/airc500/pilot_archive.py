"""Public replay of the complete successful pilot. Does not invoke the model."""

import base64
import json
from pathlib import Path

from pilot_fixture import COPY, DISPUTE, FACTS, FAMILY, MODEL_DIGEST, POLICY, ROOT, digest, encoded, plan, read_catalog, synthetic_pr
from local_adapter import LocalAdapter
from pilot_records import wire_records
from pilot_report import choose_dispute, evaluate, write_report
from review_journal import Journal, verify_signature


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_bytes(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n")


def participation(totals, records):
    return {
        "distinct_reviewers": len(totals["accepted_reviewer_ids"]),
        "assignments": totals["assignments"],
        "attempts": totals["attempts"],
        "actual_calls": len(records),
        "dispatches": totals["dispatches"],
        "accepted_receipts": totals["accepted_receipts"],
        "rejected_receipts": totals["rejected_receipts"],
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "model_family": FAMILY,
        "max_observed_concurrency": 1,
        "paid_microusd": totals["settled_microusd"],
    }


def challenge_packet(rows, calls):
    from pilot import blind_packet

    selected = []
    for domain in ("editorial", "offer"):
        prior = [c for c in calls if c["phase"] == "blind" or any(k in {r["id"] for r in rows if r["domain"] != domain} for k in c["answer"])]
        selected.append(choose_dispute([u for u in rows if u["domain"] == domain], prior))
    fixed = next(u for u in rows if u["id"] == "H01")
    if fixed not in selected:
        selected.append(fixed)
    return selected, {
        "model_opinions": {u["id"]: blind_packet(calls, u["id"]) for u in selected},
        "authored_counterevidence_exercise": {"unit": "H01", "positions": DISPUTE},
    }


def gather(out, manifest, rows, trust, mode):
    from pilot import blind_packet, messages, parse_answer, shape

    work = out / mode
    catalog = read_catalog()
    run = load(work / "run.json")
    checkpoint = load(work / "checkpoint.json")
    events = load(work / "events.json")
    replay = Journal.verify_events(run["run_id"], events, checkpoint, trust)
    totals = {key: value for key, value in replay.items() if key not in ("run", "accepted_attempts")}
    if replay["run"] != run or run["source_manifest_digest"] != digest(encoded(manifest)):
        raise ValueError("Unpinned source manifest")
    if (
        run["catalog_digest"] != digest((ROOT / "reviewers.jsonl").read_text(encoding="utf-8").encode())
        or run["policy_digest"] != digest(encoded(POLICY))
        or run["dependency_map_digest"] != digest(encoded([FACTS, COPY]))
    ):
        raise ValueError("Catalog or routing pin mismatch")
    records = []
    blind_hashes = []
    attempts = set()
    ids = set()
    jobs = plan(rows, mode == "baseline")
    prior = {e["data"]["attempt_id"]: e["data"] for e in events if e["kind"] == "receipt"}
    received = set()
    for line in (work / "calls.jsonl").read_bytes().splitlines():
        index = len(records)
        item = json.loads(line)
        ass, receipt = item["assignment"], item["receipt"]
        verify_signature(receipt, trust)
        attempt = receipt["attempt_id"]
        if attempt in received:
            raise ValueError("Duplicate raw response")
        received.add(attempt)
        logged = prior.get(attempt)
        if not logged or logged["receipt"] != receipt or logged["output"] != item["raw_base64"]:
            raise ValueError("Raw response is not the recorded adapter result")
        failed = receipt["outcome"] == "failed"
        if failed and (logged["state"] != "settled" or item["disposition"] != "ledger_only"):
            raise ValueError("Unexpected failed attempt disposition")
        attestation = (
            next(
                ({"assignment": e["data"]["assignment"], "receipt": receipt} for e in events if e["kind"] == "reserved" and e["data"]["attempt_id"] == attempt),
                None,
            )
            if failed
            else replay["accepted_attempts"].get(attempt)
        )
        if not attestation or attestation["assignment"] != ass or attestation["receipt"] != receipt or attempt in attempts:
            raise ValueError("Unknown, stale or repeated archived assignment")
        if not failed:
            attempts.add(attempt)
        if ass["assignment_id"] != f"{mode}-{index + 1:02d}" or ass["head_sha"] != manifest["head_sha"] or ass["base_sha"] != manifest["base_sha"]:
            raise ValueError("Wrong run or revision")
        if index < len(jobs):
            reviewer, domain, units = jobs[index]
            phase, peers, instructions = "blind", [], "Seal your own observations before reading any peer."
            if not failed:
                blind_hashes.append(receipt["output_digest"])
        elif mode == "targeted" and index < len(jobs) + 2:
            domain, reviewer = (("editorial", "MK-052"), ("offer", "MK-022"))[index - len(jobs)]
            units = [choose_dispute([u for u in rows if u["domain"] == domain], records)]
            phase, peers, instructions = "cross", blind_packet(records, units[0]["id"]), "Challenge the sealed interpretations against the two source lines."
        elif mode == "targeted" and index == len(jobs) + 2:
            reviewer, phase, domain = "AR-002", "arbitration", "evidence arbitration"
            units, peers = challenge_packet(rows, records)
            instructions = "Assess competing explanations. Weight verifiable observations, not votes."
        else:
            raise ValueError("Unexpected call")
        expected_request = LocalAdapter(None, "airc-qwen-" + MODEL_DIGEST[:12], None, None).payload(
            messages(catalog[reviewer], units, instructions, peers), shape(units), 613 + index
        )
        raw = base64.b64decode(item["raw_base64"], validate=True)
        if (
            item["attempt_id"] != attempt
            or (not failed and item["disposition"] != "accepted")
            or ass["reviewer_id"] != reviewer
            or ass["phase"] != phase
            or ass["topic"] != domain
            or expected_request != item["request"]
            or digest(encoded(expected_request)) != receipt["context_digest"]
            or digest(raw) != receipt["output_digest"]
            or (not failed and receipt["outcome"] != "completed")
        ):
            raise ValueError("Scope, raw output or context mismatch")
        reply = json.loads(raw)
        if (
            reply["id"] != receipt["provider_request_or_local_execution_id"]
            or reply["id"] in ids
            or reply["model"] != expected_request["model"]
            or reply["usage"]["prompt_tokens"] != receipt["input_tokens"]
            or reply["usage"]["completion_tokens"] != receipt["output_tokens"]
        ):
            raise ValueError("Adapter identity, usage or request ID mismatch")
        ids.add(reply["id"])
        if failed:
            continue
        records.append(
            {
                "assignment_id": ass["assignment_id"],
                "attempt_id": attempt,
                "reviewer_id": reviewer,
                "phase": phase,
                "answer": parse_answer(raw, [u["id"] for u in units]),
            }
        )
    seal = load(work / "blind-seal.json")
    if (
        received != set(prior)
        or len(records) != len(jobs) + (3 if mode == "targeted" else 0)
        or attempts != set(replay["accepted_attempts"])
        or seal
        != {
            "run_id": run["run_id"],
            "seal": totals["blind_seal_digest"],
            "assignments": [r["assignment_id"] for r in records if r["phase"] == "blind"],
            "outputs": blind_hashes,
        }
    ):
        raise ValueError("Missing planned receipt or invalid blind seal")
    assessment = evaluate(rows, records, manifest, run["run_id"])
    docs = wire_records(rows, [dict(c, run_id=run["run_id"]) for c in records], manifest, assessment)
    result = {
        "run_id": run["run_id"],
        "participation": participation(totals, received),
        "ledger": totals,
        "coverage": "complete",
        "evaluation": assessment,
        "decision": "changes_requested" if assessment["verified_units"] else "inconclusive",
    }
    return result, docs


def public_index(out):
    names = ["adapter.json", "trust.json", "source-manifest.json", "results.json", "REPORT.md"]
    for mode in ("baseline", "targeted"):
        names.extend(mode + "/" + file for file in ("run.json", "calls.jsonl", "checkpoint.json", "blind-seal.json", "events.json", "normalized.jsonl"))
    return {name: digest((out / name).read_bytes()) for name in sorted(names)}


def verify_index(directory, expected):
    out = Path(directory)
    data = (out / "index.json").read_bytes()
    if digest(data) != expected or json.loads(data) != public_index(out):
        raise ValueError("Evidence package differs from the externally pinned SHA-256")


def assemble(directory, trust_pin, materialize=False):
    out = Path(directory)
    if digest((out / "trust.json").read_bytes()) != trust_pin:
        raise ValueError("Untrusted public key registry")
    manifest, rows = synthetic_pr()
    if load(out / "source-manifest.json") != manifest:
        raise ValueError("Synthetic Git history mismatch")
    trust = load(out / "trust.json")
    adapter = load(out / "adapter.json")
    result = {"manifest": manifest, "adapter": adapter, "public_trust_sha256": trust_pin}
    for mode in ("targeted", "baseline"):
        work = out / mode
        if materialize:
            j = Journal(work / "ledger.sqlite")
            write(work / "events.json", j.export_events(load(work / "run.json")["run_id"]))
            j.close()
        group, records = gather(out, manifest, rows, trust, mode)
        result[mode] = group
        data = b"".join(encoded(r) + b"\n" for r in records)
        if materialize:
            (work / "normalized.jsonl").write_bytes(data)
        elif (work / "normalized.jsonl").read_bytes().replace(b"\r\n", b"\n") != data:
            raise ValueError("Normalized review records differ from raw output")
    report = write_report(result)
    if materialize:
        write(out / "results.json", result)
        (out / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    elif load(out / "results.json") != result or (out / "REPORT.md").read_text(encoding="utf-8") != report:
        raise ValueError("Consolidated report does not match journal and raw output")
    if materialize:
        write(out / "index.json", public_index(out))
        print("Evidence index SHA-256:", digest((out / "index.json").read_bytes()))
    print("Verified Git commits, signed calls, event history, review packets, evidence and quality metrics.")
