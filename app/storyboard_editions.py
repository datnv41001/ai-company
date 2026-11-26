"""Controlled creative changes to the current WF-08 document. All distribution stays offline."""

from copy import deepcopy
import json
import textwrap
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from . import c3_assets, video_storyboard as video
from .knowledge_models import KnowledgeCommand
from .knowledge_store import canonical, digest

Index = Annotated[int, Field(strict=True, ge=1, le=32)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-f0-9-]{36}$")]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShotEdit(Strict):
    # Index into the baseline the editor actually saw, before any reordering.
    shot: Index
    narration: Literal["as_caption", "listen", "look"] | None = None
    caption: Annotated[str, Field(min_length=1, max_length=79)] | None = None
    proof_lead: Literal["none", "observe", "read"] | None = None
    framing: Literal["original", "detail", "wide", "hold"] | None = None


class DistributionRef(Strict):
    landing_did: Identifier
    landing_pid: Identifier
    distribution_id: Identifier


class StoryboardEdit(Strict):
    expected_qa_revision: int = Field(ge=1, strict=True)
    expected_content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    mode: Literal["editorial", "controlled_hook"] = "editorial"
    hook_variant: Literal["direct", "audience", "product_question", "observation", "style_alternate"] | None = None
    shot_edits: list[ShotEdit] = Field(default_factory=list, max_length=32)
    shot_order: list[Index] | None = Field(default=None, min_length=2, max_length=32)
    durations: list[Annotated[int, Field(strict=True, ge=2, le=59)]] | None = Field(default=None, min_length=2, max_length=32)
    editor_note: Note | None = None
    distribution: DistributionRef | None = None


def fingerprint(value):
    return digest(canonical(value))


def cue(text):
    return "\n".join(textwrap.wrap(text, width=39, break_long_words=False, break_on_hyphens=False))


def durations_for(shots, total):
    lengths = [max(2, (max(len(s["caption"]), len(s["voice"])) + 14) // 15) for s in shots]
    if sum(lengths) > total:
        raise ValueError("Words exceed the commissioned duration")
    for i in range(total - sum(lengths)):
        lengths[i % len(shots)] += 1
    return lengths


def validate_layout(shots, lengths, total):
    if len(shots) != len(lengths) or sum(lengths) != total:
        raise ValueError("The shot durations must cover the commissioned timeline exactly")
    start = 0
    for shot, length in zip(shots, lengths, strict=True):
        lines = shot["caption"].split("\n")
        if length < 2 or len(lines) > 2 or any(not line or len(line) > 39 for line in lines) or max(len(shot["caption"]), len(shot["voice"])) > length * 15:
            raise ValueError("The caption or narration does not fit the shot at the fixed reading rate")
        shot.update(start_s=start, end_s=start + length)
        start += length


FRAMING = {
    "detail": "Cắt cận vào chi tiết đang giải thích.",
    "wide": "Lùi khung để thấy toàn bộ bố cục minh họa.",
    "hold": "Giữ khung tĩnh trong lúc đọc thẻ.",
}
NARRATION = {"as_caption": "", "listen": "Lưu ý. ", "look": "Hãy xem. "}
LEADS = {"none": "", "observe": "Quan sát. ", "read": "Đọc thẻ. "}


def apply_edits(before, body, projection, compose_variant):
    board = deepcopy(before)
    shots = board["shots"]
    old_lengths = [s["end_s"] - s["start_s"] for s in shots]
    if body.hook_variant:
        opening_count = next((i for i, shot in enumerate(shots) if shot["purpose"] != "hook"), len(shots))
        if not opening_count:
            raise ValueError("The storyboard requires an opening card")
        if body.hook_variant in ("direct", "audience"):
            opening = compose_variant(body.hook_variant)["hook"]
        elif body.hook_variant == "style_alternate":
            from .storyboard_brief import STYLES
            style = projection["task_intent"].get("editorial_style")
            if board["version"] != "amc.storyboard/2" or style not in STYLES:
                raise ValueError("This option requires a commissioned WF-08/2 editorial style")
            opening = next(s for s in STYLES[style] if s != board["hook"])
        elif body.hook_variant == "product_question":
            opening = f'{projection["product"]} dùng thế nào?'
        else:
            opening = "Bạn thấy chi tiết nào?"
        board.update(hook=opening, hook_variant=body.hook_variant)
        lines = cue(opening).splitlines()
        cards = ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
        if body.mode == "controlled_hook" and (opening_count != 1 or len(cards) != 1):
            raise ValueError("The fixed single opening card cannot accommodate this treatment")
        if len(cards) != opening_count and (body.shot_edits or body.shot_order is not None or body.durations is not None):
            raise ValueError("Save the changed opening first, then edit the newly numbered shots")
        # Archived WF-08/1 can wrap a long approved audience across several cards.
        # An ordinary edit may resize just the opening; all subsequent work survives.
        opening_shots = [dict(shots[min(i, opening_count - 1)], voice=card.replace("\n", " "), caption=card) for i, card in enumerate(cards)]
        shots[:opening_count] = opening_shots

    seen = set()
    for edit in body.shot_edits:
        if edit.shot in seen or edit.shot > len(shots):
            raise ValueError("Choose a distinct existing shot for each edit")
        seen.add(edit.shot)
        shot = shots[edit.shot - 1]
        if edit.proof_lead is not None:
            if shot["purpose"] != "proof":
                raise ValueError("Only proof cards may receive an editorial lead")
            # Remove a previously applied lead only when it has a saved marker. A
            # declaration can itself begin with the same words and must stay verbatim.
            words = shot["caption"].replace("\n", " ")
            previous = LEADS[shot.get("proof_lead", "none")]
            if previous:
                words = words.removeprefix(previous)
            spoken = LEADS[edit.proof_lead] + words
            shot.update(proof_lead=edit.proof_lead, voice=spoken, caption=cue(spoken))
        if edit.caption is not None:
            if edit.caption.replace("\n", " ") != shot["caption"].replace("\n", " "):
                raise ValueError("Caption layout must retain every approved word")
            shot["caption"] = edit.caption
        if edit.narration:
            if shot["purpose"] != "proof":
                raise ValueError("Narration leads apply only to proof cards")
            shot["voice"] = NARRATION[edit.narration] + shot["caption"].replace("\n", " ")
        if edit.framing:
            # Framing changes the shot direction without changing the licensed subject.
            for previous in FRAMING.values():
                shot["visual"] = shot["visual"].removesuffix("\n" + previous)
            if edit.framing != "original":
                shot["visual"] += "\n" + FRAMING[edit.framing]

    if body.shot_order is not None:
        n = len(shots)
        if sorted(body.shot_order) != list(range(1, n + 1)):
            raise ValueError("Each existing shot must appear once")
        ordered = [shots[i - 1] for i in body.shot_order]
        if [s["purpose"] for s in ordered] != [s["purpose"] for s in shots]:
            raise ValueError("Keep opening, proof, commercial terms, conditions and CTA in their approved positions")
        # All fragments of one declaration move together, in their original internal order.
        groups = {}
        for i, shot in enumerate(shots, 1):
            if shot["purpose"] == "proof":
                groups.setdefault(tuple(shot["source_ids"]), []).append(i)
            elif body.shot_order[i - 1] != i:
                raise ValueError("Only complete proof declarations may move")
        for group in groups.values():
            pos = body.shot_order.index(group[0])
            if body.shot_order[pos : pos + len(group)] != group:
                raise ValueError("Keep the full declaration and its qualifiers together")
        shots = board["shots"] = ordered
        old_lengths = [old_lengths[i - 1] for i in body.shot_order]
    if body.editor_note is not None:
        if body.editor_note:
            board["editorial"]["editor_note"] = body.editor_note
        else:
            board["editorial"].pop("editor_note", None)

    if body.mode == "controlled_hook":
        if not body.hook_variant or seen or any(x is not None for x in (body.shot_order, body.durations, body.editor_note)):
            raise ValueError("A controlled hook permits only a hook change; use editorial mode for multiple variables")
        lengths = old_lengths
    elif body.durations is not None:
        lengths = body.durations
    elif body.hook_variant:
        lengths = durations_for(shots, board["duration_seconds"])
    else:
        lengths = old_lengths
    validate_layout(shots, lengths, board["duration_seconds"])
    board["vtt"] = video.captions(shots)
    copy = c3_assets.normalized(" ".join([board["product"], board["cta"], *(s["voice"] for s in shots), *(s["caption"] for s in shots)]))
    if any(term in copy for term in c3_assets.prohibitions(projection)):
        raise ValueError("Edited copy conflicts with the pinned brand or task policy")
    return board


def commitments(board, landing, distribution):
    # Removing only the explicit hook treatment captures future fields too. VTT is
    # a checked derivative; every cue's timing and every other caption stay pinned.
    other = deepcopy(board)
    for key in ("hook", "hook_variant", "shots", "vtt", "cta", "buyer_action", "source_refs", "rights", "duration_seconds"):
        other.pop(key)
    shot_content = [{k: v for k, v in shot.items() if k not in ("start_s", "end_s", "visual_mode", "visual")} for shot in board["shots"]]
    opening, *rest = shot_content
    for key in ("voice", "caption"):
        opening.pop(key)
    return {
        "body": fingerprint(rest),
        "opening_structure": fingerprint(opening),
        "timeline": fingerprint([board["duration_seconds"], [(s["start_s"], s["end_s"]) for s in board["shots"]]]),
        "visual": fingerprint([(s["visual_mode"], s["visual"]) for s in board["shots"]]),
        "cta": fingerprint([board["cta"], board["buyer_action"]]),
        "offer_claims_rights": fingerprint([board["source_refs"], board["rights"]]),
        "brief_and_direction": fingerprint(other),
        "landing": fingerprint(landing),
        "distribution": fingerprint(distribution),
    }


def comparison(before, after, mode, landing, distribution):
    left, right = (commitments(b, landing, distribution) for b in (before, after))
    changes = [k for k in left if left[k] != right[k]]
    hook_changed = before["hook"] != after["hook"]
    if hook_changed:
        changes.insert(0, "hook")
    elif any(before["shots"][0][k] != after["shots"][0][k] for k in ("voice", "caption")):
        changes.append("opening_copy")
    elif before["hook_variant"] != after["hook_variant"]:
        changes.append("opening_variant")
    if mode == "controlled_hook":
        if changes != ["hook"] or after["shots"][0]["voice"] != after["hook"] or after["shots"][0]["caption"] != cue(after["hook"]):
            raise ValueError("The proposed treatment must change only the actual hook wording")
        if any(b["vtt"] != video.captions(b["shots"]) for b in (before, after)):
            raise ValueError("The WebVTT cues must match the compared shots")
    return {
        "mode": mode,
        "classification": "offline_single_hook_design" if mode == "controlled_hook" else "editorial_revision",
        "changed_variables": changes, "baseline_holds": left, "candidate_holds": right,
        "landing": landing, "distribution": distribution, "observed_traffic": 0, "outcome": None,
        "external_calls": 0, "spend_microusd": 0,
    }


def checked_board(store, doc, run, projection, ref, runtime, *, for_qa=True):
    from .revision_qa import content_digest

    current = json.loads(doc.content["client_preview"])
    revision = doc.qa_revision
    row = store.db.scalar(store.query(KnowledgeCommand).filter_by(
        operation="c3_storyboard_edit", key=f"board:{doc.id}:{revision}", snapshot_id=ref["id"],
    ))
    if row is None:
        expected = runtime.compose(projection, ref, current["hook_variant"], release=run.knowledge["registry"]["workflow"])
        if expected != current:
            raise ValueError("The preview has no matching worker or edition receipt")
    else:
        result = row.result
        if (result["run_id"], result["revision"], result["board_digest"], result["content_digest"]) != (
            run.id, revision, fingerprint(current), content_digest(doc.title, doc.content["client_preview"])
        ):
            raise ValueError("The preview does not match the immutable scoped edition receipt")
    if doc.title != run.knowledge["title"] or current["vtt"] != video.captions(current["shots"]):
        raise ValueError("The storyboard title or captions changed outside the editor")
    if for_qa:
        runtime.require_fulfillment(current, projection)
    return current, row
