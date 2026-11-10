"""One moment of a motion drawn from three sides, from the model the last build kept (runs inside Blender).

Usage (scripts/pose-preview.mjs runs it):
  blender -b private/build/goku.blend --python scripts/blender/pose_preview.py -- MOTION T OUT.png HAND FACE [FRAME]

MOTION is a name in anims.S, T its time 0..1. HAND is the right hand's shape: fist, pole (the straight pole in his
grip) or bent (the pole bending in a fast swing). FACE is one of the faces Metal Fox passed (art/faces/passed.json), worn
as the build painted it; any other face, or a painted texture that isn't what he passed, stops the preview, which
never makes a face of its own. FRAME, a picture, goes on the end of the sheet.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anims
import goku

HANDS = {"fist": None, "pole": "Right Hand Wing Cap Mesh", "bent": "Right Hand Cap Mesh"}
HEIGHT = 640
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def wear(face):
    """Paints his face with a passed face as the build painted it (the kept model's head has the unpainted one)."""
    passed = json.load(open(os.path.join(ROOT, "art", "faces", "passed.json"), encoding="utf8"))["faces"]
    if face not in passed:
        return f"{face} isn't a face Metal Fox passed: {', '.join(passed)}"
    if passed[face]["head"] is not None:
        return f"{face} has a head of its own, which this preview doesn't draw: film it in game"
    path = os.path.join(ROOT, "mod", "kid-goku", "actors", "goku", f"goku_face_{face}.ci4.png")
    if not os.path.exists(path):
        return f"no painted {face}: run node scripts/build.mjs"
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != passed[face]["texture"]:
        return f"the painted {face} isn't what Metal Fox passed: node scripts/check-faces.mjs says what changed"
    bpy.data.materials["Open Eyes (SKIN)"].f3d_mat.tex0.tex = bpy.data.images.load(path, check_existing=True)
    return None


def shown(hand):
    """His body, with the right hand's switch shape in place of the fist when he holds something."""
    body = bpy.data.objects["Mario Mesh"]
    keep = [body]
    if HANDS[hand]:
        shape = bpy.data.objects[HANDS[hand]]
        keep.append(shape)
        rig, arm = bpy.data.objects["Mario"], shape.parent
        bpy.context.view_layer.update()
        rest = rig.data.bones["Right Hand"]
        moves = rig.matrix_world @ rig.pose.bones["Right Hand"].matrix @ rest.matrix_local.inverted() @ rig.matrix_world.inverted()
        arm.matrix_world = moves @ Matrix.Translation(rig.matrix_world @ rest.head_local)
        group = body.vertex_groups.get("Right Hand DL")
        if group is not None:
            mod = body.modifiers.new("hide fist", "MASK")
            mod.vertex_group, mod.invert_vertex_group = group.name, True
    for o in bpy.data.objects:
        o.hide_render = o not in keep
    return keep


def bounds(objects):
    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objects:
        ev = o.evaluated_get(deps)
        mesh = ev.to_mesh()
        for v in mesh.vertices:
            w = ev.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
    return lo, hi


def pixels(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return a


def fit(a, height):
    """Nearest-neighbor resize to this height."""
    h, w = a.shape[:2]
    width = max(1, round(w * height / h))
    ys = (np.arange(height) * h / height).astype(int)
    xs = (np.arange(width) * w / width).astype(int)
    return a[ys][:, xs]


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    motion, t, out, hand, face = args[0], float(args[1]), args[2], args[3], args[4]
    frame = args[5] if len(args) > 5 else None
    still, warn = None, []
    if motion.endswith(".json"):
        fitted = json.load(open(motion, encoding="utf8"))
        reading = fitted["readings"][int(t) - 1]
        broken = [f"{name} ({why})" for name, ok, why in reading.get("facts", []) if not ok]
        if broken and not os.environ.get("POSE_PREVIEW_SHOW_FAILING"):
            print(f"pose_preview: reading {int(t)} breaks: {'; '.join(broken)} (--show-failing to draw it anyway)")
            return 1
        warn = [f"breaks {b}" for b in broken] + [f"guessed: {g}" for g in fitted.get("unconfirmed", [])]
        pose = anims.full({**anims.STAND, "r_wrist": 0, "l_wrist": 0, **{k: tuple(v) if isinstance(v, list) else v for k, v in reading["pose"].items()}})
        import pose_fit
        toward = pose_fit.camera(*reading["camera"]).transposed() @ Vector((0, 0, 1))
        still = Vector((toward.x, -toward.z, toward.y))
    elif motion not in anims.S:
        print(f"pose_preview: no motion {motion}")
        return 1
    else:
        pose = anims.full(anims.S[motion](t))
    refused = wear(face)
    if refused:
        print(f"pose_preview: {refused}")
        return 1
    goku.pose_rig(pose)
    objects = shown(hand)
    bpy.context.view_layer.update()
    lo, hi = bounds(objects)
    mid = (lo + hi) / 2
    size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) * 1.15
    goku.preview_materials(objects)
    far = size * 3
    views = (("front", (mid.x, mid.y - far, mid.z)), ("side", (mid.x - far, mid.y, mid.z)), ("back", (mid.x, mid.y + far, mid.z)))
    if still is not None:
        views = (("still", tuple(mid + still * far)),) + views
    work = os.path.join(os.path.dirname(os.path.abspath(out)), ".pose-preview")
    os.makedirs(work, exist_ok=True)
    paths = goku.render_views(work, views, prefix="view", size=(HEIGHT, HEIGHT), look=tuple(mid), scale=size)
    panels = [pixels(p) for p in paths]
    if frame:
        panels.append(fit(pixels(frame), HEIGHT))
    gap = np.zeros((HEIGHT, 12, 4), dtype=np.float32)
    gap[..., 3] = 1
    row = []
    for i, p in enumerate(panels):
        p = p.copy()
        bg = np.array([0.13, 0.13, 0.15, 1], dtype=np.float32)
        p[..., :3] = p[..., :3] * p[..., 3:4] + bg[:3] * (1 - p[..., 3:4])
        p[..., 3] = 1
        row += [p] + ([gap] if i < len(panels) - 1 else [])
    sheet = np.concatenate(row, axis=1)
    if warn:
        sheet[-28:, :, :3] = (0.8, 0.1, 0.1)
        print("pose stamp: red, " + "; ".join(warn))
    turn = os.environ.get("POSE_PREVIEW_TURNTABLE")
    if turn:
        ring = [(f"t{i:02d}", (mid.x + far * math.sin(math.radians(i * 15)), mid.y - far * math.cos(math.radians(i * 15)), mid.z + far * 0.25)) for i in range(24)]
        os.makedirs(turn, exist_ok=True)
        goku.render_views(turn, ring + [("top", (mid.x, mid.y - 0.01, mid.z + far))], prefix="v", size=(480, 480), look=tuple(mid), scale=size * 1.05)
    img = bpy.data.images.new("pose preview", sheet.shape[1], sheet.shape[0])
    img.pixels = sheet.ravel()
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    print(f"pose preview: {motion} at {t} ({hand}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
