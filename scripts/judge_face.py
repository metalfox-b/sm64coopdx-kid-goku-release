"""Measures a face in game and finds what's wrong with it, against every face Metal Fox has passed.

  judge_face.py measure CROP.png            prints a face's measures
  judge_face.py judge CROP.png NAME [--mood angry]    what's outside what he has passed; exits 1 if anything is
  judge_face.py calibrate DIR               every labeled picture in DIR/passed and DIR/rejected: how often it's right, leaving each passed face out

A crop is his face from a 1920x1440 film of faces-close, 640 pixels square (compare_face.py's BOX). It can only reject. Nothing here can say a face is good: passing a face is Metal Fox's.
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RANGES = os.path.join(ROOT, "art", "faces", "judge-ranges.json")
EIGHT = np.ones((3, 3), bool)
MARGIN = 0.12


def pieces(mask):
    lab, n = ndi.label(mask, EIGHT)
    return [(lab == k) for k in range(1, n + 1)]


def measure(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h, w = r.shape
    m = {}
    yy, xx = np.mgrid[:h, :w]
    white = (a.min(axis=2) > 232)
    upper = white & (yy < 410) & (yy > 200) & (xx > 130) & (xx < 510)
    eyes = sorted(pieces(upper), key=lambda p: -p.sum())[:2]
    eyes = [e for e in eyes if e.sum() > 400]
    m["eyes_seen"] = len(eyes)
    if len(eyes) == 2:
        eyes.sort(key=lambda e: xx[e].mean())
        boxes = [(xx[e].min(), xx[e].max(), yy[e].min(), yy[e].max()) for e in eyes]
        m["white_area"] = float(sum(e.sum() for e in eyes) / 2)
        m["white_tall"] = float(np.mean([b_[3] - b_[2] for b_ in boxes]) / np.mean([b_[1] - b_[0] for b_ in boxes]))
        m["white_wide"] = float(np.mean([b_[1] - b_[0] for b_ in boxes]))
        m["white_gap"] = float(boxes[1][0] - boxes[0][1])
        m["white_top"] = float(np.mean([b_[2] for b_ in boxes]))
        m["white_bottom"] = float(np.mean([b_[3] for b_ in boxes]))
    dark = a.max(axis=2) < 75
    ink = dark & (r > b) & (a.max(axis=2) > 15)
    if len(eyes) == 2:
        sizes, inward, high = [], [], []
        for e, sign, box in zip(eyes, (1, -1), boxes):
            filled = ndi.binary_fill_holes(ndi.binary_closing(e, np.ones((9, 9), bool)))
            inner = filled & ~e & dark
            blobs = [p for p in pieces(inner) if p.sum() > 25]
            if blobs:
                p = max(blobs, key=lambda q: q.sum())
                sizes.append(p.sum())
                inward.append(sign * (xx[p].mean() - (box[0] + box[1]) / 2) / max(box[1] - box[0], 1))
                high.append((yy[p].mean() - (box[2] + box[3]) / 2) / max(box[3] - box[2], 1))
        if sizes:
            m["pupil_share"] = float(np.mean(sizes) / m["white_area"])
            m["pupil_inward"] = float(np.mean(inward))
            m["pupil_high"] = float(np.mean(high))
    red = (r > 100) & (r < 185) & (g < 95) & (b < 105) & (r > g + 40)
    tongue = (r > 195) & (g > 95) & (g < 165) & (b > 95) & (b < 170) & (r > g + 50) & (g < b + 10)
    area = (yy > 330) & (yy < 620) & (xx > 110) & (xx < 530)
    core = (red | tongue) & area
    teeth = white & area & (yy > 345)
    middle = (xx[eyes[0]].mean() + xx[eyes[1]].mean()) / 2 if len(eyes) == 2 else w / 2
    if core.sum() > 60:
        near = ndi.binary_dilation(core, np.ones((21, 21), bool))
        whole = ndi.binary_closing(core | (teeth & near), np.ones((11, 11), bool))
        parts = pieces(whole)
        shape = ndi.binary_fill_holes(max(parts, key=lambda p: (p & core).sum()))
    elif teeth.sum() > 400:
        parts = pieces(ndi.binary_closing(teeth, np.ones((5, 5), bool)))
        shape = ndi.binary_fill_holes(max(parts, key=lambda p: p.sum()))
    else:
        shape = None
    if shape is not None:
        ys, xs = np.nonzero(shape)
        m["mouth_wide"] = float(xs.max() - xs.min())
        m["mouth_tall"] = float(ys.max() - ys.min())
        m["mouth_area"] = float(shape.sum())
        m["mouth_aspect"] = m["mouth_wide"] / max(m["mouth_tall"], 1.0)
        if "white_bottom" in m:
            m["mouth_top"] = float(ys.min() - m["white_bottom"])
            m["mouth_bottom"] = float(ys.max() - m["white_bottom"])
        m["mouth_tongue_share"] = float((tongue & shape).sum() / shape.sum())
        m["mouth_teeth_share"] = float((teeth & shape).sum() / shape.sum())
        m["mouth_off_middle"] = float(abs(xs.mean() - middle))
        cols = np.nonzero(shape.any(axis=0))[0]
        tips = max(len(cols) // 8, 1)
        edge = np.r_[cols[:tips], cols[-tips:]]
        mid = cols[len(cols) * 3 // 8:len(cols) * 5 // 8]
        bottom = [ys[xs == c].max() for c in cols]
        by = dict(zip(cols.tolist(), bottom))
        m["mouth_lift"] = float(np.mean([by[int(c)] for c in mid]) - np.mean([by[int(c)] for c in edge]))
    if len(eyes) == 2:
        band = ink & (yy < m["white_top"] + 45) & (yy > m["white_top"] - 110) & ~ndi.binary_dilation(a.max(axis=2) > 200, np.ones((1, 1), bool))
        blobs = [p for p in pieces(band) if p.sum() > 120]
        m["brow_ink"] = float(sum(p.sum() for p in blobs))
        slopes, cover = [], []
        for side, e in ((xx < w / 2, eyes[0]), (xx >= w / 2, eyes[1])):
            parts = [p & side for p in blobs if (p & side).sum() > 120]
            if parts:
                p = max(parts, key=lambda q: q.sum())
                x, y = xx[p], yy[p]
                if x.std() > 3:
                    k = np.polyfit(x, y, 1)[0]
                    slopes.append(k if side[0, 0] else -k)
                near = ndi.binary_dilation(p, np.ones((3, 3), bool)) & ndi.binary_dilation(e, np.ones((5, 5), bool))
                cover.append(near.sum() / max(p.sum(), 1))
        if slopes:
            m["brow_slope"] = float(np.mean(slopes))
        if cover:
            m["brow_on_eye"] = float(np.mean(cover))
    m.pop("white_top", None)
    m.pop("white_bottom", None)
    return m


OPEN_EYES = {"relaxed", "determined", "shout", "surprised", "happy", "smile", "yell"}
OPEN_MOUTHS = {"shout", "surprised", "happy", "yell", "closed", "dead"}
FOR_EYES = ("white_", "pupil_", "brow_", "eyes_")


def family(key):
    return OPEN_EYES if key.startswith(FOR_EYES) else OPEN_MOUTHS


def ranges_from(faces):
    keys = sorted({k for m in faces.values() for k in m})
    out = {}
    for k in keys:
        vals = [m[k] for n, m in faces.items() if k in m and n in family(k)]
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        pad = max((hi - lo) * MARGIN, abs(hi) * MARGIN * 0.5, 1e-3)
        out[k] = (lo - pad, hi + pad)
    return out


WORDS = {"white_area": "his eyes' size", "white_wide": "his eyes' width", "white_tall": "his eyes' shape", "white_gap": "the gap between his eyes", 
         "pupil_share": "his pupils' size", "pupil_inward": "how far in his pupils sit", "pupil_high": "how high his pupils sit",
         "mouth_wide": "his mouth's width", "mouth_tall": "his mouth's height", "mouth_area": "his mouth's size", "mouth_teeth_share": "his teeth's share of his mouth", "mouth_tongue_share": "his tongue's share of his mouth",
         "mouth_top": "how high his mouth starts", "mouth_bottom": "how low his mouth reaches", "mouth_aspect": "his mouth's shape", "mouth_lift": "how much his mouth curves up",
         "mouth_off_middle": "how far his mouth sits off his middle", "brow_ink": "his brows' weight", "brow_slope": "his brows' slant", "brow_on_eye": "his brows over his eyes", "eyes_seen": "his two eyes"}


def against(m, ranges):
    found = []
    for k, (lo, hi) in ranges.items():
        if k in m and not lo <= m[k] <= hi:
            found.append((k, m[k], lo, hi))
    return found


def calibrate(folder):
    passed = {os.path.basename(p)[:-4]: measure(p) for p in sorted(glob.glob(os.path.join(folder, "passed", "*.png")))}
    rejected = {os.path.basename(p)[:-4]: measure(p) for p in sorted(glob.glob(os.path.join(folder, "rejected", "*.png")))}
    wrong = []
    for name, m in passed.items():
        rest = {k: v for k, v in passed.items() if k != name}
        hits = [h for h in against(m, ranges_from(rest)) if name in family(h[0])]
        print(f"passed   {name:14} {'FLAGGED: ' + ', '.join(h[0] for h in hits) if hits else 'clear'}")
        if hits:
            wrong.append(name)
    ranges = ranges_from(passed)
    caught = 0
    for name, m in rejected.items():
        hits = against(m, ranges)
        caught += bool(hits)
        print(f"rejected {name:14} {'caught: ' + ', '.join(h[0] for h in hits) if hits else 'MISSED'}")
    print(f"\nrejected faces caught: {caught} of {len(rejected)}")
    print(f"passed faces wrongly flagged, each left out in turn: {len(wrong)} of {len(passed)}")
    with open(RANGES, "w") as f:
        json.dump({"note": "What the faces Metal Fox has passed measure, from judge_face.py calibrate. Numbers only.", "ranges": ranges,
                   "caught": [caught, len(rejected)], "wrongly_flagged": [len(wrong), len(passed)]}, f, indent=1)


def main():
    if sys.argv[1] == "measure":
        print(json.dumps(measure(sys.argv[2]), indent=1))
        return 0
    if sys.argv[1] == "calibrate":
        calibrate(sys.argv[2])
        return 0
    ranges = json.load(open(RANGES))["ranges"]
    hits = against(measure(sys.argv[2]), ranges)
    for k, v, lo, hi in hits:
        print(f"OFF {WORDS.get(k, k)}: {v:.2f}, where his passed faces run {lo:.2f} to {hi:.2f}")
    if hits:
        return 1
    print("nothing here is outside his passed faces. That is not a pass: it only means these measures found no fault.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
