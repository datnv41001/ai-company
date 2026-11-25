"""Check executable release contracts before the publisher writes any definition."""

from . import c3_marketing, dynamic_plan, landing_qa
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


def required_outputs(manifest):
    return manifest.get("required_outputs", sorted(set(manifest["required"]) - {"director"}))


def validate_manifest(manifest):
    try:
        check_workflow(manifest)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Malformed registry contract") from exc


def check_workflow(manifest):
    contracts = manifest["contracts"]
    required = manifest["required"]
    profile = manifest.get("profile", "landing-seo")
    profiles = {"landing-seo": ("WF-13/landing-seo-draft", ["content","seo"], ["content","seo"]),
                "research-strategy": ("WF-03/research-strategy-draft", ["research","strategy"], ["strategy"])}
    workflow = f"{manifest['workflow_id']}@{manifest['workflow_version']}"
    backed = workflow in c3_marketing.ROLES
    if (manifest.get("knowledge_projection") == "amc.marketing-manifest/1") != backed or profile not in profiles:
        raise ValueError("Unknown executable workflow profile")
    identity, stages, outputs = profiles[profile]
    if (
        not names(required)
        or set(required) != {"director", *stages} or required_outputs(manifest) != outputs
        or not set(required) <= contracts.keys()
        or manifest["mode"] != "dynamic-v1"
        or manifest["workflow_id"] != identity
        or type(manifest["workflow_version"]) is not int
        or manifest["workflow_version"] < 1
    ):
        raise ValueError("Unsupported workflow contract")

    for skill, contract in contracts.items():
        if backed and (skill not in required or contract["adapter"] != f"{skill}@{c3_marketing.VERSIONS[skill]}"):
            raise ValueError("Unsupported knowledge projection adapter")
        if not backed and profile == "research-strategy" and (skill not in required or contract["adapter"] != skill+"@2"):
            raise ValueError("Unsupported research strategy adapter")
        if not backed and profile == "landing-seo" and skill in ("director","research","strategy") and contract["adapter"] != skill+"@1":
            raise ValueError("Unsupported landing adapter")
        adapter = resolve(contract)
        if (
            not adapter
            or adapter.skill != skill
            or contract["skill_id"] != skill
            or contract["role_id"] != ROLES[skill]
            or any(type(contract[k]) is not int or contract[k] != adapter.version for k in ("skill_version", "contract_version"))
            or contract["qa_policy"] != ("c3-" + skill + "@1" if backed else skill+"-wf03@1" if profile == "research-strategy" else landing_qa.ROLE_POLICY.get(contract["adapter"], skill + "@1"))
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

    first, second = stages
    witness = {"nodes": [
        {"key":"first","skill_type":first,"parents":[],"assignment":"Produce the primary evidence for the brief."},
        {"key":"next","skill_type":second,"parents":["first"],"assignment":"Prepare the requested output using the primary evidence."},
    ]}
    try:
        dynamic_plan.compile_plan(witness, required_outputs(manifest), {"skills":required, "contracts":contracts})
    except dynamic_plan.InvalidPlan as exc:
        raise ValueError("Workflow cannot produce its required DAG: " + exc.reason) from exc
