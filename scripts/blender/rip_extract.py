"""Read Tenkaichi 3's Kid Goku rip (glTF) in its bind pose into plain data for bt3.py (runs in a clean Blender).

Usage:
  blender -b --factory-startup --python scripts/blender/rip_extract.py -- RIP.gltf OUT.json

OUT.json: joints (glTF node -> position), vertices (bind pose) with their strongest bone, triangles with UVs and a
material index, and each material's texture file. Everything stays under private/.
"""
import json
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=args[0])
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Mesh"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()
ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
me = ev.to_mesh()
me.calc_loop_triangles()
gi = {g.index: g.name for g in mesh.vertex_groups}
verts = []
for v0, v in zip(mesh.data.vertices, me.vertices):
    g = max(v0.groups, key=lambda g: g.weight) if v0.groups else None
    verts.append([list(ev.matrix_world @ v.co), int(gi[g.group].split("_")[1]) if g else -1])
uv = me.uv_layers.active.data
tris = [[list(t.vertices), [list(uv[li].uv) for li in t.loops], t.material_index] for t in me.loop_triangles]
textures = []
for m in mesh.data.materials:
    img = next((n.image for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
    textures.append(bpy.path.abspath(img.filepath) if img else None)
joints = {b.name.split("_")[1]: list(arm.matrix_world @ b.head_local) for b in arm.data.bones}
json.dump({"joints": joints, "verts": verts, "tris": tris, "textures": textures}, open(args[1], "w"))
print(f"extracted {len(verts)} verts, {len(tris)} tris, {len(textures)} textures")
