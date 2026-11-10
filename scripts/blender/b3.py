"""Kid Goku's N64 remake from Budokai 3's model, on Mario's skeleton, exported as one actor (runs inside Blender).

Usage:
  blender -b TEMPLATE.blend --python scripts/blender/b3.py -- B3.json TEX_DIR ACTOR OUT_DIR RIG.json [PREVIEW_DIR]

B3.json is obj_extract.py's output; TEX_DIR is b3_textures.py's (the textures of one costume); ACTOR names the geo
layout (goku for the Pilaf-saga gi, goku_turtle for the Turtle School gi). RIG.json gets the skeleton anims.py stands
him on. Everything made from the rip stays local.

The body is one connected skin, the way Mario's own model is: each vertex follows one bone (the region it's in) and
triangles stretch across the joints, so nothing gaps when he bends. Budokai 3's textures are multiplied by
Gouraud shading baked into the vertex colors, with lighting off, as N64 characters were drawn.
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
from mathutils import Vector

import anims
import body
import bt3
import goku

CHIN = 42.2
HEIGHT = 2.8
JOINTS = {"hips": (0, 0, 28.0), "waist": (0, -0.4, 32.5), "neck": (0, -0.8, 43.8),
          "l_shoulder": (5.6, -0.4, 42.6), "l_elbow": (12.8, -0.4, 42.4), "l_wrist": (19.6, -0.4, 42.3),
          "l_knuckle": (26.0, -0.6, 42.2), "l_hip": (3.8, 0, 27.0), "l_knee": (3.7, -0.4, 16.5),
          "l_ankle": (3.5, -0.2, 6.6)}
for k in list(JOINTS):
    if k.startswith("l_"):
        x, y, z = JOINTS[k]
        JOINTS["r_" + k[2:]] = (-x, y, z)
PART = {"phong1SG": "belt", "phong3SG": "arms", "phong4SG": "shirt", "phong2SG": "pants", "phong6SG": "face",
        "phong18SG": "face", "phong5SG": "shoes", "phong12SG": "wristband", "phong17SG": "sole", "phong15SG": "hair",
        "phong16SG": "hair", "phong14SG": "tail", "phong7SG": "powerpole", "phong13SG": "hands",
        "phong8SG": "mouth", "phong9SG": "mouth", "phong10SG": "mouth", "phong11SG": "mouth"}
DROP = {"tail", "mouth"}
SHADOW = {"face": (0.86, 0.64, 0.58), "arms": (0.86, 0.64, 0.58), "hands": (0.86, 0.64, 0.58),
          "hair": (0.55, 0.55, 0.72), "shirt": (0.58, 0.58, 0.80), "pants": (0.58, 0.58, 0.80),
          "belt": (0.62, 0.62, 0.80), "shoes": (0.58, 0.58, 0.78), "sole": (0.6, 0.6, 0.7),
          "wristband": (0.66, 0.58, 0.68), "powerpole": (0.70, 0.56, 0.56)}
LIGHT = Vector((0.35, -0.75, 0.60)).normalized()
FIST_SCALE = 1.45
TARGET_TRIS = int(os.environ.get("GOKU_TRIS", 1000))
EXPRESSIONS = {"Open Eyes (SKIN)": "relaxed", "Half Closed Eyes (SKIN)": "half", "Closed Eyes (SKIN)": "closed",
               "Left Eyes (SKIN)": "determined", "Right Eyes (SKIN)": "shout", "Up Eyes (SKIN)": "surprised",
               "Down Eyes (SKIN)": "happy", "Dead Eyes (SKIN)": "dead"}


def region(p, part, j):
    """The Mario bone a vertex follows, from where it is."""
    x, y, z = p
    side = "Left" if x > 0 else "Right"
    if part == "face" or part == "hair":
        return "Head DL" if z > CHIN or part == "hair" else "Torso"
    if part in ("arms", "wristband"):
        return f"{side} Arm Color" if abs(x) < j["l_elbow"][0] else f"{side} Forearm"
    if part in ("shoes", "sole"):
        return "Left Shoe" if x > 0 else "Right Shoe DL"
    if part in ("shirt", "powerpole"):
        return "Torso"
    if part == "belt":
        return "Butt"
    if z > j["l_hip"][2]:
        return "Butt"
    return f"{side} Thigh Color" if z > j["l_knee"][2] else f"{side} Leg"


FRAME = {"Head DL": "Head", "Left Arm Color": "Left Arm", "Right Arm Color": "Right Arm", "Left Thigh Color": "Left Thigh",
         "Right Thigh Color": "Right Thigh", "Right Shoe DL": "Right Shoe", "Left Hand DL": "Left Hand",
         "Right Hand DL": "Right Hand"}
JOINT_OF = {"Butt": "hips", "Torso": "waist", "Head": "neck", "Left Arm": "l_shoulder", "Right Arm": "r_shoulder",
            "Left Forearm": "l_elbow", "Right Forearm": "r_elbow", "Left Hand": "l_wrist", "Right Hand": "r_wrist",
            "Left Thigh": "l_hip", "Right Thigh": "r_hip", "Left Leg": "l_knee", "Right Leg": "r_knee",
            "Left Shoe": "l_ankle", "Right Shoe": "r_ankle"}


def load(path, s):
    data = json.load(open(path))
    parts = [PART[m["name"]] for m in data["materials"]]
    verts = [Vector(v) * s for v in data["verts"]]
    tris = []
    for t, uv, mi in data["tris"]:
        part = parts[mi]
        if part in DROP:
            continue
        tris.append((t, uv, part))
    pole = [k for k, (t, _, p) in enumerate(tris) if p == "powerpole"]
    adj = {}
    for k in pole:
        for i in tris[k][0]:
            adj.setdefault(i, set()).add(k)
    seen, held = set(), set()
    for k in pole:
        if k in seen:
            continue
        stack, comp = [k], set()
        while stack:
            c = stack.pop()
            if c in comp:
                continue
            comp.add(c)
            for i in tris[c][0]:
                stack.extend(adj[i] - comp)
        seen |= comp
        if min(verts[i].y for c in comp for i in tris[c][0]) < -8 * s:
            held |= comp
    tris = [t for k, t in enumerate(tris) if k not in held]
    out = []
    eps = 0.004
    for t, uv, part in tris:
        xs = [verts[i].x for i in t]
        if part != "pants" or min(xs) >= 0 or max(xs) <= 0:
            out.append((t, uv, part))
            continue
        for side in (1, -1):
            nt = []
            for i in t:
                if verts[i].x * side >= 0:
                    nt.append(i)
                else:
                    verts.append(Vector((side * eps, verts[i].y, verts[i].z)))
                    nt.append(len(verts) - 1)
            out.append((nt, uv, part))
    return verts, out


CUTS = [("pants", 2, 27.0), ("pants", 2, 16.5), ("pants", 2, 6.4), ("arms", 0, 12.8), ("arms", 0, -12.8),
        ("face", 2, CHIN)]


def reduce(verts, tris, s):
    """Decimate the body to TARGET_TRIS in its T-pose, keeping each part's texture in place: the face merges only
    near-flat triangles within its UVs, the rest collapses with UV seams held."""
    names = sorted({p for _, _, p in tris})
    me = bpy.data.meshes.new("b3")
    me.from_pydata([tuple(v) for v in verts], [], [t for t, _, _ in tris])
    print("reduce input", len(tris), "polys", len(me.polygons))
    uvl = me.uv_layers.new(name="UVMap")
    for poly, (_, uv, p) in zip(me.polygons, tris):
        poly.material_index = names.index(p)
        for k, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uv[k]
    obj = bpy.data.objects.new("b3", me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    held = set()
    for part, axis, at in CUTS:
        mi = names.index(part)
        faces = [f for f in bm.faces if f.material_index == mi]
        geom = list({e for f in faces for e in f.edges}) + faces + list({v for f in faces for v in f.verts})
        no = [0, 0, 0]
        no[axis] = 1
        co = [0, 0, 0]
        co[axis] = at * s
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, dist=1e-5)
        held |= {e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMVert)}
    bmesh.ops.triangulate(bm, faces=bm.faces)
    held_co = {tuple(round(c, 5) for c in v.co) for v in held}
    face_mi = names.index("face")
    if os.environ.get("GOKU_NO_REDUCE"):
        pass
    else:
      bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(18), use_dissolve_boundaries=False,
                             verts=[v for v in bm.verts if all(f.material_index == face_mi for f in v.link_faces)],
                             edges=[e for e in bm.edges if all(f.material_index == face_mi for f in e.link_faces)],
                             delimit={"UV", "MATERIAL"})
    bm.to_mesh(me)
    bm.free()
    keep = obj.vertex_groups.new(name="free")
    me = obj.data
    seam = set()
    uvl = me.uv_layers.active.data
    first = {}
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            u = tuple(round(c, 4) for c in uvl[li].uv)
            if vi in first and first[vi] != (u, poly.material_index):
                seam.add(vi)
            first.setdefault(vi, (u, poly.material_index))
    facev = {vi for poly in me.polygons if poly.material_index == face_mi for vi in poly.vertices}
    facev |= {v.index for v in me.vertices if tuple(round(c, 5) for c in v.co) in held_co}
    keep.add([v.index for v in me.vertices if v.index not in seam and v.index not in facev], 1.0, "REPLACE")
    now = sum(len(p.vertices) - 2 for p in me.polygons)
    mod = obj.modifiers.new("d", "DECIMATE")
    mod.ratio = max(0.05, min(1.0, TARGET_TRIS / now))
    mod.vertex_group = "free"
    mod.use_collapse_triangulate = True
    obj.modifiers.new("t", "TRIANGULATE")
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    em = ev.to_mesh()
    em.calc_loop_triangles()
    em.calc_normals_split() if hasattr(em, "calc_normals_split") else None
    vout = [Vector(v.co) for v in em.vertices]
    nout = [Vector(v.normal) for v in em.vertices]
    euv = em.uv_layers.active.data
    tout = [(list(t.vertices), [tuple(euv[li].uv) for li in t.loops], names[t.material_index]) for t in em.loop_triangles]
    ev.to_mesh_clear()
    bpy.data.objects.remove(obj)
    print(f"reduced {now} -> {len(tout)} tris")
    return vout, nout, tout


def shade(part, n):
    t = max(0.0, min(1.0, 0.42 + 0.68 * n.dot(LIGHT)))
    sr, sg, sb = SHADOW.get(part, (0.65, 0.65, 0.78))
    return (sr + (1 - sr) * t, sg + (1 - sg) * t, sb + (1 - sb) * t)


def solve_skeleton(jp):
    pose = {"pelvis": (0, 0, 0), "torso": (0, 0, 0), "head": (0, 0, 0)}
    err = []
    for side, s_ in (("l", "Left"), ("r", "Right")):
        err.append(bt3.solve(pose, f"{s_} Arm", f"{side}_arm", jp[f"{side}_elbow"] - jp[f"{side}_shoulder"],
                             [(-60, 60), (0, 140)]))
        err.append(bt3.solve(pose, f"{s_} Forearm", f"{side}_elbow", jp[f"{side}_wrist"] - jp[f"{side}_elbow"],
                             [(-30, 120)]))
        err.append(bt3.solve(pose, f"{s_} Hand", f"{side}_hand", jp[f"{side}_knuckle"] - jp[f"{side}_wrist"],
                             [(-80, 80), (-80, 80)]))
        err.append(bt3.solve(pose, f"{s_} Thigh", f"{side}_hip", jp[f"{side}_knee"] - jp[f"{side}_hip"],
                             [(-40, 40), (-20, 40)]))
        err.append(bt3.solve(pose, f"{s_} Leg", f"{side}_knee", jp[f"{side}_ankle"] - jp[f"{side}_knee"],
                             [(-30, 60)]))
        pose[f"{side}_foot"] = 0
    print("fit errors (deg):", [round(e, 2) for e in err])
    return bt3.world_frames(pose)


def main() -> int:
    args = sys.argv[sys.argv.index("--") + 1:]
    src, texdir, actor, out, rig_path = args[:5]
    preview_dir = args[5] if len(args) > 5 else None
    data = json.load(open(src))
    top = max(v[2] for v in data["verts"])
    s = HEIGHT / top
    jp = {k: Vector(v) * s for k, v in JOINTS.items()}
    verts, tris = load(src, s)
    hand_tris = [t for t in tris if t[2] == "hands"]
    body_tris = [t for t in tris if t[2] != "hands"]
    W = solve_skeleton(jp)

    def rest_offset(parent, child, par_joint):
        lx, ly, lz = W[parent].transposed() @ (jp[child] - jp[par_joint])
        return (lx, -lz, ly)
    rest = {"Torso": rest_offset("Butt", "waist", "hips"), "Head": rest_offset("Torso", "neck", "waist")}
    for side, s_ in (("l", "Left"), ("r", "Right")):
        rest[f"{s_} Arm"] = rest_offset("Torso", f"{side}_shoulder", "waist")
        rest[f"{s_} Forearm"] = rest_offset(f"{s_} Arm", f"{side}_elbow", f"{side}_shoulder")
        rest[f"{s_} Hand"] = rest_offset(f"{s_} Forearm", f"{side}_wrist", f"{side}_elbow")
        rest[f"{s_} Thigh"] = rest_offset("Butt", f"{side}_hip", "hips")
        rest[f"{s_} Leg"] = rest_offset(f"{s_} Thigh", f"{side}_knee", f"{side}_hip")
        rest[f"{s_} Shoe"] = rest_offset(f"{s_} Leg", f"{side}_ankle", f"{side}_knee")
        rest[f"{s_} Arm Color"] = rest[f"{s_} Thigh Color"] = (0, 0, 0)
    anims.REST = rest

    rverts, rnormals, rtris = reduce(verts, body_tris, s)
    vpart = {}
    for t, _, p in rtris:
        for i in t:
            vpart.setdefault(i, p)
    vbone = {i: region(tuple(v / s for v in rverts[i]), vpart[i], {k: tuple(c / s for c in jp[k]) for k in jp})
             for i in vpart}

    split = seams(rtris, vbone)

    def to_rest(p, bone):
        frame = FRAME.get(bone, bone)
        lx, ly, lz = W[frame].transposed() @ (p - jp[JOINT_OF[frame]])
        return (lx, -lz, ly)

    sole = [to_rest(rverts[i], "Left Shoe") for i in vbone if vbone[i] == "Left Shoe"]
    low = max(w for _, _, w in sole)
    xs = [u for u, _, w in sole if w > low - 0.04]
    with open(rig_path, "w") as f:
        json.dump({"REST": rest, "SOLE": [(min(xs), low), ((min(xs) + max(xs)) / 2, low), (max(xs), low)]}, f, indent=1)

    from fast64.fast64_internal.f3d.f3d_material import createF3DMat
    sizes = json.load(open(os.path.join(texdir, "sizes.json")))
    face_rows, face_cols = sizes["face_rows"], sizes["face_cols"]

    def textured(name, path):
        m = createF3DMat(None, "Shaded Texture")
        m.name = name
        f = m.f3d_mat
        f.rdp_settings.g_lighting = False
        f.rdp_settings.g_cull_back = True
        img = bpy.data.images.load(path, check_existing=True)
        img.name = os.path.basename(path).replace(".ci4.png", f"_{actor}.ci4.png")
        f.tex0.tex = img
        f.tex0.tex_format = "CI4"
        f.tex0.ci_format = "RGBA16"
        return m
    for part in ("belt", "arms", "shirt", "pants", "shoes", "wristband", "sole", "hair", "powerpole", "hands"):
        textured(f"B3 {part}", os.path.join(texdir, f"goku_b3_{part}.ci4.png"))
    for mat, expr in EXPRESSIONS.items():
        f = bpy.data.materials[mat].f3d_mat
        f.rdp_settings.g_lighting = False
        img = bpy.data.images.load(os.path.join(texdir, f"goku_face_{expr}.ci4.png"), check_existing=True)
        img.name = f"goku_face_{expr}_{actor}.ci4.png"
        f.tex0.tex = img
        f.tex0.tex_format = "CI4"
        f.tex0.ci_format = "RGBA16"
        f.tex0.S.clamp, f.tex0.T.clamp = True, True
    for name in ("Fist", goku.SKIN):
        skin = createF3DMat(None, "Shaded Solid")
        skin.name = name
        skin.f3d_mat.rdp_settings.g_lighting = False

    def mat_of(part):
        return goku.FACE if part == "face" else f"B3 {part}"

    def uv_of(part, uv):
        if part != "face":
            return uv
        u, v = uv
        return (u * 256 / face_cols, 1 + v * 256 / face_rows)

    goku.chibi_skeleton("Mario")
    goku.chibi_skeleton("Metal Mario")
    for metal in (False, True):
        obj = bpy.data.objects["Metal Mario Mesh" if metal else "Mario Mesh"]
        arm = obj.parent
        inv = obj.matrix_world.inverted()
        P, F, UV, MAT, COL, G = [], [], [], [], [], []
        index = {}
        def vert(i, b):
            if (i, b) not in index:
                index[(i, b)] = len(P)
                P.append(inv @ (goku.bone_head(arm, b) + Vector(to_rest(rverts[i], b))))
                G.append(b)
            return index[(i, b)]
        for k, (t, uv, part) in enumerate(rtris):
            if k in split and split[k] is None:
                continue
            owner = split.get(k)
            F.append([vert(i, owner or vbone[i]) for i in t])
            UV.append([uv_of(part, c) for c in uv])
            MAT.append(goku.METAL if metal else mat_of(part))
            COL.append([shade(part, rnormals[i]) for i in t])
        for side in ("Left", "Right"):
            bone = f"{side} Hand DL"
            fist = bt3.scaled(body.fist(1), FIST_SCALE / 1.15)
            fist.verts = [(u + 0.03, v, w) for u, v, w in fist.verts]
            base = len(P)
            for u, v, w in fist.verts:
                P.append(inv @ (goku.bone_head(arm, bone) + Vector((u, v, w))))
                G.append(bone)
            for idx, _, _ in fist.faces:
                F.append([base + k for k in idx])
                UV.append([(0, 0)] * len(idx))
                MAT.append(goku.METAL if metal else "Fist")
                COL.append([(0.97, 0.80, 0.68)] * len(idx))
        write_mesh(obj, P, F, UV, MAT, COL, G)
        if os.environ.get("GOKU_DEBUG"):
            fuv = [uv for uv, m in zip(UV, MAT) if m == goku.FACE][:2]
            print("FACEUV GIVEN", fuv)
    head = goku.Part()
    hindex = {}
    for t, uv, part in rtris:
        if all(vbone[i] == "Head DL" for i in t):
            for i in t:
                if i not in hindex:
                    hindex[i] = head.v(*to_rest(rverts[i], "Head DL"))
            head.face([hindex[i] for i in t], mat_of(part), [uv_of(part, c) for c in uv])
    goku.COLORS.update({goku.FACE: ("FFFFFF", "DCA894")})
    for m in EXPRESSIONS:
        goku.COLORS[m] = ("FFFFFF", "DCA894")
    goku.COLORS["B3 hair"] = ("FFFFFF", "8C8CB8")
    faceuv("after main")
    goku.build(bpy.data.objects["Capless Head Mesh"], {"Capless Head": lambda: head})
    faceuv("after capless")
    for side in ("Left", "Right"):
        hand = goku.Part()
        hix = {}
        for t, uv, part in hand_tris:
            if (verts[t[0]].x > 0) != (side == "Left"):
                continue
            for i in t:
                if i not in hix:
                    lx, ly, lz = W[f"{side} Hand"].transposed() @ (verts[i] - jp[f"{'l' if side == 'Left' else 'r'}_wrist"])
                    hix[i] = hand.v(lx, -lz, ly)
            hand.face([hix[i] for i in t], "B3 hands", uv)
        goku.COLORS["B3 hands"] = ("FFFFFF", "DCA894")
        hand = bt3.decimate(hand, 0.45, collapse=True)
        goku.build(bpy.data.objects[f"{side} Hand Open Mesh"], {f"{side} Hand Open": lambda h=hand: h})
        if side == "Right":
            for name in ("Right Hand Cap", "Right Hand Wing Cap"):
                goku.build(bpy.data.objects[f"{name} Mesh"], {name: lambda h=hand: h})
    faceuv("after hands")
    goku.build(bpy.data.objects["Right Hand Peace Mesh"], {"Right Hand Peace": lambda: bt3.scaled(goku.peace_hand(), 0.85)})
    for name in ("Capless Head", "Left Hand Open", "Right Hand Open", "Right Hand Peace", "Right Hand Cap",
                 "Right Hand Wing Cap"):
        metal = bpy.data.objects.get(f"Metal {name} Mesh")
        src_obj = bpy.data.objects.get(f"{name} Mesh")
        if metal and src_obj:
            metal.data = src_obj.data.copy()
            metal.data.materials.clear()
            metal.data.materials.append(bpy.data.materials[goku.METAL])
            for poly in metal.data.polygons:
                poly.material_index = 0
    tris_main = sum(len(p.vertices) - 2 for p in bpy.data.objects["Mario Mesh"].data.polygons)
    print(f"Kid Goku ({actor}): {tris_main} tris in the main body")

    if os.environ.get("GOKU_DEBUG"):
        me_ = bpy.data.objects["Mario Mesh"].data
        fi = [m.name for m in me_.materials].index(goku.FACE)
        u_ = me_.uv_layers.active.data
        print("FACEUV END", sorted({tuple(round(c, 2) for c in u_[li].uv) for p_ in me_.polygons
                                    if p_.material_index == fi for li in p_.loop_indices})[:6])
    if os.environ.get("GOKU_SAVE"):
        bpy.ops.wm.save_as_mainfile(filepath=os.environ["GOKU_SAVE"])
    if preview_dir:
        goku.preview(preview_dir)
        return 0
    bpy.context.scene.gameEditorMode = "SM64"
    bpy.context.scene.f3d_type = "F3D"
    sm64 = bpy.context.scene.fast64.sm64
    sm64.export_type = "C"
    props = sm64.combined_export
    props.export_header_type = "Custom"
    os.makedirs(out, exist_ok=True)
    props.custom_export_path = os.path.abspath(out)
    props.object_name = actor
    bpy.context.scene.saveTextures = True
    rig = bpy.data.objects["Mario"]
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    result = bpy.ops.object.sm64_export_geolayout_armature(export_obj=rig.name)
    if "FINISHED" not in result:
        raise RuntimeError(f"export failed: {result}")
    print("exported", actor, "->", os.path.join(out, actor))
    return 0


PARENT = {"Torso": "Butt", "Head DL": "Torso", "Left Arm Color": "Torso", "Right Arm Color": "Torso",
          "Left Forearm": "Left Arm Color", "Right Forearm": "Right Arm Color", "Left Thigh Color": "Butt",
          "Right Thigh Color": "Butt", "Left Leg": "Left Thigh Color", "Right Leg": "Right Thigh Color",
          "Left Shoe": "Left Leg", "Right Shoe DL": "Right Leg"}
MAX_SHARED = 6


def seams(tris, vbone):
    """Which triangles can't stay connected across their joint, and the bone that takes them whole.

    A triangle across a joint keeps its vertices on both bones (the skin stretches) only when the joint has few
    enough shared vertices for Fast64; otherwise it's moved whole onto the child bone (its parent-side vertices
    duplicated), and the overlapping cloth hides the seam. Triangles spanning bones that aren't parent and child are
    always moved onto the deeper bone."""
    def depth(b):
        n = 0
        while b in PARENT:
            b, n = PARENT[b], n + 1
        return n
    split, shared = {}, {}
    for k, (t, uv, part) in enumerate(tris):
        bones = {vbone[i] for i in t}
        if len(bones) == 1:
            continue
        child = max(bones, key=depth)
        if any("Left" in b for b in bones) and any("Right" in b for b in bones):
            split[k] = "Butt"
            continue
        if len(bones) == 2 and PARENT.get(child) in bones:
            shared.setdefault(child, {})[k] = {(i, tuple(round(c, 3) for c in c_), part)
                                               for i, c_ in zip(t, uv) if vbone[i] != child}
        else:
            split[k] = child
    for child, by_tri in shared.items():
        keys = set().union(*by_tri.values())
        if len(keys) > MAX_SHARED:
            for k in by_tri:
                split[k] = PARENT[child]
            print(f"joint {PARENT[child]} - {child}: {len(keys)} shared vertices, seamed")
        else:
            print(f"joint {PARENT[child]} - {child}: connected ({len(keys)} shared)")
    return split


def faceuv(tag):
    if not os.environ.get("GOKU_DEBUG"):
        return
    me_ = bpy.data.objects["Mario Mesh"].data
    fi = [m.name for m in me_.materials].index(goku.FACE)
    u_ = me_.uv_layers.active.data
    print("FACEUV", tag, len(me_.uv_layers), sorted({tuple(round(c, 2) for c in u_[li].uv) for p_ in me_.polygons
                                                   if p_.material_index == fi for li in p_.loop_indices})[:3])


def write_mesh(obj, P, F, UV, MAT, COL, G):
    me = obj.data
    names = []
    for m in MAT:
        if m not in names:
            names.append(m)
    me.clear_geometry()
    me.materials.clear()
    for n in names:
        me.materials.append(bpy.data.materials[n])
    me.from_pydata([tuple(p) for p in P], [], F)
    me.update()
    if len(me.polygons) != len(F):
        print(f"WARNING {obj.name}: {len(F)} faces given, {len(me.polygons)} made")
    col = me.color_attributes.get("Col") or me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    uvl = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name="UVMap")
    for poly, m, uv, c in zip(me.polygons, MAT, UV, COL):
        poly.material_index = names.index(m)
        poly.use_smooth = True
        for k, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uv[k]
            col.data[li].color_srgb = (*c[k], 1.0)
    if os.environ.get("GOKU_DEBUG"):
        bad = sum(1 for poly, uv in zip(me.polygons, UV) for k, li in enumerate(poly.loop_indices)
                  if (Vector(uvl.data[li].uv) - Vector(uv[k])).length > 1e-3)
        print("UVWRITE layers", [l.name for l in me.uv_layers], "bad", bad,
              "verts", [list(me.polygons[0].vertices)], F[0])
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for i, b in enumerate(G):
        groups.setdefault(b, []).append(i)
    for b, idx in groups.items():
        obj.vertex_groups.new(name=b).add(idx, 1.0, "REPLACE")
    print(f"built {obj.name}: {sum(len(p.vertices) - 2 for p in me.polygons)} tris, {len(names)} materials")


if __name__ == "__main__":
    sys.exit(main())
