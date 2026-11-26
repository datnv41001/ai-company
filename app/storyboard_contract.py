"""Exact publisher definition and one-node plan of the native storyboard capability."""

from . import video_storyboard as video
from .knowledge_store import canonical, digest


def release_manifest():
    contracts = {}
    for stage, role, version, field in (
        ("director", "ai-managing-director", video.DIRECTOR_VERSION, "assignment"),
        ("storyboard", video.ROLE, 1, "board_json"),
    ):
        contracts[stage] = dict(
            skill_id=stage,
            skill_version=version,
            role_id=role,
            contract_version=version,
            adapter=f"{stage}@{version}",
            adapter_digest=video.source_digest(),
            qa_policy="wf08-source-and-revision@1",
            model="local",
            inputs=["brief", "brand", "sources"],
            outputs=[field],
            output_schema={"type": "object", "properties": {field: {"type": "string"}}, "required": [field], "additionalProperties": False},
            success_criteria=["pinned scope", "deterministic validation"],
            predecessors=[],
            tools=[],
            approval="independent_internal_revision_qa",
            node_cap=0,
            max_attempts=3,
            timeout_seconds=300,
            owner="agency creative lead",
            objective="Produce a grounded illustrated storyboard for internal editing",
            forbidden_actions=["external_write", "publish", "spend"],
            fallback="agency creative editor",
        )
    return dict(
        workflow_id="WF-08/video-storyboard",
        workflow_version=1,
        mode="dynamic-v1",
        profile="video-storyboard",
        knowledge_projection="amc.marketing-manifest/2",
        required=list(contracts),
        required_outputs=["storyboard"],
        contracts=contracts,
    )


def plan(raw, required, binding):
    video.director_plan(raw)
    if required != ["storyboard"] or binding.get("workflow") != video.RELEASE or set(binding["skills"]) != {"director", "storyboard"}:
        raise video.GatewayError("invalid_storyboard_binding")
    specialist = binding["contracts"]["storyboard"]
    node = dict(
        node_id="n01",
        skill_type="storyboard",
        assignment=video.ASSIGNMENT,
        parents=[],
        binding={k: specialist[k] for k in ("role_id", "contract_version", "skill_id", "skill_version", "qa_policy")},
    )
    frozen = dict(catalog=1, required=required, nodes=[node], join=["n01"], registry={k: v for k, v in binding.items() if k != "contracts"})
    return frozen, digest(canonical(frozen))
