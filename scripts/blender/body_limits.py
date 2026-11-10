"""How far a pose of his is from what a body can do, measured from where his bones are, not from the angles that put
them there (runs inside Blender, for mathutils).

A fit or a solve can land every joint on its mark and still twist an arm behind him or fold his hips back: each
angle stays inside its range while their sum is a body nobody could hold (Metal Fox: "an impossible broken pose"). Two
measures, used by pose_fit.py as part of its cost:
  - limits: the plain anatomical ones, read in each joint's parent's axes: how far an upper arm swings behind his
    body (35 degrees, 70 when his arms swing back as in a run), a thigh behind him or across the other leg, how far
    his chest turns and tips on his hips and his head on his chest, a fist behind his chest, and his two fists at
    least a fist apart unless they meet on purpose (Metal Fox: an arm twisted behind him; fists behind him; hands merged);
  - strangeness: how far each limb's shape (upper arm and forearm in his chest's axes, thigh and shin in his hips')
    is from the nearest shape his own moves use. A shoulder's twist can't be read from one angle (it depends on the
    path the arm took), but an arm unlike anything he does is plain: the broken fit's arms sat 1.2 and 1.4 from
    his moves, the passed air swing's 0.4 and 0.2, while 95% of his moves' limbs are within 0.7 of another move's.
"""
from __future__ import annotations

import math

from mathutils import Vector

import anims as A
import pose_solve as S

LIMITS = {"arm_behind": 35, "thigh_behind": 45, "thigh_across": 40, "waist_turn": 40, "waist_tip": 45,
          "neck_turn": 75, "neck_tip": 50}
STRANGE = 0.8
FISTS_APART = 0.12


def _axes(world, bone):
    """A bone's own axes, in his axes (left, up, ahead): its up, ahead and left."""
    m = world[bone]
    return S.frame(m @ Vector((1, 0, 0))), S.frame(m @ Vector((0, 1, 0))), S.frame(m @ Vector((0, 0, 1)))


def _in(v, axes):
    up, ahead, left = axes
    return Vector((v.dot(left), v.dot(up), v.dot(ahead)))


def _read(p):
    pos, world = S.fk(A.full(p))
    f = S.frame
    torso, hips, head = _axes(world, "Torso"), _axes(world, "Butt"), _axes(world, "Head")
    shapes, m = {}, {}
    for side, s in (("Right", -1), ("Left", 1)):
        k = side[0].lower()
        sh, el, wr = f(pos[f"{side} Arm"]), f(pos[f"{side} Forearm"]), f(pos[f"{side} Hand"])
        arm, fore = _in(el - sh, torso).normalized(), _in(wr - el, torso).normalized()
        hp, kn, an = f(pos[f"{side} Thigh"]), f(pos[f"{side} Leg"]), f(pos[f"{side} Shoe"])
        thigh, shin = _in(kn - hp, hips).normalized(), _in(an - kn, hips).normalized()
        mirror = Vector((-s, 1, 1))
        shapes[f"{k}_arm"] = tuple(arm * mirror) + tuple(fore * mirror)
        shapes[f"{k}_leg"] = tuple(thigh * mirror) + tuple(shin * mirror)
        m[f"{k}_arm_behind"] = math.degrees(math.atan2(max(0.0, -arm.z), max(1e-6, math.hypot(arm.x, -min(arm.y, 0.0)))))
        m[f"{k}_fist_behind"] = -_in(wr - sh, torso).z
        m[f"{k}_thigh_behind"] = (math.degrees(math.atan2(max(0.0, -thigh.z), max(1e-6, -thigh.y))) if thigh.y < 0
                                  else 90.0 * max(0.0, -thigh.z))
        m[f"{k}_thigh_across"] = math.degrees(math.asin(max(0.0, min(1.0, -s * thigh.x))))
    c_up, c_ahead, _ = (_in(v, hips) for v in torso)
    m["waist_turn"] = abs(math.degrees(math.atan2(c_ahead.x, c_ahead.z)))
    m["waist_tip"] = math.degrees(math.acos(max(-1.0, min(1.0, c_up.y))))
    m["fists_apart"] = (f(pos["Right Hand"]) - f(pos["Left Hand"])).length
    h_up, h_ahead, _ = (_in(v, torso) for v in head)
    m["neck_turn"] = abs(math.degrees(math.atan2(h_ahead.x, h_ahead.z)))
    m["neck_tip"] = math.degrees(math.acos(max(-1.0, min(1.0, h_up.y))))
    return m, shapes


_LIBRARY = {}


def library(skip=()):
    """Every limb shape his moves use (24 moments of each), thinned to one per 0.1 so it stays quick."""
    key = tuple(sorted(skip))
    if key not in _LIBRARY:
        lib = {"arm": {}, "leg": {}}
        for name, motion in A.S.items():
            if name in skip:
                continue
            for i in range(24):
                try:
                    _, shapes = _read(motion(i / 23))
                except Exception:
                    continue
                for k, v in shapes.items():
                    lib[k[2:]][tuple(round(x, 1) for x in v)] = v
        _LIBRARY[key] = {k: list(v.values()) for k, v in lib.items()}
    return _LIBRARY[key]


def measures(p, skip=()):
    """The anatomical angles (degrees) and each limb's strangeness."""
    m, shapes = _read(p)
    lib = library(skip)
    for k, v in shapes.items():
        m[f"{k}_strange"] = min(math.dist(v, u) for u in lib[k[2:]])
    return m


def excess(p, skip=(), strange=STRANGE, arms_back=False, hands_touch=False):
    """What's past its limit, and by how much: degrees for an angle, distance for a limb's strangeness or a fist
    behind his chest. A fist behind his chest is only allowed with arms_back (a run swings them there; the limb
    library passed fists behind him in a guard because the run has that shape)."""
    out = {}
    got = measures(p, skip)
    if not hands_touch and got["fists_apart"] < FISTS_APART:
        out["fists_apart"] = FISTS_APART - got["fists_apart"]
    for k, v in got.items():
        if k == "fists_apart":
            continue
        if k.endswith("_arm_behind") and arms_back:
            v -= 35
        if k.endswith("_fist_behind"):
            if not arms_back and v > -0.05:
                out[k] = v + 0.05
            continue
        limit = strange if k.endswith("_strange") else LIMITS[k[2:] if k[:2] in ("r_", "l_") else k]
        if v > limit:
            out[k] = v - limit
    return out


def cost(p, skip=(), arms_back=False, hands_touch=False):
    """A smooth penalty for a fit: degrees past a limit in tens, strangeness in tenths. It starts below the strange
    limit, at 0.6, or a fit leans on the limit itself."""
    def scaled(k, d):
        if k.endswith("_fist_behind") or k == "fists_apart":
            return d / 0.01
        return d / 0.1 if k.endswith("_strange") else d / 10
    return sum(scaled(k, d) ** 2 for k, d in excess(p, skip, 0.6, arms_back, hands_touch).items())
