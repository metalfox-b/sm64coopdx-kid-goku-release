"""Where Metal Fox drew on a picture of a face, so what he drew can be traced.

  read_markup.py PICTURE MARKED OUT_DIR

MARKED is PICTURE with his marks on it, any size. Writes OUT_DIR/marks.png, his marks alone on white at PICTURE's size, and prints each mark's box in PICTURE's pixels.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def main():
    base, marked, out = sys.argv[1:4]
    a = Image.open(base).convert("RGB")
    b = Image.open(marked).convert("RGB").resize(a.size, Image.LANCZOS)
    x, y = np.asarray(a).astype(int), np.asarray(b).astype(int)
    drawn = ndi.binary_opening(np.abs(x - y).sum(axis=2) > 90, np.ones((2, 2), bool))
    os.makedirs(out, exist_ok=True)
    marks = np.full(y.shape, 255, np.uint8)
    marks[drawn] = y[drawn]
    Image.fromarray(marks).save(os.path.join(out, "marks.png"))
    lab, n = ndi.label(ndi.binary_dilation(drawn, np.ones((9, 9), bool)))
    for k, s in enumerate(ndi.find_objects(lab), 1):
        print(f"mark {k}: x {s[1].start} to {s[1].stop}, y {s[0].start} to {s[0].stop}")
    print(f"{n} marks")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
