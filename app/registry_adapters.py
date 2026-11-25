"""Trusted, versioned adapters shipped in this build. Manifests cannot load code."""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from migrations.registry_release import adapter_digest
from migrations.runtime_bundle import approved_adapter_digests
from . import dynamic_plan, landing_qa, research_strategy, registry_seo_v2, workforce_gateway as gateway
from . import c3_marketing, c3_skill_library

V1_DIGEST = "c64cf3e0e691a1bad191b954b07d06a28c7cd8675bb5fe8328ee0ae0e620880a"
ROLES = {
    "director": "ai-managing-director",
    "research": "ai-market-researcher",
    "strategy": "ai-marketing-strategist",
    "content": "ai-copywriter-content-strategist",
    "seo": "ai-seo-geo-specialist",
}


@lru_cache(maxsize=1)
def seo_v2_digest():
    extension = Path(registry_seo_v2.__file__).read_text(encoding="utf-8")
    return sha256((adapter_digest() + "\n" + extension).encode()).hexdigest()


@lru_cache(maxsize=2)
def role_qa_digest(skill):
    previous = {"content": V1_DIGEST, "seo": seo_v2_digest()}[skill]
    rules = Path(landing_qa.__file__).read_text(encoding="utf-8")
    return sha256((skill + "\n" + previous + "\n" + rules).encode()).hexdigest()


@lru_cache(maxsize=1)
def research_digest():
    return sha256((V1_DIGEST + "\n" + Path(research_strategy.__file__).read_text(encoding="utf-8")).encode()).hexdigest()


@lru_cache(maxsize=1)
def c3_digest():
    return sha256(Path(c3_marketing.__file__).read_text(encoding="utf-8").encode()).hexdigest()


@dataclass(frozen=True)
class Adapter:
    skill: str
    version: int
    digest: str
    request: Callable
    validate: Callable


@lru_cache(maxsize=1)
def runtimes():
    # Never assign a new meaning to the @1 names when deploying a changed binary.
    approved = approved_adapter_digests()
    if not approved or adapter_digest() != V1_DIGEST:
        return {}
    adapters = {s + "@1": Adapter(s, 1, V1_DIGEST, gateway.request_body, gateway.validate_output) for s in ROLES}
    adapters["seo@2"] = Adapter("seo", 2, seo_v2_digest(), registry_seo_v2.request, registry_seo_v2.validate)
    adapters["content@2"] = Adapter("content", 2, role_qa_digest("content"), gateway.request_body, landing_qa.validate)
    adapters["seo@3"] = Adapter("seo", 3, role_qa_digest("seo"), registry_seo_v2.request, landing_qa.validate)
    for skill in ("director","research","strategy"):
        adapters[skill+"@2"] = Adapter(skill,2,research_digest(),research_strategy.request,research_strategy.validate)
    for skill, version in c3_marketing.VERSIONS.items():
        adapters[f"{skill}@{version}"] = Adapter(skill, version, c3_digest(), c3_marketing.request, c3_marketing.validate)
    for skill, version in c3_skill_library.VERSIONS.items():
        adapters[f"{skill}@{version}"] = Adapter(skill, version, c3_skill_library.adapter_digest(skill), c3_skill_library.request, c3_skill_library.validate)
    return {name: adapter for name, adapter in adapters.items() if adapter.digest in approved}


def resolve(contract):
    runtime = runtimes().get(contract["adapter"])
    if runtime and runtime.digest == contract["adapter_digest"]:
        return runtime
    return None


def specialist_request(run, model, *, node, **kwargs):
    binding = run.knowledge.get("registry")
    builder = resolve(binding["contracts"][node.skill]).request if binding else gateway.request_body
    body = builder(run, model, node=node, **kwargs)
    projection = run.knowledge.get("c3_projection", {})
    if builder == c3_skill_library.request and "buyer_action" in projection.get("task_intent", {}):
        from .c3_releases import role_view
        # The v2 task envelope admits controlled editorial fields on the reviewed runtime.
        # Never forward the free-text task or planner messages to a buyer-facing role.
        message = body["messages"][-1]
        context = json.loads(message["content"])
        context["reference"] = role_view(binding["workflow"], node.skill, projection)
        message["content"] = json.dumps(context, ensure_ascii=False)
    return body


def node_request(run, model, *, node, predecessors, assignment):
    """Build the same pinned envelope for queue admission and read-only cost estimates."""
    if node.template == "dynamic-v1" and node.skill == "director":
        registry = run.knowledge.get("registry")
        if not registry or registry["contracts"]["director"]["adapter"] == "director@1":
            return dynamic_plan.planner_body(run, model)
        return specialist_request(run, model, node=node)
    return specialist_request(run, model, node=node, predecessors=predecessors, assignment=assignment)


def validate_output(raw, stage, plan, sources, binding=None):
    validator = resolve(binding["contracts"][stage]).validate if binding else gateway.validate_output
    return validator(raw, stage, plan, sources, binding)


def structural_schema(schema):
    """Static field types, including array items and nested planner tasks. Enum values depend on the brief."""
    result = {"type": schema["type"]}
    if schema["type"] == "object":
        result.update(
            required=sorted(schema["required"]),
            additionalProperties=schema["additionalProperties"],
            properties={k: structural_schema(v) for k, v in schema["properties"].items()},
        )
    elif schema["type"] == "array":
        result["items"] = structural_schema(schema["items"])
    return result


@lru_cache(maxsize=None)
def output_schema(adapter):
    # Inspect the same request builder used to form a real worker envelope.
    run = SimpleNamespace(knowledge={"sources": {"brand": {"excerpt": "fact"}}, "required_outputs": ["content", "seo"]}, checkpoints=[], plan=[], journal=[])
    if adapter.skill == "director" and adapter.version == 1:
        body = dynamic_plan.planner_body(run, "local")
    else:
        node = SimpleNamespace(skill=adapter.skill, attempts=0, last_error=None)
        body = adapter.request(run, "local", node=node, assignment="", predecessors={})
    return structural_schema(body["response_format"]["json_schema"]["schema"])
