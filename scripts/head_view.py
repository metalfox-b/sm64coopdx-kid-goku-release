"""His head from five sides, wearing a painted face, in seconds and with no build or game: for looking at the light on his skin.

Usage: python3 scripts/head_view.py FACE.json OUT.png FACE_TEXTURE.png [FACE_TEXTURE.png ...]
FACE.json is private/build/goku-face.json. Each texture gets a row: his right side, his right quarter, the front, his left quarter, his left
side. His face takes the texture; his ears and the skin round them take head_light's rule, as bt3.py bakes it; his hair is flat black. It has
no outlines and no perspective, and his ears have no art: the game is the judge of those.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import head_light
from faces import SKIN, SKIN_SHADOW

HAIR, GROUND = (22, 22, 28), (60, 170, 60)
SIZE, SCALE = 520, 700
VIEWS = (80, 38, 0, -38, -80)


def row(face, texture):
    v = np.array(face["verts"], float)
    edges = head_light.outline(face)
    tex = np.asarray(Image.open(texture).convert("RGB"))
    th, tw = tex.shape[:2]
    tris = [((idx[0], idx[k], idx[k + 1]), "Face", (uv[0], uv[k], uv[k + 1])) for idx, _, _, uv in face["faces"] for k in range(1, len(idx) - 1)]
    tris += [((idx[0], idx[k], idx[k + 1]), m, None) for idx, m in face["rest"] for k in range(1, len(idx) - 1)]
    out = Image.new("RGB", (len(VIEWS) * SIZE, SIZE), GROUND)
    for n, yaw in enumerate(VIEWS):
        a = math.radians(yaw)
        across = np.array([0, -math.cos(a), math.sin(a)])
        toward = np.array([0, math.sin(a), math.cos(a)])
        x, y, z = v @ across * SCALE + SIZE / 2, SIZE / 2 - (v[:, 0] - 0.27) * SCALE, v @ toward
        img = np.zeros((SIZE, SIZE, 3), np.uint8)
        img[:] = GROUND
        near = np.full((SIZE, SIZE), -np.inf)
        for t, kind, uv in tris:
            t = list(t)
            (x0, x1, x2), (y0, y1, y2) = x[t], y[t]
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            xa, xb = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, SIZE - 1)
            ya, yb = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, SIZE - 1)
            if abs(den) < 1e-9 or xa > xb or ya > yb:
                continue
            gx, gy = np.meshgrid(np.arange(xa, xb + 1) + .5, np.arange(ya, yb + 1) + .5)
            w0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
            w1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
            w2 = 1 - w0 - w1
            zz = w0 * z[t[0]] + w1 * z[t[1]] + w2 * z[t[2]]
            box = near[ya:yb + 1, xa:xb + 1]
            win = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6) & (zz > box)
            if not win.any():
                continue
            box[win] = zz[win]
            w = np.stack([w0[win], w1[win], w2[win]], axis=1)
            if kind == "Hair":
                color = np.array(HAIR)
            elif kind == "Face":
                st = w @ np.array(uv)
                color = tex[np.clip(((1 - st[:, 1]) * th).astype(int), 0, th - 1), np.clip((st[:, 0] * tw).astype(int), 0, tw - 1)]
            else:
                away = w @ head_light.turned_away(edges, v[t]).astype(float)
                color = np.where((away > 0.5)[:, None], SKIN_SHADOW, SKIN)
            img[ya:yb + 1, xa:xb + 1][win] = color
        out.paste(Image.fromarray(img), (n * SIZE, 0))
    return out


def main() -> int:
    face = json.load(open(sys.argv[1]))
    out, textures = sys.argv[2], sys.argv[3:]
    rows = [row(face, t) for t in textures]
    sheet = Image.new("RGB", (rows[0].width, SIZE * len(rows)))
    for k, r in enumerate(rows):
        sheet.paste(r, (0, k * SIZE))
    sheet.save(out)
    print(out, textures)
    return 0


if __name__ == "__main__":
    sys.exit(main())
