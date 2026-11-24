"""Run the paired AIRC quality experiment or replay the released evidence offline."""

from datetime import datetime, timedelta, timezone
import gzip
from jsonschema.exceptions import ValidationError
import json
from uuid import uuid4

from pilot_fixture import ROOT, digest, encoded, read_catalog
from quality_corpus import DOMAINS, deterministic
from quality_eval import CRITERIA, OPS, REASONS, structured
from review_journal import Journal
from review_plan import plan_digest

RIDS = ("MK-022", "MK-052", "MK-054", "MK-055", "LC-012", "MK-025", "QT-033", "QT-032")
WORDS = ("common", "repeat", "specialist", "cross", "arbitration")
PHASES = {"common": "blind", "repeat": "blind", "specialist": "blind", "cross": "cross", "arbitration": "arbitration"}


def save(path, obj):
    path.write_bytes(encoded(obj) + b"\n")


def read(path):
    return json.loads(path.read_bytes())


def frozen(cases, seed):
    cat = read_catalog()
    jobs = []
    for group in WORDS:
        shards = (len(cases) + 11) // 12
        for i in range(shards):
            scope = cases[i::shards]
            reviewer = (
                "MK-022" if group in ("common", "repeat") else (RIDS[(i + 1) % 8] if group == "specialist" else ("MK-053" if group == "cross" else "AR-002"))
            )
            # Common and second specialist always have distinct IDs even for the last shard.
            if group == "specialist" and reviewer == "MK-022":
                reviewer = "MK-023"
            if all(c["domain"] == "identity" for c in scope):
                reviewer = {"common": "SP-011", "repeat": "SP-011", "specialist": "SP-012", "cross": "QT-032", "arbitration": "AR-002"}[group]
            jobs.append(
                {
                    "assignment_id": f"s{seed}-{group}-{i}",
                    "phase": PHASES[group],
                    "reviewer_id": reviewer,
                    "artifact_kind": cat[reviewer]["output"]["artifact_kind"],
                    "obligations": [c["unit"] for c in scope],
                }
            )
    return {"version": 1, "assignments": jobs, "required_obligations": [c["unit"] for c in cases]}


def shape(scope):
    if all(c["domain"] == "identity" for c in scope):
        fields = {}
        for i, c in enumerate(scope):
            choices = {
                "status": ["flag", "clear", "unsure"],
                "affected_subject": c["subjects"],
                "current": c["values"],
                "expected": c["values"],
                "operation": list(OPS),
                "evidence": c["sources"],
                "regression": list(CRITERIA),
                "explanation": list(REASONS),
            }
            fields[str(i)] = {
                "type": "object",
                "properties": {k: {"enum": values} for k, values in choices.items()},
                "required": list(choices),
                "additionalProperties": False,
            }
        return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}
    # Eight typed menu indexes form a compact wire encoding. The published
    # opinion expands them to named fields and actual business values.
    fields = {
        str(i): {"type": "string", "pattern": f"^[012][01][0-{len(c['values']) - 1}][0-{len(c['values']) - 1}][0-7][01][0-7][0-9]$"}
        for i, c in enumerate(scope)
    }
    return {"type": "object", "additionalProperties": False, "properties": fields, "required": list(fields)}


def prompt(scope, reviewer, group, signals):
    cat = read_catalog()[reviewer]
    intro = (
        "Audit each simulated business fact against its authorized evidence. Each case has subject, rule, "
        "approved and published values. Return one string of eight digits per case, one menu index per field, in this exact order: "
        "verdict (0=flag defect,1=clear,2=uncertain), affected subject, current published value, expected value, "
        "proposed operation, authoritative evidence source, regression criterion, explanation. Indexes begin at zero. "
        "For correct claims use keep and consistent. For a conflict report the actual published value as current. "
        "Consider meaning, expiry, scope and qualifications. Return one response per slot. "
        f"Operations: {list(OPS)}. Regression criteria: {list(CRITERIA)}. Explanations: {list(REASONS)}. "
        f"Role: {cat['expertise']}. Mission: {cat['mission']}."
    )
    if all(c["domain"] == "identity" for c in scope):
        intro = (
            "Review the synthetic account-state policy. Compare the published decision to the authorized decision. "
            "For each case choose flag if it violates the stated policy; clear if the two decisions agree. "
            "Fill the named fields with actual values (current is published, expected is authorized). "
            "Use the relevant source ID, state the concrete operation, regression check and reason. "
            "For a clean case use keep and consistent. "
            f"Role: {cat['expertise']}. Mission: {cat['mission']}."
        )
    if group in ("cross", "arbitration"):
        intro += " Other reviewers' verdicts are advisory. You may flag a new defect or withdraw a bad claim. Make your own decision from the source."
    compact = {
        str(i): [c["subject"], c["policy"], c["authorized"], c["published"], c["subjects"], c["values"], c["sources"], c["authoritative_source"]]
        for i, c in enumerate(scope)
    }
    body = {"columns": ["subject", "rule", "authorized", "published", "subject_menu", "value_menu", "source_menu", "approved_source"], "cases": compact}
    if signals:
        body["peer_signals"] = signals
    return [{"role": "system", "content": intro}, {"role": "user", "content": encoded(body).decode()}]


def peers(records, scope, group):
    if group not in ("arbitration", "cross"):
        return {}
    prior = ("common", "specialist") if group == "cross" else ("common", "specialist", "cross")
    return {
        str(i): [
            [r["group"], r["opinions"][c["unit"]]["status"], r["opinions"][c["unit"]]["operation"], r["opinions"][c["unit"]]["explanation"]]
            for r in records
            if r["group"] in prior and c["unit"] in r["opinions"]
        ]
        for i, c in enumerate(scope)
    }


def parse(raw, scope):
    from jsonschema import Draft202012Validator

    resp = json.loads(raw)
    choice = resp["choices"][0]
    if choice["finish_reason"] != "stop":
        raise ValueError("completion truncated")
    ans = json.loads(choice["message"]["content"])
    Draft202012Validator(shape(scope)).validate(ans)
    if all(c["domain"] == "identity" for c in scope):
        return {c["unit"]: ans[str(i)] for i, c in enumerate(scope)}
    return {c["unit"]: structured(c, list(map(int, ans[str(i)]))) for i, c in enumerate(scope)}


def measurement(ass, receipt, group, opinions):
    return {
        "assignment_id": ass["assignment_id"],
        "attempt_id": receipt["attempt_id"],
        "reviewer_id": ass["reviewer_id"],
        "group": group,
        "phase": ass["phase"],
        "opinions": opinions,
        "input_tokens": receipt["input_tokens"],
        "output_tokens": receipt["output_tokens"],
        "elapsed_ms": round((datetime.fromisoformat(receipt["ended_utc"]) - datetime.fromisoformat(receipt["started_utc"])).total_seconds() * 1000),
    }


def packet(job, rows, seed, records, adapter):
    group = job["assignment_id"].split("-")[1]
    scope = [rows[u] for u in job["obligations"]]
    salt = {"common": 0, "repeat": 8, "specialist": 8, "cross": 16, "arbitration": 24}[group] + int(job["assignment_id"].split("-")[-1])
    body = adapter.payload(prompt(scope, job["reviewer_id"], group, peers(records, scope, group)), shape(scope), seed + salt)
    if all(c["domain"] == "identity" for c in scope):
        body["max_tokens"] = 1000
    return body, scope, group


def seed_run(out, seed, cases, manifest, adapter, signer, assessor, trust):
    p = frozen(cases, seed)
    catalog = read_catalog()
    rows = {c["unit"]: c for c in cases}
    rid = "quality-fixture-" + str(uuid4())
    spec = {
        "type": "run.v1",
        "run_id": rid,
        "repository": "fixture/quality-holdout",
        "pr_number": 1,
        "base_sha": manifest["base_sha"],
        "head_sha": manifest["head_sha"],
        "merge_base": manifest["base_sha"],
        "integration_sha": None,
        "catalog_digest": digest((ROOT / "reviewers.jsonl").read_text(encoding="utf8").encode()),
        "policy_digest": plan_digest(p),
        "source_manifest_digest": digest(encoded(manifest)),
        "dependency_map_digest": digest(encoded(DOMAINS)),
        "implementer_principals": ["fixture-publisher"],
        "mode": "targeted",
        "risk": "medium",
        "budget": {
            "max_concurrency": 1,
            "max_tokens": 88000,
            "max_cost_microusd": 0,
            "deadline_utc": (datetime.now(timezone.utc) + timedelta(minutes=45)).isoformat(),
            "attempt_timeout_seconds": 90,
            "max_retries": 0,
            "max_debate_rounds": 2,
            "paid_approval_id": None,
            "tariff_digest": None,
        },
    }
    j = Journal(out / "journal.sqlite")
    j.start_planned(spec, trust, p, assessor.public_key)
    records = []
    receipts = {}
    sealed = False
    try:
        for n, job in enumerate(p["assignments"]):
            body, scope, group = packet(job, rows, seed, records, adapter)
            if job["phase"] != "blind" and not sealed:
                j.seal(rid)
                sealed = True
            ass = {k: job[k] for k in ("assignment_id", "phase", "reviewer_id", "artifact_kind")}
            ass.update(
                type="assignment.v1",
                run_id=rid,
                base_sha=manifest["base_sha"],
                head_sha=manifest["head_sha"],
                principal="reviewer/" + job["reviewer_id"],
                round=0 if job["phase"] == "blind" else 1,
                topic="synthetic mixed business assertions",
                reason="paired scope and shared source changes",
                context_digest=digest(encoded(body)),
                tool_grant_digest=digest(encoded(job["obligations"])),
                output_contract=catalog[job["reviewer_id"]]["output"]["contract"],
                token_reservation=4000,
                cost_reservation_microusd=0,
            )
            adapter.admit(body)
            attempt = j.reserve(ass, signer.key_id)["attempt_id"]
            j.dispatch(attempt)
            try:
                raw = adapter.complete(body, 90)
                resp = json.loads(raw)
            except Exception:
                j.timeout(attempt)
                raise
            try:
                opinions = parse(raw, scope)
                outcome = "completed"
            except (ValueError, KeyError, TypeError, IndexError, ValidationError) as error:
                opinions = None
                outcome = "failed"
                issue = error
            receipt = j.receipt_template(attempt)
            receipt.update(
                ended_utc=datetime.now(timezone.utc).isoformat(),
                outcome=outcome,
                output_digest=digest(raw),
                usage_known=True,
                input_tokens=resp["usage"]["prompt_tokens"],
                output_tokens=resp["usage"]["completion_tokens"],
                cost_microusd=0,
                provider_request_or_local_execution_id=resp["id"],
            )
            receipt = signer.sign(receipt)
            disposition = j.ingest(receipt, raw)
            if opinions is None:
                raise ValueError("Known usage, inadmissible structured output") from issue
            if disposition != "accepted":
                raise ValueError("adapter result fenced")
            receipts[attempt] = receipt
            records.append(measurement(ass, receipt, group, opinions))
            print(seed, n + 1, group, resp["usage"]["prompt_tokens"], resp["usage"]["completion_tokens"], flush=True)
        # Only the external deterministic verifier assesses evidence sufficiency.
        # Assignment receipts attest model execution, even if answers are wrong.
        for row in records:
            if row["group"] != "arbitration":
                continue
            for uid, op in row["opinions"].items():
                grounded = op["evidence"] == rows[uid]["authoritative_source"] and op["affected_subject"] == rows[uid]["subject"]
                known = deterministic(rows[uid])
                verified = grounded and known is not None and op["status"] == ("flag" if known else "clear")
                out_digest = receipts[row["attempt_id"]]["output_digest"]
                j.record_evidence(
                    assessor.attest(
                        rid, plan_digest(p), row["assignment_id"], uid, out_digest, digest(encoded(rows[uid])), "verified" if verified else "insufficient"
                    )
                )
        artifact = {"run": spec, "plan": p, "events": j.export_events(rid), "checkpoint": j.checkpoint(rid), "coverage": j.coverage_report(rid)}
        (out / f"seed-{seed}.json.gz").write_bytes(gzip.compress(encoded(artifact), mtime=0))
        return records, artifact["coverage"]
    except Exception:
        j.cancel(rid)
        save(out / f"partial-{seed}.json", {"decision": "inconclusive", "summary": j.summary(rid), "checkpoint": j.checkpoint(rid)})
        raise
    finally:
        j.close()
