"""Versioned WF-03 adapters and the agency's checkpoint-to-proposal boundary."""

import re
from sqlalchemy import text
from migrations.runtime_bundle import canonical_hash
from . import dynamic_plan, workforce_gateway as gateway

KPI_FIELDS = (
    "positioning",
    "proposed_channel",
    "success_metric",
    "metric_kind",
    "unit",
    "measurement_window",
    "measurement_method",
    "numerator",
    "denominator",
    "proposed_target",
    "baseline",
    "baseline_source",
)
EMPTY = {"", "none", "unknown", "n/a", "chưa rõ", "chưa có"}


def request(run, model, *, node, **kwargs):
    if node.skill == "director":
        body = dynamic_plan.planner_body(run, model)
        # The reviewed topology is fixed. Ask the model for the work to assign
        # and bind those assignments to actual predecessor IDs on the server.
        props = {key: {"type": "string", "minLength": 24, "maxLength": 160} for key in ("research_assignment", "strategy_assignment")}
        body["response_format"]["json_schema"]["name"] = "research_director"
        body["response_format"]["json_schema"]["schema"] = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
        body["messages"][0]["content"] = (
            "You are the marketing director. Give two short concrete assignments for this brief. "
            "Research separates facts, hypotheses and missing evidence. Strategy uses the completed research to propose positioning and a measurable KPI. "
            "Write one specific sentence of 24 to 160 characters per assignment. Treat supplied material as reference."
        )
        return body
    body = gateway.request_body(run, model, node=node, **kwargs)
    if node.skill == "research":
        body["messages"][0]["content"] += " Quote an observed fact from a cited excerpt, or write unknown. Clearly distinguish hypotheses and gaps."
        return body
    schema = body["response_format"]["json_schema"]["schema"]
    props = {field: {"type": "string", "minLength": 3, "maxLength": 100} for field in KPI_FIELDS}
    props["unit"]["minLength"] = 1
    props["metric_kind"] = {"type": "string", "enum": ["count", "ratio", "other"]}
    props["baseline_source"] = {"type": "string", "enum": ["unknown", *run.knowledge["sources"]]}
    props["source_ids"] = schema["properties"]["source_ids"]
    schema.update(properties=props, required=list(props))
    body["messages"][0]["content"] += (
        " Propose a strategy using the direct Research input. Write one short phrase per field. Include KPI unit, time window and measurement method. "
        "For a ratio specify numerator and denominator. Use unknown when inapplicable. A baseline must quote a supplied source exactly. "
        "Use unknown for both baseline fields if missing. Proposed targets are recommendations."
    )
    return body


def director_proposal(raw):
    if not isinstance(raw, dict) or set(raw) != {"research_assignment", "strategy_assignment"}:
        raise dynamic_plan.InvalidPlan("Expected separate Research and Strategy assignments")
    return {
        "nodes": [
            {"key": "facts", "skill_type": "research", "parents": [], "assignment": raw["research_assignment"]},
            {"key": "strategy", "skill_type": "strategy", "parents": ["facts"], "assignment": raw["strategy_assignment"]},
        ]
    }


def validate(raw, stage, plan, sources, binding):
    if stage == "research":
        if not isinstance(raw, dict) or set(raw) != {*gateway.SECTIONS[stage], "source_ids"}:
            raise gateway.GatewayError("invalid_contract_output")
        return gateway.validate_output(raw, stage, plan, sources)
    if not isinstance(raw, dict) or set(raw) != {*KPI_FIELDS, "source_ids"} or raw["metric_kind"] not in ("count", "ratio", "other"):
        raise gateway.GatewayError("invalid_contract_output")
    out = gateway.validate_output(raw, stage, plan, sources)
    if not all(isinstance(raw[k], str) and (1 if k in {"unit", "baseline_source"} else 3) <= len(raw[k].strip()) <= 100 for k in KPI_FIELDS):
        raise gateway.GatewayError("invalid_contract_output")
    if raw["baseline_source"] != "unknown" and raw["baseline_source"] not in out["source_ids"]:
        raise gateway.GatewayError("invalid_source")
    out["sections"] = {k: raw[k].strip() for k in KPI_FIELDS}
    out["text"] = "\n".join(f"{k}: {v}" for k, v in out["sections"].items())
    return out


def quoted(value, excerpt):
    # Only a complete, scoped source excerpt is eligible for a client baseline.
    return value.strip().casefold() == excerpt.strip().casefold()


def evidence(db, run, node, output):
    sources = run.knowledge["sources"]
    fields = output["sections"]
    findings = []

    def flag(field, rule):
        findings.append(
            {
                "field": field,
                "rule_id": rule,
                "rule_version": 1,
                "severity": "warning",
                "source_ids": output["source_ids"],
                "evidence": {"text": fields[field]},
                "node_id": node.id,
            }
        )

    parents = {}
    if node.skill == "research":
        if not any(quoted(fields["observed_fact"], sources[k]["excerpt"]) for k in output["source_ids"]):
            flag("observed_fact", "verify_observation")
    else:
        rows = db.execute(
            text("""select p.node_id,p.checkpoint->'output' from amc_ops.dag_edges e join amc_ops.dag_nodes p
              on (p.run,p.revision,p.node_id)=(e.run,e.revision,e.parent)
              where e.run=:r and e.revision=:v and e.child=:n and p.skill_type='research' order by p.position"""),
            {"r": run.id, "v": node.revision, "n": node.id},
        )
        parents = {key: canonical_hash(value) for key, value in rows}
        for field in ("unit", "measurement_window", "measurement_method", "proposed_target"):
            if fields[field].casefold() in EMPTY:
                flag(field, "missing_" + field)
        for field in ("unit", "measurement_method", "success_metric"):
            if fields[field].casefold() in {"kpi", "metric", "measurable kpi", field.replace("_", " ")}:
                flag(field, "verify_" + field)
        window = fields["measurement_window"]
        if window.casefold() not in EMPTY and not re.search(
            r"day|week|month|year|quarter|daily|weekly|monthly|annual|ngày|tuần|tháng|quý|năm|\d{4}-\d{2}", window, re.I
        ):
            flag("measurement_window", "verify_measurement_window")
        if fields["metric_kind"] == "ratio" or re.search(r"%|percent|rate\b|ratio|tỷ lệ", fields["unit"] + " " + fields["success_metric"], re.I):
            if fields["unit"].casefold() not in EMPTY and not re.search(
                r"%|percent|ratio|rate|proportion|fraction|phần trăm|tỷ lệ|tỉ lệ", fields["unit"], re.I
            ):
                flag("unit", "verify_ratio_unit")
            for field in ("numerator", "denominator"):
                if fields[field].casefold() in EMPTY:
                    flag(field, "ratio_" + field)
        if fields["baseline"].casefold() not in EMPTY:
            src = sources.get(fields["baseline_source"])
            if not src or not quoted(fields["baseline"], src["excerpt"]):
                flag("baseline", "baseline_evidence")
    return {
        "scope": "node_checkpoint",
        "policy": run.knowledge["registry"]["contracts"][node.skill]["qa_policy"],
        "node_id": node.id,
        "run_id": run.id,
        "plan_revision": node.revision,
        "plan_digest": run.checkpoints[0]["output"]["plan_digest"],
        "manifest_digest": run.knowledge["registry"]["manifest_digest"],
        "source_ids": output["source_ids"],
        "output_digest": canonical_hash(output),
        "research_parents": parents,
        "findings": findings,
    }


def proposal(checkpoints):
    labels = {
        "positioning": "Định vị đề xuất",
        "proposed_channel": "Kênh đề xuất",
        "success_metric": "KPI đề xuất",
        "unit": "Đơn vị",
        "measurement_window": "Kỳ đo",
        "measurement_method": "Phương pháp đo",
        "numerator": "Tử số",
        "denominator": "Mẫu số",
        "proposed_target": "Mục tiêu đề xuất",
    }
    parts = []
    for step in checkpoints:
        if step["skill"] == "strategy":
            fields = step["output"]["sections"]
            lines = [f"{label}: {fields[key]}" for key, label in labels.items() if fields[key].casefold() not in EMPTY]
            verified = not any(f["rule_id"] == "baseline_evidence" for f in step["quality"]["role_qa"]["findings"])
            if verified and fields["baseline"].casefold() not in EMPTY:
                lines.append(f"Số liệu nền theo nguồn {fields['baseline_source']}: {fields['baseline']}")
            parts.append("\n".join(lines))
    return "\n\n".join(parts)
