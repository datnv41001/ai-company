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
HANDLE = re.compile(r"(?<!\w)F[0-9]+(?!\w)", re.I)
BRACKET = re.compile(r"\[\s*(F[0-9]+)\s*\]", re.I)
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
RESEARCH_GAP = re.compile(
    r"(?:buyer|customer|audience|user|market) (?:needs?|preferences?|expectations?) (?:require|need) (?:further )?(?:research|interviews|validation|testing)"
)
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


def protected_phrases(projection):
    return [*(projection.get("brand_guidelines") or {}).get("prohibited_claims", []), *(projection.get("task_intent") or {}).get("exclusions", [])]


def content_shapes(workflow, projection):
    """Derive exact public fact blocks and fixed layout from the release-specific renderer."""
    if workflow not in c3_marketing.ROLES:
        from . import c3_assets

        render = c3_assets.render
        blocks = {f["id"]: " ".join(c3_assets.fact_lines(f, projection)) for f in projection["facts"]}
    else:
        render = c3_marketing.render
        blocks = {f["id"]: c3_marketing.fact_line(f) for f in projection["facts"]}
    baseline = render(workflow, projection, {})
    # These are generated from the pinned data with no model replies. Arbitrary text after
    # a label (including an invented citation), or added after a fixed CTA, is not exempted.
    fixed = {normalized(line) for line in baseline["body"].splitlines() if line.strip()}
    # A rendered line can contain unverified profile or research prose. Being in the
    # scaffold is no proof of a buyer-facing promise. Research labels are checked in
    # their own section, outside the set of trusted layout lines.
    free_prose = [*projection.get("hypotheses", []), *projection.get("gaps", [])]
    fixed.difference_update(normalized(v) for v in free_prose)
    # Historical templates interpolate business goals and KPI text into prose. Those fields
    # can describe a plan, but cannot establish a price, a geographic promise or a benefit.
    for key in ("audience", "objective", "kpi"):
        term = normalized(projection.get(key, ""))
        if term and (
            COMMERCIAL.search(term)
            or TERRITORY.search(term)
            or CHANNEL.search(term)
            or any(pattern.search(term) for _, pattern in SEMANTIC)
            or re.search(r"[%$€£¥₫]|\b(?:vnd|usd|eur)\b", term)
        ):
            fixed = {line for line in fixed if term not in line}
    declarations = {}
    for handle, text in blocks.items():
        fixed.discard(normalized(text))
        declarations.setdefault(clean_handle(text), []).append(handle)
    return declarations, {"title": {normalized(baseline["title"]), normalized(projection["product"])}, "client_preview": fixed}


def spans(value):
    return [(match.start(), match.end(), match.group()) for match in re.finditer(r"[^\s\r\n][^\r\n]*", value)]


def sentences(start, line):
    # Keep decimal/currency punctuation and trailing [F1] with its statement.
    left = 0
    for boundary in re.finditer(r"(?<=[.?!;])\s+(?!\s|\[F\d+\])", line, re.I):
        yield start + left, start + boundary.start(), line[left : boundary.start()]
        left = boundary.end()
    yield start + left, start + len(line), line[left:]


def classify(line, facts, complete, fixed, projection):
    text = normalized(line)
    bare = clean_handle(line)
    cited = list(dict.fromkeys(h.upper() for h in HANDLE.findall(line)))
    handles = set(f["id"] for f in facts)
    forbidden = protected_phrases(projection)
    if any(normalized(term) and normalized(term) in text for term in forbidden):
        return "prohibited", "contradiction", "prohibited", cited
    if any(h not in handles for h in cited):
        return "citation", "contradiction", "unknown_handle", cited
    if complete:
        if set(cited) - set(complete):
            return "citation", "contradiction", "wrong_handle", cited
        selected = cited or complete
        if len(selected) > 1:
            return "unclassified", "unresolved", "ambiguous_evidence", selected
        fact = next(f for f in facts if f["id"] == selected[0])
        return fact["category"], "verified", "exact_declaration", selected
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
        wording = normalized(fact["wording"])
        if wording and any(negation + wording in bare for negation in ("not ", "no ", "không ", "không phải ")):
            return fact["category"], "contradiction", "negated_fact", [fact["id"]]
        if normalized(fact["wording"]) in bare and any(normalized(q) not in bare for q in fact.get("qualifiers", [])):
            return fact["category"], "contradiction", "missing_qualifier", [fact["id"]]
    cat = next((kind for kind, pattern in SEMANTIC if pattern.search(bare)), "unclassified")
    return cat, "unresolved", "unsupported", cited


def assess_document(doc, run, signature):
    from .knowledge_store import conflict

    if not run.knowledge.get("c3_manifest", {}).get("digest") or not run.knowledge.get("c3_projection"):
        conflict("The Marketing run has no pinned content evidence")
    projection = run.knowledge["c3_projection"]
    declarations, fixed = content_shapes(run.knowledge["registry"]["workflow"], projection)
    facts = projection["facts"]
    statements = []
    for field, value in (("title", doc.title), ("client_preview", doc.content.get("client_preview", ""))):
        lines = spans(value)
        # A protected phrase may straddle a line break. Mark every overlapping span
        # so a decision on two separate paraphrases cannot authorize the full phrase.
        forbidden_spans = [
            m.span()
            for phrase in protected_phrases(projection)
            if phrase.strip()
            for m in re.finditer(r"\s+".join(re.escape(word) for word in phrase.split()), value, re.I)
        ]
        section = ""
        for start, end, line in lines:
            if field == "client_preview" and normalized(line) in ("giả thuyết cần kiểm chứng", "dữ liệu cần bổ sung"):
                section = normalized(line)
            # A canonical fact and its qualifiers form one indivisible assertion. Other novel
            # prose gets individual sentence spans even when multiple claims share a paragraph.
            pieces = [(start, end, line)] if clean_handle(line) in declarations or normalized(line) in fixed[field] else sentences(start, line)
            for left, right, sentence in pieces:
                category, state, reason, handles = classify(sentence, facts, declarations.get(clean_handle(sentence)), fixed[field], projection)
                if section == "giả thuyết cần kiểm chứng" and RESEARCH_GAP.fullmatch(normalized(sentence)) and sentence in projection.get("hypotheses", []):
                    category, state, reason, handles = "editorial", "editorial", "research_question", []
                if (
                    section == "dữ liệu cần bổ sung"
                    and sentence in projection.get("gaps", [])
                    and sentence in {"Kiểm chứng nhu cầu với khách hàng trong thị trường đã chọn.", "Xác minh số liệu nền và kết quả bằng dữ liệu đo thực tế."}
                ):
                    category, state, reason, handles = "editorial", "editorial", "research_question", []
                if any(begin < right and left < finish for begin, finish in forbidden_spans):
                    category, state, reason, handles = "prohibited", "contradiction", "prohibited", []
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
