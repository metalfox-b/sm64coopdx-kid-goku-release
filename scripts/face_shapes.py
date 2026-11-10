"""Give an expression a head of its own, once Metal Fox has passed it.

Usage: python3 scripts/face_shapes.py ACTOR/model.inc.c   (build.mjs runs it)

His built head is the anime's closed-mouth face, and the anime drops his jaw to open his mouth. His eye switch
draws a whole head for each eye state, with a material swapped, so an expression here gets its own copy of those vertices. Each player's eye state picks
their own head, and nothing runs at play time. faces.py paints the expression through its own head, and trace_faces.py lays it out by that head's chin.
"""
import math
import re
import sys

SHAPES = {}
NEUTRAL = (1.0, 1.0)

EYE_HEIGHT, CHIN_HEIGHT = 0.21, -0.045
SM64_UNITS = 213.5
DEPTH_FROM, DEPTH_TO = 0.02, 0.10
FORWARD = 0.6
HEADS = ("goku_Head_DL_mesh_layer_1", "goku_Capless_Head_Switch_Option_Capless_Head_mesh_layer_1")
EYE_MATERIAL = re.compile(r"mat_goku_(\w+?)_Eyes__SKIN_")
EXPRESSION = {"Cheer": "cheer"}
VERTEX = re.compile(r"\{\{\s*\{(-?\d+), (-?\d+), (-?\d+)\}")


def stretch_of(name):
    return SHAPES.get(name, NEUTRAL)[0]


def warp(point, shape):
    """A point of his head (height, side, depth, in Blender units) on this shape. Only what's below his eye line and in front of his
    ears moves. It comes forward as it goes down, or the longer chin would sink behind his collar: the anime draws it over his neck."""
    height, side, depth = point
    stretch, widen = shape
    if height >= EYE_HEIGHT or shape == NEUTRAL:
        return point
    x = min(1.0, max(0.0, (depth - DEPTH_FROM) / (DEPTH_TO - DEPTH_FROM)))
    front = x * x * (3 - 2 * x)
    drop = (EYE_HEIGHT - height) * (stretch - 1) * front
    down = min(1.0, (EYE_HEIGHT - height) / (EYE_HEIGHT - CHIN_HEIGHT))
    return height - drop, side * (1 + (widen - 1) * front * math.sin(math.pi * down ** 1.5)), depth + drop * FORWARD


def block(model, start):
    """The whole of the C definition that starts here, with what follows it."""
    end = model.index("};", start) + 3
    return model[start:end]


def shaped_vertices(text, shape):
    def move(m):
        height, side, depth = warp((int(m[1]) / SM64_UNITS, int(m[3]) / SM64_UNITS, int(m[2]) / SM64_UNITS), shape)
        return "{{ {%d, %d, %d}" % (round(height * SM64_UNITS), round(depth * SM64_UNITS), round(side * SM64_UNITS))
    return VERTEX.sub(move, text)


def bake(model):
    for head in HEADS:
        added, shaped_names = [], set()
        for option in re.finditer(rf"Gfx {head}_opt_\d+\[\] = \{{.*?\n\}};\n", model, re.S):
            eye = EYE_MATERIAL.search(option[0])
            name = EXPRESSION.get(eye[1]) if eye else None
            if name not in SHAPES:
                continue
            shaped_names.add(name)
            shaped = option[0]
            for tri in sorted(set(re.findall(rf"{head}_tri_\d+", option[0]))):
                vtx = tri.replace("_tri_", "_vtx_")
                new_tri, new_vtx = f"{tri}_{name}", f"{vtx}_{name}"
                vertices = block(model, model.index(f"Vtx {vtx}["))
                triangles = block(model, model.index(f"Gfx {tri}[]"))
                added.append(shaped_vertices(vertices, SHAPES[name]).replace(f"Vtx {vtx}[", f"Vtx {new_vtx}[", 1))
                added.append(triangles.replace(f"Gfx {tri}[]", f"Gfx {new_tri}[]", 1).replace(f"{vtx} ", f"{new_vtx} "))
                shaped = re.sub(rf"\b{tri}\b", new_tri, shaped)
            model = model.replace(option[0], shaped)
        if shaped_names != set(SHAPES):
            raise ValueError(f"{head}: no eye state found for {sorted(set(SHAPES) - shaped_names)}")
        first = model.index(f"Gfx {head}[] = {{")
        model = model[:first] + "\n".join(added) + "\n" + model[first:]
    return model


def main():
    path = sys.argv[1]
    with open(path) as f:
        model = f.read()
    with open(path, "w") as f:
        f.write(bake(model))
    print("face shapes:", ", ".join(SHAPES))


if __name__ == "__main__":
    main()
