#!/usr/bin/env python3
"""Generate a game-ready stylized Stickman Archer GLB.

Segmented rigid-body rig (correct technique for this silhouette): each volume
is parented to a bone. Animations are real TRS keyframe clips in glTF 2.0.
Color variants use the KHR_materials_variants extension.
"""

import json
import math
import struct
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "models" / "StickmanArcher.glb"

# --- math -----------------------------------------------------------------

def clamp(v, a, b):
    return max(a, min(b, v))


def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def v_norm(a):
    l = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def quat_norm(q):
    l = math.sqrt(q[0] ** 2 + q[1] ** 2 + q[2] ** 2 + q[3] ** 2) or 1.0
    return (q[0] / l, q[1] / l, q[2] / l, q[3] / l)


def quat_from_euler_xyz(rx, ry, rz):
    """Degrees. Matches THREE.Euler order XYZ / glTF common authoring."""
    x, y, z = math.radians(rx), math.radians(ry), math.radians(rz)
    c1, c2, c3 = math.cos(x / 2), math.cos(y / 2), math.cos(z / 2)
    s1, s2, s3 = math.sin(x / 2), math.sin(y / 2), math.sin(z / 2)
    return quat_norm((
        s1 * c2 * c3 + c1 * s2 * s3,
        c1 * s2 * c3 - s1 * c2 * s3,
        c1 * c2 * s3 + s1 * s2 * c3,
        c1 * c2 * c3 - s1 * s2 * s3,
    ))


def quat_slerp(a, b, t):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    dot = ax * bx + ay * by + az * bz + aw * bw
    if dot < 0:
        bx, by, bz, bw = -bx, -by, -bz, -bw
        dot = -dot
    if dot > 0.9995:
        return quat_norm((
            ax + t * (bx - ax),
            ay + t * (by - ay),
            az + t * (bz - az),
            aw + t * (bw - aw),
        ))
    theta = math.acos(clamp(dot, -1, 1))
    s = math.sin(theta)
    w1 = math.sin((1 - t) * theta) / s
    w2 = math.sin(t * theta) / s
    return (
        ax * w1 + bx * w2,
        ay * w1 + by * w2,
        az * w1 + bz * w2,
        aw * w1 + bw * w2,
    )


def smooth(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# --- geometry -------------------------------------------------------------

def transform_mesh(positions, normals, indices, translate=(0, 0, 0), scale=(1, 1, 1), rot_euler=(0, 0, 0)):
    q = quat_from_euler_xyz(*rot_euler)
    # rotate vector by quaternion
    def qrot(v):
        x, y, z = v
        qx, qy, qz, qw = q
        # t = 2 * cross(q.xyz, v)
        tx = 2 * (qy * z - qz * y)
        ty = 2 * (qz * x - qx * z)
        tz = 2 * (qx * y - qy * x)
        return (
            x + qw * tx + (qy * tz - qz * ty),
            y + qw * ty + (qz * tx - qx * tz),
            z + qw * tz + (qx * ty - qy * tx),
        )

    out_p = []
    out_n = []
    for i in range(0, len(positions), 3):
        p = (positions[i] * scale[0], positions[i + 1] * scale[1], positions[i + 2] * scale[2])
        p = qrot(p)
        p = (p[0] + translate[0], p[1] + translate[1], p[2] + translate[2])
        out_p.extend(p)
        n = qrot((normals[i], normals[i + 1], normals[i + 2]))
        n = v_norm(n)
        out_n.extend(n)
    return out_p, out_n, list(indices)


def merge_meshes(parts):
    pos, nor, idx = [], [], []
    for p, n, ix in parts:
        base = len(pos) // 3
        pos.extend(p)
        nor.extend(n)
        idx.extend(i + base for i in ix)
    return pos, nor, idx


def sphere(radius, seg=16, rings=12):
    pos, nor, idx = [], [], []
    for y in range(rings + 1):
        v = y / rings
        phi = v * math.pi
        for x in range(seg + 1):
            u = x / seg
            theta = u * math.pi * 2
            nx = math.sin(phi) * math.cos(theta)
            ny = math.cos(phi)
            nz = math.sin(phi) * math.sin(theta)
            pos.extend((nx * radius, ny * radius, nz * radius))
            nor.extend((nx, ny, nz))
    for y in range(rings):
        for x in range(seg):
            a = y * (seg + 1) + x
            b = a + seg + 1
            idx.extend((a, b, a + 1, b, b + 1, a + 1))
    return pos, nor, idx


def cylinder(radius, length, seg=12, along="y"):
    """Cylinder from 0 to length along the given axis. Caps included."""
    pos, nor, idx = [], [], []

    def put(x, y, z, nx, ny, nz):
        if along == "y":
            pos.extend((x, y, z))
            nor.extend((nx, ny, nz))
        elif along == "z":
            pos.extend((x, z, y))
            nor.extend((nx, nz, ny))
        else:
            pos.extend((y, x, z))
            nor.extend((ny, nx, nz))

    # side
    side_start = 0
    for i in range(seg + 1):
        a = (i / seg) * math.pi * 2
        cx, cz = math.cos(a), math.sin(a)
        put(cx * radius, 0, cz * radius, cx, 0, cz)
        put(cx * radius, length, cz * radius, cx, 0, cz)
    for i in range(seg):
        a = side_start + i * 2
        idx.extend((a, a + 1, a + 2, a + 1, a + 3, a + 2))
    # caps
    bot_c = len(pos) // 3
    put(0, 0, 0, 0, -1, 0)
    top_c = len(pos) // 3
    put(0, length, 0, 0, 1, 0)
    bot0 = len(pos) // 3
    for i in range(seg):
        a = (i / seg) * math.pi * 2
        cx, cz = math.cos(a), math.sin(a)
        put(cx * radius, 0, cz * radius, 0, -1, 0)
    top0 = len(pos) // 3
    for i in range(seg):
        a = (i / seg) * math.pi * 2
        cx, cz = math.cos(a), math.sin(a)
        put(cx * radius, length, cz * radius, 0, 1, 0)
    for i in range(seg):
        j = (i + 1) % seg
        idx.extend((bot_c, bot0 + j, bot0 + i))
        idx.extend((top_c, top0 + i, top0 + j))
    return pos, nor, idx


def box(sx, sy, sz):
    x, y, z = sx / 2, sy / 2, sz / 2
    # centered
    faces = [
        ((-1, 0, 0), [(-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z)]),
        ((1, 0, 0), [(x, -y, z), (x, -y, -z), (x, y, -z), (x, y, z)]),
        ((0, -1, 0), [(-x, -y, z), (-x, -y, -z), (x, -y, -z), (x, -y, z)]),
        ((0, 1, 0), [(-x, y, -z), (-x, y, z), (x, y, z), (x, y, -z)]),
        ((0, 0, -1), [(x, -y, -z), (-x, -y, -z), (-x, y, -z), (x, y, -z)]),
        ((0, 0, 1), [(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]),
    ]
    pos, nor, idx = [], [], []
    for n, quad in faces:
        b = len(pos) // 3
        for p in quad:
            pos.extend(p)
            nor.extend(n)
        idx.extend((b, b + 1, b + 2, b, b + 2, b + 3))
    return pos, nor, idx


def bow_mesh():
    """Stylized recurve bow in the XY plane, grip at origin, limbs toward +Y/-Y, belly toward -Z."""
    parts = []
    # grip
    parts.append(transform_mesh(*cylinder(0.018, 0.16, 10), translate=(0, -0.08, 0)))
    # limbs as a chain of short cylinders along an arc
    steps = 14
    for side in (1, -1):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            y = side * (0.08 + t * 0.62)
            z = -0.02 - (t ** 1.35) * 0.28
            x = 0.0
            pts.append((x, y, z))
        for i in range(steps):
            a = pts[i]
            b = pts[i + 1]
            d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            length = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
            # cylinder along Y then rotate to direction
            # build rotation from +Y to d
            direction = v_norm(d)
            up = (0, 1, 0)
            # euler approximation: yaw/pitch
            yaw = math.degrees(math.atan2(direction[0], direction[2] if False else 1))
            # direction mostly in YZ
            pitch = math.degrees(math.atan2(direction[2], direction[1] if abs(direction[1]) > 1e-4 else 1e-4))
            # +Y rotated around X by theta lands in YZ: (0, cos, sin)
            # want (0, dy, dz) so theta = atan2(dz, dy)
            theta = math.degrees(math.atan2(direction[2], direction[1]))
            r = 0.016 * (1 - 0.45 * (i / steps))
            parts.append(transform_mesh(
                *cylinder(r, length, 8),
                translate=a,
                rot_euler=(theta, 0, 0),
            ))
        # tip
        tip = pts[-1]
        parts.append(transform_mesh(*sphere(0.02, 8, 6), translate=tip))
    # string: thin boxes along a straight line between tips
    tip_y = 0.08 + 0.62
    tip_z = -0.02 - 0.28
    parts.append(transform_mesh(
        *cylinder(0.004, tip_y * 2, 6),
        translate=(0, -tip_y, tip_z),
    ))
    return merge_meshes(parts)


def crystal():
    # octahedron-like diamond
    s = 0.045
    verts = [
        (0, s * 1.4, 0),
        (s, 0, 0), (0, 0, s), (-s, 0, 0), (0, 0, -s),
        (0, -s * 1.4, 0),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1),
        (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4),
    ]
    pos, nor, idx = [], [], []
    for f in faces:
        tri = [verts[i] for i in f]
        e1 = (tri[1][0] - tri[0][0], tri[1][1] - tri[0][1], tri[1][2] - tri[0][2])
        e2 = (tri[2][0] - tri[0][0], tri[2][1] - tri[0][1], tri[2][2] - tri[0][2])
        n = v_norm((
            e1[1] * e2[2] - e1[2] * e2[1],
            e1[2] * e2[0] - e1[0] * e2[2],
            e1[0] * e2[1] - e1[1] * e2[0],
        ))
        b = len(pos) // 3
        for p in tri:
            pos.extend(p)
            nor.extend(n)
        idx.extend((b, b + 1, b + 2))
    return pos, nor, idx


# --- scene graph ----------------------------------------------------------

# Rest local euler (degrees) and translation. Mesh is a child unless mesh is None.
# Cylinder/box meshes are authored along +Y starting at the joint (or centered — see mesh def).

def M(kind, **kw):
    return {"kind": kind, **kw}


# mesh library built later
# node spec: name, parent, t, euler, mesh, mat, radius/length params stored in mesh key

NODES = []  # filled as dicts in order; index is glTF node index. mesh nodes follow bones? 
# We'll create bone nodes first, then attach mesh as the SAME node (one mesh per bone node).
# Some bones have no mesh (shoulders). Some cosmetic nodes parented to bones.


def build_nodes():
    """Return list of node dicts in glTF order. parent is name or None."""
    specs = []

    def add(name, parent, t, euler, mesh=None, mat="body"):
        specs.append({
            "name": name,
            "parent": parent,
            "t": t,
            "euler": euler,
            "mesh": mesh,
            "mat": mat,
        })

    # proportions ~1.85m
    add("hips", None, (0, 0.90, 0), (0, 0, 0), M("sphere", r=0.09), "body")
    add("spine", "hips", (0, 0.06, 0), (2, 0, 0), M("cyl", r=0.07, h=0.16), "body")
    add("chest", "spine", (0, 0.16, 0), (0, 0, 0), M("box", sx=0.28, sy=0.28, sz=0.14, oy=0.10), "body")
    add("neck", "chest", (0, 0.24, 0), (0, 0, 0), M("cyl", r=0.04, h=0.06), "body")
    add("head", "neck", (0, 0.06, 0), (0, 0, 0), M("sphere", r=0.155, oy=0.13), "body")
    add("eyeL", "head", (0.055, 0.14, 0.12), (0, 0, 0), M("sphere", r=0.028), "glow")
    add("eyeR", "head", (-0.055, 0.14, 0.12), (0, 0, 0), M("sphere", r=0.028), "glow")

    # scarf wrap + tail (scarf material = variant)
    add("scarfWrap", "neck", (0, 0.02, 0.02), (0, 0, 0), M("cyl", r=0.055, h=0.08), "scarf")
    add("scarf1", "neck", (0.0, 0.04, -0.06), (55, 0, 8), M("box", sx=0.10, sy=0.22, sz=0.02, oy=0.11), "scarf")
    add("scarf2", "scarf1", (0, 0.22, 0), (28, 0, -6), M("box", sx=0.09, sy=0.24, sz=0.018, oy=0.12), "scarf")
    add("scarf3", "scarf2", (0, 0.24, 0), (18, 12, 0), M("box", sx=0.07, sy=0.26, sz=0.016, oy=0.13), "scarf")
    add("scarf4", "scarf3", (0, 0.26, 0), (12, -10, 4), M("box", sx=0.05, sy=0.22, sz=0.014, oy=0.11), "scarf")

    # arms. Mesh cylinder along +Y. Rest rotation swings them downward.
    add("shoulderL", "chest", (0.16, 0.20, 0), (0, 0, 0), M("sphere", r=0.045), "body")
    add("upperArmL", "shoulderL", (0, 0, 0), (18, 0, -158), M("cyl", r=0.03, h=0.28), "body")
    add("lowerArmL", "upperArmL", (0, 0.28, 0), (16, 0, 6), M("cyl", r=0.026, h=0.26), "body")
    add("handL", "lowerArmL", (0, 0.26, 0), (-10, 0, 0), M("sphere", r=0.034), "body")
    add("bow", "handL", (0.0, 0.0, 0.02), (0, 90, 80), M("bow"), "bow")
    add("bowString", "bow", (0, 0, 0), (0, 0, 0), None, "glow")  # string is inside bow mesh; placeholder bone

    add("shoulderR", "chest", (-0.16, 0.20, 0), (0, 0, 0), M("sphere", r=0.045), "body")
    add("upperArmR", "shoulderR", (0, 0, 0), (18, 0, 158), M("cyl", r=0.03, h=0.28), "body")
    add("lowerArmR", "upperArmR", (0, 0.28, 0), (16, 0, -6), M("cyl", r=0.026, h=0.26), "body")
    add("handR", "lowerArmR", (0, 0.26, 0), (-10, 0, 0), M("sphere", r=0.034), "body")

    # legs
    add("upperLegL", "hips", (0.09, -0.02, 0), (4, 0, -176), M("cyl", r=0.038, h=0.44), "body")
    add("lowerLegL", "upperLegL", (0, 0.44, 0), (8, 0, 0), M("cyl", r=0.03, h=0.42), "body")
    add("footL", "lowerLegL", (0, 0.42, 0), (78, 0, 0), M("box", sx=0.07, sy=0.05, sz=0.16, oz=0.05, oy=0.0), "body")

    add("upperLegR", "hips", (-0.09, -0.02, 0), (4, 0, 176), M("cyl", r=0.038, h=0.44), "body")
    add("lowerLegR", "upperLegR", (0, 0.44, 0), (8, 0, 0), M("cyl", r=0.03, h=0.42), "body")
    add("footR", "lowerLegR", (0, 0.42, 0), (78, 0, 0), M("box", sx=0.07, sy=0.05, sz=0.16, oz=0.05, oy=0.0), "body")

    # belt + crystal
    add("belt", "hips", (0, 0.04, 0), (0, 0, 0), M("cyl", r=0.105, h=0.045), "leather")
    add("crystal", "belt", (0, 0.02, 0.10), (0, 0, 0), M("crystal"), "glow")

    # quiver on back
    add("quiver", "chest", (0.08, 0.02, -0.10), (18, 0, 12), M("cyl", r=0.045, h=0.32), "leather")
    add("arrowA", "quiver", (0.01, 0.30, 0.01), (-8, 0, 0), M("cyl", r=0.006, h=0.28), "glow")
    add("arrowB", "quiver", (-0.012, 0.30, -0.008), (-4, 6, 0), M("cyl", r=0.006, h=0.26), "glow")
    add("arrowC", "quiver", (0.0, 0.30, 0.016), (-10, -4, 0), M("cyl", r=0.006, h=0.30), "glow")

    return specs


VARIANTS = [
    ("Blue", (0.05, 0.45, 0.95, 1), (0.15, 0.85, 1.0, 1)),
    ("Red", (0.85, 0.12, 0.14, 1), (1.0, 0.25, 0.15, 1)),
    ("Gold", (0.95, 0.72, 0.15, 1), (1.0, 0.85, 0.30, 1)),
    ("Green", (0.10, 0.72, 0.32, 1), (0.30, 1.0, 0.45, 1)),
    ("Purple", (0.55, 0.22, 0.90, 1), (0.75, 0.40, 1.0, 1)),
]


def mesh_from_spec(spec):
    if spec is None:
        return None
    k = spec["kind"]
    if k == "sphere":
        p, n, i = sphere(spec["r"], 14, 10)
        oy = spec.get("oy", 0)
        if oy:
            p, n, i = transform_mesh(p, n, i, translate=(0, oy, 0))
        return p, n, i
    if k == "cyl":
        return cylinder(spec["r"], spec["h"], 12)
    if k == "box":
        p, n, i = box(spec["sx"], spec["sy"], spec["sz"])
        # authored centered; shift so origin sits at joint
        p, n, i = transform_mesh(
            p, n, i,
            translate=(0, spec["sy"] / 2 + spec.get("oy", 0) - spec["sy"] / 2 + spec.get("oy", 0), spec.get("oz", 0)),
        )
        # The formula above double-counts. Do it cleanly:
        # Recompute simply.
        p, n, i = box(spec["sx"], spec["sy"], spec["sz"])
        p, n, i = transform_mesh(
            p, n, i,
            translate=(0, spec.get("oy", 0), spec.get("oz", 0)),
        )
        return p, n, i
    if k == "bow":
        return bow_mesh()
    if k == "crystal":
        return crystal()
    raise ValueError(k)


# Fix box: I left a messy first transform then overwrite. The function returns the second. Good.


# --- animations -----------------------------------------------------------

ANIMATED = [
    "hips", "spine", "chest", "neck", "head",
    "upperArmL", "lowerArmL", "handL",
    "upperArmR", "lowerArmR", "handR",
    "upperLegL", "lowerLegL", "footL",
    "upperLegR", "lowerLegR", "footR",
    "scarf1", "scarf2", "scarf3", "scarf4",
    "bow",
]


def rest_map(specs):
    return {s["name"]: {"euler": s["euler"], "t": s["t"]} for s in specs}


def pose(over):
    return over


def sample_clip(keys, fps, specs):
    """keys: list of (time, euler_overrides, hips_t or None). Returns dense samples."""
    duration = keys[-1][0]
    n = max(2, int(round(duration * fps)) + 1)
    times = [round(i * duration / (n - 1), 5) for i in range(n)]
    rest = rest_map(specs)

    def at(t):
        if t <= keys[0][0]:
            return keys[0]
        if t >= keys[-1][0]:
            return keys[-1]
        for i in range(len(keys) - 1):
            t0, e0, h0 = keys[i]
            t1, e1, h1 = keys[i + 1]
            if t0 <= t <= t1:
                u = smooth(0 if t1 == t0 else (t - t0) / (t1 - t0))
                return ("lerp", e0, e1, h0, h1, u)
        return keys[-1]

    samples = []  # list of {bone: quat} plus hips translation
    for t in times:
        item = at(t)
        frame = {}
        if item[0] != "lerp":
            _, eulers, hips_t = item
            for b in ANIMATED:
                eu = eulers.get(b, rest[b]["euler"])
                frame[b] = quat_from_euler_xyz(*eu)
            ht = hips_t if hips_t is not None else rest["hips"]["t"]
            frame["_hips_t"] = ht
        else:
            _, e0, e1, h0, h1, u = item
            for b in ANIMATED:
                a = quat_from_euler_xyz(*(e0.get(b, rest[b]["euler"])))
                c = quat_from_euler_xyz(*(e1.get(b, rest[b]["euler"])))
                frame[b] = quat_slerp(a, c, u)
            ha = h0 if h0 is not None else rest["hips"]["t"]
            hb = h1 if h1 is not None else rest["hips"]["t"]
            frame["_hips_t"] = tuple(ha[k] + (hb[k] - ha[k]) * u for k in range(3))
        samples.append(frame)
    return times, samples


def clips(specs):
    R = rest_map(specs)
    H = R["hips"]["t"]

    def E(**kw):
        return kw

    # Idle — breathing + scarf + weight shift. 2.4s loop
    idle = [
        (0.0, E(spine=(4, 0, 0), chest=(0, 0, 0), scarf1=(55, 0, 8), scarf2=(28, 0, -6), scarf3=(18, 12, 0), scarf4=(12, -10, 4)), H),
        (1.2, E(spine=(7, 2, 1), chest=(3, 0, 0), head=( -2, 4, 0), scarf1=(62, 8, 4), scarf2=(36, 10, -10), scarf3=(26, 18, 4), scarf4=(20, -4, 8),
                upperArmL=(20, 0, -156), upperArmR=(16, 0, 160)),
         (H[0], H[1] + 0.015, H[2])),
        (2.4, E(spine=(4, 0, 0), chest=(0, 0, 0), scarf1=(55, 0, 8), scarf2=(28, 0, -6), scarf3=(18, 12, 0), scarf4=(12, -10, 4)), H),
    ]

    # Walk in place. 1.0s loop. Opposite arm / leg.
    walk = [
        (0.0, E(
            hips=(0, 0, 0), spine=(8, 0, 2),
            upperLegL=(-28, 0, -176), lowerLegL=(18, 0, 0), footL=(70, 0, 0),
            upperLegR=(24, 0, 176), lowerLegR=(-36, 0, 0), footR=(90, 0, 0),
            upperArmR=(-22, 0, 150), lowerArmR=(20, 0, -8),
            upperArmL=(20, 0, -164), lowerArmL=(10, 0, 6),
            scarf1=(60, 6, 10), scarf2=(34, 8, -8),
        ), H),
        (0.25, E(
            spine=(6, 0, 0),
            upperLegL=(0, 0, -176), lowerLegL=(8, 0, 0),
            upperLegR=(0, 0, 176), lowerLegR=(10, 0, 0),
            upperArmL=(0, 0, -158), upperArmR=(0, 0, 158),
        ), (H[0], H[1] + 0.03, H[2])),
        (0.5, E(
            hips=(0, 0, 0), spine=(8, 0, -2),
            upperLegR=(-28, 0, 176), lowerLegR=(18, 0, 0), footR=(70, 0, 0),
            upperLegL=(24, 0, -176), lowerLegL=(-36, 0, 0), footL=(90, 0, 0),
            upperArmL=(-22, 0, -150), lowerArmL=(20, 0, 8),
            upperArmR=(20, 0, 164), lowerArmR=(10, 0, -6),
            scarf1=(58, -8, 6), scarf2=(32, -6, 8),
        ), H),
        (0.75, E(
            spine=(6, 0, 0),
            upperLegL=(0, 0, -176), lowerLegL=(8, 0, 0),
            upperLegR=(0, 0, 176), lowerLegR=(10, 0, 0),
            upperArmL=(0, 0, -158), upperArmR=(0, 0, 158),
        ), (H[0], H[1] + 0.03, H[2])),
        (1.0, E(
            hips=(0, 0, 0), spine=(8, 0, 2),
            upperLegL=(-28, 0, -176), lowerLegL=(18, 0, 0), footL=(70, 0, 0),
            upperLegR=(24, 0, 176), lowerLegR=(-36, 0, 0), footR=(90, 0, 0),
            upperArmR=(-22, 0, 150), lowerArmR=(20, 0, -8),
            upperArmL=(20, 0, -164), lowerArmL=(10, 0, 6),
            scarf1=(60, 6, 10), scarf2=(34, 8, -8),
        ), H),
    ]

    # Run. 0.6s loop. Bigger swings, forward lean.
    run = [
        (0.0, E(
            spine=(18, 0, 3), chest=(8, 0, 0), head=(-8, 0, 0),
            upperLegL=(-42, 0, -174), lowerLegL=(28, 0, 0), footL=(60, 0, 0),
            upperLegR=(36, 0, 174), lowerLegR=(-55, 0, 0), footR=(95, 0, 0),
            upperArmR=(-40, 0, 140), lowerArmR=(40, 0, -10),
            upperArmL=(34, 0, -150), lowerArmL=(18, 0, 8),
            scarf1=(78, 10, 6), scarf2=(40, 14, -12), scarf3=(30, 20, 6), scarf4=(24, 8, 8),
        ), (H[0], H[1] + 0.02, H[2])),
        (0.15, E(
            spine=(16, 0, 0),
            upperLegL=(-8, 0, -174), lowerLegL=(12, 0, 0),
            upperLegR=(6, 0, 174), lowerLegR=(16, 0, 0),
        ), (H[0], H[1] + 0.07, H[2])),
        (0.3, E(
            spine=(18, 0, -3), chest=(8, 0, 0), head=(-8, 0, 0),
            upperLegR=(-42, 0, 174), lowerLegR=(28, 0, 0), footR=(60, 0, 0),
            upperLegL=(36, 0, -174), lowerLegL=(-55, 0, 0), footL=(95, 0, 0),
            upperArmL=(-40, 0, -140), lowerArmL=(40, 0, 10),
            upperArmR=(34, 0, 150), lowerArmR=(18, 0, -8),
            scarf1=(82, -12, 4), scarf2=(44, -16, 10), scarf3=(34, -8, 4), scarf4=(26, -12, 6),
        ), (H[0], H[1] + 0.02, H[2])),
        (0.45, E(
            spine=(16, 0, 0),
            upperLegR=(-8, 0, 174), lowerLegR=(12, 0, 0),
            upperLegL=(6, 0, -174), lowerLegL=(16, 0, 0),
        ), (H[0], H[1] + 0.07, H[2])),
        (0.6, E(
            spine=(18, 0, 3), chest=(8, 0, 0), head=(-8, 0, 0),
            upperLegL=(-42, 0, -174), lowerLegL=(28, 0, 0), footL=(60, 0, 0),
            upperLegR=(36, 0, 174), lowerLegR=(-55, 0, 0), footR=(95, 0, 0),
            upperArmR=(-40, 0, 140), lowerArmR=(40, 0, -10),
            upperArmL=(34, 0, -150), lowerArmL=(18, 0, 8),
            scarf1=(78, 10, 6), scarf2=(40, 14, -12), scarf3=(30, 20, 6), scarf4=(24, 8, 8),
        ), (H[0], H[1] + 0.02, H[2])),
    ]

    # Jump — one shot 0.9s
    jump = [
        (0.0, E(), H),
        (0.18, E(
            spine=(22, 0, 0), chest=(10, 0, 0),
            upperLegL=(30, 0, -170), lowerLegL=(-70, 0, 0), footL=(40, 0, 0),
            upperLegR=(30, 0, 170), lowerLegR=(-70, 0, 0), footR=(40, 0, 0),
            upperArmL=(10, 0, -140), upperArmR=(10, 0, 140),
        ), (H[0], H[1] - 0.12, H[2])),
        (0.38, E(
            spine=(8, 0, 0), head=(-6, 0, 0),
            upperLegL=(-18, 0, -176), lowerLegL=(10, 0, 0),
            upperLegR=(-18, 0, 176), lowerLegR=(10, 0, 0),
            upperArmL=(-30, 0, -40), lowerArmL=(20, 0, 0),
            upperArmR=(-30, 0, 40), lowerArmR=(20, 0, 0),
            scarf1=(40, 0, 0), scarf2=(20, 0, 0),
        ), (H[0], H[1] + 0.35, H[2])),
        (0.7, E(
            spine=(4, 0, 0),
            upperLegL=(-8, 0, -176), upperLegR=(-8, 0, 176),
            upperArmL=(-10, 0, -70), upperArmR=(-10, 0, 70),
            scarf1=(30, 8, 0), scarf2=(16, 6, 0), scarf3=(10, 0, 0),
        ), (H[0], H[1] + 0.55, H[2])),
        (0.9, E(
            upperLegL=(8, 0, -174), lowerLegL=(-16, 0, 0),
            upperLegR=(8, 0, 174), lowerLegR=(-16, 0, 0),
            scarf1=(48, 0, 4), scarf2=(24, 0, -4),
        ), (H[0], H[1] + 0.28, H[2])),
    ]

    # Landing
    landing = [
        (0.0, E(
            upperLegL=(12, 0, -174), lowerLegL=(-20, 0, 0),
            upperLegR=(12, 0, 174), lowerLegR=(-20, 0, 0),
        ), (H[0], H[1] + 0.18, H[2])),
        (0.12, E(
            spine=(20, 0, 0), chest=(8, 0, 0),
            upperLegL=(38, 0, -168), lowerLegL=(-80, 0, 0), footL=(30, 0, 0),
            upperLegR=(38, 0, 168), lowerLegR=(-80, 0, 0), footR=(30, 0, 0),
            upperArmL=(20, 0, -130), upperArmR=(20, 0, 130),
        ), (H[0], H[1] - 0.14, H[2])),
        (0.45, E(spine=(4, 0, 0)), H),
    ]

    # Turn 90 degrees over 0.55s
    turn = [
        (0.0, E(hips=(0, 0, 0)), H),
        (0.28, E(
            hips=(0, 50, 0), spine=(0, 20, 0), head=(0, 16, 0),
            upperLegL=(8, 10, -176), upperLegR=(-6, -8, 176),
        ), H),
        (0.55, E(hips=(0, 90, 0), spine=(0, 0, 0), head=(0, 0, 0)), H),
    ]

    # Celebrate
    celebrate = [
        (0.0, E(), H),
        (0.25, E(
            spine=(-8, 0, 0), head=(-10, 0, 0), chest=(-6, 0, 0),
            upperArmL=(-70, 0, -30), lowerArmL=(-10, 0, 0),
            upperArmR=(-70, 0, 30), lowerArmR=(-10, 0, 0),
            scarf1=(30, 16, 0), scarf2=(10, 20, 0), scarf3=(0, 10, 0),
        ), (H[0], H[1] + 0.08, H[2])),
        (0.5, E(
            spine=(4, 0, 0),
            upperArmL=(-40, 0, -70), upperArmR=(-40, 0, 70),
        ), H),
        (0.75, E(
            spine=(-8, 0, 0), head=(-12, 8, 0),
            upperArmL=(-80, 10, -20), lowerArmL=(-20, 0, 10),
            upperArmR=(-80, -10, 20), lowerArmR=(-20, 0, -10),
            scarf1=(24, -14, 6), scarf2=(8, -18, -4),
        ), (H[0], H[1] + 0.10, H[2])),
        (1.0, E(
            spine=(-8, 0, 0), head=(-10, 0, 0),
            upperArmL=(-70, 0, -30), upperArmR=(-70, 0, 30),
            scarf1=(30, 16, 0), scarf2=(10, 20, 0),
        ), (H[0], H[1] + 0.08, H[2])),
    ]

    # Draw bow — left arm extends, right pulls. Bow rotates up.
    draw = [
        (0.0, E(), H),
        (0.45, E(
            spine=(6, -18, 0), chest=(4, -16, 0), head=(0, -14, 0),
            upperArmL=(-78, -20, -80), lowerArmL=(8, 0, 4), handL=(-20, 0, 0),
            upperArmR=(-70, 30, 40), lowerArmR=(-55, 0, -20), handR=(10, 0, 0),
            bow=(0, 70, 20),
            scarf1=(50, -8, 4), scarf2=(26, -6, 0),
        ), H),
    ]

    # Shoot — release snap
    shoot = [
        (0.0, E(
            spine=(6, -18, 0), chest=(4, -16, 0), head=(0, -14, 0),
            upperArmL=(-78, -20, -80), lowerArmL=(8, 0, 4), handL=(-20, 0, 0),
            upperArmR=(-70, 30, 40), lowerArmR=(-55, 0, -20), handR=(10, 0, 0),
            bow=(0, 70, 20),
        ), H),
        (0.12, E(
            spine=(2, -10, 0), chest=(0, -6, 0), head=(0, -6, 0),
            upperArmL=(-74, -10, -86), lowerArmL=(4, 0, 0),
            upperArmR=(-20, 10, 150), lowerArmR=(24, 0, -8),
            bow=(0, 90, 70),
            scarf1=(64, 10, 6), scarf2=(34, 12, -8),
        ), H),
        (0.4, E(), H),
    ]

    # Hit
    hit = [
        (0.0, E(), H),
        (0.12, E(
            spine=(-16, 20, -8), chest=(-10, 14, 0), head=(-14, 18, 0),
            upperArmL=(20, 0, -120), upperArmR=(30, 0, 100),
            scarf1=(70, 16, -10), scarf2=(40, 10, -16),
        ), (H[0] - 0.02, H[1], H[2] + 0.04)),
        (0.45, E(), H),
    ]

    # Fall
    fall = [
        (0.0, E(), H),
        (0.25, E(
            spine=(-30, 0, 6), chest=(-16, 0, 0), head=(-20, 0, 0),
            upperArmL=(-20, 0, -100), upperArmR=(-40, 0, 80),
            upperLegL=(16, 0, -170), upperLegR=(10, 0, 172),
            scarf1=(20, 0, 0), scarf2=(8, 0, 0),
        ), (H[0], H[1] + 0.05, H[2])),
        (0.6, E(
            hips=(-70, 0, 0), spine=(-20, 0, 0), head=(-10, 0, 0),
            upperArmL=(10, 0, -80), upperArmR=(16, 0, 60),
            upperLegL=(20, 0, -160), lowerLegL=(-30, 0, 0),
            upperLegR=(24, 0, 160), lowerLegR=(-24, 0, 0),
            scarf1=(10, 20, 0), scarf2=(0, 16, 0), scarf3=(-10, 10, 0),
        ), (H[0], 0.55, 0.05)),
    ]

    # Death — collapse and hold
    death = [
        (0.0, E(), H),
        (0.35, E(
            spine=(-24, 10, 8), head=(-16, 0, 6),
            upperArmL=(16, 0, -110), upperArmR=(24, 0, 90),
        ), (H[0], H[1] - 0.05, H[2])),
        (1.05, E(
            hips=(-82, 12, 0), spine=(-8, 0, 10), chest=(0, 0, 6), head=(8, 20, 0), neck=(10, 0, 0),
            upperArmL=(40, 0, -70), lowerArmL=(-20, 0, 0),
            upperArmR=(20, 0, 40), lowerArmR=(-50, 0, 0),
            upperLegL=(18, 0, -150), lowerLegL=(-46, 0, 0), footL=(40, 0, 0),
            upperLegR=(36, 0, 164), lowerLegR=(-20, 0, 0),
            scarf1=(6, 30, 10), scarf2=(-8, 24, -6), scarf3=(-16, 10, 0), scarf4=(-10, 0, 8),
        ), (0.05, 0.22, 0.08)),
        (1.4, E(
            hips=(-82, 12, 0), spine=(-8, 0, 10), chest=(0, 0, 6), head=(8, 20, 0), neck=(10, 0, 0),
            upperArmL=(40, 0, -70), lowerArmL=(-20, 0, 0),
            upperArmR=(20, 0, 40), lowerArmR=(-50, 0, 0),
            upperLegL=(18, 0, -150), lowerLegL=(-46, 0, 0), footL=(40, 0, 0),
            upperLegR=(36, 0, 164), lowerLegR=(-20, 0, 0),
            scarf1=(6, 30, 10), scarf2=(-8, 24, -6), scarf3=(-16, 10, 0), scarf4=(-10, 0, 8),
        ), (0.05, 0.22, 0.08)),
    ]

    fps = {
        "Idle": 12, "Walk": 20, "Run": 20, "Jump": 20, "Landing": 20,
        "Turn": 20, "Celebrate": 16, "Draw": 16, "Shoot": 20, "Hit": 20,
        "Fall": 16, "Death": 16,
    }
    raw = [
        ("Idle", idle, True),
        ("Walk", walk, True),
        ("Run", run, True),
        ("Jump", jump, False),
        ("Landing", landing, False),
        ("Turn", turn, False),
        ("Celebrate", celebrate, True),
        ("Draw", draw, False),
        ("Shoot", shoot, False),
        ("Hit", hit, False),
        ("Fall", fall, False),
        ("Death", death, False),
    ]
    out = []
    for name, keys, loop in raw:
        times, samples = sample_clip(keys, fps[name], specs)
        out.append({"name": name, "times": times, "samples": samples, "loop": loop})
    return out


# --- glTF pack ------------------------------------------------------------

class Blob:
    def __init__(self):
        self.buf = bytearray()
        self.views = []
        self.accessors = []

    def pad(self, n=4):
        while len(self.buf) % n:
            self.buf.append(0)

    def add(self, data: bytes, target=None):
        self.pad(4)
        start = len(self.buf)
        self.buf.extend(data)
        view = {"buffer": 0, "byteOffset": start, "byteLength": len(data)}
        if target:
            view["target"] = target
        vi = len(self.views)
        self.views.append(view)
        return vi

    def add_accessor(self, values, ctype, atype, target=None, minmax=None):
        """values: flat list of numbers. ctype 'f' or 'H'."""
        if ctype == "f":
            raw = struct.pack("<" + "f" * len(values), *values)
            comp = 5126
            count_div = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[atype]
        elif ctype == "H":
            raw = struct.pack("<" + "H" * len(values), *values)
            comp = 5123
            count_div = 1
            atype = "SCALAR"
        else:
            raise ValueError(ctype)
        vi = self.add(raw, target)
        acc = {
            "bufferView": vi,
            "byteOffset": 0,
            "componentType": comp,
            "count": len(values) // count_div,
            "type": atype,
        }
        if minmax is not None:
            acc["min"] = minmax[0]
            acc["max"] = minmax[1]
        elif atype == "SCALAR" and ctype == "f":
            acc["min"] = [min(values)]
            acc["max"] = [max(values)]
        ai = len(self.accessors)
        self.accessors.append(acc)
        return ai


def build():
    specs = build_nodes()
    # geometry cache by a hash of spec
    cache = {}

    def geom(mesh_spec):
        if mesh_spec is None:
            return None
        key = json.dumps(mesh_spec, sort_keys=True)
        if key not in cache:
            cache[key] = mesh_from_spec(mesh_spec)
        return cache[key]

    blob = Blob()

    # materials: body, leather, bow, then scarf x5, glow x5
    # indices:
    # 0 body, 1 leather, 2 bow metal
    # scarf: 3..7  (variant 0..4)
    # glow:  8..12
    materials = [
        {
            "name": "Body",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.02, 0.02, 0.025, 1],
                "metallicFactor": 0.15,
                "roughnessFactor": 0.55,
            },
        },
        {
            "name": "Leather",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.08, 0.06, 0.05, 1],
                "metallicFactor": 0.05,
                "roughnessFactor": 0.7,
            },
        },
        {
            "name": "Bow",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.04, 0.05, 0.07, 1],
                "metallicFactor": 0.6,
                "roughnessFactor": 0.35,
            },
        },
    ]
    for i, (name, scarf, glow) in enumerate(VARIANTS):
        materials.append({
            "name": f"Scarf_{name}",
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(scarf),
                "metallicFactor": 0.05,
                "roughnessFactor": 0.45,
            },
        })
    for i, (name, scarf, glow) in enumerate(VARIANTS):
        materials.append({
            "name": f"Glow_{name}",
            "pbrMetallicRoughness": {
                "baseColorFactor": list(glow),
                "metallicFactor": 0.0,
                "roughnessFactor": 0.25,
            },
            "emissiveFactor": list(glow[:3]),
        })

    scarf_mats = [3 + i for i in range(5)]
    glow_mats = [8 + i for i in range(5)]

    mat_index_default = {
        "body": 0,
        "leather": 1,
        "bow": 2,
        "scarf": scarf_mats[0],
        "glow": glow_mats[0],
    }

    # Build unique meshes (geometry + default material). Variant mappings on primitives that recolor.
    mesh_entries = []  # parallel to unique geoms
    spec_to_mesh_index = {}

    nodes = []
    name_to_index = {}

    for spec in specs:
        idx = len(nodes)
        name_to_index[spec["name"]] = idx
        node = {
            "name": spec["name"],
            "translation": [round(x, 5) for x in spec["t"]],
            "rotation": [round(x, 6) for x in quat_from_euler_xyz(*spec["euler"])],
        }
        if spec["mesh"] is not None:
            key = json.dumps({"m": spec["mesh"], "mat": spec["mat"]}, sort_keys=True)
            if key not in spec_to_mesh_index:
                p, n, ix = geom(spec["mesh"])
                # bounds
                xs = p[0::3]; ys = p[1::3]; zs = p[2::3]
                pmin = [min(xs), min(ys), min(zs)]
                pmax = [max(xs), max(ys), max(zs)]
                nmin = [min(n[0::3]), min(n[1::3]), min(n[2::3])]
                nmax = [max(n[0::3]), max(n[1::3]), max(n[2::3])]
                pa = blob.add_accessor(p, "f", "VEC3", 34962, ([round(v, 5) for v in pmin], [round(v, 5) for v in pmax]))
                na = blob.add_accessor(n, "f", "VEC3", 34962, (nmin, nmax))
                ia = blob.add_accessor(ix, "H", "SCALAR", 34963)
                mat_name = spec["mat"]
                prim = {
                    "attributes": {"POSITION": pa, "NORMAL": na},
                    "indices": ia,
                    "material": mat_index_default[mat_name],
                }
                if mat_name in ("scarf", "glow"):
                    group = scarf_mats if mat_name == "scarf" else glow_mats
                    prim["extensions"] = {
                        "KHR_materials_variants": {
                            "mappings": [
                                {"material": group[vi], "variants": [vi]} for vi in range(5)
                            ]
                        }
                    }
                spec_to_mesh_index[key] = len(mesh_entries)
                mesh_entries.append({
                    "name": f"mesh_{spec['name']}",
                    "primitives": [prim],
                })
            node["mesh"] = spec_to_mesh_index[key]
        nodes.append(node)

    # children
    children = {i: [] for i in range(len(nodes))}
    roots = []
    for spec in specs:
        i = name_to_index[spec["name"]]
        if spec["parent"] is None:
            roots.append(i)
        else:
            children[name_to_index[spec["parent"]]].append(i)
    for i, ch in children.items():
        if ch:
            nodes[i]["children"] = ch

    # animations
    anim_clips = clips(specs)
    animations = []
    loop_meta = {}
    for clip in anim_clips:
        channels = []
        samplers = []
        times = clip["times"]
        # time accessor reused per clip
        t_acc = blob.add_accessor(times, "f", "SCALAR")
        # hips translation
        hips_vals = []
        for fr in clip["samples"]:
            hips_vals.extend(fr["_hips_t"])
        h_acc = blob.add_accessor(hips_vals, "f", "VEC3")
        samplers.append({"input": t_acc, "output": h_acc, "interpolation": "LINEAR"})
        channels.append({
            "sampler": 0,
            "target": {"node": name_to_index["hips"], "path": "translation"},
        })
        for b in ANIMATED:
            vals = []
            for fr in clip["samples"]:
                q = fr[b]
                vals.extend(q)
            q_acc = blob.add_accessor(vals, "f", "VEC4")
            si = len(samplers)
            samplers.append({"input": t_acc, "output": q_acc, "interpolation": "LINEAR"})
            channels.append({
                "sampler": si,
                "target": {"node": name_to_index[b], "path": "rotation"},
            })
        animations.append({"name": clip["name"], "channels": channels, "samplers": samplers})
        loop_meta[clip["name"]] = clip["loop"]

    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "stickman-archer-procedural",
            "copyright": "Abolfazl Soltani",
        },
        "extensionsUsed": ["KHR_materials_variants"],
        "extensions": {
            "KHR_materials_variants": {
                "variants": [{"name": name} for name, _, _ in VARIANTS]
            }
        },
        "scene": 0,
        "scenes": [{"name": "StickmanArcher", "nodes": roots}],
        "nodes": nodes,
        "meshes": mesh_entries,
        "materials": materials,
        "animations": animations,
        "accessors": blob.accessors,
        "bufferViews": blob.views,
        "buffers": [{"byteLength": len(blob.buf)}],
        "extras": {
            "rig": "segmented-rigid",
            "boneCount": len(nodes),
            "looping": loop_meta,
            "facing": "+Z",
            "up": "+Y",
            "units": "meters",
            "colorVariants": [v[0] for v in VARIANTS],
            "notes": "Rigid segments parented to joints. Not a smooth-skinned humanoid. Animations are authored keyframes, in-place except Jump/Fall/Death which move the hips.",
        },
    }

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    # GLB pad JSON with spaces to 4
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "
    bin_bytes = bytes(blob.buf)
    while len(bin_bytes) % 4 != 0:
        bin_bytes += b"\x00"

    # total length
    # header 12 + json chunk 8+len + bin chunk 8+len
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    out = bytearray()
    out += struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(json_bytes), 0x4E4F534A)
    out += json_bytes
    out += struct.pack("<II", len(bin_bytes), 0x004E4942)
    out += bin_bytes
    OUT.write_bytes(out)
    print(f"wrote {OUT} ({len(out)} bytes)")
    print("nodes", len(nodes), "meshes", len(mesh_entries), "anims", [a['name'] for a in animations])
    print("loops", loop_meta)
    return OUT


if __name__ == "__main__":
    build()
