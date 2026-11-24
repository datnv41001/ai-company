import copy

import pytest

from app.dynamic_plan import compile_plan, InvalidPlan


def node(key, skill, parents=()):
    return {"key": key, "skill_type": skill, "assignment": "Draft a sourced notebook campaign asset for " + key, "parents": list(parents)}


def test_canonical_identity_and_repeat_skill():
    nodes = [node("facts", "research"), node("email", "content"), node("page", "content", ["facts"])]
    plan, digest = compile_plan({"nodes": nodes}, ["content"])
    assert (plan, digest) == compile_plan({"nodes": list(reversed(nodes))}, ["content"])
    copies = [n for n in plan["nodes"] if n["skill_type"] == "content"]
    assert len({n["node_id"] for n in copies}) == 2
    assert copies[0]["parents"] != copies[1]["parents"]
    changed = copy.deepcopy(nodes)
    changed[0]["assignment"] += " again"
    assert compile_plan({"nodes": changed}, ["content"])[1] != digest


@pytest.mark.parametrize(
    "nodes",
    [
        [],
        [node("a", "content"), node("a", "content")],
        [node("a", "seo", ["b"]), node("b", "content", ["a"])],
        [node("facts", "research"), node("a", "content")],
        [node("a", "content", ["missing"])],
        [node("a", "strategy"), node("b", "content", ["a"])],
        [node("a", "unregistered")],
        [{**node("a", "content"), "tenant": "other"}],
        [node("a", "research"), node("b", "content", ["a", "a"])],
    ],
)
def test_reject_invalid(nodes):
    with pytest.raises(InvalidPlan):
        compile_plan({"nodes": nodes}, ["content"])


def test_required_outputs_and_closed_envelope():
    with pytest.raises(InvalidPlan):
        compile_plan({"nodes": [node("a", "content")]}, ["content", "seo"])
    with pytest.raises(InvalidPlan):
        compile_plan({"nodes": [node("a", "content")], "budget": 0}, ["content"])
