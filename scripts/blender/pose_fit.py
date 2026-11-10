"""Fits his rig to joints marked on an anime still: the camera and the joint angles whose picture lands on the marks
(runs inside Blender, for mathutils).

Usage:
  blender -b --factory-startup --python scripts/blender/pose_fit.py -- MARKS.json OUT.json [--starts N]

MARKS.json, in the still's own pixels at 900 across (the anime-reference skill's zoom.py coordinates):
  {"image": "...jpg", "points": {"head": [x, y], "neck": ..., "r_shoulder": ..., "r_elbow": ..., "r_wrist": ...,
   "l_shoulder", "l_elbow", "l_wrist", "pelvis", "r_hip", "r_knee", "r_ankle", "l_hip", "l_knee", "l_ankle"},
   "pole": [[x, y], [x, y]],
   "contacts": [["r_wrist", "l_wrist"]], "mirror": ["legs"], "grounded": ["r_ankle"], "face": "viewer"}
"r" and "l" are his right and left, not the picture's. Leave out what the still hides. "contacts" are joints that
touch in 3D (both fists on the pole); "mirror" holds "legs" or "arms" to mirror images with his hips square, when
the reading of the body says so (a split). "by" names who gave each fact, {"grounded": "metalfox", ...}: a fact not
Metal Fox's is refused unless --guess, and the fit fails (exit 2) when its best reading breaks a fact. "grounded" names the feet his weight is on, when he stands: the lowest
point of him, his weight over them, the camera level (Metal Fox: a still dramatizes; know whether he's airborne or
grounded, and let that place him). "face" is where he looks: "viewer", "seen" (only that the still shows his face),
"right" or "left" across the picture, or
[right, up, toward the viewer]; a look out of the side of his eyes is "head": {"turn": 20, "tuck": [10, 35]}
instead, his chin tucked and his head barely turned. His chest turns at most 35 degrees on his hips and his head
70 on his chest, and
body_limits.py keeps every joint in a body's range and every limb near a shape his own moves use.
"fists": "chin" holds both fists up in front of his chin, for a guard the still hides. "square" keeps his chest
and head turned with his hips (Metal Fox: a twist that turned him to look behind him was wrong).
These settle what a flat still leaves open.

A still is flat, so each limb could point toward the camera or away from it and look the same. The fit compares
bone directions (his proportions aren't the drawing's), uses each bone's drawn length against his to read how far it
points at the camera, and tries the camera from several sides and the limbs both ways round; OUT.json lists the
best few readings, each with its camera, for scripts/pose-from-still.mjs to draw beside the still. Which reading is
right is judged by eye from the three views: the pose-from-frame skill.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anims as A
import pose_solve as S
import body_limits

PARAMS = [("pelvis", 0, -60, 90), ("pelvis", 1, -90, 90), ("pelvis", 2, -40, 40),
          ("torso", 0, -30, 60), ("torso", 1, -60, 60), ("torso", 2, -30, 30),
          ("head", 0, -50, 40), ("head", 1, -60, 60), ("head", 2, -30, 30)]
for _s in ("r", "l"):
    PARAMS += [(f"{_s}_arm", 0, -70, 175), (f"{_s}_arm", 1, -90, 130), (f"{_s}_arm", 2, -150, 150), (f"{_s}_elbow", None, 0, 150),
               (f"{_s}_hip", 0, -60, 130), (f"{_s}_hip", 1, -20, 95), (f"{_s}_hip", 2, -90, 40), (f"{_s}_knee", None, 0, 150)]

BONES = [("neck", "head", 1.5), ("pelvis", "neck", 2), ("r_shoulder", "l_shoulder", 1), ("r_hip", "l_hip", 1),
         ("r_shoulder", "r_elbow", 1), ("r_elbow", "r_wrist", 1), ("l_shoulder", "l_elbow", 1), ("l_elbow", "l_wrist", 1),
         ("r_hip", "r_knee", 1.2), ("r_knee", "r_ankle", 1), ("l_hip", "l_knee", 1.2), ("l_knee", "l_ankle", 1)]


MASS = {"head": 0.22, "neck": 0.08, "pelvis": 0.24, "r_shoulder": 0.04, "l_shoulder": 0.04, "r_elbow": 0.02, "l_elbow": 0.02,
        "r_wrist": 0.01, "l_wrist": 0.01, "r_hip": 0.07, "l_hip": 0.07, "r_knee": 0.05, "l_knee": 0.05, "r_ankle": 0.04, "l_ankle": 0.04}


def joints(p):
    """His joints in his own axes (left, up, ahead)."""
    pos, world = S.fk(A.full(p))
    f = S.frame
    head = pos["Head"] + world["Head"] @ Vector((0.3, 0.17, 0))
    out = {"head": f(head), "neck": f(pos["Head"]), "pelvis": f(pos["Butt"]),
           "r_shoulder": f(pos["Right Arm"]), "r_elbow": f(pos["Right Forearm"]), "r_wrist": f(pos["Right Hand"]),
           "l_shoulder": f(pos["Left Arm"]), "l_elbow": f(pos["Left Forearm"]), "l_wrist": f(pos["Left Hand"]),
           "r_hip": f(pos["Right Thigh"]), "r_knee": f(pos["Right Leg"]), "r_ankle": f(pos["Right Shoe"]),
           "l_hip": f(pos["Left Thigh"]), "l_knee": f(pos["Left Leg"]), "l_ankle": f(pos["Left Shoe"])}
    out["_pole"] = f(world["Right Hand"] @ Vector((0, 1, 0)))
    out["_face"] = f(world["Head"] @ Vector((0, 1, 0)))
    out["_chin"] = f(pos["Head"] + world["Head"] @ Vector((0.0, 0.3, 0)))
    return out


def camera(yaw, pitch, roll):
    """His axes into the picture's: x right, y up, z toward the viewer. Yaw 0 looks at his front, so his left is
    on the picture's right."""
    return (Matrix.Rotation(math.radians(roll), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "X")
            @ Matrix.Rotation(math.radians(yaw), 3, "Y"))


def pose_of(base, x):
    p = dict(base)
    for (key, i, _, _), v in zip(PARAMS, x):
        if i is None:
            p[key] = v
        else:
            t = list(p[key])
            t[i] = v
            p[key] = tuple(t)
    return p


MIRROR = {"legs": [("hip", 0), ("hip", 1), ("hip", 2), ("knee", None)], "arms": [("arm", 0), ("arm", 1), ("arm", 2), ("elbow", None)]}


def mirrored(x, groups):
    """His left side set from his right, and his hips square to his chest, for the groups named."""
    x = list(x)
    index = {(k, i): n for n, (k, i, _, _) in enumerate(PARAMS)}
    for g in groups:
        for part, i in MIRROR[g]:
            x[index[(f"l_{part}", i)]] = x[index[(f"r_{part}", i)]]
        if g == "legs":
            x[index[("pelvis", 1)]] = 0
            x[index[("r_hip", 0)]] = x[index[("l_hip", 0)]] = 0
    return x


def fit(marks, starts=24, seed=5):
    pts = {k: Vector((v[0], -v[1])) for k, v in marks["points"].items()}
    pole = marks.get("pole")
    pole2 = (Vector((pole[1][0], -pole[1][1])) - Vector((pole[0][0], -pole[0][1]))).normalized() if pole else None
    bones = [(a, b, w) for a, b, w in BONES if a in pts and b in pts]
    base = A.full({**A.STAND, "r_wrist": 0, "l_wrist": 0})
    rest = joints(base)
    spine_drawn = (pts["neck"] - pts["pelvis"]).length if "neck" in pts and "pelvis" in pts else None
    spine_his = (rest["neck"] - rest["pelvis"]).length
    rng = random.Random(seed)
    x0 = [A.full(base)[k][i] if i is not None else A.full(base)[k] for k, i, _, _ in PARAMS]
    limits = [(lo, hi) for _, _, lo, hi in PARAMS] + [(-180, 180), (-60, 60), (-60, 60)]

    turn = {"torso": 25, "head": 25} if marks.get("square") else {"torso": 35, "head": 70}
    for n, (k, i, _, _) in enumerate(PARAMS):
        if k in turn and i == 1:
            limits[n] = (-turn[k], turn[k])
    head = marks.get("head")
    if head:
        for n, (k, i, _, _) in enumerate(PARAMS):
            if k == "head" and i == 1 and "turn" in head:
                limits[n] = (-head["turn"], head["turn"])
            if k == "head" and i == 0 and "tuck" in head:
                limits[n] = tuple(head["tuck"])
    grounded = marks.get("grounded", [])
    if grounded:
        limits[-1] = (0, 0)
        limits[-2] = (-35, 35)
    contacts = marks.get("contacts", [])
    mirror = set(marks.get("mirror", []))
    names = [k for k in pts if k in rest]
    marked = [pts[k] for k in names]
    mc = sum(marked, Vector((0, 0))) / len(marked)
    spread = math.sqrt(sum((m - mc).length_squared for m in marked) / len(marked))

    def cost(x):
        if mirror:
            x = mirrored(x, mirror)
        p = pose_of(base, x[:len(PARAMS)])
        cam = camera(*x[len(PARAMS):])
        j = joints(p)
        c = 0.0
        proj = [Vector(((cam @ j[k]).x, (cam @ j[k]).y)) for k in names]
        pc = sum(proj, Vector((0, 0))) / len(proj)
        ps = math.sqrt(sum((q - pc).length_squared for q in proj) / len(proj)) or 1e-6
        c += 3 * sum(((q - pc) / ps - (m - mc) / spread).length_squared for q, m in zip(proj, marked)) / len(proj)
        for a, b in contacts:
            c += 40 * max(0.0, (j[a] - j[b]).length - 0.16) ** 2
        if marks.get("fists") == "chin":
            chin = j["_chin"]
            for w in ("r_wrist", "l_wrist"):
                c += 40 * max(0.0, (j[w] - chin).length - 0.22) ** 2
        look = cam @ j["_face"]
        face = marks.get("face")
        if face == "viewer":
            c += 20 * max(0.0, 0.35 - look.z) ** 2
        elif face == "seen":
            c += 20 * max(0.0, 0.25 - look.z) ** 2
        elif face in ("right", "left"):
            c += 20 * max(0.0, 0.5 - (look.x if face == "right" else -look.x)) ** 2
        elif isinstance(face, list):
            want = Vector(face).normalized()
            c += 20 * (1 - look.normalized().dot(want)) ** 2
        if grounded:
            feet = [j[f] for f in grounded]
            low = min(v.y for k, v in j.items() if not k.startswith("_") and k not in grounded)
            for f in feet:
                c += 60 * max(0.0, f.y - low + 0.05) ** 2
            com = sum((j[k] * w for k, w in MASS.items()), Vector()) / sum(MASS.values())
            base_pt = sum(feet, Vector()) / len(feet)
            c += 80 * max(0.0, math.hypot(com.x - base_pt.x, com.z - base_pt.z) - 0.1) ** 2
        for a, b, w in bones:
            v3 = cam @ (j[b] - j[a])
            v2 = Vector((v3.x, v3.y))
            d = pts[b] - pts[a]
            if v2.length < 1e-6 or d.length < 1e-6:
                continue
            c += w * (1 - v2.normalized().dot(d.normalized())) * 4
            if spine_drawn:
                drawn, his = d.length / spine_drawn, v2.length / spine_his
                full = (j[b] - j[a]).length / spine_his
                c += 0.5 * w * (min(drawn, full) - his) ** 2 / max(full, 1e-3) ** 2
        if pole2 is not None:
            v3 = cam @ j["_pole"]
            v2 = Vector((v3.x, v3.y))
            if v2.length > 1e-6:
                c += 3 * (1 - abs(v2.normalized().dot(pole2)))
        c += 0.00002 * sum((a - b) ** 2 for a, b in zip(x[:len(PARAMS)], x0))
        c += 0.5 * body_limits.cost(p, arms_back=marks.get("arms") == "back", hands_touch=hands_touch(marks))
        return c
    results = []
    for s in range(starts):
        yaw = (s % 8) * 45 + rng.uniform(-15, 15)
        x = [v + rng.uniform(-40, 40) if s else v for v in x0] + [yaw, rng.uniform(-20, 20), 0]
        x = [max(lo, min(hi, v)) for v, (lo, hi) in zip(x, limits)]
        x = S.descend(cost, x, limits, starts=1)
        if marks.get("mirror"):
            x = mirrored(x, set(marks["mirror"]))
        results.append((cost(x), x))
    results.sort(key=lambda r: r[0])
    out, seen = [], []
    for c, x in results:
        p = pose_of(base, x[:len(PARAMS)])
        sig = joints(p)
        if any(max((sig[k] - o[k]).length for k in sig if not k.startswith("_")) < 0.08 for o in seen):
            continue
        seen.append(sig)
        keep = {k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items() if k in {q[0] for q in PARAMS}}
        out.append({"cost": round(c, 4), "camera": [round(v, 1) for v in x[len(PARAMS):]],
                    "pose": {k: ([round(u, 1) for u in v] if isinstance(v, list) else round(v, 1)) for k, v in keep.items()},
                    "facts": check_facts(marks, p, camera(*x[len(PARAMS):])),
                    "projected": projected(marks, p, camera(*x[len(PARAMS):]))})
        if len(out) == 4:
            break
    return out


FACTS = ("contacts", "mirror", "grounded", "face", "head", "square", "fists", "arms")


def hands_touch(marks):
    return any({a, b} == {"r_wrist", "l_wrist"} for a, b in marks.get("contacts", []))


def unconfirmed(marks):
    """The facts in the marks that Metal Fox didn't give: "by" names who gave each ("metalfox" or "agent")."""
    by = marks.get("by", {})
    return [f for f in FACTS if f in marks and by.get(f) != "metalfox"]


def check_facts(marks, p, cam):
    """Each fact the marks state, measured on the pose: [name, passed, what was measured]. A body's limits and his
    fists apart always count, whatever the marks say."""
    j = joints(p)
    m = body_limits.measures(p)
    look = cam @ j["_face"]
    out = []

    def add(name, ok, why):
        out.append([name, bool(ok), why])
    for a, b in marks.get("contacts", []):
        d = (j[a] - j[b]).length
        add(f"{a} touches {b}", d <= 0.2, f"{d:.2f} apart")
    for g in marks.get("mirror", []):
        pairs = [("hip", "knee")] if g == "legs" else [("arm", "elbow")]
        same = all(p[f"r_{x}"] == p[f"l_{x}"] for pair in pairs for x in pair)
        add(f"{g} mirrored", same, "one set of angles" if same else "they differ")
    grounded = marks.get("grounded", [])
    if grounded:
        low = min(v.y for k, v in j.items() if not k.startswith("_") and k not in grounded)
        com = sum((j[k] * w for k, w in MASS.items()), Vector()) / sum(MASS.values())
        for f in grounded:
            add(f"{f} planted, the lowest of him", j[f].y <= low + 0.02, f"{j[f].y:.2f} against {low:.2f}")
        base_pt = sum((j[f] for f in grounded), Vector()) / len(grounded)
        off = math.hypot(com.x - base_pt.x, com.z - base_pt.z)
        add("his weight over his planted foot", off <= 0.15, f"{off:.2f} off it")
    face = marks.get("face")
    if face == "viewer":
        add("face toward the viewer", look.z > 0.3, f"{look.z:+.2f}")
    elif face == "seen":
        add("face seen", look.z > 0.1, f"{look.z:+.2f}")
    elif face in ("right", "left"):
        x = look.x if face == "right" else -look.x
        add(f"face toward the picture's {face}", x > 0.3, f"{x:+.2f}")
    elif isinstance(face, list):
        d = look.normalized().dot(Vector(face).normalized())
        add(f"face toward {face}", d > 0.8, f"{d:.2f} of the way")
    head = marks.get("head")
    if head:
        if "turn" in head:
            add(f"head turned at most {head['turn']} on his chest", m["neck_turn"] <= head["turn"] + 2, f"{m['neck_turn']:.0f}")
        if "tuck" in head:
            lo, hi = head["tuck"]
            add(f"chin tucked {lo} to {hi}", lo - 2 <= p["head"][0] <= hi + 2, f"{p['head'][0]:.0f}")
    if marks.get("square"):
        add("chest and head square", m["waist_turn"] <= 27 and m["neck_turn"] <= 27, f"waist {m['waist_turn']:.0f}, neck {m['neck_turn']:.0f}")
    if marks.get("fists") == "chin":
        for w in ("r_wrist", "l_wrist"):
            d = (j[w] - j["_chin"]).length
            add(f"{w} up at his chin", d <= 0.27, f"{d:.2f} from it")
    over = body_limits.excess(p, arms_back=marks.get("arms") == "back", hands_touch=hands_touch(marks))
    add("a body: every joint in range, limbs like his moves, fists in front and apart", not over,
        ", ".join(f"{k} {v:.2f}" for k, v in over.items()) or "all inside")
    return out


def projected(marks, p, cam):
    """His joints as the still's camera sees them, placed on the still's pixels the way the fit matched them."""
    pts = {k: Vector((v[0], -v[1])) for k, v in marks["points"].items()}
    j = joints(p)
    names = [k for k in pts if k in j]
    marked = [pts[k] for k in names]
    mc = sum(marked, Vector((0, 0))) / len(marked)
    spread = math.sqrt(sum((q - mc).length_squared for q in marked) / len(marked))
    proj = {k: Vector(((cam @ v).x, (cam @ v).y)) for k, v in j.items() if not k.startswith("_")}
    used = [proj[k] for k in names]
    pc = sum(used, Vector((0, 0))) / len(used)
    ps = math.sqrt(sum((q - pc).length_squared for q in used) / len(used)) or 1e-6
    return {k: [round(((q - pc) / ps * spread + mc).x, 1), round(-((q - pc) / ps * spread + mc).y, 1)] for k, q in proj.items()}


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    marks = json.load(open(args[0], encoding="utf8"))
    starts = int(args[args.index("--starts") + 1]) if "--starts" in args else 24
    guesses = unconfirmed(marks)
    if guesses and "--guess" not in args:
        print(f"pose_fit: these facts aren't Metal Fox's: {', '.join(guesses)}. Ask him, and mark them \"by\": \"metalfox\"; or pass --guess to fit them as guesses.")
        return 1
    readings = fit(marks, starts)
    json.dump({"marks": args[0], "image": marks["image"], "unconfirmed": guesses, "readings": readings},
              open(args[1], "w", encoding="utf8"), indent=1)
    for i, r in enumerate(readings):
        bad = [f for f in r["facts"] if not f[1]]
        print(f"pose_fit: reading {i + 1}: cost {r['cost']}, camera yaw {r['camera'][0]} pitch {r['camera'][1]} roll {r['camera'][2]}, "
              f"{len(r['facts']) - len(bad)} of {len(r['facts'])} facts hold")
    for name, ok, why in readings[0]["facts"]:
        print(f"pose_fit:   {'PASS' if ok else 'FAIL'} {name}: {why}")
    if guesses:
        print(f"pose_fit: fitted with guesses, not Metal Fox's: {', '.join(guesses)}")
    return 0 if all(f[1] for f in readings[0]["facts"]) else 2


if __name__ == "__main__":
    sys.exit(main())
