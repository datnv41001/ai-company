"""Make an internal 9:16 animatic from one exported WF-08 revision, without model calls."""

from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
import re

from PIL import Image, ImageDraw, ImageFont

from .production_creative import FONT, text_lines, webm

SIZE = (540, 960)
# Conservative internal mobile overlay reservation; re-check the selected placement before distribution.
SAFE = (42, 105, 453, 734)
STYLES = {
    "parts": ("#203D35", "#EDF1DD", "#BBD487", "#597D65"),
    "route": ("#193751", "#E9F3F7", "#96CFE5", "#517C93"),
    "rhythm": ("#382B43", "#F8F0E6", "#F8BC6C", "#926C83"),
}
MODES = {"mechanism", "process", "document", "comparison", "offer", "request"}


@lru_cache
def font(size):
    return ImageFont.truetype(str(FONT), size, layout_engine=ImageFont.Layout.BASIC)


def label(draw, text, box, px, ink, boxes):
    """Reserve space using visible glyph extents, including Vietnamese accents."""
    x, y, right, bottom = box
    for size in range(px, 15, -1):
        face = font(size)
        lines = text_lines(draw, text, face, right - x - 4)
        if not lines:
            continue
        heights = [draw.textbbox((0, 0), line, font=face, anchor="lt")[3] for line in lines]
        gap = max(3, size // 4)
        if sum(heights) + gap * (len(lines) - 1) > bottom - y:
            continue
        for line, height in zip(lines, heights, strict=True):
            pos = (x + 2, y)
            bounds = draw.textbbox(pos, line, font=face, anchor="lt")
            if not (SAFE[0] <= bounds[0] <= bounds[2] <= SAFE[2] and SAFE[1] <= bounds[1] <= bounds[3] <= SAFE[3]):
                raise ValueError("Visible copy outside the channel safe area")
            draw.text(pos, line, font=face, fill=ink, anchor="lt")
            boxes.append(list(bounds))
            y += height + gap
        return
    raise ValueError("Edit the copy to fit the reserved mobile safe area")


def wording(value):
    return " ".join(value.casefold().split()).rstrip(".")


def visual_direction(board, shot, style):
    """Specific diagrams require a cited declaration; the operator's palette alone grants no claim."""
    declarations = board.get("source_refs", {}).get("declarations", {})
    mode, purpose = shot["visual_mode"], shot.get("purpose")
    scene = wording(shot["caption"])
    citations = []
    if purpose == "hook":
        establishing = {"removable_divider": "installed_tray", "deliverable_map": "route_overview", "pulse_strength": "pulse_overview"}
        for proof in board["shots"]:
            if proof.get("purpose") == "proof":
                detail, refs = visual_direction(board, proof, style)
                if detail in establishing:
                    return establishing[detail], refs
    for ref in shot.get("source_ids", []):
        if ref not in declarations:
            continue
        fact = declarations[ref]
        authorized = wording(fact["wording"])
        qualifiers = [wording(q) for q in fact.get("qualifiers", [])]
        # These editorial schematics cover a narrow reviewed meaning and its visible qualifiers.
        if purpose == "proof" and all(q in scene for q in qualifiers) and authorized in scene:
            if style == "parts" and authorized == "vách ngăn có thể tháo rời" and qualifiers == ["áp dụng cho mẫu tiêu chuẩn"]:
                return "removable_divider", [ref]
            if style == "rhythm" and authorized == "bảng nhịp có ký hiệu phách mạnh và phách nhẹ":
                return "pulse_strength", [ref]
            if style == "route" and authorized == "bàn giao sơ đồ luồng nhận hàng":
                return "deliverable_map", [ref]
        if purpose == "conditions" and board.get("buyer_action") == "appointment" and scene == "người phụ trách xác nhận lịch sau khi nhận đề nghị":
            if scene in [wording(c) for c in fact.get("conditions", []) + fact.get("qualifiers", [])]:
                return "pending_confirmation", [ref]
        citations.append(ref)
    if mode == "request" and board.get("buyer_action") == "choose_session":
        return "session_selection", []
    if mode == "request":
        return "outgoing_request", []
    if mode == "offer":
        return "offer_ticket", citations
    if mode == "document":
        return "document", citations
    return "opening", []


def tray(draw, x, lifted, ink, paper, accent, muted):
    def poly(points, fill, line=None):
        draw.polygon([(x + a, b) for a, b in points], fill=fill, outline=line, width=2)

    poly([(1, 108), (101, 88), (165, 114), (59, 146)], paper, muted)
    poly([(1, 108), (59, 146), (59, 159), (1, 121)], muted)
    poly([(59, 146), (165, 114), (165, 128), (59, 159)], accent)
    # Retain the same base, contents and fixed partition in both views.
    poly([(24, 101), (81, 130), (81, 117), (24, 88)], muted, ink)
    for a, b in ((18, 108), (40, 117), (105, 103), (118, 109)):
        draw.ellipse((x + a, b, x + a + 6, b + 4), fill=ink)
    if lifted:
        draw.line((x + 78, 93, x + 78, 69), fill=accent, width=3)
        draw.polygon([(x + 73, 73), (x + 78, 66), (x + 83, 73)], fill=accent)
    poly([(62, 96 - lifted), (119, 123 - lifted), (119, 105 - lifted), (62, 78 - lifted)], accent, ink)


def illustration(style, direction, progress):
    """All marks are original internal schematics; no external images are read."""
    ink, paper, accent, muted = STYLES[style]
    im = Image.new("RGB", (409, 223), ink)
    d = ImageDraw.Draw(im)

    def mark(x, y, text, size=17, fill=paper):
        d.text((x, y), text, fill=fill, font=font(size), anchor="mt")

    if direction == "removable_divider":
        mark(204, 12, "CÙNG MỘT KHAY", 17, accent)
        tray(d, 16, 0, ink, paper, accent, muted)
        tray(d, 225, 44 + int(16 * progress), ink, paper, accent, muted)
        d.line([(185, 109), (210, 109), (201, 102)], fill=accent, width=3)
        mark(92, 183, "Vách đang lắp")
        mark(308, 183, "Nhấc vách ra")
    elif direction == "installed_tray":
        tray(d, 122, 0, ink, paper, accent, muted)
        mark(204, 170, "Mẫu tiêu chuẩn", 18)
    elif direction == "route_overview":
        d.line([(87, 140), (166, 140), (166, 92), (319, 92)], fill=accent, width=7)
        for x, y in ((87, 140), (166, 92), (319, 92)):
            d.rounded_rectangle((x - 12, y - 12, x + 12, y + 12), 4, fill=paper)
        mark(204, 176, "Luồng nhận hàng")
    elif direction == "pulse_overview":
        for i, x in enumerate((94, 168, 242, 316)):
            radius = 12 + (9 if i == min(3, int(progress * 4)) else 0)
            d.ellipse((x - radius, 104 - radius, x + radius, 104 + radius), outline=accent, width=4)
        mark(204, 164, "Đọc nhịp", 19)
    elif direction == "pulse_strength":
        mark(203, 17, "VÍ DỤ MINH HỌA", 16, accent)
        d.line((39, 117, 371, 117), fill=muted, width=3)
        for i, (x, r, text) in enumerate(((108, 29, "Phách mạnh"), (300, 15, "Phách nhẹ"))):
            d.ellipse((x - r, 111 - r, x + r, 111 + r), fill=accent if not i else ink, outline=paper, width=4)
            if int(progress * 3) % 2 == i:
                d.arc((x - r - 10, 111 - r - 10, x + r + 10, 111 + r + 10), 195, 345, fill=accent, width=3)
            mark(x, 170, text, 19)
    elif direction == "pending_confirmation":
        mark(204, 14, "SAU KHI GỬI ĐỀ NGHỊ", 16, accent)
        d.rounded_rectangle((19, 73, 141, 151), 8, outline=paper, width=4)
        d.line([(22, 78), (79, 119), (137, 78)], fill=paper, width=3)
        d.line((157, 109, 223, 109), fill=accent, width=4)
        d.line([(214, 101), (224, 109), (214, 117)], fill=accent, width=3)
        d.ellipse((272, 54, 310, 92), outline=paper, width=4)
        d.arc((242, 93, 340, 168), 180, 360, fill=paper, width=4)
        mark(82, 170, "Đề nghị")
        mark(286, 170, "Chờ xác nhận")
    elif direction == "session_selection":
        mark(204, 16, "CHỌN BUỔI", 18, accent)
        for i, y in enumerate((64, 132)):
            d.rounded_rectangle((55, y, 354, y + 52), 8, fill=paper)
            d.ellipse((78, y + 14, 102, y + 38), outline=ink, width=3)
            if i == int(progress > 0.5):
                d.ellipse((84, y + 20, 96, y + 32), fill=ink)
            d.line((127, y + 25, 245, y + 25), fill=muted, width=5)
    elif direction == "offer_ticket":
        d.rounded_rectangle((72, 50, 338, 172), 18, fill=paper)
        for x in range(90, 320, 13):
            d.line((x, 142, x + 5, 142), fill=muted, width=2)
        d.ellipse((92, 76, 120, 104), outline=ink, width=4)
        d.line((142, 89, 282, 89), fill=ink, width=7)
        d.line((144, 109, 220, 109), fill=muted, width=4)
    elif direction == "outgoing_request":
        shift = int(15 * progress)
        d.rounded_rectangle((79, 68, 257, 162), 8, outline=paper, width=5)
        d.line([(81, 72), (168, 128), (255, 72)], fill=accent, width=5)
        d.line((266, 106, 311 + shift, 106), fill=accent, width=5)
        d.line([(301 + shift, 94), (314 + shift, 106), (301 + shift, 118)], fill=accent, width=5)
    elif direction in ("document", "deliverable_map"):
        d.polygon([(99, 27), (267, 27), (310, 68), (310, 194), (99, 194)], fill=paper)
        d.polygon([(267, 27), (267, 68), (310, 68)], fill=accent)
        if direction == "deliverable_map":
            mark(189, 45, "SƠ ĐỒ", 16, ink)
            d.line([(129, 149), (185, 149), (185, 96), (267, 96)], fill=muted, width=6)
            for x, y in ((129, 149), (185, 96), (267, 96)):
                d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=ink)
        else:
            for y, end in ((92, 255), (111, 229), (130, 244)):
                d.line((136, y, end, y), fill=muted, width=3)
    else:
        # Frame the question. No object properties can be inferred from the operator's style choice.
        mark(204, 38, "?", 108, accent)
        d.line((162, 179, 247, 179), fill=paper, width=3)
    return im


def frame(board, shot, style, direction, progress):
    ink, paper, accent, muted = STYLES[style]
    photo = Image.new("RGB", SIZE, paper)
    d = ImageDraw.Draw(photo)
    boxes = []
    label(d, "MINH HỌA TỔNG HỢP", (42, 108, 450, 137), 19, ink, boxes)
    label(d, board["brand"], (42, 151, 450, 212), 45, ink, boxes)
    d.line((44, 223, 450, 223), fill=muted, width=2)
    label(d, board["product"], (42, 242, 450, 307), 26, ink, boxes)
    photo.paste(illustration(style, direction, progress), (43, 325))
    # The visible caption is always the role output; discretionary styling cannot alter meaning.
    label(d, shot["caption"], (42, 574, 450, 731), 33, ink, boxes)
    return photo, boxes


def render(source, destination, style):
    if source.stat().st_size > 192_000:
        raise ValueError("Source exceeds the preview limit")
    raw = source.read_bytes()
    files, receipt = render_bytes(raw, style, source.name)
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    (destination / "render.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf8")
    return receipt


def render_bytes(raw, style, source_name):
    if len(raw) > 192_000:
        raise ValueError("Source exceeds the preview limit")
    board = json.loads(raw)
    duration = board["duration_seconds"]
    if board["version"] not in ("amc.storyboard/1", "amc.storyboard/2") or type(duration) is not int or not 1 <= duration <= 32:
        raise ValueError("Expected a short WF-08 storyboard")
    if board.get("format") != "9:16" or board.get("rights") != "synthetic_illustration_only":
        raise ValueError("This portrait preset requires synthetic illustration rights")
    shots = board["shots"]
    if not 1 <= len(shots) <= 16:
        raise ValueError("Expected a bounded shot list")
    starts_at = 0
    frames, placements = [], []
    for shot in shots:
        end = shot["end_s"]
        if shot["start_s"] != starts_at or type(end) is not int or not starts_at < end <= duration:
            raise ValueError("Shots must form one contiguous timeline")
        if shot["visual_mode"] not in MODES or not str(shot["caption"]).strip():
            raise ValueError("Missing caption or unsupported visual mode")
        direction, refs = visual_direction(board, shot, style)
        placement = None
        for t in range(end - starts_at):
            picture, placement = frame(board, shot, style, direction, t / max(1, end - starts_at - 1))
            frames.append(picture)
        placements.append(
            {
                "from_s": starts_at,
                "to_s": end,
                "visual_mode": shot["visual_mode"],
                "glyph_boxes": placement,
                "illustration": direction,
                "illustration_source_ids": refs,
            }
        )
        starts_at = end
    if starts_at != duration:
        raise ValueError("Last shot ends before the approved duration")
    vtt = board["vtt"]
    cues = re.findall(r"^(\d\d):(\d\d):(\d\d)\.000 --> (\d\d):(\d\d):(\d\d)\.000\s*\n(.+?)(?=\n\s*\n|\Z)", vtt, flags=re.M | re.S)
    if not vtt.startswith("WEBVTT") or len(cues) != len(shots):
        raise ValueError("Missing or incomplete timed caption track")
    for cue, shot in zip(cues, shots, strict=True):
        times = [int(cue[i]) * 3600 + int(cue[i + 1]) * 60 + int(cue[i + 2]) for i in (0, 3)]
        if times != [shot["start_s"], shot["end_s"]] or cue[6].split() != shot["caption"].split():
            raise ValueError("Captions and timecodes must match the approved shot")
    files = {"preview.webm": webm(frames, seconds=1), "captions.vtt": vtt.encode("utf8")}
    still = BytesIO()
    frames[0].save(still, "PNG", optimize=True)
    files["poster.png"] = still.getvalue()
    receipt = {
        "source_file": source_name,
        "source_sha256": sha256(raw).hexdigest(),
        "renderer": "amc/storyboard-preview/2",
        "style": style,
        "format": "VP8/WebM",
        "size": SIZE,
        "duration_seconds": duration,
        "safe_rect": SAFE,
        "frames_per_second": 1,
        "audio_tracks": 0,
        "rights": "Original AMC synthetic diagrams and SIL OFL Studio font, internal sandbox only.",
        "shots": placements,
        "files": {name: sha256(data).hexdigest() for name, data in files.items()},
    }
    return files, receipt
