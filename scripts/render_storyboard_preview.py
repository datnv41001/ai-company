"""Make an internal 9:16 animatic from one exported WF-08 revision, without model calls."""

import argparse
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

from app.production_creative import FONT, text_lines, webm

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


def illustration(style, mode, progress):
    """Original schematic motion studies. Never load customer images, external URLs or fonts."""
    ink, paper, accent, muted = STYLES[style]
    im = Image.new("RGB", (409, 223), ink)
    d = ImageDraw.Draw(im)
    if mode == "offer":
        # A physical price ticket; the literal commercial terms come from the lower caption.
        d.rounded_rectangle((72, 50, 338, 172), 18, fill=paper)
        for x in range(90, 320, 13):
            d.line((x, 142, x + 5, 142), fill=muted, width=2)
        d.ellipse((92, 76, 120, 104), outline=ink, width=4)
        d.line((142, 89, 282, 89), fill=ink, width=7)
        d.line((144, 109, 220, 109), fill=muted, width=4)
    elif mode == "request":
        # Outgoing request envelope; no check mark or booked-calendar metaphor.
        shift = int(15 * progress)
        d.rounded_rectangle((79, 68, 257, 162), 8, outline=paper, width=5)
        d.line([(81, 72), (168, 128), (255, 72)], fill=accent, width=5)
        d.line((266, 106, 311 + shift, 106), fill=accent, width=5)
        d.line([(301 + shift, 94), (314 + shift, 106), (301 + shift, 118)], fill=accent, width=5)
    elif mode == "document":
        # A deliverable or conditions card; an unpriced brief never receives a currency symbol.
        d.polygon([(112, 30), (267, 30), (302, 65), (302, 188), (112, 188)], fill=paper)
        d.polygon([(267, 30), (267, 65), (302, 65)], fill=accent)
        if style == "route":
            d.line([(135, 135), (175, 135), (175, 97), (255, 97)], fill=muted, width=6)
            for x, y in ((135, 135), (175, 97), (255, 97)):
                d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=ink)
        else:
            for y, end in ((92, 255), (111, 229), (130, 244)):
                d.line((136, y, end, y), fill=muted, width=3)
        d.line((135, 166, 270, 166), fill=ink, width=2)
    elif style == "parts":
        # Exploded tray shows a removable divider with a small displacement in successive frames.
        rim = [(48, 95), (241, 65), (358, 111), (155, 151)]
        d.polygon([rim[0], rim[3], (155, 170), (48, 114)], fill=muted)
        d.polygon([rim[3], rim[2], (358, 132), (155, 170)], fill=accent)
        d.polygon(rim, fill=paper, outline=muted, width=3)
        for i, dx in enumerate((0, 60)):
            up = (10 + int(24 * progress)) if i and mode in {"mechanism", "comparison"} else 0
            d.polygon([(112 + dx, 88 - up), (207 + dx, 128 - up), (207 + dx, 109 - up), (112 + dx, 70 - up)], fill=accent, outline=ink, width=2)
        for x, y in ((93, 102), (124, 112), (238, 88), (266, 97)):
            d.ellipse((x, y, x + 9, y + 5), fill=muted)
    elif style == "route":
        # A non-geographic example route, with no time or performance claim.
        nodes = [(68, 158), (168, 158), (168, 71), (307, 71)]
        d.line(nodes, fill=accent, width=8, joint="curve")
        for i, (x, y) in enumerate(nodes):
            if i in (0, len(nodes) - 1):
                d.rounded_rectangle((x - 19, y - 19, x + 19, y + 19), 7, fill=paper)
            else:
                d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=paper)
        idx = min(2, int(progress * 3))
        frac = min(1, progress * 3 - idx)
        x, y = [a + (b - a) * frac for a, b in zip(nodes[idx], nodes[idx + 1], strict=True)]
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=ink, outline=accent, width=3)
    else:
        # Illustrative pulse notation without soundtrack, recording or suggested learning result.
        positions = [(83, 136), (152, 124), (221, 133), (290, 109)]
        for y in range(84, 159, 14):
            d.line((49, y, 351, y), fill=muted, width=2)
        for idx, (x, y) in enumerate(positions):
            color = accent if idx == min(3, int(progress * 4)) else paper
            d.ellipse((x, y - 8, x + 22, y + 7), fill=color)
            d.line((x + 20, y, x + 20, y - 55), fill=color, width=4)
        d.line((172, 69, 241, 78), fill=paper, width=5)
    return im


def frame(board, shot, style, progress):
    ink, paper, accent, muted = STYLES[style]
    photo = Image.new("RGB", SIZE, paper)
    d = ImageDraw.Draw(photo)
    boxes = []
    label(d, "MINH HỌA TỔNG HỢP", (42, 108, 450, 137), 19, ink, boxes)
    label(d, board["brand"], (42, 151, 450, 212), 45, ink, boxes)
    d.line((44, 223, 450, 223), fill=muted, width=2)
    label(d, board["product"], (42, 242, 450, 307), 26, ink, boxes)
    photo.paste(illustration(style, shot["visual_mode"], progress), (43, 325))
    # The visible caption is always the role output; discretionary styling cannot alter meaning.
    label(d, shot["caption"], (42, 574, 450, 731), 33, ink, boxes)
    return photo, boxes


def render(source, destination, style):
    if source.stat().st_size > 192_000:
        raise ValueError("Source exceeds the preview limit")
    raw = source.read_bytes()
    board = json.loads(raw)
    duration = board["duration_seconds"]
    if board["version"] != "amc.storyboard/1" or type(duration) is not int or not 1 <= duration <= 32:
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
        placement = None
        for t in range(end - starts_at):
            picture, placement = frame(board, shot, style, t / max(1, end - starts_at - 1))
            frames.append(picture)
        placements.append({"from_s": starts_at, "to_s": end, "visual_mode": shot["visual_mode"], "glyph_boxes": placement})
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
        "source_file": source.name,
        "source_sha256": sha256(raw).hexdigest(),
        "renderer": "amc/storyboard-preview/1",
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
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    (destination / "render.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf8")
    return receipt


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("destination", type=Path)
    cli.add_argument("--style", choices=STYLES, required=True, help="Illustration direction chosen by the editor")
    args = cli.parse_args()
    render(args.source, args.destination, args.style)
