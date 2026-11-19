#!/usr/bin/env python3
"""Generate the twelve stable T4 capture screens from the executable JSON contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 720, 1280
FONT = ROOT / "assets/fonts/DejaVuSans.ttf"
BOLD = ROOT / "assets/fonts/DejaVuSans-Bold.ttf"
CREAM = (247, 240, 229)
INK = (31, 25, 23)
MUTED = (104, 89, 80)
RED = (202, 67, 43)
GOLD = (224, 153, 59)
GREEN = (52, 116, 87)
DARK = (22, 17, 17)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=selected_font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    selected_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int] | str,
    max_width: int,
    line_gap: int = 5,
    max_lines: int | None = None,
) -> int:
    lines = wrap(draw, text, selected_font, max_width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=selected_font) > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    y = xy[1]
    step = selected_font.size + line_gap
    for line in lines:
        draw.text((xy[0], y), line, font=selected_font, fill=fill)
        y += step
    return y


def center_text(draw: ImageDraw.ImageDraw, y: int, text: str, selected_font: ImageFont.FreeTypeFont, fill: tuple[int, int, int] | str = "white") -> None:
    width = draw.textlength(text, font=selected_font)
    draw.text(((W - width) / 2, y), text, font=selected_font, fill=fill)


def gradient_background(scene_index: int) -> Image.Image:
    palettes = [
        ((38, 22, 20), (124, 61, 39)),
        ((28, 34, 31), (91, 100, 70)),
        ((34, 24, 30), (128, 65, 67)),
        ((24, 22, 24), (83, 58, 44)),
    ]
    top, bottom = palettes[scene_index - 1]
    image = Image.new("RGB", (W, H), top)
    px = image.load()
    for y in range(H):
        q = y / max(1, H - 1)
        for x in range(W):
            glow = max(0.0, 1.0 - math.hypot((x - W * 0.55) / W, (y - H * 0.38) / H) * 1.8)
            px[x, y] = tuple(
                max(0, min(255, int(top[c] * (1 - q) + bottom[c] * q + glow * (16 if c != 2 else 10))))
                for c in range(3)
            )
    return image


def draw_person(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float, shirt: tuple[int, int, int], skin: tuple[int, int, int] = (173, 112, 78)) -> None:
    r = int(34 * scale)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=skin)
    draw.rounded_rectangle((cx - int(62 * scale), cy + int(30 * scale), cx + int(62 * scale), cy + int(175 * scale)), radius=int(35 * scale), fill=shirt)


def draw_scene_art(image: Image.Image, scene_index: int) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    # Warm bokeh lights shared by all four previews.
    for i in range(14):
        x = 36 + (i * 109) % 680
        y = 95 + (i * 67) % 420
        r = 7 + (i % 4) * 3
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 197, 92, 75))
    if scene_index == 1:
        draw.rounded_rectangle((95, 100, 475, 800), radius=18, fill=(55, 34, 27, 220), outline=(236, 171, 88, 190), width=5)
        draw.rectangle((145, 155, 425, 755), fill=(91, 60, 44, 220))
        draw.rectangle((274, 155, 292, 755), fill=(45, 29, 24, 220))
        draw.ellipse((375, 445, 391, 461), fill=(236, 171, 88, 255))
        draw_person(draw, 545, 475, 1.25, (238, 231, 215, 255), (132, 82, 58, 255))
        draw.arc((492, 414, 598, 510), 15, 165, fill=(255, 245, 232, 255), width=5)
    elif scene_index == 2:
        draw_person(draw, 565, 330, 1.05, (232, 226, 212, 255), (146, 91, 66, 255))
        draw.rounded_rectangle((118, 570, 605, 700), radius=35, fill=(67, 42, 35, 255), outline=(225, 178, 110, 220), width=4)
        draw.ellipse((175, 505, 395, 685), fill=(228, 218, 199, 255), outline=(255, 245, 229, 255), width=5)
        draw.ellipse((214, 536, 357, 650), fill=(185, 85, 48, 255))
        draw.ellipse((243, 555, 330, 625), fill=(232, 162, 54, 255))
        draw.line((470, 535, 590, 470), fill=(146, 91, 66, 255), width=27)
    elif scene_index == 3:
        draw_person(draw, 500, 295, 1.45, (235, 221, 208, 255), (160, 98, 72, 255))
        draw.arc((430, 230, 570, 365), 20, 160, fill=(255, 244, 228, 255), width=5)
        draw.ellipse((110, 630, 515, 850), fill=(229, 219, 201, 255), outline=(255, 248, 234, 255), width=5)
        draw.ellipse((188, 674, 435, 810), fill=(141, 91, 45, 255))
        draw.line((370, 580, 490, 450), fill=(225, 225, 220, 255), width=9)
        draw.line((490, 450, 510, 430), fill=(225, 225, 220, 255), width=8)
        draw.ellipse((500, 420, 535, 452), fill=(214, 132, 65, 255))
    else:
        for x, y, s, shirt in [
            (170, 390, 0.85, (229, 219, 205, 255)),
            (355, 350, 0.95, (81, 104, 79, 255)),
            (540, 400, 0.82, (155, 68, 54, 255)),
        ]:
            draw_person(draw, x, y, s, shirt)
        draw.ellipse((65, 590, 655, 910), fill=(76, 46, 35, 255), outline=(206, 144, 75, 220), width=5)
        for x, y in [(210, 700), (360, 665), (500, 735)]:
            draw.ellipse((x - 70, y - 40, x + 70, y + 40), fill=(231, 218, 195, 255))
            draw.ellipse((x - 45, y - 25, x + 45, y + 25), fill=(183, 89, 48, 255))


def preview(scene_index: int, dim: int = 0) -> Image.Image:
    image = gradient_background(scene_index).convert("RGBA")
    draw_scene_art(image, scene_index)
    if dim:
        shade = Image.new("RGBA", (W, H), (0, 0, 0, dim))
        image = Image.alpha_composite(image, shade)
    return image.convert("RGB")


def pill(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fill: tuple[int, int, int, int], selected_font: ImageFont.FreeTypeFont) -> None:
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=fill)
    tw = draw.textlength(text, font=selected_font)
    th = selected_font.size
    draw.text((box[0] + (box[2] - box[0] - tw) / 2, box[1] + (box[3] - box[1] - th) / 2 - 2), text, font=selected_font, fill="white")


def guide_screen(screen: dict, scene: dict, guide: dict) -> Image.Image:
    image = preview(screen["scene_index"], dim=75).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((0, 315, W, H + 40), radius=34, fill=(*CREAM, 255))
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)
    pill(draw, (25, 24, 188, 72), f"SCÈNE {screen['scene_index']}/4", (16, 13, 13, 205), font(22, True))
    pill(draw, (W - 165, 24, W - 25, 72), f"{scene['secondes']} S", (160, 52, 34, 235), font(22, True))
    draw.text((38, 350), scene["titre"], font=font(38, True), fill=INK)
    y = draw_wrapped(draw, (38, 402), scene["consigne"], font(20), INK, W - 76, line_gap=4, max_lines=4)
    y += 12
    draw.text((38, y), "À FILMER", font=font(17, True), fill=GREEN)
    y += 27
    for item in scene["a_filmer"]:
        draw.ellipse((42, y + 7, 50, y + 15), fill=GREEN)
        y = draw_wrapped(draw, (60, y), item, font(16), INK, W - 100, line_gap=2, max_lines=2) + 4
    y += 4
    draw.text((38, y), "À ÉVITER", font=font(17, True), fill=RED)
    y += 27
    for item in scene["a_eviter"]:
        draw.line((42, y + 11, 51, y + 20), fill=RED, width=3)
        draw.line((51, y + 11, 42, y + 20), fill=RED, width=3)
        y = draw_wrapped(draw, (60, y), item, font(15), MUTED, W - 100, line_gap=2, max_lines=2) + 3
    y += 5
    draw.rounded_rectangle((34, y, W - 34, y + 76), radius=18, fill=(236, 222, 201), outline=(216, 194, 164), width=2)
    draw.text((53, y + 10), "GESTE CLÉ", font=font(14, True), fill=(124, 77, 49))
    draw_wrapped(draw, (53, y + 31), scene["ce_que_tu_dois_faire"], font(14), INK, W - 106, line_gap=2, max_lines=2)
    footer_y = 1110
    draw_wrapped(draw, (38, footer_y), guide["mention_langues_commune"], font(13), MUTED, W - 76, line_gap=2, max_lines=2)
    draw.rounded_rectangle((34, 1182, W - 34, 1250), radius=24, fill=RED)
    label = guide["bouton_principal"]
    tw = draw.textlength(label, font=font(22, True))
    draw.text(((W - tw) / 2, 1203), label, font=font(22, True), fill="white")
    return image.convert("RGB")


def recording_screen(screen: dict, scene: dict) -> Image.Image:
    image = preview(screen["scene_index"], dim=20).convert("RGBA")
    draw = ImageDraw.Draw(image)
    pill(draw, (25, 24, 188, 72), f"SCÈNE {screen['scene_index']}/4", (8, 8, 8, 195), font(22, True))
    draw.rounded_rectangle((W - 145, 24, W - 25, 72), radius=24, fill=(166, 22, 20, 240))
    draw.ellipse((W - 129, 42, W - 115, 56), fill="white")
    draw.text((W - 103, 36), "REC", font=font(24, True), fill="white")
    elapsed = scene["secondes"] / 2
    prompt = next((p["text"] for p in scene["recording_prompts"] if p["from_ms"] <= elapsed * 1000 < p["to_ms"]), scene["recording_prompts"][-1]["text"])
    draw.rounded_rectangle((44, H - 310, W - 44, H - 220), radius=26, fill=(8, 8, 8, 186))
    center_text(draw, H - 282, prompt, font(24, True))
    timer = f"0:{int(elapsed):02d} / 0:{scene['secondes']:02d}"
    center_text(draw, H - 174, timer, font(48, True))
    x0, x1, y = 44, W - 44, H - 92
    draw.rounded_rectangle((x0, y, x1, y + 14), radius=7, fill=(255, 255, 255, 100))
    draw.rounded_rectangle((x0, y, x0 + (x1 - x0) // 2, y + 14), radius=7, fill=RED)
    center_text(draw, H - 53, "VERTICAL · ARRÊT AUTOMATIQUE", font(16, True), fill=(244, 238, 229))
    return image.convert("RGB")


def review_screen(screen: dict, scene: dict) -> Image.Image:
    image = preview(screen["scene_index"], dim=10).convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, W, 145), fill=(9, 8, 8, 205))
    od.rounded_rectangle((0, 690, W, H + 30), radius=36, fill=(24, 19, 18, 244))
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)
    center_text(draw, 31, f"PRISE {screen['scene_index']} · 0:{scene['secondes']:02d}", font(27, True))
    # Simple speaker symbol — no platform-dependent emoji.
    draw.polygon([(286, 92), (300, 92), (318, 78), (318, 116), (300, 102), (286, 102)], fill=(235, 229, 220))
    draw.arc((311, 82, 344, 112), -50, 50, fill=(235, 229, 220), width=3)
    draw.text((355, 83), "SON ACTIVÉ", font=font(17, True), fill=(235, 229, 220))
    y = 735
    y = draw_wrapped(draw, (38, y), scene["review_question"], font(25, True), "white", W - 76, line_gap=5, max_lines=3) + 17
    for item in scene["review_checks"]:
        draw.ellipse((42, y + 5, 60, y + 23), outline=(93, 186, 135), width=3)
        draw.line((47, y + 15, 52, y + 20), fill=(93, 186, 135), width=3)
        draw.line((52, y + 20, 59, y + 9), fill=(93, 186, 135), width=3)
        y = draw_wrapped(draw, (72, y), item, font(17), (235, 228, 219), W - 112, line_gap=3, max_lines=2) + 9
    draw.rounded_rectangle((34, 1145, 255, 1225), radius=24, fill=(68, 60, 57), outline=(225, 214, 201), width=2)
    draw.text((78, 1171), "REFAIRE", font=font(23, True), fill="white")
    draw.rounded_rectangle((275, 1145, W - 34, 1225), radius=24, fill=RED)
    positive = scene["positive_action"]
    pf = font(21 if screen["scene_index"] < 4 else 19, True)
    tw = draw.textlength(positive, font=pf)
    draw.text((275 + (W - 34 - 275 - tw) / 2, 1172), positive, font=pf, fill="white")
    return image.convert("RGB")


def generate(flow: dict, guide: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenes = guide["scenes"]
    records: list[dict] = []
    expected_states = ["A_GUIDE", "B_RECORDING", "C_REVIEW"] * 4
    if [screen["state"] for screen in flow["screens"]] != expected_states:
        raise ValueError("The flow must expose A/B/C for each of four scenes")
    for screen in flow["screens"]:
        scene = scenes[screen["scene_index"] - 1]
        if screen["state"] == "A_GUIDE":
            image = guide_screen(screen, scene, guide)
        elif screen["state"] == "B_RECORDING":
            image = recording_screen(screen, scene)
        else:
            image = review_screen(screen, scene)
        destination = output_dir / f"{screen['screen_id']}.png"
        image.save(destination, optimize=True)
        records.append({
            "screen_number": screen["ordinal"],
            "scene": screen["scene_index"],
            "state": screen["state"],
            "screen_id": screen["screen_id"],
            "file": destination.name,
            "size": [W, H],
            "sha256": sha256(destination),
            "json_binding": f"config/T4_CAPTURE_FLOW_V1_0_0.json#/screens/{screen['ordinal'] - 1}"
        })

    tw, th, pad, header = 270, 480, 22, 86
    board = Image.new("RGB", (3 * tw + 4 * pad, 4 * th + 5 * pad + header), (235, 227, 216))
    draw = ImageDraw.Draw(board)
    draw.text((pad, 18), "T4 — EXACTEMENT 12 ÉCRANS STABLES", font=font(28, True), fill=(42, 32, 28))
    draw.text((pad, 56), "4 scènes × A Guide · B Enregistrement · C Validation", font=font(17), fill=(94, 76, 65))
    for index, record in enumerate(records):
        row, col = divmod(index, 3)
        x = pad + col * (tw + pad)
        y = header + pad + row * (th + pad)
        screen_image = Image.open(output_dir / record["file"]).resize((tw, th), Image.Resampling.LANCZOS)
        board.paste(screen_image, (x, y))
    board_path = output_dir / "T4_PLANCHE_12_ECRANS.png"
    board.save(board_path, optimize=True)
    manifest = {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "status": "owner_directed_implementation_proof",
        "sources": {
            "questions": "form/questions_T4.json",
            "guide": "capture-guide/consignes_T4.json",
            "capture_flow": "config/T4_CAPTURE_FLOW_V1_0_0.json"
        },
        "stable_screen_count": 12,
        "states": ["A_GUIDE", "B_RECORDING", "C_REVIEW"],
        "screens": records,
        "board": board_path.name,
        "board_size": list(board.size),
        "board_sha256": sha256(board_path),
        "external_media_used": False,
        "font_files": ["assets/fonts/DejaVuSans.ttf", "assets/fonts/DejaVuSans-Bold.ttf"]
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flow", type=Path, default=ROOT / "config/T4_CAPTURE_FLOW_V1_0_0.json")
    parser.add_argument("--guide", type=Path, default=ROOT / "capture-guide/consignes_T4.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "ui-screens")
    args = parser.parse_args()
    flow = json.loads(args.flow.read_text(encoding="utf-8"))
    guide = json.loads(args.guide.read_text(encoding="utf-8"))
    manifest = generate(flow, guide, args.output_dir)
    print(f"T4_UI_12_SCREENS_OK {manifest['board']} {manifest['board_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
