"""Kid Goku's body as the 1986 anime draws it in the Pilaf saga, built in code (runs inside Blender, from bt3.py).

The anime's proportions and gi set every part's shape; each part's size and
place in its bone's frame start from the rip's own part, measured at build time (bt3.fitted's stations), so the
joints stay where Mario's animations expect them. Only those measurements are taken from the rip, never its
triangles, and nothing measured is written down here.

Frames: the torso and pelvis are u up, v his right, w his front; a limb is u down along the bone, v across it, w
front to back; a shoe is u toward the toe, w toward the sole.
"""
import math

import goku as G

SIDES = 10
LIMB = 8
ARM_SIDES = 9
CHEST_FORWARD, WAIST_FORWARD = 0.03, 0.07
NECK_SHADE = (-0.6, 0.0, -0.8)
SEAT_FORWARD = 0.05
PANT_BACK = 0.03
PANT_WIDE, PANT_DEEP = 0.726, 1.0
ARM_FULL = 1.0


def ring_at(rings, u):
    """A loft's (rv, rw, cv, cw) at height u, straight between its rings."""
    lo = max([r for r in rings if r[0] <= u] or rings[:1], key=lambda r: r[0])
    hi = min([r for r in rings if r[0] >= u] or rings[-1:], key=lambda r: r[0])
    t = 0 if hi[0] == lo[0] else (u - lo[0]) / (hi[0] - lo[0])
    return tuple(lo[k] + (hi[k] - lo[k]) * t for k in (1, 2, 3, 4))


def surface(rings, u, f, side=1):
    """The point on a loft's front (side 1) or back (-1) at height u and f of the way out to his right (f < 0: left),
    lifted a little off it."""
    rv, rw, cv, cw = ring_at(rings, u)
    return u, cv + f * rv, cw + side * (rw * math.sqrt(max(0.0, 1 - f * f)) + 0.012)


def on_barrel(rings, u, f, side, lift=0.019):
    """The point on a loft at height u and f of the way out to his right (f < 0: left), on its front (side 1) or back (-1), lifted
    straight off the surface, including round his sides, where the surface faces away from front and back."""
    rv, rw, cv, cw = ring_at(rings, u)
    round_ = side * math.sqrt(max(0.0, 1 - f * f))
    nv, nw = f / rv, round_ / rw
    length = math.hypot(nv, nw)
    return u, cv + f * rv + lift * nv / length, cw + round_ * rw + lift * nw / length


def cord_loop(p, points, r, cw):
    """A smooth closed cord through points, in a band round his body (cw: how far forward his middle is). Each point stands out from the
    cord's own middle for the outline; the outline's usual way of telling out from in fails on a loop."""
    from mathutils import Vector
    pts = [Vector(q) for q in points]
    path = []
    for k in range(len(pts)):
        a, b, c, d = (pts[(k + o) % len(pts)] for o in (-1, 0, 1, 2))
        for t in (0.0, 0.5):
            path.append(0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t * t * t))
    rings = []
    for k, c in enumerate(path):
        along = (path[(k + 1) % len(path)] - path[k - 1]).normalized()
        out = Vector((0.0, c.y, c.z - cw))
        out = (out - along * out.dot(along)).normalized()
        across = along.cross(out)
        ring = []
        for j in range(4):
            turn = (j + 0.5) * math.pi / 2
            q = p.v(*(c + (out * math.cos(turn) + across * math.sin(turn)) * r))
            p.around[q] = tuple(c)
            ring.append(q)
        rings.append(ring)
    for k, a in enumerate(rings):
        b = rings[(k + 1) % len(rings)]
        for j in range(4):
            n = (j + 1) % 4
            p.face((a[j], a[n], b[n], b[j]), "Rope")


def ink_ring(p, u, rv, rw, cv, cw, half=0.005, proud=0.004):
    """A black line drawn round a part at height u, on a ring of that size. The outline only ever shows round his silhouette, never across
    him, so the sash's edges need their own."""
    first = len(p.faces)
    G.loft(p, [(u - half, rv + proud, rw + proud, cv, cw), (u + half, rv + proud, rw + proud, cv, cw)], SIDES, G.OUTLINE)
    for idx, m, uv in p.faces[first:]:
        p.face(idx[::-1], m, uv)
    p.flat |= set(range(first, len(p.faces)))


def torso(st, rest_torso):
    """The gi top: a round body as wide at the waist as at the chest, the belly bowed a little past it; a plain V neck a
    third of the way down; the Power Pole's cord over his right shoulder, knotted on his chest; the pole across his
    back; and the neck the head sits on."""
    p = G.Part()
    u0, u1 = st[0][0], st[-1][0]
    W, D = max(r[1] for r in st), max(r[2] for r in st)
    cw0 = sum(r[4] for r in st) / len(st)
    shape = ((0.00, 1.0, 0.94), (0.11, 1.10, 1.06), (0.30, 1.09, 1.08), (0.60, 1.03, 0.98), (0.84, 0.93, 0.84),
             (1.00, 0.58, 0.52))
    rings = [(u0 + (u1 - u0) * t, W * a, D * b, 0.0, cw0 + CHEST_FORWARD + (WAIST_FORWARD - CHEST_FORWARD) * max(0.0, 1 - t / 0.6))
             for t, a, b in shape]
    barrel = G.loft(p, rings, SIDES, G.GI, cap1=True, mats=[G.BELT, G.GI, G.GI, G.GI, G.GI])
    p.flat.add(SIDES * (len(rings) - 1))
    p.tucks = {q for ring, r in zip(barrel[3:5], rings[3:5]) for q in ring if abs(p.verts[q][1] - r[3]) > r[1] * 0.75}
    ink_ring(p, *rings[1])
    tip = u1 - (u1 - u0) * 0.36
    over = u1 + 0.024
    t0, t1, t2, t3, t4 = (p.v(*surface(rings, over, f)) for f in (-0.8, -0.4, 0, 0.4, 0.8))
    m0, m1, m2 = (p.v(*surface(rings, u1 - (u1 - tip) * 0.45, f)) for f in (-0.2, 0, 0.2))
    tp = p.v(*surface(rings, tip, 0))
    n0, n1, n2 = p.v(over, -0.08, cw0), p.v(over, 0.0, cw0 + 0.07), p.v(over, 0.08, cw0)
    p.soft.update({q: NECK_SHADE for q in (n0, n1, n2)})
    for tri in ((t0, t1, m0), (t1, m1, m0), (t1, t2, m1), (t2, t3, m1), (t3, m2, m1), (t3, t4, m2), (m0, m1, tp),
                (m1, m2, tp), (t0, n0, t1), (t1, n0, n1), (t1, n1, t2), (t2, n1, t3), (t3, n1, n2), (t3, n2, t4)):
        p.face(tri, G.SKIN, flat=True)
        p.face(tri[::-1], G.SKIN, flat=True)
    first = len(p.faces)
    made = G.loft(p, [(u1 - 0.04, 0.085, 0.075, 0.0, cw0), (u1 + 0.05, 0.082, 0.072, 0.0, cw0), (u1 + 0.14, 0.08, 0.07, 0.0, cw0)], 6, G.SKIN)
    p.soft.update({q: NECK_SHADE for ring in made for q in ring})
    p.flat |= set(range(first, first + 12))
    def laid(t, f, side=1):
        return on_barrel(rings, u0 + (u1 - u0) * t, f, side)
    knot = laid(0.38, -0.12)
    cord_loop(p, [laid(0.17, -1.0), laid(0.2, -0.9), laid(0.25, -0.68), laid(0.31, -0.41), knot, laid(0.52, 0.085), laid(0.66, 0.29),
                  laid(0.8, 0.495), laid(0.92, 0.7), laid(1.0, 0.86), (u1 + 0.016, 0.19, rings[-1][4]), laid(1.0, 0.86, -1),
                  laid(0.92, 0.7, -1), laid(0.66, 0.29, -1), laid(0.38, -0.12, -1), laid(0.25, -0.68, -1)], 0.009,
              (rings[-1][4] + rings[0][4]) / 2)
    first = len(p.faces)
    G.blob(p, knot, (0.022, 0.026, 0.016), 5, 3, "Rope")
    p.flat |= set(range(first, len(p.faces)))
    first = len(p.faces)
    for s in (-1, 1):
        G.tube(p, knot, (knot[0] - 0.07, knot[1] + s * 0.02, knot[2] + 0.004), 0.007, 4, "Rope")
    p.flat |= set(range(first, len(p.faces)))
    back = surface(rings, u0 - 0.26, -0.98, -1), surface(rings, u1 + 0.30, 1.0, -1)
    deepest = min(r[4] - r[2] for r in rings)
    ends = (back[0][0], back[0][1], deepest - 0.052), (back[1][0], back[1][1], deepest - 0.046)
    first = len(p.faces)
    G.tube(p, *ends, 0.07, 8, G.POLE)
    line = len(p.faces)
    G.tube(p, *ends, 0.078, 8, G.POLE_LINE)
    p.faces[line:] = [(idx[::-1], m, uv) for idx, m, uv in p.faces[line:]]
    for along in (0.2, 0.8):
        lashing(p, ends, along, 0.0765, 0.016)
    p.flat |= set(range(first, len(p.faces)))
    return p, rings


def lashing(p, ends, along, r, half):
    """A band of cord round a staff, this far along it."""
    from mathutils import Vector
    a, b = Vector(ends[0]), Vector(ends[1])
    axis = b - a
    mid = a + axis * along
    axis = axis.normalized()
    s = axis.orthogonal().normalized()
    o = axis.cross(s)
    sides = 8
    round_ = [s * math.cos(2 * math.pi * k / sides) + o * math.sin(2 * math.pi * k / sides) for k in range(sides)]
    near = [p.v(*(mid - axis * half + d * r)) for d in round_]
    far = [p.v(*(mid + axis * half + d * r)) for d in round_]
    for k in range(sides):
        n = (k + 1) % sides
        p.face((near[k], near[n], far[n], far[k]), "Rope")


def ribbon(p, stations, across, thick, mat, last=None):
    """A band of cloth with a little thickness, so it takes an outline. stations are (center, half width) along it; across is the
    way its width lies, in (u, v, w), and last that for the final station (a slanted cut). thick is half its depth in w."""
    rings = []
    for k, (c, half) in enumerate(stations):
        e = last if last and k == len(stations) - 1 else across
        rings.append([p.v(c[0] + s * half * e[0], c[1] + s * half * e[1], c[2] + s * half * e[2] + t * thick)
                      for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a, b_ in zip(rings, rings[1:]):
        for k in range(4):
            n = (k + 1) % 4
            p.face((a[k], a[n], b_[n], b_[k]), mat)
    p.face(list(reversed(rings[0])), mat)
    p.face(rings[-1], mat)


def pelvis(st, waist, rest_torso):
    """The pants' seat, meeting the gi top at his waist, and the white sash over the join: a band, tied in front."""
    p = G.Part()
    rv_w, rw_w, cv_w, cw_w = waist[1:]
    top = rest_torso + waist[0]
    hip = st[2]
    seat_w = cw_w + SEAT_FORWARD
    rings = [(-0.235, rv_w * 0.28, rw_w * 0.5, 0.0, seat_w), (-0.17, rv_w * 0.66, rw_w * 0.82, 0.0, seat_w),
             (-0.1, rv_w * 0.92, rw_w * 1.06, 0.0, seat_w), (-0.04, rv_w * 0.96, rw_w * 1.14, 0.0, seat_w),
             (0.04, rv_w * 0.96, rw_w * 1.08, cv_w, cw_w + 0.035), (top - 0.09, rv_w * 0.95, rw_w * 0.96, cv_w, cw_w),
             (top + 0.03, rv_w * 0.86, rw_w * 0.86, cv_w, cw_w)]
    made = G.loft(p, rings, SIDES, G.GI, cap0=True)
    shade_round(p, made, 0.0, seat_w)
    band = [(top - 0.08, rv_w * 0.99, rw_w * 1.02, cv_w, cw_w), (top + 0.04, rv_w * 0.94, rw_w * 0.92, cv_w, cw_w)]
    G.loft(p, band, SIDES, G.BELT)
    ink_ring(p, *band[0])
    front = cw_w + rw_w * 1.05
    ku, kw = top - 0.02, front + 0.02
    for s_ in (-1, 1):
        ribbon(p, [((ku + 0.004, cv_w + s_ * 0.024, kw + 0.010), 0.026), ((ku - 0.022, cv_w + s_ * 0.09, kw + 0.022), 0.056),
                   ((ku - 0.072, cv_w + s_ * 0.165, kw + 0.012), 0.058), ((ku - 0.118, cv_w + s_ * 0.205, kw - 0.006), 0.022)],
               (1, 0, s_ * -0.1), 0.017, G.BELT)
        lie = 0.018 * (s_ + 1)
        drop = 0.44 if s_ > 0 else 0.37
        ribbon(p, [((ku - 0.012, cv_w + s_ * 0.012, kw + 0.012 + lie), 0.02),
                   ((ku - 0.15, cv_w + s_ * 0.04, kw + 0.03 + lie), 0.04),
                   ((ku - 0.29, cv_w + s_ * 0.07, kw + 0.04 + lie), 0.048),
                   ((ku - drop, cv_w + s_ * 0.094, kw + 0.045 + lie), 0.056)],
               (0, 1, 0), 0.008, G.BELT, last=(s_ * -0.42, 1, 0))
    G.blob(p, (ku + 0.002, cv_w, kw + 0.02), (0.036, 0.032, 0.028), 6, 3, G.BELT)
    return p


def shade_round(p, rings, cv, cw):
    """These rings shade by which way round the middle they face, not up or down the part, so two pieces that meet there take one shade."""
    for ring in rings:
        for q in ring:
            _, v, w = p.verts[q]
            p.soft[q] = (0.0, v - cv, w - cw)


def thigh(ts, hip, seat_w):
    """A loose, straight pant leg, running up inside the seat and on over the knee so bending never opens a gap. Its top
    is a round ball: a flat top's corners stick out of the seat when he lifts his knee. hip is where it hangs from his pelvis."""
    p = G.Part()
    u0, u1 = ts[0][0], ts[-1][0]
    rv, rw, cv, cw = ts[1][1] * PANT_WIDE, ts[1][2] * PANT_DEEP, ts[1][3], ts[1][4] - PANT_BACK
    top = ts[0][3] * 0.5
    rings = [(u0 - 0.125, rv * 0.6, rw * 0.42, top, cw), (u0 - 0.08, rv * 0.9, rw * 0.74, cv * 1.2, cw),
             (u0 - 0.03, rv * 0.97, rw * 0.97, cv * 0.85, cw), (u1, rv, rw, cv, cw),
             (u1 + 0.05, rv * 0.93, rw * 0.93, cv, cw), (u1 + 0.11, rv * 0.4, rw * 0.4, cv, cw)]
    made = G.loft(p, rings, LIMB, G.GI, cap0=True, cap1=True)
    p.flat |= set(range(LIMB * 2)) | {LIMB * (len(rings) - 1)} | set(range(LIMB * 3, LIMB * 5)) | {LIMB * (len(rings) - 1) + 1}
    shade_round(p, made[:3], -hip[1], hip[2] - seat_w)
    shade_round(p, made[3:], cv, cw)
    return p, rings[3]


def shin(ss, knee, ankle_v):
    """The rest of the pant leg: straight down, gathered only in the last of it, over a thin white band. The gather closes on his
    ankle, which is off the knee's line; drawn straight down, the cuff let his ankle out through its side."""
    p = G.Part()
    _, rv, rw, cv, cw = knee
    u = [r[0] for r in ss]
    end = u[-1]
    rings = [(u[0] - 0.11, rv * 0.5, rw * 0.5, cv, cw), (u[0] - 0.01, rv + 0.01, rw + 0.01, cv, cw),
             (end - 0.12, rv * 0.93, rw * 0.93, cv, cw), (end - 0.05, rv * 0.57, rw * 0.64, ankle_v, cw),
             (end + 0.005, rv * 0.5, rw * 0.56, ankle_v, cw)]
    first = len(p.faces)
    made = G.loft(p, rings, LIMB, G.GI, cap1=True, mats=[G.GI, G.GI, G.GI, G.SOCK])
    for ring, st in zip(made, rings):
        shade_round(p, [ring], st[3], st[4])
    p.flat.add(first + LIMB * 4)
    return p


def slipper(sh):
    """A small navy slipper as episode 8 draws it: a flat sole with a pale rim, a blunt heel and a round toe, cut low so
    the top of his foot shows. His skin flares out under the pants' cuff into a wedge over the foot, down to the
    slipper's vamp halfway along. u runs heel to toe with the ankle over the rear third, w toward the sole."""
    p = G.Part()
    sole = sh[0][4] + sh[0][2] * 0.89
    toe_out = sh[-1][3] * 0.5
    rim = 0.015
    across = lambda u: toe_out * max(0.0, u + 0.02) / 0.27
    shape = ((-0.104, 0.074, 0.062), (-0.08, 0.092, 0.07), (0.0, 0.1, 0.06), (0.1, 0.102, 0.074), (0.205, 0.092, 0.07),
             (0.25, 0.07, 0.056), (0.27, 0.038, 0.036))
    rings = []
    for u, v, h in shape:
        c = across(u)
        rings.append([p.v(u, c + a, b) for a, b in ((v, sole - rim), (v, sole), (-v, sole), (-v, sole - rim),
                                                     (-v * 0.74, sole - h), (v * 0.74, sole - h))])
    faces = (G.SOCK, G.SOCK, G.SOCK, G.SHOE, G.SHOE, G.SHOE)
    for a, b in zip(rings, rings[1:]):
        for k, mat in enumerate(faces):
            n = (k + 1) % len(faces)
            p.face((a[k], a[n], b[n], b[k]), mat)
    p.face(list(reversed(rings[0])), G.SHOE)
    p.face(rings[-1], G.SHOE)
    bottom = sole - 0.015
    foot = ((-0.086, 0.05, 0.085), (-0.035, 0.072, sole + 0.03), (0.02, 0.074, sole + 0.03), (0.075, 0.072, 0.12),
            (0.125, 0.056, 0.03))
    first = len(p.faces)
    G.loft(p, [(u, v, (bottom - (sole - top)) / 2, across(u), (bottom + sole - top) / 2) for u, v, top in foot], 6, G.SKIN,
           cap0=True, cap1=True)
    p.flat |= set(range(first, len(p.faces)))
    return p


def upper_arm(st):
    """A chubby upper arm: a round shoulder, a full biceps toward his front that falls away to the elbow. Both ends are balls, so
    reaching across his chest shows a round shoulder and bending shows a crease."""
    p = G.Part()
    r = max(max(x[1], x[2]) for x in st) * ARM_FULL
    u1 = st[-1][0]
    rows = [(-0.09, 0.45, 0.45, 0.0), (0.012, 0.98, 0.98, 0.0), (0.09, 0.95, 0.96, 0.02), (u1 * 0.62, 0.93, 1.02, 0.09),
            (u1 * 0.86, 0.84, 0.88, 0.04), (u1 + 0.012, 0.74, 0.74, 0.0), (u1 + 0.05, 0.36, 0.36, 0.0)]
    G.loft(p, [(u, a * r, b * r, 0.0, c * r) for u, a, b, c in rows], ARM_SIDES, G.SKIN, cap0=True, cap1=True)
    bands = len(rows) - 1
    p.flat |= set(range(ARM_SIDES)) | set(range(ARM_SIDES * (bands - 1), ARM_SIDES * bands)) | {ARM_SIDES * bands, ARM_SIDES * bands + 1}
    return p


def forearm(st):
    """A forearm that swells below the elbow and narrows to the wrist, ending in the rolled red cuff."""
    p = G.Part()
    r = max(max(x[1], x[2]) for x in st) * ARM_FULL * 1.03
    u1 = st[-1][0]
    rings = [(-0.07, 0.42 * r, 0.42 * r, 0.0, 0.0), (0.035, 0.92 * r, 0.94 * r, 0.0, 0.0), (0.115, 0.8 * r, 0.82 * r, 0.0, 0.0),
             (u1 - 0.06, 0.6 * r, 0.6 * r, 0.0, 0.0), (u1 - 0.053, 0.76 * r, 0.76 * r, 0.0, 0.0),
             (u1 - 0.005, 0.86 * r, 0.86 * r, 0.0, 0.0), (u1 + 0.018, 0.74 * r, 0.74 * r, 0.0, 0.0)]
    G.loft(p, rings, ARM_SIDES, G.SKIN, cap0=True, cap1=True, mats=[G.SKIN, G.SKIN, G.SKIN, G.BAND, G.BAND, G.BAND])
    p.flat |= set(range(ARM_SIDES)) | {ARM_SIDES * (len(rings) - 1), ARM_SIDES * (len(rings) - 1) + 1}
    return p


def fist_with_pole(swung=False):
    """His right fist with the Power Pole in it, a little taller than he is. It runs through the fist the way the thumb points, with
    the long end ahead of the thumb. Being part of the hand, it follows every animation and every blend between them.
    swung: as the anime draws it at speed (pole-swing-airborne-secret-of-dragon-balls), straight below his grip, and above it lagging behind the swing and fanning out in the swing's plane."""
    p = fist(-1)
    if not swung:
        G.tube(p, (0.115, 0, -1.0), (0.115, 0, 2.0), 0.07, 8, G.POLE)
        return p
    sides = 8
    rings = []
    for w in (-1.0, -0.2, 0.15, 0.55, 0.95, 1.3, 1.65, 2.0):
        a = max(0.0, (w - 0.12) / 1.88)
        lag, across, along = 0.85 * a * a, 0.07 + 0.15 * a ** 1.5, 0.07 + 0.015 * a
        rings.append([p.v(0.115 + along * math.cos(2 * math.pi * k / sides), lag + across * math.sin(2 * math.pi * k / sides), w) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            n = (k + 1) % sides
            p.face((a[k], a[n], b[n], b[k]), G.POLE)
    p.face(list(reversed(rings[0])), G.POLE)
    p.face(rings[-1], G.POLE)
    return p


def fist_fingers(p, palm, k):
    """What makes it read as a fist (stance-ready-crouch-ep25): four knuckles standing round its end, so its outline is lumpy, with lines drawn between them, running up the back of his hand and
    over his curled fingers on the palm. u along the hand, v through it, w across it. A line is a thin strip lying on his skin: longer, or past the fist's edge, it stuck out as a spike."""
    cu, ru, rv, rw = 0.10 * k, 0.105 * k, 0.088 * k, 0.105 * k
    width = 0.05 * k

    def on_fist(angle, w, lift=1.04):
        across = math.sqrt(max(0.05, 1 - (w / rw) ** 2))
        return (cu + ru * across * math.cos(angle) * lift, palm * rv * across * math.sin(angle) * lift, w)
    for i in range(4):
        G.blob(p, on_fist(0.0, (-1.5 + i) * width, 0.9), (0.03 * k, 0.04 * k, 0.03 * k), 5, 3, G.SKIN)
    first = len(p.faces)
    half = 0.0032 * k
    for i in range(3):
        w = (-1 + i) * width
        for angles in ((-0.45, -0.75, -1.05), (0.42, 0.72, 1.0)):
            pairs = []
            for a in angles:
                at = on_fist(a, w)
                pairs.append((p.v(at[0], at[1], at[2] - half), p.v(at[0], at[1], at[2] + half)))
            for (a0, a1), (b0, b1) in zip(pairs, pairs[1:]):
                p.face((a0, a1, b1, b0), G.OUTLINE)
                p.face((b0, b1, a1, a0), G.OUTLINE)
    p.flat |= set(range(first, len(p.faces)))


def fist(palm):
    """A round fist, bigger than Tenkaichi's, with the thumb lying over the fingers. palm is the side of v his palm faces."""
    p = G.Part()
    k = 1.15
    G.blob(p, (0.10 * k, 0, 0.0), (0.105 * k, 0.088 * k, 0.105 * k), 7, 4, G.SKIN)
    p.flat |= {f for f, (idx, _, _) in enumerate(p.faces) if sum(p.verts[i][0] for i in idx) / len(idx) < 0.045 * k}
    first = len(p.faces)
    G.blob(p, (0.1 * k, palm * 0.07 * k, -0.036 * k), (0.03 * k, 0.026 * k, 0.05 * k), 8, 4, G.SKIN)
    p.flat |= {f for f in range(first, len(p.faces)) if sum(p.verts[i][0] for i in p.faces[f][0]) / len(p.faces[f][0]) < 0.1 * k}
    fist_fingers(p, palm, k)
    p.soft.update({i: (-0.7, -0.62, -0.35) for i in range(len(p.verts))})
    return p


def tube_along(p, pts, r, sides=6):
    """A round finger along a polyline (base, joints, tip), thinning a little toward a rounded tip."""
    from mathutils import Vector
    pts = [Vector(q) for q in pts]
    rings = []
    for i, c in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        s_ = d.orthogonal().normalized() if i == 0 else (s_ - d * s_.dot(d)).normalized()
        o = d.cross(s_)
        k = 1.0 - 0.18 * i / (len(pts) - 1)
        rings.append([p.v(*(c + (s_ * math.cos(2 * math.pi * j / sides) + o * math.sin(2 * math.pi * j / sides)) * r * k))
                      for j in range(sides)])
    for ra, rb in zip(rings, rings[1:]):
        for j in range(sides):
            n = (j + 1) % sides
            p.face((ra[j], ra[n], rb[n], rb[j]), G.SKIN)
    d = (pts[-1] - pts[-2]).normalized()
    end = p.v(*(pts[-1] + d * r * 0.4))
    for j in range(sides):
        p.face((rings[-1][j], rings[-1][(j + 1) % sides], end), G.SKIN)


def hand(center, half, chains, shape="open"):
    """His open hand or peace sign, about as wide as his fist (fist()): a slim palm, four short round fingers, a short
    thumb from the palm's lower edge. Only which side the palm and thumb face comes from Tenkaichi's measured hand
    (bt3.rip_hand); sized from Tenkaichi's chunky fingers, they came out huge. In his skin (u along the hand, v
    through it, w across it)."""
    from mathutils import Vector
    p = G.Part()
    thumb, fingers = chains[0], chains[1:]
    across = 1 if fingers[0][0][0].z > fingers[-1][0][0].z else -1
    palm_v = 1 if thumb[0][-1].y > center.y else -1
    k = 1.725
    pu, pv, pw = 0.06 * k, 0.034 * k, 0.07 * k
    G.blob(p, (0.02 * k, 0, 0), (pu, pv, pw), 8, 5, G.SKIN)
    G.loft(p, [(-0.05, pv * 0.7, pw * 0.5), (0.015 * k, pv * 0.7, pw * 0.55)], 6, G.SKIN)
    r = 0.016 * k
    lengths = (0.068, 0.075, 0.07, 0.058)
    for i in range(4):
        w = across * (0.0435 - 0.029 * i) * k
        base = Vector((0.06 * k, 0, w))
        extended = shape == "open" or i < 2
        if extended:
            spread = across * (0.02 if i == 0 else -0.02) * k if shape == "peace" else 0
            tube_along(p, [base, base + Vector((lengths[i] * k, 0, spread))], r)
        else:
            tip = base + Vector((0.01 * k, palm_v * 0.035 * k, 0))
            tube_along(p, [base, tip], r)
    start = Vector((0.012 * k, palm_v * 0.008 * k, across * 0.03 * k))
    if shape == "peace":
        end = start + Vector((0.04 * k, palm_v * 0.026 * k, across * 0.012 * k))
    else:
        end = start + Vector((0.035 * k, palm_v * 0.012 * k, across * 0.06 * k))
    tube_along(p, [start, end], r * 1.15)
    p.verts = [(u, -v, -w) for u, v, w in p.verts]
    return p


def rebuild(parts, fitted, rest):
    """Replace every part but the head with the anime body, sized from the rip's parts (rest: the skeleton)."""
    measure = lambda part, rings, **kw: fitted(part, rings, 6, [G.GI] * (rings - 1), **kw)[1]
    top, rings = torso(measure(parts["Torso"], 4, spread=0.74, top=0.88, bottom=0.12), rest["Torso"][0])
    parts["Torso"] = top
    parts["Butt"] = pelvis(measure(parts["Butt"], 4, spread=0.8), rings[0], rest["Torso"][0])
    for side in ("Left", "Right"):
        parts[f"{side} Hand DL"] = fist(1 if side == "Left" else -1)
        parts[f"{side} Arm Color"] = upper_arm(measure(parts[f"{side} Arm Color"], 2, start=-0.06))
        parts[f"{side} Forearm"] = forearm(measure(parts[f"{side} Forearm"], 3))
        th, knee = thigh(measure(parts[f"{side} Thigh Color"], 3, spread=0.97), rest[f"{side} Thigh"], rings[0][4] + SEAT_FORWARD)
        parts[f"{side} Thigh Color"] = th
        parts[f"{side} Leg"] = shin(measure(parts[f"{side} Leg"], 4, spread=0.97), knee, rest[f"{side} Shoe"][1])
        shoe = f"{side} Shoe" if side == "Left" else "Right Shoe DL"
        parts[shoe] = slipper(measure(parts[shoe], 3))
