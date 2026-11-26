"""Produce bounded local artwork, editable scene instructions, captions and VP8 video."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont, __version__, features

FONT = Path(__file__).with_name("production_media") / "BeVietnamPro-SemiBold.ttf"
PALETTES = {"forest": ("#123D31", "#E5F39A", "#FCF9ED"), "cobalt": ("#183965", "#FFB890", "#F9F4E9")}
VARIANTS = {"portrait": (720, 900), "landscape": (960, 540), "square": (720, 720)}


def encoded(im, fmt, **opts):
    output = BytesIO()
    im.save(output, fmt, **opts)
    return output.getvalue()


def text_lines(draw, value, font, width):
    lines, line = [], ""
    for word in value.split():
        if draw.textlength(word, font=font) > width:
            return []
        candidate = (line + " " + word).strip()
        if line and draw.textlength(candidate, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return [*lines, line] if line else []


def block(draw, value, box, size, color):
    x, y, width, height = box
    for px in range(size, 10, -1):
        font = ImageFont.truetype(str(FONT), px, layout_engine=ImageFont.Layout.BASIC)
        lines = text_lines(draw, value, font, width)
        if lines and len(lines) * (px * 1.5) <= height:
            for i, line in enumerate(lines):
                draw.text((x, y + i * px * 1.5), line, font=font, fill=color, anchor="lt")
            return
    raise HTTPException(422, "The approved copy exceeds this safe area. Edit and approve a shorter version.")


def colors(options):
    selected = options.get("colors") or PALETTES[options["palette"]]

    def luminance(color):
        rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        return sum((n / 12.92 if n <= 0.04045 else ((n + 0.055) / 1.055) ** 2.4) * w for n, w in zip(rgb, (0.2126, 0.7152, 0.0722)))

    ink, accent, paper = map(luminance, selected)
    if any((max(ink, bg) + 0.05) / (min(ink, bg) + 0.05) < 4.5 for bg in (accent, paper)):
        raise HTTPException(422, "The selected text and CTA colours need contrast of at least 4.5:1.")
    return selected


def illustration(selected, motif):
    bg, accent, paper = selected
    im = Image.new("RGB", (720, 450), bg)
    pen = ImageDraw.Draw(im)
    if motif == "arches":
        for i in range(8):
            pen.arc((35 + i * 26, -80 + i * 17, 685 - i * 26, 610 - i * 17), 170, 395, fill=accent if i % 3 else paper, width=10)
    else:
        for i in range(10):
            x = i * 80 - 140
            pen.polygon([(x, 410), (x + 260, 35), (x + 327, 35), (x + 65, 410)], fill=accent if i % 3 else paper)
    return im


def canvas(size, art, master, *, caption=None):
    width, height = size
    bg, accent, paper = master["colors"]
    im = Image.new("RGB", size, paper)
    pen = ImageDraw.Draw(im)
    pad = round(min(size) * 0.065)
    art_h = int(height * 0.39)
    upper = master["layout"] == "art_first"
    top = pad if upper else height - pad - art_h
    available_w = width - 2 * pad
    # Fit the whole source by center cropping only the abstract illustration.
    from PIL import ImageOps

    im.paste(ImageOps.fit(art, (available_w, art_h), method=Image.Resampling.LANCZOS), (pad, top))
    text_top = top + art_h + pad // 2 if upper else pad
    text_end = height - pad if upper else top - pad // 2
    text_h = text_end - text_top
    pen.rectangle((pad, text_top, pad + max(16, available_w // 9), text_top + 3), fill=bg)
    block(pen, caption or master["headline"], (pad, text_top + 8, available_w, int(text_h * 0.64) - 8), max(20, min(size) // 11), bg)
    action_y = text_top + int(text_h * 0.68)
    pen.rounded_rectangle((pad, action_y, width - pad, text_end), radius=max(5, pad // 4), fill=bg)
    block(pen, master["cta"], (pad + 12, action_y + 5, available_w - 24, text_end - action_y - 7), max(15, min(size) // 25), accent)
    return im


def ebml(tag, payload):
    # Minimal finite-length EBML, every video frame is an independent VP8 keyframe.
    n = 1
    while len(payload) >= (1 << (7 * n)) - 1:
        n += 1
    return bytes.fromhex(tag) + ((1 << (7 * n)) | len(payload)).to_bytes(n, "big") + payload


def integer(tag, n):
    return ebml(tag, n.to_bytes(max(1, (n.bit_length() + 7) // 8), "big"))


def webm(frames, seconds=2):
    width, height = frames[0].size
    header = b"".join(
        [integer("4286", 1), integer("42f7", 1), integer("42f2", 4), integer("42f3", 8), ebml("4282", b"webm"), integer("4287", 2), integer("4285", 2)]
    )
    info = integer("2ad7b1", 1000000) + ebml("4d80", b"AMC") + ebml("5741", b"AMC") + ebml("4489", struct.pack(">d", len(frames) * seconds * 1000))
    video = integer("b0", width) + integer("ba", height)
    track = integer("d7", 1) + integer("73c5", 1) + integer("83", 1) + ebml("86", b"V_VP8") + integer("23e383", seconds * 1000000000) + ebml("e0", video)
    blocks = []
    for i, frame in enumerate(frames):
        data = encoded(frame, "WEBP", quality=80, method=4)
        if data[12:16] != b"VP8 ":
            raise RuntimeError("Expected a standalone lossy VP8 keyframe from WebP encoder")
        size = int.from_bytes(data[16:20], "little")
        blocks.append(ebml("a3", b"\x81" + struct.pack(">hB", i * seconds * 1000, 128) + data[20 : 20 + size]))
    segment = ebml("1549a966", info) + ebml("1654ae6b", ebml("ae", track)) + ebml("1f43b675", integer("e7", 0) + b"".join(blocks))
    return ebml("1a45dfa3", header) + ebml("18538067", segment)


def produce(groups, projection, options):
    copy = groups["copy"]
    selected = colors(options)
    master = {
        "contract": "amc.creative-master/1",
        **options,
        "colors": selected,
        "palette": "custom" if options.get("colors") else options["palette"],
        "headline": copy["headline"],
        "cta": copy["call_to_action"],
        "brief": groups["creative_brief"],
        "brand_guideline_digest": projection.get("brand_guidelines", {}).get("digest"),
        "variations": VARIANTS,
        "safe_inset_percent": 6.5,
        "typeface": "Be Vietnam Pro SemiBold",
    }
    captions = [copy["headline"], copy["value_proposition"], copy["call_to_action"]]
    scenes = [{"from": i * 2, "to": i * 2 + 2, "caption": caption} for i, caption in enumerate(captions)]
    master["scenes"] = scenes
    return master, render(master)


def render(master):
    """Rebuild the same byte formats from an editable master without database access."""
    from re import fullmatch

    if master.get("contract") != "amc.creative-master/1" or master.get("motif") not in ("arches","planes") or master.get("layout") not in ("art_first","text_first"):
        raise ValueError("Unsupported master, source illustration or layout")
    selected = master.get("colors",[])
    if len(selected)!=3 or not all(isinstance(c,str) and fullmatch(r"#[a-fA-F0-9]{6}",c) for c in selected):
        raise ValueError("Supply three RGB design colours")
    colors(master)  # The offline renderer enforces the same contrast requirement as Studio.
    scenes = master["scenes"]
    if len(scenes)!=3 or any(s.get("from")!=2*i or s.get("to")!=2*i+2 for i,s in enumerate(scenes)):
        raise ValueError("This renderer supports three consecutive two-second scenes")
    captions = [s["caption"] for s in scenes]
    if not all(isinstance(s,str) and 0<len(s.strip())<=5000 for s in [*captions,master["cta"],master["headline"]]):
        raise ValueError("Provide bounded, nonempty copy for each scene")
    art = illustration(selected, master["motif"])
    source = encoded(art, "PNG", compress_level=6)
    master.update(variations=VARIANTS,safe_inset_percent=6.5,typeface="Be Vietnam Pro SemiBold",
                  source={"file":"source.png","sha256":sha256(source).hexdigest(),"type":"AMC original synthetic geometry",
                          "rights":"AMC synthetic source for internal sandbox use. No external media or photography."},
                  renderer={"engine": "Pillow", "version": __version__, "freetype": features.version("freetype2"), "webp": features.version("webp")})
    files = {"source.png": ("image/png", source)}
    for variant, size in VARIANTS.items():
        files[variant + ".png"] = ("image/png", encoded(canvas(size, art, master), "PNG", compress_level=6))
    frames = [canvas((640, 360), art, master, caption=caption) for caption in captions]
    files["preview.webm"] = ("video/webm", webm(frames))
    vtt = "WEBVTT\n\n" + "\n\n".join(f"00:00:0{s['from']}.000 --> 00:00:0{s['to']}.000\n{s['caption']}" for s in scenes) + "\n"
    files["captions.vtt"] = ("text/vtt", vtt.encode())
    files["master.json"] = ("application/json", (json.dumps(master, ensure_ascii=False, indent=2) + "\n").encode())
    return files


if __name__ == "__main__":
    import argparse

    cli=argparse.ArgumentParser(description="Render an editable AMC sandbox master into a new directory.")
    cli.add_argument("master",type=Path)
    cli.add_argument("destination",type=Path)
    args=cli.parse_args()
    if args.master.stat().st_size > 160000:
        cli.error("Master exceeds the local editing limit")
    files=render(json.loads(args.master.read_text(encoding="utf8")))
    args.destination.mkdir(parents=True,exist_ok=False)
    for name,(_,data) in files.items():
        (args.destination/name).write_bytes(data)
