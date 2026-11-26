"""Route by the exact immutable workflow identity; leave older adapters executable."""

from . import c3_assets, c3_marketing, c3_order_units, c3_skill_library
from .knowledge_store import conflict

WORKFLOWS = {**c3_marketing.ROLES, **c3_assets.ROLES}

# Task intent v2 has a fixed, reviewed two-role workflow. The Director chooses
# an editorial assignment for each role. Dynamic-plan validation still checks
# the returned plan and its dependency order before it can dispatch work.
DIRECTOR_ASSIGNMENTS = {
    "research": ("Identify the buyer problem and list evidence gaps.", "Compare the approved facts with the buyer hypothesis."),
    "strategy": ("Recommend a channel and define a measurable buyer action.", "Design a bounded test of the positioning and define its metric."),
    "content": ("Write buyer copy with the approved terms and requested action.", "Explain the supported benefit and guide the authorized next step."),
    "seo": ("Describe search intent and draft a relevant title and snippet.", "Align the search title and description with the approved page copy."),
}


def constrain_director_assignments(body, workflow):
    properties = body["response_format"]["json_schema"]["schema"]["properties"]
    for field, role in zip(c3_skill_library.ASSIGNMENTS, c3_assets.ROLES[workflow], strict=True):
        properties[field] = {"type": "string", "enum": list(DIRECTOR_ASSIGNMENTS[role])}
    body["messages"][0]["content"] += " Select one listed assignment per role from the response schema."


def is_current(workflow):
    return workflow in c3_assets.ROLES


def roles(workflow):
    return WORKFLOWS[workflow]


def role_view(workflow, stage, projection):
    if is_current(workflow):
        view = c3_skill_library.role_view(stage, projection)
        intent = projection.get("task_intent", {})
        if stage in ("director", "research", "strategy") and (metric := projection.get("measurement_contract")):
            # Customer copy roles receive buyer-facing inputs only. Internal IDs never become model context.
            view["primary_measurement"] = {k: v for k, v in metric.items() if k not in ("digest", "id")}
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
