"""The two-tone light on his head's skin: one rule for his face, his ears and the skin beside them (needs numpy).

The anime paints kid Goku's skin in two flat tones with a hard edge. Of the 144 shaded faces among the stills we hold (docs/shading.md has the
count), 131 have a band down the cheek and jaw away from the light. It follows the cheek's outline, stops at the eye's outline, widens toward
the jaw, and takes the ear on that side with it (79 of the 98 that show the ear). In 91 his hair throws slivers of shadow on his forehead
beside its spikes, on that same side whenever they're on one side.

His body's skin and clothes already turn from the light by their shape (goku.py's LIGHT and ramps: from his left, so his right is the far
side). His face can't: its expression is a texture. So faces.py paints this rule into every expression, and bt3.py puts his ears and the skin
round them on the same side of it, so the shadow runs from his cheek onto his ear without a seam.

The rule goes by where a point is across his face, never by the mesh's own normals: the rip's face folds between his nose and mouth, and
shading by its normals drew a pink sliver there. A ball in his head's place was no better: lit from
above, its whole lower half is dark, and the anime never shades his mouth and chin.
"""
import numpy as np

LIGHT = np.array((0.70, -0.62, 0.35)) / np.linalg.norm((0.70, -0.62, 0.35))
VIEW, SCALE, CX, CY = 800, 840, 400, 660
EYES, MOUTH = 0.21, 0.03
BAND_EYES, BAND_MOUTH = 0.15, 0.18
SLIVER = (27, 10)
SMOOTH = 22


def view(p):
    """A point of his head (up, toward his right, front) in the front view: his right is on its left."""
    return CX - p[1] * SCALE, CY - p[0] * SCALE


def _rows(face, hair):
    """Each front-view pixel's nearest surface: (it's hair, it's his face). Two VIEW x VIEW boolean arrays."""
    v = np.array(face["verts"], float)
    xy = np.array([view(p) for p in v])
    depth = v[:, 2]
    tris = [((idx[0], idx[k], idx[k + 1]), 1) for idx, *_ in face["faces"] for k in range(1, len(idx) - 1)]
    tris += [((idx[0], idx[k], idx[k + 1]), 2 if m == "Hair" else 0) for idx, m in face["rest"] for k in range(1, len(idx) - 1)]
    nearest = np.full((VIEW, VIEW), -np.inf)
    kind = np.zeros((VIEW, VIEW), np.uint8)
    for t, what in tris:
        if what == 2 and not hair or what == 0:
            continue
        (x0, y0), (x1, y1), (x2, y2) = xy[list(t)]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        xa, xb = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, VIEW - 1)
        ya, yb = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, VIEW - 1)
        if abs(den) < 1e-9 or xa > xb or ya > yb:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb + 1) + .5, np.arange(ya, yb + 1) + .5)
        a = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        b = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        c = 1 - a - b
        z = a * depth[t[0]] + b * depth[t[1]] + c * depth[t[2]]
        box = nearest[ya:yb + 1, xa:xb + 1]
        win = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6) & (z > box)
        box[win] = z[win]
        kind[ya:yb + 1, xa:xb + 1][win] = what
    return kind == 2, kind == 1


def outline(face):
    """His face's far and near edges in the front view, a pixel column for each row (two arrays of VIEW), eased so its corners are round."""
    _, skin = _rows(face, hair=False)
    rows = np.flatnonzero(skin.any(axis=1))
    far = np.array([np.flatnonzero(skin[y])[0] for y in rows], float)
    near = np.array([np.flatnonzero(skin[y])[-1] for y in rows], float)
    weights = np.exp(-0.5 * (np.arange(-3 * SMOOTH, 3 * SMOOTH + 1) / SMOOTH) ** 2)
    weights /= weights.sum()

    def eased(edge):
        padded = np.r_[np.full(3 * SMOOTH, edge[0]), edge, np.full(3 * SMOOTH, edge[-1])]
        whole = np.interp(np.arange(VIEW), rows, np.convolve(padded, weights, mode="valid"))
        return whole
    return eased(far), eased(near)


def across(edges, points):
    """How far across his face each point is, from its far edge (0, his right) to its near one (1), at that point's height."""
    far, near = edges
    p = np.atleast_2d(np.array(points, float))
    x, y = CX - p[:, 1] * SCALE, np.clip(CY - p[:, 0] * SCALE, 0, VIEW - 1)
    row = y.astype(int)
    return (x - far[row]) / np.maximum(near[row] - far[row], 1)


def band(points):
    """How much of his face's width is in shadow at each point's height: BAND_EYES at his eyes and above, widening to BAND_MOUTH at his mouth
    and on at that rate to his chin."""
    up = np.atleast_2d(np.array(points, float))[:, 0]
    return BAND_EYES + (BAND_MOUTH - BAND_EYES) * np.clip((EYES - up) / (EYES - MOUTH), 0, 1.5)


def turned_away(edges, points):
    """Whether each point of his head's skin is on the far side of the band's edge."""
    return across(edges, points) < band(points)


def hair_shadow(face):
    """The front view's pixels his hair's shadow falls on (a VIEW x VIEW boolean array): skin with hair within SLIVER of it toward the light,
    which is his left, the view's right, and up."""
    cover, _ = _rows(face, hair=True)
    reach, drop = SLIVER
    shadow = np.zeros_like(cover)
    steps = max(reach, drop)
    for k in range(1, steps + 1):
        dx, dy = round(reach * k / steps), round(drop * k / steps)
        shadow[dy:, :VIEW - dx] |= cover[:VIEW - dy, dx:]
    return shadow & ~cover
