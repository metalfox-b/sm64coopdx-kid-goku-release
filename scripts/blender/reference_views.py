"""His posed model beside the 3D reference it was fitted to, from the same cameras (runs inside Blender on the kept
model, private/build/goku.blend). The reference is only drawn here, grey, placed on him by the fit; it never joins
his model.

Usage:
  blender -b private/build/goku.blend --python scripts/blender/reference_views.py -- FIT.json N OUT_DIR [FACE]

FACE is a passed face's name (relaxed by default) or a draft's painted texture (goku_face_NAME.ci4.png).

Writes OUT_DIR/pairs.png (each view: him, then the reference) and OUT_DIR/turn/ (both turning, for a video).
"""
from __future__ import annotations

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
import pose_from_reference as R
import pose_preview as PV
import pose_solve as S


def shaded_grey():
    """Grey lit by a fixed key and fill light, with contact shadow and darkened silhouette edges, all in its own
    emission so the scene's lights don't matter: a flat grey left only an outline and lost every fold and overlap the
    reference's depth is read from."""
    mat = bpy.data.materials.new("reference grey")
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    n, link = t.nodes.new, t.links.new
    geo = n("ShaderNodeNewGeometry")

    def lit(direction, amount):
        light = n("ShaderNodeCombineXYZ")
        for i, v in enumerate(Vector(direction).normalized()):
            light.inputs[i].default_value = v
        dot = n("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        link(geo.outputs["Normal"], dot.inputs[0])
        link(light.outputs[0], dot.inputs[1])
        clamp = n("ShaderNodeMath")
        clamp.operation = "MULTIPLY"
        clamp.use_clamp = True
        link(dot.outputs["Value"], clamp.inputs[0])
        clamp.inputs[1].default_value = amount
        return clamp.outputs[0]
    key, fill = lit((-0.5, -0.7, 0.8), 0.75), lit((0.7, 0.6, 0.1), 0.25)
    add = n("ShaderNodeMath")
    add.operation = "ADD"
    link(key, add.inputs[0])
    link(fill, add.inputs[1])
    base = n("ShaderNodeMath")
    base.operation = "ADD"
    link(add.outputs[0], base.inputs[0])
    base.inputs[1].default_value = 0.18
    ao = n("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.15
    edge = n("ShaderNodeLayerWeight")
    edge.inputs["Blend"].default_value = 0.35
    rim = n("ShaderNodeMath")
    rim.operation = "SUBTRACT"
    rim.inputs[0].default_value = 1.0
    link(edge.outputs["Facing"], rim.inputs[1])
    shade = n("ShaderNodeMath")
    shade.operation = "MULTIPLY"
    link(base.outputs[0], shade.inputs[0])
    link(ao.outputs["AO"], shade.inputs[1])
    shade2 = n("ShaderNodeMath")
    shade2.operation = "MULTIPLY"
    link(shade.outputs[0], shade2.inputs[0])
    link(rim.outputs[0], shade2.inputs[1])
    tint = n("ShaderNodeMix")
    tint.data_type = "RGBA"
    link(shade2.outputs[0], tint.inputs["Factor"])
    tint.inputs["A"].default_value = (0.08, 0.08, 0.1, 1)
    tint.inputs["B"].default_value = (0.92, 0.93, 0.96, 1)
    em = n("ShaderNodeEmission")
    link(tint.outputs["Result"], em.inputs[0])
    out = n("ShaderNodeOutputMaterial")
    link(em.outputs[0], out.inputs[0])
    return mat


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    fit = json.load(open(args[0], encoding="utf8"))
    reading = fit["readings"][int(args[1]) - 1]
    out = args[2]
    pose = anims.full({**anims.STAND, "r_wrist": 0, "l_wrist": 0, **{k: tuple(v) if isinstance(v, list) else v for k, v in reading["pose"].items()}})
    face = args[3] if len(args) > 3 else "relaxed"
    if face.endswith(".png"):
        bpy.data.materials["Open Eyes (SKIN)"].f3d_mat.tex0.tex = bpy.data.images.load(os.path.abspath(face))
    elif PV.wear(face):
        raise SystemExit(PV.wear(face))
    goku.pose_rig(pose)
    his = PV.shown("fist")
    bpy.context.view_layer.update()
    goku.preview_materials(his)
    rig = bpy.data.objects["Mario"]
    pos, _ = S.fk(pose)
    offset = rig.matrix_world @ rig.pose.bones["Butt"].head - pos["Butt"]
    ref, _ = R.reference_space(fit["reference"], fit.get("mirror_depth", False))
    yaw, s, tx, ty, tz = reading["place"]
    into_his = (Matrix.Translation(offset + Vector((0, 0, reading["floor"]))) @ Matrix.Rotation(math.radians(-yaw), 4, "Z")
                @ Matrix.Scale(1 / s, 4) @ Matrix.Translation(-Vector((tx, ty, tz))))
    grey = shaded_grey()
    for o in ref:
        if o.parent is None:
            o.matrix_world = into_his @ o.matrix_world
        if o.type == "MESH":
            o.data.materials.clear()
            o.data.materials.append(grey)
    bpy.context.view_layer.update()
    lo, hi = PV.bounds(his)
    mid = (lo + hi) / 2
    size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) * 1.6
    far = size * 3
    views = [("still", -yaw, 0.0), ("front", 0, 0.15), ("three-quarter", 45, 0.15), ("side", 90, 0.1), ("back", 180, 0.15), ("above", 0, 3.0)]
    os.makedirs(out, exist_ok=True)

    def shoot(prefix, cams):
        return goku.render_views(out, cams, prefix=prefix, size=(640, 640), look=tuple(mid), scale=size)
    cams = [(n, (mid.x + far * math.sin(math.radians(a)), mid.y - far * math.cos(math.radians(a)), mid.z + far * h)) for n, a, h in views]
    for o in ref:
        o.hide_render = True
    his_paths = shoot("his", cams)
    for o in his:
        o.hide_render = True
    for o in ref:
        o.hide_render = o.type != "MESH"
    ref_paths = shoot("ref", cams)
    for o in his:
        o.hide_render = False
    ring = [(f"t{i:02d}", (mid.x + far * math.sin(math.radians(i * 15)), mid.y - far * math.cos(math.radians(i * 15)), mid.z + far * 0.15)) for i in range(24)]
    os.makedirs(os.path.join(out, "turn"), exist_ok=True)
    goku.render_views(os.path.join(out, "turn"), ring, prefix="both", size=(640, 640), look=tuple(mid), scale=size)
    def flat(path):
        a = PV.pixels(path)
        a[..., :3] = a[..., :3] * a[..., 3:4] + np.array([0.13, 0.13, 0.15]) * (1 - a[..., 3:4])
        a[..., 3] = 1
        return a
    his_row = np.concatenate([flat(p) for p in his_paths], axis=1)
    ref_row = np.concatenate([flat(p) for p in ref_paths], axis=1)
    sheet = np.concatenate([ref_row, his_row], axis=0)
    img = bpy.data.images.new("pairs", sheet.shape[1], sheet.shape[0])
    img.pixels = sheet.ravel()
    img.filepath_raw = os.path.join(out, "pairs.png")
    img.file_format = "PNG"
    img.save()
    print("reference views:", os.path.join(out, "pairs.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
