"""Role findings are prompts for the human reviewing this draft revision."""

import re

from .workforce_evidence import normalize


def assess_role(skill, output, sources, contract):
    sections = output["sections"]
    cited = [sources[k]["excerpt"] for k in output["source_ids"]]
    findings = []

    def flag(field, rule):
        findings.append({"field": field, "rule": rule, "claim": sections[field], "source_ids": output["source_ids"]})

    if skill == "research":
        if not any(normalize(sections["observed_fact"]) in normalize(s) for s in cited):
            flag("observed_fact", "verify_observed_fact")
    elif skill == "strategy":
        if not re.search(r"%|\d|rate|ratio|count|per |tỷ lệ|số lượng|phần trăm", sections["success_metric"], re.I):
            flag("success_metric", "specify_measurement_unit")
    elif skill == "content":
        if normalize(sections["call_to_action"]) in {normalize(sections["headline"]), normalize(sections["body_copy"])}:
            flag("call_to_action", "clarify_action")
    elif skill == "seo":
        if normalize(sections["meta_description"]) == normalize(sections["page_title"]):
            flag("meta_description", "differentiate_description")
        for field, value in sections.items():
            if re.search(r"search volume|lượt tìm kiếm", value, re.I) and not any(normalize(value) in normalize(s) for s in cited):
                flag(field, "verify_search_volume")
    return {"policy": contract["qa_policy"], "findings": findings}
