"""Counts what's wrong with his outlines, from frames filmed with every line in pure magenta (check.mjs --key-lines).

  outlines.py CAPTURE_DIR OUT_DIR SHOT[,SHOT...] [STEP]

  outlines.py round CAPTURE_DIR OUT_DIR    a sheet of him all the way round, from a film in his real colors

Writes OUT_DIR/report.json (per shot, per kind) and OUT_DIR/SHOT-KIND.jpg, the worst spots of each kind, boxed. The kinds:
  speck    a dot of line by itself
  dash     a short piece of line by itself
  dots     a row of dots too small to count one by one
  gap      a break in a line
  double   two lines side by side with a sliver between them
  float    a line standing off the part it outlines, with background between them
Needs numpy, scipy and Pillow. The background is the film engine's green, which nothing on him is.
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

EIGHT = np.ones((3, 3), bool)
SPECK, DASH = 14, 50
NOISE = 3
DOTS, DOT_GAP = 4, 6
KINDS = ("speck", "dash", "dots", "gap", "double", "float")
PARTS = ("butt", "torso", "head", "arm", "forearm", "hand", "thigh", "leg", "shoe", "pole", "tail", "chin")


def whose(greens):
    """Which part's outline these line pixels are: check.mjs --key-lines gives each part a green of its own, in fives."""
    values, counts = np.unique((greens + 2) // 5, return_counts=True)
    at = int(values[counts.argmax()])
    return PARTS[at] if at < len(PARTS) else "other"


def widths(rgb, into):
    """How wide each part's line is at each point along its middle, in pixels: what's added to into, by part."""
    r, g, b = (rgb[..., k].astype(int) for k in range(3))
    line = (r > 200) & (g < 70) & (b > 200)
    which = (g + 2) // 5
    for k, part in enumerate(PARTS):
        mine = line & (which == k)
        if mine.any():
            d = ndi.distance_transform_edt(mine)
            into.setdefault(part, []).extend((d[mine & (d == ndi.maximum_filter(d, size=3))] * 2 - 1).tolist())


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def boxes(mask, least=1):
    """Each 8-connected piece's box and size, keeping those whose longest side is at least least."""
    lab, n = ndi.label(mask, EIGHT)
    out = []
    for k, s in enumerate(ndi.find_objects(lab), 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        if max(h, w) >= least:
            out.append((s[1].start, s[0].start, s[1].stop, s[0].stop, int((lab[s] == k).sum())))
    return out


def look(rgb):
    """Every flaw in one frame: {kind: [(x0, y0, x1, y1, size)]}."""
    r, g, b = (rgb[..., k].astype(int) for k in range(3))
    line = (r > 200) & (g < 70) & (b > 200)
    ground = (g > r * 1.25 + 4) & (g > b * 1.25 + 4)
    him = ~line & ~ground
    found = {k: [] for k in KINDS}
    found["whose"] = []
    lab, n = ndi.label(line, EIGHT)
    for k, s in enumerate(ndi.find_objects(lab), 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        size = int((lab[s] == k).sum())
        if size < NOISE:
            continue
        box = (s[1].start, s[0].start, s[1].stop, s[0].stop, size)
        if max(h, w) < SPECK:
            found["speck"].append(box)
        elif max(h, w) < DASH:
            found["dash"].append(box)
    sizes = ndi.sum(line, lab, range(1, n + 1)) if n else []
    tiny = np.isin(lab, [k + 1 for k, s in enumerate(sizes) if s < NOISE])
    strings, m = ndi.label(ndi.binary_dilation(tiny, disk(DOT_GAP)), EIGHT)
    for k, s in enumerate(ndi.find_objects(strings), 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        mine = tiny[s] & (strings[s] == k)
        dots = ndi.label(mine, EIGHT)[1]
        if dots >= DOTS and max(h, w) >= SPECK:
            found["dots"].append((s[1].start, s[0].start, s[1].stop, s[0].stop, dots))
            found["whose"].append(whose(g[s][mine]))
    near, m = ndi.label(ndi.binary_dilation(line, disk(5)), EIGHT)
    for j in range(1, m + 1):
        region = near == j
        parts = np.unique(lab[region & line])
        if len(parts) > 1:
            big = [p for p in parts if (lab == p).sum() >= 40]
            if len(big) > 1:
                ys, xs = np.nonzero(region)
                found["gap"].append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), len(big) - 1))
    closed = ndi.binary_closing(line, disk(4))
    pale = (abs(r - g) < 30) & (abs(g - b) < 40) & (r > 110)
    for x0, y0, x1, y1, size in boxes(closed & ~line & ~pale, 16):
        if size / max(x1 - x0, y1 - y0) <= 6:
            found["double"].append((x0, y0, x1, y1, size))
    off = ground & ndi.binary_closing(line | him, disk(3)) & ndi.binary_dilation(line, disk(4))
    found["float"] += boxes(off, 5)
    return found


def sheet(path, spots):
    """The worst spots, each cropped at true size with its box drawn."""
    spots = sorted(spots, key=lambda s: -s[1][4])[:24]
    if not spots:
        return
    cell = 240
    across = 6
    img = Image.new("RGB", (cell * across, cell * ((len(spots) + across - 1) // across)), "white")
    for k, (file, box) in enumerate(spots):
        x0, y0, x1, y1, _ = box
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        shot = Image.open(file).convert("RGB")
        at = (cx - cell // 2, cy - cell // 2)
        crop = shot.crop((*at, at[0] + cell, at[1] + cell))
        ImageDraw.Draw(crop).rectangle((x0 - at[0] - 3, y0 - at[1] - 3, x1 - at[0] + 3, y1 - at[1] + 3), outline=(255, 255, 0))
        img.paste(crop, (k % across * cell, k // across * cell))
    img.save(path, quality=88)


def round_sheet(capture, out):
    """Him all the way round in his real colors. The counts only see lines: a black shape, a hole or a bad shade takes looking at."""
    files = re.findall(r"file '(.+)'", open(os.path.join(capture, "lines-stand.txt")).read())
    views = files[::len(files) // 12][:12]
    sheet = Image.new("RGB", (4 * 480, 3 * 640))
    for k, f in enumerate(views):
        sheet.paste(Image.open(f).convert("RGB").crop((480, 80, 1440, 1360)).resize((480, 640), Image.LANCZOS), (k % 4 * 480, k // 4 * 640))
    path = os.path.join(out, "all-round.jpg")
    sheet.save(path, quality=90)
    print("look at him all the way round:", path)


def main():
    if sys.argv[1] == "round":
        return round_sheet(sys.argv[2], sys.argv[3])
    capture, out, shots = sys.argv[1:4]
    step = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    os.makedirs(out, exist_ok=True)
    report = {}
    tally = {}
    spots_of = {}
    wide = {}
    for shot in shots.split(","):
        files = re.findall(r"file '(.+)'", open(os.path.join(capture, shot + ".txt")).read())[::step]
        spots = {k: [] for k in KINDS}
        for f in files:
            rgb = np.asarray(Image.open(f).convert("RGB"))
            found = look(rgb)
            widths(rgb, wide)
            for part, box in zip(found["whose"], found["dots"]):
                tally[part] = tally.get(part, 0) + 1
                spots_of.setdefault(part, []).append((f, box))
            for k in KINDS:
                if not (shot.endswith("-low") and k == "float"):
                    spots[k] += [(f, b) for b in found[k]]
        report[shot] = {k: len(spots[k]) for k in KINDS}
        report[shot]["frames"] = len(files)
        print(shot, report[shot], flush=True)
        for k in KINDS:
            sheet(os.path.join(out, f"{shot}-{k}.jpg"), spots[k])
    totals = {k: sum(r[k] for r in report.values()) for k in KINDS}
    for part, w in wide.items():
        totals[f"{part} line width"] = round(float(np.percentile(w, 90)), 1)
    report["all"] = totals
    print("all", totals)
    print("rows of dots, by whose line:", dict(sorted(tally.items(), key=lambda kv: -kv[1])))
    for part, spots in spots_of.items():
        sheet(os.path.join(out, f"dots-{part}.jpg"), spots)
    with open(os.path.join(out, "report.json"), "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
