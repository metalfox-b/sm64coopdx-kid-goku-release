"""The pictures compare-face.mjs makes (run through it).

  compare_face.py front NAME OUT_DIR              NAME's art from the front, beside happy's, with his eye line and chin ruled across
  compare_face.py sheets NAME CAPTURE FRAMES OUT_DIR [FRAME [BOX]]  NAME beside its frame, and in a row with passed faces
"""
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ART = os.path.join(ROOT, "art", "faces")
EYE = {"relaxed": 1, "half": 2, "closed": 3, "determined": 4, "shout": 5, "surprised": 6, "happy": 7, "dead": 8, "blink_half": 9, "blink": 10, "smile": 11,
       "grit": 12, "fierce": 13, "yell": 14, "hit": 15, "cheer": 16, "grin": 17,
       "yell_left": 18, "yell_right": 19}
BOX = (650, 270, 1290, 910)
EYE_SPACING, EYE_DOWN = 170 / 640, (600 - 270) / 640
ROW = ("happy", "determined", "surprised", "closed")
EYE_Y, CHIN_Y = 660 - .21 * 840, 660 + .045 * 840


def front(name, out):
    from faces import render
    sheet = Image.new("RGB", (1610, 800), "#fcd8ca")
    for k, n in enumerate(("happy", name)):
        art = render(os.path.join(ART, f"{n}.svg"))
        sheet.paste(art, (k * 810, 0), art)
    d = ImageDraw.Draw(sheet)
    for y in (EYE_Y, CHIN_Y):
        d.line((0, y, 1610, y), fill="#00a0ff")
    d.rectangle((800, 0, 809, 800), fill="white")
    path = os.path.join(out, "front.png")
    sheet.save(path)
    print("front:", path)


def frame_box(name, frames, frame, box):
    """Its frame, and the crop of it at the same scale as the game's, from where trace_faces.py has its eyes."""
    source = open(os.path.join(ROOT, "scripts", "trace_faces.py")).read()
    m = re.search(rf'Face\("{name}", "([^"]+)", \(([\d.]+), ([\d.]+)\), \(([\d.]+), ([\d.]+)\)', source)
    path = os.path.join(frames, frame or m[1]) if frame or m else None
    if not path:
        raise SystemExit(f"{name}: can't find its frame in trace_faces.py; pass --frame")
    im = Image.open(path).convert("RGB")
    im = im.resize((900, round(im.height * 900 / im.width)), Image.LANCZOS)
    if box:
        return im, box
    if not m:
        return im, (0, 0, 900, 900)
    rx, ry, lx, ly = (float(m[k]) for k in (2, 3, 4, 5))
    side = math.hypot(lx - rx, ly - ry) / EYE_SPACING
    x0, y0 = (rx + lx) / 2 - side / 2, (ry + ly) / 2 - side * EYE_DOWN
    return im, tuple(round(v) for v in (x0, y0, x0 + side, y0 + side))


def sheets(name, capture, frames, out, frame, box):
    shots = {s: re.findall(r"file '(.+)'", open(os.path.join(capture, f"{s}.txt")).read()) for s in ("faces-close", "faces-quarter")}

    def still(n, shot="faces-close"):
        return Image.open(shots[shot][(EYE[n] - 1) * 20 + 14]).convert("RGB").crop(BOX)
    im, box = frame_box(name, frames, frame, box)
    beside = Image.new("RGB", (1290, 640), "white")
    beside.paste(im.crop(box).resize((640, 640), Image.LANCZOS), (0, 0))
    beside.paste(still(name), (650, 0))
    still(name).save(os.path.join(out, "crop.png"))
    path = os.path.join(out, "beside-frame.png")
    beside.save(path)
    print("beside its frame:", path)
    row = [n for n in ROW if n != name]
    sheet = Image.new("RGB", (420 * (len(row) + 2), 420))
    tiles = [still(n) for n in row] + [still(name), still(name, "faces-quarter")]
    for k, tile in enumerate(tiles):
        sheet.paste(tile.resize((420, 420), Image.LANCZOS), (k * 420, 0))
    path = os.path.join(out, "with-passed.jpg")
    sheet.save(path, quality=92)
    print("with passed faces:", path)
    others = [n for n in ("happy", "determined", "surprised", "closed", "relaxed") if n != name][:4]
    row = others + [name]
    random.shuffle(row)
    blind = Image.new("RGB", (2000, 400))
    for k, n in enumerate(row):
        blind.paste(still(n).resize((400, 400), Image.LANCZOS), (k * 400, 0))
    folder = os.path.join(out, "blind")
    os.makedirs(os.path.join(folder, "key"), exist_ok=True)
    blind.save(os.path.join(folder, "row.jpg"), quality=92)
    with open(os.path.join(folder, "key", "key.txt"), "w") as f:
        f.write(f"{name} is at position {row.index(name) + 1}\n")
    print("blind reviewer's row (docs/faces.md):", os.path.join(folder, "row.jpg"))


if __name__ == "__main__":
    if sys.argv[1] == "front":
        front(sys.argv[2], sys.argv[3])
    else:
        box = tuple(int(v) for v in sys.argv[7].split(",")) if len(sys.argv) > 7 else None
        sheets(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], (sys.argv[6] or None) if len(sys.argv) > 6 else None, box)
