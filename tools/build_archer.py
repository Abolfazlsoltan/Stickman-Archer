"""Stickman archer — fused volumetric body, game rig, in-place clips.

Blender Z-up. Character faces -Y. glTF export is Y-up.
Run:
  blender --background --python build_archer.py -- --render
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Euler, Matrix, Vector

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = (SCRIPT_DIR.parent / "build") if SCRIPT_DIR.name == "tools" else (SCRIPT_DIR / "build")
OUT_DIR.mkdir(parents=True, exist_ok=True)
GLB_PATH = OUT_DIR / "StickmanArcher.glb"

# ---------------------------------------------------------------------------
# Proportions. Big head, thin limbs, feet on z=0. Relaxed pose, not a T.
# ---------------------------------------------------------------------------

HEAD_C = Vector((0.0, 0.0, 1.50))
HEAD_R = 0.178

SHO_L = Vector((-0.22, 0.0, 1.24))
ELB_L = Vector((-0.255, 0.035, 1.00))
WRI_L = Vector((-0.285, -0.015, 0.76))
HAN_L = Vector((-0.30, -0.045, 0.66))

SHO_R = Vector((0.22, 0.0, 1.24))
ELB_R = Vector((0.255, 0.035, 1.00))
WRI_R = Vector((0.285, -0.015, 0.76))
HAN_R = Vector((0.30, -0.045, 0.66))

HIP_L = Vector((-0.078, 0.0, 0.86))
KNE_L = Vector((-0.09, 0.02, 0.46))
ANK_L = Vector((-0.095, -0.005, 0.09))
TOE_L = Vector((-0.095, -0.135, 0.03))

HIP_R = Vector((0.078, 0.0, 0.86))
KNE_R = Vector((0.09, 0.02, 0.46))
ANK_R = Vector((0.095, -0.005, 0.09))
TOE_R = Vector((0.095, -0.135, 0.03))

PELVIS = Vector((0.0, 0.0, 0.90))
WAIST = Vector((0.0, 0.0, 1.00))
CHEST = Vector((0.0, 0.0, 1.16))
NECK = Vector((0.0, 0.0, 1.34))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 24


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


def new_mat(name, color, rough=0.42, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return m


def assign_mat(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def shade_smooth(obj):
    mesh = obj.data
    for p in mesh.polygons:
        p.use_smooth = True


def link_mesh(name, bm, mat=None):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    if mat:
        assign_mat(obj, mat)
    shade_smooth(obj)
    return obj


def uv_sphere(name, co, radius, u=28, v=16, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm, u_segments=u, v_segments=v, radius=radius, matrix=Matrix.LocRotScale(co, None, Vector(scale))
    )
    return link_mesh(name, bm)


def capsule(name, a, b, r0, r1, segs=16, steps=4):
    """Tapered capsule from a to b, including hemispherical caps."""
    d = b - a
    length = d.length
    if length < 1e-6:
        return uv_sphere(name, a, max(r0, r1))
    t = d.normalized()
    ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    x = t.cross(ref).normalized()
    y = t.cross(x).normalized()
    bm = bmesh.new()

    def ring(center, radius):
        verts = []
        for i in range(segs):
            ang = math.tau * i / segs
            co = center + x * (math.cos(ang) * radius) + y * (math.sin(ang) * radius)
            verts.append(bm.verts.new(co))
        return verts

    rings = []
    for i in range(steps):
        u = i / (steps - 1)
        rings.append(ring(a.lerp(b, u), r0 + (r1 - r0) * u))
    for i in range(steps - 1):
        for s in range(segs):
            s2 = (s + 1) % segs
            bm.faces.new((rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]))

    def cap(center, radius, sign, start_ring):
        prev = start_ring
        cap_rings = 3
        for k in range(1, cap_rings + 1):
            ang = (k / cap_rings) * (math.pi / 2)
            rad = radius * math.cos(ang)
            off = t * (sign * radius * math.sin(ang))
            if k == cap_rings:
                pole = bm.verts.new(center + off)
                for s in range(segs):
                    s2 = (s + 1) % segs
                    if sign > 0:
                        bm.faces.new((prev[s], prev[s2], pole))
                    else:
                        bm.faces.new((prev[s2], prev[s], pole))
            else:
                rv = ring(center + off, max(rad, 1e-5))
                for s in range(segs):
                    s2 = (s + 1) % segs
                    if sign > 0:
                        bm.faces.new((prev[s], prev[s2], rv[s2], rv[s]))
                    else:
                        bm.faces.new((prev[s2], prev[s], rv[s], rv[s2]))
                prev = rv

    cap(a, r0, -1, rings[0])
    cap(b, r1, 1, rings[-1])
    return link_mesh(name, bm)


def join_objs(objs):
    activate(objs[0])
    for o in objs:
        o.select_set(True)
    bpy.ops.object.join()
    return objs[0]


def voxel_fuse(obj, size=0.009):
    activate(obj)
    mod = obj.modifiers.new("Remesh", "REMESH")
    mod.mode = "VOXEL"
    mod.voxel_size = size
    mod.adaptivity = 0.0
    mod.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier="Remesh")
    sm = obj.modifiers.new("Smooth", "SMOOTH")
    sm.factor = 0.22
    sm.iterations = 2
    bpy.ops.object.modifier_apply(modifier="Smooth")
    shade_smooth(obj)
    print("body", obj.name, "verts", len(obj.data.vertices), "faces", len(obj.data.polygons))
    zs = [v.co.z for v in obj.data.vertices]
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    print(
        "bbox x", round(min(xs), 3), round(max(xs), 3),
        "y", round(min(ys), 3), round(max(ys), 3),
        "z", round(min(zs), 3), round(max(zs), 3),
    )
    return obj


def build_body(mat):
    parts = []
    parts.append(uv_sphere("Head", HEAD_C, HEAD_R, 40, 24))
    # neck buried in the head and the chest so the fuse is a smooth taper
    parts.append(capsule("Neck", HEAD_C + Vector((0, 0, -0.12)), CHEST + Vector((0, 0, 0.08)), 0.045, 0.055, 14, 4))
    # torso — slim, a little deeper at the chest, wider at the hips
    parts.append(capsule("Chest", CHEST + Vector((0, 0, 0.08)), WAIST, 0.078, 0.050, 16, 5))
    parts.append(uv_sphere("ChestDepth", CHEST + Vector((0, -0.012, 0.0)), 0.07, 20, 12, (1.05, 0.72, 1.15)))
    parts.append(capsule("Abdomen", WAIST, PELVIS, 0.050, 0.068, 16, 3))
    parts.append(uv_sphere("Pelvis", PELVIS, 0.072, 20, 12, (1.15, 0.78, 0.85)))

    def arm(side, sho, elb, wri, han):
        parts.append(uv_sphere(f"Sho{side}", sho, 0.052, 16, 10))
        parts.append(capsule(f"Clav{side}", CHEST + Vector((0.06 * side, 0, 0.06)), sho, 0.04, 0.048, 12, 3))
        parts.append(capsule(f"UA{side}", sho, elb, 0.034, 0.028, 14, 5))
        parts.append(uv_sphere(f"Elb{side}", elb, 0.030, 12, 8))
        parts.append(capsule(f"FA{side}", elb, wri, 0.026, 0.020, 14, 5))
        # bracer bulge, still part of the black body so the silhouette reads armor
        mid = elb.lerp(wri, 0.55)
        parts.append(uv_sphere(f"Bracer{side}", mid, 0.026, 12, 8, (1.15, 1.15, 0.7)))
        # fist. A short thick thumb, not a spike.
        parts.append(capsule(f"Palm{side}", wri, han, 0.024, 0.028, 12, 3))
        parts.append(uv_sphere(f"Fist{side}", han + Vector((0, -0.012, -0.012)), 0.032, 14, 10))
        thumb = han + Vector((0.026 * side, -0.012, 0.012))
        parts.append(uv_sphere(f"Thumb{side}", thumb, 0.018, 10, 8))

    arm(-1, SHO_L, ELB_L, WRI_L, HAN_L)
    arm(1, SHO_R, ELB_R, WRI_R, HAN_R)

    def leg(side, hip, kne, ank, toe):
        parts.append(uv_sphere(f"HipBall{side}", hip, 0.050, 14, 10))
        parts.append(capsule(f"Thigh{side}", hip, kne, 0.046, 0.034, 14, 5))
        parts.append(uv_sphere(f"Knee{side}", kne, 0.036, 12, 8))
        parts.append(capsule(f"Shin{side}", kne, ank, 0.032, 0.022, 14, 5))
        # boot: cuff, sole, toe. Thick enough to survive remesh and read from the front.
        parts.append(uv_sphere(f"Cuff{side}", ank + Vector((0, 0.0, 0.012)), 0.038, 14, 10))
        heel = Vector((ank.x, 0.02, 0.04))
        ball = Vector((ank.x, -0.07, 0.038))
        toe = Vector((ank.x, -0.135, 0.03))
        parts.append(capsule(f"Heel{side}", ank + Vector((0, 0, -0.01)), heel, 0.032, 0.036, 12, 3))
        parts.append(capsule(f"Sole{side}", heel, ball, 0.036, 0.032, 12, 3))
        parts.append(capsule(f"ToeBoot{side}", ball, toe, 0.030, 0.020, 12, 3))

    leg(-1, HIP_L, KNE_L, ANK_L, TOE_L)
    leg(1, HIP_R, KNE_R, ANK_R, TOE_R)

    body = join_objs(parts)
    body.name = "Body"
    body = voxel_fuse(body, 0.0085)
    assign_mat(body, mat)
    # drop tiny islands the remesh sometimes leaves (stray thumb shells)
    activate(body)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    islands = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    islands.sort(key=lambda o: len(o.data.vertices), reverse=True)
    body = islands[0]
    body.name = "Body"
    for extra in islands[1:]:
        print("drop island", extra.name, len(extra.data.vertices))
        bpy.data.objects.remove(extra, do_unlink=True)
    assign_mat(body, mat)
    shade_smooth(body)
    return body


def mesh_from_py(name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    assign_mat(obj, mat)
    shade_smooth(obj)
    return obj


def solid_ribbon(name, centers, widths, thick, mat):
    """Closed thin band. Side axis is kept continuous so the strip cannot flip."""
    frames = []
    prev_side = None
    for i, c in enumerate(centers):
        if i == 0:
            tang = (centers[1] - centers[0]).normalized()
        elif i == len(centers) - 1:
            tang = (centers[-1] - centers[-2]).normalized()
        else:
            tang = (centers[i + 1] - centers[i - 1]).normalized()
        side = Vector((1, 0, 0)) - tang * Vector((1, 0, 0)).dot(tang)
        if side.length < 0.25:
            side = Vector((0, 0, 1)) - tang * Vector((0, 0, 1)).dot(tang)
        side.normalize()
        if prev_side is not None and side.dot(prev_side) < 0:
            side.negate()
        prev_side = side.copy()
        up = tang.cross(side).normalized()
        frames.append((c, side, up))

    verts = []
    for (c, side, up), w in zip(frames, widths):
        hw = w * 0.5
        ht = thick * 0.5
        verts.append(c + side * hw + up * ht)
        verts.append(c - side * hw + up * ht)
        verts.append(c - side * hw - up * ht)
        verts.append(c + side * hw - up * ht)
    faces = []
    n = len(centers)
    for i in range(n - 1):
        a = i * 4
        b = a + 4
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((a + k, b + k, b + k2, a + k2))
    # caps
    faces.append((0, 1, 2, 3))
    last = (n - 1) * 4
    faces.append((last, last + 3, last + 2, last + 1))
    # quad -> triangles
    tris = []
    for f in faces:
        if len(f) == 4:
            tris.append((f[0], f[1], f[2]))
            tris.append((f[0], f[2], f[3]))
        else:
            tris.append(f)
    return mesh_from_py(name, verts, tris, mat)


def tube(name, points, radii, mat, sides=10):
    rings = []
    frames = []
    prev_x = None
    for i, p in enumerate(points):
        if i == 0:
            t = (points[1] - points[0]).normalized()
        elif i == len(points) - 1:
            t = (points[-1] - points[-2]).normalized()
        else:
            t = (points[i + 1] - points[i - 1]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.85 else Vector((1, 0, 0))
        x = t.cross(ref)
        if x.length < 1e-6:
            x = t.cross(Vector((0, 1, 0)))
        x.normalize()
        if prev_x is not None and x.dot(prev_x) < 0:
            x.negate()
        prev_x = x.copy()
        y = t.cross(x).normalized()
        frames.append((p, x, y))
    verts = []
    for i, ((p, x, y), r) in enumerate(zip(frames, radii)):
        for s in range(sides):
            a = (s / sides) * math.tau
            verts.append(p + x * (math.cos(a) * r) + y * (math.sin(a) * r))
    faces = []
    for i in range(len(points) - 1):
        for s in range(sides):
            s2 = (s + 1) % sides
            a = i * sides + s
            b = i * sides + s2
            c = (i + 1) * sides + s2
            d = (i + 1) * sides + s
            faces.append((a, b, c))
            faces.append((a, c, d))
    # end caps
    def cap(index, sign):
        cx = sum((verts[index * sides + s] for s in range(sides)), Vector()) / sides
        ci = len(verts)
        verts.append(cx)
        for s in range(sides):
            s2 = (s + 1) % sides
            a = index * sides + s
            b = index * sides + s2
            faces.append((ci, a, b) if sign < 0 else (ci, b, a))

    cap(0, -1)
    cap(len(points) - 1, 1)
    return mesh_from_py(name, verts, faces, mat)


def scarf_paths():
    """Collar is separate. Tails start at the back of the neck and fall to the left."""
    tails = []

    def tail(length, drop, sway, phase, start_x):
        pts = []
        widths = []
        for i in range(22):
            t = i / 21
            x = start_x + math.sin(t * math.pi + phase) * sway * t
            y = 0.055 + (t ** 1.05) * length
            z = 1.36 - drop * (t ** 1.08) + math.sin(t * math.pi) * 0.03
            pts.append(Vector((x, y, z)))
            w = 0.045 + math.sin(t * math.pi) * 0.07
            w *= 1.0 - 0.55 * (t ** 1.4)
            widths.append(max(0.012, w))
        widths[0] = 0.03
        return pts, widths

    tails.append(tail(0.50, 0.78, 0.10, 0.4, -0.02))
    tails.append(tail(0.38, 0.62, -0.08, 1.3, 0.04))
    return tails


def build_scarf(mat):
    # collar ring
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.078,
        minor_radius=0.016,
        major_segments=32,
        minor_segments=8,
        location=NECK + Vector((0, 0.005, -0.01)),
    )
    collar = bpy.context.active_object
    collar.name = "ScarfCollar"
    collar.scale = (1.0, 0.86, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    assign_mat(collar, mat)
    shade_smooth(collar)

    ribbons = []
    centers = []
    for i, (pts, widths) in enumerate(scarf_paths()):
        rib = solid_ribbon(f"ScarfTail{i}", pts, widths, 0.007, mat)
        ribbons.append(rib)
        centers.append(pts)
    return collar, ribbons, centers


def build_bow(mat, string_mat):
    grip = HAN_L + Vector((0.012, -0.004, 0.015))
    pts = []
    radii = []
    steps = 36
    height = 1.02
    for i in range(steps):
        t = i / (steps - 1)
        z = (t - 0.40) * height
        u = abs((t - 0.5) * 2)
        flare = u ** 1.45
        x = -0.07 * flare
        y = -0.02 * flare
        r = 0.0155 * (1.0 - 0.42 * u)
        if 0.34 < t < 0.48:
            r = 0.021
        if t < 0.035 or t > 0.965:
            r = 0.012
        pts.append(grip + Vector((x, y, z)))
        radii.append(r)
    bow = tube("Bow", pts, radii, mat, sides=12)
    a = pts[0] + Vector((0.03, 0.006, 0.0))
    b = pts[-1] + Vector((0.03, 0.006, 0.0))
    mid = a.lerp(b, 0.5) + Vector((0.01, 0.0, 0.0))
    string = tube("BowString", [a, mid, b], [0.0032, 0.0032, 0.0032], string_mat, sides=6)
    return bow, string


def build_quiver(leather, glow, shaft_mat):
    base = Vector((0.11, 0.145, 0.96))
    top = Vector((0.055, 0.165, 1.34))
    pts = [base.lerp(top, i / 8) for i in range(9)]
    radii = [0.040 - i * 0.0012 for i in range(9)]
    quiver = tube("Quiver", pts, radii, leather, sides=12)
    # lip
    lip_a = top
    lip_b = top + (top - base).normalized() * 0.03
    lip = tube("QuiverLip", [lip_a, lip_b], [0.046, 0.044], leather, sides=12)
    arrows = [quiver, lip]
    direction = (top - base).normalized()
    for k in range(4):
        ang = k * 1.4
        off = Vector((math.cos(ang) * 0.012, math.sin(ang) * 0.008, 0))
        a0 = top + off + direction * 0.02
        a1 = a0 + direction * 0.26 + Vector((0.01, 0.0, 0.02))
        arrows.append(tube(f"Arrow{k}", [a0, a1], [0.0055, 0.0045], shaft_mat, sides=6))
        tip = a1 + direction * 0.055
        arrows.append(tube(f"ArrowTip{k}", [a1, tip], [0.010, 0.001], glow, sides=6))
        # small fletch
        f0 = a0 + direction * 0.03
        f1 = f0 + Vector((0.012, 0.0, 0.02))
        arrows.append(tube(f"Fletch{k}", [f0, f1], [0.006, 0.001], leather, sides=4))
    return arrows


def build_belt(leather, glow):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.078,
        minor_radius=0.011,
        major_segments=28,
        minor_segments=8,
        location=WAIST + Vector((0, 0, -0.01)),
    )
    belt = bpy.context.active_object
    belt.name = "Belt"
    belt.scale = (1.05, 0.78, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    assign_mat(belt, leather)
    shade_smooth(belt)

    c = WAIST + Vector((0.0, -0.082, 0.0))
    s = 0.022
    verts = [
        c + Vector((0, -s * 1.15, 0)),
        c + Vector((0, s * 0.45, 0)),
        c + Vector((s * 0.7, 0, 0)),
        c + Vector((-s * 0.7, 0, 0)),
        c + Vector((0, 0, s * 1.25)),
        c + Vector((0, 0, -s * 0.7)),
    ]
    faces = [
        (0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2),
        (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5),
    ]
    gem = mesh_from_py("Gem", verts, faces, glow)
    return belt, gem


def build_strap(mat):
    a = Vector((-0.12, -0.06, 1.22))
    b = Vector((0.10, 0.08, 1.02))
    return tube("Strap", [a, a.lerp(b, 0.5) + Vector((0, -0.01, 0)), b], [0.008, 0.008, 0.008], mat, sides=6)


def build_eyes(mat):
    eyes = []
    for name, side in (("EyeL", -1), ("EyeR", 1)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1.0, location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = name
        obj.scale = (0.050, 0.006, 0.018)
        obj.location = HEAD_C + Vector((0.038 * side, -HEAD_R * 0.98, 0.016))
        obj.rotation_euler = Euler((math.radians(4), 0.0, math.radians(-18 * side)))
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        assign_mat(obj, mat)
        shade_smooth(obj)
        eyes.append(obj)
    return eyes


def build_bracers(mat):
    objs = []
    for name, a, b in (("BracerL", ELB_L, WRI_L), ("BracerR", ELB_R, WRI_R)):
        p0 = a.lerp(b, 0.42)
        p1 = a.lerp(b, 0.78)
        objs.append(tube(name, [p0, p1], [0.029, 0.026], mat, sides=12))
    return objs


# ---------------------------------------------------------------------------
# Rig. Local +X is world +X, so X rotation swings limbs in the sagittal plane.
# Positive X on a downward limb swings it backward. Positive X on the spine
# bends it forward.
# ---------------------------------------------------------------------------

def build_armature():
    arm_data = bpy.data.armatures.new("StickmanRig")
    arm = bpy.data.objects.new("StickmanRig", arm_data)
    bpy.context.collection.objects.link(arm)
    activate(arm)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones

    def bone(name, head, tail, parent=None, connect=False):
        b = eb.new(name)
        b.head = head
        b.tail = tail
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        y = (b.tail - b.head).normalized()
        target_x = Vector((1, 0, 0))
        target_x = target_x - y * target_x.dot(y)
        if target_x.length < 1e-4:
            target_x = Vector((0, 1, 0))
            target_x = target_x - y * target_x.dot(y)
        target_x.normalize()
        z_axis = target_x.cross(y).normalized()
        b.align_roll(z_axis)
        return b

    bone("Hips", PELVIS + Vector((0, 0, -0.06)), PELVIS + Vector((0, 0, 0.06)))
    bone("Spine", PELVIS + Vector((0, 0, 0.02)), WAIST, "Hips", True)
    bone("Spine1", WAIST, CHEST, "Spine", True)
    bone("Spine2", CHEST, CHEST + Vector((0, 0, 0.08)), "Spine1", True)
    bone("Neck", NECK + Vector((0, 0, -0.04)), NECK + Vector((0, 0, 0.05)), "Spine2")
    bone("Head", NECK + Vector((0, 0, 0.02)), HEAD_C + Vector((0, 0, HEAD_R * 0.95)), "Neck")

    bone("LeftShoulder", CHEST + Vector((-0.04, 0, 0.05)), SHO_L, "Spine2")
    bone("LeftArm", SHO_L, ELB_L, "LeftShoulder")
    bone("LeftForeArm", ELB_L, WRI_L, "LeftArm")
    bone("LeftHand", WRI_L, HAN_L, "LeftForeArm")

    bone("RightShoulder", CHEST + Vector((0.04, 0, 0.05)), SHO_R, "Spine2")
    bone("RightArm", SHO_R, ELB_R, "RightShoulder")
    bone("RightForeArm", ELB_R, WRI_R, "RightArm")
    bone("RightHand", WRI_R, HAN_R, "RightForeArm")

    bone("LeftUpLeg", HIP_L, KNE_L, "Hips")
    bone("LeftLeg", KNE_L, ANK_L, "LeftUpLeg")
    bone("LeftFoot", ANK_L, TOE_L, "LeftLeg")

    bone("RightUpLeg", HIP_R, KNE_R, "Hips")
    bone("RightLeg", KNE_R, ANK_R, "RightUpLeg")
    bone("RightFoot", ANK_R, TOE_R, "RightLeg")

    # scarf chains follow the two tails (sampled every few points)
    tails = scarf_paths()
    for ti, (pts, _w) in enumerate(tails):
        parent = "Neck"
        step = 5
        idxs = list(range(0, len(pts) - 1, step))
        if idxs[-1] != len(pts) - 1:
            idxs.append(len(pts) - 1)
        for k in range(len(idxs) - 1):
            name = f"Scarf{ti}_{k}"
            bone(name, pts[idxs[k]], pts[idxs[k + 1]], parent)
            parent = name

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def bone_segments(arm, skip_prefix=("Scarf",)):
    segs = []
    for b in arm.data.bones:
        if b.name.startswith(skip_prefix):
            continue
        segs.append((b.name, Vector(b.head_local), Vector(b.tail_local)))
    return segs


def scarf_segments(arm):
    segs = []
    for b in arm.data.bones:
        if b.name.startswith("Scarf") or b.name in {"Neck", "Head"}:
            segs.append((b.name, Vector(b.head_local), Vector(b.tail_local)))
    return segs


def bind_smooth(obj, segments, iterations=3, max_inf=4):
    """Distance weights to bone segments, then a short neighbor smooth."""
    mesh = obj.data
    names = []
    for name, _h, _t in segments:
        if name not in obj.vertex_groups:
            obj.vertex_groups.new(name=name)
        names.append(name)
    raw = []
    for v in mesh.vertices:
        co = v.co
        scored = []
        for name, h, t in segments:
            ab = t - h
            L2 = ab.length_squared
            if L2 < 1e-10:
                d = (co - h).length
            else:
                u = max(0.0, min(1.0, (co - h).dot(ab) / L2))
                d = (co - (h + ab * u)).length
            scored.append((d, name))
        scored.sort(key=lambda x: x[0])
        acc = {}
        for d, name in scored[:3]:
            acc[name] = acc.get(name, 0.0) + 1.0 / (d * d + 0.0004)
        s = sum(acc.values()) or 1.0
        items = sorted(((n, w / s) for n, w in acc.items()), key=lambda x: -x[1])[:max_inf]
        s2 = sum(w for _n, w in items) or 1.0
        raw.append({n: w / s2 for n, w in items if w / s2 > 0.03})

    neighbors = [[] for _ in mesh.vertices]
    for e in mesh.edges:
        a, b = e.vertices
        neighbors[a].append(b)
        neighbors[b].append(a)

    W = raw
    for _ in range(iterations):
        newW = []
        for i, nbrs in enumerate(neighbors):
            acc = {k: val * 2.0 for k, val in W[i].items()}
            coef = 2.0
            for n in nbrs:
                for k, val in W[n].items():
                    acc[k] = acc.get(k, 0.0) + val
                coef += 1.0
            s = sum(acc.values()) or 1.0
            items = sorted(((k, v / s) for k, v in acc.items()), key=lambda x: -x[1])[:max_inf]
            s2 = sum(v for _k, v in items) or 1.0
            newW.append({k: v / s2 for k, v in items if v / s2 > 0.025})
        W = newW

    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {name: obj.vertex_groups.new(name=name) for name in names}
    for i, weights in enumerate(W):
        for name, w in weights.items():
            if name in groups:
                groups[name].add([i], w, "REPLACE")


def skin(obj, arm):
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()


def weight_one(obj, bone_name):
    vg = obj.vertex_groups.new(name=bone_name)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")


# ---------------------------------------------------------------------------
# Animation. Every key stores a full pose so curves cannot drift.
# ---------------------------------------------------------------------------

BODY_BONES = [
    "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot",
    "RightUpLeg", "RightLeg", "RightFoot",
]


def scarf_bone_names(arm):
    return [b.name for b in arm.data.bones if b.name.startswith("Scarf")]


def zero_pose(arm):
    pose = {n: (0.0, 0.0, 0.0) for n in BODY_BONES}
    for n in scarf_bone_names(arm):
        pose[n] = (0.0, 0.0, 0.0)
    return pose


def pose_with(base, **overrides):
    p = dict(base)
    for k, v in overrides.items():
        p[k] = v
    return p


def key_pose(arm, frame, pose, loc=None):
    bpy.context.view_layer.objects.active = arm
    if bpy.context.object.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")
    for name, euler in pose.items():
        if name not in arm.pose.bones:
            continue
        pb = arm.pose.bones[name]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = Euler(tuple(math.radians(v) for v in euler), "XYZ")
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc:
        for name, xyz in loc.items():
            pb = arm.pose.bones[name]
            pb.location = Vector(xyz)
            pb.keyframe_insert("location", frame=frame)
    bpy.ops.object.mode_set(mode="OBJECT")


def key_root_z(arm, frame, z):
    """Armature object Z is world up. Bone-local location did not lift the mesh."""
    bpy.context.view_layer.objects.active = arm
    if bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    arm.location = (0.0, 0.0, float(z))
    arm.keyframe_insert(data_path="location", frame=frame)


def polish(action):
    if not action:
        return
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"


def new_action(arm, name):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    return act


def scarf_wave(arm, amount, roll=0.0):
    """Small per-bone offsets so the tails trail instead of staying rigid."""
    out = {}
    for n in scarf_bone_names(arm):
        # Scarf0_2 -> tail 0, index 2
        try:
            tail_i, idx = n.replace("Scarf", "").split("_")
            tail_i = int(tail_i)
            idx = int(idx)
        except ValueError:
            continue
        sign = -1 if tail_i == 1 else 1
        out[n] = (amount * (0.35 + idx * 0.45), sign * amount * 0.15 * idx, roll * sign)
    return out


def animate(arm):
    if arm.animation_data is None:
        arm.animation_data_create()
    z = zero_pose(arm)
    actions = []

    # Idle — breath, weight shift, scarf drift. 4 seconds.
    act = new_action(arm, "Idle")
    keys = {
        1: (pose_with(z, **scarf_wave(arm, 6, 3)), {"Hips": (0, 0, 0)}),
        48: (
            pose_with(
                z,
                Spine=(3.5, 1.2, 1.0),
                Spine1=(2.0, 0.0, 0.4),
                Head=(-1.5, 2.0, 0.0),
                Hips=(0.6, 2.0, 0.0),
                LeftArm=(2.0, 0, 0),
                RightArm=(-1.5, 0, 0),
                **scarf_wave(arm, 14, -6),
            ),
            {"Hips": (0.01, 0.012, 0)},
        ),
        96: (pose_with(z, **scarf_wave(arm, 6, 3)), {"Hips": (0, 0, 0)}),
    }
    for f, (p, loc) in keys.items():
        key_pose(arm, f, p, loc)
    polish(act)
    actions.append(act)

    # Walk — in place. Negative UpLeg X is forward, positive Leg X bends the knee,
    # positive Arm X swings the arm back.
    act = new_action(arm, "Walk")
    walk_rot = {
        1: dict(
            Hips=(3, -4, -2), Spine=(5, 0, 3), Spine1=(3, 0, 1), Head=(-3, 0, -1),
            LeftUpLeg=(-32, 0, 0), LeftLeg=(22, 0, 0), LeftFoot=(18, 0, 0),
            RightUpLeg=(24, 0, 0), RightLeg=(38, 0, 0), RightFoot=(-8, 0, 0),
            LeftArm=(12, 0, 2), LeftForeArm=(16, 0, 0),
            RightArm=(-26, 0, -2), RightForeArm=(30, 0, 0),
        ),
        7: dict(
            Hips=(-1, 0, 0), Spine=(4, 0, 0), Spine1=(2, 0, 0), Head=(-1, 0, 0),
            LeftUpLeg=(4, 0, 0), LeftLeg=(48, 0, 0), LeftFoot=(6, 0, 0),
            RightUpLeg=(-4, 0, 0), RightLeg=(12, 0, 0), RightFoot=(8, 0, 0),
            LeftArm=(-4, 0, 0), LeftForeArm=(16, 0, 0),
            RightArm=(4, 0, 0), RightForeArm=(16, 0, 0),
        ),
        13: dict(
            Hips=(3, 4, 2), Spine=(5, 0, -3), Spine1=(3, 0, -1), Head=(-3, 0, 1),
            RightUpLeg=(-32, 0, 0), RightLeg=(22, 0, 0), RightFoot=(18, 0, 0),
            LeftUpLeg=(24, 0, 0), LeftLeg=(38, 0, 0), LeftFoot=(-8, 0, 0),
            RightArm=(12, 0, -2), RightForeArm=(16, 0, 0),
            LeftArm=(-14, 0, 2), LeftForeArm=(22, 0, 0),
        ),
        19: dict(
            Hips=(-1, 0, 0), Spine=(4, 0, 0), Spine1=(2, 0, 0), Head=(-1, 0, 0),
            RightUpLeg=(4, 0, 0), RightLeg=(48, 0, 0), RightFoot=(6, 0, 0),
            LeftUpLeg=(-4, 0, 0), LeftLeg=(12, 0, 0), LeftFoot=(8, 0, 0),
            RightArm=(-4, 0, 0), RightForeArm=(16, 0, 0),
            LeftArm=(4, 0, 0), LeftForeArm=(16, 0, 0),
        ),
        25: dict(
            Hips=(3, -4, -2), Spine=(5, 0, 3), Spine1=(3, 0, 1), Head=(-3, 0, -1),
            LeftUpLeg=(-32, 0, 0), LeftLeg=(22, 0, 0), LeftFoot=(18, 0, 0),
            RightUpLeg=(24, 0, 0), RightLeg=(38, 0, 0), RightFoot=(-8, 0, 0),
            LeftArm=(12, 0, 2), LeftForeArm=(16, 0, 0),
            RightArm=(-26, 0, -2), RightForeArm=(30, 0, 0),
        ),
    }
    walk_loc = {
        1: {"Hips": (-0.02, 0.0, 0.0)},
        7: {"Hips": (0.0, 0.03, 0.0)},
        13: {"Hips": (0.02, 0.0, 0.0)},
        19: {"Hips": (0.0, 0.03, 0.0)},
        25: {"Hips": (-0.02, 0.0, 0.0)},
    }
    for f, rot in walk_rot.items():
        p = pose_with(z, **rot, **scarf_wave(arm, 8 if f in (1, 13, 25) else 4, 4 if f == 1 else -4))
        key_pose(arm, f, p, walk_loc[f])
    polish(act)
    actions.append(act)

    # Run
    act = new_action(arm, "Run")
    run_rot = {
        1: dict(
            Hips=(8, -6, -3), Spine=(16, 0, 4), Spine1=(8, 0, 2), Head=(-10, 0, -2),
            LeftUpLeg=(-46, 0, 0), LeftLeg=(28, 0, 0), LeftFoot=(14, 0, 0),
            RightUpLeg=(18, 0, 0), RightLeg=(62, 0, 0), RightFoot=(4, 0, 0),
            LeftArm=(16, 0, 3), LeftForeArm=(20, 0, 0),
            RightArm=(-36, 0, -4), RightForeArm=(24, 0, 0),
        ),
        5: dict(
            Hips=(4, 0, 0), Spine=(14, 0, 0), Spine1=(6, 0, 0), Head=(-8, 0, 0),
            LeftUpLeg=(6, 0, 0), LeftLeg=(22, 0, 0), LeftFoot=(4, 0, 0),
            RightUpLeg=(-8, 0, 0), RightLeg=(18, 0, 0), RightFoot=(6, 0, 0),
            LeftArm=(0, 0, 0), LeftForeArm=(24, 0, 0),
            RightArm=(0, 0, 0), RightForeArm=(24, 0, 0),
        ),
        9: dict(
            Hips=(8, 6, 3), Spine=(16, 0, -4), Spine1=(8, 0, -2), Head=(-10, 0, 2),
            RightUpLeg=(-46, 0, 0), RightLeg=(28, 0, 0), RightFoot=(14, 0, 0),
            LeftUpLeg=(18, 0, 0), LeftLeg=(62, 0, 0), LeftFoot=(4, 0, 0),
            RightArm=(16, 0, -3), RightForeArm=(20, 0, 0),
            LeftArm=(-18, 0, 3), LeftForeArm=(22, 0, 0),
        ),
        13: dict(
            Hips=(4, 0, 0), Spine=(14, 0, 0), Spine1=(6, 0, 0), Head=(-8, 0, 0),
            RightUpLeg=(6, 0, 0), RightLeg=(22, 0, 0), RightFoot=(4, 0, 0),
            LeftUpLeg=(-8, 0, 0), LeftLeg=(18, 0, 0), LeftFoot=(6, 0, 0),
            LeftArm=(0, 0, 0), LeftForeArm=(24, 0, 0),
            RightArm=(0, 0, 0), RightForeArm=(24, 0, 0),
        ),
        17: dict(
            Hips=(8, -6, -3), Spine=(16, 0, 4), Spine1=(8, 0, 2), Head=(-10, 0, -2),
            LeftUpLeg=(-46, 0, 0), LeftLeg=(28, 0, 0), LeftFoot=(14, 0, 0),
            RightUpLeg=(18, 0, 0), RightLeg=(62, 0, 0), RightFoot=(4, 0, 0),
            LeftArm=(16, 0, 3), LeftForeArm=(20, 0, 0),
            RightArm=(-36, 0, -4), RightForeArm=(24, 0, 0),
        ),
    }
    run_loc = {
        1: {"Hips": (-0.02, 0.0, 0.0)},
        5: {"Hips": (0.0, 0.05, 0.0)},
        9: {"Hips": (0.02, 0.0, 0.0)},
        13: {"Hips": (0.0, 0.05, 0.0)},
        17: {"Hips": (-0.02, 0.0, 0.0)},
    }
    for f, rot in run_rot.items():
        p = pose_with(z, **rot, **scarf_wave(arm, 18, 8))
        key_pose(arm, f, p, run_loc[f])
    polish(act)
    actions.append(act)

    # Jump — crouch, rise, apex, land. Vertical motion lives on Hips.
    act = new_action(arm, "Jump")
    jump_rot = {
        1: dict(),
        8: dict(
            Spine=(12, 0, 0), Spine1=(6, 0, 0), Head=(4, 0, 0),
            LeftUpLeg=(-30, 0, 0), LeftLeg=(68, 0, 0), LeftFoot=(8, 0, 0),
            RightUpLeg=(-30, 0, 0), RightLeg=(68, 0, 0), RightFoot=(8, 0, 0),
            LeftArm=(6, 0, 4), LeftForeArm=(18, 0, 0),
            RightArm=(20, 0, -6), RightForeArm=(24, 0, 0),
        ),
        14: dict(
            Spine=(2, 0, 0), Head=(-6, 0, 0),
            LeftUpLeg=(8, 0, 0), LeftLeg=(8, 0, 0), LeftFoot=(-6, 0, 0),
            RightUpLeg=(8, 0, 0), RightLeg=(8, 0, 0), RightFoot=(-6, 0, 0),
            LeftArm=(-70, 0, 8), LeftForeArm=(16, 0, 0),
            RightArm=(-70, 0, -8), RightForeArm=(16, 0, 0),
        ),
        28: dict(
            Spine=(-2, 0, 0), Head=(2, 0, 0),
            LeftUpLeg=(-12, 0, 0), LeftLeg=(30, 0, 0), LeftFoot=(4, 0, 0),
            RightUpLeg=(-8, 0, 0), RightLeg=(26, 0, 0), RightFoot=(4, 0, 0),
            LeftArm=(-50, 0, 10), LeftForeArm=(12, 0, 0),
            RightArm=(-46, 0, -10), RightForeArm=(12, 0, 0),
        ),
        40: dict(
            Spine=(16, 0, 0), Spine1=(8, 0, 0), Head=(6, 0, 0),
            LeftUpLeg=(-42, 0, 0), LeftLeg=(86, 0, 0), LeftFoot=(12, 0, 0),
            RightUpLeg=(-42, 0, 0), RightLeg=(86, 0, 0), RightFoot=(12, 0, 0),
            LeftArm=(24, 0, 4), LeftForeArm=(20, 0, 0),
            RightArm=(24, 0, -4), RightForeArm=(20, 0, 0),
        ),
        52: dict(),
    }
    jump_loc = {
        # Hips local Y is world up. Local Z points forward, so do not use it for height.
        1: {"Hips": (0, 0, 0)},
        8: {"Hips": (0, -0.16, 0)},
        14: {"Hips": (0, 0.24, 0)},
        28: {"Hips": (0, 0.58, 0)},
        40: {"Hips": (0, -0.03, 0)},
        52: {"Hips": (0, 0, 0)},
    }
    for f, rot in jump_rot.items():
        wave = 4 if f < 14 else (16 if f < 40 else 8)
        p = pose_with(z, **rot, **scarf_wave(arm, wave, 2))
        key_pose(arm, f, p, None)
    # Crouch stays grounded. Apex is a real hop, about 0.7m.
    for f, height in ((1, 0.0), (8, -0.02), (14, 0.32), (28, 0.70), (40, 0.0), (52, 0.0)):
        key_root_z(arm, f, height)
    polish(act)
    actions.append(act)

    arm.animation_data.action = None
    for act in actions:
        track = arm.animation_data.nla_tracks.new()
        track.name = act.name
        strip = track.strips.new(act.name, 1, act)
        strip.name = act.name
    bpy.ops.object.mode_set(mode="OBJECT")
    return actions


def studio(scene):
    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.035, 0.042, 0.055, 1)
    bg.inputs["Strength"].default_value = 0.55

    def light(name, loc, energy, size, color):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = color
        obj = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (CHEST - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    light("Key", (1.8, -2.6, 2.6), 250, 1.6, (0.90, 0.93, 1.0))
    light("Fill", (-2.4, -1.4, 1.5), 80, 2.2, (0.55, 0.68, 0.9))
    light("Rim", (-0.4, 2.4, 2.2), 280, 1.0, (0.55, 0.78, 1.0))

    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    assign_mat(ground, new_mat("Ground", (0.025, 0.03, 0.036), rough=0.92))


def camera_look(loc, target):
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 58
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def render_still(path, loc, frame=1, look_z=0.92):
    scene = bpy.context.scene
    scene.frame_set(frame)
    rig = bpy.data.objects.get("StickmanRig")
    body = bpy.data.objects.get("Body")
    if rig is not None:
        bpy.context.view_layer.update()
        bz = body.matrix_world.translation.z if body else -1
        print(
            "frame", frame,
            "root_z", round(rig.matrix_world.translation.z, 3),
            "body_z", round(bz, 3),
            "parent", body.parent.name if body and body.parent else None,
            flush=True,
        )
    target = Vector((0.0, 0.0, look_z))
    camera_look(Vector(loc), target)
    scene.render.resolution_x = 720
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.render.film_transparent = False
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("rendered", path, flush=True)


def mute_nla(arm, muted):
    if not arm.animation_data:
        return
    for track in arm.animation_data.nla_tracks:
        track.mute = muted


def set_action(arm, name):
    mute_nla(arm, True)
    arm.animation_data.action = None if name is None else bpy.data.actions[name]
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


VARIANTS = {
    "Blue": ((0.07, 0.42, 0.95), (0.45, 0.88, 1.0)),
    "Red": ((0.82, 0.12, 0.14), (1.0, 0.38, 0.28)),
    "Gold": ((0.86, 0.64, 0.18), (1.0, 0.84, 0.40)),
    "Green": ((0.12, 0.62, 0.32), (0.45, 1.0, 0.62)),
    "Violet": ((0.52, 0.28, 0.95), (0.78, 0.62, 1.0)),
}


def paint_variant(scarf_color, glow_color):
    def set_color(mat_name, color, emit, strength, metal=0.0, rough=0.4):
        mat = bpy.data.materials[mat_name]
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if emit:
            bsdf.inputs["Emission Color"].default_value = (*emit, 1)
            bsdf.inputs["Emission Strength"].default_value = strength

    set_color("Scarf", scarf_color, None, 0, rough=0.38)
    set_color("Glow", glow_color, glow_color, 10.0, rough=0.25)
    set_color("BowString", (0.85, 0.93, 1.0), glow_color, 4.0, rough=0.2)


def export_glb(path):
    for obj in list(bpy.data.objects):
        if obj.type in {"LIGHT", "CAMERA"} or obj.name == "Ground":
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_apply=False,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_nla_strips=True,
        export_skins=True,
        export_yup=True,
        export_lights=False,
        export_cameras=False,
        export_materials="EXPORT",
    )
    print("exported", path, path.stat().st_size)


def build_all(do_render=False, do_export=True, quick=False):
    reset()
    mat_body = new_mat("Body", (0.012, 0.013, 0.016), rough=0.38, metal=0.06)
    mat_scarf = new_mat("Scarf", (0.07, 0.42, 0.95), rough=0.38)
    mat_glow = new_mat("Glow", (0.45, 0.88, 1.0), rough=0.22, emit=(0.45, 0.9, 1.0), emit_strength=10)
    mat_bow = new_mat("Bow", (0.035, 0.04, 0.05), rough=0.28, metal=0.72)
    mat_leather = new_mat("Leather", (0.09, 0.055, 0.04), rough=0.55, metal=0.08)
    mat_string = new_mat("BowString", (0.8, 0.92, 1.0), rough=0.2, emit=(0.5, 0.85, 1.0), emit_strength=3.5)
    mat_shaft = new_mat("Shaft", (0.15, 0.16, 0.18), rough=0.4, metal=0.35)
    mat_bracer = new_mat("Bracer", (0.05, 0.055, 0.065), rough=0.25, metal=0.8)

    body = build_body(mat_body)
    collar, ribbons, _centers = build_scarf(mat_scarf)
    bow, string = build_bow(mat_bow, mat_string)
    props = build_quiver(mat_leather, mat_glow, mat_shaft)
    belt, gem = build_belt(mat_leather, mat_glow)
    strap = build_strap(mat_leather)
    eyes = build_eyes(mat_glow)
    bracers = build_bracers(mat_bracer)

    arm = build_armature()
    bind_smooth(body, bone_segments(arm), iterations=7)
    skin(body, arm)

    weight_one(collar, "Neck")
    skin(collar, arm)
    for rib in ribbons:
        bind_smooth(rib, scarf_segments(arm), iterations=2, max_inf=3)
        skin(rib, arm)

    for obj, bone_name in (
        (bow, "LeftHand"),
        (string, "LeftHand"),
        (belt, "Hips"),
        (gem, "Hips"),
        (strap, "Spine2"),
        (bracers[0], "LeftForeArm"),
        (bracers[1], "RightForeArm"),
    ):
        weight_one(obj, bone_name)
        skin(obj, arm)
    for obj in props:
        weight_one(obj, "Spine2")
        skin(obj, arm)
    for obj in eyes:
        weight_one(obj, "Head")
        skin(obj, arm)

    animate(arm)

    if do_render:
        studio(bpy.context.scene)
        set_action(arm, None)
        views = {
            "front": Vector((0.15, -2.55, 1.05)),
            "side": Vector((2.55, -0.35, 1.02)),
            "threeq": Vector((1.7, -1.9, 1.08)),
            "back": Vector((-0.2, 2.55, 1.05)),
        }
        for name, loc in views.items():
            if quick:
                continue
            render_still(OUT_DIR / f"pose_{name}.png", loc, frame=1)
        threeq = Vector((1.9, -1.7, 0.95))
        clips = (
            ("Walk", (1, 7, 13)),
            ("Run", (1, 5)),
            ("Jump", (8, 28, 40)),
            ("Idle", (48,)),
        )
        if quick:
            clips = (("Jump", (8, 14, 28)),)
        for clip, frames in clips:
            set_action(arm, clip)
            for fr in frames:
                look = 0.92
                cam = threeq
                if clip == "Jump" and fr >= 20:
                    look = 1.15
                    cam = Vector((2.3, -2.5, 1.2))
                elif clip == "Jump" and fr >= 12:
                    look = 1.05
                    cam = Vector((2.15, -2.3, 1.05))
                elif clip == "Jump":
                    look = 0.85
                    cam = Vector((2.0, -2.15, 0.9))
                render_still(OUT_DIR / f"{clip.lower()}_{fr:02d}.png", cam, frame=fr, look_z=look)
        set_action(arm, None)
        mute_nla(arm, False)

    if do_export:
        mute_nla(arm, False)
        if arm.animation_data:
            arm.animation_data.action = None
        export_glb(GLB_PATH)
        # color variants — same mesh and clips, accent materials only
        for name, (scarf_c, glow_c) in VARIANTS.items():
            paint_variant(scarf_c, glow_c)
            export_glb(OUT_DIR / f"StickmanArcher_{name}.glb")


if __name__ == "__main__":
    build_all(
        do_render="--render" in sys.argv,
        do_export="--no-export" not in sys.argv,
        quick="--quick" in sys.argv,
    )
