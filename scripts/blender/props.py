"""Build Kid Goku's props in code and export each as a DynOS actor (runs inside Blender).

Usage:
  blender -b --python scripts/blender/props.py -- OUT_ACTORS_DIR [SAVE.blend]

goku_beam  the Kamehameha's shaft: 100 units long along +Z, radius 50 (the beam scales it)
goku_dash  a white dash that runs up the shaft: 100 units long along +Z, 100 wide
goku_ball  the charge ball and the beam's bulbs: radius 50 (flat, it faces the camera)
goku_burst the spray where the wave hits a wall: radius 50, jagged
goku_nimbus the Flying Nimbus, about 170 units across
goku_trail one link of the band it leaves behind it as it flies: radius 50, 100 long, narrowing
goku_tail  one link of his tail: 10 units long along +Z, 3.6 thick, rounded at both ends
goku_dragon_ball the four-star Dragon Ball: radius 50 (a dome, it faces the camera)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
from mathutils import Matrix, Vector

import n64

FWD = Vector((0, -1, 0))
U = 1 / n64.SCALE


def cylinder(segments: int, radius: float, start: Vector, end: Vector, cap: bool = True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=segments, radius1=radius, radius2=radius, depth=1)
    bmesh.ops.translate(bm, vec=(0, 0, 0.5), verts=bm.verts)
    n64.along(bm, start, end)
    return bm


def light_mesh(name, bm, colors, cull=False):
    obj = n64.mesh_object(name, bm)
    n64.f3d_material(obj, name + " Light", n64.LAYER_TRANSPARENT, alpha=True, cull=cull)
    n64.paint(obj, lambda co, n, mat: colors[tuple(round(v, 5) for v in co)])
    return obj


def light_vertex(bm, colors, point, color, opacity):
    v = bm.verts.new(point)
    colors[tuple(round(c, 5) for c in v.co)] = (*n64.hex_rgb(color), opacity)
    return v


def beam():
    """Three nested tubes, any way the camera looks: a soft outer glow, the blue contour the anime rings the wave
    with, and an ice core the white dashes (goku_dash) run up. The two outer ones show only their far sides, so
    they sit behind the core; a transparent layer that lay over it would tint it."""
    bm, colors = bmesh.new(), {}
    sides = 8

    def shell(radius, color, alpha, flip):
        bands = [(0, radius * 0.55), (2.5, radius * 0.92), (9, radius), (88, radius), (100, radius * 0.72)]
        rings = [[light_vertex(bm, colors, (r * U * math.cos(i * math.tau / sides), -z * U,
                                            r * U * math.sin(i * math.tau / sides)), color, alpha)
                  for i in range(sides)] for z, r in bands]
        for a, b in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                face = (a[i], b[i], b[j], a[j])
                bm.faces.new(face if flip else face[::-1])

    shell(68, "2FA8FF", 0.30, True)
    shell(52, "2B9DFF", 1.0, True)
    shell(36, "86D8FF", 1.0, False)
    return light_mesh("goku_beam", bm, colors, cull=True)


def dash():
    """A slanted white dash with pointed ends, as the anime paints up the wave. The beam turns it to the camera."""
    bm, colors = bmesh.new(), {}
    slant = 16
    rows = [(0, 0.20), (22, 0.46), (78, 0.46), (100, 0.20)]
    prev = None
    for z, half in rows:
        row = [light_vertex(bm, colors, (0, -(z + h * slant) * U, h * half * 100 * U), "FFFFFF", 1)
               for h in (-1, 1)]
        if prev:
            bm.faces.new((prev[0], prev[1], row[1], row[0]))
        prev = row
    return light_mesh("goku_dash", bm, colors)


def ball():
    """A round white center, a crisp ice-blue contour and a soft outer ring, at any viewing angle. It's as bright as
    the anime's bulb: most of its radius is pure white."""
    bm, colors = bmesh.new(), {}
    core = light_vertex(bm, colors, (0, -0.43, 0), "FFFFFF", 1)
    prev = []
    for radius, color, alpha in ((0.25, "FFFFFF", 1), (0.325, "D2F4FF", 1),
                                  (0.385, "39B4FF", 1), (0.44, "2B9DFF", 0.6), (0.50, "2B9DFF", 0)):
        depth = math.sqrt(max(0, 0.43 ** 2 - radius ** 2))
        row = [light_vertex(bm, colors, (radius * math.cos(a), -depth, radius * math.sin(a)), color, alpha)
               for a in (i * math.tau / 24 for i in range(24))]
        for i, v in enumerate(row):
            j = (i + 1) % len(row)
            bm.faces.new((prev[i], prev[j], row[j], v) if prev else (core, row[j], v))
        prev = row
    return light_mesh("goku_ball", bm, colors)


def burst():
    """The blue spray where the wave strikes: a jagged star round a white heart, the way episode 8 draws it."""
    bm, colors = bmesh.new(), {}
    core = light_vertex(bm, colors, (0, -0.02, 0), "FFFFFF", 1)
    spikes = 11
    inner, tips = [], []
    for i in range(spikes):
        a = i * math.tau / spikes
        reach = 0.5 if i % 2 == 0 else 0.34
        inner.append(light_vertex(bm, colors, (0.17 * math.cos(a), 0, 0.17 * math.sin(a)), "E8FBFF", 1))
        b = a + math.pi / spikes
        tips.append(light_vertex(bm, colors, (reach * math.cos(b), 0, reach * math.sin(b)), "2B9DFF", 0.75))
    for i in range(spikes):
        j = (i + 1) % spikes
        bm.faces.new((core, inner[j], inner[i]))
        bm.faces.new((inner[i], inner[j], tips[i]))
    return light_mesh("goku_burst", bm, colors)



def nimbus():
    """The Flying Nimbus as episode 3 draws it: a big soft heap of round puffs, pale cream on top and warm gold below,
    ringed by a thin orange line, with a wisp trailing behind."""
    bm = bmesh.new()
    puffs = [((0, 0, 0), 0.60, (1.28, 1.05, 0.50)), ((0.62, 0.10, 0.03), 0.36, (1, 1, 0.82)),
             ((-0.62, 0.05, 0.03), 0.38, (1, 1, 0.82)), ((0.30, -0.52, 0.03), 0.36, (1, 1, 0.8)),
             ((-0.32, -0.50, 0.02), 0.34, (1, 1, 0.8)), ((0.32, 0.52, 0.04), 0.34, (1, 1, 0.8)),
             ((-0.30, 0.54, 0.03), 0.36, (1, 1, 0.8)), ((0.0, 0.05, 0.20), 0.40, (1.25, 1.1, 0.55)),
             ((0.02, 0.94, 0.00), 0.25, (0.9, 1.1, 0.72)), ((0.0, 1.27, -0.01), 0.15, (0.8, 1.2, 0.7))]
    for (x, y, z), r, (sx, sy, sz) in puffs:
        part = bmesh.new()
        bmesh.ops.create_icosphere(part, subdivisions=2, radius=r)
        bmesh.ops.transform(part, matrix=Matrix.Translation((x, y, z)) @ Matrix.Diagonal((sx, sy, sz, 1)),
                            verts=part.verts)
        me = bpy.data.meshes.new("tmp")
        part.to_mesh(me)
        part.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.scale(bm, vec=(0.96, 0.96, 0.96), verts=bm.verts)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    shell = {v: bm.verts.new(v.co + v.normal * 0.014) for v in list(bm.verts)}
    for f in list(bm.faces):
        new = bm.faces.new([shell[v] for v in reversed(f.verts)])
        new.material_index = 1
    obj = n64.mesh_object("goku_nimbus", bm)
    n64.f3d_material(obj, "Nimbus")
    n64.f3d_material(obj, "Nimbus Line")
    line = n64.hex_rgb("E09A3C")
    top, mid, low = n64.hex_rgb("FFF4BE"), n64.hex_rgb("FFE08A"), n64.hex_rgb("F0B445")

    def tone(co, n, m):
        if m == 1:
            return (*line, 1.0)
        return (*(top if n.z > 0.25 else mid if n.z > -0.35 else low), 1.0)
    n64.paint(obj, tone)
    return obj


def trail():
    """One link of the band the Nimbus draws across the sky behind it (the anime's long gold streak): a tube 50 in radius and 100 long that
    narrows by TRAIL_TAPER along its length, so d-nimbus.lua can lay them end to end, each as wide as the last one ended, down to nothing.
    Its wide end is a shallow dome that fills the outside of a bend; its narrow end is open, inside the next link's dome. The cloud's own
    flat tones, with no line: a line round every link showed as a tick across the band wherever it bent."""
    bm = bmesh.new()
    sides, taper = 10, 0.86
    stations = [(-0.15, 0.0), (-0.12, 0.3), (-0.07, 0.42), (0.0, 0.5), (1.0, 0.5 * taper)]
    rings = []
    for y, r in stations:
        if r == 0:
            rings.append([bm.verts.new((0, -y, 0))])
        else:
            rings.append([bm.verts.new((r * math.cos(k * math.tau / sides), -y, r * math.sin(k * math.tau / sides))) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            n = (k + 1) % sides
            bm.faces.new((a[0], b[n], b[k]) if len(a) == 1 else (a[k], a[n], b[n], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    obj = n64.mesh_object("goku_trail", bm)
    n64.f3d_material(obj, "Trail", cull=False)
    top, mid, low = n64.hex_rgb("FFF4BE"), n64.hex_rgb("FFE08A"), n64.hex_rgb("F0B445")
    n64.paint(obj, lambda co, n, m: (*(top if n.z > 0.55 else mid if n.z > -0.3 else low), 1.0))
    return obj


def tail():
    """One link of his tail: a slim capsule, its ends round about the joints it shares with the links either side. e-body.lua strings them
    along a curve, so however they bend, their sides and their outlines run into each other as one smooth line; any other ends stuck
    out past the next link at each joint as a black tick. The anime's own browns as hard cel tones, a whole face each: a shadow blended
    across each link broke into patches where the next one crossed it (Goku_using_his_tail)."""
    bm = bmesh.new()
    sides = 12
    r = 3.6
    line = 0.3
    stretch = 0.595

    def capsule(radius, flip, material, sides):
        cap = [(radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a)) / stretch) for a in (70, 40, 20)]
        stations = [(-reach, ring) for ring, reach in cap] + [(0, radius), (10, radius)] + [(10 + reach, ring) for ring, reach in reversed(cap)]
        rings = [[bm.verts.new((ring * U * math.cos(a), -z * U, ring * U * math.sin(a)))
                  for a in ((k + 0.5) * math.tau / sides for k in range(sides))] for z, ring in stations]
        faces = []
        for a, b in zip(rings, rings[1:]):
            for k in range(sides):
                n = (k + 1) % sides
                faces.append((a[k], b[k], b[n], a[n]))
        faces.append(tuple(rings[0]))
        faces.append(tuple(reversed(rings[-1])))
        for f in faces:
            face = bm.faces.new(f if flip else f[::-1])
            face.material_index = material

    capsule(r, False, 0, sides)
    capsule(r + line, True, 1, sides * 2)
    obj = n64.mesh_object("goku_tail", bm)
    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    body_mat = createF3DMat(obj, "Shaded Texture")
    body_mat.name = "Tail"
    body_mat.f3d_mat.rdp_settings.g_lighting = False
    body_mat.f3d_mat.rdp_settings.g_mdsft_text_filt = "G_TF_POINT"
    body_mat.f3d_mat.draw_layer.sm64 = "3"
    ramp = bpy.data.images.new("goku_ramp_tail.rgba16.png", 16, 4, alpha=True)
    ramp.colorspace_settings.name = "sRGB"
    light, shade = n64.hex_rgb("774A2F"), n64.hex_rgb("5A3626")
    ramp.pixels = [c for _y in range(4) for x in range(16) for c in (*(light if x >= 8 else shade), 1.0)]
    ramp.filepath_raw = os.path.join(os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--") + 1])), "goku_ramp_tail.rgba16.png")
    ramp.file_format = "PNG"
    ramp.save()
    body_mat.f3d_mat.tex0.tex = ramp
    body_mat.f3d_mat.tex0.tex_format = "RGBA16"
    tex = body_mat.f3d_mat.tex0
    tex.S.clamp, tex.T.clamp = True, True
    tex.autoprop = False
    tex.S.low, tex.S.high, tex.S.mask = 0, 15, 4
    tex.T.low, tex.T.high, tex.T.mask = 0, 3, 2
    outline = n64.f3d_material(obj, "Tail Outline").f3d_mat.rdp_settings
    outline.set_rendermode = True
    outline.rendermode_preset_cycle_1, outline.rendermode_preset_cycle_2 = "G_RM_AA_ZB_XLU_SURF", "G_RM_AA_ZB_XLU_SURF2"
    ink = n64.hex_rgb("120A08")
    me = obj.data
    col = me.color_attributes.get("Col") or me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    alpha = me.color_attributes.get("Alpha") or me.color_attributes.new("Alpha", "BYTE_COLOR", "CORNER")
    uv = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (max(0.0, min(1.0, 0.5 + (v.z / max(math.hypot(v.x, v.z), 1e-6)) / 4)), 0.5)
            col.data[li].color_srgb = (*(ink if poly.material_index == 1 else (1.0, 1.0, 1.0)), 1.0)
            alpha.data[li].color_srgb = (1.0, 1.0, 1.0, 1.0)
    return obj


def dragon_ball():
    """The four-star Dragon Ball as episode 2 draws them (e02-Bulma_finds_the_Dragon_Balls_that_aren't_gone): orange, a pale crescent of
    light round its upper left edge, a small round glint by its top, and red stars in its middle. A dome that faces the camera, so
    its four stars always show, as they do however the anime turns one."""
    R, SEG = 0.5, 32
    rings = (0.14, 0.26, 0.36, 0.43, 0.47, R)
    BASE, LIGHT, LINE, STAR = range(4)
    bm = bmesh.new()

    def depth(r):
        return -0.55 * math.sqrt(max(0.0, R * R - r * r))

    def face(verts, material):
        f = bm.faces.new(verts)
        f.material_index = material

    center = bm.verts.new((0, depth(0), 0))
    rows = [[bm.verts.new((r * math.cos(i * math.tau / SEG), depth(r), r * math.sin(i * math.tau / SEG))) for i in range(SEG)]
            for r in rings]
    for i in range(SEG):
        j = (i + 1) % SEG
        face((center, rows[0][i], rows[0][j]), BASE)
        mid = math.degrees((i + 0.5) * math.tau / SEG)
        for k in range(len(rings) - 1):
            lit = k in (2, 3) and 112 < mid < 205
            face((rows[k][i], rows[k + 1][i], rows[k + 1][j], rows[k][j]), LINE if k == len(rings) - 2 else LIGHT if lit else BASE)

    def disc(x, z, radius, y, material, points):
        hub = bm.verts.new((x, y, z))
        rim = [bm.verts.new((x + r * math.cos(a), y, z + r * math.sin(a))) for r, a in points(radius)]
        for i, v in enumerate(rim):
            face((hub, v, rim[(i + 1) % len(rim)]), material)

    disc(0.05, 0.30, 0.055, depth(0.3) - 0.03, LIGHT, lambda r: [(r, i * math.tau / 10) for i in range(10)])
    for x, z, turn in ((-0.105, 0.085, 8), (0.10, 0.11, -14), (-0.085, -0.125, -6), (0.115, -0.09, 20)):
        disc(x, z, 0.095, depth(0) - 0.03, STAR,
             lambda r, turn=turn: [((r if i % 2 == 0 else r * 0.42), math.radians(90 + turn) + i * math.tau / 10) for i in range(10)])
    bm.normal_update()
    for f in bm.faces:
        if f.normal.y > 0:
            f.normal_flip()
    obj = n64.mesh_object("goku_dragon_ball", bm)
    colors = [n64.hex_rgb(c) for c in ("F08C28", "FBE3BE", "C65A14", "D7341C")]
    for name in ("Dragon Ball", "Dragon Ball Light", "Dragon Ball Line", "Dragon Ball Star"):
        n64.f3d_material(obj, name)
    n64.paint(obj, lambda co, n, m: (*colors[m], 1.0))
    return obj


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = args[0]
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    n64.setup_scene()
    for build in (beam, dash, ball, burst, nimbus, trail, tail, dragon_ball):
        obj = build()
        bm = obj.data
        bpy.ops.object.select_all(action="DESELECT")
        print(f"built {obj.name}: {n64.tris(obj)} tris, {len(bm.materials)} materials")
        n64.export_object(obj, obj.name, out)
    if len(args) > 1:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
