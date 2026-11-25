"""Route by the exact immutable workflow identity; leave older adapters executable."""

from . import c3_assets, c3_marketing, c3_order_units, c3_skill_library
from .knowledge_store import conflict

WORKFLOWS = {**c3_marketing.ROLES, **c3_assets.ROLES}


def is_current(workflow):
    return workflow in c3_assets.ROLES


def roles(workflow):
    return WORKFLOWS[workflow]


def role_view(workflow, stage, projection):
    if is_current(workflow):
        view = c3_skill_library.role_view(stage, projection)
        intent = projection.get("task_intent", {})
        if "buyer_action" in intent:
            view["buyer_action"] = intent["buyer_action"]
            view["editorial_style"] = intent["editorial_style"]
            if intent.get("buyer_input"):
                view["buyer_input"] = intent["buyer_input"]
        return view
    return c3_marketing.role_view(stage, projection)


def fact_text(workflow, fact, projection):
    if is_current(workflow):
        return f"[{fact['id']}] " + " ".join(c3_order_units.fact_lines(fact, projection))
    return c3_marketing.fact_line(fact)


def check_capacity(workflow, projection):
    if is_current(workflow):
        try:
            preview = c3_order_units.render(workflow, projection, {})
        except ValueError as exc:
            conflict(str(exc))
        public = c3_assets.normalized(preview["body"])
        if any(phrase in public for phrase in c3_assets.prohibitions(projection)):
            conflict("An exclusion conflicts with an approved public fact, product or region. Revise the selection or request clarification.")
        # Three public text fields can enter the body. The fourth copy field is the title.
        maximum = len(preview["body"]) + 3 * (200 + 2)
    else:
        maximum = len(c3_marketing.render(workflow, projection, {})["body"])
        maximum += sum(sum(len(c3_marketing.LABELS[k]) + 3 + 200 for k in c3_marketing.FIELDS[role]) + 64
                       for role in WORKFLOWS[workflow])
    if maximum > 30_000:
        conflict("Select fewer approved claims so every qualifier fits in one deliverable")
