"""Read Budokai 3's Kid Goku rip (OBJ) into plain data for b3.py (runs in a clean Blender).

Usage:
  blender -b --factory-startup --python scripts/blender/obj_extract.py -- RIP.obj OUT.json

OUT.json: vertices (T-pose; x his left, y back, z up), triangles with UVs and a material index, and each material's
name and texture file. Everything stays under private/.
"""
import json
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=args[0])
obj = next(o for o in bpy.data.objects if o.type == "MESH")
me = obj.data
me.calc_loop_triangles()
verts = [list(obj.matrix_world @ v.co) for v in me.vertices]
uv = me.uv_layers.active.data
tris = [[list(t.vertices), [list(uv[li].uv) for li in t.loops], t.material_index] for t in me.loop_triangles]
mats = []
for m in me.materials:
    img = next((n.image for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
    mats.append({"name": m.name, "texture": bpy.path.abspath(img.filepath) if img else None})
json.dump({"verts": verts, "tris": tris, "materials": mats}, open(args[1], "w"))
print(f"extracted {len(verts)} verts, {len(tris)} tris, {len(mats)} materials")
