"""Check executable release contracts before the publisher writes any definition."""

from . import dynamic_plan, landing_qa
from .registry_adapters import ROLES, output_schema, resolve

FIELDS = {
    "skill_id",
    "skill_version",
    "role_id",
    "contract_version",
    "adapter",
    "adapter_digest",
    "qa_policy",
    "qa_limits",
    "model",
    "inputs",
    "outputs",
    "output_schema",
    "success_criteria",
    "predecessors",
    "tools",
    "approval",
    "node_cap",
    "max_attempts",
    "timeout_seconds",
    "owner",
    "objective",
    "forbidden_actions",
    "fallback",
}


def names(value):
    return isinstance(value, list) and all(isinstance(s, str) for s in value) and len(set(value)) == len(value)


def validate_manifest(manifest):
    try:
        check_workflow(manifest)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Malformed registry contract") from exc


def check_workflow(manifest):
    contracts = manifest["contracts"]
    required = manifest["required"]
    if (
        not names(required)
        or set(required) != {"director", "content", "seo"}
        or not set(required) <= contracts.keys()
        or manifest["mode"] != "dynamic-v1"
        or manifest["workflow_id"] != "WF-13/landing-seo-draft"
        or type(manifest["workflow_version"]) is not int
        or manifest["workflow_version"] < 1
    ):
        raise ValueError("Unsupported workflow contract")

    for skill, contract in contracts.items():
        adapter = resolve(contract)
        if (
            not adapter
            or adapter.skill != skill
            or contract["skill_id"] != skill
            or contract["role_id"] != ROLES[skill]
            or any(type(contract[k]) is not int or contract[k] != adapter.version for k in ("skill_version", "contract_version"))
            or contract["qa_policy"] != landing_qa.ROLE_POLICY.get(contract["adapter"], skill + "@1")
            or not landing_qa.valid_limits(contract)
        ):
            raise ValueError(f"Unsupported adapter, role or skill version for {skill}")
        schema = output_schema(adapter)
        outputs = contract["outputs"]
        if not names(outputs) or set(outputs) != set(schema["properties"]) or contract.get("output_schema", schema) != schema:
            raise ValueError(f"Incompatible output schema for {skill}")
        parents = contract["predecessors"]
        if not names(parents) or not set(parents) <= dynamic_plan.PARENTS.get(skill, set()) & contracts.keys():
            raise ValueError(f"Incompatible predecessors for {skill}")
        if skill == "strategy" and "research" not in parents:
            raise ValueError("Strategy requires a Research predecessor")
        if (
            set(contract) - FIELDS
            or contract["inputs"] != ["brief", "brand", "sources"]
            or contract["tools"] != []
            or contract["model"] != "local"
            or type(contract["node_cap"]) is not int
            or contract["node_cap"] < 0
            or contract["max_attempts"] != 3
            or contract["timeout_seconds"] != 300
            or contract["approval"] != "revision_qa_and_client_snapshot"
        ):
            raise ValueError(f"Unsupported execution contract for {skill}")

    # The first supported workflow always needs these two outputs. Compile a
    # witness using only mandatory grants, before optional skills can be enabled.
    witness = {
        "nodes": [
            {"key": "page", "skill_type": "content", "parents": [], "assignment": "Write the sourced landing page draft."},
            {"key": "meta", "skill_type": "seo", "parents": ["page"], "assignment": "Write SEO metadata for this landing page."},
        ]
    }
    try:
        dynamic_plan.compile_plan(witness, ["content", "seo"], {"skills": required, "contracts": contracts})
    except dynamic_plan.InvalidPlan as exc:
        raise ValueError("Workflow cannot produce its required DAG: " + exc.reason) from exc
