"""Give Kid Goku's model a node at each joint for g-blend.lua to turn, so one animation can flow into the next.

Usage: python3 scripts/blend_nodes.py ACTOR/geo.inc.c   (build.mjs runs it)

An animated part draws its own mesh straight after the animation has posed it, so a node placed after the part wouldn't reach
that mesh. So each moving joint's mesh moves down into a display-list node under a new rotation node, which turns the mesh and
everything below it:

    GEO_ANIMATED_PART(layer, x, y, z, NULL),
    GEO_OPEN_NODE(),
        GEO_ROTATION_NODE(LAYER_FORCE, joint, 90, -90),
        GEO_OPEN_NODE(),
            GEO_DISPLAY_LIST(layer, mesh),
            ...what was under the part...

The pole on his back moves off his torso's mesh into a list of its own, under a scale node of 65537 (no other scale is), so
g-blend.lua can shrink it away while it's in his hands.

The rotation is how Lua tells which joint a node is: the joint's number in degrees, and 90 and -90, which no other node of his
starts at. g-blend.lua reads it and zeroes it before his first frame. A translation node round the root does the same for his
height. Only his normal body has them: the metal one just cuts.
"""
import re
import sys

ORDER = ["Body", "Butt", "Torso", "Head", "Left Arm", "Left Arm Color", "Left Forearm", "Left Hand", "Right Arm",
         "Right Arm Color", "Right Forearm", "Right Hand", "Left Thigh", "Left Thigh Color", "Left Leg", "Left Shoe",
         "Right Thigh", "Right Thigh Color", "Right Leg", "Right Shoe"]
HANDS = {"goku_Left_Hand_Open": "Left Hand", "goku_Right_Hand_Open": "Right Hand", "goku_Right_Hand_Peace": "Right Hand",
         "goku_Right_Hand_Cap": "Right Hand", "goku_Right_Hand_Wing_Cap": "Right Hand"}
PART = re.compile(r"^(\s*)GEO_ANIMATED_PART\((\w+), (-?\d+), (-?\d+), (-?\d+), (\w+)\),\s*$")
NEXT_OPENS = re.compile(r"^\s*GEO_OPEN_NODE\(\),\s*$")
CLOSES = re.compile(r"^\s*GEO_CLOSE_NODE\(\),\s*$")


def layout(lines, name):
    start = next(i for i, line in enumerate(lines) if line.startswith(f"const GeoLayout {name}[]"))
    return start, next(i for i in range(start, len(lines)) if lines[i].startswith("};"))


def subtree_end(lines, opened):
    depth = 0
    for i in range(opened, len(lines)):
        depth += bool(NEXT_OPENS.match(lines[i])) - bool(CLOSES.match(lines[i]))
        if depth == 0:
            return i
    raise ValueError("unbalanced geo layout")


def split_back_pole(geo_path):
    """Move the pole's own materials out of his torso's display list, into goku_Back_Pole_mesh_layer_1."""
    folder = geo_path.rsplit("/", 1)[0]
    with open(f"{folder}/model.inc.c") as f:
        model = f.read()
    start = model.index("Gfx goku_Torso_mesh_layer_1[] = {")
    end = model.index("};", start)
    moved = re.findall(r"\tgsSPDisplayList\(mat_goku_Pole(?:_Line)?\),\n\tgsSPDisplayList\(\w+\),\n"
                       r"\tgsSPDisplayList\(mat_revert_goku_Pole(?:_Line)?\),\n", model[start:end])
    if len(moved) != 2:
        raise ValueError(f"expected the back pole and its outline in the torso's list, found {len(moved)}")
    block = model[start:end]
    for lines in moved:
        block = block.replace(lines, "")
    own = "Gfx goku_Back_Pole_mesh_layer_1[] = {\n" + "".join(moved) + "\tgsSPEndDisplayList(),\n};\n\n"
    with open(f"{folder}/model.inc.c", "w") as f:
        f.write(model[:start] + own + block + model[end:])
    with open(f"{folder}/geo_header.h", "a") as f:
        f.write("extern Gfx goku_Back_Pole_mesh_layer_1[];\n")


def wrap_part(lines, at, joint):
    """Put a rotation node for this joint (ORDER's number, from 1) under the part at this line."""
    pad, layer, x, y, z, mesh = PART.match(lines[at]).groups()
    has_children = NEXT_OPENS.match(lines[at + 1])
    end = subtree_end(lines, at + 1) if has_children else at
    inner = lines[at + 2:end] if has_children else []
    lines[at:end + 1] = [
        f"{pad}GEO_ANIMATED_PART({layer}, {x}, {y}, {z}, NULL),\n",
        f"{pad}GEO_OPEN_NODE(),\n",
        f"{pad}\tGEO_ROTATION_NODE(LAYER_FORCE, {joint}, 90, -90),\n",
        f"{pad}\tGEO_OPEN_NODE(),\n",
        *([f"{pad}\t\tGEO_DISPLAY_LIST({layer}, {mesh}),\n"] if mesh != "NULL" else []),
        *([f"{pad}\t\tGEO_SCALE(LAYER_FORCE, 65537),\n", f"{pad}\t\tGEO_OPEN_NODE(),\n",
           f"{pad}\t\t\tGEO_DISPLAY_LIST({layer}, goku_Back_Pole_mesh_layer_1),\n",
           f"{pad}\t\tGEO_CLOSE_NODE(),\n"] if joint == ORDER.index("Torso") + 1 else []),
        *inner,
        f"{pad}\tGEO_CLOSE_NODE(),\n",
        f"{pad}GEO_CLOSE_NODE(),\n",
    ]


def wrap_root(lines, at):
    pad = PART.match(lines[at]).group(1)
    end = subtree_end(lines, at + 1)
    lines[at:end + 1] = [f"{pad}GEO_TRANSLATE_NODE(LAYER_FORCE, 0, 0, 0),\n", f"{pad}GEO_OPEN_NODE(),\n",
                         *lines[at:end + 1], f"{pad}GEO_CLOSE_NODE(),\n"]


def main():
    path = sys.argv[1]
    with open(path) as f:
        lines = f.readlines()
    for name, bone in HANDS.items():
        start, end = layout(lines, name)
        at = next(i for i in range(start, end) if PART.match(lines[i]))
        wrap_part(lines, at, ORDER.index(bone) + 1)
    start, end = layout(lines, "goku_geo")
    parts = [i for i in range(start, end) if PART.match(lines[i])]
    if len(parts) != len(ORDER):
        raise ValueError(f"expected {len(ORDER)} animated parts in goku_geo, found {len(parts)}")
    for at, bone in reversed(list(zip(parts, ORDER))):
        if bone == "Body":
            wrap_root(lines, at)
        elif "Color" not in bone:
            wrap_part(lines, at, ORDER.index(bone) + 1)
    with open(path, "w") as f:
        f.writelines(lines)
    split_back_pole(path)
    print("blend nodes: 15 joints, 5 hands")


if __name__ == "__main__":
    main()
