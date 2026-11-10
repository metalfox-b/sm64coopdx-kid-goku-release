"""Contact sheet of captured frames: python3 scripts/sheet.py DIR OUT.png [first last step] (needs Pillow)."""
import os
import sys

from PIL import Image

d, out = sys.argv[1], sys.argv[2]
files = sorted(f for f in os.listdir(d) if f.endswith(".ppm"))
first, last, step = (int(a) for a in sys.argv[3:6]) if len(sys.argv) > 5 else (0, len(files) - 1, 8)
pick = files[first:last + 1:step]
cols = 4
w, h = 320, 240
sheet = Image.new("RGB", (w * cols, h * ((len(pick) + cols - 1) // cols)))
for i, f in enumerate(pick):
    sheet.paste(Image.open(os.path.join(d, f)).convert("RGB").resize((w, h)), ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(out, len(pick), "frames")
