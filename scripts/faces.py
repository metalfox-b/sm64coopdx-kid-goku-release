"""Paint Kid Goku's expressions onto his built head from their traced art (needs Pillow, resvg-py and shapely:
scripts/requirements.txt).

Usage: python3 scripts/faces.py FACE.json ART_DIR ACTOR_DIR

FACE.json is bt3.py's head: its vertices, and the face's triangles with Tenkaichi's UVs and the even ones bt3.py gives
them.
ART_DIR is art/faces: an SVG per expression (scripts/trace_faces.py writes them, traced over the 1986 anime) and
shadow.svg, the cel shadow they all share. The goku_face_<name>.ci4.png files in ACTOR_DIR are overwritten, one per
SVG, and goku_n64_ear.ci4.png with a copy of his ear at the size it mostly shows on screen: any sharper, and its lines break into dots as it turns away.

An SVG is a front view of his head. It's rendered, and carried onto the texture through the face's UVs: every texel
takes the color of the art where that texel shows from the front, over the anime's skin. The skin is in its
shadow tone where his head turns from the light or his hair's shadow falls (head_light.py), and wherever
shadow.svg, drawn by hand, covers it.
"""
import io
import json
import math
import os
import re
import sys

import numpy as np
import resvg_py
from PIL import Image
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from face_shapes import NEUTRAL, SHAPES, warp
import head_light
from ear import draw as draw_ear
from rip_textures import ANIME_SKIN as SKIN, EAR_INK

SIZE = 256
VIEW, SCALE = 800, 840
CX, CY = 400, 660
assert (VIEW, SCALE, CX, CY) == (head_light.VIEW, head_light.SCALE, head_light.CX, head_light.CY)
EMPTY = {"hit": "surprised", "grin": "determined"}
SKIN_SHADOW = (215, 152, 133)


def texel_points(face):
    """Each texel of the 2*SIZE x SIZE texture -> where it shows in the front view, where it was on Tenkaichi's
    mirrored texture (the frontmost, where the face folds over itself), and where it is on his head."""
    verts, size = face["verts"], SIZE
    where, depth = {}, {}
    for idx, _, uv0, uv in face["faces"]:
        for k in range(1, len(idx) - 1):
            corner = (0, k, k + 1)
            ps = [verts[idx[c]] for c in corner]
            olds = [uv0[c] for c in corner]
            ts = [(uv[c][0] * 2 * size, (1 - uv[c][1]) * size) for c in corner]
            (x0, y0), (x1, y1), (x2, y2) = ts
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9:
                continue
            for y in range(max(0, int(min(y0, y1, y2))), min(size, int(max(y0, y1, y2)) + 1)):
                for x in range(max(0, int(min(x0, x1, x2))), min(2 * size, int(max(x0, x1, x2)) + 1)):
                    a = ((y1 - y2) * (x + .5 - x2) + (x2 - x1) * (y + .5 - y2)) / den
                    b = ((y2 - y0) * (x + .5 - x2) + (x0 - x2) * (y + .5 - y2)) / den
                    c = 1 - a - b
                    if min(a, b, c) < -1e-6:
                        continue
                    p = tuple(a * ps[0][i] + b * ps[1][i] + c * ps[2][i] for i in range(3))
                    s0, t0 = (a * olds[0][i] + b * olds[1][i] + c * olds[2][i] for i in range(2))
                    if (x, y) not in depth or p[2] > depth[(x, y)]:
                        depth[(x, y)] = p[2]
                        where[(x, y)] = ((CX - p[1] * SCALE, CY - p[0] * SCALE),
                                         ((s0 if s0 < 1 else 2 - s0) * size, (1 - t0) * size), p)
    return where


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return tuple(u * u * u * a + 3 * u * u * t * b + 3 * u * t * t * c + t * t * t * d for a, b, c, d in zip(p0, p1, p2, p3))


def ink_outline(d, widths, step=0.25):
    """An ink line (absolute M/C centerline, a width at each on-curve point) as one filled outline: discs along it
    and quads between them, merged. Built any other way, a tapered line notches at its ends or leaves specks where
    a tight bend folds its inner edge back (the map's ticket 05)."""
    nums = [float(v) for v in re.findall(r"-?[\d.]+(?:e-?\d+)?", d)]
    p, segments = (nums[0], nums[1]), []
    for i in range(2, len(nums), 6):
        segments.append((p, (nums[i], nums[i + 1]), (nums[i + 2], nums[i + 3]), (nums[i + 4], nums[i + 5])))
        p = segments[-1][3]
    pts = []
    for k, seg in enumerate(segments):
        n = max(8, int(sum(math.dist(a, b) for a, b in zip(seg, seg[1:])) / step))
        for i in range(0 if k == 0 else 1, n + 1):
            pts.append((*cubic(*seg, i / n), widths[k] + (widths[k + 1] - widths[k]) * i / n))
    shapes = [Point(x, y).buffer(w / 2, quad_segs=16) for x, y, w in pts if w > 0.02]
    for (x0, y0, w0), (x1, y1, w1) in zip(pts, pts[1:]):
        length = math.hypot(x1 - x0, y1 - y0) or 1
        nx, ny = -(y1 - y0) / length, (x1 - x0) / length
        shapes.append(Polygon([(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
                               (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)]))
    merged = unary_union(shapes).simplify(0.01)

    def ring(r):
        return "M" + "L".join(f"{x:.3f},{y:.3f}" for x, y in r.coords) + "Z"
    return "".join(ring(g.exterior) + "".join(ring(h) for h in g.interiors) for g in getattr(merged, "geoms", [merged]))


def render(path):
    """An art SVG at VIEW x VIEW, RGBA, its ink lines expanded to outlines."""
    def expand(m):
        tag = m.group(0)
        d = re.search(r'\bd="([^"]+)"', tag).group(1)
        widths = [float(v) for v in re.search(r'data-w="([^"]+)"', tag).group(1).split()]
        color = re.search(r'stroke="([^"]+)"', tag).group(1)
        return f'<path d="{ink_outline(d, widths)}" fill="{color}"/>'
    svg = re.sub(r'<path class="ink"[^>]*/>', expand, open(path).read())
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=svg, width=VIEW, height=VIEW)))).convert("RGBA")


def sample(px, w, h, x, y):
    """Bilinear sample of an RGBA image's pixels, alpha-weighted: (premultiplied rgb, alpha)."""
    x, y = min(max(x - .5, 0), w - 1.001), min(max(y - .5, 0), h - 1.001)
    ix, iy = int(x), int(y)
    fx, fy = x - ix, y - iy
    rgb, alpha = [0.0, 0.0, 0.0], 0.0
    for dx, dy, wt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        p = px[ix + dx, iy + dy]
        for k in range(3):
            rgb[k] += p[k] * p[3] / 255 * wt
        alpha += p[3] * wt
    return rgb, alpha


def paint(where, shadowed, art):
    tex = Image.new("RGB", (2 * SIZE, SIZE), SKIN)
    ap, tp = art.load(), tex.load()
    for key, ((sx, sy), _, _) in where.items():
        skin = SKIN_SHADOW if key in shadowed else SKIN
        art_rgb, alpha = sample(ap, VIEW, VIEW, sx, sy)
        a = alpha / 255
        tp[key] = tuple(min(255, round(art_rgb[k] + skin[k] * (1 - a))) for k in range(3))
    pixels, used = np.array(tex), np.zeros((SIZE, 2 * SIZE), bool)
    for x, y in where:
        used[y, x] = True
    for _ in range(6):
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            came, from_used = np.roll(pixels, (dy, dx), axis=(0, 1)), np.roll(used, (dy, dx), axis=(0, 1))
            take = ~used & from_used
            pixels[take], used = came[take], used | take
    return Image.fromarray(pixels)


def in_shadow(face, where, drawn):
    """The texels whose skin is in shadow: where his head is turned from the light, where his hair's shadow falls on that side of his face, and
    where shadow.svg covers."""
    keys = list(where)
    spots = np.array([where[k][0] for k in keys])
    points = [where[k][2] for k in keys]
    edges = head_light.outline(face)
    how_far = head_light.across(edges, points)
    x, y = np.clip(spots[:, 0].astype(int), 0, VIEW - 1), np.clip(spots[:, 1].astype(int), 0, VIEW - 1)
    inside = (spots[:, 0] >= 0) & (spots[:, 0] < VIEW) & (spots[:, 1] >= 0) & (spots[:, 1] < VIEW)
    dark = (how_far < head_light.band(points)) | (inside & head_light.hair_shadow(face)[y, x] & (how_far < 0.5))
    dark |= np.array([bool(i) and drawn[int(a), int(b)] > 127 for i, a, b in zip(inside, x, y)])
    return {k for k, d in zip(keys, dark) if d}


def main() -> int:
    face_json, art, actor = sys.argv[1:4]
    face = json.load(open(face_json))
    where = texel_points(face)
    shadowed = in_shadow(face, where, render(os.path.join(art, "shadow.svg")).getchannel("A").load())
    names = sorted(f[:-4] for f in os.listdir(art) if f.endswith(".svg") and f != "shadow.svg")
    for name in names:
        shape = SHAPES.get(name, NEUTRAL)
        own = where if shape == NEUTRAL else texel_points({**face, "verts": [warp(tuple(v), shape) for v in face["verts"]]})
        paint(own, shadowed, render(os.path.join(art, f"{name}.svg"))).save(
            os.path.join(actor, f"goku_face_{name}.ci4.png"))
    for name, shown in EMPTY.items():
        assert name not in names, f"{name} has art again: take it out of EMPTY"
        Image.open(os.path.join(actor, f"goku_face_{shown}.ci4.png")).save(os.path.join(actor, f"goku_face_{name}.ci4.png"))
    draw_ear(128, SKIN, EAR_INK).save(os.path.join(actor, "goku_n64_ear.ci4.png"))
    print("faces:", ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
