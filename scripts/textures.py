"""Draw Kid Goku's textures in code, then quantize each to its N64 format with the n64-texture skill.

Usage: python3 scripts/textures.py  (needs Pillow; writes art/textures/)

goku_eyes_<state>.rgba16.png  32x64, drawn with Mirror S across the face (64x64): eyes, brows and mouth, transparent
                              elsewhere so the baked skin shows through
goku_anime_eyes_<state>.rgba16.png  the same, in the original anime's face: round eyes, small pupils, an open grin
goku_kanji.rgba16.png         32x32: the 亀 kanji in black, transparent elsewhere so the palette's emblem color
                              makes the circle
goku_metal_<light|shade>.rgba16.png  32x32: the metal cap's environment map, a sky-over-ground chrome gradient
"""
from __future__ import annotations

import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "art", "textures")
QUANTIZE = os.path.expanduser("~/.claude/skills/n64-texture/scripts/quantize_texture.py")
INK = (20, 20, 22, 255)
WHITE = (250, 250, 250, 255)
K = 4


def s(*v):
    return [x * K for x in v]


def box(x0, y0, x1, y1):
    return s(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def face(state: str) -> Image.Image:
    """Tenkaichi 3's Kid Goku face, 64x64 (stored as its left half, drawn mirrored): white eyes with black pupils
    under a heavy lash line, thick brows angled down to the nose, a small set mouth. Rows run from above his brows
    (top) to his chin; everything else is transparent so the baked skin shows."""
    img = Image.new("RGBA", (64 * K, 64 * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for side in (-1, 1):
        cx = 32 + side * 13

        def x(v):
            return cx + side * v
        d.polygon(s(x(10.5), 11, x(-8), 17.5, x(-7.5), 22, x(10), 15), fill=INK)
        if state == "open":
            d.ellipse(box(cx - 9.5, 21.5, cx + 9.5, 45), fill=WHITE, outline=INK, width=int(1.3 * K))
            d.ellipse(box(x(-5.4), 27, x(2.0), 42.5), fill=INK)
            d.ellipse(box(x(-1.4), 30, x(0.8), 33), fill=WHITE)
            d.polygon(s(x(11), 18, x(-11), 18, x(-11), 29, x(10.5), 24), fill=(0, 0, 0, 0))
            d.line(s(x(10.5), 24, x(-10.5), 29), fill=INK, width=int(3.2 * K))
        elif state == "half":
            d.ellipse(box(cx - 8, 30, cx + 8, 44), fill=WHITE, outline=INK, width=int(1.3 * K))
            d.line(s(cx - 8.6, 32, cx + 8.6, 32), fill=INK, width=int(3 * K))
            d.chord(box(x(-4.6), 30, x(1.8), 41.5), 0, 180, fill=INK)
        elif state == "closed":
            d.arc(box(cx - 8.6, 26, cx + 8.6, 42), 10, 170, fill=INK, width=int(2.6 * K))
        elif state == "dead":
            d.line(s(cx - 6, 26, cx + 6, 41), fill=INK, width=int(2.4 * K))
            d.line(s(cx + 6, 26, cx - 6, 41), fill=INK, width=int(2.4 * K))
    d.line(s(28.5, 51, 35.5, 51), fill=(110, 36, 26, 255), width=int(1.6 * K))
    return img


def face_anime(state: str) -> Image.Image:
    """The original anime's face, 64x64 like face(): big round white eyes with small pupils looking ahead, short
    brows, and his open grin."""
    img = Image.new("RGBA", (64 * K, 64 * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for side in (-1, 1):
        cx = 32 + side * 13.5

        def x(v):
            return cx + side * v
        d.polygon(s(x(8), 9, x(-6), 12.5, x(-6), 15, x(8), 11.5), fill=INK)
        if state == "open":
            d.ellipse(box(cx - 8.5, 17, cx + 8.5, 37), fill=WHITE, outline=INK, width=int(1.6 * K))
            d.ellipse(box(x(-2.6), 24, x(2.2), 31), fill=INK)
            d.ellipse(box(x(-0.4), 24.6, x(1.2), 26.6), fill=WHITE)
        elif state == "half":
            d.chord(box(cx - 8.5, 17, cx + 8.5, 37), 0, 180, fill=WHITE, outline=INK, width=int(1.6 * K))
            d.line(s(cx - 8.5, 27, cx + 8.5, 27), fill=INK, width=int(2 * K))
            d.chord(box(x(-2.6), 26, x(2.2), 32), 0, 180, fill=INK)
        elif state == "closed":
            d.arc(box(cx - 8, 20, cx + 8, 34), 200, 340, fill=INK, width=int(2.4 * K))
        elif state == "dead":
            d.line(s(cx - 6, 20, cx + 6, 34), fill=INK, width=int(2.4 * K))
            d.line(s(cx + 6, 20, cx - 6, 34), fill=INK, width=int(2.4 * K))
    d.chord(box(23, 44, 41, 60), 0, 180, fill=(96, 22, 20, 255), outline=INK, width=int(1.2 * K))
    d.chord(box(27, 52, 37, 60), 0, 180, fill=(232, 120, 120, 255))
    d.line(s(23.5, 52, 40.5, 52), fill=INK, width=int(1.2 * K))
    return img


def kanji() -> Image.Image:
    """亀, drawn in thick strokes on a 32x32 grid."""
    img = Image.new("RGBA", (32 * K, 32 * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = int(2.4 * K)

    def line(*pts):
        d.line(s(*pts), fill=INK, width=w, joint="curve")
    line(13, 2.5, 9.5, 7)
    line(11, 4.5, 20, 4.5, 17.5, 8)
    d.rectangle(s(8.5, 8.5, 23.5, 20), outline=INK, width=w)
    line(8.5, 14.2, 23.5, 14.2)
    line(16, 7, 16, 26.5, 25, 26.5, 25.5, 23)
    return img


def metal(light: bool) -> Image.Image:
    """Chrome: bright sky over a dark horizon band and a mid ground, with a soft highlight."""
    img = Image.new("RGBA", (32 * K, 32 * K))
    d = ImageDraw.Draw(img)
    for y in range(32 * K):
        t = y / (32 * K)
        if t < 0.45:
            v = 235 - 70 * t / 0.45
        elif t < 0.55:
            v = 60
        else:
            v = 110 + 40 * (t - 0.55) / 0.45
        v = v if light else v * 0.6
        d.line((0, y, 32 * K, y), fill=(int(v), int(v), int(v + 8), 255))
    d.ellipse(s(8, 4, 20, 12), fill=(255, 255, 255, 255) if light else (170, 170, 178, 255))
    return img


def quantize(src: Image.Image, name: str, size: str, mirror: bool):
    tmp = os.path.join(OUT, f".{name}.src.png")
    src.save(tmp)
    out = os.path.join(OUT, f"{name}.rgba16.png")
    args = [sys.executable, QUANTIZE, tmp, out, "--format", "RGBA16", "--size", size, "--dither", "none"]
    if mirror:
        args += ["--half-mirror", "x"]
    subprocess.run(args, check=True)
    os.remove(tmp)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for state in ("open", "half", "closed", "dead"):
        quantize(face(state), f"goku_eyes_{state}", "32x64", True)
        quantize(face_anime(state), f"goku_anime_eyes_{state}", "32x64", True)
    quantize(kanji(), "goku_kanji", "32x32", False)
    quantize(metal(True), "goku_metal_light", "32x32", False)
    quantize(metal(False), "goku_metal_shade", "32x32", False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
