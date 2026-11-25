"""Reproduce both C3 catalog manifests without publishing or approving the runtime."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import c3_marketing as c3  # noqa: E402
from app.registry_adapters import Adapter, ROLES, c3_digest, output_schema  # noqa: E402


def manifest(workflow):
    roles = c3.ROLES[workflow]
    contracts = {}
    for skill in ("director", *roles):
        version = c3.VERSIONS[skill]
        adapter = Adapter(skill, version, c3_digest(), c3.request, c3.validate)
        schema = output_schema(adapter)
        contracts[skill] = {"skill_id":skill, "skill_version":version, "role_id":ROLES[skill],
            "contract_version":version, "adapter":f"{skill}@{version}", "adapter_digest":adapter.digest,
            "qa_policy":f"c3-{skill}@1", "model":"local", "inputs":["brief","brand","sources"],
            "outputs":schema["required"], "output_schema":schema, "success_criteria":schema["required"],
            "predecessors":[roles[0]] if skill == roles[1] else [], "tools":[], "approval":"revision_qa_and_client_snapshot",
            "node_cap":1000, "max_attempts":3, "timeout_seconds":300, "owner":"agency marketing lead",
            "objective":"Use this role's approved knowledge projection to prepare internal Marketing work",
            "forbidden_actions":["external_write","publish","spend"], "fallback":"agency editor"}
    id_, version = workflow.rsplit("@", 1)
    return {"workflow_id":id_, "workflow_version":int(version), "mode":"dynamic-v1",
            "profile":"research-strategy" if workflow == c3.RESEARCH else "landing-seo",
            "required":["director",*roles], "required_outputs":["strategy"] if workflow == c3.RESEARCH else list(roles),
            "knowledge_projection":"amc.marketing-manifest/1", "contracts":contracts}


if __name__ == "__main__":
    for name, workflow in (("research-strategy-v2", c3.RESEARCH), ("landing-seo-v5", c3.LANDING)):
        (ROOT/"catalog"/(name+".json")).write_text(json.dumps(manifest(workflow),indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
