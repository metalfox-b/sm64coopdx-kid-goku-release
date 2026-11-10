"""Write Kid Goku's traced expressions as art/faces/<name>.svg (needs nothing beyond Python).

Usage: python3 scripts/trace_faces.py [NAME ...]   (all of them when none is named)

Each expression is traced by hand over one frame of the 1986 anime: its points are read off zoomed, gridded crops of
the frame resized to 900 wide, and stay in that frame's pixels here. The frames themselves stay local
(private/reference/anime-faces/); this file and the SVGs it writes are our drawing.

An SVG's viewBox is faces.py's front view of his head (800x800, his head's origin at (400, 660), 840 px a unit). Its
groups lay the frame on it:
- each eye at the frame's own proportions, scaled evenly by the eye spacing about its center, level, on its place;
- the nose and mouth symmetric (traced as half offsets from their middle, the frame's halves averaged), level, on the
  face's middle line, scaled across by the eye spacing and down by the eyes-to-chin height, so a turned head's mouth
  can't come out lopsided;
- the brows, where the frame's bangs hide them, borrowed from a frame of the same mood that shows them on skin and
  set by their own eye.
Ink lines are centerlines with a width at each point (class="ink", data-w), which faces.py turns into filled outlines.
"""
import math
import os
import sys

from face_shapes import stretch_of

ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "art", "faces")
INK, WHITE, MOUTH, TONGUE = "#1e161a", "#ffffff", "#8c303a", "#e28084"
RIGHT_EYE, LEFT_EYE = (400 - .13 * 840, 660 - .21 * 840), (400 + .13 * 840, 660 - .21 * 840)
CHIN = 660 + .045 * 840


def smooth(pts, closed=False):
    """Absolute M/C path data through pts (Catmull-Rom as cubic Béziers)."""
    p = [pts[-1]] + pts + pts[:2] if closed else [pts[0]] + pts + [pts[-1]]
    out = [f"M{p[1][0]:.1f},{p[1][1]:.1f}"]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(out) + (" Z" if closed else "")


def mirrored(half):
    """A curve from the left end to the middle (x 0), mirrored into the whole curve, left to right."""
    return half + [(-x, y) for x, y in reversed(half[:-1])]


def ink(pts, widths):
    """A line through pts, its width at each point in the frame's pixels (0 is a pointed tip)."""
    assert len(widths) == len(pts), (len(widths), len(pts))
    return (f'<path class="ink" d="{smooth(pts)}" data-w="{" ".join(str(w) for w in widths)}" fill="none" '
            f'stroke="{INK}" stroke-width="{max(widths)}" stroke-linecap="round"/>')


def shape(pts, fill):
    return f'<path d="{smooth(pts, closed=True)}" fill="{fill}"/>'


def ellipse(cx, cy, rx, ry, fill, turn=0):
    t = f' transform="rotate({turn} {cx} {cy})"' if turn else ""
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"{t}/>'


def levelled(pts, pivot, angle):
    """Points traced on a tilted head, turned level about pivot (angle: how far its eye line dips toward his left eye, in degrees)."""
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return [(round(pivot[0] + (x - pivot[0]) * c + (y - pivot[1]) * s, 2), round(pivot[1] - (x - pivot[0]) * s + (y - pivot[1]) * c, 2))
            for x, y in pts]


MOUTH_WIDTH = 242.5 * 2 * .13 * 840 / math.hypot(180, 11.5)
GRIT_MIDDLE, GRIT_TILT = (589.25, 240.25), 10.43
GRIT_EYES = 0.85
GRIT_MOUTH = 0.92
GRIT_LIFT = 16


class Face:
    """One expression's frame: its eyes' centers (his right eye is on the left of the frame), its chin's height, and
    the middle of its mouth, all in the frame's pixels."""

    def __init__(self, name, frame, right_eye, left_eye, chin, middle):
        self.name, self.frame, self.middle = name, frame, middle
        self.right_eye, self.left_eye = right_eye, left_eye
        mx, my = (right_eye[0] + left_eye[0]) / 2, (right_eye[1] + left_eye[1]) / 2
        dx, dy = left_eye[0] - right_eye[0], left_eye[1] - right_eye[1]
        self.turn = -math.atan2(dy, dx)
        self.kx = (LEFT_EYE[0] - RIGHT_EYE[0]) / math.hypot(dx, dy)
        self.ky = (CHIN - RIGHT_EYE[1]) * stretch_of(name) / ((chin - my) * math.cos(self.turn))
        drop = (middle[0] - mx) * math.sin(self.turn) + (middle[1] - my) * math.cos(self.turn)
        self.middle_y = RIGHT_EYE[1] + self.ky * drop
        self.parts = []

    def eye(self, which, *elements, size=1, inward=0):
        """An eye's elements (traced round center), at the frame's own proportions on his right or left eye; size
        (across, down) scales it about its center, for a frame whose eyes are drawn bigger than his head carries
        them; inward moves it toward the middle (front-view pixels)."""
        center, at = (self.right_eye, RIGHT_EYE) if which == "right" else (self.left_eye, LEFT_EYE)
        at = (at[0] + (inward if which == "right" else -inward), at[1])
        sx, sy = (size, size) if isinstance(size, (int, float)) else size
        k, c, s = self.kx, math.cos(self.turn), math.sin(self.turn)
        m = (k * sx * c, k * sx * s, -k * sy * s, k * sy * c)
        e, f = at[0] - (m[0] * center[0] + m[2] * center[1]), at[1] - (m[1] * center[0] + m[3] * center[1])
        self.group(f"{m[0]:.5f} {m[1]:.5f} {m[2]:.5f} {m[3]:.5f} {e:.3f} {f:.3f}", elements)

    def mirror_eye(self, *elements):
        """The left eye's elements mirrored onto the right eye (for a face whose eyes must match a mirrored brow)."""
        (lx, ly), (rx, ry) = self.left_eye, self.right_eye
        self.eye("right", f'<g transform="matrix(-1 0 0 1 {lx + rx} {ry - ly})">' + "\n".join(elements) + "</g>")

    def mid(self, *elements, clip=None, fit=(1, 1)):
        """The nose and mouth, traced as x offsets from the middle and the frame's y: level on the middle line. fit
        shrinks them about the middle where an open mouth runs past his jaw (his head is the anime's closed-mouth
        face)."""
        defs = f'<defs><clipPath id="{self.name}-mouth"><path d="{clip}"/></clipPath></defs>\n' if clip else ""
        self.parts.append(defs)
        sx, sy = self.kx * fit[0], self.ky * fit[1]
        self.group(f"{sx:.5f} 0 0 {sy:.5f} 400 {self.middle_y - sy * self.middle[1]:.3f}", elements)

    def brow(self, brow, half_width, by="width", drop=0, inward=0):
        """A brow (see BROWS) on both eyes, scaled by this frame's eye half-width (or half-height) against its own
        and the eye spacing, mirrored onto the other eye; drop (the brow frame's pixels) lowers it where his built
        bangs would hide it at the frame's height; inward follows eyes moved toward the middle."""
        k = self.kx * (half_width / brow["hw"] if by == "width" else half_width / brow["hh"])
        (ex, ey), d = brow["eye"], smooth(brow["pts"], closed=True)
        ey -= drop
        left, right = (LEFT_EYE[0] - inward, LEFT_EYE[1]), (RIGHT_EYE[0] + inward, RIGHT_EYE[1])
        same, other = (left, right) if brow["over"] == "left" else (right, left)
        self.group(f"{k:.5f} 0 0 {k:.5f} {same[0] - k * ex:.3f} {same[1] - k * ey:.3f}", [f'<path d="{d}" fill="{INK}"/>'])
        self.group(f"{-k:.5f} 0 0 {k:.5f} {other[0] + k * ex:.3f} {other[1] - k * ey:.3f}", [f'<path d="{d}" fill="{INK}"/>'])

    def group(self, matrix, elements):
        self.parts.append(f'<g transform="matrix({matrix})">\n' + "\n".join(elements) + "\n</g>\n")

    def svg(self, note):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">\n'
                f"<!-- Kid Goku, {self.name}: traced over {self.frame} (Dragon Ball Wiki) by scripts/trace_faces.py."
                f" {note} -->\n" + "".join(self.parts) + "</svg>\n")


def clipped(name, *elements):
    return f'<g clip-path="url(#{name}-mouth)">\n' + "\n".join(elements) + "\n</g>"


BROWS = {
    "happy": {"frame": "Goku_reassuring_Mouse_that_all_will_be_well.png", "eye": (461, 325), "hw": 46, "over": "left",
              "pts": [(424, 253), (431, 236), (441.4, 217), (457, 203), (477, 196.4), (487, 197), (500, 203),
                      (511, 210), (518.6, 218.6), (519, 234), (513, 246), (505.7, 224), (494, 213), (480, 211.4),
                      (463, 213), (448.6, 221.4), (434, 237)]},
    "relaxed": {"frame": "An_edit_error_Goku_has_no_Wristbands.jpg", "eye": (518, 258), "hw": 41.5, "hh": 58,
                "over": "left",
                "pts": [(497, 152), (500, 138), (506, 124), (515, 110), (526, 102), (540, 99), (552, 105), (559, 117),
                        (562, 132), (561, 147), (556, 154), (548, 155), (545, 148), (540, 138), (532, 129), (524, 124),
                        (516, 126), (508, 134), (501, 147)]},
    "drowsy": {"frame": "Goku_falling_asleep_due_to_Jackie's_Sleepy_Boy_Technique.png", "eye": (520, 241), "hw": 36,
               "hh": 41, "over": "left",
               "pts": [(521, 159), (527, 150), (535, 141), (542, 136), (550, 132), (560, 130), (569, 141), (571, 150),
                       (572, 161), (570, 165), (564, 167), (559, 164), (557, 152), (553, 147), (547, 146), (541, 148),
                       (534, 152), (527, 158), (522, 164)]},
    "determined": {"frame": "Goku_face_to_face_with_King_Piccolo.png", "eye": (518, 291), "hw": 46, "over": "left",
                   "pts": [(458, 295), (462, 293), (481, 266), (497, 248), (532, 216), (547, 204), (566, 196),
                           (577, 198), (583, 215), (577, 235), (566, 237), (544, 246), (530, 250), (527, 255),
                           (498, 274), (498, 284), (493, 294), (485, 298), (462, 304)]},
    "shout": {"frame": "Goku_angry_at_Bulmas_car.jpg", "eye": (516, 370), "hw": 38, "over": "left",
              "pts": [(492, 328), (507, 312), (525, 297), (546, 283), (570, 284), (579, 287), (589, 290), (599, 297),
                      (591, 306), (593, 315), (589, 323), (580, 319), (568, 308), (560, 304), (540, 303), (523, 313),
                      (510, 327), (499, 333)]},
    "grit": {"frame": "Goku_lunges_at_Giran.png", "eye": (659.65, 240.25), "hw": 56.5, "over": "left",
             "pts": levelled([(593, 246), (600, 234.5), (610, 221.8), (620, 213.8), (630, 204), (640, 195.2), (650, 186.5), (660, 178), (670, 170),
                              (680, 163), (690, 158), (700, 154), (710, 152), (720, 153), (727, 158), (729, 168), (726, 182), (720, 178.8),
                              (710, 174.8), (700, 181.5), (690, 188.5), (683, 191), (675, 188.5), (668, 188), (660, 193.2), (650, 199),
                              (640, 206.5), (630, 214), (620, 222), (610, 230.8), (600, 240.2)], GRIT_MIDDLE, GRIT_TILT)},
    "fierce": {"frame": "Goku_looking_heroic.png", "eye": (514, 336), "hw": 30, "over": "left",
               "pts": [(473.75, 336.25), (487.5, 323.75), (500, 307.5), (512.5, 293.75), (527.5, 281.25), (542.5, 275.75), (557.5, 277.5),
                       (568.75, 283.75), (572, 291.25), (568.75, 300), (560, 301.25), (545, 299.5), (530, 300), (517.5, 302.5), (507.5, 310),
                       (496.25, 321.25), (483.75, 332), (476.25, 337)]},
    "dead": {"frame": "GokuDizzy.png", "eye": (486, 228), "hw": 28, "over": "right",
             "pts": [(472, 185), (469, 179), (474, 166), (477, 160), (486, 152), (496, 145), (509, 156), (516, 177),
                     (512, 186), (507, 182), (507, 177), (505, 169), (502, 164), (495, 158), (484, 166), (479, 172),
                     (480, 177), (477, 187), (474, 188)]},
}


def happy():
    f = Face("happy", "Goku_happy_after_seeing_the_Flying_Nimbus.jpg", (340.5, 378.0), (520.5, 366.5), 580.0,
             (426.25, 517))
    f.eye("right", ellipse(340.5, 378, 60, 71, WHITE), ellipse(392, 396, 9, 14, INK, -8),
          ink([(387, 332), (370, 314), (344, 306.5), (314, 314), (294, 334), (284, 352), (280, 386), (283, 408),
               (290, 424), (306, 440), (322, 447), (337, 449)],
              [0.3, 1.6, 2.4, 2.6, 2.6, 2.4, 2.2, 2.2, 2.2, 2.0, 1.4, 0.3]),
          ink([(266, 453), (272, 447), (281, 445)], [0.4, 1.6, 0.4]),
          ink([(284, 452), (290, 447), (297, 446)], [0.4, 1.4, 0.4]))
    f.eye("left", ellipse(520.5, 366.5, 60.5, 69.5, WHITE), ellipse(468, 391, 9.5, 14, INK, 8),
          ink([(474, 325), (490, 304), (518, 294.5), (550, 302), (570, 320), (581, 356), (580, 392), (570, 416),
               (550, 432), (528, 437)], [0.3, 2.0, 2.4, 2.6, 2.6, 2.4, 2.2, 2.2, 1.8, 0.3]),
          ink([(514, 445), (519, 443.5), (524, 445)], [0.4, 1.2, 0.4]),
          ink([(526, 448), (538, 442), (556, 445)], [0.4, 1.8, 0.4]))
    top = mirrored([(-121.25, 492.5), (-113.75, 477.5), (-101.25, 473.25), (-67.5, 479.25), (-25, 486.75), (0, 488.5)])
    bottom = mirrored([(-121.25, 492.5), (-107.5, 516.25), (-75, 540), (-37.5, 556.25), (0, 562.5)])[::-1]
    mouth = smooth(top + bottom[1:-1], closed=True)
    teeth = mirrored([(-104, 484.5), (-85, 486), (-62.5, 492), (-32, 497), (0, 498.5)])
    tongue = mirrored([(-51.5, 557), (-47, 544), (-38, 536.5), (-20, 533), (-6, 537), (0, 544)])
    f.mid(f'<path d="{mouth}" fill="{MOUTH}"/>',
          clipped("happy", shape(top[2:-2] + teeth[::-1], WHITE), shape(tongue + [(30, 572), (-30, 572)], TONGUE),
                  ink(teeth, [0.6, 1.4, 1.6, 1.6, 1.6, 1.6, 1.6, 1.4, 0.6]),
                  ink(tongue, [0.5, 1.2, 1.4, 1.4, 1.2, 1.0, 1.2, 1.4, 1.4, 1.2, 0.5])),
          ink(top, [1.2, 2.2, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 2.4, 2.2, 1.2]),
          ink(bottom, [1.2, 2.2, 2.4, 2.4, 2.4, 2.4, 2.4, 2.2, 1.2]),
          ink(mirrored([(-7.5, 467.2), (-4, 463.5), (0, 462)]), [0.4, 1.4, 1.6, 1.4, 0.4]), clip=mouth)
    f.brow(BROWS["happy"], 60)
    return f.svg("Brows from Goku_reassuring_Mouse_that_all_will_be_well.png.")


EYES = 0.88
RIGHT_CENTER, LEFT_CENTER = (397.75, 256), (519, 257)
RIGHT_WHITE = [(400, 196), (416, 198), (428, 206), (436, 225), (439.5, 250), (438, 275), (430, 295), (415, 310), (398, 314),
               (380, 311), (366, 301), (358, 286), (355, 267), (356, 250), (360, 231), (368, 214), (381, 202)]
LEFT_WHITE = [(526, 199), (540, 202), (551, 212), (558, 226), (561, 250), (559, 275), (552, 295), (538, 309), (522, 315),
              (505, 313), (490, 303), (481, 285), (477, 262), (478, 240), (484, 222), (497, 207), (511, 200)]
RIGHT_LINE = [(375.75, 308.75), (365, 300), (357.5, 286.25), (354.5, 267.5), (355, 250), (358.75, 231.25), (367.5, 213.75),
              (381.25, 201.25), (400, 195), (416.25, 197.5), (428.75, 206.25), (438, 230)]
LEFT_LINE = [(480, 230), (487.5, 217.5), (500, 205), (512.5, 198.75), (526.25, 197.5), (540, 200.5), (551.25, 211.25),
             (558.75, 225), (562, 250), (560, 275), (552.5, 295), (538.25, 308.75)]
EYE_LINE = [0.4, 1.7, 1.8, 1.8, 1.8, 1.8, 1.8, 1.9, 2.0, 2.0, 1.8, 0.4]
RIGHT_CREASE = ([(351.25, 325), (362.5, 319.25), (375.75, 317)], [0.4, 1.3, 0.4])
LEFT_CREASE = ([(526.25, 319.25), (537.5, 316.25), (548.75, 316.75)], [0.4, 1.3, 0.4])
SHUT = [(-41, -21.5), (-40, -8), (-37, 8), (-30, 23.5), (-17, 37), (0, 42), (17, 37), (30, 23.5), (37, 8), (40, -8), (41, -21.5)]
SHUT_INK = [0.5, 1.5, 2.2, 2.8, 3.2, 3.4, 3.2, 2.8, 2.2, 1.5, 0.5]
HALF_OPEN = 0.56


def at(center, pts):
    return [(center[0] + x, center[1] + y) for x, y in pts]


def relaxed_rest(f, mouth=None):
    """Relaxed's nose, small closed mouth (or this one) and brows, on a Face laid like relaxed's."""
    f.mid(mouth or ink(mirrored([(-12.5, 354.5), (-6, 352.6), (0, 352)]), [0.5, 1.7, 2.1, 1.7, 0.5]),
          ink(mirrored([(-8.75, 326), (-4.5, 322), (0, 320.8)]), [0.4, 1.9, 2.2, 1.9, 0.4]))
    f.brow(BROWS["relaxed"], 43.9, by="height")


def relaxed_face(name):
    return Face(name, "An_edit_error_Goku_has_no_Wristbands.jpg", RIGHT_CENTER, LEFT_CENTER, 405, (455, 353))


def open_eyes(f):
    f.eye("right", shape(RIGHT_WHITE, WHITE), ellipse(431.25, 277, 6.75, 10, INK), ink(RIGHT_LINE, EYE_LINE),
          ink(*RIGHT_CREASE), size=EYES)
    f.eye("left", shape(LEFT_WHITE, WHITE), ellipse(483.75, 278, 6.5, 9.5, INK), ink(LEFT_LINE, EYE_LINE), ink(*LEFT_CREASE),
          size=EYES)


def relaxed():
    f = relaxed_face("relaxed")
    open_eyes(f)
    relaxed_rest(f)
    return f.svg("Its own brows.")


def smile():
    f = relaxed_face("smile")
    open_eyes(f)
    relaxed_rest(f, ink(mirrored([(-36, 336), (-27, 345), (-15, 351), (0, 354)]), [0.5, 1.7, 2.1, 2.3, 2.1, 1.7, 0.5]))
    return f.svg("Its mouth from Goku_after_drinking_the_juice.jpg, on relaxed's eyes.")


def lowered(pts, center):
    """An eye's points with its top brought down toward its bottom, which stays put."""
    bottom = center[1] + 58
    return [(x, bottom - (bottom - y) * HALF_OPEN) for x, y in pts]


def blink_half():
    f = relaxed_face("blink_half")
    f.eye("right", shape(lowered(RIGHT_WHITE, RIGHT_CENTER), WHITE), ellipse(431.25, 277, 6.75, 10, INK),
          ink(lowered(RIGHT_LINE, RIGHT_CENTER), EYE_LINE), ink(*RIGHT_CREASE), size=EYES)
    f.eye("left", shape(lowered(LEFT_WHITE, LEFT_CENTER), WHITE), ellipse(483.75, 278, 6.5, 9.5, INK),
          ink(lowered(LEFT_LINE, LEFT_CENTER), EYE_LINE), ink(*LEFT_CREASE), size=EYES)
    relaxed_rest(f)
    return f.svg("Relaxed's face, its lids partway down.")


def blink():
    f = relaxed_face("blink")
    f.eye("right", ink(at(RIGHT_CENTER, SHUT), SHUT_INK), ink(*RIGHT_CREASE), size=EYES)
    f.eye("left", ink(at(LEFT_CENTER, SHUT), SHUT_INK), ink(*LEFT_CREASE), size=EYES)
    relaxed_rest(f)
    return f.svg("Relaxed's face, its eyes shut as Yamcha_Seeing_Goku_Asleep.jpg draws them.")


def determined():
    f = Face("determined", "Goku_face_to_face_with_King_Piccolo.png", (379, 295), (518, 291), 425, (450, 368))
    left = [shape([(470, 296), (490, 285), (500, 268), (518, 252), (538, 246), (552, 248), (562, 262), (567, 282),
                   (565, 302), (556, 318), (540, 330), (518, 334), (498, 330), (484, 318), (474, 306)], WHITE),
            ink([(562, 259), (567, 280), (566, 297), (557, 315), (545, 327), (522, 333), (500, 332)],
                [0.4, 1.6, 1.8, 1.8, 1.8, 1.6, 0.4])]
    f.mirror_eye(*left, ellipse(492, 292, 8, 10, INK))
    f.eye("left", *left, ellipse(466, 292, 8, 10, INK),
          ink([(515, 343), (525, 337), (535, 335)], [0.4, 1.2, 0.4]),
          ink([(530, 342), (542, 335), (555, 333)], [0.4, 1.2, 0.4]),
          ink([(545, 340), (558, 333), (570, 332)], [0.4, 1.2, 0.4]))
    f.eye("right", ink([(332, 356), (342, 350), (352, 348)], [0.4, 1.2, 0.4]),
          ink([(347, 358), (358, 351), (368, 349)], [0.4, 1.2, 0.4]),
          ink([(362, 359), (374, 352), (385, 351)], [0.4, 1.2, 0.4]))
    f.mid(ink([(-35, 376), (-25, 379), (-10, 377), (10, 373), (30, 367), (43, 362), (48, 356)],
              [0.5, 1.8, 2.0, 2.0, 2.0, 1.8, 0.5]),
          ink(mirrored([(-9, 358), (-4, 349), (0, 347)]), [0.4, 1.8, 2.0, 1.8, 0.4]))
    f.brow(BROWS["determined"], 46)
    return f.svg("Its own brows.")


def shout():
    f = Face("shout", "Goku_angry_at_Bulmas_car.jpg", (403, 366), (517, 368), 505, (456, 448))
    f.eye("right", ellipse(403, 366, 39, 40, WHITE), ellipse(433, 358, 8, 11, INK),
          ink([(449, 347), (437, 338), (424, 330), (408, 325), (392, 326), (378, 334), (368, 348), (362, 368),
               (366, 386), (376, 397), (383, 400)], [0.4, 2.2, 2.6, 2.8, 2.8, 2.6, 2.4, 2.4, 2.2, 1.6, 0.4]),
          ink([(360, 411), (370, 407), (380, 407), (390, 409)], [0.4, 1.6, 1.6, 0.4]),
          ink([(366, 416), (375, 413), (384, 414)], [0.4, 1.2, 0.4]))
    f.eye("left", ellipse(517, 368, 40, 42, WHITE), ellipse(485, 360, 7, 9, INK),
          ink([(477, 345), (488, 335), (500, 330), (520, 326), (537, 331), (550, 342), (556, 360), (556, 380),
               (550, 395), (537, 406), (522, 410)], [0.4, 2.2, 2.6, 2.8, 2.8, 2.6, 2.4, 2.4, 2.2, 1.6, 0.4]),
          ink([(511, 414), (519, 410), (527, 409), (536, 410), (545, 411)], [0.4, 1.6, 1.6, 1.4, 0.4]),
          ink([(522, 418), (531, 415), (540, 416)], [0.4, 1.2, 0.4]))
    top = mirrored([(-72, 438), (-66.5, 426), (-50, 423), (-25, 426.5), (0, 428)])
    bottom = mirrored([(-72, 438), (-67.5, 453.5), (-57.5, 463.5), (-39, 469), (-12.5, 471), (0, 472)])[::-1]
    mouth = smooth(top + bottom[1:-1], closed=True)
    upper = mirrored([(-62, 435), (-40, 438.5), (-12, 441), (0, 441)])
    lower = mirrored([(-63, 456.5), (-34, 462), (-12, 464.5), (0, 465)])
    tongue = mirrored([(-26, 463), (-23, 456), (-14, 452), (-4, 454), (0, 456)])
    f.mid(f'<path d="{mouth}" fill="{MOUTH}"/>',
          clipped("shout", shape(top[1:-1] + upper[::-1], WHITE), shape(tongue + [(20, 470), (-20, 470)], TONGUE),
                  shape(lower + bottom[1:-1], WHITE),
                  ink(upper, [0.5, 1.6, 1.8, 1.8, 1.8, 1.6, 0.5]), ink(lower, [0.5, 1.6, 1.8, 1.8, 1.8, 1.6, 0.5]),
                  ink(tongue, [0.4, 1.2, 1.4, 1.2, 1.0, 1.2, 1.4, 1.2, 0.4])),
          ink(top, [1.4, 2.6, 2.8, 2.8, 2.8, 2.8, 2.8, 2.6, 1.4]),
          ink(bottom, [1.4, 2.6, 2.8, 2.8, 2.8, 2.8, 2.8, 2.8, 2.8, 2.6, 1.4]),
          ink(mirrored([(-6, 418), (-3, 415.5), (0, 415)]), [0.4, 1.8, 2.0, 1.8, 0.4]),
          *(ink([(x, 330), (x - 1, 340), (x, 349)], [0.4, 1.6, 0.4]) for x in (-4, 3, 10)))
    f.brow(BROWS["shout"], 39)
    return f.svg("Its own brows.")


def half():
    f = Face("half", "Goku_wants_to_eat_now.jpg", (371, 327), (521, 329), 520, (441, 470))
    f.eye("right", shape([(320, 357), (350, 342), (400, 332), (424, 331), (426, 345), (422, 362), (412, 376),
                          (395, 386), (375, 389), (352, 386), (334, 378), (325, 368)], WHITE),
          shape([(409, 331), (425, 330), (424, 336), (418, 340), (412, 338)], INK),
          ink([(336, 381), (327, 372), (320, 360), (316, 340), (317, 320), (320, 300), (330, 280), (345, 269),
               (365, 265), (385, 266), (397, 270)], [0.4, 1.4, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.4, 0.4]),
          ink([(314, 359), (330, 351), (350, 342), (375, 336), (400, 332), (424, 330)], [0.6, 2.2, 2.6, 2.8, 2.8, 2.4]),
          ink([(320, 409), (332, 402), (345, 401), (355, 399)], [0.4, 1.4, 1.4, 0.4]))
    f.eye("left", shape([(468, 332), (500, 334), (527, 339), (552, 346), (574, 352), (568, 368), (555, 382),
                         (535, 389), (515, 390), (495, 386), (478, 376), (469, 360)], WHITE),
          shape([(469, 332), (486, 334), (485, 340), (479, 343), (472, 341)], INK),
          ink([(472, 312), (482, 297), (495, 282), (512, 271), (530, 269), (550, 274), (565, 285), (572, 300),
               (575, 320), (575, 342), (570, 365), (557, 380), (547, 386)],
              [0.4, 1.4, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.4, 0.4]),
          ink([(469, 332), (500, 334), (527, 339), (552, 346), (575, 352)], [2.4, 2.8, 2.8, 2.6, 0.6]),
          ink([(525, 402), (535, 397), (545, 398), (552, 401)], [0.4, 1.4, 1.4, 0.4]))
    top = mirrored([(-39.5, 471), (-31, 464.5), (-18, 462.5), (0, 464)])
    bottom = mirrored([(-39.5, 471), (-36, 473.5), (-20, 474), (0, 474.5)])[::-1]
    f.mid(shape(top + bottom[1:-1], MOUTH),
          shape([(-30, 471), (-15, 468.5), (0, 469), (15, 468.5), (30, 471), (15, 472), (0, 472.5), (-15, 472)],
                TONGUE),
          ink(top, [0.8, 2.0, 2.4, 2.4, 2.4, 2.0, 0.8]), ink(bottom, [0.8, 2.0, 2.4, 2.4, 2.4, 2.0, 0.8]),
          ink(mirrored([(-11, 409), (-5, 403.5), (0, 402.5)]), [0.4, 2.0, 2.2, 2.0, 0.4]))
    f.brow(BROWS["drowsy"], 54.5, drop=24)
    return f.svg("Brows from Goku_falling_asleep_due_to_Jackie's_Sleepy_Boy_Technique.png.")


def surprised():
    f = Face("surprised", "Goku_asking_Bulma_where_there_going.jpg", (372, 369), (537.5, 364), 563, (461, 500))
    f.eye("right", ellipse(372, 369, 55, 63, WHITE), ellipse(417, 368.5, 12, 16, INK),
          ink([(368, 306), (340, 315), (322.5, 337.5), (317.5, 362.5), (320, 390), (330, 415), (350, 429),
               (372.5, 432.5)], [0.4, 1.8, 2.0, 2.0, 2.0, 2.0, 1.8, 0.4]),
          ink([(328, 441), (340, 435), (355, 433), (368, 434)], [0.4, 1.4, 1.4, 0.4]))
    f.eye("left", ellipse(537.5, 364, 52, 64, WHITE), ellipse(493.5, 364, 9, 16, INK),
          ink([(525, 300), (560, 307), (585, 330), (591, 362.5), (585, 400), (565, 422.5), (540, 427.5)],
              [0.4, 1.8, 2.0, 2.0, 2.0, 1.8, 0.4]),
          ink([(527, 436), (540, 432), (552, 433), (562, 437)], [0.4, 1.4, 1.4, 0.4]))
    edge = mirrored([(0, 466), (-12, 468), (-22, 476), (-27, 490), (-28, 505), (-24, 520), (-14, 530), (0, 533.5)][::-1])
    mouth = smooth(edge[:-1], closed=True)
    teeth = mirrored([(-15, 472), (-8, 476.5), (0, 478)])
    tongue = mirrored([(-25, 509), (-14, 504), (-5, 506), (0, 510)])
    f.mid(f'<path d="{mouth}" fill="{MOUTH}"/>',
          clipped("surprised", shape([(-20, 465)] + teeth + [(20, 465)], WHITE),
                  shape(tongue + [(28, 540), (-28, 540)], TONGUE),
                  ink(teeth, [0.4, 1.4, 1.6, 1.4, 0.4]), ink(tongue, [0.4, 1.2, 1.2, 1.0, 1.2, 1.2, 0.4])),
          f'<path class="ink" d="{mouth}" data-w="{" ".join(["2.4"] * 15)}" fill="none" stroke="{INK}" '
          f'stroke-width="2.4" stroke-linecap="round"/>',
          ink(mirrored([(-7.5, 439.5), (-3.5, 436), (0, 435.5)]), [0.4, 1.8, 2.0, 1.8, 0.4]),
          clip=mouth, fit=(0.81, 1))
    f.brow(BROWS["happy"], 55)
    return f.svg("Brows from Goku_reassuring_Mouse_that_all_will_be_well.png.")


def closed():
    f = Face("closed", "Goku_tells_Bulma_what_he_did_with_her_panties.jpg", (399, 350), (497, 350), 505, (451, 443))
    f.eye("right", ink([(372.5, 380.5), (371, 365), (374, 345), (380, 327.5), (389, 317.5), (397.5, 315),
                        (406, 319), (414, 330), (420, 347.5), (425, 365), (426, 376)],
                       [0.4, 1.6, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.6, 0.4]),
          ink([(355, 395), (363, 392), (370, 391.5), (376, 392)], [0.4, 1.3, 1.3, 0.4]))
    f.eye("left", ink([(470, 374), (470.5, 357.5), (474, 340), (481, 322.5), (492.5, 312), (500, 311), (510, 315),
                       (517.5, 327.5), (522.5, 345), (524.5, 365), (524, 379)],
                      [0.4, 1.6, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.6, 0.4]),
          ink([(500, 387), (512, 386), (526, 389), (540, 394)], [0.4, 1.3, 1.3, 0.4]))
    top = mirrored([(-91, 426.7), (-81, 410), (-64, 406.7), (-31, 415), (0, 416.7)])
    bottom = mirrored([(-91, 426.7), (-84, 446.7), (-57.7, 468.3), (-31, 476.7), (0, 479.3)])[::-1]
    mouth = smooth(top + bottom[1:-1], closed=True)
    tongue = mirrored([(-86, 437), (-70, 420), (-40, 419), (0, 421)])
    f.mid(f'<path d="{mouth}" fill="{MOUTH}"/>',
          clipped("closed", shape(tongue + [(90, 490), (-90, 490)], TONGUE),
                  ink(tongue, [0.4, 1.2, 1.4, 1.4, 1.4, 1.2, 0.4])),
          ink(top, [1.2, 2.2, 2.4, 2.4, 2.4, 2.4, 2.4, 2.2, 1.2]),
          ink(bottom, [1.2, 2.2, 2.4, 2.4, 2.4, 2.4, 2.4, 2.2, 1.2]),
          ink(mirrored([(-7, 392), (-3.5, 387.5), (0, 386.5)]), [0.4, 1.8, 2.0, 1.8, 0.4]),
          clip=mouth, fit=(0.72, 1.15))
    f.brow(BROWS["relaxed"], 35.6, by="height")
    return f.svg("Brows as relaxed's.")


def spiral(cx, cy, r, turns=2.75):
    """A dizzy eye: a white disc, its outline and a spiral wound in from it, as GokuDizzy.png draws them (that frame
    is small and soft, so the spiral is drawn clean at its size, not traced stroke by stroke)."""
    w = r * 0.065
    ring = [(cx + r * math.cos(a / 18 * math.pi), cy + r * math.sin(a / 18 * math.pi)) for a in range(38)]
    n = int(turns * 18)
    coil = [(cx + r * (0.12 + 0.73 * i / n) * math.cos(i / 9 * math.pi + 1.2),
             cy + r * (0.12 + 0.73 * i / n) * math.sin(i / 9 * math.pi + 1.2)) for i in range(n + 1)]
    return [ellipse(cx, cy, r, r, WHITE), ink(ring, [w] * len(ring)),
            ink(coil, [0.3] + [w] * (len(coil) - 2) + [0.4])]


def level_symmetric(pts, angle, center, n=13):
    """A curve traced on a tilted head (left to right), turned level about center and made symmetric: offsets
    from center's x, its height at each the average of the curve's at x and -x, as the other mouths are."""
    c, s_ = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    lv = sorted(((x - center[0]) * c + (y - center[1]) * s_, -(x - center[0]) * s_ + (y - center[1]) * c + center[1])
                for x, y in pts)

    def at(x):
        x = min(max(x, lv[0][0]), lv[-1][0])
        for (x0, y0), (x1, y1) in zip(lv, lv[1:]):
            if x <= x1:
                return y0 + (y1 - y0) * (x - x0) / ((x1 - x0) or 1)
        return lv[-1][1]
    half = min(-lv[0][0], lv[-1][0])
    xs = [-half + 2 * half * i / (n - 1) for i in range(n)]
    return [(round(x, 1), round((at(x) + at(-x)) / 2, 1)) for x in xs]


def dead():
    tilt, c = 25.8, (495, 305)
    f = Face("dead", "GokuDizzy.png", (448, 208), (548, 258), 355, c)
    f.eye("right", *spiral(448, 208, 29))
    f.eye("left", *spiral(548, 258, 29))
    top = level_symmetric([(408.75, 290), (412.5, 267.5), (422.5, 253.75), (440, 251.25), (450, 253.75),
                           (465, 267.5), (475, 282.5), (495, 296.25), (515, 295.5), (540, 295.5), (560, 302.5),
                           (575, 315), (578.75, 330), (577.5, 342.5)], tilt, c)
    bottom = level_symmetric([(408.75, 290), (413.75, 301), (425, 310), (445, 320), (465, 332.5), (485, 340),
                              (507.5, 350), (530, 360), (550, 367.5), (562.5, 366), (575, 355), (577.5, 342.5)],
                             tilt, c)
    upper = level_symmetric([(415, 270), (440, 262), (453.75, 267.5), (462.5, 277.5), (475, 283.75), (497.5, 298.75),
                             (520, 305), (540, 307.5), (555, 312.5), (565, 321), (575, 325)], tilt, c)
    lower = level_symmetric([(415, 292.5), (427.5, 302.5), (447.5, 310), (462.5, 315), (477.5, 327.5),
                             (497.5, 335), (520, 345), (540, 355), (550, 362.5)], tilt, c)
    mouth = smooth(top + bottom[::-1][1:-1], closed=True)
    tongue = level_symmetric([(440, 302.5), (465, 307.5), (490, 315), (505, 327.5)], tilt, (472.5, 315), n=7)
    lift = sum(y for _, y in tongue) / len(tongue) - (sum(y for _, y in lower) / len(lower)) + 4
    tongue = [(x * 0.6, y - lift) for x, y in tongue]
    f.mid(f'<path d="{mouth}" fill="{MOUTH}"/>',
          clipped("dead", shape(top[1:-1] + upper[::-1][1:-1], WHITE), shape(lower[1:-1] + bottom[::-1][1:-1], WHITE),
                  shape(tongue + [(t[0], t[1] + 30) for t in tongue[::-1]], TONGUE),
                  ink(upper, [0.5] + [1.6] * 11 + [0.5]), ink(lower, [0.5] + [1.6] * 11 + [0.5]),
                  ink(tongue, [0.4] + [1.3] * 5 + [0.4])),
          ink(top, [1.2] + [2.4] * 11 + [1.2]), ink(bottom, [1.2] + [2.4] * 11 + [1.2]),
          ink(mirrored([(-5, 266), (-2.5, 262), (0, 261)]), [0.4, 1.8, 2.0, 1.8, 0.4]),
          clip=mouth, fit=(0.85, 0.85))
    f.brow(BROWS["dead"], 29)
    return f.svg("Spiral eyes, brows and mouth from GokuDizzy.png.")


def grit():
    def lv(pts):
        return levelled(pts, GRIT_MIDDLE, GRIT_TILT)
    outline = lv([(450, 299), (467, 288), (485, 287), (500, 292), (522, 304), (550, 317), (570, 326), (585, 330), (605, 329), (630, 327), (650, 330),
                  (670, 336), (682, 345), (687, 356), (687, 375), (682, 395), (672, 412), (660, 425), (645, 428), (625, 425), (605, 417), (585, 409),
                  (565, 402), (545, 399), (520, 398), (495, 399), (470, 396), (450, 391), (437, 380), (428, 360), (430, 325), (440, 310)])
    xs, ys = [x for x, _ in outline], [y for _, y in outline]
    middle = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    f = Face("grit", "Goku_lunges_at_Giran.png", (518.85, 240.25), (659.65, 240.25), 462.25, middle)

    eye = (659.65, 240.25)
    pupil = lv([(623.5, 242)])[0]
    white = lv([(602, 236.5), (610, 228.8), (620, 220), (630, 212), (640, 204.5), (650, 197), (657, 195.5), (665, 197.5), (680, 198), (692, 203), (702, 213), (709, 225), (714, 240),
                (715, 257), (712.5, 272), (707, 285), (698, 297), (687, 305), (677, 309), (668, 309), (650, 305), (633, 295), (620, 280),
                (612, 263), (606, 248)])
    left = [shape(white, WHITE),
            ink(lv([(665, 197.5), (680, 198), (692, 203), (702, 213), (709, 225), (714, 240), (715, 257), (712.5, 272), (707, 285), (698, 297),
                    (687, 305), (677, 309), (668, 308)]), [0.4, 1.4, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6, 1.5, 1.2, 0.4]),
            ellipse(pupil[0], pupil[1], 9.5, 16, INK),
            ink(lv([(663, 324), (672, 319), (683, 321)]), [0.4, 1.4, 0.4]), ink(lv([(674, 329), (686, 324), (699, 330)]), [0.4, 1.4, 0.4])]
    f.eye("right", f'<g transform="matrix(-1 0 0 1 {2 * GRIT_MIDDLE[0]} 0)">' + "\n".join(left) + "</g>", size=GRIT_EYES)
    f.eye("left", *left, size=GRIT_EYES)

    def mid(pts):
        return [(round(x - middle[0], 2), y) for x, y in lv(pts)]
    teeth = mid([(450, 299), (467, 288), (485, 287), (500, 292), (522, 304), (550, 317), (570, 326), (585, 330), (605, 329), (630, 327), (650, 330),
                 (670, 336), (679, 346), (677, 362), (679, 378), (670, 398), (661, 420), (645, 428), (625, 425), (605, 417), (585, 409), (565, 402),
                 (545, 399), (520, 398), (495, 399), (470, 396), (452, 390), (441, 378), (438, 360), (446, 342), (441, 322)])
    gap = mid([(447, 344), (465, 344.5), (485, 345), (497, 344), (515, 349), (530, 348), (550, 352), (570, 359), (590, 358), (600, 364),
               (620, 370), (635, 372), (642, 377), (655, 381), (670, 375), (678, 370)])
    ticks = [mid(t) for t in ([(458, 329), (462, 340), (470, 343.5)], [(450, 350), (449.5, 356), (450, 362)], [(468, 350), (465, 360), (464, 370)],
                              [(496, 345), (493, 354), (490, 362)], [(650, 380), (650.5, 392), (650, 405)], [(662, 385), (664, 393), (665, 400)])]
    edge = [(round(x - middle[0], 2), y) for x, y in outline]
    scale = GRIT_MOUTH * MOUTH_WIDTH / (max(xs) - min(xs))
    eyes = f.kx * GRIT_EYES
    nose = RIGHT_EYE[1] + eyes * (lv([(590, 277)])[0][1] - eye[1])
    f.group(f"{eyes:.5f} 0 0 {eyes:.5f} 400 {nose:.3f}", [ink(mirrored([(-9.5, 6.5), (-5, 1.5), (0, 0)]), [0.4, 1.6, 1.8, 1.6, 0.4])])
    f.brow(BROWS["grit"], 56.5 * GRIT_EYES)
    f.parts = [f'<g transform="translate(0 {-GRIT_LIFT})">\n', *f.parts, "</g>\n"]
    under = RIGHT_EYE[1] - GRIT_LIFT + eyes * (max(y for _, y in white) - eye[1])
    tall = scale * (max(ys) - min(ys))
    above, below = min(ys) - max(y for _, y in white), 462.25 - max(ys)
    room = CHIN - under - tall
    assert room > 0, room
    f.middle_y = under + room * above / (above + below) + tall / 2
    f.mid(shape(edge, INK), shape(teeth, WHITE),
          ink(gap, [0.5] + [1.5] * 14 + [0.5]), *(ink(t, [1.3, 1.2, 0.4]) for t in ticks),
          ink(edge + [edge[0]], [2.2] * 33), fit=(scale / f.kx, scale / f.ky))
    print(f"grit: eyes {GRIT_EYES} of the frame's, mouth {scale / f.kx:.2f} of the frame's across (kept in shape), {room:.0f} px of room round the mouth",
          file=sys.stderr)
    return f.svg("Its own brows.")


def fierce():
    f = Face("fierce", "Goku_looking_heroic.png", (417.5, 331), (514, 336), 426, (468, 388))
    f.eye("right", shape([(417.5, 301), (432.5, 312.5), (447, 324.5), (454, 334), (453.5, 347), (446, 358), (435, 362), (423.75, 363), (413.75, 362.5),
                          (401.25, 357.5), (390, 346), (383, 330), (385, 317.5), (393.75, 305.5), (405, 301)], WHITE),
          ellipse(446.25, 339.25, 6, 8.5, INK),
          ink([(417.5, 300.5), (405, 301), (393.75, 305.5), (385, 317.5), (383, 330), (390, 346), (401.25, 357.5), (413.75, 362.5), (423.75, 363)],
              [0.4, 1.6, 1.8, 1.8, 1.8, 1.8, 1.8, 1.6, 0.4]),
          ink([(392.5, 370), (400, 369.25), (408.75, 372)], [0.4, 1.6, 0.4]))
    f.eye("left", shape([(483.75, 339), (490, 327), (497, 320), (507.5, 311), (520, 308), (530, 310), (540, 320), (544.5, 332.5), (541.25, 347.5),
                         (530, 359.5), (520, 363.75), (507.5, 364), (497, 359), (488.5, 352), (484, 345)], WHITE),
          ellipse(490.75, 342.5, 6.5, 8, INK),
          ink([(520, 308.75), (530, 310), (540, 320), (544.5, 332.5), (541.25, 347.5), (530, 359.5), (520, 363.75), (507.5, 363.75)],
              [0.4, 1.6, 1.8, 1.8, 1.8, 1.8, 1.6, 0.4]),
          ink([(522.75, 377), (531.5, 374.25), (539, 375)], [0.4, 1.6, 0.4]))
    f.mid(ink(mirrored([(-19.5, 392), (-10, 389.3), (0, 388)]), [0.5, 1.4, 1.6, 1.4, 0.5]),
          ink(mirrored([(-8.5, 374.8), (-4.5, 370.3), (0, 368.8)]), [0.4, 1.6, 1.8, 1.6, 0.4]),
          *(ink([(side * 6.5, 325), (side * 6, 329), (side * 7, 334)], [0.4, 1.3, 0.4]) for side in (-1, 1)))
    f.brow(BROWS["fierce"], 30)
    return f.svg("Its own brows.")








def yell(name="yell", pupils=((433, 358, 8, 11), (485, 360, 7, 9))):
    f = Face(name, "Goku_angry_at_Bulmas_car.jpg", (403, 366), (517, 368), 505, (456, 448))
    f.eye("right", ellipse(403, 366, 39, 40, WHITE), ellipse(*pupils[0], INK),
          ink([(449, 347), (437, 338), (424, 330), (408, 325), (392, 326), (378, 334), (368, 348), (362, 368),
               (366, 386), (376, 397), (383, 400)], [0.4, 2.2, 2.6, 2.8, 2.8, 2.6, 2.4, 2.4, 2.2, 1.6, 0.4]),
          ink([(360, 411), (370, 407), (380, 407), (390, 409)], [0.4, 1.6, 1.6, 0.4]),
          ink([(366, 416), (375, 413), (384, 414)], [0.4, 1.2, 0.4]))
    f.eye("left", ellipse(517, 368, 40, 42, WHITE), ellipse(*pupils[1], INK),
          ink([(477, 345), (488, 335), (500, 330), (520, 326), (537, 331), (550, 342), (556, 360), (556, 380),
               (550, 395), (537, 406), (522, 410)], [0.4, 2.2, 2.6, 2.8, 2.8, 2.6, 2.4, 2.4, 2.2, 1.6, 0.4]),
          ink([(511, 414), (519, 410), (527, 409), (536, 410), (545, 411)], [0.4, 1.6, 1.6, 1.4, 0.4]),
          ink([(522, 418), (531, 415), (540, 416)], [0.4, 1.2, 0.4]))
    f.mid(ink(mirrored([(-6, 418), (-3, 415.5), (0, 415)]), [0.4, 1.8, 2.0, 1.8, 0.4]),
          *(ink([(x, 330), (x - 1, 340), (x, 349)], [0.4, 1.6, 0.4]) for x in (-4, 3, 10)))
    pressed = {**BROWS["shout"], "pts": [(464, 356), (478, 334), (490, 320), (503, 309), (520, 299), (545, 290), (570, 282), (596, 279), (600, 286), (592, 295), (572, 303), (545, 315),
                                         (520, 325), (503, 331), (490, 338), (478, 346)]}
    f.brow(pressed, 39)
    ring = [(160, 600), (167, 570), (183, 543), (212, 512), (233, 502), (260, 499), (300, 503), (350, 507), (400, 505), (450, 502), (500, 495), (543, 493), (580, 496),
            (607, 507), (623, 533), (638, 560), (642, 587), (633, 603), (610, 623), (577, 635), (517, 643), (450, 644), (400, 644), (317, 647), (250, 653), (217, 647), (173, 630), (162, 617)]
    up = [(212, 518), (220, 532), (237, 540), (263, 540), (300, 540), (350, 542), (400, 537), (460, 533), (517, 538), (560, 538), (593, 530), (610, 518)]
    tongue = [(252, 615), (250, 597), (263, 578), (283, 565), (310, 558), (337, 559), (367, 565), (382, 570), (407, 562), (433, 553), (463, 550), (497, 553), (523, 565), (547, 583), (563, 605)]
    low = [(175, 623), (188, 603), (200, 598), (213, 577), (222, 565), (237, 560), (250, 565), (258, 577), (247, 600), (240, 614), (275, 626), (310, 621), (350, 626), (400, 618), (450, 618),
           (517, 615), (563, 605), (547, 573), (555, 555), (580, 548), (597, 553), (615, 573), (630, 583), (638, 593)]
    x0, x1, y0, y1 = 160, 642, 493, 653
    k = 270 / (x1 - x0)
    top, pen = 572, 5

    def place(pts):
        return [(400 + (x - (x0 + x1) / 2) * k, top + (y - y0) * k) for x, y in pts]
    outer, up, tongue, low = place(ring), place(up), place(tongue), place(low)
    tips = lambda p: [0.6] + [pen] * (len(p) - 2) + [0.6]
    mouth = smooth(outer, closed=True)

    def closed(curve, fill, *rest):
        return f'<path d="{smooth(curve)} ' + " ".join(f"L{a:.1f},{b:.1f}" for a, b in rest) + f' Z" fill="{fill}"/>'
    f.parts.append(f'<defs><clipPath id="{name}-mouth"><path d="{mouth}"/></clipPath></defs>\n')
    f.group("1 0 0 1 0 0", [f'<path d="{mouth}" fill="{MOUTH}"/>',
                            clipped(name, closed(tongue, TONGUE, (tongue[-1][0], top + 240), (tongue[0][0], top + 240)),
                                    closed(low, WHITE, (low[-1][0] + 80, top + 240), (low[0][0] - 80, top + 240)),
                                    closed(up, WHITE, (up[-1][0] + 80, top - 80), (up[0][0] - 80, top - 80)),
                                    ink(tongue, tips(tongue)), ink(low, tips(low)), ink(up, tips(up))),
                            ink(outer + outer[:1], [pen] * (len(outer) + 1))])
    return f.svg("His mouth from the Kamehameha frame, its eyes shout's." + (" Its pupils glance to his side." if name != "yell" else ""))


def yell_left():
    """yell glancing hard to his left, at what he's kicking (the side kick still): its pupils three-fifths across each
    eye toward his left and a little low."""
    return yell("yell_left", ((426, 370, 8, 11), (541, 372, 7, 9)))


def yell_right():
    """yell_left mirrored, for the side kick on his right leg: its pupils three-fifths across each eye toward his right."""
    return yell("yell_right", ((380, 370, 8, 11), (493, 372, 7, 9)))


CHEER_EYES, CHEER_MOUTH = 0.8, 1.12
CHEER_TOP = 95


def cheer():
    f = Face("cheer", "GokuThisTime.Ep.079.png", (408, 322), (508, 322), 470, (460, 418))
    f.eye("right", ink([(389, 352), (391, 330), (396, 308), (405, 294), (412, 292), (419, 300), (425, 320), (427.5, 354)],
                       [0.3, 1.2, 1.3, 1.3, 1.3, 1.3, 1.2, 0.3]),
          ink([(347, 362), (360, 360), (373, 362)], [0.3, 0.9, 0.3]), size=(1, CHEER_EYES))
    f.eye("left", ink([(489, 354), (492, 330), (498, 310), (507.5, 296), (515, 294), (522, 300), (527, 320), (528.5, 350)],
                      [0.3, 1.2, 1.3, 1.3, 1.3, 1.3, 1.2, 0.3]),
          ink([(535, 362), (550, 360), (565, 362)], [0.3, 0.9, 0.3]), size=(1, CHEER_EYES))
    tall = f.kx * CHEER_EYES
    lift = CHEER_TOP - tall * (322 - 292)
    f.parts = [f'<g transform="translate(0 {-lift:.1f})">\n', *f.parts, "</g>\n"]
    ends = RIGHT_EYE[1] - lift + tall * (354 - 322)
    nose = ends + f.kx * 16
    f.middle_y = nose + f.ky * (418 - 370)
    f.mid(ink(mirrored([(-9, 375), (-4.5, 371), (0, 370)]), [0.3, 1.2, 1.3, 1.2, 0.3]))
    top = mirrored([(-97.5, 400), (-85, 386), (-60, 383), (-35, 390), (0, 395)])
    bottom = mirrored([(-97.5, 400), (-92.5, 417), (-75, 435), (-45, 447.5), (-10, 451), (0, 451)])[::-1]
    mouth = smooth(top + bottom[1:-1], closed=True)
    gap = mirrored([(-90, 405), (-60, 412.5), (-20, 417.5), (0, 418.5)])
    scale = CHEER_MOUTH * MOUTH_WIDTH / 195
    f.middle_y = nose + f.ky * (375 - 370) + f.kx * 8 * 0.6 + scale * (418 - 383)
    f.mid(f'<path d="{mouth}" fill="{WHITE}"/>', ink(gap, [0.4, 1.2, 1.3, 1.3, 1.3, 1.2, 0.4]),
          *(ink([(x, y - 3), (x, y + 4)], [0.8, 0.8]) for x, y in ((-80, 408), (-60, 412), (-18, 418), (18, 418), (60, 412), (80, 408))),
          ink(top, [1.0] + [1.8] * 7 + [1.0]), ink(bottom, [1.0] + [1.8] * 9 + [1.0]),
          fit=(scale / f.kx, scale / f.ky))
    f.brow(BROWS["relaxed"], 35.6, by="height")
    print(f"cheer: arcs {tall * 62:.0f} px tall, ending {ends - RIGHT_EYE[1]:+.0f} from his eye line; nose at {nose - RIGHT_EYE[1]:+.0f}; mouth "
          f"{CHEER_MOUTH * MOUTH_WIDTH:.0f} px wide, {f.middle_y - scale * 35 - RIGHT_EYE[1]:+.0f} to {f.middle_y + scale * 33 - RIGHT_EYE[1]:+.0f}; "
          f"his chin is at {CHIN - RIGHT_EYE[1]:+.0f}", file=sys.stderr)
    return f.svg("Brows as relaxed's.")


FACES = {"happy": happy, "relaxed": relaxed, "determined": determined, "shout": shout, "half": half,
         "surprised": surprised, "closed": closed, "dead": dead, "blink_half": blink_half, "blink": blink, "smile": smile,
         "grit": grit, "fierce": fierce, "yell": yell, "cheer": cheer, "yell_left": yell_left, "yell_right": yell_right}


def main() -> int:
    os.makedirs(ART, exist_ok=True)
    for name in sys.argv[1:] or FACES:
        svg = FACES[name]()
        with open(os.path.join(ART, f"{name}.svg"), "w") as out:
            out.write(svg)
        print("wrote", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
