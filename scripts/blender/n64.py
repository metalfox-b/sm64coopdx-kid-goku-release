"""Helpers the Blender build scripts share: Fast64 materials, vertex colors and the actor export.

Fast64 maps Blender +Z to SM64 +Y and Blender -Y to SM64 +Z (forward), at `SCALE` SM64 units per Blender unit.
"""
from __future__ import annotations

import os

import bmesh
import bpy
from mathutils import Matrix, Vector

SCALE = 100.0

LAYER_OPAQUE = "1"
LAYER_TRANSPARENT = "5"


def hex_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def f3d_material(obj, name: str, layer: str = LAYER_OPAQUE, lit: bool = False, alpha: bool = False,
                 cull: bool = True):
    """A vertex-colored, unlit Fast64 material (SHADE), or lit when the player's palette lights it."""
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat

    mat = createF3DMat(obj, "Shaded Solid")
    mat.name = name
    f = mat.f3d_mat
    f.rdp_settings.g_lighting = lit
    f.rdp_settings.g_cull_back = cull
    f.draw_layer.sm64 = layer
    if alpha:
        f.combiner1.D_alpha = "SHADE"
    return mat


def paint(obj, color_of):
    """Write the face-corner "Col" layer Fast64 exports: color_of(world_co, normal, material_index) -> (r, g, b, a)."""
    me = obj.data
    col = me.color_attributes.get("Col") or me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    alpha = me.color_attributes.get("Alpha") or me.color_attributes.new("Alpha", "BYTE_COLOR", "CORNER")
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            r, g, b, a = color_of(obj.matrix_world @ v.co, v.normal, poly.material_index)
            col.data[li].color_srgb = (r, g, b, 1.0)
            alpha.data[li].color_srgb = (a, a, a, 1.0)


def mesh_object(name: str, bm: bmesh.types.BMesh):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def tris(obj) -> int:
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def setup_scene():
    bpy.context.scene.gameEditorMode = "SM64"
    bpy.context.scene.f3d_type = "F3D"
    sm64 = bpy.context.scene.fast64.sm64
    sm64.blender_to_sm64_scale = SCALE
    sm64.export_type = "C"
    bpy.context.scene.saveTextures = True


def export_object(obj, name: str, out_dir: str) -> str:
    """Export one mesh as a DynOS actor folder out_dir/name (geo layout name_geo)."""
    props = bpy.context.scene.fast64.sm64.combined_export
    props.export_header_type = "Custom"
    os.makedirs(out_dir, exist_ok=True)
    props.custom_export_path = os.path.abspath(out_dir)
    props.object_name = name
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.object.sm64_export_geolayout_object(export_obj=obj.name)
    folder = os.path.join(os.path.abspath(out_dir), name)
    if "FINISHED" not in result or not os.path.exists(os.path.join(folder, "geo.inc.c")):
        raise RuntimeError(f"export of {name} failed: {result}")
    return folder


def along(bm, start: Vector, end: Vector):
    """Turn geometry built along +Z (0..1) to run from start to end."""
    d = end - start
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(start) @ rot @ Matrix.Diagonal((1, 1, d.length, 1)),
                        verts=bm.verts)
