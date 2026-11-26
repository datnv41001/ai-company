"""Render preproduction shot boards from the checked editorial revisions using the Studio typeface."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from production_edits import FOLDER

FONT = Path(__file__).resolve().parents[3] / "app/production_media/BeVietnamPro-SemiBold.ttf"
PAPER = "#F7F5EE"
INK = "#162D32"
LINE = "#A1B4B0"
PALE = "#DCEAE2"
ACCENT = "#1F6155"


def font(size):
    return ImageFont.truetype(str(FONT), size)


def paragraph(draw, xy, words, size, width, color=INK):
    x, y = xy
    face = font(size)
    line = ""
    for word in words.split():
        extended = (line + " " + word).strip()
        if draw.textlength(extended, font=face) > width and line:
            draw.text((x, y), line, fill=color, font=face)
            y += size + 6
            line = word
        else:
            line = extended
    draw.text((x, y), line, fill=color, font=face)
    return y + size + 6


def tray(draw, x, y, lifted):
    rim = [(x, y + 42), (x + 208, y + 18), (x + 280, y + 51), (x + 70, y + 78)]
    draw.polygon([rim[3], rim[2], (x + 280, y + 68), (x + 70, y + 96)], fill="#66887F", outline=INK, width=2)
    draw.polygon([rim[0], rim[3], (x + 70, y + 96), (x, y + 60)], fill=LINE, outline=INK, width=2)
    draw.polygon(rim, fill="#BAD2C3", outline=INK, width=3)
    for move in (68, 135):
        up = 17 if lifted and move == 135 else 0
        draw.polygon(
            [(x + move, y + 35 - up), (x + move + 65, y + 68 - up), (x + move + 65, y + 54 - up), (x + move, y + 20 - up)], fill=PALE, outline=INK, width=2
        )
    if lifted:
        draw.line((x + 160, y + 26, x + 160, y + 2), fill=ACCENT, width=3)
        draw.polygon([(x + 154, y + 6), (x + 160, y), (x + 166, y + 6)], fill=ACCENT)
    for dx, dy in ((-68, 34), (-48, 40), (-63, 47), (312, 52), (327, 61), (309, 68)):
        draw.ellipse((x + dx, y + dy, x + dx + 11, y + dy + 6), fill=INK)


def flow(draw, x, y, wait):
    for num, label in enumerate(("Cửa nhận", "Bàn kiểm", "Bàn giao")):
        sx = x + num * 153
        draw.rounded_rectangle((sx, y + 22, sx + 116, y + 71), 6, fill=PALE, outline=INK, width=2)
        draw.text((sx + 58, y + 46), label, font=font(16), fill=INK, anchor="mm")
        if num < 2:
            draw.line((sx + 118, y + 47, sx + 148, y + 47), fill=ACCENT, width=3)
            draw.polygon([(sx + 145, y + 42), (sx + 151, y + 47), (sx + 145, y + 52)], fill=ACCENT)
    if wait:
        draw.text((x + 130, y - 6), "?", font=font(23), fill=ACCENT)
    else:
        draw.rectangle((x + 123, y + 56, x + 141, y + 67), fill="#B38A63", outline=INK)


def paper_form(draw, x, y, labels):
    for idx, label in enumerate(labels):
        yy = y + idx * 27
        draw.text((x, yy), label, fill=INK, font=font(16))
        draw.line((x + 160, yy + 17, x + 375, yy + 17), fill=LINE, width=2)


def board(folder):
    raw = (folder / "edit.json").read_bytes().replace(b"\r\n", b"\n")
    edit = json.loads(raw)
    if edit["revision"] != 2 or len(edit["shots"]) != 5:
        raise ValueError("Review the shot diagrams when the edit changes")
    rfq = edit["case"] == "index-tray"
    modes = ["tray", "divider", "price", "form", "cta"] if rfq else ["route", "wait", "map", "price", "cta"]
    sheet = Image.new("RGB", (1400, 1270), PAPER)
    d = ImageDraw.Draw(sheet)
    d.rectangle((0, 0, 1400, 149), fill=INK)
    d.text((44, 19), "BẢN DỰNG TRƯỚC KHI QUAY   /   V2", font=font(18), fill="#B4D5B9")
    d.text((42, 48), edit["product"], font=font(37), fill=PAPER)
    d.text((44, 106), edit["audience"] + "  ·  Dọc 9:16  ·  " + str(edit["shots"][-1]["end"]) + " giây", font=font(18), fill=PAPER)
    for i, (shot, mode) in enumerate(zip(edit["shots"], modes, strict=True)):
        x = 42 + (i % 2) * 670
        y = 176 + (i // 2) * 350
        d.rounded_rectangle((x, y, x + 644, y + 327), radius=12, fill="#FFFFFF", outline="#CBD5CE", width=2)
        d.text((x + 18, y + 12), f"CẢNH {i + 1}    {shot['start']:02}–{shot['end']:02} giây", font=font(17), fill=ACCENT)
        d.rounded_rectangle((x + 18, y + 47, x + 626, y + 157), radius=7, fill="#EDF3ED")
        if mode in ("tray", "divider"):
            tray(d, x + 168, y + 53, mode == "divider")
        elif mode in ("route", "wait", "map"):
            flow(d, x + 106, y + 63, mode == "wait")
        elif mode == "price":
            d.rounded_rectangle((x + 133, y + 70, x + 512, y + 139), 8, fill=PAPER, outline=INK, width=2)
            d.text((x + 322, y + 101), "Thẻ giá tham khảo", font=font(24), fill=INK, anchor="mm")
        elif mode == "form":
            paper_form(d, x + 130, y + 56, ("Số hộp", "Địa bàn", "Khi nào cần hàng"))
        else:
            d.rounded_rectangle((x + 100, y + 73, x + 542, y + 132), 12, fill=ACCENT)
            d.text((x + 321, y + 101), "Yêu cầu báo giá" if rfq else "Gửi đề nghị khảo sát", font=font(24), fill="white", anchor="mm")
        caption = edit["hooks"]["A"] if i == 0 else shot["caption"]
        bottom = paragraph(d, (x + 18, y + 170), caption, 23, 607)
        bottom = paragraph(d, (x + 18, bottom + 6), shot["picture"], 17, 605, color="#3C5354")
        if bottom > y + 322:
            raise ValueError(f"Overflow in shot {i + 1}")
    x, y = 712, 876
    d.text((x + 17, y + 16), "Biến thể mở đầu", fill=INK, font=font(30))
    h = paragraph(d, (x + 17, y + 76), "A   " + edit["hooks"]["A"], 21, 605)
    h = paragraph(d, (x + 17, h + 14), "B   " + edit["hooks"]["B"], 21, 605)
    paragraph(
        d,
        (x + 17, h + 25),
        "Giữ cùng hình mở đầu, thời lượng, phần thân và CTA. Kiểm phụ đề khi tắt tiếng; đối chiếu giá và điều kiện theo brief trước khi quay.",
        18,
        598,
        color="#3C5354",
    )
    d.text((44, 1230), "Minh họa bố trí cảnh bằng sơ đồ. Đạo cụ và địa điểm thực tế cần được chủ sở hữu cho phép.", font=font(16), fill=INK)
    info = PngImagePlugin.PngInfo()
    info.add_text("edit_sha256", hashlib.sha256(raw).hexdigest())
    sheet.save(folder / "storyboard.png", pnginfo=info)


if __name__ == "__main__":
    for case in ("index-tray", "receipt-map"):
        board(FOLDER / case)
