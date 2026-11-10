"""Sets each motion's film beside the anime frames it follows, one sheet per motion (art/motions.json).

  motion_sheet.py CAPTURE_DIR REFERENCE_DIR OUT_DIR [MOTION,MOTION...] [--picks N]

CAPTURE_DIR is a film from check.mjs --case review --no-clips. Each sheet has a strip of evenly spaced moments, then the frames, each named. Needs Pillow.
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
picks = int(sys.argv[sys.argv.index("--picks") + 1]) if "--picks" in sys.argv else 8
if "--picks" in sys.argv:
    args.remove(str(picks))
capture, reference, out = args[:3]
only = args[3].split(",") if len(args) > 3 else None
motions = json.load(open(os.path.join(ROOT, "art", "motions.json")))["motions"]
os.makedirs(out, exist_ok=True)
try:
    FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
except OSError:
    FONT = ImageFont.load_default()
CELL, HIGH = 400, 300

for name, m in motions.items():
    if only and name not in only:
        continue
    listing = os.path.join(capture, m["shot"] + ".txt")
    if not os.path.exists(listing):
        print(f"{name}: no film of {m['shot']}")
        continue
    files = re.findall(r"file '(.+)'", open(listing).read())
    moments = [files[int((i + 0.5) * len(files) / picks)] for i in range(picks)]
    frames = []
    for f in m["frames"]:
        path = os.path.join(reference, f)
        if os.path.exists(path):
            frames.append((f, Image.open(path).convert("RGB")))
        else:
            print(f"{name}: no frame {f}")
    across = 4
    rows = (picks + across - 1) // across + (len(frames) + across - 1) // across
    sheet = Image.new("RGB", (across * CELL, rows * (HIGH + 24)), (28, 28, 32))
    draw = ImageDraw.Draw(sheet)
    cells = [(f"{m['shot']} {i + 1}/{picks}", Image.open(p if os.path.isabs(p) else os.path.join(capture, p)).convert("RGB")) for i, p in enumerate(moments)]
    cells += [(os.path.basename(f), im) for f, im in frames]
    for k, (label, im) in enumerate(cells):
        at = k if k < picks else ((picks + across - 1) // across) * across + k - picks
        x, y = at % across * CELL, at // across * (HIGH + 24)
        scale = min(CELL / im.width, HIGH / im.height)
        small = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        sheet.paste(small, (x + (CELL - small.width) // 2, y + 24))
        draw.text((x + 6, y + 2), label[:46], fill=(255, 255, 255) if k < picks else (255, 220, 90), font=FONT)
    path = os.path.join(out, name + ".jpg")
    sheet.save(path, quality=88)
    print(path)
