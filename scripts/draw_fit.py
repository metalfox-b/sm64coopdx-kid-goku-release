"""A fit's skeleton over its still: the marks in yellow, the fitted joints as the still's camera saw them in cyan,
so where the fit departs from the marks shows on the frame itself.

Usage: python3 scripts/draw_fit.py FIT.json N OUT.png   (pose-preview.mjs runs it)
"""
import json
import sys

from PIL import Image, ImageDraw

BONES = [("neck", "head"), ("neck", "pelvis"), ("r_shoulder", "l_shoulder"), ("r_hip", "l_hip"),
         ("r_shoulder", "r_elbow"), ("r_elbow", "r_wrist"), ("l_shoulder", "l_elbow"), ("l_elbow", "l_wrist"),
         ("r_hip", "r_knee"), ("r_knee", "r_ankle"), ("l_hip", "l_knee"), ("l_knee", "l_ankle")]

fit = json.load(open(sys.argv[1], encoding="utf8"))
reading = fit["readings"][int(sys.argv[2]) - 1]
marks = json.load(open(fit["marks"], encoding="utf8"))
im = Image.open(fit["image"]).convert("RGB")
scale = 1 if marks.get("pixels") == "still" else im.width / 900
d = ImageDraw.Draw(im)
for pts, color, width in ((marks["points"], (255, 220, 0), 5), (reading["projected"], (0, 230, 255), 3)):
    at = {k: (v[0] * scale, v[1] * scale) for k, v in pts.items()}
    for a, b in BONES:
        if a in at and b in at:
            d.line([at[a], at[b]], fill=color, width=width)
    for v in at.values():
        d.ellipse([v[0] - 4, v[1] - 4, v[0] + 4, v[1] + 4], fill=color)
im.save(sys.argv[3])
print("skeleton:", sys.argv[3])
