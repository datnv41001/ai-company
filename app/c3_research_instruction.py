"""Internal Research instruction vocabulary, version one. Each sentence needs a signed review."""
VERSION = "amc.research-instruction/1"
HANDOVER = "At the last handover, what did you try to find immediately before using or putting aside the tray?"

# Whole, reviewed utterances only. Never interpolate model text, product names, source locators
# or claimed outcomes here. New wording needs an explicit vocabulary review.
SENTENCES = {
    "en-US": frozenset({
        HANDOVER,
        "What did you do immediately before your last purchase?",
        "What information did you look for before your last purchase?",
        "Show the step or document you used.",
    }),
    "vi-VN": frozenset({
        "Ngay trước lần mua gần nhất, bạn đã làm gì?",
        "Bạn đã tìm thông tin gì trước lần mua gần nhất?",
        "Hãy chỉ ra bước hoặc tài liệu bạn đã sử dụng.",
    }),
}


def eligible_span(row, projection):
    if row["text"] == HANDOVER:
        product_words = projection.get("product", "").casefold().split()
        purpose = projection.get("task_intent", {}).get("purpose", "").casefold()
        if "tray" not in product_words or "handover" not in purpose:
            return False
    return (row["field"] == "studio.research.research_question"
            and row["outcome"] == "unresolved" and row["claim_type"] in ("unclassified", "comparison")
            and row["reason"] == "unsupported" and not row["handles"]
            and row["text"] in SENTENCES.get(projection["locale"], ()))


def identity(row, run, snap):
    return dict(contract=VERSION, purpose="internal_research_planning",
                manifest_id=snap.id, manifest_digest=snap.digest, campaign_id=run.campaign_id,
                tenant_id=run.tenant_id, client_id=run.client_id, brand_id=run.brand_id,
                statement_id=row["id"], field=row["field"], start=row["start"], end=row["end"], text=row["text"])
