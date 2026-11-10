"""The 3D reference (a Meshy figure) drawn lit from many known cameras, for finding its joints
(scripts/reference_joints.py). Runs inside Blender. The reference is only drawn here; it never joins his model.

Usage:
  blender -b --factory-startup --python scripts/blender/reference_renders.py -- REFERENCE.glb OUT_DIR [--mirror-depth]

Writes OUT_DIR/view-NN.png and OUT_DIR/cameras.json: each camera's place, its right and up axes, how wide it sees and
the image size, in the reference's space (lowest point on the floor, centered: pose_from_reference.reference_space).
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_from_reference as R
from reference_views import shaded_grey

SIZE = 768


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    path, out = args[0], args[1]
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    objs, _ = R.reference_space(path, "--mirror-depth" in args)
    grey = shaded_grey()
    for o in objs:
        if o.type == "MESH":
            o.data.materials.clear()
            o.data.materials.append(grey)
    pts = [o.matrix_world @ v.co for o in objs if o.type == "MESH" for v in o.data.vertices]
    hi = Vector([max(p[k] for p in pts) for k in range(3)])
    lo = Vector([min(p[k] for p in pts) for k in range(3)])
    mid = (lo + hi) / 2
    width = 2.1 * max((p - mid).length for p in pts)
    far = 10.0
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.render.film_transparent = False
    scene.world = scene.world or bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.03, 0.03, 0.035, 1)
    cam = bpy.data.objects.new("RefCam", bpy.data.cameras.new("RefCam"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = width
    scene.camera = cam
    rings = [(a, 10) for a in range(0, 360, 30)] + [(a, 45) for a in range(0, 360, 60)] + [(a, -20) for a in range(0, 360, 90)]
    cams = []
    os.makedirs(out, exist_ok=True)
    for i, (a, up) in enumerate(rings):
        d = Vector((math.sin(math.radians(a)) * math.cos(math.radians(up)), -math.cos(math.radians(a)) * math.cos(math.radians(up)),
                    math.sin(math.radians(up))))
        cam.location = mid + d * far
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        m = cam.matrix_world.to_3x3()
        name = f"view-{i:02d}.png"
        scene.render.filepath = os.path.join(out, name)
        bpy.ops.render.render(write_still=True)
        cams.append({"image": name, "turn": a, "up": up, "place": list(cam.location), "right": list(m.col[0]),
                     "upward": list(m.col[1]), "width": width, "size": SIZE})
    json.dump({"reference": path, "mirror_depth": "--mirror-depth" in args, "cameras": cams},
              open(os.path.join(out, "cameras.json"), "w", encoding="utf8"), indent=1)
    print("reference renders:", len(cams), "in", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
