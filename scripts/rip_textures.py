"""Remake Tenkaichi 3's Kid Goku textures as N64 textures: cropped to what the model uses, box-downscaled and
quantized to CI4 (16 colors) with the n64-texture skill, every one fitting TMEM. Everything stays local.

Usage: python3 scripts/rip_textures.py RIP_DIR OUT_DIR   (needs Pillow; writes goku_n64_<k>.ci4.png, a
goku_face_<name>.ci4.png per expression and crops.json)

crops.json maps each texture to the UV box its crop keeps (u0, v0, u1, v1, in Blender's UV space, v up), so bt3.py
can remap the model's UVs; "mirror" means the crop is half the image, drawn with Mirror S. A texture listed as
"vertex" is plain color and becomes vertex color only.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ear import draw as draw_ear
from textures import kanji

QUANTIZE = os.path.expanduser("~/.claude/skills/n64-texture/scripts/quantize_texture.py")
PLAN = {
    0: (None, "64x64"),
    1: (None, "64x64"),
    2: (None, "32x32"),
    3: (None, "32x128"),
    4: (None, "64x64"),
    5: (None, "64x64"),
    7: (None, "64x64"),
    8: ((0, 0, 128, 128), "64x64"),
    9: (None, "16x16"),
}
PLAIN = {6}
BADGES = {1: [(72, 56, 96, 94), (168, 39, 215, 110)]}
CREAM, INK = (214, 178, 84, 255), (24, 20, 16, 255)


SKIN = (254, 198, 161)
ANIME_SKIN = (252, 216, 202)
EAR_INK = (58, 34, 30)
SKIN_TEXTURES = {5, 7}


def anime_skin(im):
    return im.point([min(255, round(v * ANIME_SKIN[b] / SKIN[b])) if b < 3 else v for b in range(4) for v in range(256)])


def clean_face(im):
    """Skin texels flattened to the one skin color (no banding noise, no pink drift against the vertex-color skin),
    and the ink thickened a texel so it survives the downscale."""
    px = im.load()
    ink = Image.new("L", im.size, 0)
    ik = ink.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if r + g + b < 230:
                ik[x, y] = 255
            elif r > 200 and g > 200 and b > 200:
                px[x, y] = (255, 255, 255, a)
            elif abs(r - SKIN[0]) + abs(g - SKIN[1]) + abs(b - SKIN[2]) < 70:
                px[x, y] = (*SKIN, a)
    im.paste(Image.new("RGBA", im.size, (24, 18, 16, 255)), (0, 0), ink.filter(ImageFilter.MaxFilter(3)))
    return im


EXPRESSIONS = ("relaxed", "half", "closed", "determined", "shout", "surprised", "happy", "dead", "blink_half", "blink",
               "smile", "grit", "fierce", "yell", "hit", "cheer", "grin", "yell_left", "yell_right")


def redraw_badges(path, k, src_size, dst_size):
    im = Image.open(path).convert("RGBA")
    sx, sy = dst_size[0] / src_size[0], dst_size[1] / src_size[1]
    glyph = kanji().split()[3]
    for x0, y0, x1, y1 in BADGES.get(k, []):
        box = (round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy))
        ImageDraw.Draw(im).ellipse((box[0], box[1], box[2] - 1, box[3] - 1), fill=CREAM)
        w, h = box[2] - box[0], box[3] - box[1]
        mask = glyph.filter(ImageFilter.MaxFilter(5)).resize((max(1, round(w * 0.86)), max(1, round(h * 0.74))),
                                                              Image.LANCZOS).point(lambda a: 255 if a > 105 else 0)
        ink = Image.new("RGBA", mask.size, INK)
        im.paste(ink, (box[0] + (w - mask.width) // 2, box[1] + (h - mask.height) // 2), mask)
    im.save(path)


def main() -> int:
    rip, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, ".src_ear.png")
    draw_ear(64, ANIME_SKIN, EAR_INK).save(tmp)
    subprocess.run([sys.executable, QUANTIZE, tmp, os.path.join(out, "goku_n64_ear.ci4.png"), "--format", "CI4", "--size", "64x64",
                    "--dither", "none"], check=True, capture_output=True)
    os.remove(tmp)
    crops = {}
    for k in range(10):
        src = os.path.join(rip, f"chara011_1p_{k}.png")
        im = Image.open(src).convert("RGBA")
        if k in PLAIN:
            crops[k] = {"vertex": list(im.getpixel((0, 0))[:3])}
            continue
        box, size = PLAN[k]
        if box:
            im = im.crop(box)
            w, h = Image.open(src).size
            crops[k] = {"uv": [box[0] / w, 1 - box[3] / h, box[2] / w, 1 - box[1] / h], "mirror": k == 8}
        else:
            crops[k] = {"uv": [0, 0, 1, 1]}
        if k in SKIN_TEXTURES:
            im = anime_skin(im)
        if k == 8:
            im = clean_face(im)
            crops["faces"] = {}
            whole = Image.new("RGBA", (im.width * 2, im.height))
            whole.paste(im, (0, 0))
            whole.paste(im.transpose(Image.FLIP_LEFT_RIGHT), (im.width, 0))
            for name in EXPRESSIONS:
                tmp = os.path.join(out, f".src_face_{name}.png")
                whole.save(tmp)
                dst = os.path.join(out, f"goku_face_{name}.ci4.png")
                subprocess.run([sys.executable, QUANTIZE, tmp, dst, "--format", "CI4", "--size", size, "--dither",
                                "none"], check=True, capture_output=True)
                os.remove(tmp)
                crops["faces"][name] = dst
        tmp = os.path.join(out, f".src_{k}.png")
        im.save(tmp)
        dst = os.path.join(out, f"goku_n64_{k}.ci4.png")
        subprocess.run([sys.executable, QUANTIZE, tmp, dst, "--format", "CI4", "--size", size, "--dither", "none"],
                       check=True, capture_output=True)
        os.remove(tmp)
        if k in BADGES:
            redraw_badges(dst, k, Image.open(src).size, tuple(int(n) for n in size.split("x")))
            subprocess.run([sys.executable, QUANTIZE, dst, dst, "--format", "CI4", "--size", size, "--dither", "none"],
                           check=True, capture_output=True)
        crops[k]["file"] = dst
        crops[k]["size"] = size
        print(f"{k}: {size} CI4")
    with open(os.path.join(out, "crops.json"), "w") as f:
        json.dump(crops, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
