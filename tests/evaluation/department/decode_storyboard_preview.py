"""Seek each exported scene in Chromium and save the actual decoded frames for inspection."""

import argparse
from base64 import b64decode, b64encode
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]


def verify(folder, executable=None):
    receipt = json.loads((folder / "render.json").read_bytes())
    media = (folder / "preview.webm").read_bytes()
    assert receipt["files"]["preview.webm"] == sha256(media).hexdigest()
    samples = []
    times = [shot["from_s"] + 0.5 for shot in receipt["shots"]]
    motions = [i for i, shot in enumerate(receipt["shots"]) if shot.get("illustration") in {"removable_divider", "pulse_strength", "session_selection"}]
    extra_times = [receipt["shots"][i]["to_s"] - 0.5 for i in motions]
    with sync_playwright() as pw:
        with pw.chromium.launch(executable_path=executable) as browser:
            browser_version = browser.version
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.set_content('<video id="v" muted preload="auto"></video>')
            # A fully local Blob also permits seeking on machines without an HTTP range server.
            page.evaluate(
                """data => {
                const bytes = Uint8Array.from(atob(data), c => c.charCodeAt(0));
                v.src = URL.createObjectURL(new Blob([bytes], {type:'video/webm'}));
            }""",
                b64encode(media).decode("ascii"),
            )
            page.wait_for_function("v.readyState >= 2")
            actual = page.evaluate("() => ({width:v.videoWidth,height:v.videoHeight,duration:v.duration})")
            assert [actual["width"], actual["height"]] == receipt["size"]
            assert abs(actual["duration"] - receipt["duration_seconds"]) <= 0.01
            for time in times + extra_times:
                page.evaluate("time => {v.currentTime=time}", time)
                page.wait_for_function("time => !v.seeking && v.readyState >= 2 && Math.abs(v.currentTime-time)<0.05", arg=time)
                frame = page.evaluate("""() => {const c=document.createElement('canvas');
                    c.width=v.videoWidth;c.height=v.videoHeight;
                    c.getContext('2d').drawImage(v,0,0);return c.toDataURL('image/png').split(',')[1]}""")
                samples.append(Image.open(BytesIO(b64decode(frame))).convert("RGB"))
    end_frames, samples = samples[len(times) :], samples[: len(times)]
    motion_receipts = []
    for i, end, time in zip(motions, end_frames, extra_times, strict=True):
        # Check the decoded illustration itself. Caption identity cannot make a static diagram appear animated.
        region = (43, 325, 452, 548)
        before = sha256(samples[i].crop(region).tobytes()).hexdigest()
        after = sha256(end.crop(region).tobytes()).hexdigest()
        assert before != after
        motion_receipts.append({"from_s": times[i], "to_s": time, "first_art_sha256": before, "last_art_sha256": after})
    assert len({sha256(im.tobytes()).hexdigest() for im in samples}) == len(times), "Two scenes decode to one identical frame"
    # Pixel differences in the decoded border are allowed for VP8 compression; all required content stays inside the inset.
    x0, y0, x1, y1 = receipt["safe_rect"]

    def luma(rgb):
        return sum(c * k for c, k in zip(rgb, (0.2126, 0.7152, 0.0722), strict=True))

    for im in samples:
        bg = luma(im.getpixel((1, 1)))
        for x, y in ((x0 - 8, y0 - 8), (x1 + 8, y1 + 8), (x0 - 8, (y0 + y1) // 2), (x1 + 8, (y0 + y1) // 2)):
            assert abs(luma(im.getpixel((x, y))) - bg) < 8
    width = 216
    height = width * 16 // 9
    sheet = Image.new("RGB", ((width + 12) * len(samples) + 12, height + 54), "#F6F4EE")
    d = ImageDraw.Draw(sheet)
    face = ImageFont.truetype(str(ROOT / "app/production_media/BeVietnamPro-SemiBold.ttf"), 15)
    for i, (sample, time) in enumerate(zip(samples, times, strict=True)):
        x = 12 + i * (width + 12)
        sheet.paste(sample.resize((width, height), Image.Resampling.LANCZOS), (x, 12))
        d.text((x, height + 20), f"{time:g} s", fill="#192C2E", font=face)
    sheet.save(folder / "decoded-shots.png")
    report = {
        "browser": "Chromium",
        "version": browser_version,
        "video_sha256": sha256(media).hexdigest(),
        "decoded": actual,
        "times_s": times,
        "motion_samples": motion_receipts,
        "sample_sha256_rgb": [sha256(im.tobytes()).hexdigest() for im in samples],
        "contact_sheet_sha256": sha256((folder / "decoded-shots.png").read_bytes()).hexdigest(),
    }
    (folder / "decoder.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--chromium", help="Optional path to an installed Chrome/Chromium executable")
    cli = parser.parse_args()
    print(json.dumps(verify(cli.folder, cli.chromium), indent=2))
