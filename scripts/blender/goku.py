"""Build Kid Goku on Mario's skeleton and export him as the goku_geo actor (runs inside Blender).

Usage:
  blender -b TEMPLATE.blend --python scripts/blender/goku.py -- OUT_ACTORS_DIR [SAVE.blend] [PREVIEW_DIR]

TEMPLATE.blend is Character Select's pack template (its Mario armature and switch layout); every mesh in it is
replaced. He is modelled after Tenkaichi 3's Kid Goku, built N64-style: lofted low-poly parts, a face texture, and
two-tone cel shading baked into the vertex colors with lighting off (palettes don't apply). PREVIEW_DIR gets front,
side and back renders in his standing pose, for checking shapes against the reference before export.

Parts are written in each bone's rest frame, which lies the figure down along +X:
  u along the bone (up the body, down each limb), v to his right, w to his front (for the shoe: toward the sole).
Units are Blender units, about 53 SM64 units each.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
from mathutils import Vector

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
TEX = os.path.join(ROOT, "art", "textures")


def rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


GI, GI_EDGE, SKIN, HAIR, BELT, BAND, SHOE, SOCK, POLE, KANJI, WING, OUTLINE = (
    "Gi", "Gi Edge", "Skin", "Hair", "Belt", "Wristband", "Shoe", "Sock", "Pole", "Kanji", "Wing", "Outline")
POLE_LINE = "Pole Line"
HEAD_LINE = "Head Line"
FACE = "Open Eyes (SKIN)"
OUTFIT = os.environ.get("GOKU_OUTFIT", "pilaf")
FACE_SET = os.environ.get("GOKU_FACE", "tenkaichi")
SHADING = os.environ.get("GOKU_SHADING", "gouraud")
OUTLINES = os.environ.get("GOKU_OUTLINE", "1") == "1"
OUTFITS = {
    "pilaf": {GI: ("3C3FD0", "2A2290"), GI_EDGE: ("3036B8", "21207E"), BELT: ("F2F2F2", "B8BCD0"),
              BAND: ("E0352B", "9C1F18"), SHOE: ("2B2F6E", "171A44"), SOCK: ("3C3FD0", "2A2290")},
    "turtle": {GI: ("DA4A2B", "992C1B"), GI_EDGE: ("B53A22", "7A2214"), BELT: ("1E1E22", "0C0C0E"),
               BAND: ("3060C0", "1C3C82"), SHOE: ("2D52A8", "1A3170"), SOCK: ("F2F0EA", "BDBAB2")},
}
COLORS = {
    GI: ("E4481F", "A12812"), GI_EDGE: ("B5321A", "7E1C0C"), SKIN: ("F6BF8E", "D08A5C"), HAIR: ("26262F", "0C0C14"),
    BELT: ("23264A", "11132A"), BAND: ("2E55B0", "1B3272"), SHOE: ("2B3C7E", "17224C"), SOCK: ("F4F4F4", "B9BCCB"),
    POLE: ("C8392B", "7E1E15"), KANJI: ("F4E7B6", "D9C58C"), WING: ("FAFAFA", "C8C8D2"), FACE: ("EFB07C", "BF7C4E"),
    OUTLINE: ("0A0A0E", "0A0A0E"), POLE_LINE: ("0A0A0E", "0A0A0E"), HEAD_LINE: ("0A0A0E", "0A0A0E"),
}
COLORS.update(OUTFITS[OUTFIT])
COLORS[FACE] = COLORS[SKIN]
EYE_MATS = {"Open Eyes (SKIN)": "open", "Half Closed Eyes (SKIN)": "half", "Closed Eyes (SKIN)": "closed",
            "Dead Eyes (SKIN)": "dead", "Left Eyes (SKIN)": "open", "Right Eyes (SKIN)": "open",
            "Up Eyes (SKIN)": "open", "Down Eyes (SKIN)": "open"}
METAL = "Metal (METAL)"


class Part:
    """Polygons in one bone's frame, each with a material and optional UVs."""

    def __init__(self):
        self.verts: list[tuple[float, float, float]] = []
        self.faces: list[tuple[list[int], str, list | None]] = []
        self.flat: set[int] = set()
        self.soft: dict[int, tuple] = {}
        self.around: dict[int, tuple] = {}
        self.sinks = True
        self.tucks: set[int] = set()

    def v(self, u, v, w):
        self.verts.append((u, v, w))
        return len(self.verts) - 1

    def face(self, idx, mat, uv=None, flat=False):
        self.faces.append((list(idx), mat, uv))
        if flat:
            self.flat.add(len(self.faces) - 1)


def loft(p: Part, stations, sides, mat, cap0=False, cap1=False, phase=0.5, mats=None):
    """Elliptical rings along u. stations: (u, half-width v, half-depth w[, center v, center w])."""
    rings = []
    for st in stations:
        u, rv, rw = st[:3]
        cv, cw = (st[3], st[4]) if len(st) > 3 else (0.0, 0.0)
        rings.append([p.v(u, cv + math.cos(2 * math.pi * (k + phase) / sides) * rv,
                          cw + math.sin(2 * math.pi * (k + phase) / sides) * rw) for k in range(sides)])
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        m = mats[i] if mats else mat
        for k in range(sides):
            n = (k + 1) % sides
            p.face((a[k], a[n], b[n], b[k]), m)
    if cap0:
        p.face(list(reversed(rings[0])), mat)
    if cap1:
        p.face(rings[-1], mat)
    return rings


def blob(p: Part, c, r, segs, rings, mat, shape=None, keep=None, uv_of=None, mat_of=None):
    """A UV sphere; shape(u, v, w) reshapes each vertex, keep(face center) drops faces, uv_of maps textured faces."""
    pts = [(c[0] + r[0], c[1], c[2]), (c[0] - r[0], c[1], c[2])]
    for i in range(1, rings):
        t = math.pi * i / rings
        for k in range(segs):
            a = 2 * math.pi * k / segs
            pts.append((c[0] + r[0] * math.cos(t), c[1] + r[1] * math.sin(t) * math.cos(a),
                        c[2] + r[2] * math.sin(t) * math.sin(a)))
    if shape:
        pts = [shape(*q) for q in pts]
    base = len(p.verts)
    for q in pts:
        p.v(*q)
    top, bot = base, base + 1
    row = lambda i, k: base + 2 + (i - 1) * segs + (k % segs)
    quads = []
    for k in range(segs):
        quads.append((top, row(1, k + 1), row(1, k)))
        quads.append((bot, row(rings - 1, k), row(rings - 1, k + 1)))
    for i in range(1, rings - 1):
        for k in range(segs):
            quads.append((row(i, k), row(i, k + 1), row(i + 1, k + 1), row(i + 1, k)))
    for q in quads:
        cen = tuple(sum(p.verts[j][x] for j in q) / len(q) for x in range(3))
        if keep and not keep(cen):
            continue
        m = mat_of(cen) if mat_of else mat
        uv = [uv_of(p.verts[j]) for j in q] if (uv_of and m == FACE) else None
        p.face(q, m, uv)


def spike(p: Part, base, tip, width, thick, out, bend=0.0, mat=HAIR, sides=6):
    """A hair spike: a soft, flattened cone swept from base to tip. out is the way its broad side faces; bend pushes
    its middle outward so it curves like a brushed clump."""
    base, tip, out = Vector(base), Vector(tip), Vector(out).normalized()
    axis = tip - base
    side = axis.cross(out).normalized()
    flat = side.cross(axis).normalized()
    rings = []
    for t, scale in ((0.0, 1.0), (0.38, 0.80), (0.72, 0.45)):
        center = base + axis * t + flat * bend * math.sin(math.pi * t)
        rings.append([p.v(*(center + side * math.cos(2 * math.pi * k / sides) * width * scale
                            + flat * math.sin(2 * math.pi * k / sides) * thick * scale)) for k in range(sides)])
    tp = p.v(*tip)
    for a_, b_ in zip(rings, rings[1:]):
        for k in range(sides):
            n = (k + 1) % sides
            p.face((a_[k], a_[n], b_[n], b_[k]), mat)
    for k in range(sides):
        p.face((rings[-1][k], rings[-1][(k + 1) % sides], tp), mat)


def box(p: Part, c, half, mat):
    cu, cv, cw = c
    hu, hv, hw = half
    q = [p.v(cu + su * hu, cv + sv * hv, cw + sw * hw) for su in (-1, 1) for sv in (-1, 1) for sw in (-1, 1)]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        p.face([q[i] for i in f], mat)


def disc(p: Part, c, normal, up, r, sides, mat):
    """A flat polygon facing normal, its texture upright along up."""
    c, n, up = Vector(c), Vector(normal).normalized(), Vector(up).normalized()
    right = up.cross(n).normalized()
    up = n.cross(right).normalized()
    idx, uvs = [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        idx.append(p.v(*(c + (right * math.cos(a) + up * math.sin(a)) * r)))
        uvs.append((0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)))
    p.face(idx, mat, uvs, flat=True)


def tube(p: Part, a, b, r, sides, mat):
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    s = axis.orthogonal().normalized()
    o = axis.cross(s)
    ring = [s * math.cos(2 * math.pi * k / sides) + o * math.sin(2 * math.pi * k / sides) for k in range(sides)]
    ra = [p.v(*(a + d * r)) for d in ring]
    rb = [p.v(*(b + d * r)) for d in ring]
    for k in range(sides):
        n = (k + 1) % sides
        p.face((ra[k], ra[n], rb[n], rb[k]), mat)
    p.face(list(reversed(ra)), mat)
    p.face(rb, mat)



def pelvis():
    p = Part()
    loft(p, [(-0.20, 0.31, 0.24), (-0.10, 0.35, 0.27), (0.04, 0.35, 0.27), (0.14, 0.32, 0.24), (0.22, 0.30, 0.215)],
         14, GI, cap0=True)
    loft(p, [(0.10, 0.315, 0.235), (0.21, 0.305, 0.225)], 14, BELT)
    blob(p, (0.15, 0.0, 0.235), (0.055, 0.065, 0.045), 8, 5, BELT)
    for s_ in (-1, 1):
        a, b = p.v(0.12, s_ * 0.015, 0.27), p.v(0.12, s_ * 0.08, 0.27)
        c, d = p.v(-0.36, s_ * 0.13, 0.30), p.v(-0.36, s_ * 0.05, 0.305)
        p.face((a, b, c, d), BELT, flat=True)
        p.face((d, c, b, a), BELT, flat=True)
    return p


def torso():
    p = Part()
    loft(p, [(-0.06, 0.31, 0.22), (0.08, 0.33, 0.22), (0.20, 0.35, 0.21), (0.30, 0.31, 0.18), (0.36, 0.16, 0.11)],
         14, GI, cap1=True)
    p.face((p.v(0.36, -0.07, 0.115), p.v(0.12, 0.02, 0.208), p.v(0.36, 0.06, 0.115)), SKIN, flat=True)
    p.face((p.v(0.36, -0.10, 0.11), p.v(0.36, -0.065, 0.12), p.v(0.10, 0.035, 0.212), p.v(0.09, 0.0, 0.208)), GI_EDGE,
           flat=True)
    loft(p, [(0.30, 0.08, 0.075), (0.42, 0.076, 0.07)], 8, SKIN)
    for s_ in (-1, 1):
        blob(p, (0.26, s_ * 0.32, -0.01), (0.09, 0.085, 0.09), 8, 5, SKIN)
    if OUTFIT == "turtle":
        disc(p, (0.12, 0, -0.225), (0, 0, -1), (1, 0, 0), 0.14, 12, KANJI)
        disc(p, (0.21, -0.15, 0.226), (0, -0.25, 1), (1, 0, 0), 0.065, 10, KANJI)
    tube(p, (0.36, 0.17, 0.10), (-0.02, -0.22, 0.21), 0.012, 4, SOCK)
    tube(p, (-0.18, -0.22, -0.24), (0.62, 0.22, -0.27), 0.034, 6, POLE)
    return p


HEAD_C = (0.31, 0.0, 0.03)
HEAD_R = (0.30, 0.33, 0.31)


def head_shape(u, v, w):
    """A kid's round head: full cranium and cheeks, a small rounded chin."""
    if u < HEAD_C[0]:
        t = (HEAD_C[0] - u) / HEAD_R[0]
        v *= 1 - 0.30 * t ** 1.7
        w = (w - HEAD_C[2]) * (1 - 0.10 * t) + HEAD_C[2] + 0.04 * t * (1 if w > HEAD_C[2] else 0.3)
    return u, v, w


def face_uv(q):
    return ((q[1] + 0.30) / 0.30, (q[0] - 0.02) / 0.54)


def head():
    p = Part()
    c = Vector(HEAD_C)

    def mat(cen):
        return FACE if cen[2] > 0.09 and 0.0 < cen[0] < 0.50 and abs(cen[1]) < 0.30 else SKIN
    blob(p, HEAD_C, HEAD_R, 20, 14, SKIN, shape=head_shape, mat_of=mat, uv_of=face_uv)
    for s_ in (-1, 1):
        blob(p, (0.28, s_ * 0.32, -0.01), (0.085, 0.035, 0.06), 8, 5, SKIN)
    blob(p, (0.22, 0.0, 0.325), (0.022, 0.02, 0.018), 6, 4, SKIN)

    def keep(cen):
        u, v, w = cen
        if w > 0.04 and u < 0.52:
            return False
        if u < 0.14 and w > -0.20:
            return False
        return not (abs(v) > 0.22 and u < 0.36 and w > -0.17)
    blob(p, (HEAD_C[0] + 0.03, 0, HEAD_C[2] - 0.03), (HEAD_R[0] + 0.05, HEAD_R[1] + 0.04, HEAD_R[2] + 0.05),
         18, 12, HAIR, keep=keep)

    def S(base_dir, tip, width, thick=0.08, bend=0.07):
        d = Vector(base_dir).normalized()
        r = Vector(HEAD_R)
        base = c + Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * 0.92
        spike(p, base, Vector(tip), width * 1.3, thick * 1.7, d, bend)
    S((1.0, 0.05, -0.15), (0.98, 0.08, -0.30), 0.20, 0.09, 0.08)
    S((0.90, -0.30, -0.10), (0.92, -0.42, -0.24), 0.18)
    S((0.85, 0.35, -0.12), (0.88, 0.50, -0.30), 0.18)
    S((0.55, -0.80, 0.0), (0.66, -1.02, -0.08), 0.18, 0.08, 0.06)
    S((0.30, -0.95, -0.10), (0.34, -0.96, -0.22), 0.16)
    S((0.55, 0.80, 0.0), (0.66, 1.04, -0.06), 0.18, 0.08, 0.06)
    S((0.30, 0.95, -0.10), (0.34, 0.98, -0.22), 0.16)
    S((0.60, 0.0, -0.80), (0.70, 0.02, -0.66), 0.20)
    S((0.25, -0.45, -0.85), (0.24, -0.46, -0.62), 0.17)
    S((0.25, 0.45, -0.85), (0.26, 0.48, -0.62), 0.17)
    S((-0.10, 0.0, -1.0), (0.02, 0.02, -0.52), 0.15)
    for v, tv, w0 in ((0.04, 0.10, 0.09), (-0.12, -0.20, 0.08), (0.20, 0.27, 0.08), (-0.25, -0.33, 0.07)):
        spike(p, Vector((0.55, v, 0.22)), Vector((0.40, tv, 0.36)), w0, 0.04, Vector((0.3, 0, 1)), 0.02)
    for s_ in (-1, 1):
        spike(p, Vector((0.38, s_ * 0.28, 0.08)), Vector((0.20, s_ * 0.33, 0.13)), 0.05, 0.03, Vector((0, s_, 0.4)),
              0.0)
    p.verts = [(u * 1.24, v * 1.24, w * 1.24) for u, v, w in p.verts]
    return p


def upper_arm():
    p = Part()
    loft(p, [(0.0, 0.085, 0.085), (0.26, 0.076, 0.076)], 8, SKIN)
    return p


def forearm():
    p = Part()
    loft(p, [(-0.02, 0.068, 0.068), (0.14, 0.064, 0.064)], 8, SKIN)
    loft(p, [(0.12, 0.085, 0.085), (0.25, 0.085, 0.085)], 10, BAND, cap1=True)
    return p


def fist():
    p = Part()
    blob(p, (0.11, 0, 0.0), (0.12, 0.10, 0.12), 10, 7, SKIN)
    blob(p, (0.08, 0.0, 0.10), (0.05, 0.04, 0.04), 6, 4, SKIN)
    return p


def open_hand():
    p = Part()
    blob(p, (0.09, 0, 0), (0.095, 0.05, 0.105), 8, 5, SKIN)
    for k in range(4):
        w = -0.06 + 0.04 * k
        tube(p, (0.15, 0, w), (0.26, 0, w * 1.1), 0.025, 5, SKIN)
    tube(p, (0.05, 0, 0.08), (0.13, 0, 0.15), 0.027, 5, SKIN)
    return p


def peace_hand():
    p = Part()
    blob(p, (0.11, 0, 0.0), (0.12, 0.10, 0.12), 10, 7, SKIN)
    for w in (-0.03, 0.03):
        tube(p, (0.18, 0, w), (0.33, 0, w * 2.2), 0.027, 5, SKIN)
    return p


def thigh():
    p = Part()
    loft(p, [(-0.08, 0.20, 0.19), (0.12, 0.25, 0.23), (0.36, 0.29, 0.26), (0.58, 0.30, 0.27), (0.70, 0.29, 0.26)],
         12, GI, cap0=True)
    return p


def shin():
    p = Part()
    loft(p, [(-0.04, 0.29, 0.26), (0.14, 0.28, 0.25), (0.30, 0.22, 0.20), (0.42, 0.14, 0.13), (0.47, 0.09, 0.09)],
         12, GI)
    loft(p, [(0.44, 0.088, 0.088), (0.54, 0.082, 0.082), (0.60, 0.08, 0.08)], 10, SOCK)
    return p


def shoe():
    """A blue kung fu slip-on; w points to the sole."""
    p = Part()

    def shape(u, v, w):
        if u > 0.18:
            v *= 1 - 0.35 * (u - 0.18) / 0.18
        return u, v, min(w, 0.15)
    blob(p, (0.15, 0, 0.065), (0.25, 0.12, 0.09), 12, 7, SHOE, shape=shape)
    return p


def wing():
    p = Part()
    a, b, c, d = p.v(0, 0, 0), p.v(0.25, 0.02, -0.15), p.v(0.38, 0.05, -0.45), p.v(0.10, 0.02, -0.40)
    p.face((a, b, c, d), WING)
    p.face((d, c, b, a), WING)
    return p


MAIN_PARTS = {
    "Butt": pelvis, "Torso": torso, "Head DL": head,
    "Left Arm Color": upper_arm, "Right Arm Color": upper_arm, "Left Forearm": forearm, "Right Forearm": forearm,
    "Left Hand DL": fist, "Right Hand DL": fist,
    "Left Thigh Color": thigh, "Right Thigh Color": thigh, "Left Leg": shin, "Right Leg": shin,
    "Left Shoe": shoe, "Right Shoe DL": shoe,
    "Left Wing DL": wing, "Right Wing DL": wing,
}
NO_OUTLINE = {"Left Wing DL", "Right Wing DL"}
EXTRA = {
    "Capless Head Mesh": {"Capless Head": head},
    "Left Hand Open Mesh": {"Left Hand Open": open_hand},
    "Right Hand Open Mesh": {"Right Hand Open": open_hand},
    "Right Hand Peace Mesh": {"Right Hand Peace": peace_hand},
    "Right Hand Cap Mesh": {"Right Hand Cap": open_hand},
    "Right Hand Wing Cap Mesh": {"Right Hand Wing Cap": open_hand},
}



def image(name):
    img = bpy.data.images.load(os.path.join(TEX, f"{name}.rgba16.png"), check_existing=True)
    img.name = f"{name}.rgba16.png"
    return img


def setup_materials():
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    for name in (GI, GI_EDGE, SKIN, HAIR, BELT, BAND, SHOE, SOCK, POLE, POLE_LINE, WING, OUTLINE, HEAD_LINE):
        m = createF3DMat(None, "Shaded Solid")
        m.name = name
        m.f3d_mat.rdp_settings.g_lighting = False
        m.f3d_mat.rdp_settings.g_cull_back = name != WING
        if name == HEAD_LINE:
            m.f3d_mat.rdp_settings.set_rendermode = True
            m.f3d_mat.rdp_settings.rendermode_preset_cycle_1, m.f3d_mat.rdp_settings.rendermode_preset_cycle_2 = "G_RM_AA_ZB_XLU_SURF", "G_RM_AA_ZB_XLU_SURF2"
    for mat, state in EYE_MATS.items():
        f = bpy.data.materials[mat].f3d_mat
        f.rdp_settings.g_lighting = False
        f.tex0.tex = image(f"goku_anime_eyes_{state}" if FACE_SET == "anime" else f"goku_eyes_{state}")
        f.tex0.tex_format = "RGBA16"
        f.tex0.S.mirror, f.tex0.S.clamp = True, False
        f.tex0.T.mirror, f.tex0.T.clamp = False, True
    kanji = bpy.data.materials[FACE].copy()
    kanji.name = KANJI
    f = kanji.f3d_mat
    f.tex0.tex = image("goku_kanji")
    f.tex0.S.mirror, f.tex0.S.clamp = False, True
    f.draw_layer.sm64 = "2"
    f = bpy.data.materials[METAL].f3d_mat
    for tex in (f.tex0, f.tex1):
        if tex.tex is not None:
            tex.tex = image("goku_metal_shade" if "shade" in tex.tex.name.lower() else "goku_metal_light")


LIGHT = Vector((0.70, 0.35, -0.62)).normalized()


def standing(n, bone):
    """A rest-frame normal (X up the bone, Y his right, Z his front) turned into his standing frame."""
    if "Shoe" in bone:
        return Vector((-n.z, n.x, n.y))
    if any(k in bone for k in ("Arm", "Forearm", "Hand", "Thigh", "Leg")):
        return Vector((-n.x, -n.z, n.y))
    return Vector((n.x, n.z, n.y))


RAMPED = {GI: -0.2, GI_EDGE: -0.2, SKIN: -0.08, BELT: -0.35, BAND: -0.15, SHOE: -0.15, SOCK: -0.2, POLE: -0.15, "Rope": -0.2}
RAMP_REACH = 4.0


def ramp_materials(tex_dir):
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    for name in RAMPED:
        old = bpy.data.materials.get(name)
        if old is not None:
            old.name = name + " (flat)"
        m = createF3DMat(None, "Shaded Texture")
        m.name = name
        f = m.f3d_mat
        f.rdp_settings.g_lighting = False
        f.rdp_settings.g_mdsft_text_filt = "G_TF_POINT"
        slug = name.lower().replace(" ", "_")
        lit, dark = (rgb(h) for h in COLORS[name])
        size = 16
        img = bpy.data.images.new(f"goku_ramp_{slug}.rgba16.png", size, 4, alpha=True)
        img.colorspace_settings.name = "sRGB"
        pixels = []
        for _y in range(4):
            for x in range(size):
                pixels += [*(lit if x >= size // 2 else dark), 1.0]
        img.pixels = pixels
        img.filepath_raw = os.path.join(tex_dir, img.name)
        img.file_format = "PNG"
        img.save()
        f.tex0.tex = img
        f.tex0.tex_format = "RGBA16"
        f.tex0.S.clamp, f.tex0.T.clamp = True, True


def ramp_at(name, d):
    """Where along its ramp a vertex this much towards the light sits."""
    return max(0.0, min(1.0, 0.5 + (d - RAMPED[name]) / RAMP_REACH)), 0.5


def cel(name, d):
    lit, dark = (rgb(h) for h in COLORS.get(name, ("FFFFFF", "C0C0C0")))
    if name in (OUTLINE, POLE_LINE, HEAD_LINE):
        return lit
    if SHADING == "cel":
        t = 1.0 if d > 0.30 else 0.5 if d > -0.10 else 0.0
        return tuple(round((dk + (lt - dk) * t) * 31) / 31 for lt, dk in zip(lit, dark))
    if not name.startswith("BT3") and "Eyes" not in name and name not in (BELT, SKIN):
        dark = tuple(c * DEEPEN for c in dark)
    t = max(0.0, min(1.0, 0.5 + 1.1 * d))
    t = t * t * (3 - 2 * t)
    return tuple(dk + (lt - dk) * t for lt, dk in zip(lit, dark))


DEEPEN = 0.72



def chibi_skeleton(arm_name):
    """Move the template's bones to the avatar proportions in anims.REST: each animated bone sits at its animated
    parent plus REST's offset; every other bone keeps its offset from its own parent."""
    import anims
    arm = bpy.data.objects.get(arm_name)
    if arm is None:
        return
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    old = {b.name: b.head.copy() for b in eb}
    new = {}

    def place(b):
        if b.name in new:
            return
        if b.parent is not None:
            place(b.parent)
        if b.name in anims.REST and anims.PARENT.get(b.name) in old:
            par = anims.PARENT[b.name]
            place(eb[par])
            ox, oy, oz = anims.REST[b.name]
            new[b.name] = new[par] + Vector((ox, oy, oz))
        elif b.parent is not None:
            new[b.name] = new[b.parent.name] + (old[b.name] - old[b.parent.name])
        else:
            new[b.name] = old[b.name]
    for b in eb:
        place(b)
    for b in eb:
        d = new[b.name] - b.head
        b.head += d
        b.tail += d
    bpy.ops.object.mode_set(mode="OBJECT")


def sink_where_touching(part, find, shell_at, thickness):
    """Which vertices' outlines to pull inside their own piece, because another piece of the part covers them or nearly does. An outline
    skimming a surface at a shallow angle is cut by it into dashes and specks; pulled under, the line tapers away cleanly along one
    polygon. Only into pieces about as big or bigger: a thin cord across his barrel mustn't take a bite out of the barrel's line."""
    from mathutils.bvhtree import BVHTree
    faces_of, verts_of = {}, {}
    for idx, _, _ in part.faces:
        faces_of.setdefault(find(idx[0]), []).append(list(idx))
    for i in range(len(part.verts)):
        verts_of.setdefault(find(i), []).append(Vector(part.verts[i]))

    def size(r):
        pts = verts_of[r]
        return max((max(p[c] for p in pts) - min(p[c] for p in pts)) ** 2 for c in range(3)) ** 0.5
    trees = {r: BVHTree.FromPolygons([tuple(v) for v in part.verts], fs, all_triangles=False) for r, fs in faces_of.items()}
    sizes = {r: size(r) for r in faces_of}

    def inside(tree, x):
        hits, at, up = 0, x, Vector((1.0, 0.0, 0.0))
        while hits < 12:
            loc, _, _, _ = tree.ray_cast(at, up)
            if loc is None:
                break
            hits += 1
            at = loc + up * 1e-5
        return hits % 2 == 1

    sunk = set()
    for i, x in enumerate(shell_at):
        own = find(i)
        for r, tree in trees.items():
            if r == own or sizes.get(own, 0.0) > sizes[r] / 0.8:
                continue
            _, _, _, d = tree.find_nearest(x)
            if d is not None and (d < thickness * 1.2 or inside(tree, x)):
                sunk.add(i)
                break
    return sunk


def outline_shell(part: Part, thickness=0.008):
    """The avatar's black outline: the part again, pushed out along its normals with its faces turned inward, so
    only its back faces draw around the silhouette. The face's triangles count as facing away from the part's
    middle (shell.outward, which build() winds them by): the rip winds some of them inward, and their shell showed
    through his eyes as black. Every other face is pushed out from the middle of its own piece (the faces sharing
    its vertices): blob() winds its faces inward, which sank the outline of every round part (fists, palms, the
    sash's knot) inside it."""
    acc = [Vector() for _ in part.verts]
    faces_at = [[] for _ in part.verts]
    cen = sum((Vector(v) for v in part.verts), Vector()) / max(len(part.verts), 1)
    root = list(range(len(part.verts)))

    def find(i):
        while root[i] != i:
            root[i] = root[root[i]]
            i = root[i]
        return i
    for idx, _, _ in part.faces:
        for i in idx[1:]:
            root[find(i)] = find(idx[0])
    sums = {}
    for i, v in enumerate(part.verts):
        s, n_ = sums.get(find(i), (Vector(), 0))
        sums[find(i)] = (s + Vector(v), n_ + 1)
    piece = {r: s / n_ for r, (s, n_) in sums.items()}
    outward = {}
    for k, (idx, mat, _) in enumerate(part.faces):
        a, b, c = (Vector(part.verts[i]) for i in idx[:3])
        n = (b - a).cross(c - a)
        mid = (a + b + c) / 3
        if mat in EYE_MATS:
            n = n if n.dot(mid - cen) >= 0 else -n
            outward[k] = n
        elif n.dot(mid - piece[find(idx[0])]) < 0:
            n = -n
        if n.length == 0:
            continue
        n = n.normalized()
        for at, i in enumerate(idx):
            here = Vector(part.verts[i])
            one, two = Vector(part.verts[idx[at - 1]]) - here, Vector(part.verts[idx[(at + 1) % len(idx)]]) - here
            if one.length and two.length:
                acc[i] += n * one.angle(two, 0.0)
                faces_at[i].append(n)
    shell = Part()
    shell.twin, shell.outward = [], {}
    thin = {i for idx, mat, _ in part.faces if mat == "Rope" for i in idx}
    out_by = []
    for i, (v, n) in enumerate(zip(part.verts, acc)):
        v = Vector(v)
        if i in part.around:
            n = v - Vector(part.around[i])
        n = n.normalized() if n.length > 0 else (v - cen).normalized()
        square = min((n.dot(f) for f in faces_at[i]), default=1.0)
        out_by.append(n * thickness * (0.75 if i in thin else 1.0) / max(square, 0.6))
    at = [Vector(v) + o for v, o in zip(part.verts, out_by)]
    sunk = (sink_where_touching(part, find, at, thickness) if part.sinks else set()) | part.tucks
    for i, (v, o) in enumerate(zip(part.verts, out_by)):
        shell.v(*(Vector(v) + (-o if i in sunk else o)))
    for k, (idx, mat, _) in enumerate(part.faces):
        mid = sum((Vector(part.verts[i]) for i in idx), Vector()) / len(idx)
        if all(i in sunk for i in idx):
            continue
        if k in part.flat or mat == HAIR or k in outward and (abs(mid.y) < 0.12 and 0 < mid.x < 0.26 or mid.z > 0.33):
            continue
        if k in outward:
            shell.outward[len(shell.faces)] = outward[k]
        shell.twin.append(k)
        shell.face(list(reversed(idx)), OUTLINE)
    return shell



def bone_head(arm, bone):
    return arm.matrix_world @ arm.data.bones[bone].head_local


def build(obj, parts: dict, material_override=None, rewind=True):
    arm = obj.parent
    me = obj.data
    mats: list[str] = []
    verts, faces, groups, uvs, face_mats = [], [], [], [], []
    inv = obj.matrix_world.inverted()
    pieces = []
    soft = {}
    for bone, make in parts.items():
        part = make()
        pieces.append((bone, part, None))
        if OUTLINES and material_override is None and bone not in NO_OUTLINE:
            pieces.append((bone, outline_shell(part), part))
    twins = []
    for bone, part, body_of in pieces:
        h = bone_head(arm, bone)
        base = len(verts)
        for u, v, w in part.verts:
            verts.append(inv @ Vector((h.x + u, h.y + v, h.z + w)))
            groups.append(bone)
        soft.update({base + i: Vector(n).normalized() for i, n in part.soft.items()})
        if body_of is not None:
            first = len(faces) - len(body_of.faces)
            rot = inv.to_3x3()
            twins += [(len(faces) + j, first + k, rot @ part.outward[j] if j in part.outward else None)
                      for j, k in enumerate(part.twin)]
        for idx, mat, uv in part.faces:
            mat = material_override or mat
            if mat not in mats:
                mats.insert(0, mat) if mat == HEAD_LINE else mats.append(mat)
                face_mats = [m + 1 for m in face_mats] if mat == HEAD_LINE else face_mats
            faces.append([base + i for i in idx])
            face_mats.append(mats.index(mat))
            uvs.append(uv)
    me.clear_geometry()
    me.materials.clear()
    for m in mats:
        me.materials.append(bpy.data.materials[m])
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    for poly, mi in zip(me.polygons, face_mats):
        poly.material_index = mi
    uv_layer = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, uvs):
        for k, li in enumerate(poly.loop_indices):
            uv_layer.data[li].uv = uv[k] if uv else (0.0, 0.0)
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    by_bone: dict[str, list[int]] = {}
    for i, b in enumerate(groups):
        by_bone.setdefault(b, []).append(i)
    for b, idx in by_bone.items():
        obj.vertex_groups.new(name=b).add(idx, 1.0, "REPLACE")
    bm = bmesh.new()
    bm.from_mesh(me)
    outline = mats.index(OUTLINE) if OUTLINE in mats else -1
    pole_line = mats.index(POLE_LINE) if POLE_LINE in mats else -1
    head_line = mats.index(HEAD_LINE) if HEAD_LINE in mats else -1
    if not rewind:
        bm.free()
        bm = None
    if bm is not None:
        body = [f for f in bm.faces if f.material_index not in (outline, pole_line, head_line)]
        bmesh.ops.recalc_face_normals(bm, faces=body)
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[s] for s, b, out in twins
                                           if bm.faces[s].normal.dot(bm.faces[b].normal if out is None else out) > 0])
        bm.to_mesh(me)
        bm.free()
        me.update()
    for poly in me.polygons:
        poly.use_smooth = True
    rot = obj.matrix_world.to_3x3()
    col = me.color_attributes.get("Col") or me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    uv_layer = me.uv_layers[0]
    normals = {}
    for poly in me.polygons:
        for vi in poly.vertices:
            normals.setdefault(vi, Vector())
            normals[vi] += poly.normal * poly.area
    for poly in me.polygons:
        name = mats[poly.material_index]
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            n = soft[vi] if vi in soft else (rot @ normals[vi]).normalized()
            d = standing(n, groups[vi]).dot(LIGHT)
            if name in RAMPED and bpy.data.materials[name].f3d_mat.tex0.tex is not None:
                uv_layer.data[li].uv = ramp_at(name, d)
                col.data[li].color_srgb = (1.0, 1.0, 1.0, 1.0)
            else:
                col.data[li].color_srgb = (*cel(name, d), 1.0)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"built {obj.name}: {tris} tris, {len(mats)} materials")
    return tris



def pose_rig(p):
    """Mario's skeleton in pose p (anims.full), standing his lowest sole on the floor."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import anims
    rig = bpy.data.objects["Mario"]
    loc = anims.local_rotations(p)
    rig.animation_data_clear()
    for b in anims.ORDER:
        pb = rig.pose.bones[b]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = loc[b].to_euler("XYZ")
    rig.pose.bones["Body"].location = (0, -anims.sole_height(loc), 0)


def preview_materials(objects):
    """Each object drawn as the game draws it: baked vertex colors unlit, the face texture mirrored across S, back faces culled."""
    for slot in [slot for o in objects for slot in o.material_slots]:
        src = slot.material
        if src is None or src.name.startswith("preview "):
            continue
        m = bpy.data.materials.new(f"preview {src.name}")
        m.use_nodes = True
        m.use_backface_culling = src.f3d_mat.rdp_settings.g_cull_back if getattr(src, "f3d_mat", None) else True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        emit = nt.nodes.new("ShaderNodeEmission")
        col = nt.nodes.new("ShaderNodeAttribute")
        col.attribute_name = "Col"
        color = col.outputs["Color"]
        tex = src.f3d_mat.tex0.tex if getattr(src, "f3d_mat", None) and src.f3d_mat.tex0.tex_set else None
        if os.environ.get("GOKU_DEBUG"):
            print("PREVIEW", src.name, tex.name if tex else None, tex.size[:] if tex else None)
        if tex is not None and (src.name in (FACE, KANJI) or src.name.startswith(("BT3", "B3 ")) or src.name.endswith("Eyes (SKIN)")):
            uv = nt.nodes.new("ShaderNodeUVMap")
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            nt.links.new(uv.outputs["UV"], sep.inputs[0])
            x = sep.outputs[0]
            if src.f3d_mat.tex0.S.mirror:
                sub = nt.nodes.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 1
                ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
                inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
                nt.links.new(x, sub.inputs[0]); nt.links.new(sub.outputs[0], ab.inputs[0])
                nt.links.new(ab.outputs[0], inv.inputs[1]); x = inv.outputs[0]
            comb = nt.nodes.new("ShaderNodeCombineXYZ")
            nt.links.new(x, comb.inputs[0]); nt.links.new(sep.outputs[1], comb.inputs[1])
            img = nt.nodes.new("ShaderNodeTexImage")
            img.image = tex
            img.interpolation = "Linear"
            img.extension = "EXTEND" if src.f3d_mat.tex0.S.clamp or src.name in (FACE, KANJI) else "REPEAT"
            nt.links.new(comb.outputs[0], img.inputs[0])
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
            nt.links.new(img.outputs["Alpha"], mix.inputs[0])
            nt.links.new(color, mix.inputs[6]); nt.links.new(img.outputs["Color"], mix.inputs[7])
            color = mix.outputs[2]
        elif tex is not None:
            img = nt.nodes.new("ShaderNodeTexImage")
            img.image = tex
            img.interpolation = "Closest"
            img.extension = "EXTEND"
            nt.links.new(nt.nodes.new("ShaderNodeUVMap").outputs["UV"], img.inputs[0])
            mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
            mul.inputs[0].default_value = 1
            nt.links.new(img.outputs["Color"], mul.inputs[6]); nt.links.new(color, mul.inputs[7])
            color = mul.outputs[2]
        nt.links.new(color, emit.inputs["Color"])
        nt.links.new(emit.outputs[0], out.inputs["Surface"])
        if src.name == WING:
            nt.links.new(nt.nodes.new("ShaderNodeHoldout").outputs[0], out.inputs["Surface"])
        slot.material = m


def render_views(out_dir, views, prefix="preview", size=(480, 640), look=(0, 0, 1.38), scale=3.4):
    """One render per view, (name, camera position), each looking at `look`, orthographic and `scale` wide."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.film_transparent = True
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    scene.camera = cam
    paths = []
    for name, pos in views:
        cam.location = pos
        d = Vector(look) - Vector(pos)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out_dir, f"{prefix}-{name}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(scene.render.filepath)
    return paths


def preview(out_dir):
    """Front, three-quarter, side and back renders of the model standing, as the game draws it."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import anims
    pose_rig(anims.full({}))
    body = bpy.data.objects["Mario Mesh"]
    for o in bpy.data.objects:
        o.hide_render = o is not body
    preview_materials([body])
    render_views(out_dir, (("front", (0, -6, 1.45)), ("three-quarter", (-4.2, -4.2, 1.85)), ("side", (-6, 0, 1.45)),
                           ("back", (0, 6, 1.45))))

def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = args[0]
    setup_materials()
    chibi_skeleton("Mario")
    chibi_skeleton("Metal Mario")
    total = build(bpy.data.objects["Mario Mesh"], MAIN_PARTS)
    build(bpy.data.objects["Metal Mario Mesh"], dict(MAIN_PARTS), METAL)
    for name, parts in EXTRA.items():
        build(bpy.data.objects[name], parts)
        metal = bpy.data.objects.get("Metal " + name)
        if metal:
            build(metal, dict(parts), METAL)
    print(f"Kid Goku: {total} tris in the main body")
    if len(args) > 2:
        preview(args[2])
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
    if len(args) > 1:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
