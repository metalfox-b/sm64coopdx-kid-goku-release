"""Forward kinematics and a small optimizer for his rig, shared by the pose tools (pose_fit.py, pose_copy.py,
pose_from_reference.py, reference_views.py, body_limits.py). Runs inside Blender, for mathutils.
"""
from __future__ import annotations

import os
import random
import sys

from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anims as A

def frame(v):
    """A vector in his own axes: his left, up, ahead."""
    return Vector((v.x, v.z, -v.y))


def fk(p):
    """Each bone's position and world rotation for a full pose."""
    loc = A.local_rotations(p)
    world = {"Body": A.R0 @ A.BODY}
    pos = {"Body": Vector(), "Butt": Vector()}
    for bone in A.ORDER[1:]:
        par = A.PARENT[bone]
        if bone != "Butt":
            up, right, forward = A.REST[bone]
            pos[bone] = pos[par] + world[par] @ Vector((up, forward, -right))
        world[bone] = world[par] @ loc[bone]
    return pos, world



def descend(cost, seed, limits, starts=3, spread=40):
    """Coordinate descent from the seed (and starts - 1 jittered copies), halving the step until it stops moving."""
    rng = random.Random(9)
    best, bc = list(seed), cost(seed)
    for start in range(starts):
        a = list(seed) if start == 0 else [max(lo, min(hi, s + rng.uniform(-spread, spread))) for s, (lo, hi) in zip(seed, limits)]
        c = cost(a)
        step = 20.0
        while step > 0.5:
            moved = False
            for i in range(len(a)):
                for d in (-step, step):
                    b = list(a)
                    b[i] = max(limits[i][0], min(limits[i][1], b[i] + d))
                    cb = cost(b)
                    if cb < c:
                        a, c, moved = b, cb, True
            if not moved:
                step /= 2
        if c < bc:
            best, bc = a, c
    return best
