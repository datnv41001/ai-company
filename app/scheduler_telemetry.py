"""Advertise this process's verified capabilities and interpret a single read-only PG snapshot."""

import json
from types import SimpleNamespace
from sqlalchemy import text
from migrations.runtime_bundle import runtime_fingerprint, APPROVAL
from .registry_adapters import runtimes, resolve, specialist_request
from . import dynamic_plan
from .workforce_gateway import Gateway, reserve_tokens, PROMPT_VERSION


def capabilities(config):
    return {
        "fingerprint": runtime_fingerprint(),
        "adapters": {name: a.digest for name, a in runtimes().items()},
        "provider": config.provider,
        "model": config.model,
        "timeout": config.timeout,
        "input_rate": config.input_rate,
        "output_rate": config.output_rate,
    }


def dispatcher_heartbeat(db, config):
    db.execute(text("select amc_ops.heartbeat('dispatcher',cast(:caps as jsonb))"), {"caps": json.dumps(capabilities(config))})


def worker_heartbeat(conn, config):
    conn.execute("select amc_ops.heartbeat('worker',%s::jsonb)", (json.dumps(capabilities(config)),))


def estimate(run, node, parents, caps):
    config = Gateway(caps["provider"], caps["model"], "", caps["input_rate"], caps["output_rate"], caps["timeout"])
    if node.template == "dynamic-v1" and node.skill == "director":
        body = dynamic_plan.planner_body(run, config.model)
    else:
        earlier = {p["id"]: p["checkpoint"]["output"]["text"][:1400] for p in parents if p["id"] != "director"}
        assignment = node.assignment or ""
        if node.template != "dynamic-v1" and node.id != "director":
            assignment = run.checkpoints[0]["output"]["assignments"][node.id]
        body = specialist_request(run, config.model, node=node, predecessors=earlier, assignment=assignment)
    return config.price(reserve_tokens(body), body["max_tokens"])


def compatible(caps, contract, reporting, approved):
    if not caps or caps.get("fingerprint") not in approved:
        return False
    if contract is None:
        return True
    digest = contract["adapter_digest"]
    if digest not in approved[caps["fingerprint"]]["adapters"] or caps.get("adapters", {}).get(contract["adapter"]) != digest:
        return False
    return reporting or (caps.get("provider") == contract["model"] and caps.get("timeout", 9999) <= contract["timeout_seconds"])


def inspect_waits(snapshot):
    run = SimpleNamespace(**snapshot)
    contracts = run.knowledge.get("registry", {}).get("contracts", {})
    replicas = snapshot["dispatchers"] or []
    approved = json.loads(APPROVAL.read_text(encoding="utf-8"))["fingerprints"]
    # A registered login with no fresh observation, or an unreviewed build, leaves fleet coverage unknown.
    coverage = bool(replicas) and all(c and c.get("fingerprint") in approved for c in replicas)
    rows = []
    for raw in run.nodes:
        reasons = []
        routes = raw["routes"] or []
        row = {"node_id": raw["node_id"], "revision": raw["revision"], "candidate": raw["candidate"], "wait_reasons": reasons}
        rows.append(row)
        if raw["checkpoint"] or run.state not in ("queued", "running"):
            continue
        parents = raw["parents"] or []
        if any(not p["checkpoint"] for p in parents):
            reasons.append("dependency_pending")
        if raw["slot"] is None:
            continue
        node = SimpleNamespace(
            id=raw["node_id"],
            skill=raw["skill_type"] or raw["node_id"],
            template=raw["template"],
            assignment=raw["assignment"],
            attempts=raw["attempts"],
            last_error=raw["last_error"],
        )
        contract = contracts.get(node.skill)
        active = raw["active"] or []
        reporting = any(a["status"] == "reported" and a["live"] for a in active)
        if active and not reporting:
            row["phase"] = "lease_active" if any(a["live"] for a in active) else "awaiting_reconciliation"
            continue
        row["phase"] = "report" if reporting else "admission"
        peers = [c for c in replicas if compatible(c, contract, reporting, approved)]
        if not peers:
            reasons.append(("report_waiting_adapter" if reporting else "adapter_unavailable") if coverage else "telemetry_unknown")
        if not coverage and "telemetry_unknown" not in reasons:
            reasons.append("telemetry_unknown")
        if reporting:
            continue
        allowed = [r for r in routes if r["operator_ok"]]
        if not allowed or not any(r["polling"] or not r["worker_free"] for r in allowed):
            reasons.append("worker_unavailable")
        elif not any(r["worker_free"] and r["polling"] for r in allowed):
            reasons.append("worker_busy")
        if any(r["polling"] and not r["worker_known"] for r in allowed) and "telemetry_unknown" not in reasons:
            reasons.append("telemetry_unknown")
        if routes and not routes[0]["enabled"]:
            reasons.append("agency_disabled")
        if routes and not routes[0]["capacity_free"]:
            reasons.append("capacity_full")
        if routes and not routes[0]["run_free"]:
            reasons.append("run_slot_busy")
        if routes and not routes[0]["due"] and run.state == "queued":
            reasons.append("retry_backoff")
            row["retry_at"] = raw["ready_at"] if raw["multi"] else run.run_ready_at
        if "dependency_pending" in reasons:
            continue
        if node.attempts >= 3 or run.knowledge.get("prompt_version") != PROMPT_VERSION:
            reasons.append("attempt_limit" if node.attempts >= 3 else "prompt_version")
            continue
        # Different active releases can build different envelopes. Price only a locally
        # reproducible build; an unseen or unpriced dispatcher might still admit this node.
        local_build = runtime_fingerprint()
        if peers and coverage and all(c["fingerprint"] == local_build for c in peers) and (not contract or resolve(contract)):
            holds = [estimate(run, node, parents, c) for c in peers]
            headroom = [run.run_budget, run.agency_budget if run.agency_budget is not None else -1]
            if contract:
                headroom.append(contract["node_cap"] - raw["exposure"])
            if min(holds) > min(headroom):
                reasons.append("budget_insufficient")
        elif peers and "telemetry_unknown" not in reasons:
            reasons.append("telemetry_unknown")
    return {"observed_at": run.observed_at, "nodes": rows}
