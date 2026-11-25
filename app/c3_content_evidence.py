"""Review exact client-visible spans against a frozen Marketing projection.

Only a complete published declaration can prove a commercial term. Unknown prose goes
to independent domain review; a role-level list of citations is never sentence evidence.
"""

import re
import unicodedata

from . import c3_marketing
from .commercial_scope import TERRITORIES, TERRITORY_BY_LABEL
from .knowledge_store import canonical, digest


VERSION = "amc.content-evidence/1"
HANDLE = re.compile(r"(?<!\w)F[1-9][0-9]*(?!\w)", re.I)
BRACKET = re.compile(r"\[\s*(F[1-9][0-9]*)\s*\]", re.I)
NUMERIC = re.compile(r"\d|[%$€£¥₫₱]")
COMMERCIAL = re.compile(
    r"\b(discount|rebate|sale price|free shipping|vat|tax|moq|prepaid|warranty|giảm giá|khuyến mãi|miễn phí|thuế|bảo hành|chiết khấu|trả trước|tối thiểu|tối đa|giao miễn phí|giá bán|báo giá cố định)\b",
    re.I,
)
TERRITORY = re.compile(
    r"\b(nationwide|worldwide|globally|everywhere|all regions|ships? to|available in|delivery (?:in|to)|toàn quốc|toàn cầu|mọi nơi|mọi tỉnh|cả nước|giao hàng (?:đến|tại)|phục vụ tại|áp dụng tại)\b",
    re.I,
)
CHANNEL = re.compile(r"\b(all channels|mọi kênh|tất cả các kênh|offline|tại cửa hàng|marketplace|trên sàn|in.store.only)\b", re.I)
SEMANTIC = (
    ("comparison", re.compile(r"\b(hơn|nhất|đối thủ|cheaper|than|best|competing|competitors?|superior)\b", re.I)),
    ("regulated", re.compile(r"\b(bác sĩ|chữa|điều trị|cures?|medical|doctor|clinically)\b", re.I)),
    ("performance", re.compile(r"\b(bảo đảm|cam kết|hiệu quả|guarantee\w*|proven|performance)\b", re.I)),
)
SCOPE_FIELDS = {
    "sku": "sku",
    "mã sản phẩm": "sku",
    "product": "product",
    "sản phẩm": "product",
    "variant": "product",
    "biến thể": "product",
    "market": "market",
    "thị trường": "market",
    "region": "region",
    "area": "region",
    "phạm vi": "region",
    "khu vực": "region",
    "channel": "channel",
    "kênh": "channel",
}


def normalized(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split()).strip(" .!?")


def marketing_run(run):
    if run is None:
        return False
    workflow = run.knowledge.get("registry", {}).get("workflow")
    if not workflow:
        return False
    from .c3_releases import WORKFLOWS

    return workflow in WORKFLOWS


def clean_handle(line):
    return normalized(BRACKET.sub("", line))


def content_shapes(workflow, projection):
    """Derive exact public fact blocks and fixed layout from the release-specific renderer."""
    if workflow not in c3_marketing.ROLES:
        from . import c3_assets

        render = c3_assets.render
        blocks = {f["id"]: [" ".join(c3_assets.fact_lines(f, projection))] for f in projection["facts"]}
    else:
        render = c3_marketing.render
        blocks = {f["id"]: [c3_marketing.fact_line(f)] for f in projection["facts"]}
    baseline = render(workflow, projection, {})
    # These are generated from the pinned data with no model replies. Arbitrary text after
    # a label (including an invented citation), or added after a fixed CTA, is not exempted.
    fixed = {normalized(line) for line in baseline["body"].splitlines() if line.strip()}
    for lines in blocks.values():
        fixed.difference_update(normalized(line) for line in lines)
    return blocks, {"title": {normalized(baseline["title"]), normalized(projection["product"])}, "client_preview": fixed}


def spans(value):
    return [(match.start(), match.end(), match.group()) for match in re.finditer(r"[^\s\r\n][^\r\n]*", value)]


def sentences(start, line):
    # Keep decimal/currency punctuation and trailing [F1] with its statement.
    left = 0
    for boundary in re.finditer(r"(?<=[.?!;])\s+(?!\s|\[F\d+\])", line, re.I):
        yield start + left, start + boundary.start(), line[left : boundary.start()]
        left = boundary.end()
    yield start + left, start + len(line), line[left:]


def source_map(facts, blocks, lines):
    """A multi-line price only verifies when all lines and qualifiers occur together."""
    complete = {}
    text = [clean_handle(line) for _, _, line in lines]
    for fact in facts:
        key = fact["id"]
        expected = [clean_handle(line) for line in blocks[key] if line.strip()]
        if not expected:
            continue
        for i, value in enumerate(text):
            if value != expected[0] or text[i : i + len(expected)] != expected:
                continue
            for j in range(i, i + len(expected)):
                cites = {c.upper() for c in HANDLE.findall(lines[j][2])}
                if cites and cites != {key}:
                    break
            else:
                for j in range(i, i + len(expected)):
                    complete.setdefault(j, []).append(key)
    return complete


def classify(line, facts, complete, fixed, projection):
    text = normalized(line)
    bare = clean_handle(line)
    cited = list(dict.fromkeys(h.upper() for h in HANDLE.findall(line)))
    handles = set(f["id"] for f in facts)
    forbidden = [*(projection.get("brand_guidelines") or {}).get("prohibited_claims", []), *(projection.get("task_intent") or {}).get("exclusions", [])]
    if any(normalized(term) and normalized(term) in text for term in forbidden):
        return "prohibited", "contradiction", "prohibited", cited
    if any(h not in handles for h in cited):
        return "citation", "contradiction", "unknown_handle", cited
    if complete and len(complete) > 1:
        return "unclassified", "unresolved", "ambiguous_evidence", complete
    if complete:
        return "fact", "verified", "exact_declaration", complete
    for fact in facts:
        if bare == normalized(fact["wording"]) and not fact.get("price") and not fact.get("applicability"):
            if cited and cited != [fact["id"]]:
                return "citation", "contradiction", "wrong_handle", cited
            if fact.get("qualifiers"):
                return fact["category"], "contradiction", "missing_qualifier", [fact["id"]]
            return fact["category"], "verified", "exact_declaration", [fact["id"]]
    if bare == normalized(projection.get("product", "")) and bare:
        return "product", "verified", "exact_scope", ["PRODUCT"]
    label, sep, value = bare.partition(":")
    if sep and label.strip() in SCOPE_FIELDS:
        key = SCOPE_FIELDS[label.strip()]
        expected = normalized(projection.get(key) or "")
        if value.strip() == expected and expected:
            return key, "verified", "exact_scope", ["PRODUCT" if key in ("sku", "product") else "MARKET"]
        return key, "contradiction", {"region": "geography", "market": "geography", "channel": "channel"}.get(key, "product_identity"), cited
    if text in fixed or re.fullmatch(r"căn cứ tham khảo:\s*f\d+(?:,\s*f\d+)*", text):
        return "editorial", "editorial", "layout_or_pinned_context", []
    region = projection["region"]
    allowed_region = TERRITORY_BY_LABEL.get(region, region)
    foreign = (label for key, labels in TERRITORIES.items() if key != allowed_region for label in (key, *labels))
    if TERRITORY.search(bare) or any(re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", bare, re.I) for label in foreign):
        return "region", "contradiction", "geography", cited
    if CHANNEL.search(bare):
        return "channel", "contradiction", "channel", cited
    if re.search(r"\b(sku|mã sản phẩm|variant|biến thể)\b", bare):
        return "product", "contradiction", "product_identity", cited
    if NUMERIC.search(bare) or COMMERCIAL.search(bare):
        return "structured", "contradiction", "commercial_terms", cited
    for fact in facts:
        if normalized(fact["wording"]) in bare and any(normalized(q) not in bare for q in fact.get("qualifiers", [])):
            return fact["category"], "contradiction", "missing_qualifier", [fact["id"]]
    cat = next((kind for kind, pattern in SEMANTIC if pattern.search(bare)), "unclassified")
    return cat, "unresolved", "unsupported", cited


def assess_document(doc, run, signature):
    from .knowledge_store import conflict

    if not run.knowledge.get("c3_manifest", {}).get("digest") or not run.knowledge.get("c3_projection"):
        conflict("The Marketing run has no pinned content evidence")
    projection = run.knowledge["c3_projection"]
    blocks, fixed = content_shapes(run.knowledge["registry"]["workflow"], projection)
    facts = projection["facts"]
    statements = []
    for field, value in (("title", doc.title), ("client_preview", doc.content.get("client_preview", ""))):
        lines = spans(value)
        complete = source_map(facts, blocks, lines)
        for i, (start, end, line) in enumerate(lines):
            # A canonical fact and its qualifiers form one indivisible assertion. Other novel
            # prose gets individual sentence spans even when multiple claims share a paragraph.
            pieces = [(start, end, line)] if i in complete or normalized(line) in fixed[field] else sentences(start, line)
            for left, right, sentence in pieces:
                category, state, reason, handles = classify(sentence, facts, complete.get(i), fixed[field], projection)
                if len(statements) >= 200:
                    category, state, reason, handles = "scope", "contradiction", "statement_limit", []
                    right, sentence = len(value), value[left:]
                key = digest(canonical([VERSION, doc.id, doc.qa_revision, signature, field, left, right]))
                statements.append(
                    dict(id=key, field=field, start=left, end=right, text=sentence, claim_type=category, outcome=state, reason=reason, handles=handles)
                )
                if reason == "statement_limit":
                    break
            if statements[-1]["reason"] == "statement_limit":
                break
    return dict(
        version=VERSION,
        qa_revision=doc.qa_revision,
        content_digest=signature,
        manifest_digest=run.knowledge["c3_manifest"]["digest"],
        scope={k: projection.get(k) for k in ("product", "sku", "market", "locale", "region", "channel")},
        statements=statements,
    )
