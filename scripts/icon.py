"""Kid Goku's Character Select icon, drawn pixel by pixel here, and written as the mod's texture.

Usage: python3 scripts/icon.py  (needs Pillow; writes mod/kid-goku/textures/goku_icon.tex)
"""
import io
import os
import struct

from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
COLORS = {".": (0, 0, 0, 0), "K": (18, 16, 22, 255), "S": (252, 216, 202, 255), "A": (228, 168, 150, 255),
          "W": (255, 255, 255, 255), "M": (140, 48, 58, 255)}
ART = """
.....K....K.....
..K..KK..KK..K..
..KK.KKKKKK.KK..
K.KKKKKKKKKKKK.K
.KKKKKKKKKKKKKK.
KKKKKKSKKSKKKKKK
.KKKSKSSSSKSKKK.
KKKSSSSSSSSSSKKK
.KSWWWSSSSWWWSK.
.ASWKWSSSSWKWSA.
.ASWWWSSSSWWWSA.
..SSSSSASSSSSS..
...SSSSSSSSSS...
...SSMSSSSMSS...
....ASMMMMSA....
.....AAAAAA.....
"""


def main():
    rows = ART.split()
    image = Image.new("RGBA", (16, 16))
    image.putdata([COLORS[c] for row in rows for c in row])
    png = io.BytesIO()
    image.save(png, "PNG")
    name = b"goku_icon"
    folder = os.path.join(ROOT, "mod", "kid-goku", "textures")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "goku_icon.tex"), "wb") as out:
        out.write(bytes((2, len(name))) + name + struct.pack("<I", png.getbuffer().nbytes) + png.getvalue())
    print("wrote goku_icon.tex")


if __name__ == "__main__":
    main()
