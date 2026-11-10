"""Make a copy of the character template that Blender 5 opens (runs inside Blender, --factory-startup).

Usage: blender -b --factory-startup --python scripts/blender/convert_template.py -- TEMPLATE.blend OUT.blend

The template was saved by Blender 4.1 with a link to Fast64's material library on its author's PC. Blender 5.2 and 5.3 crash
opening it (read_libraries frees a property twice), with the link repointed too, but they append its scene cleanly.
"""
import sys

import bpy

src_path, out_path = sys.argv[sys.argv.index("--") + 1:][:2]
with bpy.data.libraries.load(src_path, link=False) as (src, dst):
    dst.scenes = src.scenes
blank = bpy.data.scenes["Scene"]
template = next(s for s in bpy.data.scenes if s is not blank)
for window in bpy.context.window_manager.windows:
    window.scene = template
for o in list(blank.objects):
    if o.name not in template.objects:
        bpy.data.objects.remove(o)
bpy.data.scenes.remove(blank)
template.name = "Scene"
bpy.ops.wm.save_as_mainfile(filepath=out_path, relative_remap=False)
print("converted template:", len(bpy.data.objects), "objects")
