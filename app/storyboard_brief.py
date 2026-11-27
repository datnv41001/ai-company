"""Scoped, deterministic editorial handoff. Unrecognized free text stays visible for clarification."""

import textwrap
import unicodedata

from . import c3_assets, c3_order_units, c3_studio, video_storyboard as legacy
from .knowledge_store import canonical, digest


def normalize(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split()).rstrip(".!?")


# These are whole supported instructions. A compound or negated instruction
# must never pass just because one of its words matches a supported operation.
ILLUSTRATE = "Soạn storyboard có hình minh họa."
PROOF = "Minh họa dữ kiện sản phẩm trước lời mời hành động."
TERMS = "Giải thích điều kiện báo giá trước lời mời hành động."
COMMERCIAL = "Đối chiếu điều kiện thương mại theo đúng nguồn."
CAPTIONS = "Có phụ đề tiếng Việt khớp lời thoại."
UNSUPPORTED = ("Thu âm lời thoại.", "Xuất video quảng cáo có âm thanh.", "Dùng cảnh quay người thật.")
# Each pair offers two editorial treatments of the same authorized conversion.
# Approved price declarations and the creative angle never select a different action.
HOOKS = {
    "rfq": {
        "plain": ("Bạn cần báo giá gì?", "Hỏi báo giá cần chuẩn bị gì?"),
        "concise": ("Cần báo giá?", "Hỏi báo giá cần gì?"),
        "formal": ("Quý vị cần báo giá?", "Quý vị muốn hỏi báo giá nào?"),
        "friendly": ("Mình cần báo giá gì nhỉ?", "Mình xem gì trước khi hỏi báo giá?"),
    },
    "appointment": {
        "plain": ("Bạn muốn hẹn lúc nào?", "Bạn cần biết gì trước khi hẹn?"),
        "concise": ("Hẹn khi nào?", "Cần gì trước khi hẹn?"),
        "formal": ("Quý vị muốn đề nghị lịch hẹn nào?", "Quý vị cần biết gì trước khi hẹn?"),
        "friendly": ("Mình muốn hẹn khi nào nhỉ?", "Mình xem gì trước khi hẹn nhé?"),
    },
    "choose_session": {
        "plain": ("Bạn muốn chọn buổi nào?", "Buổi nào hợp với bạn?"),
        "concise": ("Chọn buổi nào?", "Buổi nào phù hợp?"),
        "formal": ("Quý vị muốn chọn buổi nào?", "Buổi nào phù hợp với quý vị?"),
        "friendly": ("Mình chọn buổi nào nhỉ?", "Buổi nào hợp với mình nhỉ?"),
    },
}
PURPOSES = {
    "rfq": ("Nhận yêu cầu báo giá", "Giúp người mua đối chiếu điều kiện báo giá"),
    "appointment": ("Nhận đề nghị đặt lịch", "Giúp người mua chuẩn bị đề nghị đặt lịch"),
    "choose_session": ("Thu nhận lựa chọn buổi", "Giúp người học chọn buổi"),
}


def purpose_kind(projection):
    intent = projection["task_intent"]
    target = normalize(intent["purpose"])
    if target != normalize(projection["objective"]):
        return None
    for index, template in enumerate(PURPOSES[intent["buyer_action"]]):
        if target == normalize(f"{template} {projection['product']}"):
            return ("request", "prepare")[index]
    return None


def style_hooks(projection):
    intent = projection["task_intent"]
    return HOOKS[intent["buyer_action"]][intent["editorial_style"]]


def handoff(projection, ref):
    intent = projection["task_intent"]
    notes = {normalize(v) for v in [*intent["requirements"], *intent["acceptance_criteria"]]}
    proof = [f for f in projection["facts"] if f["category"] == "description"]
    if not proof:
        raise ValueError("A channel message needs an approved description")
    rfq = intent["buyer_action"] == "rfq"
    wants_terms = normalize(TERMS) in notes or (rfq and purpose_kind(projection) == "prepare")
    has_conditions = any((f.get("price") or {}).get("conditions") for f in projection["facts"])
    angle = "show_evidence"
    direction = "Vẽ hai trạng thái minh họa; đặt dữ kiện đã duyệt ngay dưới hình."
    if wants_terms and (rfq or has_conditions):
        angle = "quote_conditions" if rfq else "commercial_conditions"
        direction = "Đặt thẻ điều kiện theo nguồn sau minh họa, trước lời mời hành động đã duyệt."
    hook = style_hooks(projection)[0]
    copy = [{"source_id": f["id"], "lines": c3_order_units.fact_lines(f, projection)} for f in projection["facts"]]
    return {
        "version": "amc.content-storyboard-handoff/1",
        "role": "ai-copywriter-content-strategist",
        "method": "deterministic",
        "manifest": ref,
        "audience": projection["audience"],
        "purpose": intent["purpose"],
        "channel": projection["channel"],
        "editorial_style": intent["editorial_style"],
        "question_to_validate": (
            {"rfq": "Người mua cần đối chiếu điều gì trước khi hỏi báo giá?",
             "appointment": "Người mua muốn biết phạm vi nào trước khi đề nghị đặt lịch?",
             "choose_session": "Người học cần biết gì để chọn buổi phù hợp?"}[intent["buyer_action"]]
        ),
        "audience_hypotheses": projection.get("hypotheses", []),
        "angle": angle,
        "message_source_id": proof[0]["id"],
        "channel_copy": {"opening": hook, "declarations": copy, "action": c3_studio.buyer_action(projection)},
        "production_direction": direction,
    }


def revise_layout(board, plan, variant):
    hook = plan["channel_copy"]["opening"] if variant == "direct" else f"{plan['audience']} cần biết gì?"
    width = 39
    lines = textwrap.wrap(hook, width=width, break_long_words=False, break_on_hyphens=False)
    if len(lines) > 2 or any(len(line) > width for line in lines):
        raise ValueError("Opening line is too long for a caption card")
    shots = board["shots"]
    while len(shots) > 1 and shots[1]["purpose"] == "hook":
        del shots[1]
    shots[0].update(voice=hook, caption="\n".join(lines), visual=plan["production_direction"])
    board.update(hook=hook, hook_variant=variant)
    lengths = [max(2, (len(s["caption"]) + 14) // 15) for s in shots]
    remaining = board["duration_seconds"] - sum(lengths)
    if remaining < 0:
        raise ValueError("A separate revision is required to fit the approved words")
    for n in range(remaining):
        lengths[n % len(shots)] += 1
    start = 0
    for shot, length in zip(shots, lengths, strict=True):
        shot.update(start_s=start, end_s=start + length)
        start += length
    board["vtt"] = legacy.captions(shots)


def assessment(projection, board):
    intent = projection["task_intent"]
    shots = board["shots"]
    facts = projection["facts"]
    evidence = [s for s in shots if s["source_ids"]]
    facts_covered = set(f["id"] for f in facts) == {f for s in evidence for f in s["source_ids"]}
    action = c3_studio.buyer_action(projection)
    action_words = " ".join(s["voice"] for s in shots if s["purpose"] == "action")
    action_matches = normalize(action_words) == normalize(action) and board["cta"] == action and board["buyer_action"] == intent["buyer_action"]
    terms = [s for s in shots if s["purpose"] in ("terms", "conditions")]
    # A non-RFQ brief can ask to explain pinned commercial terms before its own
    # CTA. A listed price or free-text instruction alone does not supply those conditions.
    conditions_shown = False
    for fact in facts:
        required = (fact.get("price") or {}).get("conditions") or []
        spoken = normalize(" ".join(s["voice"] for s in terms if s["purpose"] == "conditions" and s["source_ids"] == [fact["id"]]))
        if required and all(normalize(condition) in spoken for condition in required):
            conditions_shown = True
    instructions = {
        normalize(ILLUSTRATE): (board["rights"] == legacy.RIGHTS and all(s["visual"].strip() for s in shots), "shots[].visual; rights"),
        normalize(PROOF): (facts_covered and bool(evidence) and max(s["end_s"] for s in evidence) <=
                           min((s["start_s"] for s in shots if s["purpose"] == "action"), default=-1), "proof before action; source_ids"),
        normalize(TERMS): (bool(terms) and bool(evidence) and action_matches and (intent["buyer_action"] == "rfq" or conditions_shown) and
                           max(s["end_s"] for s in terms) <= min((s["start_s"] for s in shots if s["purpose"] == "action"), default=-1),
                           "approved commercial terms and source conditions before the signed action"),
        normalize(COMMERCIAL): (facts_covered and bool(evidence) and
                                (bool(terms) if any(f.get("price") for f in facts) else board["editorial"]["price_status"] == "unavailable"),
                                "source_refs.declarations; terms or recorded missing price"),
        normalize(CAPTIONS): (all(normalize(s["caption"]) == normalize(s["voice"]) for s in shots)
                              and board["vtt"] == legacy.captions(shots), "shots[].voice; WebVTT"),
    }
    rows = []

    def record(field, value, status, evidence):
        rows.append(dict(field=field, requested=value, status=status, evidence=evidence))

    purpose = purpose_kind(projection)
    style = intent["editorial_style"]
    openings = [s for s in shots if s["purpose"] == "hook"]
    spoken_hook = " ".join(s["voice"] for s in openings)
    caption_hook = " ".join(" ".join(s["caption"].splitlines()) for s in openings)
    hook_matches = board["hook"] == spoken_hook == caption_hook
    audience_hook = board["hook"] == f"{projection['audience']} cần biết gì?"
    fits_action = audience_hook or any(board["hook"] in pair for pair in HOOKS[intent["buyer_action"]].values())
    purpose_met = bool(purpose) and hook_matches and fits_action and action_matches and (purpose != "prepare" or intent["buyer_action"] != "rfq" or bool(terms))
    record("purpose", intent["purpose"], "met" if purpose_met else "clarify",
           "signed objective, action-compatible opening, current CTA and requested preparation" if purpose_met else
           "Confirm a supported product objective and its evidence before approval.")
    # Only the opening has a controlled style. Protected declarations keep their approved wording.
    style_met = hook_matches and (board["hook"] in style_hooks(projection) or (style == "plain" and audience_hook))
    record("editorial_style", style, "met" if style_met else "clarify", "spoken and captioned opening against action-specific style alternatives")
    for field in ("requirements", "acceptance_criteria"):
        for n, value in enumerate(intent[field]):
            key = normalize(value)
            if key in instructions:
                met, reason = instructions[key]
                status = "met" if met else "clarify"
            elif key in {normalize(v) for v in UNSUPPORTED}:
                status, reason = "unsupported", "Outside the synthetic, silent storyboard production scope."
            else:
                status, reason = "clarify", "Ask the brief owner for a testable supported instruction."
            record(f"{field}[{n}]", value, status, reason)
    record("channel", projection["channel"], "met" if projection["channel"] == "vertical-social" else "unsupported",
           "Vietnamese vertical-social script and captions, 9:16")
    return {"version": "amc.storyboard-fulfillment/1", "rows": rows, "ready_for_qa": all(r["status"] == "met" for r in rows),
            "manifest": board["source_refs"]["manifest"], "fact_handles": [f["id"] for f in facts]}


def compose(projection, ref, variant="direct", *, plan=None):
    board = legacy.compose(projection, ref)
    if variant not in ("direct", "audience"):
        raise ValueError("Unknown storyboard opening")
    if plan is None:
        plan = handoff(projection, ref)
    revise_layout(board, plan, variant)
    public = c3_assets.normalized(" ".join([board["product"], *(s["voice"] for s in board["shots"])]))
    if any(term in public for term in c3_assets.prohibitions(projection)):
        raise ValueError("Opening conflicts with pinned editorial prohibitions")
    board.update(version="amc.storyboard/2", content_handoff_digest=digest(canonical(plan)),
                 brief_fulfillment=assessment(projection, board))
    return board
