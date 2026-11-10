"""Kid Goku's N64 textures from Budokai 3's: every texture box-downscaled to 64 texels or less and quantized to CI4
with the n64-texture skill, and his eight expression faces drawn the way Toriyama draws Kid Goku in the manga and the
1986 anime. Everything stays local.

Usage: python3 scripts/b3_textures.py B3_TEXTURE_DIR OUT_DIR   (needs Pillow)

Writes goku_b3_<part>.ci4.png, goku_face_<expression>.ci4.png and sizes.json. The face textures keep only the top
FACE_COLS x FACE_ROWS of Budokai 3's 256x256 face; b3.py remaps the face's UVs to match.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

QUANTIZE = os.path.expanduser("~/.claude/skills/n64-texture/scripts/quantize_texture.py")
SIZES = {"Belt": "64x32", "Arms": "64x64", "Shirt": "64x64", "Pants": "32x64", "Shoes": "32x32", "Wristband": "32x32",
         "Sole": "16x16", "Hair": "64x64", "Powerpole": "32x32", "Hands": "64x32"}
FACE_ROWS, FACE_COLS = 160, 180
SKIN = (255, 210, 170, 255)
INK = (16, 12, 12, 255)
MOUTH_DARK = (110, 20, 26, 255)
TONGUE = (226, 110, 110, 255)


def sheet(src, name):
    return Image.open(os.path.join(src, f"Kid Goku_{name}.png")).convert("RGBA")


Z = 4
CX = 90
EYE_Y, EYE_W, EYE_H, EYE_GAP = 60, 21, 27, 2
NOSE_Y, MOUTH_Y = 94, 107
WHITE = (255, 255, 255, 255)


def z(*v):
    return [c * Z for c in v]


def eye_boxes():
    for side in (-1, 1):
        cx = CX + side * (EYE_GAP / 2 + EYE_W)
        yield side, cx


def draw_eyes(d, kind):
    for side, cx in eye_boxes():
        x0, y0, x1, y1 = cx - EYE_W, EYE_Y - EYE_H, cx + EYE_W, EYE_Y + EYE_H
        inner = cx - side * EYE_W
        if kind in ("open", "half", "surprised", "determined", "shout"):
            d.ellipse(z(x0, y0, x1, y1), fill=WHITE, outline=INK, width=round(2.5 * Z))
            if kind == "surprised":
                px, py, r = cx - side * 2, EYE_Y, 3.2
            elif kind in ("determined", "shout"):
                px, py, r = cx - side * 6, EYE_Y + 6, 8.5
            else:
                px, py, r = cx - side * 4, EYE_Y + 3, 9.5
            d.ellipse(z(px - r, py - r * 1.15, px + r, py + r * 1.15), fill=INK)
            if r > 4:
                d.ellipse(z(px - side * 2 - 1.8, py - 4.5, px - side * 2 + 1.8, py - 1), fill=WHITE)
            if kind in ("determined", "shout"):
                d.polygon(z(cx + side * (EYE_W + 3), y0 - 6, inner - side * 3, y0 - 6, inner - side * 3, EYE_Y - 6,
                            cx + side * (EYE_W + 3), EYE_Y - 15), fill=SKIN)
                d.line(z(cx + side * (EYE_W + 1), EYE_Y - 15, inner, EYE_Y - 5), fill=INK, width=6 * Z)
            if kind == "half":
                d.rectangle(z(x0 - 2, y0 - 2, x1 + 2, EYE_Y - 2), fill=SKIN)
                d.line(z(x0 + 1, EYE_Y - 2, x1 - 1, EYE_Y - 2), fill=INK, width=4 * Z)
        elif kind == "closed":
            d.arc(z(x0 + 2, EYE_Y - 14, x1 - 2, EYE_Y + 10), 15, 165, fill=INK, width=4 * Z)
        elif kind == "happy":
            d.arc(z(x0 + 2, EYE_Y - 4, x1 - 2, EYE_Y + 22), 195, 345, fill=INK, width=5 * Z)
        elif kind == "dead":
            for k in range(3):
                r = 5 + k * 5
                d.arc(z(cx - r, EYE_Y - r, cx + r, EYE_Y + r), 0 + k * 40, 300 + k * 40, fill=INK, width=2 * Z)


def draw_brows(d, kind):
    for side, cx in eye_boxes():
        outer, inner = cx + side * (EYE_W + 2), cx - side * (EYE_W - 4)
        if kind in ("determined", "shout"):
            continue
        if kind == "surprised":
            y_out, y_in = EYE_Y - EYE_H - 12, EYE_Y - EYE_H - 14
        elif kind in ("happy",):
            y_out, y_in = EYE_Y - EYE_H - 4, EYE_Y - EYE_H - 6
        else:
            y_out, y_in = EYE_Y - EYE_H - 8, EYE_Y - EYE_H - 3
        d.polygon(z(outer + side * 2, y_out - 1, inner, y_in - 5, inner - side * 2, y_in + 4, outer - side * 5,
                    y_out + 5), fill=INK)


def draw_nose(d):
    d.arc(z(CX - 3, NOSE_Y - 3, CX + 3, NOSE_Y + 3), 300, 160, fill=INK, width=2 * Z)


def draw_mouth(d, kind):
    x, y = CX, MOUTH_Y
    if kind == "smile":
        d.arc(z(x - 9, y - 7, x + 9, y + 4), 25, 155, fill=INK, width=3 * Z)
    elif kind == "pout":
        d.line(z(x - 6, y + 1, x - 2, y - 1, x + 2, y + 1, x + 6, y - 1), fill=INK, width=3 * Z, joint="curve")
    elif kind in ("shout", "grin"):
        w, h = (28, 32) if kind == "grin" else (24, 30)
        d.chord(z(x - w, y - h + 6, x + w, y + h), 0, 180, fill=MOUTH_DARK, outline=INK, width=3 * Z)
        d.rectangle(z(x - w + 2, y + 6, x + w - 2, y + 10), fill=WHITE)
        d.line(z(x - w, y + 6, x + w, y + 6), fill=INK, width=3 * Z)
        d.chord(z(x - w * 0.55, y + 10, x + w * 0.55, y + h - 2), 180, 360, fill=TONGUE)
    elif kind == "o":
        d.ellipse(z(x - 7, y - 3, x + 7, y + 13), fill=MOUTH_DARK, outline=INK, width=3 * Z)
    elif kind == "wail":
        d.chord(z(x - 11, y - 8, x + 11, y + 14), 0, 180, fill=MOUTH_DARK, outline=INK, width=3 * Z)


def toriyama(src, eyes, mouth_kind):
    base = sheet(src, "Face")
    ImageDraw.Draw(base).rectangle((CX - 66, 14, CX + 66, 160), fill=SKIN)
    ImageDraw.Draw(base).rectangle((0, 112, 180, 160), fill=SKIN)
    big = Image.new("RGBA", (256 * Z, 160 * Z), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    draw_brows(d, eyes)
    draw_eyes(d, eyes)
    draw_nose(d)
    draw_mouth(d, mouth_kind)
    small = big.resize((256, 160), Image.BOX)
    base.alpha_composite(small, (0, 0))
    return base


def expressions(src):
    return {
        "relaxed": toriyama(src, "open", "smile"),
        "half": toriyama(src, "half", "smile"),
        "closed": toriyama(src, "closed", "smile"),
        "determined": toriyama(src, "determined", "pout"),
        "shout": toriyama(src, "shout", "shout"),
        "surprised": toriyama(src, "surprised", "o"),
        "happy": toriyama(src, "happy", "grin"),
        "dead": toriyama(src, "dead", "wail"),
    }


def quantize(img, dst, size):
    tmp = dst + ".src.png"
    img.save(tmp)
    subprocess.run([sys.executable, QUANTIZE, tmp, dst, "--format", "CI4", "--size", size, "--dither", "none"],
                   check=True, capture_output=True)
    os.remove(tmp)


def main() -> int:
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for part, size in SIZES.items():
        quantize(sheet(src, part), os.path.join(out, f"goku_b3_{part.lower()}.ci4.png"), size)
    for name, img in expressions(src).items():
        quantize(img.crop((0, 0, FACE_COLS, FACE_ROWS)), os.path.join(out, f"goku_face_{name}.ci4.png"), "64x64")
    with open(os.path.join(out, "sizes.json"), "w") as f:
        json.dump({"parts": SIZES, "face_rows": FACE_ROWS, "face_cols": FACE_COLS}, f)
    print("textures:", len(SIZES) + 8)
    return 0


if __name__ == "__main__":
    sys.exit(main())
