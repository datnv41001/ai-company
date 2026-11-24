"""Version 2 triage of original, validated Content and SEO outputs using frozen run inputs."""

import re

from sqlalchemy import text

from migrations.runtime_bundle import canonical_hash
from . import workforce_gateway as gateway
from .workforce_evidence import RULES, normalize


# Informational checks use lexical anchors. Generic marketing terms carry little
# evidence of alignment with a specific product, brief or predecessor.
STOP = set(
    "the and for with from this that your you can page shop buy offer explore read visit product best with our "
    "write landing metadata matching about find see class of in to a is an by or at on for more learn "
    "và của cho một với sản phẩm các này những xem thêm tìm hiểu trang".split()
)
ACTION = re.compile(
    r"^(?:(?:please|now|hãy|vui lòng)\s+)?(?:explore|read|visit|shop|buy|book|try|compare|order|discover|choose|browse|download|contact|join|register|sign up|learn|see|start|get|view|xem|mua|đặt|chọn|khám phá|tìm hiểu|đọc|đăng ký|liên hệ|tải|thử)\b",
    re.I,
)
MEASURABLE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?(?:\s*%|\b)|search volume|lượt tìm kiếm", re.I)
PROHIBITION = re.compile(r"(?:^|[.;\n])\s*(?:avoid|do not use|không dùng|tránh)\s*:?\s*([^.;\n]+)", re.I)
ROLE_POLICY = {"content@2": "content-qa@2", "seo@3": "seo-qa@2"}


def terms(value):
    return {w.removesuffix("s") if w.isascii() and len(w) > 4 else w for w in re.findall(r"[^\W_]+", normalize(value)) if len(w) > 1 and w not in STOP}


def validate(raw, stage, plan, sources, binding):
    # Validate exact keys before calling the original typed field and scoped-source checks.
    if not isinstance(raw, dict) or set(raw) != {*gateway.SECTIONS[stage], "source_ids"}:
        raise gateway.GatewayError("invalid_contract_output")
    return gateway.validate_output(raw, stage, plan, sources)


def valid_limits(contract):
    limits = contract.get("qa_limits")
    if contract["qa_policy"] != "seo-qa@2":
        return "qa_limits" not in contract
    return (
        isinstance(limits, dict)
        and set(limits) == {"page_title", "meta_description"}
        and all(isinstance(pair, list) and len(pair) == 2 and all(type(n) is int for n in pair) and 1 <= pair[0] <= pair[1] <= 900 for pair in limits.values())
    )


def claim_findings(sections, citations, flag):
    quotes = {}
    for key, excerpt in citations.items():
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", excerpt):
            quotes.setdefault(normalize(sentence), []).append(key)
    for field, value in sections.items():
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", value):
            if MEASURABLE.search(sentence) or any(pattern.search(sentence) for pattern in RULES.values()):
                matching = sorted(set(quotes.get(normalize(sentence), [])))
                flag(
                    field,
                    "quote_context" if matching else "claim_evidence",
                    {"claim": sentence, "matching_ids": matching},
                    severity="info" if matching else "warning",
                )


def content_findings(sections, knowledge, flag):
    headline, copy, cta = (sections[k] for k in ("headline", "body_copy", "call_to_action"))
    if normalize(cta) in {normalize(headline), normalize(copy)} or not ACTION.match(normalize(cta)):
        flag("call_to_action", "cta_action", {"text": cta})
    anchors = terms(headline + " " + copy)
    for rule, values in (
        ("brief_alignment", [knowledge[k] for k in ("objective", "audience", "offer")]),
        ("brand_alignment", [knowledge["sources"]["brand"]["excerpt"]]),
    ):
        targets = terms(" ".join(values))
        if targets and not anchors.intersection(targets):
            flag("body_copy", rule, {"text": copy, "reference": values})
    # Check narrower brief dimensions even if a generic product word matches.
    # An omission prompts a reviewer to decide whether the audience must be explicit.
    for field, rule in (("audience", "audience_alignment"), ("offer", "offer_alignment")):
        reference = knowledge[field]
        expected = terms(reference)
        if expected and not anchors.intersection(expected):
            flag("body_copy", rule, {"text": copy, "reference": reference}, severity="info")
    for forbidden in PROHIBITION.findall(knowledge["brand_rules"]):
        for phrase in forbidden.split(","):
            phrase = normalize(phrase).strip("\"'“” ")
            for field, value in sections.items():
                if phrase and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalize(value)):
                    flag(field, "brand_instruction", {"text": value, "avoid": phrase})


def seo_findings(sections, limits, parents, flag):
    # Only actual Content parent edges from the same frozen plan are in this map.
    anchors = set()
    for parent in parents.values():
        anchors.update(terms(parent["sections"]["headline"] + " " + parent["sections"]["body_copy"]))
    for field, value in sections.items():
        if not anchors or not terms(value).intersection(anchors):
            flag(field, "intent_alignment" if field == "search_intent" else "page_alignment", {"text": value, "content_parents": list(parents)})
        if field in limits:
            low, high = limits[field]
            if not low <= len(value) <= high:
                flag(field, "metadata_length", {"length": len(value), "range": [low, high]}, severity="info")
    if normalize(sections["page_title"]) == normalize(sections["meta_description"]):
        flag("meta_description", "duplicate_metadata", {"text": sections["meta_description"]})


def evaluate_node(db, run, node, output):
    knowledge = run.knowledge
    binding = knowledge["registry"]
    contract = binding["contracts"][node.skill]
    citations = {key: knowledge["sources"][key]["excerpt"] for key in output["source_ids"]}
    findings = []

    def flag(field, rule, evidence, severity="warning"):
        findings.append(
            {
                "rule_id": rule,
                "rule_version": 2,
                "severity": severity,
                "node_id": node.id,
                "field": field,
                "evidence": evidence,
                "source_ids": list(citations),
                "status": "needs_review",
            }
        )

    sections = output["sections"]
    parents = {}
    if node.skill == "content":
        content_findings(sections, knowledge, flag)
    else:
        rows = db.execute(
            text("""
            SELECT p.node_id, p.checkpoint->'output' FROM amc_ops.dag_edges e JOIN amc_ops.dag_nodes p
              ON (p.run,p.revision,p.node_id)=(e.run,e.revision,e.parent)
             WHERE e.run=:run AND e.revision=:rev AND e.child=:child AND p.skill_type='content'
             ORDER BY p.position
        """),
            {"run": run.id, "rev": node.revision, "child": node.id},
        )
        parents = {pid: original for pid, original in rows}
        seo_findings(sections, contract["qa_limits"], parents, flag)
    claim_findings(sections, citations, flag)
    return {
        "scope": "node_checkpoint",
        "policy": contract["qa_policy"],
        "role_id": contract["role_id"],
        "contract_version": contract["contract_version"],
        "contract_digest": canonical_hash(contract),
        "run_id": run.id,
        "node_id": node.id,
        "plan_revision": node.revision,
        "plan_digest": run.checkpoints[0]["output"]["plan_digest"],
        "manifest_digest": binding["manifest_digest"],
        "output_digest": canonical_hash(output),
        "source_ids": list(citations),
        "content_parents": {key: canonical_hash(value) for key, value in parents.items()},
        "findings": findings,
    }
