"""Fits his rig to a 3D reference of a pose (a Meshy 7.1 figure made from an anime still): his joint angles, turn,
size and place, so the body his bones carry covers the reference's surface and stays inside it (runs inside
Blender, for mathutils).

Usage:
  blender -b private/build/goku.blend --python scripts/blender/pose_from_reference.py -- REFERENCE.glb OUT.json [--starts N] [--hops N] [--mirror-depth] [--joints JOINTS.json] [--facts MARKS.json] [--from FIT.json N [--hold PARTS]]

The reference is only a reference (Metal Fox: his model is already good): nothing of it enters his model or the game. It
replaces reading joints off a flat still, which left every limb's depth to a guess that kept coming out wrong; a
figure in 3D settles depth, and which leg kicks or which way he faces falls out of its shape. His body here is his own
mesh's points, each moving with its one bone (rounded shapes along his bones were too small for his head and hair, and
the fit grew him 1.9 times and curled him up). The cost: the reference's surface all near his, and his all near the
reference's, plus body_limits.py, so no fit leaves a body's range. Surfaces alone can't tell one limb from another
(a fit put his fists in his face and a hand between his legs), so --joints puts his joints on the reference's own
(scripts/reference_joints.py), and his hands and forearms are kept out of his head, body and legs. --facts takes the
still's marks (art/marks/NAME.json): the facts Metal Fox confirmed for it (head turn, chin tuck, fists, the planted foot)
are part of the cost, and each reading reports them passed or failed.

--mirror-depth flips the reference front to back along the still's own camera (Meshy's front, Blender's Y): a still
draws a figure and its depth mirror the same, and Meshy can build the wrong one. On the side kick it built Goku kicking
with his left leg, where Metal Fox confirmed his right kicks and his left is planted. A flip mends legs but not a face the still
shows, so his face keeps the unflipped figure's direction; and the flipped side kick put his back to the camera, where
the still shows his face, so its facts only hold on the unflipped figure kicking with his left (side_kick2's leg).
The still's camera is the reference's front, so its marks' "face" ([right, up, toward the viewer]) and "eyes" (his
eye line's rise across the picture, right eye to left, in degrees) are fitted and checked in it. --from FIT.json N
carries on from a reading, and --hold pelvis,l_hip,... keeps those parts (or "place") as it had them. OUT.json is in pose_fit.py's form (readings with a pose and a camera that looks at the
reference's front), for scripts/pose-preview.mjs; scripts/blender/reference_views.py draws him beside it.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector, kdtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anims as A
import body_limits
import pose_fit as F
import pose_solve as S

HEAD_CLEAR = 0.36
SKULL = 0.45
FACE_WEIGHT = float(os.environ.get("FACE_WEIGHT", 20))
ARMS = {"Right Hand", "Left Hand", "Right Forearm", "Left Forearm"}


JOINTS = {"r_shoulder": "Right Arm", "r_elbow": "Right Forearm", "r_wrist": "Right Hand",
          "l_shoulder": "Left Arm", "l_elbow": "Left Forearm", "l_wrist": "Left Hand",
          "r_hip": "Right Thigh", "r_knee": "Right Leg", "r_ankle": "Right Shoe",
          "l_hip": "Left Thigh", "l_knee": "Left Leg", "l_ankle": "Left Shoe"}
KEEP_OUT = [("Butt", "Torso", 0.2), ("Torso", "Head", 0.17),
            ("Right Thigh", "Right Leg", 0.1), ("Right Leg", "Right Shoe", 0.08),
            ("Left Thigh", "Left Leg", 0.1), ("Left Leg", "Left Shoe", 0.08)]


BONES = [("r_shoulder", "r_elbow"), ("r_elbow", "r_wrist"), ("l_shoulder", "l_elbow"), ("l_elbow", "l_wrist"),
         ("r_hip", "r_knee"), ("r_knee", "r_ankle"), ("l_hip", "l_knee"), ("l_knee", "l_ankle"),
         ("r_shoulder", "l_shoulder"), ("r_hip", "l_hip"), ("hips", "neck"), ("r_hip", "r_ankle"), ("l_hip", "l_ankle"), ("neck", "head"), ("neck", "head")]


def reference_joints(path, mirror, planted):
    """reference_joints.py's joints in this fit's space. A detector reads a kicking leg's knee and foot as the planted
    leg's, so only the planted leg (the side Metal Fox named) keeps its knee and ankle. Joints named in its "by_hand" were
    marked on the renders and triangulated, and are kept over the detector's: draw every joint back over the renders
    first (the detector's legs ran both chains to the planted foot, and fits aimed at them missed the kick).
    Without a hand-marked kick, the surface places it."""
    data = json.load(open(path, encoding="utf8"))
    joints = {k: Vector(v) for k, v in data["joints"].items()}
    face = (joints["nose"] - joints["head"]).normalized()
    if mirror != data.get("mirror_depth", False):
        swap = {"r": "l", "l": "r"}
        joints = {(swap[k[0]] + k[1:] if k[:2] in ("r_", "l_") else k): Vector((v.x, -v.y, v.z)) for k, v in joints.items()}
    kick = "r" if planted == "l" else "l"
    by_hand = {(swap[k[0]] + k[1:] if mirror != data.get("mirror_depth", False) and k[:2] in ("r_", "l_") else k)
               for k in data.get("by_hand", [])}
    kept = {k: joints[k] for k in by_hand if k in joints}
    ankles = [joints[f"{s}_ankle"] for s in "rl" if f"{s}_ankle" in joints and f"{s}_ankle" not in kept]
    foot = sum(ankles, Vector()) / len(ankles)
    knees = [joints[f"{s}_knee"] for s in "rl" if f"{s}_knee" in joints and f"{s}_knee" not in kept]
    knee = min(knees, key=lambda k: (k - foot).xy.length)
    for k in (f"{kick}_knee", f"{kick}_ankle"):
        joints.pop(k, None)
    joints[f"{planted}_ankle"], joints[f"{planted}_knee"] = foot, knee
    joints.update(kept)
    head = joints["head"]
    joints = {k: v for k, v in joints.items() if k in JOINTS}
    joints["head"] = head
    joints["hips"] = (joints["r_hip"] + joints["l_hip"]) / 2
    joints["neck"] = (joints["r_shoulder"] + joints["l_shoulder"]) / 2
    return joints, face


def _segment(q, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (q - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (q - (a + ab * t)).length


def reference_space(path, mirror=False):
    """Imports the reference into the open scene in the space every reference tool shares: unit scale 1 (the kept
    model's scene shrinks imports by 2.13), flipped front to back with --mirror-depth, its lowest point on the floor
    and centered over the origin. Returns its objects and the shift that centered it."""
    units = bpy.context.scene.unit_settings
    kept, units.scale_length = units.scale_length, 1.0
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    units.scale_length = kept
    objs = [o for o in bpy.data.objects if o not in before]
    flip = Matrix.Diagonal((1, -1 if mirror else 1, 1, 1))
    pts = [flip @ o.matrix_world @ v.co for o in objs if o.type == "MESH" for v in o.data.vertices]
    lo = Vector([min(p[k] for p in pts) for k in range(3)])
    hi = Vector([max(p[k] for p in pts) for k in range(3)])
    shift = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    for o in objs:
        if o.parent is None:
            o.matrix_world = Matrix.Translation(shift) @ flip @ o.matrix_world
    bpy.context.view_layer.update()
    return objs, shift


def reference_points(path, count=3600, seed=3, mirror=False):
    """Points spread over the reference's surface by area, in reference_space."""
    objs, shift = reference_space(path, mirror)
    tris = []
    for o in objs:
        if o.type != "MESH":
            continue
        m = o.data
        m.calc_loop_triangles()
        for t in m.loop_triangles:
            a, b, c = (o.matrix_world @ m.vertices[i].co for i in t.vertices)
            tris.append((a, b, c, ((b - a).cross(c - a)).length / 2))
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    rng = random.Random(seed)
    total = sum(t[3] for t in tris)
    picks = sorted(rng.random() * total for _ in range(count))
    pts, acc, i = [], 0.0, 0
    for a, b, c, area in tris:
        acc += area
        while i < len(picks) and picks[i] <= acc:
            u, v = rng.random(), rng.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            pts.append(a + (b - a) * u + (c - a) * v)
            i += 1
    return pts, shift


def his_points(per_bone=45, seed=5):
    """Points of his own mesh (the kept model's), each in its bone's frame: every part of him moves with one bone, so
    a pose places them with forward kinematics alone."""
    body = bpy.data.objects["Mario Mesh"]
    rig = bpy.data.objects["Mario"]
    names = {g.index: g.name for g in body.vertex_groups}
    groups = {}
    for v in body.data.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        if best is None or best.weight < 0.5:
            continue
        bone = names[best.group].replace(" DL", "").replace(" Color", "")
        if bone in rig.data.bones:
            groups.setdefault(bone, []).append(body.matrix_world @ v.co)
    rng = random.Random(seed)
    out = []
    for bone, verts in groups.items():
        rest = rig.data.bones[bone]
        to_bone = (rig.matrix_world @ rest.matrix_local).inverted()
        for v in rng.sample(verts, min(per_bone, len(verts))):
            out.append((bone, to_bone @ v))
    return out


def broken_facts(marks, p):
    """How far pose p is from the facts Metal Fox confirmed for this still (pose_fit's marks): 0 when it keeps them all."""
    if not marks:
        return 0.0
    c = 0.0
    head = marks.get("head", {})
    if "turn" in head:
        c += (max(0.0, body_limits.measures(p)["neck_turn"] - head["turn"]) / 10) ** 2
    if "tuck" in head:
        lo, hi = head["tuck"]
        c += (max(0.0, lo - p["head"][0], p["head"][0] - hi) / 10) ** 2
    j = F.joints(p)
    if marks.get("grounded"):
        com = sum((j[k] * w for k, w in F.MASS.items()), Vector()) / sum(F.MASS.values())
        base = sum((j[f] for f in marks["grounded"]), Vector()) / len(marks["grounded"])
        c += (max(0.0, math.hypot(com.x - base.x, com.z - base.z) - 0.15) / 0.05) ** 2
    if marks.get("fists") == "chin":
        c += sum((max(0.0, (j[w] - j["_chin"]).length - 0.27) / 0.1) ** 2 for w in ("r_wrist", "l_wrist"))
    return c


def fit(path, starts=16, seed=7, hops=0, mirror=False, joints=None, planted="l", marks=None, start=None, hold=()):
    ref, shift = reference_points(path, mirror=mirror)
    targets, face = reference_joints(joints, mirror, planted) if joints else ({}, None)
    if targets and f"{'l' if planted == 'r' else 'r'}_ankle" not in targets:
        kick = "l" if planted == "r" else "r"
        low = [q for q in ref if q.z < targets["neck"].z]
        far = max(low, key=lambda q: (q - targets["hips"]).length)
        shoe = [q for q in low if (q - far).length < 0.12]
        targets[f"{kick}_ankle"] = sum(shoe, Vector()) / len(shoe)
    tree = kdtree.KDTree(len(ref))
    for i, q in enumerate(ref):
        tree.insert(q, i)
    tree.balance()
    sample = ref[::2]
    his = his_points()
    pos, world = S.fk(A.full({**A.STAND, "r_wrist": 0, "l_wrist": 0}))
    skull = pos["Head"] + world["Head"] @ Vector((0.3, 0.17, 0))
    his = [(b, v) for b, v in his if b != "Head" or (pos[b] + world[b] @ v - skull).length < SKULL]
    base = A.full({**A.STAND, "r_wrist": 0, "l_wrist": 0})
    x0 = [base[k][i] if i is not None else base[k] for k, i, _, _ in F.PARAMS]
    limits = [(lo, hi) for _, _, lo, hi in F.PARAMS] + [(-180, 180), (60, 160), (-60, 60), (-60, 60), (-40, 80)]

    def placed(x):
        p = F.pose_of(base, x[:len(F.PARAMS)])
        yaw, s, tx, ty, tz = x[len(F.PARAMS)], *(v / 100 for v in x[len(F.PARAMS) + 1:])
        rot = Matrix.Rotation(math.radians(yaw), 3, "Z")
        move = Vector((tx, ty, tz))
        pos, world = S.fk(A.full(p))
        pts = [pos[b] + world[b] @ v for b, v in his]
        floor = min(q.z for q in pts)
        head = pos["Head"] + world["Head"] @ Vector((0.3, 0.17, 0))
        inside = 0.0
        for b, v in his:
            if b in ARMS:
                q = pos[b] + world[b] @ v
                inside += max(0.0, HEAD_CLEAR - (q - head).length) ** 2
                inside += sum(max(0.0, r - _segment(q, pos[a], pos[c])) ** 2 for a, c, r in KEEP_OUT)
        place = lambda q: rot @ (q - Vector((0, 0, floor))) * s + move
        mine = {k: rot @ pos[b] for k, b in JOINTS.items()}
        mine["hips"], mine["neck"] = (mine["r_hip"] + mine["l_hip"]) / 2, (mine["r_shoulder"] + mine["l_shoulder"]) / 2
        mine["head"] = rot @ head
        off, n, each = 0.0, 0, {}
        for a, b in BONES:
            if a in targets and b in targets:
                d, e = mine[b] - mine[a], targets[b] - targets[a]
                each[f"{a}-{b}"] = (d.normalized() - e.normalized()).length_squared
                off += each[f"{a}-{b}"]
                n += 1
        off /= max(n, 1)
        looks = 0.0
        still = (marks or {}).get("face")
        if isinstance(still, list):
            cam = F.camera(-yaw, 0, 0)
            looks = (cam @ S.frame(world["Head"] @ Vector((0, 1, 0))) - Vector(still).normalized()).length_squared
            if "eyes" in marks:
                e = cam @ S.frame(world["Head"] @ Vector((0, 0, 1)))
                want = math.radians(marks["eyes"])
                looks += 0.5 * (1 - (e.x * math.cos(want) + e.y * math.sin(want)) / max(math.hypot(e.x, e.y), 1e-6))
        elif face is not None:
            looks = (rot @ (world["Head"] @ Vector((0, 1, 0))) - face).length_squared
        return p, [place(q) for q in pts], floor, (inside, off, looks, each)

    def cost(x):
        p, pts, _, inside = placed(x)
        mine = kdtree.KDTree(len(pts))
        for i, q in enumerate(pts):
            mine.insert(q, i)
        mine.balance()
        c = sum(min(mine.find(q)[2], 0.2) ** 2 for q in sample) / len(sample)
        c += sum(min(tree.find(q)[2], 0.2) ** 2 for q in pts) / len(pts)
        return 40 * c + 0.3 * body_limits.cost(p) + 400 * inside[0] / len(pts) + 8 * inside[1] + FACE_WEIGHT * inside[2] + broken_facts(marks, p)
    rng = random.Random(seed)
    results = []
    for k in range(starts):
        yaw = (k % 8) * 45 + rng.uniform(-10, 10)
        x = [v + (rng.uniform(-35, 35) if k >= 8 else 0) for v in x0] + [yaw, 100, 0, 0, 0]
        x = [max(lo, min(hi, v)) for v, (lo, hi) in zip(x, limits)]
        x = S.descend(cost, x, limits, starts=1, spread=30)
        results.append((cost(x), x))
    if start:
        x = [start["pose"][k][i] if i is not None else start["pose"][k] for k, i, _, _ in F.PARAMS]
        x += [start["place"][0]] + [v * 100 for v in start["place"][1:]]
        for i, (k, _, _, _) in enumerate(F.PARAMS):
            if k in hold:
                limits[i] = (x[i], x[i])
        if "place" in hold:
            for i in range(len(F.PARAMS), len(limits)):
                limits[i] = (x[i], x[i])
        x = S.descend(cost, [max(lo, min(hi, v)) for v, (lo, hi) in zip(x, limits)], limits, starts=1, spread=10)
        results.append((cost(x), x))
    results.sort(key=lambda r: r[0])
    groups = {}
    for i, (k, _, _, _) in enumerate(F.PARAMS):
        side = k[:2] if k[:2] in ("r_", "l_") else ""
        groups.setdefault(side + ("leg" if "hip" in k or "knee" in k else "arm" if side else "body"), []).append(i)
    groups["place"] = list(range(len(F.PARAMS), len(limits)))
    names = sorted(groups)
    for r in range(min(2, len(results))):
        c, x = results[r]
        for h in range(hops):
            b = list(x)
            for i in groups[names[h % len(names)]]:
                b[i] = max(limits[i][0], min(limits[i][1], b[i] + rng.uniform(-60, 60)))
            b = S.descend(cost, b, limits, starts=1, spread=30)
            cb = cost(b)
            if cb < c:
                c, x = cb, b
        results[r] = (c, x)
    results.sort(key=lambda r: r[0])
    out = []
    for c, x in results[:4]:
        p, pts, floor, inside = placed(x)
        keep = {k: (list(v) if isinstance(v, tuple) else v) for k, v in p.items() if k in {q[0] for q in F.PARAMS}}
        yaw = x[len(F.PARAMS)]
        place = [yaw] + [v / 100 for v in x[len(F.PARAMS) + 1:]]
        out.append({"cost": round(c, 4), "camera": [round(-yaw, 1), 0, 0], "place": [round(v, 3) for v in place], "floor": round(floor, 4), "arms_inside": round(inside[0], 4), "bones_off_deg": round(math.degrees(2 * math.asin(min(1, math.sqrt(max(inside[1], 0)) / 2))), 1),
                    "each_bone_off_deg": {k: round(math.degrees(2 * math.asin(min(1, math.sqrt(v) / 2))), 1) for k, v in inside[3].items()},
                    "face_off_deg": round(math.degrees(2 * math.asin(min(1, math.sqrt(inside[2]) / 2))), 1),
                    "pose": {k: ([round(u, 1) for u in v] if isinstance(v, list) else round(v, 1)) for k, v in keep.items()},
                    "limits": {k: round(v, 2) for k, v in body_limits.excess(p).items()},
                    "facts": F.check_facts(marks or {}, A.full(p), F.camera(-yaw, 0, 0))})
    return out, shift


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    starts = int(args[args.index("--starts") + 1]) if "--starts" in args else 16
    hops = int(args[args.index("--hops") + 1]) if "--hops" in args else 24
    mirror = "--mirror-depth" in args
    joints = args[args.index("--joints") + 1] if "--joints" in args else None
    marks = json.load(open(args[args.index("--facts") + 1], encoding="utf8")) if "--facts" in args else None
    start = None
    if "--from" in args:
        i = args.index("--from")
        start = json.load(open(args[i + 1], encoding="utf8"))["readings"][int(args[i + 2]) - 1]
    hold = args[args.index("--hold") + 1].split(",") if "--hold" in args else ()
    planted = "r" if marks and marks.get("grounded") == ["r_ankle"] else "l"
    readings, shift = fit(args[0], starts, hops=hops, mirror=mirror, joints=joints, planted=planted, marks=marks, start=start, hold=hold)
    json.dump({"reference": args[0], "image": args[0], "shift": [round(v, 4) for v in shift], "mirror_depth": mirror, "readings": readings, "facts_from": "the reference's 3D shape"},
              open(args[1], "w", encoding="utf8"), indent=1)
    for i, r in enumerate(readings):
        for name, ok, why in r["facts"]:
            print(f"  {'PASS' if ok else 'FAIL'} {name}: {why}")
        print(f"pose_from_reference: reading {i + 1}: cost {r['cost']}, turn {r['place'][0]}, size {r['place'][1]}, bones off by {r['bones_off_deg']} deg, face off by {r['face_off_deg']}, arms inside him {r['arms_inside']}, past limits: {r['limits'] or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
