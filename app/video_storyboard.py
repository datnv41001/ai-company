"""WF-08 internal preproduction. Only pinned public declarations can become buyer-facing copy."""

import hashlib
import json
from pathlib import Path
import textwrap

from . import c3_assets, c3_order_units, c3_studio
from .knowledge_store import canonical, digest
from .workforce_gateway import GatewayError

RELEASE = "WF-08/video-storyboard@1"
ROLE = "ai-video-storyboard"
ADAPTER = "local-storyboard/1"
GUIDE = "catalog/video-storyboard-sop-v1.json"
EXPORT = "amc.storyboard/1"
RIGHTS = "synthetic_illustration_only"
DIRECTOR_VERSION = 6
POLICIES = {
    "rfq": ("product_demonstration", "mechanism", "Cách dùng nào phù hợp với công việc?", "Tách thao tác thành hai trạng thái để người xem đối chiếu."),
    "appointment": ("service_deliverable", "process", "Khi gửi đề nghị, bạn cần biết điều gì?", "Vẽ luồng bàn giao rồi phóng vào kết quả được duyệt."),
    "choose_session": ("educational", "comparison", "Bạn muốn chọn buổi nào?", "Đặt hai thẻ lựa chọn cạnh nhau rồi đánh dấu bước người xem cần thực hiện."),
}


def source_digest():
    return hashlib.sha256(Path(__file__).read_text(encoding="utf8").encode()).hexdigest()


def json_text(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def concept(projection):
    intent = projection["task_intent"]
    policy = POLICIES.get(intent.get("buyer_action"))
    if not policy or projection["locale"] != "vi-VN" or intent.get("rights") != RIGHTS:
        raise ValueError("This release requires a supported Vietnamese brief and synthetic-only illustration rights")
    return policy


def captions(shots):
    parts = ["WEBVTT", ""]
    for n, s in enumerate(shots, 1):
        start, end = s["start_s"], s["end_s"]
        parts.extend([str(n), f"00:00:{start:02d}.000 --> 00:00:{end:02d}.000", s["caption"], ""])
    return "\n".join(parts)


def compose(projection, ref, variant="direct"):
    method, visual_mode, opening, demonstration = concept(projection)
    intent = projection["task_intent"]
    facts = projection["facts"]
    descriptions = [f for f in facts if f["category"] == "description"]
    offers = [f for f in facts if f.get("price")]
    if not descriptions or len(offers) > 1 or any(f["category"] not in ("description", "price") for f in facts):
        raise ValueError("Select a description and at most one consistent approved offer")
    if variant not in ("direct", "audience"):
        raise ValueError("Unknown hook revision")
    if variant == "audience":
        opening = projection["audience"] + " cần biết gì?"
    product = projection["product"]
    cta = c3_studio.buyer_action(projection)
    frames = [("hook", visual_mode, opening, demonstration, [])]
    for f in descriptions:
        parts = c3_order_units.fact_lines(f, projection)
        wording = " ".join(t if t.endswith((".", "?", "!", "…")) else t + "." for t in parts)
        frames.append(
            (
                "proof",
                "document" if method == "service_deliverable" else visual_mode,
                wording,
                demonstration + " Ghi đúng phạm vi của " + f["id"] + ".",
                [f["id"]],
            )
        )
    if offers:
        f = offers[0]
        price = f["price"]
        # Only accept terms this short format can show without dropping a tier, condition or precision.
        if price["currency"] != "VND" or price.get("tier_max") or price["moq"] != price["tier_min"] or f.get("quantity") != price["moq"]:
            raise ValueError("Commercial tiers require a separate editorial review")
        lines = c3_order_units.fact_lines(f, projection)
        frames.append(("terms", "offer", " ".join(lines[:2]), "Tách số tiền, đơn vị tính thuế và mức đặt tối thiểu.", [f["id"]]))
        conditions = list(dict.fromkeys([*price["conditions"], *f["qualifiers"]]))
        if conditions:
            frames.append(("conditions", "document", " ".join(conditions), "Giữ nguyên điều kiện trên thẻ chữ.", [f["id"]]))
    else:
        frames.append(("scope", "document", "Chưa có giá được duyệt.", "Để trống ô giá và chỉ dẫn nơi hỏi thêm.", []))
    frames.append(("action", "request", cta, "Hiện nút gửi yêu cầu; không vẽ dấu đã xác nhận.", []))
    duration = intent["duration_seconds"]
    shots, start = [], 0
    lengths = []
    for purpose, mode, spoken, visual, refs in frames:
        wrapped = textwrap.wrap(spoken, width=39, break_long_words=False, break_on_hyphens=False)
        # Long commercial declarations keep their exact wording across consecutive cards.
        for pair in range(0, len(wrapped), 2):
            caption = "\n".join(wrapped[pair : pair + 2])
            shots.append(dict(purpose=purpose, visual_mode=mode, visual=visual, voice=caption.replace("\n", " "), caption=caption, source_ids=refs))
            lengths.append(max(2, (len(caption) + 14) // 15))
    if sum(lengths) > duration or any(len(line) > 39 for s in shots for line in s["caption"].splitlines()):
        raise ValueError("The approved words exceed the safe caption or duration limit; shorten the brief or revise the duration")
    for n in range(duration - sum(lengths)):
        lengths[n % len(lengths)] += 1
    for s, length in zip(shots, lengths, strict=True):
        s.update(start_s=start, end_s=start + length)
        start += length
    result = dict(
        version=EXPORT,
        brand=projection["brand"],
        product=product,
        audience=projection["audience"],
        channel=projection["channel"],
        format="9:16",
        duration_seconds=duration,
        concept=method,
        hook=opening,
        hook_variant=variant,
        cta=cta,
        rights=RIGHTS,
        source_refs={"manifest": ref, "guidelines": projection["brand_guidelines"]["digest"], "facts": [f["id"] for f in facts]},
        brand_direction=projection["brand_guidelines"]["guidance"],
        method_ref={
            "path": GUIDE,
            "revision": "wf08-production-sop/1",
            "digest": digest(canonical(json.loads((Path(__file__).resolve().parents[1] / GUIDE).read_text(encoding="utf8")))),
        },
        shots=shots,
        vtt=captions(shots),
    )
    public_copy = c3_assets.normalized(" ".join([product, cta, *(s["voice"] for s in shots)]))
    if any(term in public_copy for term in c3_assets.prohibitions(projection)):
        raise ValueError("The approved declarations conflict with the brand or task policy")
    return result


def request(run, model, *, node, **_):
    stage = node.skill
    field = "assignment" if stage == "director" else "board_json"
    return {
        "local_adapter": ADAPTER,
        "stage": stage,
        "model": ADAPTER,
        "max_tokens": 1,
        "context": run.knowledge.get("c3_projection", {}),
        "manifest": run.knowledge.get("c3_manifest", {}),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "wf08_" + stage,
                "schema": {"type": "object", "properties": {field: {"type": "string"}}, "required": [field], "additionalProperties": False},
            },
        },
    }


ASSIGNMENT = "Produce a scoped, source-bound storyboard with legible commercial terms and a request CTA."


def execute(body):
    if body.get("local_adapter") != ADAPTER or body["stage"] not in ("director", "storyboard"):
        raise GatewayError("unknown_storyboard_adapter")
    try:
        raw = {"assignment": ASSIGNMENT} if body["stage"] == "director" else {"board_json": json_text(compose(body["context"], body["manifest"]))}
    except (ValueError, KeyError) as exc:
        raise GatewayError("storyboard_needs_revision") from exc
    return raw, 0, 0


def director_plan(raw):
    if raw != {"assignment": ASSIGNMENT}:
        raise GatewayError("invalid_storyboard_reply")
    return {"nodes": [{"key": "board", "skill_type": "storyboard", "parents": [], "assignment": ASSIGNMENT}]}


def validated(raw, body):
    expected = execute(body)[0]
    if raw != expected:
        raise GatewayError("invalid_storyboard_reply")
    value = json.loads(raw["board_json"])
    return {
        "text": raw["board_json"],
        "sections": {"storyboard": raw["board_json"]},
        "source_ids": value["source_refs"]["facts"],
        "storyboard_digest": digest(canonical(value)),
    }


def is_run(run):
    return run is not None and run.knowledge.get("registry", {}).get("workflow") == RELEASE
