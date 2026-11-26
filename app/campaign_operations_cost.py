"""Scoped cost coverage for actual attempts. A manual estimate does not certify an invoice."""
import hashlib
import hmac
import os

from .knowledge_store import canonical, conflict, digest


CATEGORIES = {"model", "compute", "tools", "human"}


def token_totals(attempts):
    # An absent meter reading differs from the integer zero reported by a meter.
    inputs = [a["input_tokens"] for a in attempts if a["input_tokens"] is not None]
    outputs = [a["output_tokens"] for a in attempts if a["output_tokens"] is not None]
    fully_metered = sum(a["input_tokens"] is not None and a["output_tokens"] is not None for a in attempts)
    return {"reported_input_attempts":len(inputs), "reported_output_attempts":len(outputs),
            "fully_metered_attempts":fully_metered,"unmeasured_token_attempts":len(attempts)-fully_metered,
            "observed_input_tokens":sum(inputs) if inputs else None,"observed_output_tokens":sum(outputs) if outputs else None}


def inventory(unit):
    attempts = [{k:j.get(k) for k in ("skill","node_id","attempt","model","provider","started_at","finished_at","outcome",
                                      "input_tokens","output_tokens","estimated_microusd")} for j in unit.get("worker_journal", [])]
    missing = []
    if unit["status"] == "requested" or unit.get("run_state") in ("running","queued"):
        missing.append("unfinished_work")
    if unit.get("run_id") and not attempts:
        missing.append("attempt_inventory")
    if any(a["finished_at"] is None or a["input_tokens"] is None or a["output_tokens"] is None for a in attempts):
        missing.append("unmeasured_attempts")
    coverage = {"scope":unit["scope"],"plan":unit["plan_id"],"unit":unit["id"],"status":unit["status"],
                "run":unit.get("run_id"), "queue":unit.get("queue_receipt"), "attempts":attempts, "labor":unit["labor"],
                "artifact_revision":unit.get("artifact_revision"),"artifact_digest":unit.get("artifact_digest"),
                "acceptance":unit.get("acceptance"),"cost_statement":unit.get("cost_statement")}
    return {"digest":digest(canonical(coverage)), "attempts":attempts, "missing":missing, **token_totals(attempts),
            "manual_baseline_seconds":(unit.get("cost_statement") or {}).get("manual_baseline_seconds")}


def verify(cmd, unit, rows):
    observed = inventory(unit)
    if observed["missing"] or observed["digest"] != cmd.inventory_digest:
        conflict("Meter coverage missing or inventory changed")
    lines = [line.model_dump() for line in cmd.lines]
    ids = {line["allocation_id"] for line in lines}
    if {line["category"] for line in lines} != CATEGORIES or len(ids) != 4:
        conflict("Each cost category requires its own measured allocation")
    # Meter allocations are slices of a real invoice or timesheet. Reusing one slice for two groups would double-count a run.
    for row in rows:
        event = row.result
        if event["kind"] == "verify_unit_cost" and event["entity_id"] != unit["id"]:
            if ids.intersection(line["allocation_id"] for line in event["value"]["meter"]["lines"]):
                conflict("An allocation already belongs to another commissioned unit")
    payload = {"contract":"campaign-cost-meter/1","scope":unit["scope"],"plan_id":unit["plan_id"],"unit_id":unit["id"],
               "inventory_digest":observed["digest"],"lines":lines}
    secret = os.getenv("AMC_SANDBOX_COST_METER_KEY","").encode()
    if len(secret) < 32 or not hmac.compare_digest(cmd.signature,hmac.new(secret,canonical(payload).encode(),hashlib.sha256).hexdigest()):
        conflict("A verified cost-meter receipt from the configured accounting authority is required")
    return {**payload,"signature":cmd.signature,"total_vnd":sum(line["amount_vnd"] for line in lines)}


def summarize(units):
    actual_runs = set()
    observations = {}
    complete = bool(units)
    total = 0
    for unit in units:
        coverage = inventory(unit)
        meter = unit.get("meter") or {}
        ok = not coverage["missing"] and meter.get("inventory_digest") == coverage["digest"]
        if not ok:
            coverage["missing"] += sorted(CATEGORIES)
            complete = False
        else:
            total += meter["total_vnd"]
        coverage["verified_vnd"] = meter["total_vnd"] if ok else None
        unit["cost_coverage"] = coverage
        if unit.get("run_id"):
            actual_runs.add(unit["run_id"])
            for a in coverage["attempts"]:
                identity = (unit["run_id"],a["node_id"],a["skill"],a["attempt"],a["started_at"])
                # Several groups can cite the same run. Merge individual readings once; an empty later
                # inventory, including that of a composed sibling, cannot erase observed worker calls.
                readings = observations.setdefault(identity, {"input_tokens":set(),"output_tokens":set()})
                for metric in readings:
                    if a[metric] is not None:
                        readings[metric].add(a[metric])
    attempts = [{k:next(iter(v)) if len(v)==1 else None for k,v in readings.items()} for readings in observations.values()]
    conflicts = sum(any(len(v)>1 for v in readings.values()) for readings in observations.values())
    complete = complete and not conflicts
    accepted = sum((u.get("acceptance") or {}).get("status") == "business_accepted" for u in units)
    return {"cost_status":"all_units_costed" if complete else "unmeasured_complete_production_cost",
            "cost_per_business_accepted_vnd":total / accepted if complete and accepted else None,
            "observed_runs":len(actual_runs),"observed_attempts":len(attempts),"conflicting_token_attempts":conflicts,**token_totals(attempts)}
