"""Kid Goku's animations, authored as poses in code and written as Lua registrations (runs inside Blender).

Usage:
  blender -b --factory-startup --python scripts/blender/anims.py -- art/mario-anim-timing.json mod/kid-goku/anims-data.lua \
    SM64COOPDX/autogen/lua_definitions/constants.lua

Every one of Mario's 209 animation slots gets one of Goku's motions, resampled to that slot's frame count so SM64's
actions keep their timing (they read the frame number, not the pose). His own moves (Kamehameha, Nimbus)
get theirs under their own names.

A pose is joint angles in degrees on Mario's skeleton (the template's 20 animated bones):
  root (x, height, forward) in Blender units, or height None to stand the lowest sole on the floor
  lift: how far above the floor that lowest sole is, for the airborne beats of a run
  pelvis/torso/head (pitch forward, twist left, lean left)
  yaw: the whole body's turn about the vertical, for the actions where the game flips him 180 degrees part way through
  l_arm/r_arm (forward, out, twist) from hanging down; l_elbow/r_elbow bend; l_hand/r_hand (pitch, roll); l_wrist/r_wrist turn about the forearm
  l_hip/r_hip (forward, out, twist) from straight down; l_knee/r_knee bend; l_foot/r_foot pitch (toes down)
Angles are relative to the parent; a pose only lists what differs from STAND.
"""
from __future__ import annotations

import json
import math
import os
import sys

from mathutils import Matrix, Vector

SCALE = 212.766

ORDER = ["Body", "Butt", "Torso", "Head", "Left Arm", "Left Arm Color", "Left Forearm", "Left Hand", "Right Arm",
         "Right Arm Color", "Right Forearm", "Right Hand", "Left Thigh", "Left Thigh Color", "Left Leg", "Left Shoe",
         "Right Thigh", "Right Thigh Color", "Right Leg", "Right Shoe"]
PARENT = {"Butt": "Body", "Torso": "Butt", "Head": "Torso", "Left Arm": "Torso", "Left Arm Color": "Left Arm",
          "Left Forearm": "Left Arm Color", "Left Hand": "Left Forearm", "Right Arm": "Torso",
          "Right Arm Color": "Right Arm", "Right Forearm": "Right Arm Color", "Right Hand": "Right Forearm",
          "Left Thigh": "Butt", "Left Thigh Color": "Left Thigh", "Left Leg": "Left Thigh Color",
          "Left Shoe": "Left Leg", "Right Thigh": "Butt", "Right Thigh Color": "Right Thigh",
          "Right Leg": "Right Thigh Color", "Right Shoe": "Right Leg"}
REST = {"Torso": (0.22, 0, 0), "Head": (0.30, 0, 0), "Left Arm": (0.24, -0.36, -0.02), "Left Arm Color": (0, 0, 0),
        "Left Forearm": (0.25, 0, 0), "Left Hand": (0.24, 0, 0), "Right Arm": (0.24, 0.36, -0.02),
        "Right Arm Color": (0, 0, 0), "Right Forearm": (0.25, 0, 0), "Right Hand": (0.24, 0, 0),
        "Left Thigh": (0.0, -0.15, 0.0), "Left Thigh Color": (0, 0, 0), "Left Leg": (0.66, 0, 0),
        "Left Shoe": (0.60, 0, 0), "Right Thigh": (0.0, 0.15, 0.0), "Right Thigh Color": (0, 0, 0),
        "Right Leg": (0.66, 0, 0), "Right Shoe": (0.60, 0, 0)}
SOLE = [(-0.10, 0.15), (0.15, 0.16), (0.38, 0.15)]

_RIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "private", "build", "goku-rig.json")
if os.path.exists(_RIG):
    with open(_RIG) as _f:
        _rig = json.load(_f)
    REST = {k: tuple(v) for k, v in _rig["REST"].items()}
    SOLE = [tuple(p) for p in _rig["SOLE"]]

R0 = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
BODY = Matrix.Rotation(math.radians(90), 3, "Y")
PELVIS = Matrix(((0, 0, 1), (0, -1, 0), (1, 0, 0))).transposed()
DOWN = Matrix.Rotation(math.pi, 3, "Z")
FOOT = Matrix.Rotation(-math.pi / 2, 3, "Z")


def rz(d): return Matrix.Rotation(math.radians(d), 3, "Z")
def ry(d): return Matrix.Rotation(math.radians(d), 3, "Y")
def rx(d): return Matrix.Rotation(math.radians(d), 3, "X")


STAND = {
    "root": (0, None, 0), "lift": 0, "yaw": 0,
    "pelvis": (2, 0, 0), "torso": (-3, 0, 0), "head": (1, 0, 0),
    "l_arm": (6, 26, 0), "r_arm": (6, 26, 0), "l_elbow": 36, "r_elbow": 36,
    "l_hand": (0, 0), "r_hand": (0, 0), "l_wrist": 0, "r_wrist": 0,
    "l_hip": (5, 19, -20), "r_hip": (5, 19, -20), "l_knee": 12, "r_knee": 12, "l_foot": 0, "r_foot": 0,
}


def full(pose):
    p = dict(STAND)
    p.update(pose)
    return p


def local_rotations(p):
    """Each bone's rotation relative to its parent (what SM64 animates), for pose p."""
    loc = {"Body": BODY}
    pitch, twist, lean = p["pelvis"]
    world_pelvis = Matrix.Rotation(math.radians(p["yaw"]), 3, "Z") @ PELVIS @ rz(pitch) @ rx(twist) @ ry(-lean)
    world_body = R0 @ BODY
    loc["Butt"] = world_body.inverted() @ world_pelvis
    pitch, twist, lean = p["torso"]
    loc["Torso"] = rz(pitch) @ rx(twist) @ ry(-lean)
    pitch, twist, lean = p["head"]
    loc["Head"] = rz(pitch) @ rx(twist) @ ry(-lean)
    for side, s in (("Left", 1), ("Right", -1)):
        k = side[0].lower()
        fwd, out, tw = p[f"{k}_arm"]
        loc[f"{side} Arm"] = DOWN @ rz(-fwd) @ ry(-out * s) @ rx(tw * s)
        loc[f"{side} Arm Color"] = Matrix.Identity(3)
        loc[f"{side} Forearm"] = rz(-p[f"{k}_elbow"])
        hp, hr = p[f"{k}_hand"]
        loc[f"{side} Hand"] = rz(-hp) @ ry(-hr * s) @ rx(p[f"{k}_wrist"])
        fwd, out, tw = p[f"{k}_hip"]
        loc[f"{side} Thigh"] = DOWN @ rz(-fwd) @ ry(-out * s) @ rx(tw * s)
        loc[f"{side} Thigh Color"] = Matrix.Identity(3)
        loc[f"{side} Leg"] = rz(p[f"{k}_knee"])
        loc[f"{side} Shoe"] = FOOT @ rz(p[f"{k}_foot"])
    return loc


def sole_height(loc):
    """The lowest sole point's height with the hips at 0, standing."""
    world = {"Body": R0 @ BODY}
    head = {"Body": Vector(), "Butt": Vector()}
    low = 0.0
    for b in ORDER[1:]:
        par = PARENT[b]
        if b != "Butt":
            ox, oy, oz = REST[b]
            head[b] = head[par] + world[par] @ Vector((ox, oz, -oy))
        world[b] = world[par] @ loc[b]
        if b.endswith("Shoe"):
            for x, y in SOLE:
                low = min(low, (head[b] + world[b] @ Vector((x, y, 0))).z)
    return low


def sole_points(p, side):
    """The heights of one foot's sole points, heel to toe, with the hips at 0."""
    loc = local_rotations(p)
    world = {"Body": R0 @ BODY}
    head = {"Body": Vector(), "Butt": Vector()}
    for b in ORDER[1:]:
        par = PARENT[b]
        if b != "Butt":
            ox, oy, oz = REST[b]
            head[b] = head[par] + world[par] @ Vector((ox, oz, -oy))
        world[b] = world[par] @ loc[b]
    shoe = f"{side} Shoe"
    return [(head[shoe] + world[shoe] @ Vector((x, y, 0))).z for x, y in SOLE]


def solve(f, center, reach):
    """The angle within reach of center where f is nearest 0: the closest crossing, or failing one, its smallest."""
    samples = [center + reach * (k / 12 - 1) for k in range(25)]
    values = [f(a) for a in samples]
    crossings = [(a, b, fa, fb) for a, b, fa, fb in zip(samples, samples[1:], values, values[1:]) if fa * fb <= 0]
    if not crossings:
        return min(zip(samples, values), key=lambda v: abs(v[1]))[0]
    a, b, fa, _ = min(crossings, key=lambda c: abs((c[0] + c[1]) / 2 - center))
    for _ in range(20):
        m = (a + b) / 2
        fm = f(m)
        if fa * fm <= 0:
            b = m
        else:
            a, fa = m, fm
    return (a + b) / 2


def flat(pose, feet="lr"):
    """The pose with these feet's soles level, heel and toe both down, whatever the leg above them is doing. A foot left
    to its pose hovers on its toes with the heel in the air."""
    p = full(pose)
    for k in feet:
        side = "Left" if k == "l" else "Right"

        def tilt(angle):
            points = sole_points({**p, f"{k}_foot": angle}, side)
            return points[0] - points[-1]
        p[f"{k}_foot"] = solve(tilt, p[f"{k}_foot"], 70)
    return p


def sole_forward(p):
    """How far ahead of his hips the middle of his soles is."""
    loc = local_rotations(p)
    world = {"Body": R0 @ BODY}
    head = {"Body": Vector(), "Butt": Vector()}
    points = []
    for b in ORDER[1:]:
        par = PARENT[b]
        if b != "Butt":
            ox, oy, oz = REST[b]
            head[b] = head[par] + world[par] @ Vector((ox, oz, -oy))
        world[b] = world[par] @ loc[b]
        if b.endswith("Shoe"):
            points += [-(head[b] + world[b] @ Vector((x, y, 0))).y for x, y in SOLE]
    return sum(points) / len(points)


STANDING_FEET = sole_forward(STAND)


def planted(p):
    """The pose with where his hips go written out, so his soles are on the floor, and under him as they are standing, however his legs bend. Left at his position, his hips
    stay put as they bend and his feet swing out ahead of him."""
    p = full(p)
    return {**p, "root": (0, -sole_height(local_rotations(p)) + p["lift"], STANDING_FEET - sole_forward(p))}


def on_the_floor(motion):
    """The motion with his soles flat and still on the floor at every frame, not only at its key poses."""
    return lambda t: planted(flat(motion(t)))


def channels(p, compat=None):
    """The 63 animation channels for pose p: root translation, then each bone's XYZ rotation. With compat (each bone's angles
    on the frame before, filled in as it goes), each bone's angles stay the set nearest those: the same turn written as another set of angles
    spun the joint round between frames whenever the game blended or smoothed them."""
    loc = local_rotations(p)
    x, h, f = p["root"]
    if h is None:
        h = -sole_height(loc) + p["lift"]
    out = [round(x * SCALE), round(h * SCALE), round(f * SCALE)]
    for b in ORDER:
        e = loc[b].to_euler("XYZ", compat[b]) if compat is not None and b in compat else loc[b].to_euler("XYZ")
        if compat is not None:
            compat[b] = e
        out += [round(math.degrees(a) * 65536 / 360) for a in e]
    return out


def mix(a, b, t):
    """Blend two poses (missing keys from STAND)."""
    a, b = full(a), full(b)
    out = {}
    for k in a:
        va, vb = a[k], b[k]
        if isinstance(va, tuple):
            out[k] = tuple(None if (x is None or y is None) else x + (y - x) * t for x, y in zip(va, vb))
        else:
            out[k] = va + (vb - va) * t
    return out


def smooth(t): return t * t * (3 - 2 * t)


def keys(*ks, loop=False):
    """A motion through key poses: ks are (t, pose) with t in 0..1, eased between."""
    def at(t):
        if loop:
            t = t % 1.0
        for (t0, p0), (t1, p1) in zip(ks, ks[1:]):
            if t0 <= t <= t1:
                return mix(p0, p1, smooth((t - t0) / max(t1 - t0, 1e-6)))
        return full(ks[-1][1] if t > ks[-1][0] else ks[0][1])
    if loop and ks[-1][0] < 1.0:
        ks = ks + ((1.0, ks[0][1]),)
    return at


def pose(p): return lambda t: full(p)


LAG = {"torso": .5, "head": 1.2, "l_arm": 1, "r_arm": 1.5, "l_elbow": 2, "r_elbow": 2.5, "l_hand": 3, "r_hand": 3, "l_knee": .3, "r_knee": .6, "l_foot": .8, "r_foot": 1.1}
BODY_LAG = {k: v for k, v in LAG.items() if k[2:] not in ("knee", "foot")}


def flow(frames, *ks, lag=LAG, soft=1.0):
    """A motion through key poses at these frames of a clip this long, for what's in the air or landing. keys() eases to a stop at every pose, which looks fine for a
    punch and stiff for a body in flight. This passes through them at speed (a spline), settling only on the last, with each part trailing by its lag, and takes the
    edge off by averaging each frame with what's this many frames either side."""
    last = frames - 1
    times = [f / last for f, _ in ks]
    poses = [full(p) for _, p in ks]
    n = len(ks)

    def curve(i, u, get):
        v1, v2 = get(i), get(i + 1)
        if v1 is None or v2 is None:
            return None
        h = times[i + 1] - times[i]
        v0, v3 = get(i - 1) if i > 0 else None, get(i + 2) if i + 2 < n else None
        m1 = v2 - v1 if i == 0 or v0 is None else (v2 - v0) * h / (times[i + 1] - times[i - 1])
        m2 = 0 if i + 2 >= n or v3 is None else (v3 - v1) * h / (times[i + 2] - times[i])
        return ((2 * u ** 3 - 3 * u ** 2 + 1) * v1 + (u ** 3 - 2 * u ** 2 + u) * m1 + (-2 * u ** 3 + 3 * u ** 2) * v2 + (u ** 3 - u ** 2) * m2)

    def raw(t):
        out = {}
        for k, first in poses[0].items():
            tk = max(times[0], min(times[-1], t - lag.get(k, 0) / last))
            i = next((j for j in range(n - 1) if tk <= times[j + 1]), n - 2)
            u = (tk - times[i]) / (times[i + 1] - times[i])
            if isinstance(first, tuple):
                out[k] = tuple(curve(i, u, lambda j, c=c: poses[j][k][c]) for c in range(len(first)))
            else:
                out[k] = curve(i, u, lambda j: poses[j][k])
        return out

    def at(t):
        d = soft / last
        return mix(mix(raw(t - d), raw(t + d), .5), raw(t), .5)
    return at



GRIP_LAG = {"torso": .6, "head": 1.4, "l_arm": .8, "r_arm": .8, "l_elbow": .8, "r_elbow": .8, "l_hand": .8, "r_hand": .8}


def glide(frames, *ks, lag=BODY_LAG, soft=.6):
    """keys() on flow()'s spline (Metal Fox: fluid, connecting it all): ks are (t, pose) as for keys(), the clip this many frames
    long. It passes through each pose instead of stopping, its parts trailing by their lag, and still starts on its first
    pose and ends on its last, as the clips before and after it in a chain expect. A pose held twice becomes a moving hold,
    drifting on toward what comes next (or easing into the last pose), and elbows and knees never bend backward past
    straight however the curve swings."""
    times = [t for t, _ in ks]
    poses = [full(q) for _, q in ks]
    for i in range(1, len(poses)):
        if poses[i] == poses[i - 1]:
            if i + 1 < len(poses):
                poses[i] = mix(poses[i], poses[i + 1], .12)
            elif i >= 2:
                poses[i - 1] = mix(poses[i - 2], poses[i], .88)
    last = frames - 1
    keyed = [(t * last, q) for t, q in zip(times, poses)]
    trailing, exact = flow(frames, *keyed, lag=lag, soft=soft), flow(frames, *keyed, lag={}, soft=0)

    def at(t):
        settle = smooth(min(1.0, max(0.0, (t - .7) / .3)))
        q = mix(trailing(t), exact(t), settle) if settle > 0 else trailing(t)
        for k in ("l_elbow", "r_elbow", "l_knee", "r_knee"):
            q[k] = max(0.0, q[k])
        return q
    return at


def idle(t):
    """Standing ready: knees soft, fists loose in front of his hips, breathing, a little bounce a kid can't hold in."""
    b = math.sin(t * 2 * math.pi)
    sway = math.sin(t * 2 * math.pi + 1.1)
    return flat({
        "pelvis": (3, 3 * sway, 1.5 * sway), "torso": (-3 + 1.6 * b, -2 * sway, 0), "head": (1, 0, -1.5 * sway),
        "l_arm": (14 + 2 * b, 27, 0), "r_arm": (14 - 2 * b, 27, 0), "l_elbow": 48, "r_elbow": 48,
        "l_hip": (7, 19, -20), "r_hip": (7, 19, -20), "l_knee": 15 + 4 * b, "r_knee": 15 + 4 * b,
    })


def look(side):
    def f(t):
        p = idle(t)
        p["head"] = (-8, 20 * side * math.sin(min(t * 1.6, 1) * math.pi), 0)
        return p
    return f


def walk(t, lean=5, stride=30, swing=30):
    a = math.sin(t * 2 * math.pi)
    lift = lambda ph: 14 + 42 * max(0.0, math.sin(t * 2 * math.pi + ph))
    return full({
        "lift": 0.03 * abs(a),
        "pelvis": (lean, 7 * a, 2 * a), "torso": (0, -11 * a, 0), "head": (-lean + 2, 5 * a, -2 * a),
        "l_arm": (-swing * a + 6, 22, 0), "r_arm": (swing * a + 6, 22, 0), "l_elbow": 42, "r_elbow": 42,
        "l_hip": (stride * a + 4, 10, -12), "r_hip": (-stride * a + 4, 10, -12),
        "l_knee": lift(math.pi / 2), "r_knee": lift(-math.pi / 2),
        "l_foot": 12 * max(0.0, -a), "r_foot": 12 * max(0.0, a),
    })


def run(t):
    """anime-run/SnowGokuRun: he leans into it with his head leading and his arms flung out and straight back, fists
    clenched, barely moving while his legs do the work in great bounding strides, airborne between them. His front knee
    drives high; his back leg trails nearly straight."""
    w = t * 2 * math.pi
    a, c = math.sin(w), math.cos(w)
    knee = lambda v: 14 + 100 * max(0.0, v) ** 1.5
    return full({
        "root": (0, None, 0.06), "lift": 0.24 * abs(a) ** 1.5,
        "pelvis": (16, 11 * a, 0), "torso": (6, -13 * a, 0), "head": (-20, 6 * a, 0),
        "l_arm": (-58 - 6 * a, 20, 0), "r_arm": (-58 + 6 * a, 20, 0), "l_elbow": 6, "r_elbow": 6,
        "l_hip": (78 * a + 8, 7, -8), "r_hip": (-78 * a + 8, 7, -8),
        "l_knee": knee(c), "r_knee": knee(-c),
        "l_foot": -34 * max(0.0, -a) + 6, "r_foot": -34 * max(0.0, a) + 6,
    })


AIR = {"root": (0, 0.85, 0)}
TUCK = {**AIR, "pelvis": (20, 0, 0), "torso": (10, 0, 0), "head": (-14, 0, 0),
        "l_arm": (40, 30, 0), "r_arm": (40, 30, 0), "l_elbow": 100, "r_elbow": 100,
        "l_hip": (85, 10, -8), "r_hip": (85, 10, -8), "l_knee": 120, "r_knee": 120}
JUMP_UP = {**AIR, "pelvis": (0, -12, 0), "torso": (-10, 14, 0), "head": (-4, -4, 0),
           "r_arm": (158, 16, 0), "r_elbow": 16, "l_arm": (-26, 46, 0), "l_elbow": 62,
           "l_hip": (80, 14, -12), "l_knee": 112, "l_foot": -8, "r_hip": (-16, 12, -8), "r_knee": 46, "r_foot": -36}
JUMP_APEX = {**AIR, "pelvis": (0, -6, 0), "torso": (-4, 8, 0), "head": (2, -2, 0),
             "r_arm": (120, 24, 0), "r_elbow": 40, "l_arm": (-6, 54, 0), "l_elbow": 50,
             "l_hip": (56, 12, -10), "l_knee": 84, "l_foot": -10, "r_hip": (2, 12, -8), "r_knee": 44, "r_foot": -26}
JUMP_PUSH = {**AIR, "pelvis": (12, -6, 0), "torso": (6, 8, 0), "head": (-6, -2, 0), "r_arm": (40, 24, 0), "r_elbow": 70, "l_arm": (-30, 30, 0), "l_elbow": 60,
             "l_hip": (58, 14, -12), "l_knee": 86, "l_foot": 0, "r_hip": (8, 12, -8), "r_knee": 34, "r_foot": -30}
JUMP_TOP = {**AIR, "pelvis": (-6, -4, 0), "torso": (14, 4, 0), "head": (-10, -2, 0), "r_arm": (86, 20, 0), "r_elbow": 62, "l_arm": (78, 24, 0), "l_elbow": 66,
            "l_hip": (92, 34, -10), "l_knee": 114, "l_foot": 10, "r_hip": (70, 30, -8), "r_knee": 104, "r_foot": 8}
JUMP_DROP = {**AIR, "pelvis": (-2, 3, 0), "torso": (-4, -3, 0), "head": (10, 2, 0), "r_arm": (30, 78, 0), "r_elbow": 34, "l_arm": (22, 82, 0), "l_elbow": 30,
             "l_hip": (38, 12, -10), "l_knee": 62, "l_foot": -6, "r_hip": (14, 12, -8), "r_knee": 42, "r_foot": -14}
JUMP_REACH = {**AIR, "pelvis": (4, 0, 0), "torso": (2, 0, 0), "head": (12, 0, 0), "r_arm": (40, 86, 0), "r_elbow": 22, "l_arm": (34, 88, 0), "l_elbow": 22,
              "l_hip": (22, 12, -10), "l_knee": 34, "l_foot": -18, "r_hip": (8, 12, -8), "r_knee": 22, "r_foot": -18}
JUMP_FLAIL_A = {**JUMP_REACH, "pelvis": (2, 4, 0), "torso": (0, -4, 0), "r_arm": (54, 80, 0), "l_arm": (20, 84, 0), "l_hip": (34, 12, -10), "l_knee": 52, "r_hip": (2, 12, -8),
                "r_knee": 30}
JUMP_FLAIL_B = {**JUMP_REACH, "pelvis": (2, -4, 0), "torso": (0, 4, 0), "r_arm": (20, 84, 0), "l_arm": (54, 80, 0), "l_hip": (6, 12, -10), "l_knee": 30, "r_hip": (30, 12, -8),
                "r_knee": 50}
LONG_JUMP = {**AIR, "pelvis": (46, -8, 0), "torso": (16, 6, 0), "head": (-66, 2, 0), "r_arm": (142, 8, 78), "r_elbow": 10, "l_arm": (136, 6, 78), "l_elbow": 12,
             "l_hip": (141, 26, -10), "l_knee": 28, "l_foot": 30, "r_hip": (116, 22, -10), "r_knee": 34, "r_foot": 30}
LONG_JUMP_END = {**LONG_JUMP, "pelvis": (36, -8, 0), "head": (-56, 2, 0), "l_hip": (124, 26, -10), "l_knee": 34, "r_hip": (100, 22, -10), "r_knee": 38}
HEROIC = {**AIR, "pelvis": (6, -18, 0), "torso": (4, 22, 0), "head": (-14, -14, 0),
          "l_arm": (94, 10, 0), "l_elbow": 6, "r_arm": (-20, 40, 0), "r_elbow": 70,
          "l_hip": (68, 12, -10), "l_knee": 96, "l_foot": -12, "r_hip": (-22, 12, -8), "r_knee": 22, "r_foot": -38}
STOMP = {**AIR, "pelvis": (26, 0, 0), "torso": (14, 0, 0), "head": (-24, 0, 0), "l_arm": (70, 20, 30), "r_arm": (90, 40, 0),
         "l_elbow": 120, "r_elbow": 110, "l_hip": (72, 14, -12), "r_hip": (72, 14, -12), "l_knee": 96, "r_knee": 96,
         "l_foot": 24, "r_foot": 24}
FALL = {**AIR, "pelvis": (-4, 0, 0), "torso": (-6, 0, 0), "head": (6, 0, 0),
        "l_arm": (20, 70, 0), "r_arm": (20, 70, 0), "l_elbow": 30, "r_elbow": 30,
        "l_hip": (25, 10, -8), "r_hip": (5, 10, -8), "l_knee": 50, "r_knee": 35, "l_foot": -15, "r_foot": -15}
CROUCH = {"pelvis": (30, 0, 0), "torso": (14, 0, 0), "head": (-30, 0, 0),
          "l_arm": (50, 20, 0), "r_arm": (50, 20, 0), "l_elbow": 100, "r_elbow": 100,
          "l_hip": (80, 14, -14), "r_hip": (80, 14, -14), "l_knee": 130, "r_knee": 130, "l_foot": 40, "r_foot": 40}
SUPERMAN = {**AIR, "pelvis": (88, 0, 0), "torso": (2, 0, 0), "head": (-60, 0, 0),
            "l_arm": (170, 8, 0), "r_arm": (100, 30, 0), "l_elbow": 5, "r_elbow": 100,
            "l_hip": (-6, 6, 0), "r_hip": (-2, 6, 0), "l_knee": 20, "r_knee": 50, "l_foot": -40, "r_foot": -40,
            "l_wrist": 90, "r_wrist": -60}
LYING_BACK = {"root": (0, 0.18, 0), "pelvis": (-90, 0, 0), "torso": (-4, 0, 0), "head": (10, 0, 0),
              "l_arm": (10, 60, 0), "r_arm": (10, 60, 0), "l_elbow": 20, "r_elbow": 20,
              "l_hip": (6, 10, 0), "r_hip": (6, 10, 0), "l_knee": 10, "r_knee": 10, "l_foot": -30, "r_foot": -30}
LYING_FRONT = {"root": (0, 0.2, 0), "pelvis": (90, 0, 0), "torso": (4, 0, 0), "head": (-40, 20, 0),
               "l_arm": (160, 30, 0), "r_arm": (160, 30, 0), "l_elbow": 30, "r_elbow": 30,
               "l_hip": (-4, 10, 0), "r_hip": (-4, 10, 0), "l_knee": 20, "r_knee": 20, "l_foot": -50, "r_foot": -50}
HANG = {"root": (0, 0.85, 0), "pelvis": (0, 0, 0), "torso": (0, 0, 0), "head": (-12, 0, 0),
        "l_arm": (178, 10, 0), "r_arm": (178, 10, 0), "l_elbow": 15, "r_elbow": 15,
        "l_hip": (10, 6, -4), "r_hip": (2, 6, -4), "l_knee": 30, "r_knee": 20, "l_foot": -30, "r_foot": -30}
HOLD_FRONT = {"l_arm": (70, 4, 0), "r_arm": (70, 4, 0), "l_elbow": 40, "r_elbow": 40}
HOLD_OVER = {"l_arm": (175, 8, 0), "r_arm": (175, 8, 0), "l_elbow": 30, "r_elbow": 30}
TWIRL = {**AIR, "torso": (-8, 0, 0), "head": (-14, 0, 0), "l_arm": (0, 104, 0), "r_arm": (0, 96, 0), "l_elbow": 22, "r_elbow": 14,
         "l_hip": (38, 8, -6), "r_hip": (-4, 4, 0), "l_knee": 70, "r_knee": 8, "l_foot": 36, "r_foot": 44}


def carrying(motion):
    """The motion with both hands kept on what he carries. The game hangs it from his hand, so arms left to a jump or a fall fling it about."""
    return lambda t: {**full(motion(t)), **HOLD_FRONT}
SWIM_A = {"root": (0, 0.8, 0), "pelvis": (80, 0, 0), "torso": (0, 0, 0), "head": (-60, 0, 0),
          "l_arm": (170, 20, 0), "r_arm": (170, 20, 0), "l_elbow": 10, "r_elbow": 10,
          "l_hip": (0, 10, 0), "r_hip": (0, 10, 0), "l_knee": 30, "r_knee": 30, "l_foot": -50, "r_foot": -50}
SWIM_B = {**SWIM_A, "l_arm": (60, 80, 0), "r_arm": (60, 80, 0), "l_elbow": 30, "r_elbow": 30,
          "l_knee": 90, "r_knee": 90, "l_hip": (40, 30, 0), "r_hip": (40, 30, 0)}
TREAD = {"root": (0, 0.8, 0), "pelvis": (6, 0, 0), "head": (-6, 0, 0),
         "l_arm": (40, 50, 0), "r_arm": (40, 50, 0), "l_elbow": 40, "r_elbow": 40,
         "l_hip": (20, 14, 0), "r_hip": (10, 14, 0), "l_knee": 50, "r_knee": 40, "l_foot": -30, "r_foot": -30}
SIT_CROSSED = {"root": (0, 0.28, 0), "pelvis": (-6, 0, 0), "torso": (10, 0, 0), "head": (-6, 0, 0),
               "l_arm": (30, 20, 0), "r_arm": (30, 20, 0), "l_elbow": 70, "r_elbow": 70,
               "l_hip": (85, 55, -60), "r_hip": (85, 55, -60), "l_knee": 140, "r_knee": 140}


def mirror(motion):
    """The same motion with left and right swapped."""
    def f(t):
        p = motion(t)
        out = {}
        for k, v in p.items():
            k2 = ("r_" + k[2:]) if k.startswith("l_") else ("l_" + k[2:]) if k.startswith("r_") else k
            if k in ("pelvis", "torso", "head"):
                v = (v[0], -v[1], -v[2])
            out[k2] = v
        return out
    return f


def flip_pose(pose):
    """The same pose with left and right swapped."""
    out = {}
    for k, v in pose.items():
        k2 = ("r_" + k[2:]) if k.startswith("l_") else ("l_" + k[2:]) if k.startswith("r_") else k
        out[k2] = (v[0], -v[1], -v[2]) if k in ("pelvis", "torso", "head") else -v if k == "yaw" else v
    return out


READY = flat({"pelvis": (6, 0, 0), "torso": (2, 0, 0), "head": (-4, 0, 0), "l_arm": (30, 24, 0), "r_arm": (30, 24, 0),
              "l_elbow": 90, "r_elbow": 90, "l_hip": (20, 22, -20), "r_hip": (20, 22, -20), "l_knee": 34, "r_knee": 34})
ROCK_DRAW = {"pelvis": (6, 22, 0), "torso": (6, 20, 0), "head": (-8, -30, 0),
             "l_arm": (8, 32, 0), "l_elbow": 128, "r_arm": (54, 18, 0), "r_elbow": 94,
             "l_hip": (28, 22, -18), "r_hip": (6, 18, -16), "l_knee": 44, "r_knee": 28, "l_foot": 8}
ROCK_HIT = flat({"root": (0, None, 0.3), "pelvis": (24, -26, 0), "torso": (12, -24, 0), "head": (-34, 38, 0),
                 "l_arm": (140, 6, 0), "l_elbow": 0, "r_arm": (-14, 30, 0), "r_elbow": 112,
                 "l_hip": (88, 20, -18), "l_knee": 102, "r_hip": (-52, 16, -10), "r_knee": 6, "r_foot": -56}, "l")
SCISSORS_DRAW = flip_pose({**ROCK_DRAW, "l_arm": (30, 34, 0), "l_elbow": 134})
SCISSORS_HIT = flat(flip_pose({**ROCK_HIT, "l_arm": (146, 4, 0), "head": (-36, 30, 0), "torso": (10, -24, 0)}), "r")
PAPER_DRAW = {"pelvis": (4, 30, 0), "torso": (8, 26, 0), "head": (-6, -34, 0),
              "l_arm": (10, 40, 0), "l_elbow": 124, "l_hand": (-30, 0), "r_arm": (60, 14, 0), "r_elbow": 70,
              "l_hip": (24, 22, -18), "r_hip": (10, 18, -14), "l_knee": 40, "r_knee": 30}
PAPER_HIT = flat({"root": (0, None, 0.34), "pelvis": (26, -32, 0), "torso": (12, -24, 0), "head": (-40, 26, 0),
                  "l_arm": (138, 4, 0), "l_elbow": 2, "l_hand": (30, 0), "r_arm": (-18, 34, 0), "r_elbow": 96,
                  "l_hip": (92, 20, -18), "l_knee": 108, "r_hip": (-56, 16, -8), "r_knee": 6, "r_foot": -60}, "l")


def rock_in(t): return glide(5, (0, ROCK_DRAW), (1, ROCK_HIT))(t)
def rock_out(t): return glide(10, (0, ROCK_HIT), (0.3, ROCK_HIT), (1, READY))(t)
def scissors_in(t): return glide(4, (0, SCISSORS_DRAW), (1, SCISSORS_HIT))(t)
def scissors_out(t): return glide(13, (0, SCISSORS_HIT), (0.3, SCISSORS_HIT), (1, READY))(t)
def paper(t): return glide(26, (0, PAPER_DRAW), (0.16, PAPER_HIT), (0.52, PAPER_HIT), (1, READY))(t)


KICK_OUT = {**AIR, "pelvis": (-6, 78, 58), "torso": (6, -24, -6), "head": (-4, -46, -34),
            "r_hip": (6, 34, -70), "r_knee": 4, "r_foot": 0, "l_hip": (62, -14, -12), "l_knee": 108, "l_foot": -12,
            "r_arm": (30, 104, 0), "r_elbow": 26, "l_arm": (-14, 128, 0), "l_elbow": 16}
KICK_WIND = {**AIR, "pelvis": (-4, 40, 14), "torso": (12, -10, 0), "head": (-10, -24, -6), "r_hip": (94, 14, -6), "r_knee": 120,
             "r_foot": 14, "l_hip": (50, 14, -10), "l_knee": 104, "r_arm": (40, 30, 0), "r_elbow": 100, "l_arm": (50, 24, 0),
             "l_elbow": 100}
KICK_SNAP = {**KICK_OUT, "pelvis": (-8, 84, 66), "head": (-4, -50, -40), "r_hip": (6, 42, -70), "r_knee": 0, "r_foot": -4,
             "r_arm": (30, 116, 0), "r_elbow": 12, "l_arm": (-20, 140, 0), "l_elbow": 6}


FLY_KICK = {**AIR, "yaw": 93, "pelvis": (47.7, 2.6, 44.0), "torso": (-2.6, 14.8, 4.5), "head": (-39.8, -60, -30),
            "l_arm": (6.2, 35.7, 10.0), "r_arm": (95.3, 21.2, 37.5), "l_elbow": 108.8, "r_elbow": 51.9,
            "l_hand": (0.2, -1.7), "r_hand": (0, -2.5), "l_wrist": 40.0, "r_wrist": 165.6,
            "l_hip": (89.3, 58.0, 7.1), "r_hip": (-26.1, 46.6, 58.1), "l_knee": 63.5, "r_knee": 0, "l_foot": 27.2, "r_foot": 59.6}
FLY_CHAMBER = {**FLY_KICK, "yaw": 60, "r_hip": (70, 30, 20), "r_knee": 120, "r_foot": 20}


def flying_kick(t):
    """Knees up as he turns his side to the target, then the leg snaps out to the frame's kick and holds while the game carries him."""
    return glide(32, (0, TUCK), (0.09, FLY_CHAMBER), (0.2, FLY_KICK), (0.78, FLY_KICK), (1, FALL), lag=LAG)(t)


LUNGE = {**AIR, "pelvis": (-8, 58, 38), "torso": (10, -18, -4), "head": (-2, -36, -24),
         "r_hip": (8, 16, -70), "r_knee": 0, "r_foot": 0, "l_hip": (118, -22, -12), "l_knee": 142, "l_foot": -10,
         "r_arm": (96, 70, 0), "r_elbow": 18, "l_arm": (-10, 118, 0), "l_elbow": 60}
LUNGE_SNAP = {**LUNGE, "pelvis": (-10, 66, 46), "r_hip": (8, 22, -70), "r_foot": -4, "r_arm": (104, 84, 0), "r_elbow": 6,
              "l_arm": (-16, 130, 0), "l_elbow": 46}


def lunge(t):
    """He throws himself off the ground, boot leading and arms flung apart, then draws his other knee in as he flies."""
    return glide(20, (0, JUMP_UP), (0.16, LUNGE_SNAP), (0.5, LUNGE), (1, {**LUNGE, "l_knee": 146, "l_arm": (-8, 110, 0)}), lag=LAG)(t)


def lunge_skid(t):
    """Landing from the lunge on his feet: braced back on his rear knee with the front leg out, sliding."""
    return flat({"pelvis": (-14, 18, 0), "torso": (22, -8, 0), "head": (-16, -6, 0),
                 "l_arm": (24, 58, 0), "l_elbow": 40, "r_arm": (10, 62, 0), "r_elbow": 40,
                 "r_hip": (58, 14, -8), "r_knee": 18, "l_hip": (34, 22, -16), "l_knee": 104})


SIDE_CHAMBER = {"pelvis": (-6, 24, 0), "torso": (10, -8, 0), "head": (-6, -16, 0),
                "l_arm": (34, 10, 30), "l_elbow": 122, "r_arm": (44, 20, 30), "r_elbow": 122,
                "r_hip": (92, 14, -6), "r_knee": 112, "r_foot": 10, "l_hip": (8, 18, -16), "l_knee": 26}
SIDE_SNAP = flat({"yaw": 149, "pelvis": (20.2, -28.8, -5.7), "torso": (-1.7, -20.9, -6.8), "head": (27.4, -42.8, 1.4),
                  "r_arm": (37.8, 16.9, 36.2), "r_elbow": 89.8, "r_hand": (5.8, -31.7), "r_wrist": 135.0,
                  "l_arm": (47.0, 6.4, 61.0), "l_elbow": 84.2, "l_hand": (-66.4, 55.0), "l_wrist": 73.8,
                  "r_hip": (82.8, 145.6, -63.5), "r_knee": 10.0, "r_foot": 47.5,
                  "l_hip": (54.4, -18.7, 22.8), "l_knee": 50.4, "l_foot": 15.3}, "l")
SIDE_HIT = SIDE_SNAP
SIDE_CHAMBER = {**SIDE_CHAMBER, "yaw": 75}


def _kick_in(chamber, snap):
    return glide(8, (0, READY), (0.5, chamber), (1, snap))


def _kick_out(snap, hit):
    return glide(14, (0, snap), (0.2, hit), (0.55, hit), (1, READY))


side_kick_in = _kick_in(flip_pose(SIDE_CHAMBER), flip_pose(SIDE_SNAP))
side_kick_out = _kick_out(flip_pose(SIDE_SNAP), flip_pose(SIDE_HIT))
side_kick2_in = _kick_in(SIDE_CHAMBER, SIDE_SNAP)
side_kick2_out = _kick_out(SIDE_SNAP, SIDE_HIT)


def fight_ready(t):
    """stance-ready-crouch-ep25: a horse stance, knees right out over flat feet set wide, his chest turned toward the camera and his head back toward the target. His elbows stand out:
    the near fist up at chin height, a head's width off his face, the other out at his chest. He can't keep still in it: his weight rocks and his fists pump."""
    s = math.sin(t * 2 * math.pi)
    b = math.sin(t * 4 * math.pi)
    return flat({"pelvis": (12, 30 + 2 * s, 6), "torso": (6 + b, -4 - 2 * s, 0), "head": (-14, -26, -4),
                 "r_arm": (54 + 2 * s, 27, -52), "r_elbow": 83 - 3 * s, "r_hand": (-12, 24), "r_wrist": 169, "l_arm": (-14 - 2 * s, 107, 15), "l_elbow": 86 + 3 * s, "l_hand": (12, -25), "l_wrist": 155,
                 "l_hip": (78, 62, 0), "l_knee": 88 + 3 * b + 3 * s, "r_hip": (78, 62, 0), "r_knee": 88 + 3 * b - 3 * s})


WOLF = planted(flat({"pelvis": (45, 0, 0), "torso": (30, 0, 0), "head": (-45, 0, 0),
                     "l_arm": (-75, 8, 0), "l_elbow": 120, "r_arm": (-30, 20, 0), "r_elbow": 90,
                     "l_hip": (55, 14, -12), "r_hip": (55, 14, -12), "l_knee": 105, "r_knee": 105}))
WOLF_DEEP = planted(flat({"pelvis": (50, 0, 0), "torso": (32, 0, 0), "head": (-50, 0, 0),
                          "l_arm": (-92, 8, 0), "l_elbow": 130, "r_arm": (-46, 20, 0), "r_elbow": 100,
                          "l_hip": (60, 14, -12), "r_hip": (60, 14, -12), "l_knee": 116, "r_knee": 116}))
WOLF_SPRING = {**AIR, "pelvis": (8, 0, 0), "torso": (-4, 0, 0), "head": (-10, 0, 0), "l_arm": (-30, 58, 0), "l_elbow": 50, "r_arm": (-14, 62, 0), "r_elbow": 46,
               "l_hip": (24, 12, -10), "r_hip": (18, 12, -10), "l_knee": 30, "r_knee": 26, "l_foot": -28, "r_foot": -28}


stomp_enemy = flow(24, (0, WOLF), (3, WOLF_DEEP), (7, WOLF_SPRING), (11, JUMP_TOP), (16, JUMP_DROP), (20, JUMP_REACH), (23, JUMP_REACH), lag=BODY_LAG, soft=.5)


def flip(turns=1.0, start=TUCK, end=FALL, axis="pitch", tuck=TUCK):
    def f(t):
        p = mix(start, tuck, smooth(min(t * 4, 1)))
        if t > 0.75:
            p = mix(tuck, end, smooth((t - 0.75) * 4))
        a = 360 * turns * smooth(min(t / 0.85, 1))
        pitch, twist, lean = p["pelvis"]
        p["pelvis"] = (pitch - a, twist, lean) if axis == "pitch" else (pitch, twist, lean + a)
        return p
    return f


BACKFLIP_THROW = {**AIR, "pelvis": (-12, 0, 0), "torso": (-14, 0, 0), "head": (-22, 0, 0),
                  "l_arm": (160, 20, 0), "l_elbow": 20, "r_arm": (156, 22, 0), "r_elbow": 24,
                  "l_hip": (14, 10, -8), "r_hip": (8, 10, -8), "l_knee": 30, "r_knee": 24, "l_foot": -30, "r_foot": -30}
BACKFLIP_TUCK = {**AIR, "pelvis": (24, 0, 0), "torso": (26, 0, 0), "head": (-16, 0, 0),
                 "l_arm": (58, 16, 0), "r_arm": (58, 16, 0), "l_elbow": 70, "r_elbow": 70,
                 "l_hip": (128, 12, -8), "r_hip": (128, 12, -8), "l_knee": 148, "r_knee": 148, "l_foot": 30, "r_foot": 30}
BACKFLIP_OPEN = {**AIR, "pelvis": (12, 22, 0), "torso": (6, -12, 0), "head": (-14, 14, 0),
                 "r_arm": (84, 18, 0), "r_elbow": 18, "l_arm": (-12, 40, 0), "l_elbow": 110,
                 "l_hip": (54, 16, -12), "l_knee": 76, "l_foot": -10, "r_hip": (30, 16, -12), "r_knee": 52, "r_foot": -16}


LAND_TOUCH = {**JUMP_REACH, "root": (0, None, 0)}
LAND_DEEP = flat({"pelvis": (24, 4, 0), "torso": (14, -3, 0), "head": (-24, 2, 0), "l_arm": (-16, 62, 0), "r_arm": (-8, 66, 0), "l_elbow": 34, "r_elbow": 30,
                  "l_hip": (78, 14, -14), "r_hip": (82, 14, -14), "l_knee": 122, "r_knee": 128})
LAND_RISE = flat({"pelvis": (12, -2, 0), "torso": (2, 2, 0), "head": (-10, -2, 0), "l_arm": (8, 44, 0), "r_arm": (12, 46, 0), "l_elbow": 40, "r_elbow": 38,
                  "l_hip": (34, 16, -14), "r_hip": (36, 16, -14), "l_knee": 50, "r_knee": 54})
LAND_OVER = flat({"pelvis": (-2, 1, 0), "torso": (-6, -1, 0), "head": (2, 1, 0), "l_arm": (16, 26, 0), "r_arm": (18, 28, 0), "l_elbow": 50, "r_elbow": 52,
                  "l_hip": (4, 18, -16), "r_hip": (5, 18, -16), "l_knee": 6, "r_knee": 8})


def land_ready(t):
    return on_the_floor(flow(16, (0, LAND_TOUCH), (3, LAND_DEEP), (9, fight_ready(0)), (15, fight_ready(0)), lag=BODY_LAG, soft=.6))(t)


land = on_the_floor(flow(16, (0, LAND_TOUCH), (2.5, LAND_DEEP), (6.5, LAND_RISE), (10.5, LAND_OVER), (15, STAND), lag=BODY_LAG, soft=.6))


def steps_on(motion, first, frames):
    """A walk cycle moved along so his right foot lands on this frame of a loop this long, which is where SM64 plays the step. The right, because his first steps
    end just after it lands, so his legs carry on from them instead of swapping over."""
    return lambda t: motion(t + .75 - first / frames)


def from_frame(motion, start, frames):
    """A motion for a slot the game starts part way through: Mario's real landings start at frame 22 of 38 and 9 of 24 (art/mario-anim-timing.json has them at 0), so
    whatever a clip did before then was never seen. The whole motion goes in what's played."""
    return lambda t: motion(max(0.0, (t * (frames - 1) - start) / (frames - 1 - start)))


def ground_pound_start(t):
    return keys((0, TUCK), (0.8, {**TUCK, "pelvis": (20 - 360, 0, 0)}), (1, {**STOMP, "pelvis": (26 - 360, 0, 0)}))(t)


def gp_land(t):
    return glide(6, (0, STOMP), (0.2, {**CROUCH, "l_arm": (-30, 62, 0), "r_arm": (-30, 62, 0), "l_elbow": 40,
                                   "r_elbow": 40}), (1, CROUCH))(t)


def knockback(back: bool, air: bool):
    hit = {"pelvis": (-30 if back else 40, 0, 0), "torso": (-20 if back else 20, 0, 0), "head": (20, 0, 0),
           "l_arm": (60, 60, 0), "r_arm": (60, 60, 0), "l_elbow": 20, "r_elbow": 20,
           "l_hip": (30, 14, 0), "r_hip": (10, 14, 0), "l_knee": 40, "r_knee": 20}
    end = (LYING_BACK if back else LYING_FRONT) if not air else {**hit, **AIR}
    return glide(30, (0, hit), (1, end), lag=LAG if air else BODY_LAG)


def star_dance(t):
    """Goku_cheering: a crouch, a leap, both fists flung up and shaking, then his grin and peace sign at the end."""
    cheer = {"pelvis": (-2, 0, 0), "torso": (-10, 0, 0), "head": (-14, 0, 0), "l_arm": (140, 40, 30), "r_arm": (140, 40, 30),
             "l_elbow": 20, "r_elbow": 20, "l_hip": (6, 20, -20), "r_hip": (6, 20, -20), "l_knee": 14, "r_knee": 14}
    shake = {**cheer, "l_elbow": 46, "r_elbow": 46, "torso": (-14, 0, 0)}
    return glide(64, (0, STAND), (0.12, CROUCH), (0.28, {**cheer, "lift": 0.3, "l_knee": 40, "r_knee": 40}), (0.42, cheer),
                (0.5, shake), (0.58, cheer), (0.66, shake), (0.74, cheer),
                (0.94, {"r_arm": (95, 25, 40), "r_elbow": 60, "l_arm": (10, 30, 0), "l_elbow": 100,
                        "pelvis": (2, -10, 0), "head": (-4, 10, 0)}),
                (1, {"r_arm": (95, 25, 40), "r_elbow": 60, "l_arm": (10, 30, 0), "l_elbow": 100,
                     "pelvis": (2, -10, 0), "head": (-4, 10, 0)}))(t)


def scratch_head(t):
    """Goku's sheepish hand behind his head."""
    b = math.sin(t * 6 * math.pi)
    return full({"pelvis": (2, 0, 0), "torso": (0, 0, 4), "head": (-4, 0, 6),
                 "r_arm": (150, 40, -30), "r_elbow": 135 + 6 * b, "r_hand": (20, 0),
                 "l_arm": (10, 12, 0), "l_elbow": 40})


def sleep_sit(t):
    """Nodding off sitting up: not so far forward that his hair hides his shut eyes."""
    b = math.sin(t * 2 * math.pi)
    return full({**SIT_CROSSED, "torso": (16 + 3 * b, 0, 0), "head": (2 + 5 * b, 0, 9)})


def up_from_sitting(motion, sitting):
    """Getting up from a pose held until this point. Seated his hips rest on the floor, lower than his soles would put them, so they rise to meet his soles
    over a few frames instead of jumping there in one."""
    def at(t):
        p = motion(t)
        x, h, f = p["root"]
        if h is not None:
            return p
        seat = SIT_CROSSED["root"][1]
        feet = -sole_height(local_rotations(p)) + p["lift"]
        return {**p, "root": (x, seat + (feet - seat) * smooth(min(1.0, (t - sitting) / .15)), f)}
    return at


def wake_sitting(t):
    return up_from_sitting(glide(26, (0, sleep_sit(0)), (0.3, {**SIT_CROSSED, "torso": (6, 0, 0), "head": (-12, 0, 0)}), (0.72, CROUCH), (1, idle(0))), .3)(t)


def wake_lying(t):
    return up_from_sitting(glide(21, (0, sleep_back(0)), (0.35, {**SIT_CROSSED, "torso": (6, 0, 0), "head": (-8, 0, 0)}), (0.72, CROUCH), (1, idle(0))), .35)(t)


GAME_UNITS = SCALE / 4


def door_pull(t):
    """A door that swings toward him. SM64 stands him on the door and moves him by this clip's root (ROOT_WALKS): a hand to it while
    it swings, then on through."""
    going = max(0.0, min(1.0, (t - 0.32) / 0.6))
    reach = {"r_arm": (88, 14, 0), "r_elbow": 18, "pelvis": (4, 10, 0), "torso": (2, 8, 0)}
    p = walk(going * 3) if t >= 0.32 else keys((0, idle(0)), (0.14, reach), (0.24, reach), (0.32, walk(0)))(t)
    return {**p, "root": (0, None, (-109 + 408 * going) / GAME_UNITS)}


def door_push(t):
    """A door that swings away from him, so he just walks. SM64 keeps him faced along the door and turns him round only as he
    finishes, so he's walking backward as far as it knows and the clip has him the right way round."""
    going = min(1.0, t / 0.82)
    return {**walk(going * 3), "root": (0, None, (95 - 396 * going) / GAME_UNITS), "yaw": 180}


def climb(t):
    a = math.sin(t * 2 * math.pi)
    return full({**HANG, "root": (0, 0.75, 0.1), "l_arm": (170 + 10 * a, 10, 0), "r_arm": (170 - 10 * a, 10, 0),
                 "l_elbow": 40 + 30 * a, "r_elbow": 40 - 30 * a, "l_hip": (50 + 20 * a, 10, 0),
                 "r_hip": (50 - 20 * a, 10, 0), "l_knee": 80, "r_knee": 80})


def ledge_climb(t):
    return glide(10, (0, HANG), (0.5, {**CROUCH, "root": (0, 0.6, 0)}), (1, STAND))(t)


def swim(t):
    return keys((0, SWIM_A), (0.5, SWIM_B), (1, SWIM_A))(t)


def flutter(t):
    a = math.sin(t * 4 * math.pi)
    return full({**SWIM_A, "l_hip": (20 * a, 10, 0), "r_hip": (-20 * a, 10, 0)})


def tread(t):
    a = math.sin(t * 2 * math.pi)
    return full({**TREAD, "l_arm": (40 + 15 * a, 50, 0), "r_arm": (40 - 15 * a, 50, 0)})


def shiver(t):
    j = math.sin(t * 40 * math.pi) * 3
    return full({"pelvis": (10, 0, 0), "torso": (14, 0, 0), "head": (-10, j, 0), "l_arm": (40, 0, 30),
                 "r_arm": (40, 0, 30), "l_elbow": 130, "r_elbow": 130, "l_knee": 30, "r_knee": 30})


def shocked(t):
    j = math.sin(t * 50 * math.pi) * 8
    return full({"pelvis": (-6, j, 0), "torso": (-10, 0, j), "head": (10, 0, 0), "l_arm": (90, 80, 0),
                 "r_arm": (90, 80, 0), "l_elbow": 10, "r_elbow": 10, "l_hip": (10, 30, 0), "r_hip": (10, 30, 0)})


def push(t):
    a = math.sin(t * 2 * math.pi)
    return full({"pelvis": (30, 0, 0), "torso": (10, 0, 0), "head": (-30, 0, 0), "l_arm": (95, 10, 0),
                 "r_arm": (95, 10, 0), "l_elbow": 30, "r_elbow": 30, "l_hip": (30 + 20 * a, 6, 0),
                 "r_hip": (30 - 20 * a, 6, 0), "l_knee": 40, "r_knee": 40})


def slide(t):
    return full({"root": (0, 0.35, 0), "pelvis": (-50, 0, 0), "torso": (30, 0, 0), "head": (-10, 0, 0),
                 "l_arm": (40, 50, 0), "r_arm": (40, 50, 0), "l_elbow": 30, "r_elbow": 30,
                 "l_hip": (80, 8, 0), "r_hip": (60, 8, 0), "l_knee": 20, "r_knee": 60})


def slide_kick(t):
    return full({"root": (0, 0.3, 0), "pelvis": (-60, 0, 0), "torso": (40, 0, 0), "head": (-10, 0, 0),
                 "l_arm": (-30, 30, 0), "r_arm": (-30, 30, 0), "l_elbow": 20, "r_elbow": 20,
                 "l_hip": (95, 4, 0), "r_hip": (50, 10, 0), "l_knee": 0, "r_knee": 90})


SWEEP_DROP = {"pelvis": (40, 0, 18), "torso": (24, 0, 8), "head": (-46, 0, -10),
              "l_arm": (34, 20, 0), "r_arm": (26, 44, 0), "l_elbow": 10, "r_elbow": 14, "l_hand": (-60, 0), "r_hand": (-60, 0),
              "l_hip": (100, 26, -18), "l_knee": 150, "l_foot": 44,
              "r_hip": (14, 86, 0), "r_knee": 4, "r_foot": -8}


def _sweep_reach(out):
    """How far the swept foot's lowest point is above the planted one's, with the leg thrown out this far."""
    q = full({**SWEEP_DROP, "r_hip": (SWEEP_DROP["r_hip"][0], out, SWEEP_DROP["r_hip"][2])})
    return min(sole_points(q, "Right")) - min(sole_points(q, "Left"))


SWEEP_DROP["r_hip"] = (SWEEP_DROP["r_hip"][0], solve(_sweep_reach, 60, 30), SWEEP_DROP["r_hip"][2])


def leg_sweep(t):
    go = smooth(min(1.0, max(0.0, (t - 0.12) / 0.6)))
    p = glide(24, (0, CROUCH), (0.12, SWEEP_DROP), (0.72, SWEEP_DROP), (1, CROUCH), lag=BODY_LAG)(t)
    p["yaw"] = 360 * go if t < 0.995 else 0
    p["root"] = (0, -min(sole_points(p, "Left")), 0)
    return p

def crawl(t):
    a = math.sin(t * 2 * math.pi)
    return full({"root": (0, 0.42, 0), "pelvis": (75, 0, 0), "torso": (6, 0, 0), "head": (-60, 0, 0),
                 "l_arm": (85 + 20 * a, 10, 0), "r_arm": (85 - 20 * a, 10, 0), "l_elbow": 10, "r_elbow": 10,
                 "l_hip": (90 - 20 * a, 8, 0), "r_hip": (90 + 20 * a, 8, 0), "l_knee": 100, "r_knee": 100})


def skid(t):
    return full({"pelvis": (-14, 0, 0), "torso": (-10, 0, 0), "head": (10, 0, 0), "l_arm": (40, 50, 0),
                 "r_arm": (40, 50, 0), "l_elbow": 20, "r_elbow": 20, "l_hip": (40, 10, 0), "r_hip": (-20, 10, 0),
                 "l_knee": 20, "r_knee": 50})


def around(values, u):
    """A smooth curve through evenly spaced values around a loop, passing each at speed."""
    n = len(values)
    x = (u % 1.0) * n
    i = int(x)
    f = x - i
    a, b, c, d = (values[(i + k) % n] for k in (-1, 0, 1, 2))
    return 0.5 * (2 * b + (c - a) * f + (2 * a - 5 * b + 4 * c - d) * f * f + (3 * b - a - 3 * c + d) * f * f * f)


TIPTOE_HIP = (13, -6, -25, 1, 40, 33)
TIPTOE_KNEE = (16, 20, 10, 57, 72, 10)
TIPTOE_TOES = (30, 40, 50, 50, 30, 25)


def tiptoe(t):
    """Creeping on his toes, shaped on Mario's tiptoe, since no frame shows Goku sneaking: heels up and taller than he stands, sinking as each foot lands and rising as the
    next reaches out. His elbows stay out with his hands low. Mario's back pumps with each step; on Goku that read as bucking his chest, so his stays in a slight hunch."""
    pelvis, torso = 6 + 1.5 * math.cos(2 * math.pi * (2 * t - .26)), 6
    p = {"pelvis": (pelvis, 0, 0), "torso": (torso, 0, 0), "head": (2 - pelvis - torso, 0, 0)}
    for k in "lr":
        p[f"{k}_arm"] = (-44, 36, -28)
        p[f"{k}_elbow"] = 84
    legs = (("l", t - .25), ("r", t - .75))
    for k, u in legs:
        hip, knee = around(TIPTOE_HIP, u), around(TIPTOE_KNEE, u)
        p[f"{k}_hip"], p[f"{k}_knee"], p[f"{k}_foot"] = (hip, 8, -10), knee, hip - knee - pelvis
    p = flat(p)
    for k, u in legs:
        p[f"{k}_foot"] += around(TIPTOE_TOES, u)
    return p


def wave(t):
    a = math.sin(t * 6 * math.pi)
    return full({"r_arm": (150, 40 + 15 * a, 0), "r_elbow": 30, "l_arm": (10, 12, 0), "l_elbow": 40,
                 "head": (-8, 0, 0)})


def stuck_head(t):
    a = math.sin(t * 4 * math.pi)
    return full({"root": (0, 0.9, 0), "pelvis": (180, 0, 0), "l_hip": (20 * a, 20, 0), "r_hip": (-20 * a, 20, 0),
                 "l_knee": 30, "r_knee": 30, "l_arm": (20, 40, 0), "r_arm": (20, 40, 0)})


def stuck_legs(t):
    a = math.sin(t * 4 * math.pi)
    return full({"root": (0, 0.2, 0), "torso": (10 * a, 0, 0), "l_arm": (90, 60, 0), "r_arm": (90, 60, 0),
                 "l_elbow": 20 + 20 * a, "r_elbow": 20 - 20 * a})


def swing_bowser(t):
    return full({"pelvis": (-20, 0, 0), "torso": (-10, 0, 0), "head": (10, 0, 0), "l_arm": (80, 10, 0),
                 "r_arm": (80, 10, 0), "l_elbow": 10, "r_elbow": 10, "l_hip": (20, 20, 0), "r_hip": (-10, 20, 0),
                 "l_knee": 30, "r_knee": 30})


def throw(t):
    return glide(21, (0, {"torso": (-20, 30, 0), "r_arm": (150, 30, 0), "r_elbow": 60}),
                (0.4, {"torso": (20, -20, 0), "r_arm": (80, 10, 0), "r_elbow": 0}), (1, STAND))(t)


def pick_up(t):
    return glide(20, (0, STAND), (0.5, {**CROUCH, **HOLD_FRONT}), (1, {**STAND, **HOLD_FRONT}), lag=GRIP_LAG)(t)


def wing_fly(t):
    a = math.sin(t * 2 * math.pi)
    p = full(SUPERMAN)
    p["l_hip"] = (-6 + 6 * a, 6, 0)
    p["r_hip"] = (-2 - 6 * a, 6, 0)
    return p


def dying(t):
    return glide(60, (0, STAND), (0.3, {"torso": (40, 0, 0), "head": (30, 0, 0), "l_knee": 60, "r_knee": 60,
                                   "l_hip": (50, 10, 0), "r_hip": (50, 10, 0)}), (1, LYING_FRONT))(t)


KAME_KA = flat({"pelvis": (6, -14, -1.5), "torso": (6, -12, 0), "head": (-8, 26, 0),
                "l_arm": (66, -4, 36), "l_elbow": 66, "l_hand": (-20, 0), "r_arm": (40, 8, 0), "r_elbow": 92,
                "r_hand": (-20, 0), "l_hip": (66, 28, 0), "r_hip": (66, 28, 0), "l_knee": 72, "r_knee": 72})
KAME_ME = flat({"pelvis": (8, -26, -3.5), "torso": (12, -14, 0), "head": (-14, 40, 0),
                "l_arm": (76, -6, 56), "l_elbow": 76, "l_hand": (-10, 0), "r_arm": (24, 16, 0), "r_elbow": 118,
                "r_hand": (-10, 0), "l_hip": (78, 46, 0), "r_hip": (78, 46, 0), "l_knee": 84, "r_knee": 84})
KAME_CUP = flat({"pelvis": (12, -32, -6.4), "torso": (16, -16, 0), "head": (-22, 46, 0),
                 "l_arm": (78, -8, 68), "l_elbow": 84, "l_hand": (0, 0), "r_arm": (2, 34, 0), "r_elbow": 112,
                 "r_hand": (0, 0), "l_hip": (78, 58, 0), "r_hip": (78, 58, 0), "l_knee": 88, "r_knee": 88})
KAME_THRUST = flat({"root": (0, None, 0.2), "pelvis": (10, -4, 0), "torso": (6, 4, 0), "head": (-16, 0, 0),
                    "l_arm": (106, -14, 0), "l_elbow": 2, "l_hand": (-76, 0), "r_arm": (98, -14, 0), "r_elbow": 2,
                    "r_hand": (-76, 0), "l_hip": (100, 12, 0), "l_knee": 108, "r_hip": (-62, 14, -6), "r_knee": 4,
                    "r_foot": -62}, "l")
CHARGE_DRAW, CHARGE_HOLD = 34, 8
THRUST, BRACE, RECOVER = 3, 8, 10


def tremble(p, t, amount):
    """Shake with effort, in his arms only. t runs 0 to 1 over a loop. His head hangs off the end of his hips, torso and knees, so any wobble
    in those shook it, however small."""
    p = full(p)
    b = math.sin(t * 4 * math.pi + 0.7)
    for key in ("l_elbow", "r_elbow"):
        p[key] += amount * b
    return p


def kame_charge(t):
    f = t * (CHARGE_DRAW + CHARGE_HOLD - 1)
    if f >= CHARGE_DRAW:
        return tremble(KAME_CUP, (f - CHARGE_DRAW) / CHARGE_HOLD, 1.3)
    return glide(CHARGE_DRAW, (0, idle(0)), (6 / CHARGE_DRAW, KAME_KA), (14 / CHARGE_DRAW, KAME_ME), (24 / CHARGE_DRAW, KAME_CUP),
                (1, KAME_CUP), lag=GRIP_LAG)(f / CHARGE_DRAW)


def kame_fire(t):
    f = t * (THRUST + BRACE + RECOVER - 1)
    if f < THRUST:
        return mix(KAME_CUP, KAME_THRUST, smooth(f / THRUST))
    if f < THRUST + BRACE:
        return tremble(KAME_THRUST, (f - THRUST) / BRACE, 1.0)
    return mix(KAME_THRUST, idle(0), smooth((f - THRUST - BRACE + 1) / RECOVER))


def nimbus_call(t):
    """Goku_calling_Nimbus: chin up and shouting at the sky, a fist curled at his mouth and the other clenched low in front
    of him. "Nimbus!" Then a crouch, for the hop onto it."""
    call = flat({"pelvis": (-4, 8, 0), "torso": (-10, 4, 0), "head": (-20, 6, 0),
                 "l_arm": (110, 30, 60), "l_elbow": 90, "r_arm": (10, 30, 20), "r_elbow": 100,
                 "l_hip": (4, 16, -16), "r_hip": (-2, 16, -16), "l_knee": 8, "r_knee": 8})
    return glide(30, (0, call), (0.72, call), (1, CROUCH))(t)


NIMBUS_STAND = {"pelvis": (2, 0, 0), "torso": (-5, 0, 0), "head": (2, 0, 0),
                "l_arm": (8, 82, 0), "r_arm": (8, 82, 0), "l_elbow": 8, "r_elbow": 8,
                "l_hip": (50, 44, -34), "r_hip": (50, 44, -34), "l_knee": 84, "r_knee": 84}
NIMBUS_LAND = {"pelvis": (24, 0, 0), "torso": (12, 0, 0), "head": (-26, 0, 0),
               "l_arm": (20, 66, 0), "r_arm": (20, 66, 0), "l_elbow": 24, "r_elbow": 24,
               "l_hip": (66, 28, -24), "r_hip": (66, 28, -24), "l_knee": 104, "r_knee": 104}


def nimbus_board(t):
    """Out of the crouch, up off the ground with his arms high, knees tucked over the cloud, then down onto it and up to
    stand. The game has him at the top of his leap, where the cloud catches him, at 10 frames of 26."""
    leap = {"pelvis": (-4, 0, 0), "torso": (-8, 0, 0), "head": (-12, 0, 0), "l_arm": (150, 26, 0), "r_arm": (150, 26, 0),
            "l_elbow": 14, "r_elbow": 14, "l_hip": (4, 8, -8), "r_hip": (4, 8, -8), "l_knee": 8, "r_knee": 8,
            "l_foot": 30, "r_foot": 30}
    tuck = {"lift": 0.16, "pelvis": (10, 0, 0), "torso": (4, 0, 0), "head": (-14, 0, 0), "l_arm": (30, 76, 0), "r_arm": (30, 76, 0),
            "l_elbow": 30, "r_elbow": 30, "l_hip": (82, 24, -20), "r_hip": (82, 24, -20), "l_knee": 112, "r_knee": 112,
            "l_foot": 6, "r_foot": 6}
    return glide(26, (0, CROUCH), (0.12, leap), (0.32, tuck), (0.42, flat(NIMBUS_LAND)), (0.54, flat(NIMBUS_LAND)),
                (1, flat(NIMBUS_STAND)))(t)


def nimbus_stand(t):
    """Balancing on it, delighted: he rocks from foot to foot and his arms see-saw."""
    s = math.sin(t * 2 * math.pi)
    b = math.sin(t * 4 * math.pi)
    return flat({**NIMBUS_STAND, "pelvis": (2, 2 * s, 2 * s), "torso": (-5 + b, -2 * s, -s), "head": (2, 0, -2.5 * s),
                 "l_arm": (8, 82 + 7 * s, 0), "r_arm": (8, 82 - 7 * s, 0), "l_elbow": 8 + 3 * b, "r_elbow": 8 + 3 * b,
                 "l_knee": 84 + 5 * s, "r_knee": 84 - 5 * s})


def nimbus_fly(t):
    """Flying: down in a crouch and into the wind, his left fist thrown out ahead and up, his right arm flung back
    (Goku_riding_Flying_Nimbus_for_the_first_time, and its _2)."""
    b = math.sin(t * 2 * math.pi)
    w = math.sin(t * 6 * math.pi + 0.7)
    return flat({"pelvis": (14, 8, 0), "torso": (2 + b, -24, 0), "head": (-14, 16, 0),
                 "l_arm": (122 + 3 * b, 4, 0), "l_elbow": 8 + 3 * w, "r_arm": (-20 - 3 * b, 76, 0), "r_elbow": 12 + 3 * w,
                 "l_hip": (58, 22, -16), "l_knee": 88 + 3 * b, "r_hip": (14, 24, -16), "r_knee": 56 + 3 * b})


def nimbus_ride(t):
    """Hovering: sat cross-legged, leaning over his ankles and holding on to them, looking about him
    (ChichiAndGokuOnTheNimbus)."""
    b = math.sin(t * 2 * math.pi)
    look = math.sin(t * 2 * math.pi + 0.8)
    return full({"root": (0, 0.24, 0), "pelvis": (-8, 0, 0), "torso": (24 + 2 * b, 0, 1.5 * b), "head": (-16, -14 + 16 * look, 2 * look),
                 "l_arm": (50, -20, 40), "r_arm": (50, -20, 40), "l_elbow": 10, "r_elbow": 10,
                 "l_hip": (56, 66, -45), "r_hip": (56, 66, -45), "l_knee": 134, "r_knee": 138, "l_foot": -30, "r_foot": -30})


def nimbus_lie(t):
    """Goku_lying_on_the_Nimbus: flat on his back when the cloud has stopped, hands behind his head, one knee up and the other
    foot resting on it."""
    b = math.sin(t * 2 * math.pi)
    foot = math.sin(t * 4 * math.pi)
    return full({"root": (0, -0.10, 0), "pelvis": (-62, 0, 0), "torso": (-6 + 1.5 * b, 0, 0), "head": (28, 0, 0),
                 "l_arm": (180, 40, 60), "r_arm": (180, 40, 60), "l_elbow": 90, "r_elbow": 90,
                 "l_hip": (58, 10, -12), "l_knee": 56, "l_foot": -12, "r_hip": (70, 22, -30), "r_knee": 72,
                 "r_foot": -24 + 8 * foot})


def tired(t):
    """Winding down: his shoulders drop and his head nods."""
    slump = {"pelvis": (4, 0, 0), "torso": (12, 0, 0), "head": (6, 0, 0), "l_arm": (6, 14, 0), "r_arm": (6, 14, 0),
             "l_elbow": 18, "r_elbow": 18, "l_knee": 8, "r_knee": 8}
    nod = {**slump, "head": (15, 0, 2)}
    return glide(50, (0, idle(0)), (0.3, slump), (0.55, nod), (0.7, slump), (0.9, nod), (1, slump))(t)


def yawn(t):
    """Goku_wakes_up: a great stretch with his feet together, fists flung up in a V, his chest out and chin up."""
    slump = tired(1)
    stretch = {"pelvis": (-2, 0, 0), "torso": (-14, 0, 0), "head": (-26, 0, 0),
               "l_arm": (140, 40, 30), "r_arm": (140, 40, 30), "l_elbow": 30, "r_elbow": 30,
               "l_hip": (0, 7, -7), "r_hip": (0, 7, -7), "l_knee": 2, "r_knee": 2}
    return glide(59, (0, slump), (0.32, flat(stretch)), (0.72, flat({**stretch, "torso": (-18, 0, 3), "head": (-30, 0, 4)})), (1, slump))(t)


def sit_down(t):
    return glide(64, (0, tired(1)), (0.3, {**CROUCH, "root": (0, None, 0)}), (0.62, SIT_CROSSED),
                (1, {**SIT_CROSSED, "torso": (22, 0, 0), "head": (16, 0, 6)}))(t)


SLEEP_BACK = {"root": (0, 0.2, 0), "pelvis": (-88, 6, 0), "torso": (-2, -6, 0), "head": (6, 12, 0),
              "l_arm": (160, 34, 0), "l_elbow": 34, "r_arm": (34, 24, 40), "r_elbow": 96,
              "l_hip": (8, 22, -10), "l_knee": 14, "l_foot": -34, "r_hip": (44, 26, -24), "r_knee": 70, "r_foot": -18}


def lie_down(t):
    return glide(40, (0, {**SIT_CROSSED, "torso": (22, 0, 0), "head": (16, 0, 6)}), (0.7, SLEEP_BACK), (1, SLEEP_BACK))(t)


def sleep_back(t):
    """Flat on his back and fast asleep (Yamcha_Seeing_Goku_Asleep, GokuKrillinBeds), an arm flung out, his belly going up and
    down with his snores."""
    b = math.sin(t * 2 * math.pi)
    return full({**SLEEP_BACK, "torso": (-2 + 3 * b, -6, 0), "head": (6 - 3 * b, 12, 0), "r_elbow": 96 + 4 * b})


def panting(t):
    """Worn out and hungry: bent over with his hands on his belly, his shoulders heaving."""
    b = math.sin(t * 2 * math.pi)
    return flat({"pelvis": (8, 0, 0), "torso": (18 + 4 * b, 0, 0), "head": (-12 - 3 * b, 0, 0),
                 "l_arm": (26 - 3 * b, 16, 62), "r_arm": (26 - 3 * b, 16, 62), "l_elbow": 92, "r_elbow": 92,
                 "l_hip": (16, 19, -20), "r_hip": (16, 19, -20), "l_knee": 26 + 3 * b, "r_knee": 26 + 3 * b})


def hips(t):
    """Goku_walks_in_on_Bulma: fists on his hips, chest out, having a good look round."""
    b = math.sin(t * 2 * math.pi)
    akimbo = {"pelvis": (0, 0, 0), "torso": (-7 + 1.5 * b, 0, 0), "l_arm": (16, 60, 90), "r_arm": (16, 60, 90),
              "l_elbow": 80, "r_elbow": 80, "l_hip": (4, 21, -22), "r_hip": (4, 21, -22), "l_knee": 8, "r_knee": 8}
    looks = glide(75, (0, {**akimbo, "head": (2, 0, 0)}), (0.14, {**akimbo, "head": (-2, 38, 0)}), (0.42, {**akimbo, "head": (-2, 38, 0)}),
                 (0.58, {**akimbo, "head": (-2, -38, 0)}), (0.84, {**akimbo, "head": (-2, -38, 0)}), (1, {**akimbo, "head": (2, 0, 0)}))
    return flat(looks(t))


def flex(t):
    """Goku_acting_tough: chin down and chest puffed, both fists hauled up beside his shoulders, showing off."""
    tough = {"pelvis": (0, 0, 0), "torso": (-10, 0, 0), "head": (10, 0, 0), "l_arm": (64, 70, 0), "r_arm": (64, 70, 0),
             "l_elbow": 128, "r_elbow": 128, "l_hip": (6, 24, -24), "r_hip": (6, 24, -24), "l_knee": 16, "r_knee": 16}
    strain = {**tough, "torso": (-14, 0, 0), "l_elbow": 138, "r_elbow": 138, "l_arm": (72, 74, 0), "r_arm": (72, 74, 0)}
    return flat(glide(60, (0, tough), (0.22, tough), (0.38, strain), (0.5, tough), (0.66, strain), (0.8, strain), (1, tough))(t))


def fall(t):
    """Falling, g042-Gokufall: his arms and legs going, and his whole body turning a little with them."""
    a, c = math.sin(t * 2 * math.pi), math.cos(t * 2 * math.pi)
    return full({**FALL, "pelvis": (-4 + 3 * c, 5 * a, 2 * a), "torso": (-6 - 2 * c, -6 * a, 0), "head": (6 + 2 * a, 3 * c, 0),
                 "l_arm": (30 + 22 * a, 74, 0), "r_arm": (30 - 22 * a, 74, 0), "l_elbow": 34 + 14 * c, "r_elbow": 34 - 14 * c,
                 "l_hip": (28 + 14 * a, 10, -8), "r_hip": (8 - 14 * a, 10, -8), "l_knee": 52 + 14 * c, "r_knee": 38 - 14 * c,
                 "l_foot": -15 + 8 * a, "r_foot": -15 - 8 * a})


def burn(t):
    """His pants on fire: arms up and waving, legs running on air."""
    a = math.sin(t * 2 * math.pi)
    return full({**AIR, "pelvis": (8, 12 * a, 0), "torso": (-6, -14 * a, 0), "head": (-18, 8 * a, 0),
                 "l_arm": (150 + 22 * a, 34, 0), "r_arm": (150 - 22 * a, 34, 0), "l_elbow": 34, "r_elbow": 34,
                 "l_hip": (42 * a + 24, 8, -8), "r_hip": (-42 * a + 24, 8, -8), "l_knee": 62 - 28 * a, "r_knee": 62 + 28 * a})


def sideflip(t):
    """The game shows him turned 180 degrees through a side flip and its landing, so the flip has to come round itself."""
    p = flip(1.0, axis="lean")(t)
    p["yaw"] = 180 * smooth(min(t / 0.85, 1))
    return p


def sideflip_land(t):
    return {**land(t), "yaw": 180}


def turn(t):
    """Coming out of a skid: the game hands him the new direction at the end, so he has to get round to it himself."""
    drive = {"pelvis": (14, 0, 0), "torso": (4, 0, 0), "head": (-10, 0, 0), "l_arm": (30, 30, 0), "r_arm": (-10, 30, 0),
             "l_elbow": 90, "r_elbow": 90, "l_hip": (34, 10, -8), "r_hip": (-22, 10, -8), "l_knee": 40, "r_knee": 16}
    start = {**skid(0), "yaw": 0}
    return keys((0, start), (0.3, {**drive, "yaw": 50}), (0.75, {**drive, "yaw": 150}), (1, {**drive, "yaw": 180}))(t)


def menu(t):
    """Character Select's spotlight: stance, then a grin and a fist forward."""
    return keys((0, idle(0)), (0.4, {"r_arm": (90, 8, 0), "r_elbow": 10, "l_arm": (30, 18, 0), "l_elbow": 110,
                                     "pelvis": (8, 20, 0), "torso": (6, 14, 0), "head": (-10, -10, 0),
                                     "l_hip": (20, 14, -14), "r_hip": (-10, 10, 0)}), (1, idle(0)), loop=True)(t)



S = {
    "idle": idle, "look_l": look(1), "look_r": look(-1), "walk": walk, "run": run, "tiptoe": tiptoe, "tiptoe_step": steps_on(tiptoe, 14, 116),
    "jump": flow(38, (0, JUMP_PUSH), (4, JUMP_UP), (7.5, JUMP_APEX), (11, JUMP_TOP), (15, JUMP_TOP), (19, JUMP_DROP), (24, JUMP_REACH), (31, JUMP_FLAIL_A), (37, JUMP_FLAIL_B)),
    "double": flow(20, (0, JUMP_PUSH), (4, HEROIC), (10, {**HEROIC, "l_arm": (120, 14, 0), "l_elbow": 30, "r_hip": (6, 12, -8), "r_knee": 40}), (15, JUMP_APEX), (19, JUMP_TOP)),
    "double_fall": flow(30, (0, JUMP_TOP), (6, JUMP_DROP), (12, JUMP_REACH), (20, JUMP_FLAIL_A), (29, JUMP_FLAIL_B)), "fall": fall, "land": land, "land_single": from_frame(land, 22, 38), "land_general": from_frame(land, 9, 24), "tuck": pose(TUCK), "flip": flip(), "backflip": flip(2.0, start=BACKFLIP_THROW, tuck=BACKFLIP_TUCK, end=BACKFLIP_OPEN),
    "back_spin": flip(1.0, start=BACKFLIP_THROW, tuck=BACKFLIP_TUCK),
    "sideflip": sideflip, "sideflip_land": sideflip_land, "turn": turn, "triple": flip(2.0), "rock_in": rock_in, "rock_out": rock_out,
    "scissors_in": scissors_in, "scissors_out": scissors_out, "paper": paper,
    "kick": flying_kick, "lunge": lunge, "lunge_skid": lunge_skid, "stomp_enemy": stomp_enemy, "side_kick_in": side_kick_in, "side_kick_out": side_kick_out,
    "side_kick2_in": side_kick2_in, "side_kick2_out": side_kick2_out, "fight_ready": fight_ready, "land_ready": land_ready,
    "superman": pose(SUPERMAN),
    "belly": pose({**LYING_FRONT}), "crouch": pose(CROUCH), "crouch_in": glide(16, (0, STAND), (1, CROUCH)),
    "crouch_out": glide(16, (0, CROUCH), (1, STAND)), "crawl": crawl, "gp_start": ground_pound_start, "gp": pose(TUCK),
    "gp_land": gp_land, "stomp": pose(STOMP), "longjump": glide(20, (0, CROUCH), (0.3, LONG_JUMP), (0.62, LONG_JUMP), (1, LONG_JUMP_END), lag=LAG),
    "kb_back": knockback(True, False), "kb_front": knockback(False, False), "kb_air_back": knockback(True, True),
    "kb_air_front": knockback(False, True), "lying_back": pose(LYING_BACK), "lying_front": pose(LYING_FRONT),
    "dying": dying, "hang": pose(HANG), "climb": climb, "ledge_climb": ledge_climb, "swim": swim,
    "flutter": flutter, "tread": tread, "star": star_dance, "scratch": scratch_head, "sleep": sleep_sit,
    "tired": tired, "yawn": yawn, "wake_sitting": from_frame(wake_sitting, 6, 26), "wake_lying": wake_lying, "door_push": door_push, "door_pull": door_pull,
    "sit_down": sit_down, "lie_down": lie_down, "sleep_back": sleep_back, "panting": panting,
    "hips": hips, "flex": flex, "burn": burn, "nimbus_lie": nimbus_lie,
    "shiver": shiver, "shocked": shocked, "push": push, "slide": slide, "slide_kick": slide_kick, "leg_sweep": leg_sweep, "skid": skid,
    "wave": wave, "stuck_head": stuck_head, "stuck_legs": stuck_legs, "swing": swing_bowser, "throw": throw,
    "pick_up": pick_up, "hold": pose({**STAND, **HOLD_FRONT}), "hold_walk": lambda t: {**walk(t), **HOLD_FRONT},
    "hold_run": lambda t: {**run(t), **HOLD_FRONT}, "heavy": pose({**STAND, **HOLD_OVER}),
    "heavy_walk": lambda t: {**walk(t, stride=16), **HOLD_OVER}, "wing": wing_fly, "stand": pose(STAND),
    "kame_charge": kame_charge, "kame_fire": kame_fire,
    "nimbus_call": nimbus_call, "nimbus_board": nimbus_board, "nimbus_stand": nimbus_stand, "nimbus_ride": nimbus_ride,
    "nimbus_fly": nimbus_fly, "menu": menu,
    "twirl_start": glide(5, (0, JUMP_APEX), (1, TWIRL), lag=LAG), "twirl": pose(TWIRL),
    "hold_jump": carrying(flow(10, (0, JUMP_PUSH), (4, JUMP_UP), (9, JUMP_APEX))), "hold_fall": carrying(fall),
    "hold_land": carrying(land), "hold_slide": carrying(slide), "hold_stand_up": carrying(glide(16, (0, CROUCH), (1, STAND))),
}
LENGTHS = {"AIR_KICK": 32, "DOUBLE_JUMP_RISE": 20, "DOUBLE_JUMP_FALL": 30, "WAKE_FROM_SLEEP": 26, "TIPTOE": 116}
LOOPING = {"idle", "look_l", "look_r", "walk", "run", "tiptoe", "tiptoe_step", "crawl", "climb", "swim", "flutter", "tread", "fall",
           "sleep_back", "panting", "burn", "nimbus_lie", "fight_ready",
           "sleep", "shiver", "shocked", "push", "wave", "stuck_head", "stuck_legs", "hold_walk", "hold_run",
           "heavy_walk", "hold_fall", "wing", "nimbus_stand", "nimbus_ride", "nimbus_fly", "menu", "scratch", "slide", "superman"}

SLOTS = {
    "IDLE_HEAD_CENTER": "idle", "IDLE_HEAD_LEFT": "look_l", "IDLE_HEAD_RIGHT": "look_r", "FIRST_PERSON": "idle",
    "A_POSE": "stand", "WALKING": "walk", "RUNNING": "run", "RUNNING_UNUSED": "run", "TIPTOE": "tiptoe_step",
    "START_TIPTOE": "tiptoe", "WALK_PANTING": "panting", "SINGLE_JUMP": "jump", "DOUBLE_JUMP_RISE": "double",
    "DOUBLE_JUMP_FALL": "double_fall", "TRIPLE_JUMP": "triple", "TRIPLE_JUMP_FLY": "superman", "TRIPLE_JUMP_LAND": "land",
    "LAND_FROM_SINGLE_JUMP": "land_single", "LAND_FROM_DOUBLE_JUMP": "land", "GENERAL_FALL": "fall", "GENERAL_LAND": "land_general",
    "BACKFLIP": "backflip", "SLIDEFLIP": "sideflip", "SLIDEFLIP_LAND": "sideflip_land", "FORWARD_FLIP": "flip",
    "FORWARD_SPINNING": "flip", "BACKWARD_SPINNING": "back_spin", "FORWARD_SPINNING_FLIP": "flip",
    "START_FORWARD_SPINNING": "tuck", "SLIDEJUMP": "jump", "START_WALLKICK": "crouch",
    "FIRST_PUNCH": "rock_in", "FIRST_PUNCH_FAST": "rock_out", "SECOND_PUNCH": "scissors_in",
    "SECOND_PUNCH_FAST": "scissors_out",
    "GROUND_KICK": "paper", "AIR_KICK": "kick", "BREAKDANCE": "leg_sweep",
    "DIVE": "lunge", "SLIDE_DIVE": "belly", "AIRBORNE_ON_STOMACH": "superman", "LAND_ON_STOMACH": "belly",
    "SLOW_LAND_FROM_DIVE": "crouch_out", "FLY_FROM_CANNON": "superman", "WING_CAP_FLY": "wing",
    "FAST_LONGJUMP": "longjump", "SLOW_LONGJUMP": "longjump", "CROUCH_FROM_FAST_LONGJUMP": "crouch_out",
    "CROUCH_FROM_SLOW_LONGJUMP": "crouch_out",
    "START_CROUCHING": "crouch_in", "CROUCHING": "crouch", "STOP_CROUCHING": "crouch_out", "CRAWLING": "crawl",
    "START_CRAWLING": "crawl", "STOP_CRAWLING": "crouch",
    "START_GROUND_POUND": "gp_start", "TRIPLE_JUMP_GROUND_POUND": "gp_start", "GROUND_POUND": "stomp",
    "GROUND_POUND_LANDING": "gp_land",
    "BACKWARD_KB": "kb_back", "FORWARD_KB": "kb_front", "SOFT_BACK_KB": "kb_back", "SOFT_FRONT_KB": "kb_front",
    "BACKWARD_AIR_KB": "kb_air_back", "AIR_FORWARD_KB": "kb_air_front", "FALL_OVER_BACKWARDS": "kb_back",
    "GROUND_BONK": "kb_back", "DYING_ON_BACK": "lying_back", "DYING_ON_STOMACH": "lying_front",
    "DYING_FALL_OVER": "dying", "ELECTROCUTION": "shocked", "SHOCKED": "shocked", "FIRE_LAVA_BURN": "burn",
    "STAND_UP_FROM_LAVA_BOOST": "crouch_out",
    "IDLE_ON_LEDGE": "hang", "SLOW_LEDGE_GRAB": "hang", "FAST_LEDGE_GRAB": "hang", "CLIMB_DOWN_LEDGE": "ledge_climb",
    "HANG_ON_CEILING": "hang", "HANG_ON_OWL": "hang", "BEING_GRABBED": "hang",
    "CLIMB_UP_POLE": "climb", "GRAB_POLE_SHORT": "hang", "GRAB_POLE_SWING_PART1": "hang",
    "GRAB_POLE_SWING_PART2": "hang", "IDLE_ON_POLE": "hang", "MOVE_ON_WIRE_NET_RIGHT": "climb",
    "MOVE_ON_WIRE_NET_LEFT": "climb",
    "SWIM_PART1": "swim", "SWIM_PART2": "swim", "FLUTTERKICK": "flutter", "WATER_IDLE": "tread",
    "WATER_ACTION_END": "tread", "SWIM_WITH_OBJ_PART1": "swim", "SWIM_WITH_OBJ_PART2": "swim",
    "FLUTTERKICK_WITH_OBJ": "flutter", "WATER_IDLE_WITH_OBJ": "tread", "WATER_ACTION_END_WITH_OBJ": "tread",
    "BACKWARDS_WATER_KB": "kb_air_back", "WATER_FORWARD_KB": "kb_air_front", "WATER_DYING": "lying_back",
    "DROWNING_PART1": "shiver", "DROWNING_PART2": "lying_back", "FALL_FROM_WATER": "fall",
    "WATER_STAR_DANCE": "star", "RETURN_FROM_WATER_STAR_DANCE": "tread",
    "STAR_DANCE": "star", "RETURN_FROM_STAR_DANCE": "crouch_out", "SUMMON_STAR": "star",
    "START_SLEEP_IDLE": "tired", "START_SLEEP_SCRATCH": "scratch", "START_SLEEP_YAWN": "yawn",
    "START_SLEEP_SITTING": "sit_down", "SLEEP_IDLE": "sleep", "SLEEP_START_LYING": "lie_down", "SLEEP_LYING": "sleep_back",
    "WAKE_FROM_SLEEP": "wake_sitting", "WAKE_FROM_LYING": "wake_lying",
    "SHIVERING": "shiver", "SHIVERING_WARMING_HAND": "shiver", "SHIVERING_RETURN_TO_IDLE": "idle",
    "COUGHING": "shiver", "SUFFOCATING": "shiver", "PANTING": "idle",
    "PUSHING": "push", "STAND_AGAINST_WALL": "stand", "SIDESTEP_LEFT": "walk", "SIDESTEP_RIGHT": "walk",
    "SKID_ON_GROUND": "skid", "STOP_SKID": "crouch_out", "TURNING_PART1": "skid", "TURNING_PART2": "turn",
    "SLIDE": "slide", "STOP_SLIDE": "crouch_out", "FALL_FROM_SLIDE": "fall", "SLIDE_KICK": "slide_kick",
    "CROUCH_FROM_SLIDE_KICK": "crouch_out", "FALL_FROM_SLIDE_KICK": "fall", "SLIDE_MOTIONLESS": "slide",
    "HEAD_STUCK_IN_GROUND": "stuck_head", "BOTTOM_STUCK_IN_GROUND": "stuck_legs", "LEGS_STUCK_IN_GROUND": "stuck_legs",
    "GRAB_BOWSER": "hold", "SWINGING_BOWSER": "swing", "RELEASE_BOWSER": "throw", "HOLDING_BOWSER": "swing",
    "HEAVY_THROW": "throw", "THROW_LIGHT_OBJECT": "throw", "GROUND_THROW": "throw", "THROW_CATCH_KEY": "star",
    "PICK_UP_LIGHT_OBJ": "pick_up", "PLACE_LIGHT_OBJ": "crouch_in", "GRAB_HEAVY_OBJECT": "pick_up",
    "IDLE_WITH_LIGHT_OBJ": "hold", "WALK_WITH_LIGHT_OBJ": "hold_walk", "RUN_WITH_LIGHT_OBJ": "hold_run",
    "SLOW_WALK_WITH_LIGHT_OBJ": "hold_walk", "IDLE_HEAVY_OBJ": "heavy", "WALK_WITH_HEAVY_OBJ": "heavy_walk",
    "RIDING_SHELL": "crouch", "START_RIDING_SHELL": "crouch_in", "JUMP_RIDING_SHELL": "tuck",
    "BEND_KNESS_RIDING_SHELL": "crouch",
    "PUT_CAP_ON": "scratch", "TAKE_CAP_OFF_THEN_ON": "scratch", "QUICKLY_PUT_CAP_ON": "scratch",
    "MISSING_CAP": "scratch", "CREDITS_TAKE_OFF_CAP": "scratch",
    "PULL_DOOR_WALK_IN": "door_pull", "PUSH_DOOR_WALK_IN": "door_push", "UNLOCK_DOOR": "push",
    "START_REACH_POCKET": "scratch", "REACH_POCKET": "scratch", "STOP_REACH_POCKET": "idle",
    "RETURN_STAR_APPROACH_DOOR": "walk", "CREDITS_WAVING": "wave", "CREDITS_RAISE_HAND": "wave",
    "CREDITS_PEACE_SIGN": "star", "FINAL_BOWSER_RAISE_HAND_SPIN": "star",
    "DYING_IN_QUICKSAND": "stuck_legs", "IDLE_IN_QUICKSAND": "stuck_legs", "MOVE_IN_QUICKSAND": "stuck_legs",
    "HANDSTAND_IDLE": "stand", "HANDSTAND_LEFT": "walk", "HANDSTAND_RIGHT": "walk", "HANDSTAND_JUMP": "jump",
    "START_HANDSTAND": "crouch_in", "RETURN_FROM_HANDSTAND": "crouch_out",
    "START_TWIRL": "twirl_start", "TWIRL": "twirl", "TWIRL_LAND": "land",
    "JUMP_WITH_LIGHT_OBJ": "hold_jump", "FALL_WITH_LIGHT_OBJ": "hold_fall", "FALL_FROM_SLIDING_WITH_LIGHT_OBJ": "hold_fall",
    "JUMP_LAND_WITH_LIGHT_OBJ": "hold_land", "FALL_LAND_WITH_LIGHT_OBJ": "hold_land",
    "SLIDING_ON_BOTTOM_WITH_LIGHT_OBJ": "hold_slide", "STAND_UP_FROM_SLIDING_WITH_LIGHT_OBJ": "hold_stand_up",
    "STOP_SLIDE_LIGHT_OBJ": "hold_stand_up",
}


def slot_motion(name: str) -> str:
    if name in SLOTS:
        return SLOTS[name]
    for key, motion in (("CREDITS", "idle"), ("FALL", "fall"), ("LAND", "land"), ("JUMP", "jump"),
                        ("WATER", "tread"), ("SWIM", "swim"), ("WALK", "walk"), ("RUN", "run"), ("KB", "kb_back"),
                        ("DYING", "lying_back"), ("SLIDE", "slide"), ("CAP", "scratch")):
        if key in name:
            return motion
    return "idle"


ROOT_WALKS = (door_push, door_pull)


def encode(name: str, motion, frames: int, loop: bool) -> str:
    """One smlua_anim_util_register_animation call; constant channels are stored once."""
    frames = max(frames, 1)
    compat = {}
    samples = [channels(motion(f / frames if loop else f / max(frames - 1, 1)), compat) for f in range(frames)]
    values, index = [], []
    for c in range(63):
        col = [samples[f][c] & 0xFFFF for f in range(frames)]
        if all(v == col[0] for v in col):
            col = col[:1]
        index += [len(col), len(values)]
        values += col
    flags = 0 if loop else 1
    walks = motion in ROOT_WALKS
    if walks:
        flags |= 8
    yaws = [round(motion(f / frames if loop else f / max(frames - 1, 1)).get("yaw", 0) * 65536 / 360) for f in range(frames)]
    turns = f"GOKU_CLIP_YAW['{name}'] = {{{','.join(map(str, yaws))}}}\n" if any(yaws) else ""
    return (f"do local v, i = {{{','.join(map(str, values))}}},\n    {{{','.join(map(str, index))}}}\n"
            f"smlua_anim_util_register_animation('{name}', {flags}, 0, 0, 0, {frames}, v, i)\n"
            f"GOKU_ANIMS['{name}'] = true\nGOKU_CLIPS['{name}'] = {{v, i{', walks = true' if walks else ''}}} end\n{turns}")


def kame_emitter(p):
    """Between the open palms, just past them, in game units. Bake it so collision also works off camera."""
    loc = local_rotations(p)
    world = {"Body": R0 @ BODY}
    pos = {"Body": Vector(), "Butt": Vector()}
    for bone in ORDER[1:12]:
        par = PARENT[bone]
        if bone != "Butt":
            up, right, forward = REST[bone]
            pos[bone] = pos[par] + world[par] @ Vector((up, forward, -right))
        world[bone] = world[par] @ loc[bone]
    palm = sum((pos[b] + world[b] @ Vector((0.20, 0, 0)) for b in ("Left Hand", "Right Hand")), Vector()) / 2
    x, _, forward = p["root"]
    return tuple(round(v * SCALE / 4, 1) for v in (x + palm.x, palm.z - sole_height(loc) + p["lift"], forward - palm.y))




BARREL = ((0.0, .31, .24), (.06, .33, .26), (.17, .33, .25), (.33, .30, .22), (.46, .27, .18), (.55, .18, .12))
SEAT = ((-.24, .2, .16), (-.12, .3, .22), (0.0, .33, .26), (.23, .33, .26))


def arm_depth(p):
    """How deep his arms are inside his barrel or seat, at the worst point, in game units."""
    loc = local_rotations(p)
    world = {"Body": R0 @ BODY}
    pos = {"Body": Vector(), "Butt": Vector()}
    for bone in ORDER[1:]:
        par = PARENT[bone]
        if bone != "Butt":
            up, right, forward = REST[bone]
            pos[bone] = pos[par] + world[par] @ Vector((up, forward, -right))
        world[bone] = world[par] @ loc[bone]

    def inside(q, bone, table, r):
        v = world[bone].inverted() @ (q - pos[bone])
        if v.x < table[0][0] - r or v.x > table[-1][0] + r:
            return 0.0
        x = max(table[0][0], min(table[-1][0], v.x))
        for (a, wa, da), (b, wb, db) in zip(table, table[1:]):
            if a <= x <= b:
                t = (x - a) / max(b - a, 1e-6)
                w, d = wa + (wb - wa) * t + r, da + (db - da) * t + r
                return max(0.0, (1 - math.hypot(v.z / w, v.y / d)) * min(w, d))
        return 0.0
    worst = 0.0
    for side in ("Left", "Right"):
        s, e, w = pos[f"{side} Arm"], pos[f"{side} Forearm"], pos[f"{side} Hand"]
        points = [(s + (e - s) * .9, .04)] + [(e + (w - e) * t, .04) for t in (.33, .66, 1)] + [(w + world[f"{side} Hand"] @ Vector((.115, 0, 0)), .07)]
        for q, r in points:
            worst = max(worst, inside(q, "Torso", BARREL, r), inside(q, "Butt", SEAT, r))
    return worst * SCALE / 4


ARMS_CLEAR = {"fight_ready": 40}


def refuse_arms_through_him():
    """An arm set onto a target can go straight through him unless he turns (Metal Fox). These poses were set that way, with room for the two faces meeting."""
    for motion, frames in ARMS_CLEAR.items():
        worst = max(arm_depth(S[motion](f / (frames - 1))) for f in range(frames))
        print(f"arms in {motion}: {worst:.1f} units deep")
        if worst > 2.5:
            raise SystemExit(f"{motion}: his arms go {worst:.1f} units into his body")


def refuse_flat_tiptoe():
    """A foot angle's sign is easy to get backward, and a tiptoe on his heels once went unseen through three versions."""
    for i in range(116):
        p = full(tiptoe(i / 116))
        for side in ("Left", "Right"):
            heel, *_, toe = sole_points(p, side)
            if heel <= toe:
                raise SystemExit(f"tiptoe frame {i}: his {side} heel is at or below his toes")


def main() -> int:
    refuse_flat_tiptoe()
    refuse_arms_through_him()
    args = sys.argv[sys.argv.index("--") + 1:]
    timing = json.load(open(args[0]))
    consts = args[2]
    ids = {}
    for line in open(consts):
        if line.startswith("CHAR_ANIM_") and "=" in line:
            nm, val = line.split("=")[0].strip(), line.split("=")[1].split("-")[0].strip()
            if val.isdigit() and nm != "CHAR_ANIM_MAX":
                ids[nm[len("CHAR_ANIM_"):]] = int(val)
    out = ["-- Written by scripts/blender/anims.py from Goku's motions; don't edit by hand.\n",
           "if not _G.charSelectExists then return end\n", "GOKU_ANIMS = GOKU_ANIMS or {}\n",
           "GOKU_CLIPS = {}  -- their poses, for g-blend.lua\n",
           "GOKU_SLOT_ANIMS = {}\nGOKU_CLIP_YAW = {}\n"]
    done = {}
    for slot, cid in sorted(ids.items(), key=lambda kv: kv[1]):
        t = timing.get(f"{cid:02X}", {})
        frames = LENGTHS.get(slot) or int(t.get("loopEnd", 30)) or 30
        motion = slot_motion(slot)
        loop = motion in LOOPING
        key = f"goku_{motion}_{frames}"
        if key not in done:
            out.append(encode(key, S[motion], frames, loop))
            done[key] = True
        out.append(f"GOKU_SLOT_ANIMS[{cid}] = '{key}' -- {slot}\n")
    for motion, frames in (("kame_charge", CHARGE_DRAW + CHARGE_HOLD), ("kame_fire", THRUST + BRACE + RECOVER),
                           ("nimbus_call", 30), ("nimbus_board", 26),
                           ("nimbus_stand", 90), ("nimbus_ride", 150), ("nimbus_fly", 60), ("menu", 90), ("hips", 75), ("flex", 60), ("nimbus_lie", 80),
                           ("side_kick_in", 8), ("side_kick_out", 14), ("side_kick2_in", 7), ("side_kick2_out", 14),
                           ("lunge_skid", 20), ("stomp_enemy", 24), ("fight_ready", 40), ("land_ready", 16)):
        out.append(encode(f"goku_{motion}", S[motion], frames, motion in LOOPING))
    out.append("GOKU_KAME_PALMS = {\n")
    for phase, motion, frames in (("charge", kame_charge, CHARGE_DRAW + CHARGE_HOLD),
                                  ("fire", kame_fire, THRUST + BRACE + RECOVER)):
        points = [kame_emitter(motion(f / (frames - 1))) for f in range(frames)]
        out.append(f"    {phase} = {{" + ", ".join("{%g,%g,%g}" % point for point in points) + "},\n")
    out.append("}\n")
    with open(args[1], "w") as f:
        f.write("".join(out))
    print(f"wrote {len(done) + 17} animations for {len(ids)} slots to {args[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
