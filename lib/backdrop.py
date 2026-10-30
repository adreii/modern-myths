"""What surrounds the Old Town: terrain, the river, the forest, wooded hills and the mountains.

    backdrop.build(ctx)   # called by oldtown.build_town()

- Terrain: one grid mesh following oldtown.ground() (Church Hill, Castle Ridge, the river bed,
  the hills rising north). Grass that turns to meadow and earth by noise.
- River: a water strip along the bed, under a stone bridge's road.
- Forest: one Geometry Nodes object instancing the stand-in trees on a cloud of points (kind,
  rotation and scale per point), so ~2,600 trees cost one object.
- Mountains: two ranges of displaced grids north of town (blue middle range, far peaks with snow);
  the compositor's distance fog (lib/lighting.py) fades them into the sky.
"""
import math
import random

import bpy
from mathutils import Vector, noise

from .oldtown import EXT, MB, P, ground, lin, noisy, plan, smooth

UP = Vector((0, 0, 1))


def _grass(ctx):
    """Grass: two greens by large noise, earthy patches, finer variation on top."""
    m = bpy.data.materials.new("Terrain")
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    big = nt.nodes.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value = 0.006
    big.inputs["Detail"].default_value = 6
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 0.15
    fine.inputs["Detail"].default_value = 8
    for n in (big, fine):
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.3, (*lin((60, 86, 42)), 1)
    cr.elements[1].position, cr.elements[1].color = 0.62, (*lin((104, 114, 62)), 1)
    e = cr.elements.new(0.46)
    e.color = (*lin((80, 104, 50)), 1)
    e = cr.elements.new(0.75)
    e.color = (*lin((116, 102, 74)), 1)
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "MULTIPLY_ADD"
    mix.inputs[1].default_value = 0.25
    nt.links.new(fine.outputs["Fac"], mix.inputs[0])
    nt.links.new(big.outputs["Fac"], mix.inputs[2])
    nt.links.new(mix.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.95
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.25
    nt.links.new(fine.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    return m


def _axis(lo, hi, step, outer_lo, outer_hi):
    """Grid lines: every `step` studs from lo to hi, then wider and wider out to the outer
    limits, so the land runs on to the horizon without a seam or a million faces."""
    xs = [lo + i * step for i in range(int((hi - lo) / step) + 1)]
    d, x = step * 2, lo
    left = []
    while x > outer_lo:
        x = max(outer_lo, x - d)
        left.append(x)
        d *= 1.18
    d, x = step * 2, xs[-1]
    right = []
    while x < outer_hi:
        x = min(outer_hi, x + d)
        right.append(x)
        d *= 1.18
    return left[::-1] + xs + right


def terrain(ctx, x0=-1000, x1=1000, z0=-1150, z1=700, step=8):
    L = ctx.L
    xs = _axis(x0, x1, step, -7000, 7000)
    zs = _axis(z0, z1, step, -1500, 7000)
    nx, nz = len(xs), len(zs)
    verts = []
    for z in zs:
        for x in xs:
            verts.append(P(x, ground(x, z, L), z))
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i)
             for j in range(nz - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new("Terrain")
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    me.materials.append(_grass(ctx))
    me.update()
    ob = bpy.data.objects.new("Backdrop.Terrain", me)
    ctx.b.into("Backdrop")._link(ob)
    return ob


def river(ctx, z0=-1150, z1=2500):
    rv = ctx.L["river"]
    mb = MB()
    pts = []
    for j in range(0, int((z1 - z0) / 10) + 1):
        z = z0 + j * 10
        x = rv["x"] + 6 * math.sin(z * 0.012)
        pts.append((x, z))
    for (xa, za), (xb, zb) in zip(pts, pts[1:]):
        w = rv["width"] * 0.55
        y = 0.05 - rv["depth"] * 0.45
        mb.poly([P(xa - w, y, za), P(xb - w, y, zb), P(xb + w, y, zb), P(xa + w, y, za)], ctx.m.water)
    ob = mb.build("Backdrop.River")
    ctx.b.into("Backdrop")._link(ob)
    # the stone bridge carrying the road over it at z = -5
    bz = -5
    bx = rv["x"] + 6 * math.sin(bz * 0.012)
    mb = MB()
    mb.abox(P(bx - 16, -1.0, bz - 5), P(bx + 16, 0.9, bz + 5), ctx.m.stone)
    for sx in (-1, 1):
        mb.abox(P(bx - 16, 0.9, bz + sx * 4.4 - 0.6), P(bx + 16, 2.4, bz + sx * 4.4 + 0.6), ctx.m.stone)
    ctx.b.into("Backdrop")._link(mb.build("Backdrop.Bridge"))


def _points(ctx):
    """Tree positions as (kind, x, z, rotation, scale)."""
    L = ctx.L
    sc = L["scatter"]
    rng = random.Random(42)
    out = []
    near = sc["forest"]["kinds"]
    # the forest belt: outside the town's ellipse, in clumps, not in the river
    tries = 0
    while sum(1 for k in out if k[0] != "far") < sc["forest"]["count"] and tries < 40000:
        tries += 1
        x, z = rng.uniform(-620, 620), rng.uniform(-330, 560)
        e = (x / 245) ** 2 + ((z + 20) / 215) ** 2
        if e < 1.0 or abs(x - L["river"]["x"]) < 18:
            continue
        clump = noise.noise(Vector((x * 0.012, z * 0.012, 5.0)))
        if clump < -0.05 + 0.25 * smooth(1.6 - e):
            continue
        out.append((rng.choice(near), x, z, rng.uniform(0, 6.283), rng.uniform(0.8, 1.25)))
    # cypress and pines on the ridge slope
    r = sc["ridge"]
    for _ in range(r["count"]):
        a = rng.uniform(0, 6.283)
        d = math.sqrt(rng.uniform(0.15, 1))
        x, z = r["x"] + math.cos(a) * r["rx"] * d, r["z"] + math.sin(a) * r["rz"] * d
        if abs(x + 82) < 18 and abs(z + 238) < 18 or abs(x + 50) < 11 and abs(z + 230) < 11:
            continue  # not inside the keep or the belfry
        out.append((rng.choice(r["kinds"]), x, z, rng.uniform(0, 6.283), rng.uniform(0.8, 1.15)))
    # wooded hills to the north: low trees, dense
    h = sc["hills"]
    for _ in range(h["count"]):
        x, z = rng.uniform(-1000, 1000), rng.uniform(-1140, -330)
        if noise.noise(Vector((x * 0.006, z * 0.006, 9.0))) < -0.25:
            continue  # clearings
        out.append(("far", x, z, rng.uniform(0, 6.283), rng.uniform(1.0, 1.6)))
    # woods and copses across the southern, eastern and western farmland, out to ~2 km
    for _ in range(h.get("south", 2600)):
        x, z = rng.uniform(-2200, 2200), rng.uniform(-300, 2200)
        if (x / 620) ** 2 + ((z - 120) / 560) ** 2 < 1.0 or abs(x - L["river"]["x"]) < 20:
            continue  # leave the near fields open around the town
        if noise.noise(Vector((x * 0.004, z * 0.004, 4.4))) < 0.05:
            continue  # woods in patches, fields between
        out.append((rng.choice(("far", "far", "oak", "pine")), x, z, rng.uniform(0, 6.283), rng.uniform(1.0, 1.6)))
    return out


def forest(ctx):
    L = ctx.L
    pts = _points(ctx)
    kinds = sorted({k for k, *_ in pts})
    # one object per kind (variant 0) in a collection the instancer picks from by index
    kc = bpy.data.collections.new("ForestKinds")
    kc.use_fake_user = True
    for i, kind in enumerate(kinds):
        src = next(o for o in ctx.tree(kind, 0).all_objects if o.type in ("MESH", "EMPTY"))
        ob = bpy.data.objects.new(f"F{i:02d}_{kind}", src.data)
        if src.type == "EMPTY":  # an imported asset: instance its collection
            ob = bpy.data.objects.new(f"F{i:02d}_{kind}", None)
            ob.instance_type, ob.instance_collection = "COLLECTION", ctx.tree(kind, 0)
        kc.objects.link(ob)
    me = bpy.data.meshes.new("ForestPoints")
    co = [tuple(P(x, ground(x, z, L) - 0.4, z)) for _, x, z, _, _ in pts]
    me.from_pydata(co, [], [])
    a = me.attributes.new("kind", "INT", "POINT")
    a.data.foreach_set("value", [kinds.index(k) for k, *_ in pts])
    a = me.attributes.new("rot", "FLOAT", "POINT")
    a.data.foreach_set("value", [r for *_, r, _ in pts])
    a = me.attributes.new("scale", "FLOAT", "POINT")
    a.data.foreach_set("value", [s for *_, s in pts])
    ob = bpy.data.objects.new("Backdrop.Forest", me)
    mod = ob.modifiers.new("Instancer", "NODES")
    mod.node_group = _instancer(kc)
    ctx.b.into("Backdrop")._link(ob)
    print(f"  forest: {len(pts)} trees, kinds {kinds}")
    return ob


def _instancer(coll):
    ng = bpy.data.node_groups.new("ForestInstancer", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n, L = ng.nodes, ng.links.new
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    ci = n.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = coll
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop = n.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    kind = n.new("GeometryNodeInputNamedAttribute")
    kind.data_type = "INT"
    kind.inputs["Name"].default_value = "kind"
    rot = n.new("GeometryNodeInputNamedAttribute")
    rot.data_type = "FLOAT"
    rot.inputs["Name"].default_value = "rot"
    scl = n.new("GeometryNodeInputNamedAttribute")
    scl.data_type = "FLOAT"
    scl.inputs["Name"].default_value = "scale"
    cxyz = n.new("ShaderNodeCombineXYZ")
    L(rot.outputs["Attribute"], cxyz.inputs["Z"])
    L(gi.outputs[0], iop.inputs["Points"])
    L(ci.outputs[0], iop.inputs["Instance"])
    L(kind.outputs["Attribute"], iop.inputs["Instance Index"])
    L(cxyz.outputs[0], iop.inputs["Rotation"])
    L(scl.outputs["Attribute"], iop.inputs["Scale"])
    L(iop.outputs[0], go.inputs[0])
    return ng


def _mountain_mat(name, rock, snow_from):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.004
    nz.inputs["Detail"].default_value = 8
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 180
    nt.links.new(nz.outputs["Fac"], add.inputs[0])
    nt.links.new(sep.outputs["Z"], add.inputs[2])
    # steepness: snow only where the slope is gentle
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = (0, 0, 1)
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (*rock[0], 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (0.92, 0.94, 1.0, 1)
    e = cr.elements.new(0.55)
    e.color = (*rock[1], 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = snow_from * 0.4, snow_from * 1.25
    nt.links.new(add.outputs[0], mr.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(mr.outputs["Result"], mul.inputs[0])
    st = nt.nodes.new("ShaderNodeMapRange")
    st.inputs["From Min"].default_value, st.inputs["From Max"].default_value = 0.45, 0.8
    st.inputs["To Min"].default_value = 0.5
    nt.links.new(dot.outputs["Value"], st.inputs["Value"])
    nt.links.new(st.outputs["Result"], mul.inputs[1])
    nt.links.new(mul.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.9
    return m


def mountain_range(ctx, name, z_front, depth, x_span, peak, n_peaks, seed, rock, snow_from, step=40, south=False):
    """A band of mountains: peaks as smooth bumps plus ridged noise, sinking at the edges.
    It runs north from z_front, or south with south=True."""
    rng = random.Random(seed)
    k = -1 if south else 1  # which way "back" is

    def zb(t):  # depth t behind the front -> z
        return z_front - k * t
    peaks = [(rng.uniform(-x_span, x_span), zb(rng.uniform(depth * 0.2, depth * 0.85)),
              rng.uniform(0.55, 1.0) * peak, rng.uniform(depth * 0.25, depth * 0.5)) for _ in range(n_peaks)]

    def h(x, z):
        v = 0.0
        for px, pz, ph, pr in peaks:
            d = math.hypot((x - px) / 1.3, z - pz)
            v = max(v, ph * math.exp(-(d / pr) ** 2))
        rid = 1 - abs(noise.noise(Vector((x * 0.0022, z * 0.0022, seed))))
        v += peak * 0.22 * rid ** 3
        t = (z_front - z) * k
        edge = smooth(t / (depth * 0.15)) * smooth((depth - t) / (depth * 0.15) + 0.3)
        return v * edge - 30

    nx, nz = int(2 * x_span / step) + 1, int(depth / step) + 1
    verts = [P(-x_span + i * step, h(-x_span + i * step, zb(j * step)), zb(j * step))
             for j in range(nz) for i in range(nx)]
    faces = [(j * nx + i, (j + 1) * nx + i, (j + 1) * nx + i + 1, j * nx + i + 1)
             for j in range(nz - 1) for i in range(nx - 1)]
    if south:
        faces = [tuple(reversed(f)) for f in faces]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    me.materials.append(_mountain_mat(f"{name}_Rock", rock, snow_from))
    me.update()
    ob = bpy.data.objects.new(f"Backdrop.{name}", me)
    ctx.b.into("Backdrop")._link(ob)
    return ob


FOG = [  # (z, x half-width, bottom, top, density): vertical haze sheets facing the town
    (-290, 900, -10, 90, 0.45), (-520, 1300, 0, 170, 0.5), (-800, 1800, 10, 260, 0.55),
    (-1120, 2600, 0, 380, 0.6), (-1750, 3600, 60, 700, 0.5),
    (430, 900, -10, 80, 0.4), (820, 1500, 0, 160, 0.5), (1350, 2400, 0, 300, 0.55), (2200, 3800, 40, 600, 0.55),
]


def _fog_mat():
    """Soft, patchy haze: white-blue, see-through, densest in the middle of each sheet."""
    m = bpy.data.materials.get("FogCard")
    if m:
        return m
    m = bpy.data.materials.new("FogCard")
    m.use_nodes = True
    nt = m.node_tree
    n, L = nt.nodes, nt.links.new
    p = next(x for x in n if x.type == "BSDF_PRINCIPLED")
    out = next(x for x in n if x.type == "OUTPUT_MATERIAL")
    p.inputs["Base Color"].default_value = (0.86, 0.89, 0.93, 1)
    p.inputs["Roughness"].default_value = 1.0
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.004
    nz.inputs["Detail"].default_value = 4
    L(tc.outputs["Object"], nz.inputs["Vector"])
    patchy = n.new("ShaderNodeMapRange")
    patchy.inputs["From Min"].default_value, patchy.inputs["From Max"].default_value = 0.35, 0.7
    L(nz.outputs["Fac"], patchy.inputs["Value"])
    sep = n.new("ShaderNodeSeparateXYZ")
    L(tc.outputs["UV"], sep.inputs[0])

    def band(sock, a, b, c, d):  # 0 below a, up to 1 by b, 1 until c, down to 0 by d
        up = n.new("ShaderNodeMapRange")
        up.interpolation_type = "SMOOTHSTEP"
        up.inputs["From Min"].default_value, up.inputs["From Max"].default_value = a, b
        dn = n.new("ShaderNodeMapRange")
        dn.interpolation_type = "SMOOTHSTEP"
        dn.inputs["From Min"].default_value, dn.inputs["From Max"].default_value = d, c
        L(sock, up.inputs["Value"])
        L(sock, dn.inputs["Value"])
        mul = n.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        L(up.outputs["Result"], mul.inputs[0])
        L(dn.outputs["Result"], mul.inputs[1])
        return mul.outputs[0]
    v = band(sep.outputs["Y"], 0.0, 0.3, 0.45, 1.0)
    u = band(sep.outputs["X"], 0.0, 0.15, 0.85, 1.0)
    a1 = n.new("ShaderNodeMath")
    a1.operation = "MULTIPLY"
    L(v, a1.inputs[0])
    L(u, a1.inputs[1])
    a2 = n.new("ShaderNodeMath")
    a2.operation = "MULTIPLY"
    L(a1.outputs[0], a2.inputs[0])
    L(patchy.outputs["Result"], a2.inputs[1])
    dens = n.new("ShaderNodeAttribute")
    dens.attribute_type, dens.attribute_name = "OBJECT", "fog_density"
    a3 = n.new("ShaderNodeMath")
    a3.operation = "MULTIPLY"
    L(a2.outputs[0], a3.inputs[0])
    L(dens.outputs["Fac"], a3.inputs[1])
    tr = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    L(a3.outputs[0], mix.inputs[0])
    L(tr.outputs[0], mix.inputs[1])
    L(p.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs["Surface"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    return m


def fog_planes(ctx):
    """Haze sheets across the valleys between the town and the hills, north and south: layers of
    depth that the mountains fade into. They only show to the camera (no shadows, no bounce)."""
    for i, (z, hw, y0, y1, dens) in enumerate(FOG):
        me = bpy.data.meshes.new(f"Fog_{i}")
        a, b = P(-hw, y0, z), P(hw, y0, z)
        c, d = P(hw, y1, z), P(-hw, y1, z)
        me.from_pydata([tuple(a), tuple(b), tuple(c), tuple(d)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
        me.materials.append(_fog_mat())
        ob = bpy.data.objects.new(f"Backdrop.Fog_{i}", me)
        ob["fog_density"] = dens
        for vis in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission",
                    "visible_volume_scatter"):
            if hasattr(ob, vis):
                setattr(ob, vis, False)
        ctx.b.into("Backdrop")._link(ob)


def build(ctx):
    terrain(ctx)
    river(ctx)
    forest(ctx)
    mountain_range(ctx, "MiddleRange", z_front=-950, depth=900, x_span=3200, peak=560, n_peaks=14, seed=3,
                   rock=(lin((62, 78, 70)), lin((96, 104, 104))), snow_from=1e6)
    mountain_range(ctx, "FarPeaks", z_front=-1900, depth=1300, x_span=4600, peak=1700, n_peaks=11, seed=8,
                   rock=(lin((96, 104, 118)), lin((128, 136, 150))), snow_from=900)
    # the other side: wooded hills, then a lower blue range far to the south
    mountain_range(ctx, "SouthHills", z_front=1900, depth=1100, x_span=4200, peak=360, n_peaks=13, seed=21,
                   rock=(lin((58, 76, 52)), lin((84, 96, 80))), snow_from=1e6, south=True)
    mountain_range(ctx, "SouthRange", z_front=3300, depth=1500, x_span=5600, peak=950, n_peaks=10, seed=34,
                   rock=(lin((92, 102, 118)), lin((124, 134, 150))), snow_from=760, south=True)
    fog_planes(ctx)
