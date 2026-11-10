"""Finds a 3D reference's joints: a body detector (RTMPose, through rtmlib) on each of reference_renders.py's lit
views, triangulated through the views' known cameras. The detector misses limbs on flat anime stills, but a lit 3D
figure seen all round is what it was trained on; a joint seen from many cameras is placed by the views that agree.

Usage (a Python with rtmlib, onnxruntime, opencv-python and numpy):
  python scripts/reference_joints.py RENDERS_DIR OUT.json [--sheet SHEET.jpg]

Which side is his right comes from the body, not the detector's labels: his right is to the right of where his face
points, and both sides' chains are kept whole (shoulder to wrist, hip to ankle).
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np
from rtmlib import Body

PAIRS = [("shoulder", 5, 6), ("elbow", 7, 8), ("wrist", 9, 10), ("hip", 11, 12), ("knee", 13, 14), ("ankle", 15, 16),
         ("ear", 3, 4), ("eye", 1, 2)]
MIDDLE = [("nose", 0)]
SURE = 0.45


def rows(cam, px, py):
    """The two planes a pixel puts its 3D point on, for an orthographic camera: (normal, offset) each."""
    right, up, place = np.array(cam["right"]), np.array(cam["upward"]), np.array(cam["place"])
    w, n = cam["width"], cam["size"]
    return [(right, (px / n - 0.5) * w + right @ place), (up, (0.5 - py / n) * w + up @ place)]


def project(cam, p):
    right, up, place = np.array(cam["right"]), np.array(cam["upward"]), np.array(cam["place"])
    w, n = cam["width"], cam["size"]
    return np.array([((p - place) @ right / w + 0.5) * n, (0.5 - (p - place) @ up / w) * n])


def solve(obs):
    """Least squares through every (camera, pixel, score) seen; None under two views."""
    if len(obs) < 2:
        return None
    a, b, wt = [], [], []
    for cam, px, py, sc in obs:
        for nrm, off in rows(cam, px, py):
            a.append(nrm)
            b.append(off)
            wt.append(sc)
    a, b, wt = np.array(a), np.array(b), np.sqrt(np.array(wt))
    return np.linalg.lstsq(a * wt[:, None], b * wt, rcond=None)[0]


def triangulate(dets, cams, swap):
    """Each joint from every view sure of it, the views' left and right swapped where swap says, dropping views
    that disagree by over three times the median."""
    out, err, used = {}, {}, {}
    names = [(f"a_{n}", i, j) for n, i, j in PAIRS] + [(f"b_{n}", j, i) for n, i, j in PAIRS] + [(n, i, i) for n, i in MIDDLE]
    for name, i, j in names:
        obs = []
        for v, (kp, sc) in enumerate(dets):
            k = j if swap[v] else i
            if sc[k] >= SURE:
                obs.append((cams[v], kp[k][0], kp[k][1], sc[k]))
        p = solve(obs)
        if p is None:
            continue
        for _ in range(2):
            e = [np.linalg.norm(project(c, p) - (x, y)) for c, x, y, _ in obs]
            keep = [o for o, ee in zip(obs, e) if ee <= max(3 * np.median(e), 6)]
            if len(keep) >= 2:
                obs, p = keep, solve(keep)
        out[name] = p
        err[name] = float(np.median([np.linalg.norm(project(c, p) - (x, y)) for c, x, y, _ in obs]))
        used[name] = len(obs)
    return out, err, used


def total_error(dets, cams, joints, v, swapped):
    e = 0.0
    for name, i, j in PAIRS:
        for side, k in (("a", j if swapped else i), ("b", i if swapped else j)):
            p = joints.get(f"{side}_{name}")
            kp, sc = dets[v]
            if p is not None and sc[k] >= SURE:
                e += min(np.linalg.norm(project(cams[v], p) - kp[k]), 80) * sc[k]
    return e


def detect(body, img):
    """The view's most certain body. The detector reads people standing: a figure upside down in a flip or flat in a
    dive is read at each quarter turn, and the turn it's surest of is turned back."""
    h, w = img.shape[:2]
    best = (np.zeros((17, 2)), np.zeros(17))
    for k in range(4):
        kp, sc = body(np.ascontiguousarray(np.rot90(img, k)))
        if not len(sc):
            continue
        i = int(np.argmax(sc.mean(axis=1)))
        if sc[i].mean() <= best[1].mean():
            continue
        x, y = kp[i][:, 0], kp[i][:, 1]
        back = {0: (x, y), 1: (w - 1 - y, x), 2: (w - 1 - x, h - 1 - y), 3: (y, h - 1 - x)}[k]
        best = (np.stack(back, axis=1), sc[i])
    return best


def main() -> int:
    renders, out = sys.argv[1], sys.argv[2]
    meta = json.load(open(os.path.join(renders, "cameras.json"), encoding="utf8"))
    cams = meta["cameras"]
    body = Body(mode="performance", backend="onnxruntime", device="cpu")
    dets, images = [], []
    for cam in cams:
        img = cv2.imread(os.path.join(renders, cam["image"]))
        dets.append(detect(body, img))
        images.append(img)
    swap = [False] * len(cams)
    for _ in range(6):
        joints, err, used = triangulate(dets, cams, swap)
        new = [total_error(dets, cams, joints, v, True) < total_error(dets, cams, joints, v, False) for v in range(len(cams))]
        if new == swap:
            break
        swap = new
    joints, err, used = triangulate(dets, cams, swap)
    ears = [joints[k] for k in ("a_ear", "b_ear") if k in joints] or [joints[k] for k in ("a_eye", "b_eye") if k in joints]
    head = sum(ears) / len(ears)
    up = head - (joints["a_hip"] + joints["b_hip"]) / 2
    up = up / np.linalg.norm(up)
    ahead = joints["nose"] - head
    ahead = ahead - up * (ahead @ up)
    right = np.cross(ahead, up)
    a_right = ((joints["a_shoulder"] - joints["b_shoulder"]) + (joints["a_hip"] - joints["b_hip"])) @ right > 0
    named = {}
    for name, p in joints.items():
        if name[:2] in ("a_", "b_"):
            side = "r" if (name[0] == "a") == a_right else "l"
            named[f"{side}_{name[2:]}"] = p
        else:
            named[name] = p
    named["head"] = head
    for side in ("r", "l"):
        e = err.pop(f"{'a' if (side == 'r') == a_right else 'b'}_ankle", None)
        if e is not None:
            err[f"{side}_ankle"] = e
    kicking = "right" if named["r_ankle"][2] > named["l_ankle"][2] else "left"
    result = {"renders": renders, "mirror_depth": meta.get("mirror_depth", False), "kicking": kicking, "error_px": {k: round(float(v), 1) for k, v in err.items()},
              "views_swapped": int(sum(swap)), "joints": {k: [round(float(u), 4) for u in v] for k, v in named.items()},
              "seen_in": {k.replace("a_", "r_" if a_right else "l_").replace("b_", "l_" if a_right else "r_"): n for k, n in used.items()}}
    json.dump(result, open(out, "w", encoding="utf8"), indent=1)
    print("reference joints:", out, "| kicking leg:", kicking, "| views relabelled:", sum(swap))
    for k in sorted(named):
        print(f"  {k:12s}", [round(float(u), 3) for u in named[k]])
    if "--sheet" in sys.argv:
        tiles = []
        for cam, img in zip(cams, images):
            t = img.copy()
            for k, p in named.items():
                x, y = project(cam, p)
                color = (60, 60, 230) if k.startswith("r_") else (230, 120, 40) if k.startswith("l_") else (80, 220, 80)
                cv2.circle(t, (int(x), int(y)), 7, color, -1)
            for side, color in (("r", (60, 60, 230)), ("l", (230, 120, 40))):
                for a, b in (("shoulder", "elbow"), ("elbow", "wrist"), ("hip", "knee"), ("knee", "ankle"), ("shoulder", "hip")):
                    pa, pb = named.get(f"{side}_{a}"), named.get(f"{side}_{b}")
                    if pa is not None and pb is not None:
                        cv2.line(t, tuple(int(u) for u in project(cam, pa)), tuple(int(u) for u in project(cam, pb)), color, 3)
            tiles.append(cv2.resize(t, (320, 320)))
        while len(tiles) % 6:
            tiles.append(np.zeros_like(tiles[0]))
        sheet = np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)])
        cv2.imwrite(sys.argv[sys.argv.index("--sheet") + 1], sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
