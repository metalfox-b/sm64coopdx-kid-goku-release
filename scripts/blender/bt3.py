"""Convert Tenkaichi 3's Kid Goku (a glTF rip) onto Mario's skeleton and export him as goku_geo (runs inside Blender).

Usage:
  blender -b TEMPLATE.blend --python scripts/blender/bt3.py -- RIP.json OUT_ACTORS_DIR RIG.json N64TEX_DIR [PREVIEW_DIR]

N64TEX_DIR is rip_textures.py's output: the N64 remakes of his textures and how they map onto the old UVs. Only his
head keeps the rip's triangles; body.py builds his body to the anime, sized from the rip's parts.

RIP.json comes from rip_extract.py (the glTF importer crashes in the template's scene).

The rip stays local: it, its textures and everything made from it live under private/ and in the
gitignored mod/kid-goku/actors/goku/. RIG.json gets the skeleton the rip implies (Mario's joints moved to Tenkaichi's,
plus where his soles are), which anims.py reads so the animations stand him on the floor.

Fitting: the rip's T-pose is posed on Mario's skeleton with the same frame conventions the animations use (anims.py),
each of the rip's vertices goes to the Mario bone its strongest weight's bone maps to, and is rewritten in that bone's
rest frame. Skinning is rigid, one bone per vertex, the N64 way.
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bpy
from mathutils import Matrix, Vector

import anims
import body
import ear
import goku
import head_light

MAP = {}
for n in (0, 1, 2, 3, 8, 12, 52, 53, 54, 87, 88, 89, 90):
    MAP[n] = "Butt"
for n in (16, 17, 18, 32, 66):
    MAP[n] = "Torso"
for n in (46, 47, 48, 49, 50, 51, 79, 80, 81, 82, 83, 84, 85):
    MAP[n] = "Head DL"
MAP.update({19: "Right Arm Color", 20: "Right Forearm", 9: "Right Thigh Color", 10: "Right Leg", 11: "Right Shoe DL",
            33: "Left Arm Color", 34: "Left Forearm", 13: "Left Thigh Color", 14: "Left Leg", 15: "Left Shoe"})
for n in range(21, 32):
    MAP[n] = "Right Hand DL"
for n in range(35, 46):
    MAP[n] = "Left Hand DL"
FRAME_OF = {"Head DL": "Head", "Left Arm Color": "Left Arm", "Right Arm Color": "Right Arm",
            "Left Hand DL": "Left Hand", "Right Hand DL": "Right Hand", "Right Shoe DL": "Right Shoe",
            "Left Thigh Color": "Left Thigh", "Right Thigh Color": "Right Thigh"}
J = {"hips": 3, "waist": 16, "neck": 46, "l_shoulder": 33, "l_elbow": 34, "l_wrist": 35, "l_knuckle": 39,
     "r_shoulder": 19, "r_elbow": 20, "r_wrist": 21, "r_knuckle": 25, "l_hip": 13, "l_knee": 14, "l_ankle": 15,
     "r_hip": 9, "r_knee": 10, "r_ankle": 11}
HEIGHT = 2.56
LEG = 0.605
TORSO = 0.7
ARM = 0.75
HEAD_SCALE = 1.05
SHOE_SCALE = 1.15
TENKAICHI = {goku.GI: ("C5391C", "86230E"), goku.SKIN: ("FEC6A1", "D9946A"), goku.BELT: ("1E1E22", "0C0C0E"),
             goku.BAND: ("1C4395", "102A62"), goku.SHOE: ("1A3A80", "0E2050"), goku.SOCK: ("E6E6E6", "A8A8B4"),
             goku.POLE: ("C23A1B", "7C2210"), goku.HAIR: ("1A1A22", "060608"), "Rope": ("977F4B", "5E4E2C")}
G_HAIR = goku.HAIR
LINE_OFF_GROUND = 0.012
EAR = "BT3 Ear"
NECK_SHADE = body.NECK_SHADE
PILAF = {goku.GI: ("4E5CC4", "303A8A"), goku.BELT: ("F8F8F4", "CDD2E0"), goku.BAND: ("D0322A", "8E1C18"),
         goku.SHOE: ("23264A", "10122A"), goku.SOCK: ("E6E8EC", "B4B8C2"), "Rope": ("C8CCD6", "8A90A6"),
         goku.SKIN: ("FCD8CA", "D79885"), goku.POLE: ("E2401E", "962512")}


def fitted(part, rings, sides, mats, caps=(True, True), spread=0.92, top=0.99, start=0.0, first=None, bottom=0.01,
           tuck=None, hang=None):
    """A low-poly loft that keeps the part's shape: the rip's vertices sliced into bands along the bone (u), each
    ring an ellipse through the band's spread (the spread-quantile of its distances, so stray belt tails or rope
    don't bloat it). mats: one material per segment between rings.

    tuck and hang, (length, scale), add a ring past the first or last one: cloth that runs on under or over the
    neighboring part, so a bent joint never opens a gap. The returned stations leave them out."""
    us = sorted(u for u, _, _ in part.verts)
    u0, u1 = us[int(len(us) * bottom)], us[int(len(us) * top) - 1]
    stations = []
    for i in range(rings):
        t = i / (rings - 1)
        uc = u0 + (u1 - u0) * t
        half = (u1 - u0) / (rings - 1) * 0.6
        band = [(v, w) for u, v, w in part.verts if abs(u - uc) <= half] or [(v, w) for _, v, w in part.verts]
        vs, ws = sorted(v for v, _ in band), sorted(w for _, w in band)

        def q(xs, f):
            return xs[min(len(xs) - 1, max(0, int(len(xs) * f)))]
        cv, cw = (q(vs, 0.5 - spread / 2) + q(vs, 0.5 + spread / 2)) / 2, (q(ws, 0.5 - spread / 2) + q(ws, 0.5 + spread / 2)) / 2
        rv, rw = (q(vs, 0.5 + spread / 2) - q(vs, 0.5 - spread / 2)) / 2, (q(ws, 0.5 + spread / 2) - q(ws, 0.5 - spread / 2)) / 2
        stations.append((uc + (start if i == 0 else 0.0), max(rv, 0.02), max(rw, 0.02), cv, cw))
    if first is not None:
        stations[0] = (min(stations[0][0], 0.0), first[1], first[2], first[3], first[4])
    rings_out, mats = list(stations), list(mats)
    if tuck:
        u, rv, rw, cv, cw = stations[0]
        rings_out.insert(0, (u - tuck[0], rv * tuck[1], rw * tuck[1], cv, cw))
        mats.insert(0, mats[0])
    if hang:
        u, rv, rw, cv, cw = stations[-1]
        rings_out.append((u + hang[0], rv * hang[1], rw * hang[1], cv, cw))
        mats.append(mats[-1])
    out = goku.Part()
    goku.loft(out, rings_out, sides, mats[0], cap0=caps[0], cap1=caps[1], mats=mats)
    return out, stations


def decimate(part, ratio, collapse=False):
    """The part reduced, UVs and materials kept: near-flat triangles merged (ratio is the angle limit in degrees), or
    with collapse, edges collapsed down to ratio of the triangles (for untextured parts, where nothing can swim)."""
    mats = sorted({m for _, m, _ in part.faces})
    me = bpy.data.meshes.new("decimate")
    me.from_pydata(part.verts, [], [f for f, _, _ in part.faces])
    uvl = me.uv_layers.new(name="UVMap")
    for poly, (_, m, uv) in zip(me.polygons, part.faces):
        poly.material_index = mats.index(m)
        for k, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uv[k] if uv else (0.0, 0.0)
    obj = bpy.data.objects.new("decimate", me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new("d", "DECIMATE")
    if collapse:
        mod.ratio = ratio
    else:
        mod.decimate_type = "DISSOLVE"
        mod.angle_limit = math.radians(ratio)
        mod.delimit = {"UV", "MATERIAL"}
    tri = obj.modifiers.new("t", "TRIANGULATE")
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    em = ev.to_mesh()
    em.calc_loop_triangles()
    out = goku.Part()
    out.verts = [tuple(v.co) for v in em.vertices]
    euv = em.uv_layers.active.data
    for t in em.loop_triangles:
        m = mats[t.material_index]
        untextured = not m.startswith("BT3") and m not in (goku.FACE, goku.KANJI)
        out.face(list(t.vertices), m, None if untextured else [tuple(euv[li].uv) for li in t.loops])
    ev.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(me)
    return out
RIP_HEAD_TOP = 10.4


def rebuild_n64(parts, rest):
    """Bring him to an N64 budget: the anime body built in code (body.py), the hair as plain color reduced freely,
    and the face reduced only where it can't move the texture."""
    G = goku
    body.rebuild(parts, fitted, rest)
    head = parts["Head DL"]
    hair, face = G.Part(), G.Part()
    for idx, m, uv in head.faces:
        (hair if m == "BT3 0" else face).face(idx, G.HAIR if m == "BT3 0" else m, None if m == "BT3 0" else uv)
    hair.verts = face.verts = head.verts
    hair = fill_hair_holes(decimate(hair, HAIR_DEGREES))
    face = decimate(face, FACE_DEGREES)
    merged = G.Part()
    for src in (hair, face):
        base = len(merged.verts)
        merged.verts += src.verts
        for idx, m, uv in src.faces:
            merged.face([base + i for i in idx], m, uv)
    head = parts["Head DL"] = close_cracks(merged)
    head.faces = [f for f in head.faces if not (f[1] == "BT3 5" and max(head.verts[i][0] for i in f[0]) < 0.08)]
    first = len(head.faces)
    seal_head(head)
    stub = len(head.verts)
    G.blob(head, (0.03, 0.0, -0.01), (0.085, 0.125, 0.12), 8, 4, G.SKIN)
    head.soft.update({i: NECK_SHADE for i in range(stub, len(head.verts))})
    G.blob(head, (0.22, 0.0, 0.06), (0.16, 0.2, 0.15), 8, 3, G.HAIR)
    lining, lined = len(head.faces), len(head.verts)
    G.blob(head, (0.09, 0.0, 0.16), (0.12, 0.2, 0.17), 8, 3, G.SKIN, keep=lambda c: c[2] >= 0.1)
    for idx, m, uv in head.faces[lining:]:
        head.face(idx[::-1], m, uv)
    head.soft.update({i: NECK_SHADE for i in range(lined, len(head.verts))})
    G.blob(head, (0.16, 0.0, -0.03), (0.16, 0.235, 0.19), 10, 5, G.HAIR, shape=lambda u, v, w: (u, v, min(w, -0.04 + max(u, 0.0) / 0.16 * 0.2)))
    head.flat |= set(range(first, len(head.faces)))
    head.flat |= {k for k, (idx, m, _) in enumerate(head.faces)
                  if m == "BT3 5" and sum(head.verts[i][2] for i in idx) / len(idx) < 0.03}


def outline_head(head, ears, plain_backs):
    """The line round his face: his own skin again, each corner pushed out a line's width and turned inside out, as his body's line is, so it follows his nose, lips and jaw because it's made of them.
    A shell wrapped round him from outside couldn't: its points were coarser than a lip, so it cut straight across them and swelled in every hollow. It draws first and leaves no depth (goku.HEAD_LINE), so his skin
    always covers it: with depth, this surface came through his skin in dots. Corners that meet share one direction out, or his torn skin would tear his line as well."""
    from mathutils import Vector
    line = 0.008
    middle = Vector((0.17, 0.0, 0.08))
    plain = lambda idx, m, uv, k: m == EAR and k not in plain_backs and uv == [ear.PLAIN] * len(idx)
    skin = [idx for k, (idx, m, uv) in enumerate(head.faces) if k in ears or m == goku.FACE or plain(idx, m, uv, k)]
    surface = [idx for k, (idx, m, uv) in enumerate(head.faces) if k not in ears and (m == goku.FACE or plain(idx, m, uv, k))]

    def where(i):
        return tuple(round(c, 4) for c in head.verts[i])
    out, facing = {}, {}
    for idx in surface:
        pts = [Vector(head.verts[i]) for i in idx]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if n.length == 0:
            continue
        n.normalize()
        if n.dot(sum(pts, Vector()) / len(pts) - middle) < 0:
            n = -n
        for at, i in enumerate(idx):
            one, two = pts[at - 1] - pts[at], pts[(at + 1) % len(pts)] - pts[at]
            if one.length and two.length:
                out[where(i)] = out.get(where(i), Vector()) + n * one.angle(two, 0.0)
                facing.setdefault(where(i), []).append(n)
    pushed = {}

    def corner(i):
        k = where(i)
        if k not in pushed:
            n = out[k].normalized()
            pushed[k] = head.v(*(Vector(head.verts[i]) + n * line / max(min(n.dot(f) for f in facing[k]), 0.6)))
        return pushed[k]
    edges = {}
    for idx in surface:
        if not all(where(i) in out for i in idx):
            continue
        shell = [corner(i) for i in idx]
        a, b, c = (Vector(head.verts[i]) for i in shell[:3])
        head.face(shell if (b - a).cross(c - a).dot((a + b + c) / 3 - middle) < 0 else shell[::-1], goku.HEAD_LINE)
        for s, t in zip(shell, shell[1:] + shell[:1]):
            edges.setdefault(frozenset((s, t)), []).append(((a + b + c) / 3, s, t))
    inward = {}

    def behind(q):
        if q not in inward:
            p = Vector(head.verts[q])
            inward[q] = head.v(*(p + (middle - p) * 0.08))
        return inward[q]
    for seen in edges.values():
        if len(seen) == 1 and not all(head.verts[q][0] < 0.13 and head.verts[q][2] < 0.06 or head.verts[q][0] > 0.27 for q in seen[0][1:]):
            center, s, t = seen[0]
            wall = [s, t, behind(t), behind(q=s)]
            a, b, c = (Vector(head.verts[i]) for i in wall[:3])
            head.face(wall if (b - a).cross(c - a).dot(center - (a + b) / 2) > 0 else wall[::-1], goku.HEAD_LINE)
    for side in (-1, 1):
        ear_line(head, [head.faces[k][0] for k in ears if sum(head.verts[i][1] for i in head.faces[k][0]) * side > 0], middle, line)
    chin_line(head, skin)
    head.flat = set(range(len(head.faces)))


def ear_line(head, faces, middle, line):
    """The line round one ear: a thin closed box, seen from inside, a line's width past the ear's outline and set just behind it, so his cheek covers it and it shows only where his ear stands against what's behind him."""
    from mathutils import Vector
    pts = [Vector(head.verts[i]) for idx in faces for i in idx]
    center = sum(pts, Vector()) / len(pts)
    normal = Vector()
    for idx in faces:
        a, b, c = (Vector(head.verts[i]) for i in idx[:3])
        n = (b - a).cross(c - a)
        normal += n if n.dot(center - middle) > 0 else -n
    normal.normalize()
    across = normal.orthogonal().normalized()
    along = normal.cross(across)
    flat = sorted({(round((p - center).dot(across), 5), round((p - center).dot(along), 5)) for p in pts})

    def hull(points):
        out = []
        for p in points:
            while len(out) > 1 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    rim = [center + across * x + along * y for x, y in hull(flat) + hull(flat[::-1])]
    reach = sorted((p - middle).length for p in rim)[len(rim) // 2]
    top = max(p.x - center.x for p in rim)
    near = [head.v(*(p + (p - center).normalized() * line * 2.4 + normal * line * 1.2 if (p - middle).length >= reach and p.x - center.x < top * 0.5 else center + (p - center) * 0.7 - normal * 0.035)) for p in rim]
    mid = center - normal * 0.035
    deep = [head.v(*(mid + (p - center - normal * ((p - center).dot(normal))) * 0.5)) for p in rim]

    def inward(idx):
        a, b, c = (Vector(head.verts[i]) for i in idx[:3])
        head.face(tuple(idx) if (b - a).cross(c - a).dot(mid - a) > 0 else tuple(reversed(idx)), goku.HEAD_LINE)
    for k in range(len(rim)):
        n = (k + 1) % len(rim)
        inward((near[k], near[n], deep[n], deep[k]))
    inward(tuple(deep))


def chin_line(head, skin):
    """A black ribbon along the bottom of his jaw, tapering away at each end. A shell can't draw this: his chin rests so close to his chest that the shell behind it is inside his
    chest. It lies on his skin, so it never leaves it, however he turns."""
    faces = [idx for idx in skin if sum(head.verts[i][2] for i in idx) / len(idx) > 0.06]
    width, proud = 0.0055, 0.007
    span = 0.54 * max(abs(head.verts[i][1]) for idx in faces for i in idx if head.verts[i][0] < 0.11)
    steps = 12
    low, high = [], []
    for s in range(steps + 1):
        v = span * (1 - 2 * s / steps)
        hits = []
        for idx in faces:
            for a, b in zip(idx, idx[1:] + idx[:1]):
                p, q = head.verts[a], head.verts[b]
                if (p[1] - v) * (q[1] - v) <= 0 and p[1] != q[1]:
                    t = (v - p[1]) / (q[1] - p[1])
                    hits.append((p[0] + (q[0] - p[0]) * t, p[2] + (q[2] - p[2]) * t))
        lowest = min(u for u, _ in hits)
        w = max(w for u, w in hits if u < lowest + 0.012)
        here = math.sin(math.pi * s / steps) ** 0.5
        out_v, out_w = v, w - 0.08
        size = math.hypot(out_v, out_w) or 1.0
        place = (v + out_v / size * proud, w + out_w / size * proud)
        low.append(head.v(lowest - width * here, place[0], place[1]))
        high.append(head.v(lowest + width * here * 0.45, place[0], place[1]))
    for k in range(steps):
        head.face((low[k], low[k + 1], high[k + 1], high[k]), goku.OUTLINE)


EXPRESSIONS = {"Open Eyes (SKIN)": "relaxed", "Half Closed Eyes (SKIN)": "half", "Closed Eyes (SKIN)": "closed",
               "Dead Eyes (SKIN)": "dead", "Left Eyes (SKIN)": "determined", "Right Eyes (SKIN)": "shout",
               "Up Eyes (SKIN)": "surprised", "Down Eyes (SKIN)": "happy", "Blink Half Eyes (SKIN)": "blink_half",
               "Blink Eyes (SKIN)": "blink", "Smile Eyes (SKIN)": "smile", "Grit Eyes (SKIN)": "grit",
               "Fierce Eyes (SKIN)": "fierce", "Yell Eyes (SKIN)": "yell", "Hit Eyes (SKIN)": "hit", "Cheer Eyes (SKIN)": "cheer",
               "Grin Eyes (SKIN)": "grin", "Yell Left Eyes (SKIN)": "yell_left", "Yell Right Eyes (SKIN)": "yell_right"}


T_KNOTS = ((-0.06, 0.0), (0.10, 0.31), (0.34, 0.84), (0.60, 1.0))
S_KNOTS = ((0.0, 0.0), (0.62, 0.75), (1.0, 1.0))


def knots(x, ks):
    x = min(max(x, ks[0][0]), ks[-1][0])
    for (x0, y0), (x1, y1) in zip(ks, ks[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def wrap_uv(p):
    """A face vertex's UV wrapped round his head: s by how far round from his nose it is seen from the front, 0.5 at
    the nose and 0 and 1 at either side (not mirrored: the anime's faces are lopsided); t by height."""
    u, v, w = p
    return ((1 + math.copysign(knots(abs(v) / max(math.hypot(v, w), 1e-6), S_KNOTS), v)) / 2, knots(u, T_KNOTS))


def walk_rings(beside):
    """The rings in a set of open edges, each vertex mapped to the set of vertices it shares an open edge with. Two rings can
    touch at a corner, so a walk stops and files a ring as soon as it comes back to where it has been."""
    rings = []
    for start in list(beside):
        path = [start]
        while beside[path[-1]]:
            here = path[-1]
            step = beside[here].pop()
            beside[step].discard(here)
            if step in path:
                at_ring = path.index(step)
                rings.append(path[at_ring:])
                path = path[:at_ring + 1]
            else:
                path.append(step)
    return rings


def fill_hair_holes(part):
    """Reducing the hair tears holes in its shell: slivers of his face's back, or the ground beyond, show through at some
    angles. The rip's shell has one real opening, the widest, where his face goes. Every other ring of open edges on the
    shell is a tear and gets filled, nearest corners first. The hair's few loose locks are left alone."""
    import collections

    def key(i):
        return tuple(round(c, 4) for c in part.verts[i])
    at = {}
    lock = {}

    def root(k):
        lock.setdefault(k, k)
        while lock[k] != k:
            lock[k] = lock[lock[k]]
            k = lock[k]
        return k
    edges = collections.Counter()
    follows = {}
    for idx, _, _ in part.faces:
        for i in idx:
            at[key(i)] = i
        for a, b in zip(idx, idx[1:] + idx[:1]):
            ka, kb = key(a), key(b)
            if ka != kb:
                edges[tuple(sorted((ka, kb)))] += 1
                follows[(ka, kb)] = True
                lock[root(ka)] = root(kb)
    sizes = collections.Counter(root(key(idx[0])) for idx, _, _ in part.faces)
    shell = sizes.most_common(1)[0][0]
    beside = collections.defaultdict(set)
    for (a, b), n in edges.items():
        if n == 1 and root(a) == shell:
            beside[a].add(b)
            beside[b].add(a)
    rings = walk_rings(beside)

    def around(ring):
        return sum(math.dist(a, b) for a, b in zip(ring, ring[1:] + ring[:1]))
    opening = max(rings, key=around)
    for ring in rings:
        if ring is opening:
            continue
        if (ring[0], ring[1]) in follows:
            ring = ring[::-1]
        while len(ring) > 3:
            n = len(ring)
            k = min(range(n), key=lambda j: math.dist(ring[j - 1], ring[(j + 1) % n]))
            part.face([at[ring[k - 1]], at[ring[k]], at[ring[(k + 1) % n]]], goku.HAIR, None)
            ring = ring[:k] + ring[k + 1:]
        part.face([at[c] for c in ring], goku.HAIR, None)
    return part


def seal_head(part):
    """The hair and the face, reduced apart, don't quite meet: reduction cuts straight across a curve in the hair's edge, which
    leaves thin wedges between it and his skin, at his hairline, temples and nape. Through them you see into his head, down
    to his neck and the pole on his back. The wedges are filled in black, as more hair. The skin's own tears at his cheeks are
    filled in skin. The hair's loose locks are open by design, and so is the bottom of his head, where the underside goes."""
    import collections

    def key(i):
        return tuple(round(c, 3) for c in part.verts[i])
    edges = collections.defaultdict(list)
    corner = {}
    for idx, m, uv in part.faces:
        for k in range(len(idx)):
            ka, kb = key(idx[k]), key(idx[(k + 1) % len(idx)])
            corner[ka] = (idx[k], m, uv[k] if uv else None)
            if ka != kb:
                edges[tuple(sorted((ka, kb)))].append((ka, m))
    beside = collections.defaultdict(set)
    for (a, b), uses in edges.items():
        if len(uses) == 1:
            beside[a].add(b)
            beside[b].add(a)
    for ring in walk_rings(beside):
        sides = list(zip(ring, ring[1:] + ring[:1]))
        mats = {m for e in sides for _, m in edges[tuple(sorted(e))]}
        skin_only = goku.HAIR not in mats
        if mats == {goku.HAIR} or (skin_only and min(p[0] for p in ring) < 0.03):
            continue
        if edges[tuple(sorted(sides[0]))][0][0] == ring[0]:
            ring = ring[::-1]
        mat = next(m for _, m, _ in map(corner.get, ring) if m != goku.HAIR) if skin_only else goku.HAIR

        def fill(a, b, c):
            part.face([corner[p][0] for p in (a, b, c)], mat, [corner[p][2] for p in (a, b, c)] if skin_only else None)
        while len(ring) > 3:
            n = len(ring)
            k = min(range(n), key=lambda j: math.dist(ring[j - 1], ring[(j + 1) % n]))
            fill(ring[k - 1], ring[k], ring[(k + 1) % n])
            ring = ring[:k] + ring[k + 1:]
        fill(*ring)
    return part


def close_cracks(part, tol=0.012):
    """Reduced apart, the hair and the face can disagree along their border: one keeps a vertex the other dropped,
    and the hair's dark inside shows through the crack (a black line across his forehead). Each border edge with
    another border vertex lying on it is split there, so both sides meet exactly."""
    import collections
    for _ in range(4):
        count = collections.Counter()
        for idx, _, _ in part.faces:
            for k in range(len(idx)):
                count[tuple(sorted((idx[k], idx[(k + 1) % len(idx)])))] += 1
        border = [e for e, n in count.items() if n == 1]
        points = {i for e in border for i in e}
        split = {}
        for a, b in border:
            A, B = Vector(part.verts[a]), Vector(part.verts[b])
            ab = B - A
            for p in points:
                P = Vector(part.verts[p])
                if p in (a, b) or (P - A).length < 1e-6 or (P - B).length < 1e-6:
                    continue
                t = (P - A).dot(ab) / ab.length_squared
                if 0.02 < t < 0.98 and (A + ab * t - P).length < tol:
                    split[(a, b)] = (p, t)
                    break
        if not split:
            return fill_slivers(part)
        faces = []
        for idx, m, uv in part.faces:
            for k in range(len(idx)):
                a, b = idx[k], idx[(k + 1) % len(idx)]
                hit = split.get((a, b)) or split.get((b, a))
                if hit and len(idx) == 3:
                    p, t = hit
                    if (b, a) in split:
                        t = 1 - t
                    c = idx[(k + 2) % 3]
                    q = part.v(*part.verts[p])
                    if uv:
                        ua, ub, uc = uv[k], uv[(k + 1) % 3], uv[(k + 2) % 3]
                        um = (ua[0] + (ub[0] - ua[0]) * t, ua[1] + (ub[1] - ua[1]) * t)
                        faces += [((a, q, c), m, [ua, um, uc]), ((q, b, c), m, [um, ub, uc])]
                    else:
                        faces += [((a, q, c), m, None), ((q, b, c), m, None)]
                    break
            else:
                faces.append((idx, m, uv))
        part.faces = faces
    return fill_slivers(part)


def fill_slivers(part, most=6):
    """The face's reduction can also leave a thin hole, its few border edges all its own (one runs across his
    forehead). Small holes ringed only by textured edges are filled, each corner keeping the UVs of the triangle
    beside it; a triangle left touching nothing is dropped."""
    def key(i):
        return tuple(round(c, 4) for c in part.verts[i])
    half = {}
    for idx, m, uv in part.faces:
        for k in range(len(idx)):
            a, b = idx[k], idx[(k + 1) % len(idx)]
            half[(key(a), key(b))] = (a, uv[k] if uv else None, m)
    start = {}
    for (ka, kb), info in half.items():
        if (kb, ka) not in half:
            start[ka] = (kb, info)
    seen, fills = set(), []
    lone, stray = {frozenset(map(key, idx)) for idx, _, _ in part.faces}, set()
    for k0 in list(start):
        if k0 in seen:
            continue
        loop, k = [], k0
        while k in start and k not in seen and len(loop) <= most:
            seen.add(k)
            nxt, info = start[k]
            loop.append(info)
            k = nxt
        if k != k0 or not 3 <= len(loop) <= most or any(m != loop[0][2] or uv is None for _, uv, m in loop):
            continue
        if frozenset(key(v) for v, _, _ in loop) in lone:
            stray.add(frozenset(key(v) for v, _, _ in loop))
            continue
        ring = list(reversed(loop))
        for i in range(1, len(ring) - 1):
            c = (ring[0], ring[i], ring[i + 1])
            fills.append(([v for v, _, _ in c], ring[0][2], [uv for _, uv, _ in c]))
    part.faces = [f for f in part.faces if frozenset(map(key, f[0])) not in stray] + fills
    return part


def scaled(part, k):
    part.verts = [(u * k, v * k, w * k) for u, v, w in part.verts]
    return part


HAIR_DEGREES = 36
FACE_DEGREES = 26


def world_frames(pose):
    """Each animated bone's rotation in the standing frame (x his left, y back, z up) for an anims pose."""
    loc = anims.local_rotations(anims.full(pose))
    w = {"Body": anims.R0 @ anims.BODY}
    for b in anims.ORDER[1:]:
        w[b] = w[anims.PARENT[b]] @ loc[b]
    return w


def solve(pose, bone, key, target, ranges):
    """Search pose[key]'s leading angles (within ranges) so bone's X axis points along target; returns the error in
    degrees. A coarse grid, then a shrinking-step local search."""
    target = target.normalized()
    cur = pose.get(key, anims.STAND[key])
    n = len(ranges)
    lead = list(cur[:n]) if isinstance(cur, tuple) else [cur]

    def err(vals):
        p = dict(pose)
        p[key] = (tuple(vals) + tuple(cur[n:])) if isinstance(cur, tuple) else vals[0]
        return world_frames(p)[bone].col[0].angle(target)
    import itertools
    grid = [[lo + (hi - lo) * k / 8 for k in range(9)] for lo, hi in ranges]
    best = min((list(c) for c in itertools.product(*grid)), key=err)
    step = (ranges[0][1] - ranges[0][0]) / 8
    e = err(best)
    while step > 0.05:
        moved = False
        for i in range(n):
            for d in (-step, step):
                trial = list(best)
                trial[i] += d
                te = err(trial)
                if te < e:
                    best, e, moved = trial, te, True
        if not moved:
            step /= 2
    pose[key] = (tuple(best) + tuple(cur[n:])) if isinstance(cur, tuple) else best[0]
    return math.degrees(e)


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    rip, out, rig_path = args[0], args[1], args[2]
    texdir = args[3]
    preview_dir = args[4] if len(args) > 4 else None
    crops = json.load(open(os.path.join(texdir, "crops.json")))
    faces = crops.pop("faces")
    crops = {int(k): v for k, v in crops.items()}

    data = json.load(open(rip))
    s = HEIGHT / RIP_HEAD_TOP
    jp = {k: Vector(data["joints"][str(n)]) * s for k, n in J.items()}

    pose = {"pelvis": (0, 0, 0), "torso": (0, 0, 0), "head": (0, 0, 0)}
    report = []
    for side, s_ in (("l", "Left"), ("r", "Right")):
        report.append(solve(pose, f"{s_} Arm", f"{side}_arm", jp[f"{side}_elbow"] - jp[f"{side}_shoulder"],
                            [(-60, 60), (0, 140)]))
        report.append(solve(pose, f"{s_} Forearm", f"{side}_elbow", jp[f"{side}_wrist"] - jp[f"{side}_elbow"],
                            [(-30, 120)]))
        report.append(solve(pose, f"{s_} Hand", f"{side}_hand", jp[f"{side}_knuckle"] - jp[f"{side}_wrist"],
                            [(-80, 80), (-80, 80)]))
        report.append(solve(pose, f"{s_} Thigh", f"{side}_hip", jp[f"{side}_knee"] - jp[f"{side}_hip"],
                            [(-40, 40), (-20, 40)]))
        report.append(solve(pose, f"{s_} Leg", f"{side}_knee", jp[f"{side}_ankle"] - jp[f"{side}_knee"], [(-30, 60)]))
        pose[f"{side}_foot"] = 0
    W = world_frames(pose)
    print("fit errors (deg):", [round(e, 2) for e in report])

    def rest_offset(parent, child_pos, parent_pos):
        lx, ly, lz = W[parent].transposed() @ (child_pos - parent_pos)
        return (lx, -lz, ly)

    rest = {
        "Torso": rest_offset("Butt", jp["waist"], jp["hips"]),
        "Head": rest_offset("Torso", jp["neck"], jp["waist"]),
        "Left Arm": rest_offset("Torso", jp["l_shoulder"], jp["waist"]),
        "Right Arm": rest_offset("Torso", jp["r_shoulder"], jp["waist"]),
        "Left Arm Color": (0, 0, 0), "Right Arm Color": (0, 0, 0),
        "Left Forearm": rest_offset("Left Arm", jp["l_elbow"], jp["l_shoulder"]),
        "Right Forearm": rest_offset("Right Arm", jp["r_elbow"], jp["r_shoulder"]),
        "Left Hand": rest_offset("Left Forearm", jp["l_wrist"], jp["l_elbow"]),
        "Right Hand": rest_offset("Right Forearm", jp["r_wrist"], jp["r_elbow"]),
        "Left Thigh": rest_offset("Butt", jp["l_hip"], jp["hips"]),
        "Right Thigh": rest_offset("Butt", jp["r_hip"], jp["hips"]),
        "Left Thigh Color": (0, 0, 0), "Right Thigh Color": (0, 0, 0),
        "Left Leg": rest_offset("Left Thigh", jp["l_knee"], jp["l_hip"]),
        "Right Leg": rest_offset("Right Thigh", jp["r_knee"], jp["r_hip"]),
        "Left Shoe": rest_offset("Left Leg", jp["l_ankle"], jp["l_knee"]),
        "Right Shoe": rest_offset("Right Leg", jp["r_ankle"], jp["r_knee"]),
    }
    anims.REST = rest
    pos = {"Butt": jp["hips"], "Torso": jp["waist"], "Head": jp["neck"], "Left Arm": jp["l_shoulder"],
           "Right Arm": jp["r_shoulder"], "Left Forearm": jp["l_elbow"], "Right Forearm": jp["r_elbow"],
           "Left Hand": jp["l_wrist"], "Right Hand": jp["r_wrist"], "Left Thigh": jp["l_hip"],
           "Right Thigh": jp["r_hip"], "Left Leg": jp["l_knee"], "Right Leg": jp["r_knee"],
           "Left Shoe": jp["l_ankle"], "Right Shoe": jp["r_ankle"]}

    vbone = [MAP.get(n) for _, n in data["verts"]]
    vpos = [Vector(p) * s for p, _ in data["verts"]]
    parts: dict[str, goku.Part] = {}
    remap: dict[tuple[str, int], int] = {}
    for tri, uvs, mi in data["tris"]:
        bones = [vbone[i] for i in tri]
        if any(b is None for b in bones):
            continue
        bone = max(set(bones), key=bones.count)
        frame = FRAME_OF.get(bone, bone)
        part = parts.setdefault(bone, goku.Part())
        Wb = W[frame].transposed()
        idx = []
        for vi in tri:
            key = (bone, vi)
            if key not in remap:
                lx, ly, lz = Wb @ (vpos[vi] - pos[frame])
                remap[key] = part.v(lx, -lz, ly)
            idx.append(remap[key])
        c = crops[mi]
        if "vertex" in c:
            part.face(idx, goku.SKIN)
            continue
        u0, v0, u1, v1 = c["uv"]
        part.face(idx, f"BT3 {mi}", [((u - u0) / (u1 - u0), (v - v0) / (v1 - v0)) for u, v in uvs])

    def rip_hand(side, shape):
        """His open hand and peace sign, built (body.hand) to Tenkaichi's hand, which Metal Fox picked: the rip's hand
        posed, "open" as it is, "peace" with the ring and little fingers curled, the thumb over them and the other two
        spread in a V (each finger turns about its own joints: the thumb, then index to little finger, two joints each,
        off the wrist), then measured. His fists stay body.fist: folded, the rip's hand opened gaps, and fists are on
        screen all the time."""
        o = 0 if side == "Left" else -14
        thumb, fingers = 36 + o, [(37 + o, 38 + o), (39 + o, 40 + o), (41 + o, 42 + o), (43 + o, 44 + o)]
        hand = set(range(35 + o, 46 + o))
        joint = {n: Vector(data["joints"][str(n)]) * s for n in hand}
        palm = Vector((0, 0, -1))
        curled = {"open": set(), "peace": {2, 3}}[shape]
        posed = {}
        tris = [(t, uvs, mi) for t, uvs, mi in data["tris"] if sum(data["verts"][i][1] in hand for i in t) >= 2]
        for t, _, _ in tris:
            for vi in t:
                posed.setdefault(vi, vpos[vi].copy())

        def turn(nodes, center, axis, deg):
            m = Matrix.Rotation(math.radians(deg), 3, axis)
            for vi, p in posed.items():
                if data["verts"][vi][1] in nodes:
                    posed[vi] = m @ (p - center) + center
            for n in nodes:
                joint[n] = m @ (joint[n] - center) + center
        for k, (a, b) in enumerate(fingers):
            fdir = (joint[b] - joint[a]).normalized()
            if k in curled:
                turn({a, b}, joint[a], fdir.cross(palm).normalized(), 80)
                turn({b}, joint[b], (joint[b] - joint[a]).normalized().cross(palm).normalized(), 95)
            elif shape == "peace":
                turn({a, b}, joint[a], palm, 16 if k == 0 else -16)
        if shape != "open":
            tdir = (joint[thumb] - joint[35 + o]).normalized()
            turn({thumb}, joint[thumb], tdir.cross(palm).normalized() * (1 if side == "Left" else -1), 35)
        frame = FRAME_OF[f"{side} Hand DL"]
        Wb = W[frame].transposed()

        def local(p):
            lx, ly, lz = Wb @ (p - pos[frame])
            return Vector((lx, -lz, ly))
        node_verts = {}
        for vi, p in posed.items():
            node_verts.setdefault(data["verts"][vi][1], []).append(local(p))
        chains = []
        for k, (a, b) in enumerate([(thumb, thumb)] + fingers):
            base, mid = local(joint[a]), local(joint[b])
            pts = node_verts.get(b, []) or node_verts.get(a, [])
            tip = max(pts, key=lambda q: (q - base).length)
            axis = (tip - base).normalized()
            r = sorted((q - base - axis * (q - base).dot(axis)).length for q in node_verts.get(a, pts))
            r = r[len(r) // 2] if r else 0.02
            chains.append(([base, mid, tip] if k - 1 in curled else [base, tip], r))
        palm = [q for q in node_verts.get(35 + o, []) + node_verts.get(45 + o, []) if q.x > -0.02]
        lo = Vector(tuple(min(q[i] for q in palm) for i in range(3)))
        hi = Vector(tuple(max(q[i] for q in palm) for i in range(3)))
        return body.hand((lo + hi) / 2, (hi - lo) / 2, chains, shape)
    for side in ("Left", "Right"):
        for b in (f"{side} Thigh Color", f"{side} Leg"):
            parts[b].verts = [(u * LEG, v, w) for u, v, w in parts[b].verts]
        for b in (f"{side} Leg", f"{side} Shoe"):
            ox, oy, oz = rest[b]
            rest[b] = (ox * LEG, oy, oz)
    parts["Torso"].verts = [(u * TORSO, v, w) for u, v, w in parts["Torso"].verts]
    for b in ("Head", "Left Arm", "Right Arm"):
        ox, oy, oz = rest[b]
        rest[b] = (ox * TORSO, oy, oz)
    for side in ("Left", "Right"):
        for b in (f"{side} Arm Color", f"{side} Forearm"):
            parts[b].verts = [(u * ARM, v, w) for u, v, w in parts[b].verts]
        for b in (f"{side} Forearm", f"{side} Hand"):
            ox, oy, oz = rest[b]
            rest[b] = (ox * ARM, oy, oz)
    for side in ("Left", "Right"):
        b = f"{side} Shoe" if side == "Left" else "Right Shoe DL"
        parts[b].verts = [(u * SHOE_SCALE, v * SHOE_SCALE, w * SHOE_SCALE) for u, v, w in parts[b].verts]
    parts["Head DL"].verts = [(u * HEAD_SCALE, v * HEAD_SCALE, w * HEAD_SCALE) for u, v, w in parts["Head DL"].verts]
    for side in ("Left", "Right"):
        ox, oy, oz = rest[f"{side} Arm"]
        rest[f"{side} Arm"] = (ox, oy * 0.85, oz)
    for b in ("Left Shoe", "Right Shoe DL"):
        parts[b].verts = [(u, v, w * 0.75) for u, v, w in parts[b].verts]
    rebuild_n64(parts, rest)
    shoe = parts["Left Shoe"]
    low = max(w for _, _, w in shoe.verts) + LINE_OFF_GROUND
    xs = [u for u, _, w in shoe.verts if w > low - 0.04]
    sole = [(min(xs), low), ((min(xs) + max(xs)) / 2, low), (max(xs), low)]
    with open(rig_path, "w") as f:
        json.dump({"REST": rest, "SOLE": sole}, f, indent=1)
    head = parts["Head DL"]
    head.sinks = False
    ears = [k for k, (idx, m, _) in enumerate(head.faces)
            if m == "BT3 8" and sum(abs(head.verts[i][1]) for i in idx) / len(idx) > ear.FROM_SIDE]
    for idx, m, _ in head.faces:
        if m == G_HAIR:
            for i in idx:
                up, side, front = head.verts[i]
                if up < 0.16 and abs(side) > 0.2 and front > -0.06:
                    head.verts[i] = (0.2, side * 0.95, front - 0.045)
    plain_backs = set()
    for k in ears:
        idx = head.faces[k][0]
        head.faces[k] = (idx, EAR, [ear.uv(head.verts[i]) for i in idx])
        back = [head.v(*ear.behind(head.verts[i])) for i in idx]
        head.flat.add(len(head.faces))
        plain_backs.add(len(head.faces))
        head.face(back[::-1], EAR, [ear.PLAIN] * len(idx))
    head.faces = [(idx, EAR, [ear.PLAIN] * len(idx))
                  if m in ("BT3 5", "BT3 9") or m == "BT3 8" and sum(head.verts[i][2] for i in idx) / len(idx) < ear.BEHIND
                  else (idx, m, uv) for idx, m, uv in head.faces]
    plain = lambda k, idx, m, uv: m == EAR and uv == [ear.PLAIN] * len(idx) and k not in plain_backs and sum(head.verts[i][2] for i in idx) / len(idx) < ear.NAPE
    low = lambda idx: sum(head.verts[i][0] for i in idx) / len(idx) < ear.BELOW
    tucked = {k for k, (idx, m, uv) in enumerate(head.faces) if plain(k, idx, m, uv) and low(idx)}
    head.faces = [(idx, G_HAIR, None) if plain(k, idx, m, uv) and k not in tucked else (idx, m, uv)
                  for k, (idx, m, uv) in enumerate(head.faces)]
    for i in {i for k in tucked for i in head.faces[k][0]}:
        up, side, front = head.verts[i]
        if front < ear.NAPE:
            head.verts[i] = (up, side * 0.72, front)
        head.soft[i] = NECK_SHADE
    for k, (idx, m, uv) in enumerate(head.faces):
        if m == EAR and uv == [ear.PLAIN] * len(idx) and sum(head.verts[i][0] for i in idx) / len(idx) < ear.BELOW:
            head.soft.update({i: NECK_SHADE for i in idx})
            head.faces[k] = (idx, goku.SKIN, None)
    wrapped = [(idx, m, uv, [wrap_uv(head.verts[i]) for i in idx] if m == "BT3 8" else uv) for idx, m, uv in head.faces]
    face = {"verts": head.verts, "faces": [(i, m, uv0, uv) for i, m, uv0, uv in wrapped if m == "BT3 8"],
            "rest": [(i, m) for i, m, _, _ in wrapped if m != "BT3 8"]}
    with open(os.path.join(os.path.dirname(rig_path), "goku-face.json"), "w") as f:
        json.dump(face, f)
    edges = head_light.outline(face)
    toward = tuple(float(c) for c in head_light.LIGHT)
    for idx, m, _ in head.faces:
        if m == EAR:
            for i, away in zip(idx, head_light.turned_away(edges, [head.verts[i] for i in idx])):
                head.soft.setdefault(i, tuple(-c for c in toward) if away else toward)
    head.faces = [(idx, goku.FACE if m == "BT3 8" else m, uv) for idx, m, _, uv in wrapped]
    outline_head(head, set(ears), plain_backs)
    print("parts:", {b: sum(len(f) - 2 for f, _, _ in p.faces) for b, p in parts.items()})

    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    goku.setup_materials()
    for k, c in crops.items():
        if "file" not in c:
            continue
        m = createF3DMat(None, "Shaded Texture")
        m.name = f"BT3 {k}"
        f = m.f3d_mat
        f.rdp_settings.g_lighting = False
        f.rdp_settings.g_cull_back = False
        img = bpy.data.images.load(c["file"], check_existing=True)
        img.name = f"goku_n64_{k}.ci4.png"
        f.tex0.tex = img
        f.tex0.tex_format = "CI4"
        f.tex0.ci_format = "RGBA16"
        f.tex0.S.clamp, f.tex0.T.clamp = False, False
        f.tex0.S.mirror = bool(c.get("mirror"))
        goku.COLORS[m.name] = ("FFFFFF", "FFFFFF") if k == 8 else ("FFFFFF", "C9C2DA")

    m = createF3DMat(None, "Shaded Texture")
    m.name = EAR
    m.f3d_mat.rdp_settings.g_lighting = False
    m.f3d_mat.rdp_settings.g_cull_back = False
    img = bpy.data.images.load(os.path.join(texdir, "goku_n64_ear.ci4.png"), check_existing=True)
    m.f3d_mat.tex0.tex = img
    m.f3d_mat.tex0.tex_format = "CI4"
    m.f3d_mat.tex0.ci_format = "RGBA16"
    m.f3d_mat.tex0.S.clamp, m.f3d_mat.tex0.T.clamp = True, True
    goku.COLORS[EAR] = ("FFFFFF", "DAB3A8")

    more_faces = ("Blink Half Eyes (SKIN)", "Blink Eyes (SKIN)", "Smile Eyes (SKIN)", "Grit Eyes (SKIN)", "Fierce Eyes (SKIN)",
                  "Yell Eyes (SKIN)", "Hit Eyes (SKIN)", "Cheer Eyes (SKIN)", "Grin Eyes (SKIN)", "Yell Left Eyes (SKIN)",
                  "Yell Right Eyes (SKIN)")
    open_eyes = bpy.data.materials["Open Eyes (SKIN)"]
    for mat in more_faces:
        open_eyes.copy().name = mat
    for armature, switch in (("Mario", "Eye State Switch"), ("Capless Head", "Capless Head Eye State Switch")):
        options = bpy.data.objects[armature].data.bones[switch].switch_options
        for mat in more_faces:
            option = options.add()
            option.switchType, option.materialOverrideType = "Material", "Specific"
            option.materialOverride = bpy.data.materials[mat]
            option.specificOverrideArray.add().material = open_eyes

    for mat, name in EXPRESSIONS.items():
        f = bpy.data.materials[mat].f3d_mat
        f.rdp_settings.g_lighting = False
        f.rdp_settings.g_cull_back = False
        img = bpy.data.images.load(faces[name], check_existing=True)
        f.tex0.tex = img
        f.tex0.tex_format = "CI4"
        f.tex0.ci_format = "RGBA16"
        f.tex0.S.clamp, f.tex0.T.clamp = True, False
        f.tex0.S.mirror, f.tex0.T.mirror = False, False
        goku.COLORS[mat] = goku.COLORS["BT3 8"]
    goku.COLORS.update(TENKAICHI)
    if goku.OUTFIT == "pilaf":
        goku.COLORS.update(PILAF)
    rope = createF3DMat(None, "Shaded Solid")
    rope.name = "Rope"
    rope.f3d_mat.rdp_settings.g_lighting = False
    bpy.data.materials[goku.HAIR].f3d_mat.rdp_settings.g_cull_back = False
    goku.ramp_materials(texdir)
    goku.chibi_skeleton("Mario")
    goku.chibi_skeleton("Metal Mario")
    main_parts = {b: (lambda p=p: p) for b, p in parts.items()}
    goku.build(bpy.data.objects["Mario Mesh"], main_parts, rewind=True)
    goku.build(bpy.data.objects["Metal Mario Mesh"], dict(main_parts), goku.METAL, rewind=True)
    extra = {"Capless Head Mesh": {"Capless Head": parts["Head DL"]},
             "Left Hand Open Mesh": {"Left Hand Open": rip_hand("Left", "open")},
             "Right Hand Open Mesh": {"Right Hand Open": rip_hand("Right", "open")},
             "Right Hand Peace Mesh": {"Right Hand Peace": rip_hand("Right", "peace")},
             "Right Hand Cap Mesh": {"Right Hand Cap": body.fist_with_pole(swung=True)},
             "Right Hand Wing Cap Mesh": {"Right Hand Wing Cap": body.fist_with_pole()}}
    for name, ps in extra.items():
        mk = {b: (lambda p=p: p) for b, p in ps.items()}
        goku.build(bpy.data.objects[name], mk, rewind=True)
        metal = bpy.data.objects.get("Metal " + name)
        if metal:
            goku.build(metal, dict(mk), goku.METAL, rewind=True)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(out)), "goku.blend"), copy=True)
    if preview_dir:
        goku.preview(preview_dir)
        return 0
    bpy.context.scene.gameEditorMode = "SM64"
    bpy.context.scene.f3d_type = "F3D"
    sm64 = bpy.context.scene.fast64.sm64
    sm64.export_type = "C"
    props = sm64.combined_export
    props.export_header_type = "Custom"
    os.makedirs(out, exist_ok=True)
    props.custom_export_path = os.path.abspath(out)
    props.object_name = "goku"
    bpy.context.scene.saveTextures = True
    rig = bpy.data.objects["Mario"]
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    result = bpy.ops.object.sm64_export_geolayout_armature(export_obj=rig.name)
    if "FINISHED" not in result:
        raise RuntimeError(f"export failed: {result}")
    print("exported goku ->", os.path.join(out, "goku"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
