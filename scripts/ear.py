"""His ear, drawn as the anime draws it (Goku_Smiling_13245): a plain oval with a swoop over the top that runs into a small curl.

It has its own texture, laid flat on the ear's plane. On his face's texture the wrap round his head squeezes the ear into a sliver,
where any line comes out as a scribble. Both ears share it, mirrored by how far each point is from his head.
"""
import math

CENTER_SIDE, CENTER_FRONT, TURN = 0.339, 0.102, 0.68
A0, A1, B0, B1 = 0.06, 0.38, -0.16, 0.12
FROM_SIDE = 0.29
BEHIND = 0.17
NAPE = 0.06
BELOW = 0.13


def uv(p):
    """A head vertex's place on the ear's texture."""
    up, side, front = p
    b = (abs(side) - CENTER_SIDE) * math.cos(TURN) - (front - CENTER_FRONT) * math.sin(TURN)
    return min(1.0, max(0.0, (b - B0) / (B1 - B0))), min(1.0, max(0.0, (up - A0) / (A1 - A0)))


PLAIN = (0.02, 0.98)
BACK = 0.03


def behind(p):
    """A head vertex a little toward the back of the ear."""
    up, side, front = p
    return up, side - math.copysign(BACK * math.sin(TURN), side), front - BACK * math.cos(TURN)


SWOOPS = (
    ((158, 500), (153, 445), (168, 395), (205, 360), (245, 372), (280, 420), (305, 470), (322, 530), (320, 575), (298, 600), (272, 585),
     (258, 552), (265, 525), (285, 512)),
    ((210, 545), (204, 490), (215, 440), (245, 420), (275, 432), (297, 462)),
    ((262, 540), (255, 580), (272, 635), (305, 688), (340, 695), (356, 668), (340, 640), (318, 640)),
)
LINE = 0.0036
EDGE_ON = 2.2


def _on_ear(x, y):
    return 0.097 - (x - 105) * (0.148 / 295), 0.307 - (y - 280) * (0.227 / 550)


def _smooth(points, steps=10):
    """A curve through the points."""
    out = []
    ends = [points[0], *points, points[-1]]
    for k in range(1, len(ends) - 2):
        p0, p1, p2, p3 = ends[k - 1:k + 3]
        for i in range(steps):
            t = i / steps
            out.append(tuple(0.5 * (2 * p1[c] + (p2[c] - p0[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                    + (3 * p1[c] - p0[c] - 3 * p2[c] + p3[c]) * t * t * t) for c in (0, 1)))
    out.append(points[-1])
    return out


def draw(size, skin, ink):
    """The texture, size pixels square: his skin, with the swoops in ink."""
    from PIL import Image, ImageDraw
    big = size * 4
    im = Image.new("RGB", (big, big), skin)
    d = ImageDraw.Draw(im)
    per_unit = big / (A1 - A0)
    for swoop in SWOOPS:
        curve = _smooth(swoop)
        for k, (x, y) in enumerate(curve):
            b, a = _on_ear(x, y)
            px, py = (b - B0) / (B1 - B0) * big, (1 - (a - A0) / (A1 - A0)) * big
            r = LINE * per_unit / 2 * (0.55 + 0.45 * math.sin(math.pi * k / (len(curve) - 1)))
            d.ellipse((px - r * EDGE_ON, py - r, px + r * EDGE_ON, py + r), fill=ink)
    return im.resize((size, size), Image.LANCZOS)
