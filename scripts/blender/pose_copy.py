"""Copies a 3D reference's pose onto his rig bone by bone: each bone of his, from his hips out, turned to point along
the reference's matching bone, with nothing else deciding (runs inside Blender on the kept model, for his mesh).

Usage:
  blender -b private/build/goku.blend --python scripts/blender/pose_copy.py -- REFERENCE.glb JOINTS.json OUT.json

JOINTS.json is the reference's joints in reference_space (scripts/reference_joints.py's file, with the joints marked by
hand on its renders: "by_hand"). Draw every joint back over the renders before copying (Metal Fox: "rig the skeleton the same
as the 3D model"); a fit that weighed his surface, a still's facts and body limits against the joints compromised the
pose and never posed his feet or hands. Here each part takes only its own bones' directions:
  hips and chest   his hip line, spine and shoulder line
  head             skull to nose, skull to ear, and neck to skull
  each arm         shoulder to elbow, elbow to wrist, wrist to knuckles
  each leg         hip to knee, knee to ankle, and the shoe: ankle to sole, and heel to toe
His own nose, ear, knuckles, soles, toes and heels come from his mesh's materials. The reference's kicking shoe's long
axis is measured from its surface (its broader end is the toe). Only directions are copied: he is shorter-legged and
bigger-headed than a Meshy figure, so his joints can't all sit on its. OUT.json is in pose_from_reference.py's form,
each bone's miss in degrees under "each_bone_off_deg".
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
import pose_fit as F
import pose_from_reference as R
import pose_solve as S

SIDES = {"r": "Right", "l": "Left"}
HAND = 0.1
SOLE = 0.06
RANGE = {(k, i): (lo, hi) for k, i, lo, hi in F.PARAMS}
RANGE.update({("pelvis", 1): (-90, 90), ("pelvis", 2): (-80, 80)})
for _s in "rl":
    RANGE.update({(f"{_s}_hand", 0): (-80, 80), (f"{_s}_hand", 1): (-80, 80), (f"{_s}_wrist", None): (0, 180),
                  (f"{_s}_foot", None): (-80, 80), (f"{_s}_hip", 0): (-60, 150), (f"{_s}_hip", 1): (-30, 150),
                  (f"{_s}_hip", 2): (-90, 90), (f"{_s}_knee", None): (0, 160), (f"{_s}_elbow", None): (0, 160)})


def landmarks():
    """His nose, left and right ear, knuckles, soles, toes and heels: (bone, point in that bone's rest frame), read off
    his mesh standing."""
    body = bpy.data.objects["Mario Mesh"]
    rig = bpy.data.objects["Mario"]
    names = {g.index: g.name for g in body.vertex_groups}
    mats = [m.name if m else "" for m in body.data.materials]
    by_vert_mat = {}
    for poly in body.data.polygons:
        for i in poly.vertices:
            by_vert_mat.setdefault(i, set()).add(mats[poly.material_index])
    pos, world = S.fk(A.full({**A.STAND, "r_wrist": 0, "l_wrist": 0}))

    def group(v):
        best = max(v.groups, key=lambda g: g.weight, default=None)
        return names[best.group].replace(" DL", "").replace(" Color", "") if best else None

    pts = {}
    for v in body.data.vertices:
        b = group(v)
        if b not in rig.data.bones:
            continue
        rest = rig.data.bones[b]
        local = (rig.matrix_world @ rest.matrix_local).inverted() @ (body.matrix_world @ v.co)
        stand = pos[b] + world[b] @ local
        pts.setdefault(b, []).append((local, S.frame(stand), by_vert_mat.get(v.index, set())))
    out = {}

    def mean(rows):
        return sum((r[0] for r in rows), Vector()) / len(rows)
    face = [r for r in pts["Head"] if "Open Eyes (SKIN)" in r[2]]
    front = max(r[1].z for r in face)
    out["nose"] = ("Head", mean([r for r in face if r[1].z > front - 0.03]))
    for s, name in SIDES.items():
        ear = [r for r in pts["Head"] if "BT3 Ear" in r[2] and (r[1].x > 0) == (s == "l")]
        out[f"{s}_ear"] = ("Head", mean(ear))
        hand = pts[f"{name} Hand"]
        far = sorted(hand, key=lambda r: r[0].length)[-max(1, len(hand) // 4):]
        out[f"{s}_hand"] = (f"{name} Hand", mean(far))
        shoe = [r for r in pts[f"{name} Shoe"] if "Shoe" in r[2]] or pts[f"{name} Shoe"]
        low = min(r[1].y for r in shoe)
        sole = [r for r in shoe if r[1].y < low + 0.03]
        out[f"{s}_sole"] = (f"{name} Shoe", mean(sole))
        ahead = max(r[1].z for r in sole)
        behind = min(r[1].z for r in sole)
        out[f"{s}_toe"] = (f"{name} Shoe", mean([r for r in sole if r[1].z > ahead - 0.03]))
        out[f"{s}_heel"] = (f"{name} Shoe", mean([r for r in sole if r[1].z < behind + 0.03]))
    out["head"] = ("Head", Vector((0.3, 0.17, 0)))
    return out


def shoe_axis(path, ankle, sole, knee):
    """The reference's kicking shoe: the direction from its heel to its toe, measured from its surface. Its points past
    the ankle along the shin, their long axis across the sole, signed toward the broader end."""
    ref, _ = R.reference_points(path, count=20000)
    shin = (ankle - knee).normalized()
    pts = [q for q in ref if (q - ankle).dot(shin) > -0.02 and (q - sole).length < 0.4]
    mid = sum(pts, Vector()) / len(pts)
    m = Matrix(((0.0,) * 3,) * 3)
    for q in pts:
        d = q - mid
        for i in range(3):
            for j in range(3):
                m[i][j] += d[i] * d[j]
    axis = Vector((1, 0, 0)) if abs(shin.x) < 0.9 else Vector((0, 1, 0))
    for _ in range(60):
        axis = m @ axis
        axis -= shin * axis.dot(shin)
        axis.normalize()

    def width(end):
        ring = [q for q in pts if (q - mid).dot(axis) * end > 0.12]
        if not ring:
            return 0.0
        c = sum(ring, Vector()) / len(ring)
        return sum(((q - c) - axis * (q - c).dot(axis)).length for q in ring) / len(ring)
    return axis if width(1) >= width(-1) else -axis


def part_points(bone, skip=("Hair",)):
    """His mesh's points on one bone, in its rest frame, leaving out these materials (his hair isn't the figure's)."""
    body = bpy.data.objects["Mario Mesh"]
    rig = bpy.data.objects["Mario"]
    names = {g.index: g.name for g in body.vertex_groups}
    mats = [m.name if m else "" for m in body.data.materials]
    skipped = {i for poly in body.data.polygons if mats[poly.material_index] in skip for i in poly.vertices}
    to_bone = (rig.matrix_world @ rig.data.bones[bone].matrix_local).inverted()
    out = []
    for v in body.data.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        if best and names[best.group].replace(" DL", "").replace(" Color", "") == bone and v.index not in skipped:
            out.append(to_bone @ (body.matrix_world @ v.co))
    return out


def match_shape(local, start_rot, anchor, tree, tries=12, seed=3):
    """How the reference holds a part of him: his part's points (in its bone's frame) matched onto the reference's
    surface near anchor, turned, moved and scaled freely (the figure's shoe is bigger than his), from several starting
    turns. Returns the part's turn in the reference's space and the mean miss."""
    import numpy as np
    P = np.array([tuple(v) for v in local])
    rng = random.Random(seed)
    best = None
    for k in range(tries):
        rot = np.array(start_rot)
        if k:
            axis = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized()
            rot = np.array(Matrix.Rotation(rng.uniform(0.3, 2.6), 3, axis)) @ rot
        scale, t = 1.0, np.array(tuple(anchor)) - (P @ np.array(start_rot).T).mean(0)
        for _ in range(40):
            X = (P @ rot.T) * scale + t
            near = [tree.find(Vector(x)) for x in X]
            Y = np.array([tuple(n[0]) for n in near])
            d = np.array([n[2] for n in near])
            keep = d < max(np.median(d) * 2.0, 1e-4)
            A_, B_ = P[keep], Y[keep]
            ma, mb = A_.mean(0), B_.mean(0)
            H = (A_ - ma).T @ (B_ - mb)
            U, Sg, Vt = np.linalg.svd(H)
            D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
            rot = Vt.T @ D @ U.T
            scale = float((Sg * np.diag(D)).sum() / ((A_ - ma) ** 2).sum())
            t = mb - scale * (rot @ ma)
        miss = float(np.mean([tree.find(Vector(x))[2] for x in (P @ rot.T) * scale + t]))
        if best is None or miss < best[1]:
            best = (Matrix(rot.tolist()), miss)
    return best


def copy(path, joints_path):
    data = json.load(open(joints_path, encoding="utf8"))
    J = {k: Vector(v) for k, v in data["joints"].items()}
    J["hips"] = (J["r_hip"] + J["l_hip"]) / 2
    J["neck"] = (J["r_shoulder"] + J["l_shoulder"]) / 2
    toe_axis = {}
    for s in "rl":
        if f"{s}_hand" not in J:
            J[f"{s}_hand"] = J[f"{s}_wrist"] + (J[f"{s}_wrist"] - J[f"{s}_elbow"]).normalized() * HAND
        if f"{s}_heel" in J and f"{s}_toe" in J:
            J.setdefault(f"{s}_sole", (J[f"{s}_heel"] + J[f"{s}_toe"]) / 2)
            toe_axis[s] = (J[f"{s}_toe"] - J[f"{s}_heel"]).normalized()
        else:
            if f"{s}_toe" in J:
                J.setdefault(f"{s}_sole", J.pop(f"{s}_toe"))
            J.setdefault(f"{s}_sole", J[f"{s}_ankle"] + (J[f"{s}_ankle"] - J[f"{s}_knee"]).normalized() * SOLE)
            toe_axis[s] = shoe_axis(path, J[f"{s}_ankle"], J[f"{s}_sole"], J[f"{s}_knee"])
    spine = (J["neck"] - J["hips"]).normalized()
    T = {}
    for a, b in (("r_hip", "l_hip"), ("r_shoulder", "l_shoulder")):
        v = J[b] - J[a]
        T[(a, b)] = (v - spine * v.dot(spine)).normalized()
    ref, _ = R.reference_points(path, count=20000)
    tree = kdtree.KDTree(len(ref))
    for i, q in enumerate(ref):
        tree.insert(q, i)
    tree.balance()
    marks = landmarks()
    base = A.full({**A.STAND, "r_wrist": 0, "l_wrist": 0})
    state = {"pose": dict(base), "yaw": 0.0}
    put_state = {"pose": dict(base), "yaw": 0.0}
    bone_of = dict(R.JOINTS)

    def where(p, yaw):
        pos, world = S.fk(A.full(p))
        rot = Matrix.Rotation(math.radians(yaw), 3, "Z")
        mine = {k: rot @ pos[b] for k, b in bone_of.items()}
        for k, (b, local) in marks.items():
            mine[k] = rot @ (pos[b] + world[b] @ local)
        mine["hips"] = (mine["r_hip"] + mine["l_hip"]) / 2
        mine["neck"] = (mine["r_shoulder"] + mine["l_shoulder"]) / 2
        return mine

    def off(m, a, b, target=None):
        d = (m[b] - m[a]).normalized()
        e = target if target is not None else T.get((a, b), (J[b] - J[a]).normalized())
        return 1 - d.dot(e)

    def solve(keys, segments, extra=None, turn=None):
        """Turn only these joints (pose key and index, or "yaw") until these segments point along the reference's."""
        def put(x):
            p, yaw = dict(state["pose"]), state["yaw"]
            for (k, i), v in zip(keys, x):
                if k == "yaw":
                    yaw = v
                elif i is None:
                    p[k] = v
                else:
                    t = list(p[k])
                    t[i] = v
                    p[k] = tuple(t)
            return p, yaw

        def cost(x):
            p, yaw = put(x)
            put_state["pose"], put_state["yaw"] = p, yaw
            m = where(p, yaw)
            c = sum(w * off(m, a, b) for a, b, w in segments)
            if turn:
                bone, want = turn
                got = turn_of(bone, p, yaw)
                c += sum(1 - (got @ Vector(e)).dot(want @ Vector(e)) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
            return c + (extra(m) if extra else 0.0)
        x0 = [state["yaw"] if k == "yaw" else (state["pose"][k] if i is None else state["pose"][k][i]) for k, i in keys]
        lim = [(-360, 360) if k == "yaw" else RANGE.get((k, i), (-90, 90)) for k, i in keys]
        x0 = [max(lo, min(hi, v)) for v, (lo, hi) in zip(x0, lim)]
        rng = random.Random(len(keys))
        starts = [x0] + [[rng.uniform(lo, hi) for lo, hi in lim] for _ in range(40)]
        best = min((S.descend(cost, x, lim, starts=1, spread=0) for x in starts), key=cost)
        state["pose"], state["yaw"] = put(best)
        return cost(best)

    solve([("yaw", None), ("pelvis", 0), ("pelvis", 1), ("pelvis", 2)], [("r_hip", "l_hip", 1), ("hips", "neck", 1)])
    solve([("torso", 0), ("torso", 1), ("torso", 2)], [("r_shoulder", "l_shoulder", 1), ("hips", "neck", 1)])
    def turn_of(bone, pose, yaw):
        pos, world = S.fk(A.full(pose))
        return Matrix.Rotation(math.radians(yaw), 3, "Z") @ world[bone]

    shapes = {}
    face_anchor = (J["nose"] + J["l_ear"]) / 2
    want_head, miss = match_shape(part_points("Head", skip=("Hair", "Head Line")), turn_of("Head", state["pose"], state["yaw"]), face_anchor, tree)
    shapes["Head"] = round(miss, 4)
    wants = {"Head": want_head}
    face = (J["nose"] - J["head"]).normalized()
    up = (J["head"] - J["neck"]).normalized() if data.get("face_by_hand") else want_head @ Vector((0, 0, 1))

    def looks(m):
        got = turn_of("Head", put_state["pose"], put_state["yaw"])
        return 2 * (1 - (got @ Vector((0, 1, 0))).dot(face)) + 0.5 * (1 - (got @ Vector((0, 0, 1))).dot(up))
    solve([("head", 0), ("head", 1), ("head", 2)], [], extra=looks)
    wants["Head"] = None
    for s in "rl":
        solve([(f"{s}_arm", 0), (f"{s}_arm", 1), (f"{s}_arm", 2), (f"{s}_elbow", None)],
              [(f"{s}_shoulder", f"{s}_elbow", 1), (f"{s}_elbow", f"{s}_wrist", 1)])
        solve([(f"{s}_hand", 0), (f"{s}_hand", 1), (f"{s}_wrist", None)], [(f"{s}_wrist", f"{s}_hand", 1)])
        legs = [(f"{s}_hip", 0), (f"{s}_hip", 1), (f"{s}_hip", 2), (f"{s}_knee", None), (f"{s}_foot", None)]
        bones = [(f"{s}_hip", f"{s}_knee", 1), (f"{s}_knee", f"{s}_ankle", 1)]
        solve(legs, bones + [(f"{s}_ankle", f"{s}_sole", 1)], extra=lambda m, s=s: off(m, f"{s}_heel", f"{s}_toe", toe_axis[s]))
        shoe = f"{SIDES[s]} Shoe"
        want_shoe, miss = match_shape(part_points(shoe, skip=()), turn_of(shoe, state["pose"], state["yaw"]), J[f"{s}_sole"] * 0.5 + J[f"{s}_ankle"] * 0.5, tree)
        shapes[shoe] = round(miss, 4)
        wants[shoe] = want_shoe
        solve(legs, [(a, b, 3) for a, b, _ in bones], turn=(shoe, want_shoe))
    m = where(state["pose"], state["yaw"])
    report = {}
    for a, b in (("r_hip", "l_hip"), ("hips", "neck"), ("r_shoulder", "l_shoulder"), ("head", "nose"), ("head", "l_ear"),
                 ("neck", "head"), ("r_shoulder", "r_elbow"), ("r_elbow", "r_wrist"), ("r_wrist", "r_hand"),
                 ("l_shoulder", "l_elbow"), ("l_elbow", "l_wrist"), ("l_wrist", "l_hand"), ("r_hip", "r_knee"),
                 ("r_knee", "r_ankle"), ("r_ankle", "r_sole"), ("l_hip", "l_knee"), ("l_knee", "l_ankle"), ("l_ankle", "l_sole")):
        report[f"{a}-{b}"] = round(math.degrees(math.acos(max(-1, min(1, 1 - off(m, a, b))))), 1)
    for s in "rl":
        report[f"{s}_heel-{s}_toe"] = round(math.degrees(math.acos(max(-1, min(1, 1 - off(m, f"{s}_heel", f"{s}_toe", toe_axis[s]))))), 1)
    got = turn_of("Head", state["pose"], state["yaw"])
    report["face"] = round(math.degrees(math.acos(max(-1, min(1, (got @ Vector((0, 1, 0))).dot(face))))), 1)
    for bone, want in wants.items():
        if want is None:
            continue
        got = turn_of(bone, state["pose"], state["yaw"])
        report[f"{bone} turn"] = round(max(math.degrees(math.acos(max(-1, min(1, (got @ Vector(e)).dot(want @ Vector(e))))))
                                           for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))), 1)
    keys = [k for k in R.JOINTS if k in J]
    mc = sum((m[k] for k in keys), Vector()) / len(keys)
    jc = sum((J[k] for k in keys), Vector()) / len(keys)
    s = sum((J[k] - jc).length for k in keys) / sum((m[k] - mc).length for k in keys)
    pos, world = S.fk(A.full(state["pose"]))
    his = [pos[b] + world[b] @ v for b, v in R.his_points()]
    floor = min(q.z for q in his)
    rot = Matrix.Rotation(math.radians(state["yaw"]), 3, "Z")
    t = jc - (mc - rot @ Vector((0, 0, floor))) * s
    pose = {k: ([round(u, 1) for u in v] if isinstance(v, tuple) else round(v, 1)) for k, v in state["pose"].items()
            if k in {q[0] for q in F.PARAMS} or k.endswith(("_foot", "_hand", "_wrist"))}
    return {"cost": 0, "camera": [round(-state["yaw"], 1), 0, 0], "place": [round(state["yaw"], 3), round(s, 3), *(round(v, 3) for v in t)],
            "floor": round(floor, 4), "pose": pose, "each_bone_off_deg": report, "shape_miss": shapes, "limits": {}, "facts": []}


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    reading = copy(args[0], args[1])
    json.dump({"reference": args[0], "image": args[0], "shift": [0, 0, 0], "mirror_depth": False, "readings": [reading],
               "facts_from": "the reference's joints, copied bone by bone"}, open(args[2], "w", encoding="utf8"), indent=1)
    worst = sorted(reading["each_bone_off_deg"].items(), key=lambda kv: -kv[1])
    print("pose_copy: each bone off the reference's, worst first:", ", ".join(f"{k} {v}" for k, v in worst))
    print("pose_copy: his head and shoes matched onto the figure's surface, mean miss:", reading["shape_miss"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
