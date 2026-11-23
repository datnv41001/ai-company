"""Deterministic QA triage. A matching quote is traceability, not an endorsement."""

import re
import unicodedata

PATTERNS = {
    "price": r"\b(?:giá phải chăng|gia phai chang|giá rẻ|rẻ nhất|affordable|cheapest|lowest price|budget.friendly)\b",
    "endorsement": r"\b(?:được chuyên gia (?:khuyên dùng|khuyến nghị)|bác sĩ khuyên dùng|expert.recommended|recommended by experts|doctor.recommended)\b",
    "superiority": r"\b(?:chất lượng hàng đầu|tốt nhất|tot nhat|số một|best.in.class|top.quality|the best|number one)\b",
    "guarantee": r"\b(?:đảm bảo kết quả|cam kết hiệu quả|guaranteed results|guaranteed to)\b",
}
RULESET = "marketing-evidence-2"
RULES = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in PATTERNS.items()}


def normalize(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split()).strip(" .!?;")


def assess(output, sources):
    cited = {k: sources[k]["excerpt"] for k in output["source_ids"] if k in sources}
    quotes = {}
    for key, excerpt in cited.items():
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", excerpt):
            quotes.setdefault(normalize(sentence), set()).add(key)
    findings = []
    for field, value in output["sections"].items():
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", value):
            sentence = unicodedata.normalize("NFC", sentence.strip())
            categories = [name for name, pattern in RULES.items() if pattern.search(sentence)]
            if not categories:
                continue
            # Restrict matches to complete sentences in cited excerpts: "not affordable"
            # or a claim about a different product cannot support a substring match.
            matches = sorted(quotes.get(normalize(sentence), ()))
            findings.append(
                {
                    "field": field,
                    "claim": sentence,
                    "categories": categories,
                    "cited_ids": list(cited),
                    "matching_ids": matches,
                    "status": "source_quote" if matches else "needs_evidence",
                }
            )
    return {"ruleset": RULESET, "claims": findings}
